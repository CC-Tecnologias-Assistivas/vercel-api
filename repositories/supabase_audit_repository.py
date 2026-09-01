from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx

from core.config import Settings


class SupabaseAuditRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def record(
        self,
        *,
        action: str,
        outcome: str,
        organization_id: str | None = None,
        credential_id: str | None = None,
        payload_id: str | None = None,
        request_id: str | None = None,
    ) -> None:
        body: dict[str, Any] = {
            "action": action,
            "outcome": outcome,
            "occurred_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        for key, value in {
            "organization_id": organization_id,
            "credential_id": credential_id,
            "payload_id": payload_id,
            "request_id": request_id,
        }.items():
            if value:
                body[key] = value

        if not self._settings.supabase_url or not self._settings.supabase_service_role_key:
            return
        url = (
            f"{self._settings.supabase_url.rstrip('/')}/rest/v1/"
            f"{quote(self._settings.supabase_audit_table)}"
        )
        try:
            response = httpx.post(
                url,
                headers={
                    "apikey": self._settings.supabase_service_role_key,
                    "Authorization": f"Bearer {self._settings.supabase_service_role_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                json=body,
                timeout=10,
            )
            if response.status_code not in (200, 201, 204):
                return
        except httpx.HTTPError:
            return
