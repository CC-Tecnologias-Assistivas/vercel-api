from __future__ import annotations

from services.pdf_extractors import cvtug, equilibrio, indexindex

REPORT_TYPE_CVTUG = "CVTUG"
REPORT_TYPE_EQUILIBRIO = "EQUILIBRIO"
REPORT_TYPE_INDEX_INDEX = "INDEX_INDEX"


def extract_payload_from_pdf_bytes(pdf_bytes: bytes) -> tuple[dict, str]:
    """Try the supported clinical report extractors in order."""
    errors: list[str] = []

    try:
        payload = cvtug.build_payload_from_pdf_bytes(pdf_bytes)
        return payload, REPORT_TYPE_CVTUG
    except Exception as exc:  # noqa: BLE001 - collect extractor errors for the caller
        errors.append(f"CvTUG: {exc}")

    try:
        payload = equilibrio.build_payload_from_pdf_bytes(pdf_bytes)
        return payload, REPORT_TYPE_EQUILIBRIO
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Equilibrio: {exc}")

    try:
        payload = indexindex.build_payload_from_pdf_bytes(pdf_bytes)
        return payload, REPORT_TYPE_INDEX_INDEX
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Index-Index: {exc}")

    detail = " | ".join(errors) if errors else "formato nao reconhecido"
    raise ValueError(
        "Nao foi possivel extrair um relatorio CvTUG, de equilibrio ou Index-Index do PDF. "
        f"Detalhes: {detail}"
    )
