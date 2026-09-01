from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx

from core.config import Settings
from core.errors import PayloadStoreUnavailableError


class SupabasePayloadRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def insert_payload(
        self,
        payload_id: str,
        created_at: datetime,
        expires_at: datetime,
        source: str,
        payload: dict[str, Any],
        organization_id: str,
        credential_id: str,
        pdf_path: str | None = None,
        report_type: str | None = None,
    ) -> None:
        body: dict[str, Any] = {
            "id": payload_id,
            "created_at": self._format_timestamp(created_at),
            "expires_at": self._format_timestamp(expires_at),
            "source": source,
            "payload": payload,
            "organization_id": organization_id,
            "ingest_credential_id": credential_id,
        }
        if pdf_path is not None:
            body["pdf_path"] = pdf_path
        if report_type is not None:
            body["report_type"] = report_type

        response = self._request(
            "POST",
            "",
            json=body,
            headers={"Prefer": "return=minimal"},
        )
        if response.status_code in (200, 201, 204):
            return

        raise PayloadStoreUnavailableError(response.text)

    def consume_payload(
        self,
        payload_id: str,
        consumed_at: datetime,
        organization_id: str,
    ) -> dict[str, Any] | None:
        row = self._consume_with_select(
            payload_id=payload_id,
            consumed_at=consumed_at,
            organization_id=organization_id,
            select="id,payload,pdf_path,report_type",
        )
        return row

    def _consume_with_select(
        self,
        payload_id: str,
        consumed_at: datetime,
        organization_id: str,
        select: str,
    ) -> dict[str, Any] | None:
        response = self._request(
            "PATCH",
            (
                f"?id=eq.{quote(payload_id)}"
                f"&organization_id=eq.{quote(organization_id)}"
                "&consumed_at=is.null"
                f"&expires_at=gt.{quote(self._format_timestamp(datetime.now(timezone.utc)))}"
                f"&select={select}"
            ),
            json={"consumed_at": self._format_timestamp(consumed_at)},
            headers={"Prefer": "return=representation"},
        )
        if response.status_code != 200:
            raise PayloadStoreUnavailableError(response.text)

        rows = response.json()
        return rows[0] if rows else None

    def consume_next_payload(
        self, consumed_at: datetime, organization_id: str
    ) -> dict[str, Any] | None:
        response = self._request(
            "GET",
            (
                "?consumed_at=is.null"
                f"&organization_id=eq.{quote(organization_id)}"
                f"&expires_at=gt.{quote(self._format_timestamp(datetime.now(timezone.utc)))}"
                "&select=id"
                "&order=created_at.asc"
                "&limit=5"
            ),
        )
        if response.status_code != 200:
            raise PayloadStoreUnavailableError(response.text)

        for row in response.json():
            consumed = self.consume_payload(row["id"], consumed_at, organization_id)
            if consumed is not None:
                return consumed

        return None

    def get_payload_status(self, payload_id: str, organization_id: str) -> dict[str, Any] | None:
        response = self._request(
            "GET",
            (
                f"?id=eq.{quote(payload_id)}"
                f"&organization_id=eq.{quote(organization_id)}"
                "&select=id,expires_at,consumed_at"
                "&limit=1"
            ),
        )
        if response.status_code != 200:
            raise PayloadStoreUnavailableError(response.text)

        rows = response.json()
        return rows[0] if rows else None

    def find_cleanup_candidates(self, cutoff: datetime) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        expired_before = self._format_timestamp(datetime.now(timezone.utc))
        for query in (
            f"?expires_at=lt.{quote(expired_before)}&select=id,pdf_path,organization_id",
            f"?consumed_at=lt.{quote(self._format_timestamp(cutoff))}&select=id,pdf_path,organization_id",
        ):
            response = self._request("GET", query)
            if response.status_code != 200:
                raise PayloadStoreUnavailableError(response.text)
            candidates.extend(row for row in response.json() if isinstance(row, dict))
        unique: dict[str, dict[str, Any]] = {
            row["id"]: row for row in candidates if isinstance(row.get("id"), str)
        }
        return list(unique.values())

    def delete_payload(self, payload_id: str) -> bool:
        response = self._request(
            "DELETE",
            f"?id=eq.{quote(payload_id)}",
            headers={"Prefer": "return=minimal"},
        )
        if response.status_code not in (200, 204):
            raise PayloadStoreUnavailableError(response.text)
        return True

    def list_referenced_pdf_paths(self) -> set[str]:
        response = self._request("GET", "?pdf_path=not.is.null&select=pdf_path")
        if response.status_code != 200:
            raise PayloadStoreUnavailableError(response.text)
        return {
            row["pdf_path"]
            for row in response.json()
            if isinstance(row, dict) and isinstance(row.get("pdf_path"), str)
        }

    def _request(
        self,
        method: str,
        path_and_query: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        if not self._settings.supabase_url or not self._settings.supabase_service_role_key:
            raise PayloadStoreUnavailableError("Supabase nao configurado")

        url = (
            f"{self._settings.supabase_url.rstrip('/')}/rest/v1/"
            f"{quote(self._settings.supabase_payloads_table)}{path_and_query}"
        )
        request_headers = {
            "apikey": self._settings.supabase_service_role_key,
            "Authorization": f"Bearer {self._settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }
        if headers:
            request_headers.update(headers)

        try:
            return httpx.request(
                method,
                url,
                headers=request_headers,
                json=json,
                timeout=15,
            )
        except httpx.HTTPError as exc:
            raise PayloadStoreUnavailableError from exc

    @staticmethod
    def _format_timestamp(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
