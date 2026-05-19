import base64
import hashlib
import hmac
import json
import time
from json import JSONDecodeError
from typing import Any

from fastapi import Request

from core.config import Settings
from core.errors import InvalidPayloadError, PayloadNotFoundError, PayloadTooLargeError
from schemas.payload_schema import (
    CreatePayloadResponse,
    PayloadStatusFoundResponse,
    PayloadStatusNotFoundResponse,
    RetrievePayloadResponse,
)


class PayloadService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def create_payload(self, request: Request) -> CreatePayloadResponse:
        content_type = request.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            raise InvalidPayloadError

        raw_body = await request.body()
        if len(raw_body) > self._settings.max_payload_bytes:
            raise PayloadTooLargeError

        if not raw_body:
            raise InvalidPayloadError

        try:
            payload = json.loads(raw_body)
        except JSONDecodeError as exc:
            raise InvalidPayloadError from exc

        if not isinstance(payload, dict) or not payload:
            raise InvalidPayloadError

        now = int(time.time())
        envelope = {
            "created_at": now,
            "expires_at": now + self._settings.payload_ttl_seconds,
            "source": "sistema-a",
            "payload": payload,
        }
        payload_id = self._encode_token(envelope)

        return CreatePayloadResponse(
            id=payload_id,
            expires_in_seconds=self._settings.payload_ttl_seconds,
            expires_in_minutes=self._settings.payload_ttl_seconds // 60,
        )

    def consume_payload(self, payload_id: str) -> RetrievePayloadResponse:
        stored_payload = self._decode_token(payload_id)
        return RetrievePayloadResponse(
            id=payload_id,
            payload=stored_payload["payload"],
            consumed=True,
        )

    def get_payload_status(
        self, payload_id: str
    ) -> PayloadStatusFoundResponse | PayloadStatusNotFoundResponse:
        try:
            stored_payload = self._decode_token(payload_id)
        except PayloadNotFoundError:
            return PayloadStatusNotFoundResponse(id=payload_id)

        ttl_seconds = int(stored_payload["expires_at"]) - int(time.time())
        if ttl_seconds <= 0:
            return PayloadStatusNotFoundResponse(id=payload_id)

        return PayloadStatusFoundResponse(id=payload_id, ttl_seconds=ttl_seconds)

    def _encode_token(self, envelope: dict[str, Any]) -> str:
        body = json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode("utf-8")
        body_token = self._base64url_encode(body)
        signature = self._sign(body_token)
        return f"payload_{body_token}.{signature}"

    def _decode_token(self, payload_id: str) -> dict[str, Any]:
        if not payload_id.startswith("payload_"):
            raise PayloadNotFoundError

        token = payload_id.removeprefix("payload_")
        try:
            body_token, signature = token.rsplit(".", 1)
        except ValueError as exc:
            raise PayloadNotFoundError from exc

        expected_signature = self._sign(body_token)
        if not hmac.compare_digest(signature, expected_signature):
            raise PayloadNotFoundError

        try:
            raw_body = self._base64url_decode(body_token)
            envelope = json.loads(raw_body)
        except (JSONDecodeError, ValueError) as exc:
            raise PayloadNotFoundError from exc

        if not isinstance(envelope, dict) or not isinstance(envelope.get("payload"), dict):
            raise PayloadNotFoundError

        expires_at = envelope.get("expires_at")
        if not isinstance(expires_at, int) or expires_at <= int(time.time()):
            raise PayloadNotFoundError

        return envelope

    def _sign(self, body_token: str) -> str:
        digest = hmac.new(
            self._signing_secret().encode("utf-8"),
            body_token.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return self._base64url_encode(digest)

    def _signing_secret(self) -> str:
        if self._settings.transfer_signing_secret:
            return self._settings.transfer_signing_secret

        return f"{self._settings.system_a_api_key}:{self._settings.system_b_api_key}"

    @staticmethod
    def _base64url_encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")

    @staticmethod
    def _base64url_decode(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)
