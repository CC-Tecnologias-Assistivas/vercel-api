"""Create and revoke organization-scoped API credentials.

The generated secret is printed once. Store it in the target consumer/publisher
secret manager; it is never written to Supabase or to a repository.
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
from datetime import datetime, timezone
from urllib.parse import quote

import httpx
from argon2 import PasswordHasher


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices={"create", "revoke", "rotate"})
    parser.add_argument("--organization-id", help="ID existente da organizacao")
    parser.add_argument("--role", choices={"publisher", "consumer"})
    parser.add_argument("--name", default="integration", help="Nome operacional da credencial")
    parser.add_argument("--credential-id", help="ID da credencial a revogar")
    parser.add_argument("--expires-at", help="Data ISO 8601 opcional")
    args = parser.parse_args()

    base_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    pepper = os.getenv("CREDENTIAL_HASH_PEPPER", "")
    if not base_url or not service_key or len(pepper) < 32:
        parser.error("Defina SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY e CREDENTIAL_HASH_PEPPER (>= 32 caracteres)")

    if args.action in {"create", "rotate"}:
        if not args.organization_id or not args.role:
            parser.error("create/rotate exige --organization-id e --role")
        if args.action == "rotate" and not args.credential_id:
            parser.error("rotate exige --credential-id da credencial anterior")
        result = create_credential(base_url, service_key, pepper, args)
        if result != 0 or args.action != "rotate":
            return result
        return revoke_credential(base_url, service_key, args.credential_id)

    if not args.credential_id:
        parser.error("revoke exige --credential-id")
    return revoke_credential(base_url, service_key, args.credential_id)


def create_credential(base_url: str, service_key: str, pepper: str, args: argparse.Namespace) -> int:
    key_id = secrets.token_urlsafe(12)
    secret = secrets.token_urlsafe(32)
    body = {
        "id": secrets.token_urlsafe(16),
        "organization_id": args.organization_id,
        "key_id": key_id,
        "label": args.name,
        "role": args.role,
        "secret_hash": PasswordHasher().hash(secret + pepper),
    }
    if args.expires_at:
        body["expires_at"] = args.expires_at
    response = request(base_url, service_key, "POST", "/rest/v1/api_credentials", body)
    if response.status_code not in (200, 201, 204):
        print("Falha ao criar credencial.", file=sys.stderr)
        return 1
    record_audit(
        base_url,
        service_key,
        action="credential.create",
        organization_id=args.organization_id,
        credential_id=body["id"],
    )
    print(f"credential_id={body['id']}")
    print(f"organization_id={args.organization_id}")
    print(f"role={args.role}")
    print(f"X-API-KEY={key_id}.{secret}")
    return 0


def revoke_credential(base_url: str, service_key: str, credential_id: str) -> int:
    response = request(
        base_url,
        service_key,
        "PATCH",
        f"/rest/v1/api_credentials?id=eq.{quote(credential_id)}",
        {"revoked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")},
    )
    if response.status_code not in (200, 204):
        print("Falha ao revogar credencial.", file=sys.stderr)
        return 1
    record_audit(
        base_url,
        service_key,
        action="credential.revoke",
        credential_id=credential_id,
    )
    print("Credencial revogada.")
    return 0


def record_audit(
    base_url: str,
    service_key: str,
    *,
    action: str,
    organization_id: str | None = None,
    credential_id: str | None = None,
) -> None:
    body = {
        "action": action,
        "outcome": "success",
        "occurred_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if organization_id:
        body["organization_id"] = organization_id
    if credential_id:
        body["credential_id"] = credential_id
    request(base_url, service_key, "POST", "/rest/v1/audit_events", body)


def request(base_url: str, service_key: str, method: str, path: str, body: dict) -> httpx.Response:
    try:
        return httpx.request(
            method,
            f"{base_url}{path}",
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json=body,
            timeout=15,
        )
    except httpx.HTTPError as exc:
        print(f"Falha de comunicacao: {type(exc).__name__}", file=sys.stderr)
        return httpx.Response(503)


if __name__ == "__main__":
    raise SystemExit(main())
