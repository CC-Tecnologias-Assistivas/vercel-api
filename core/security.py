import re
import secrets
from dataclasses import dataclass

from fastapi import Header, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from core.config import settings
from core.errors import AuthenticationUnavailableError
from repositories.supabase_credential_repository import SupabaseCredentialRepository
from repositories.supabase_audit_repository import SupabaseAuditRepository


api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)
KEY_PATTERN = re.compile(r"^(?P<key_id>[A-Za-z0-9_-]{8,64})\.(?P<secret>[A-Za-z0-9_-]{32,})$")


@dataclass(frozen=True)
class Principal:
    credential_id: str
    organization_id: str
    role: str
    key_id: str


def _authenticate(provided_key: str | None, required_role: str, request_id: str | None) -> Principal:
    if not provided_key:
        _audit_auth_failure(request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credencial ausente ou invalida")

    match = KEY_PATTERN.fullmatch(provided_key.strip())
    if match is None:
        _audit_auth_failure(request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credencial ausente ou invalida")

    key_id = match.group("key_id")
    try:
        credential = SupabaseCredentialRepository(settings).authenticate(
            key_id, match.group("secret"), required_role
        )
    except AuthenticationUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servico de autenticacao indisponivel",
        )

    if not credential or not credential.get("organization_id") or not credential.get("credential_id"):
        _audit_auth_failure(request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credencial ausente ou invalida")

    SupabaseCredentialRepository(settings).touch_last_used(credential["credential_id"])
    return Principal(
        credential_id=credential["credential_id"],
        organization_id=credential["organization_id"],
        role=credential["role"],
        key_id=credential["key_id"],
    )


def require_system_a(request: Request, x_api_key: str | None = Security(api_key_header)) -> Principal:
    return _authenticate(x_api_key, "publisher", request.state.request_id)


def require_system_b(request: Request, x_api_key: str | None = Security(api_key_header)) -> Principal:
    return _authenticate(x_api_key, "consumer", request.state.request_id)


def require_maintenance_key(
    request: Request,
    x_maintenance_key: str | None = Header(default=None, alias="X-MAINTENANCE-KEY"),
    authorization: str | None = Header(default=None),
) -> None:
    maintenance_valid = bool(
        x_maintenance_key
        and settings.maintenance_key
        and secrets.compare_digest(x_maintenance_key, settings.maintenance_key)
    )
    cron_valid = bool(
        authorization
        and settings.cron_secret
        and secrets.compare_digest(authorization, f"Bearer {settings.cron_secret}")
    )
    if not (maintenance_valid or cron_valid):
        SupabaseAuditRepository(settings).record(
            action="maintenance.auth",
            outcome="failure",
            request_id=request.state.request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credencial de manutencao ausente ou invalida",
        )

    SupabaseAuditRepository(settings).record(
        action="maintenance.auth",
        outcome="success",
        request_id=request.state.request_id,
    )


def _audit_auth_failure(request_id: str | None) -> None:
    SupabaseAuditRepository(settings).record(
        action="auth.failure",
        outcome="failure",
        request_id=request_id,
    )
