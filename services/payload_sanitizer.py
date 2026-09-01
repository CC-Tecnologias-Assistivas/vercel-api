from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from core.config import Settings
from core.errors import InvalidPayloadError


_SCHEMA_FILES = {
    "GENERIC": "recommended_payload_schema.json",
    "CVTUG": "cvtug_payload_schema.json",
    "EQUILIBRIO": "equilibrio_payload_schema.json",
    "INDEX_INDEX": "indexindex_payload_schema.json",
}

def sanitize_payload(payload: dict[str, Any], settings: Settings) -> dict[str, Any]:
    """Validate the supported contract and return an allow-listed payload.

    Unknown keys are deliberately discarded before persistence. The source external
    patient identifier is replaced by a deterministic HMAC pseudonym while retaining
    the existing `external_id` wire field for desktop compatibility.
    """
    if not isinstance(payload, dict) or not payload:
        raise InvalidPayloadError("Payload vazio ou invalido")

    report_type = _resolve_report_type(payload)
    if report_type is None:
        sanitized = _sanitize_generic(payload)
    else:
        schema = _load_schema(report_type)
        errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(payload), key=lambda error: list(error.path))
        if errors:
            raise InvalidPayloadError("Payload nao atende ao contrato do relatorio")
        sanitized = _prune_by_schema(payload, schema)

    _pseudonymize_patient_ids(sanitized, settings.patient_pseudonymization_key)
    return sanitized


def _resolve_report_type(payload: dict[str, Any]) -> str | None:
    source = str(payload.get("source", "")).strip().lower()
    report_type = str(payload.get("report_type", "")).strip().upper()
    if source == "cvtug" or report_type in {"TUG", "CVTUG"}:
        return "CVTUG"
    if source in {"posturografia-vr", "equilibrio"} or report_type == "EQUILIBRIO":
        return "EQUILIBRIO"
    if source == "index-index" or report_type == "INDEX_INDEX":
        return "INDEX_INDEX"
    return None


def _load_schema(report_type: str) -> dict[str, Any]:
    schema_path = Path(__file__).resolve().parents[1] / "docs" / _SCHEMA_FILES[report_type]
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidPayloadError("Contrato de payload indisponivel") from exc


def _sanitize_generic(payload: dict[str, Any]) -> dict[str, Any]:
    schema = _load_schema("GENERIC")
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(payload),
        key=lambda error: list(error.path),
    )
    if errors:
        raise InvalidPayloadError("Payload nao atende ao contrato generico")
    return _prune_by_schema(payload, schema)


def _prune_by_schema(value: Any, schema: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties")
        result: dict[str, Any] = {}
        for key, item in value.items():
            if key in properties:
                result[key] = _prune_by_schema(item, properties[key])
            elif isinstance(additional, dict):
                result[key] = _prune_by_schema(item, additional)
        return result
    if isinstance(value, list):
        item_schema = schema.get("items", {})
        return [_prune_by_schema(item, item_schema) for item in value]
    return value


def _pseudonymize_patient_ids(payload: dict[str, Any], key: str) -> None:
    if not key:
        raise InvalidPayloadError("Pseudonimizacao nao configurada")
    for record in payload.get("records", []):
        if not isinstance(record, dict):
            continue
        patient = record.get("patient")
        if not isinstance(patient, dict):
            continue
        external_id = patient.get("external_id")
        if isinstance(external_id, str) and external_id:
            digest = hmac.new(
                key.encode("utf-8"), external_id.encode("utf-8"), hashlib.sha256
            ).hexdigest()
            patient["external_id"] = digest[:32]
