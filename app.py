from fastapi import Depends, FastAPI, File, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from core.config import settings
from core.errors import (
    InvalidPayloadError,
    PayloadExtractionError,
    PayloadNotFoundError,
    PayloadStoreUnavailableError,
    PayloadTooLargeError,
)
from core.security import require_system_a, require_system_b
from repositories.supabase_payload_repository import SupabasePayloadRepository
from repositories.supabase_storage_repository import SupabaseStorageRepository
from schemas.payload_examples import (
    CVTUG_PAYLOAD_EXAMPLE,
    EQUILIBRIO_PAYLOAD_EXAMPLE,
    GENERIC_PAYLOAD_EXAMPLE,
    INDEX_INDEX_PAYLOAD_EXAMPLE,
)
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
        "API para transferencia temporaria de payloads JSON e PDF entre sistemas. "
        "O Sistema A publica com `POST /api/payloads` (JSON) ou "
        "`POST /api/payloads/pdf` (PDF CvTUG/equilibrio/Index-Index), o Sistema B consome "
        "uma unica vez com `GET /api/payloads/{id}` ou `GET /api/payloads/next`, "
        "e o Supabase controla expiracao, Storage do PDF e consumo unico."
    ),
    version="1.7.0",
)


def get_payload_service() -> PayloadService:
    repository = SupabasePayloadRepository(settings=settings)
    storage_repository = SupabaseStorageRepository(settings=settings)
    return PayloadService(
        repository=repository,
        settings=settings,
        storage_repository=storage_repository,
    )


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
    detail = str(exc).strip() if str(exc) else "Payload vazio ou invalido"
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": detail},
    )


@app.exception_handler(PayloadExtractionError)
async def payload_extraction_handler(
    request: Request, exc: PayloadExtractionError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc) or "Falha ao extrair dados do PDF"},
    )


@app.exception_handler(PayloadNotFoundError)
async def payload_not_found_handler(
    request: Request, exc: PayloadNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Payload nao encontrado, expirado ou ja consumido"},
    )


@app.exception_handler(PayloadStoreUnavailableError)
async def payload_store_unavailable_handler(
    request: Request, exc: PayloadStoreUnavailableError
) -> JSONResponse:
    detail = "Banco Supabase indisponivel ou nao configurado"
    if str(exc):
        detail = f"{detail}: {str(exc)}"

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": detail},
    )


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Verifica se a API esta respondendo",
)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="rehabeasy-transfer-api")


@app.post(
    "/api/payloads",
    response_model=CreatePayloadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["payloads"],
    summary="Publica um payload JSON temporario",
    description=(
        "Uso exclusivo do Sistema A. O corpo deve ser um JSON valido. "
        "A API aceita payload livre, mas recomenda o formato com "
        "`source`, `schema_version` e `records` para padronizar a integracao."
    ),
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "description": (
                            "Payload JSON livre. O formato recomendado usa "
                            "cabecalho do payload e um array `records`."
                        ),
                    },
                    "examples": {
                        "generic_payload": {
                            "summary": "Payload generico recomendado",
                            "value": GENERIC_PAYLOAD_EXAMPLE,
                        },
                        "cvtug_payload": {
                            "summary": "Payload completo do integrador CvTUG",
                            "value": CVTUG_PAYLOAD_EXAMPLE,
                        },
                        "equilibrio_payload": {
                            "summary": "Payload de avaliacao de equilibrio (posturografia VR)",
                            "value": EQUILIBRIO_PAYLOAD_EXAMPLE,
                        },
                        "indexindex_payload": {
                            "summary": "Payload Index-Index (coordenacao motora fina VR)",
                            "value": INDEX_INDEX_PAYLOAD_EXAMPLE,
                        },
                    },
                }
            },
        }
    },
)
async def create_payload(
    request: Request,
    _: None = Depends(require_system_a),
    service: PayloadService = Depends(get_payload_service),
) -> CreatePayloadResponse:
    return await service.create_payload(request)


@app.post(
    "/api/payloads/pdf",
    response_model=CreatePayloadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["payloads"],
    summary="Publica um PDF CvTUG, equilibrio ou Index-Index",
    description=(
        "Uso exclusivo do Sistema A. Envie `multipart/form-data` com o campo "
        "`file` contendo o PDF. A API extrai o JSON estruturado, guarda o PDF "
        "no Supabase Storage e disponibiliza o payload para consumo unico."
    ),
)
async def create_payload_from_pdf(
    file: UploadFile = File(
        ..., description="PDF do relatorio CvTUG, equilibrio ou Index-Index"
    ),
    _: None = Depends(require_system_a),
    service: PayloadService = Depends(get_payload_service),
) -> CreatePayloadResponse:
    return await service.create_payload_from_pdf(file)


@app.get(
    "/api/payloads/next",
    response_model=RetrievePayloadResponse,
    tags=["payloads"],
    summary="Consome o proximo payload pendente",
    description=(
        "Uso exclusivo do Sistema B. Retorna o payload pendente mais antigo "
        "que ainda nao expirou e ainda nao foi consumido. Quando houver PDF, "
        "inclui `pdf_url` assinada."
    ),
)
def consume_next_payload(
    _: None = Depends(require_system_b),
    service: PayloadService = Depends(get_payload_service),
) -> RetrievePayloadResponse:
    return service.consume_next_payload()


@app.get(
    "/api/payloads/{payload_id}",
    response_model=RetrievePayloadResponse,
    tags=["payloads"],
    summary="Consome um payload especifico pelo ID",
    description=(
        "Uso exclusivo do Sistema B. Se o payload existir e ainda estiver "
        "disponivel, ele e retornado e marcado como consumido. Quando houver "
        "PDF, inclui `pdf_url` assinada."
    ),
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
    summary="Consulta a disponibilidade de um payload",
    description=(
        "Uso exclusivo do Sistema B. Nao consome o payload; apenas informa "
        "se ele continua disponivel dentro do TTL."
    ),
)
def get_payload_status(
    payload_id: str,
    _: None = Depends(require_system_b),
    service: PayloadService = Depends(get_payload_service),
) -> PayloadStatusFoundResponse | PayloadStatusNotFoundResponse:
    return service.get_payload_status(payload_id)
