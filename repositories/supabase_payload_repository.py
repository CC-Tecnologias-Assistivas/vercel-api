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
        payload: dict[str, Any],
    ) -> None:
        response = self._request(
            "POST",
            "",
            json={
                "id": payload_id,
                "created_at": self._format_timestamp(created_at),
                "expires_at": self._format_timestamp(expires_at),
                "source": "sistema-a",
                "payload": payload,
            },
            headers={"Prefer": "return=minimal"},
        )
        if response.status_code not in (200, 201, 204):
            raise PayloadStoreUnavailableError(response.text)

    def consume_payload(self, payload_id: str, consumed_at: datetime) -> dict[str, Any] | None:
        response = self._request(
            "PATCH",
            (
                f"?id=eq.{quote(payload_id)}"
                "&consumed_at=is.null"
                f"&expires_at=gt.{quote(self._format_timestamp(datetime.now(timezone.utc)))}"
                "&select=id,payload"
            ),
            json={"consumed_at": self._format_timestamp(consumed_at)},
            headers={"Prefer": "return=representation"},
        )
        if response.status_code != 200:
            raise PayloadStoreUnavailableError(response.text)

        rows = response.json()
        return rows[0] if rows else None

    def consume_next_payload(self, consumed_at: datetime) -> dict[str, Any] | None:
        response = self._request(
            "GET",
            (
                "?consumed_at=is.null"
                f"&expires_at=gt.{quote(self._format_timestamp(datetime.now(timezone.utc)))}"
                "&select=id"
                "&order=created_at.asc"
                "&limit=5"
            ),
        )
        if response.status_code != 200:
            raise PayloadStoreUnavailableError(response.text)

        for row in response.json():
            consumed = self.consume_payload(row["id"], consumed_at)
            if consumed is not None:
                return consumed

        return None

    def get_payload_status(self, payload_id: str) -> dict[str, Any] | None:
        response = self._request(
            "GET",
            (
                f"?id=eq.{quote(payload_id)}"
                "&select=id,expires_at,consumed_at"
                "&limit=1"
            ),
        )
        if response.status_code != 200:
            raise PayloadStoreUnavailableError(response.text)

        rows = response.json()
        return rows[0] if rows else None

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
