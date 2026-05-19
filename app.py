from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from core.config import settings
from core.errors import (
    InvalidPayloadError,
    PayloadNotFoundError,
    PayloadTooLargeError,
    RedisUnavailableError,
)
from core.security import require_system_a, require_system_b
from repositories.redis_repository import RedisPayloadRepository
from schemas.payload_schema import (
    CreatePayloadResponse,
    HealthResponse,
    PayloadStatusFoundResponse,
    PayloadStatusNotFoundResponse,
    RetrievePayloadResponse,
)
from services.payload_service import PayloadService


app = FastAPI(
    title="RehabEasy Transfer API",
    description=(
        "API intermediaria para transferencia de payloads entre sistemas "
        "e consumo unico pelo RehabEasy."
    ),
    version="1.1.0",
)


def get_payload_service() -> PayloadService:
    repository = RedisPayloadRepository.from_settings(settings)
    return PayloadService(repository=repository, settings=settings)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Payload vazio ou invalido"},
    )


@app.exception_handler(PayloadTooLargeError)
async def payload_too_large_handler(
    request: Request, exc: PayloadTooLargeError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        content={"detail": "Payload excede o tamanho maximo permitido"},
    )


@app.exception_handler(InvalidPayloadError)
async def invalid_payload_handler(
    request: Request, exc: InvalidPayloadError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Payload vazio ou invalido"},
    )


@app.exception_handler(PayloadNotFoundError)
async def payload_not_found_handler(
    request: Request, exc: PayloadNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Payload nao encontrado, expirado ou ja consumido"},
    )


@app.exception_handler(RedisUnavailableError)
async def redis_unavailable_handler(
    request: Request, exc: RedisUnavailableError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Redis indisponivel"},
    )


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="rehabeasy-transfer-api")


@app.post(
    "/api/payloads",
    response_model=CreatePayloadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["payloads"],
)
async def create_payload(
    request: Request,
    _: None = Depends(require_system_a),
    service: PayloadService = Depends(get_payload_service),
) -> CreatePayloadResponse:
    return await service.create_payload(request)


@app.get(
    "/api/payloads/{payload_id}",
    response_model=RetrievePayloadResponse,
    tags=["payloads"],
)
def consume_payload(
    payload_id: str,
    _: None = Depends(require_system_b),
    service: PayloadService = Depends(get_payload_service),
) -> RetrievePayloadResponse:
    return service.consume_payload(payload_id)


@app.get(
    "/api/payloads/{payload_id}/status",
    response_model=PayloadStatusFoundResponse | PayloadStatusNotFoundResponse,
    tags=["payloads"],
)
def get_payload_status(
    payload_id: str,
    _: None = Depends(require_system_b),
    service: PayloadService = Depends(get_payload_service),
) -> PayloadStatusFoundResponse | PayloadStatusNotFoundResponse:
    return service.get_payload_status(payload_id)
