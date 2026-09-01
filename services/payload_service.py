import json
import secrets
from datetime import datetime, timedelta, timezone
from json import JSONDecodeError
from typing import Any

from fastapi import Request, UploadFile

from core.config import Settings
from core.errors import (
    InvalidPayloadError,
    PayloadExtractionError,
    PayloadNotFoundError,
    PayloadTooLargeError,
)
from repositories.supabase_payload_repository import SupabasePayloadRepository
from repositories.supabase_storage_repository import SupabaseStorageRepository
from repositories.supabase_audit_repository import SupabaseAuditRepository
from core.security import Principal
from schemas.payload_schema import (
    CreatePayloadResponse,
    PayloadStatusFoundResponse,
    PayloadStatusNotFoundResponse,
    RetrievePayloadResponse,
)
from services.pdf_extractors import extract_payload_from_pdf_bytes
from services.payload_sanitizer import sanitize_payload


class PayloadService:
    def __init__(
        self,
        repository: SupabasePayloadRepository,
        settings: Settings,
        storage_repository: SupabaseStorageRepository | None = None,
        audit_repository: SupabaseAuditRepository | None = None,
    ) -> None:
        self._repository = repository
        self._storage = storage_repository or SupabaseStorageRepository(settings=settings)
        self._audit = audit_repository or SupabaseAuditRepository(settings=settings)
        self._settings = settings

    async def create_payload(
        self, request: Request, principal: Principal
    ) -> CreatePayloadResponse:
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

        return self._persist_payload(payload=payload, principal=principal, request_id=request.state.request_id)

    async def create_payload_from_pdf(
        self, upload: UploadFile, principal: Principal, request_id: str
    ) -> CreatePayloadResponse:
        filename = (upload.filename or "").lower()
        content_type = (upload.content_type or "").lower()
        if not (
            filename.endswith(".pdf")
            or content_type in {"application/pdf", "application/x-pdf", "binary/octet-stream", ""}
        ):
            raise InvalidPayloadError

        pdf_bytes = await upload.read()
        if not pdf_bytes:
            raise InvalidPayloadError

        if len(pdf_bytes) > self._settings.max_pdf_bytes:
            raise PayloadTooLargeError

        try:
            payload, report_type = extract_payload_from_pdf_bytes(pdf_bytes)
        except ValueError as exc:
            raise PayloadExtractionError(str(exc)) from exc

        payload_id = self._generate_payload_id()
        object_path = f"{payload_id}/{secrets.token_urlsafe(8)}.pdf"
        self._storage.upload_pdf(object_path, pdf_bytes)

        try:
            return self._persist_payload(
                payload=payload,
                principal=principal,
                request_id=request_id,
                payload_id=payload_id,
                pdf_path=object_path,
                report_type=report_type,
            )
        except Exception:
            self._delete_pdf_best_effort(object_path)
            raise

    def consume_payload(
        self, payload_id: str, principal: Principal, request_id: str
    ) -> RetrievePayloadResponse:
        row = self._repository.consume_payload(
            payload_id=payload_id,
            consumed_at=datetime.now(timezone.utc),
            organization_id=principal.organization_id,
        )
        if row is None:
            self._audit.record(
                action="payload.consume",
                outcome="failure",
                organization_id=principal.organization_id,
                credential_id=principal.credential_id,
                payload_id=payload_id,
                request_id=request_id,
            )
            raise PayloadNotFoundError

        response = self._build_retrieve_response(row)
        self._audit.record(
            action="payload.consume",
            outcome="success",
            organization_id=principal.organization_id,
            credential_id=principal.credential_id,
            payload_id=payload_id,
            request_id=request_id,
        )
        if response.pdf_url:
            self._audit.record(
                action="payload.pdf.access",
                outcome="success",
                organization_id=principal.organization_id,
                credential_id=principal.credential_id,
                payload_id=payload_id,
                request_id=request_id,
            )
        return response

    def consume_next_payload(
        self, principal: Principal, request_id: str
    ) -> RetrievePayloadResponse:
        row = self._repository.consume_next_payload(
            consumed_at=datetime.now(timezone.utc),
            organization_id=principal.organization_id,
        )
        if row is None:
            self._audit.record(
                action="payload.consume_next",
                outcome="failure",
                organization_id=principal.organization_id,
                credential_id=principal.credential_id,
                request_id=request_id,
            )
            raise PayloadNotFoundError

        response = self._build_retrieve_response(row)
        self._audit.record(
            action="payload.consume_next",
            outcome="success",
            organization_id=principal.organization_id,
            credential_id=principal.credential_id,
            payload_id=response.id,
            request_id=request_id,
        )
        if response.pdf_url:
            self._audit.record(
                action="payload.pdf.access",
                outcome="success",
                organization_id=principal.organization_id,
                credential_id=principal.credential_id,
                payload_id=response.id,
                request_id=request_id,
            )
        return response

    def get_payload_status(
        self, payload_id: str, principal: Principal, request_id: str
    ) -> PayloadStatusFoundResponse | PayloadStatusNotFoundResponse:
        row = self._repository.get_payload_status(payload_id, principal.organization_id)
        if row is None or row.get("consumed_at"):
            self._audit.record(
                action="payload.status",
                outcome="failure",
                organization_id=principal.organization_id,
                credential_id=principal.credential_id,
                payload_id=payload_id,
                request_id=request_id,
            )
            return PayloadStatusNotFoundResponse(id=payload_id)

        expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
        ttl_seconds = int((expires_at - datetime.now(timezone.utc)).total_seconds())
        if ttl_seconds <= 0:
            self._audit.record(
                action="payload.status",
                outcome="failure",
                organization_id=principal.organization_id,
                credential_id=principal.credential_id,
                payload_id=payload_id,
                request_id=request_id,
            )
            return PayloadStatusNotFoundResponse(id=payload_id)

        self._audit.record(
            action="payload.status",
            outcome="success",
            organization_id=principal.organization_id,
            credential_id=principal.credential_id,
            payload_id=payload_id,
            request_id=request_id,
        )
        return PayloadStatusFoundResponse(id=payload_id, ttl_seconds=ttl_seconds)

    def _persist_payload(
        self,
        payload: dict[str, Any],
        principal: Principal,
        request_id: str,
        payload_id: str | None = None,
        pdf_path: str | None = None,
        report_type: str | None = None,
    ) -> CreatePayloadResponse:
        payload = sanitize_payload(payload, self._settings)
        resolved_id = payload_id or self._generate_payload_id()
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(seconds=self._settings.payload_ttl_seconds)
        resolved_report_type = report_type or self._extract_report_type(payload)

        try:
            self._repository.insert_payload(
                payload_id=resolved_id,
                created_at=created_at,
                expires_at=expires_at,
                source=self._extract_source(payload),
                payload=payload,
                organization_id=principal.organization_id,
                credential_id=principal.credential_id,
                pdf_path=pdf_path,
                report_type=resolved_report_type,
            )
        except Exception:
            self._audit.record(
                action="payload.publish",
                outcome="failure",
                organization_id=principal.organization_id,
                credential_id=principal.credential_id,
                payload_id=resolved_id,
                request_id=request_id,
            )
            raise

        self._audit.record(
            action="payload.publish",
            outcome="success",
            organization_id=principal.organization_id,
            credential_id=principal.credential_id,
            payload_id=resolved_id,
            request_id=request_id,
        )

        return CreatePayloadResponse(
            id=resolved_id,
            expires_in_seconds=self._settings.payload_ttl_seconds,
            expires_in_minutes=self._settings.payload_ttl_seconds // 60,
        )

    def purge(self, request_id: str | None = None) -> dict[str, int]:
        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=self._settings.consumed_payload_grace_seconds
        )
        candidates = self._repository.find_cleanup_candidates(cutoff)
        deleted_payloads = 0
        deleted_pdfs = 0
        for candidate in candidates:
            pdf_path = candidate.get("pdf_path")
            if isinstance(pdf_path, str) and pdf_path:
                self._storage.delete_pdf(pdf_path)
                deleted_pdfs += 1
            if isinstance(candidate.get("id"), str):
                self._repository.delete_payload(candidate["id"])
                deleted_payloads += 1
                self._audit.record(
                    action="payload.delete",
                    outcome="success",
                    organization_id=candidate.get("organization_id"),
                    payload_id=candidate["id"],
                    request_id=request_id,
                )

        referenced = self._repository.list_referenced_pdf_paths()
        for pdf_path in self._storage.list_pdf_objects():
            if pdf_path not in referenced:
                self._storage.delete_pdf(pdf_path)
                deleted_pdfs += 1

        return {"deleted_payloads": deleted_payloads, "deleted_pdfs": deleted_pdfs}

    def _delete_pdf_best_effort(self, object_path: str) -> None:
        try:
            self._storage.delete_pdf(object_path)
        except Exception:
            return

    def _build_retrieve_response(self, row: dict[str, Any]) -> RetrievePayloadResponse:
        payload = row.get("payload")
        if not isinstance(payload, dict):
            payload = {}

        pdf_path = row.get("pdf_path")
        if not isinstance(pdf_path, str) or not pdf_path:
            pdf_path = None

        clean_payload = dict(payload)
        clean_payload.pop("pdf_storage_path", None)

        pdf_url = None
        if pdf_path:
            pdf_url = self._storage.create_signed_url(
                pdf_path,
                self._settings.pdf_signed_url_seconds,
            )

        return RetrievePayloadResponse(
            id=row["id"],
            payload=clean_payload,
            consumed=True,
            pdf_url=pdf_url,
        )

    @staticmethod
    def _generate_payload_id() -> str:
        return f"payload_{secrets.token_urlsafe(32)}"

    @staticmethod
    def _extract_source(payload: dict) -> str:
        source = payload.get("source")
        return source.strip() if isinstance(source, str) and source.strip() else "unknown"

    @staticmethod
    def _extract_report_type(payload: dict) -> str | None:
        report_type = payload.get("report_type")
        if isinstance(report_type, str) and report_type.strip():
            return report_type.strip().upper()
        return None
