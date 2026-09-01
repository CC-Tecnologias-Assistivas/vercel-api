from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from core.config import Settings
from core.errors import AuthenticationUnavailableError


class SupabaseCredentialRepository:
    """Reads credential metadata using the backend-only Supabase service role."""

    _hasher = PasswordHasher()

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def authenticate(self, key_id: str, secret: str, required_role: str) -> dict[str, Any] | None:
        if not self._settings.supabase_url or not self._settings.supabase_service_role_key:
            raise AuthenticationUnavailableError("Supabase nao configurado")

        response = self._request(
            "GET",
            f"?key_id=eq.{quote(key_id)}&revoked_at=is.null&select=id,organization_id,role,secret_hash,expires_at&limit=1",
        )
        if response.status_code != 200:
            raise AuthenticationUnavailableError("Nao foi possivel consultar credenciais")

        rows = response.json()
        if not rows:
            return None

        credential = rows[0]
        if credential.get("role") != required_role:
            return None

        expires_at = credential.get("expires_at")
        if expires_at:
            try:
                expired = datetime.fromisoformat(expires_at.replace("Z", "+00:00")) <= datetime.now(timezone.utc)
            except (AttributeError, TypeError, ValueError):
                return None
            if expired:
                return None

        organization_id = credential.get("organization_id")
        if not isinstance(organization_id, str) or not organization_id:
            return None
        if not self._organization_is_active(organization_id):
            return None

        stored_hash = credential.get("secret_hash")
        if not isinstance(stored_hash, str) or not stored_hash.startswith("$argon2id$"):
            return None

        try:
            self._hasher.verify(stored_hash, secret + self._settings.credential_hash_pepper)
        except (TypeError, ValueError):
            return None
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return None

        return {
            "credential_id": credential.get("id"),
            "organization_id": organization_id,
            "role": credential.get("role"),
            "key_id": key_id,
        }

    def _organization_is_active(self, organization_id: str) -> bool:
        response = self._request_organizations(
            "GET",
            f"?id=eq.{quote(organization_id)}&active=eq.true&select=id&limit=1",
        )
        if response.status_code != 200:
            raise AuthenticationUnavailableError("Nao foi possivel consultar organizacao")
        rows = response.json()
        return isinstance(rows, list) and bool(rows)

    def touch_last_used(self, credential_id: str) -> None:
        response = self._request(
            "PATCH",
            f"?id=eq.{quote(credential_id)}&revoked_at=is.null",
            json={"last_used_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")},
            headers={"Prefer": "return=minimal"},
        )
        if response.status_code not in (200, 204):
            # Usage metadata must never prevent an otherwise valid clinical transfer.
            return

    def _request(
        self,
        method: str,
        path_and_query: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        url = (
            f"{self._settings.supabase_url.rstrip('/')}/rest/v1/"
            f"{quote(self._settings.supabase_credentials_table)}{path_and_query}"
        )
        request_headers = {
            "apikey": self._settings.supabase_service_role_key,
            "Authorization": f"Bearer {self._settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }
        if headers:
            request_headers.update(headers)

        try:
            return httpx.request(method, url, headers=request_headers, json=json, timeout=10)
        except httpx.HTTPError as exc:
            raise AuthenticationUnavailableError from exc

    def _request_organizations(self, method: str, path_and_query: str) -> httpx.Response:
        url = (
            f"{self._settings.supabase_url.rstrip('/')}/rest/v1/"
            f"{quote(self._settings.supabase_organizations_table)}{path_and_query}"
        )
        request_headers = {
            "apikey": self._settings.supabase_service_role_key,
            "Authorization": f"Bearer {self._settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }
        try:
            return httpx.request(method, url, headers=request_headers, timeout=10)
        except httpx.HTTPError as exc:
            raise AuthenticationUnavailableError from exc
