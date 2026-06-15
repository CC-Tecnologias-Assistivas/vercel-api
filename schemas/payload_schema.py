from typing import Any

from pydantic import BaseModel, Field

from schemas.payload_examples import (
    CVTUG_PAYLOAD_EXAMPLE,
    EQUILIBRIO_PAYLOAD_EXAMPLE,
    GENERIC_PAYLOAD_EXAMPLE,
)


class CreatePayloadResponse(BaseModel):
    id: str = Field(description="Identificador unico gerado pela API.")
    expires_in_seconds: int = Field(description="TTL do payload em segundos.")
    expires_in_minutes: int = Field(description="TTL do payload em minutos.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "payload_W7SQFp1kgG9QiM1OCf-Nw8OfxZJ7lfljIDV5itKf4d4",
                "expires_in_seconds": 1800,
                "expires_in_minutes": 30,
            }
        }
    }


class RetrievePayloadResponse(BaseModel):
    id: str = Field(description="Identificador do payload consumido.")
    payload: dict[str, Any] = Field(
        description="Conteudo bruto do payload enviado pelo sistema de origem."
    )
    consumed: bool = Field(
        default=True, description="Sempre true quando a leitura for bem-sucedida."
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "payload_exemplo_generico",
                    "payload": GENERIC_PAYLOAD_EXAMPLE,
                    "consumed": True,
                },
                {
                    "id": "payload_exemplo_cvtug",
                    "payload": CVTUG_PAYLOAD_EXAMPLE,
                    "consumed": True,
                },
                {
                    "id": "payload_exemplo_equilibrio",
                    "payload": EQUILIBRIO_PAYLOAD_EXAMPLE,
                    "consumed": True,
                },
            ]
        }
    }


class PayloadStatusFoundResponse(BaseModel):
    id: str = Field(description="Identificador do payload consultado.")
    exists: bool = Field(
        default=True, description="Indica que o payload ainda esta disponivel."
    )
    ttl_seconds: int = Field(description="Tempo restante ate expirar.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "payload_W7SQFp1kgG9QiM1OCf-Nw8OfxZJ7lfljIDV5itKf4d4",
                "exists": True,
                "ttl_seconds": 1724,
            }
        }
    }


class PayloadStatusNotFoundResponse(BaseModel):
    id: str = Field(description="Identificador do payload consultado.")
    exists: bool = Field(
        default=False, description="Indica que o payload nao esta mais disponivel."
    )
    reason: str = Field(
        default="expired_or_consumed_or_not_found",
        description="Motivo padrao para indisponibilidade do payload.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "payload_W7SQFp1kgG9QiM1OCf-Nw8OfxZJ7lfljIDV5itKf4d4",
                "exists": False,
                "reason": "expired_or_consumed_or_not_found",
            }
        }
    }


class HealthResponse(BaseModel):
    status: str = Field(description="Status basico da API.")
    service: str = Field(description="Nome logico do servico.")

    model_config = {
        "json_schema_extra": {
            "example": {"status": "ok", "service": "rehabeasy-transfer-api"}
        }
    }
