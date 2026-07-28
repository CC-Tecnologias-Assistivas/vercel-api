from __future__ import annotations

from services.pdf_extractors import cvtug, equilibrio

REPORT_TYPE_CVTUG = "CVTUG"
REPORT_TYPE_EQUILIBRIO = "EQUILIBRIO"


def extract_payload_from_pdf_bytes(pdf_bytes: bytes) -> tuple[dict, str]:
    """Try CvTUG first, then equilibrio. Returns (payload, report_type)."""
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

    detail = " | ".join(errors) if errors else "formato nao reconhecido"
    raise ValueError(
        "Nao foi possivel extrair um relatorio CvTUG ou de equilibrio do PDF. "
        f"Detalhes: {detail}"
    )
