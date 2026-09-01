from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from core.config import Settings
from core.errors import PayloadStoreUnavailableError


class SupabaseStorageRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._bucket_ready = False

    def upload_pdf(self, object_path: str, pdf_bytes: bytes) -> str:
        self._ensure_bucket()
        response = self._request(
            "POST",
            f"/storage/v1/object/{quote(self._settings.supabase_pdf_bucket)}/{quote(object_path, safe='/')}",
            content=pdf_bytes,
            headers={
                "Content-Type": "application/pdf",
                "x-upsert": "true",
            },
        )
        if response.status_code not in (200, 201):
            raise PayloadStoreUnavailableError(
                f"Falha ao enviar PDF ao Storage: {response.text}"
            )
        return object_path

    def create_signed_url(self, object_path: str, expires_in_seconds: int) -> str | None:
        if not object_path:
            return None

        self._ensure_bucket()
        response = self._request(
            "POST",
            (
                f"/storage/v1/object/sign/"
                f"{quote(self._settings.supabase_pdf_bucket)}/"
                f"{quote(object_path, safe='/')}"
            ),
            json={"expiresIn": max(expires_in_seconds, 60)},
        )
        if response.status_code not in (200, 201):
            raise PayloadStoreUnavailableError(
                f"Falha ao assinar URL do PDF: {response.text}"
            )

        payload: dict[str, Any] = response.json()
        signed_path = payload.get("signedURL") or payload.get("signedUrl")
        if not isinstance(signed_path, str) or not signed_path:
            return None

        if signed_path.startswith("http://") or signed_path.startswith("https://"):
            return signed_path

        base = self._settings.supabase_url.rstrip("/")
        path = signed_path if signed_path.startswith("/") else f"/{signed_path}"
        if path.startswith("/storage/v1/"):
            return f"{base}{path}"
        return f"{base}/storage/v1{path}"

    def delete_pdf(self, object_path: str) -> None:
        if not object_path:
            return
        response = self._request(
            "DELETE",
            f"/storage/v1/object/{quote(self._settings.supabase_pdf_bucket)}/{quote(object_path, safe='/')}",
        )
        if response.status_code not in (200, 204, 404):
            raise PayloadStoreUnavailableError(
                f"Falha ao remover PDF do Storage: {response.text}"
            )

    def list_pdf_objects(self) -> list[str]:
        self._ensure_bucket()
        response = self._request(
            "POST",
            f"/storage/v1/object/list/{quote(self._settings.supabase_pdf_bucket)}",
            json={"prefix": "", "limit": 1000, "offset": 0, "sortBy": {"column": "name", "order": "asc"}},
        )
        if response.status_code != 200:
            raise PayloadStoreUnavailableError(
                f"Falha ao listar PDFs do Storage: {response.text}"
            )
        return self._extract_pdf_paths(response.json(), prefix="")

    def _extract_pdf_paths(self, entries: Any, prefix: str) -> list[str]:
        paths: list[str] = []
        if not isinstance(entries, list):
            return paths
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
                continue
            name = entry["name"]
            path = f"{prefix}{name}"
            if entry.get("id") is not None and name.lower().endswith(".pdf"):
                paths.append(path)
            elif entry.get("id") is None:
                nested = self._request(
                    "POST",
                    f"/storage/v1/object/list/{quote(self._settings.supabase_pdf_bucket)}",
                    json={"prefix": f"{path}/", "limit": 1000, "offset": 0, "sortBy": {"column": "name", "order": "asc"}},
                )
                if nested.status_code == 200:
                    paths.extend(self._extract_pdf_paths(nested.json(), f"{path}/"))
        return paths

    def _ensure_bucket(self) -> None:
        if self._bucket_ready:
            return

        list_response = self._request("GET", "/storage/v1/bucket")
        if list_response.status_code == 200:
            buckets = list_response.json()
            if isinstance(buckets, list):
                for item in buckets:
                    if not isinstance(item, dict) or item.get("id") != self._settings.supabase_pdf_bucket:
                        continue
                    if item.get("public") is not False:
                        raise PayloadStoreUnavailableError("O bucket de PDFs precisa ser privado")
                    self._bucket_ready = True
                    return

        create_response = self._request(
            "POST",
            "/storage/v1/bucket",
            json={
                "id": self._settings.supabase_pdf_bucket,
                "name": self._settings.supabase_pdf_bucket,
                "public": False,
                "file_size_limit": self._settings.max_pdf_bytes,
                "allowed_mime_types": ["application/pdf"],
            },
        )
        if create_response.status_code not in (200, 201):
            # Bucket may already exist from a race; verify before failing hard.
            verify = self._request("GET", "/storage/v1/bucket")
            if verify.status_code == 200:
                buckets = verify.json()
                if isinstance(buckets, list) and any(
                    isinstance(item, dict)
                    and item.get("id") == self._settings.supabase_pdf_bucket
                    for item in buckets
                ):
                    self._bucket_ready = True
                    return
            raise PayloadStoreUnavailableError(
                f"Falha ao preparar bucket de PDFs: {create_response.text}"
            )

        self._bucket_ready = True

    def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        if not self._settings.supabase_url or not self._settings.supabase_service_role_key:
            raise PayloadStoreUnavailableError("Supabase nao configurado")

        url = f"{self._settings.supabase_url.rstrip('/')}{path}"
        request_headers = {
            "apikey": self._settings.supabase_service_role_key,
            "Authorization": f"Bearer {self._settings.supabase_service_role_key}",
        }
        if headers:
            request_headers.update(headers)

        try:
            return httpx.request(
                method,
                url,
                headers=request_headers,
                json=json,
                content=content,
                timeout=30,
            )
        except httpx.HTTPError as exc:
            raise PayloadStoreUnavailableError from exc
