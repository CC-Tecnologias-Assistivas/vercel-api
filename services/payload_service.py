import json
import secrets
from json import JSONDecodeError
from datetime import datetime, timezone
from typing import Any

from fastapi import Request

from core.config import Settings
from core.errors import InvalidPayloadError, PayloadNotFoundError, PayloadTooLargeError
from repositories.redis_repository import RedisPayloadRepository
from schemas.payload_schema import (
    CreatePayloadResponse,
    PayloadStatusFoundResponse,
    PayloadStatusNotFoundResponse,
    RetrievePayloadResponse,
    StoredPayload,
)


class PayloadService:
    def __init__(self, repository: RedisPayloadRepository, settings: Settings) -> None:
        self._repository = repository
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
            payload = await request.json()
        except JSONDecodeError as exc:
            raise InvalidPayloadError from exc

        if not isinstance(payload, dict) or not payload:
            raise InvalidPayloadError

        payload_id = self._generate_payload_id()
        redis_key = self._redis_key(payload_id)
        stored_payload = StoredPayload(
            created_at=datetime.now(timezone.utc).isoformat(),
            source="sistema-a",
            payload=payload,
        )

        self._repository.set_payload(
            redis_key,
            stored_payload.model_dump_json(),
            self._settings.payload_ttl_seconds,
        )

        return CreatePayloadResponse(
            id=payload_id,
            expires_in_seconds=self._settings.payload_ttl_seconds,
            expires_in_minutes=self._settings.payload_ttl_seconds // 60,
        )

    def consume_payload(self, payload_id: str) -> RetrievePayloadResponse:
        stored_value = self._repository.getdel_payload(self._redis_key(payload_id))
        if stored_value is None:
            raise PayloadNotFoundError

        stored_payload = self._parse_stored_payload(stored_value)
        return RetrievePayloadResponse(
            id=payload_id,
            payload=stored_payload["payload"],
            consumed=True,
        )

    def get_payload_status(
        self, payload_id: str
    ) -> PayloadStatusFoundResponse | PayloadStatusNotFoundResponse:
        redis_key = self._redis_key(payload_id)
        if not self._repository.payload_exists(redis_key):
            return PayloadStatusNotFoundResponse(id=payload_id)

        ttl_seconds = self._repository.get_ttl(redis_key)
        if ttl_seconds < 0:
            return PayloadStatusNotFoundResponse(id=payload_id)

        return PayloadStatusFoundResponse(id=payload_id, ttl_seconds=ttl_seconds)

    @staticmethod
    def _generate_payload_id() -> str:
        return f"payload_{secrets.token_urlsafe(32)}"

    @staticmethod
    def _redis_key(payload_id: str) -> str:
        return f"payload:{payload_id}"

    @staticmethod
    def _parse_stored_payload(stored_value: Any) -> dict[str, Any]:
        if isinstance(stored_value, dict):
            return stored_value

        if isinstance(stored_value, bytes):
            stored_value = stored_value.decode("utf-8")

        return json.loads(stored_value)
