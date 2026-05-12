from typing import Any

from pydantic import BaseModel, ConfigDict


class CreatePayloadResponse(BaseModel):
    id: str
    expires_in_seconds: int
    expires_in_minutes: int


class RetrievePayloadResponse(BaseModel):
    id: str
    payload: dict[str, Any]
    consumed: bool = True


class PayloadStatusFoundResponse(BaseModel):
    id: str
    exists: bool = True
    ttl_seconds: int


class PayloadStatusNotFoundResponse(BaseModel):
    id: str
    exists: bool = False
    reason: str = "expired_or_consumed_or_not_found"


class HealthResponse(BaseModel):
    status: str
    service: str


class StoredPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    created_at: str
    source: str
    payload: dict[str, Any]
