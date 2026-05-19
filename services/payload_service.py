import json
import secrets
from datetime import datetime, timedelta, timezone
from json import JSONDecodeError

from fastapi import Request

from core.config import Settings
from core.errors import InvalidPayloadError, PayloadNotFoundError, PayloadTooLargeError
from repositories.supabase_payload_repository import SupabasePayloadRepository
from schemas.payload_schema import (
    CreatePayloadResponse,
    PayloadStatusFoundResponse,
    PayloadStatusNotFoundResponse,
    RetrievePayloadResponse,
)


class PayloadService:
    def __init__(self, repository: SupabasePayloadRepository, settings: Settings) -> None:
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
            payload = json.loads(raw_body)
        except JSONDecodeError as exc:
            raise InvalidPayloadError from exc

        if not isinstance(payload, dict) or not payload:
            raise InvalidPayloadError

        payload_id = self._generate_payload_id()
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(seconds=self._settings.payload_ttl_seconds)

        self._repository.insert_payload(
            payload_id=payload_id,
            created_at=created_at,
            expires_at=expires_at,
            payload=payload,
        )

        return CreatePayloadResponse(
            id=payload_id,
            expires_in_seconds=self._settings.payload_ttl_seconds,
            expires_in_minutes=self._settings.payload_ttl_seconds // 60,
        )

    def consume_payload(self, payload_id: str) -> RetrievePayloadResponse:
        row = self._repository.consume_payload(
            payload_id=payload_id,
            consumed_at=datetime.now(timezone.utc),
        )
        if row is None:
            raise PayloadNotFoundError

        return RetrievePayloadResponse(
            id=payload_id,
            payload=row["payload"],
            consumed=True,
        )

    def consume_next_payload(self) -> RetrievePayloadResponse:
        row = self._repository.consume_next_payload(
            consumed_at=datetime.now(timezone.utc),
        )
        if row is None:
            raise PayloadNotFoundError

        return RetrievePayloadResponse(
            id=row["id"],
            payload=row["payload"],
            consumed=True,
        )

    def get_payload_status(
        self, payload_id: str
    ) -> PayloadStatusFoundResponse | PayloadStatusNotFoundResponse:
        row = self._repository.get_payload_status(payload_id)
        if row is None or row.get("consumed_at"):
            return PayloadStatusNotFoundResponse(id=payload_id)

        expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
        ttl_seconds = int((expires_at - datetime.now(timezone.utc)).total_seconds())
        if ttl_seconds <= 0:
            return PayloadStatusNotFoundResponse(id=payload_id)

        return PayloadStatusFoundResponse(id=payload_id, ttl_seconds=ttl_seconds)

    @staticmethod
    def _generate_payload_id() -> str:
        return f"payload_{secrets.token_urlsafe(32)}"
