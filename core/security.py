import secrets

from fastapi import Header, HTTPException, status

from core.config import settings


def _validate_api_key(
    provided_key: str | None,
    expected_key: str,
    forbidden_key: str,
) -> None:
    if not provided_key or not expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key ausente ou invalida",
        )

    if not secrets.compare_digest(provided_key, expected_key):
        if forbidden_key and secrets.compare_digest(provided_key, forbidden_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sistema autenticado sem permissao para esta acao",
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key ausente ou invalida",
        )


def require_system_a(x_api_key: str | None = Header(default=None)) -> None:
    _validate_api_key(
        x_api_key,
        settings.system_a_api_key,
        settings.system_b_api_key,
    )


def require_system_b(x_api_key: str | None = Header(default=None)) -> None:
    _validate_api_key(
        x_api_key,
        settings.system_b_api_key,
        settings.system_a_api_key,
    )
