import re
import unicodedata
from datetime import datetime
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


REPORT_MARKERS = (
    "INDEX-INDEX",
    "DISTÂNCIA ENTRE AS PONTAS",
    "DISTANCIA ENTRE AS PONTAS",
)
ASYMMETRY_ALERT_THRESHOLD = 3.0


def build_payload_from_pdf(pdf_path: Path | str) -> dict:
    return build_payload_from_pdf_bytes(Path(pdf_path).read_bytes())


def build_payload_from_pdf_bytes(pdf_bytes: bytes) -> dict:
    reader = PdfReader(BytesIO(pdf_bytes))
    raw_text = "\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()
    return build_payload_from_text(raw_text)


def build_payload_from_text(raw_text: str) -> dict:
    if not raw_text.strip():
        raise ValueError("Nao foi possivel extrair texto do PDF.")

    normalized_text = normalize_spaces(raw_text)
    if not any(marker in normalized_text.upper() for marker in REPORT_MARKERS):
        raise ValueError("PDF nao parece ser um relatorio Index-Index.")

    patient_name = capture(normalized_text, r"Paciente:\s*(.+?)\s+Sexo:")
    sex = capture(normalized_text, r"Sexo:\s*(.+?)\s+Idade:")
    age_years = int(capture(normalized_text, r"Idade:\s*(\d+)"))
    report_datetime_text = capture(
        normalized_text, r"Data:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})"
    )
    performed_at = parse_br_datetime(report_datetime_text)
    evaluator = capture(normalized_text, r"Avaliador:\s*(.+?)\s+ID exame:")
    exam_id = capture(normalized_text, r"ID exame:\s*(\S+)")

    closing_criterion = capture(
        normalized_text,
        r"Crit[eé]rio de encerramento:\s*(.+?)\s+Dist[aâ]ncia entre as pontas ao final:",
    )
    final_distance = capture_float(
        normalized_text,
        r"Dist[aâ]ncia entre as pontas ao final:\s*([\d.,]+)\s*mm",
    )
    movement_duration = capture_float(
        normalized_text,
        r"Dura[cç][aã]o do movimento avaliado:\s*([\d.,]+)\s*s",
    )
    guide_line_length = capture_float(
        normalized_text,
        r"Comprimento da reta[- ]guia:\s*([\d.,]+)\s*mm",
    )
    left_oscillation = capture_float(
        normalized_text,
        r"Oscila[cç][aã]o\s*[—-]\s*m[aã]o esquerda \(DP\):\s*([\d.,]+)\s*mm",
    )
    right_oscillation = capture_float(
        normalized_text,
        r"Oscila[cç][aã]o\s*[—-]\s*m[aã]o direita \(DP\):\s*([\d.,]+)\s*mm",
    )
    overall_oscillation = capture_float(
        normalized_text,
        r"Oscila[cç][aã]o\s*[—-]\s*geral \(DP\):\s*([\d.,]+)\s*mm",
    )
    touch_threshold = capture_float(
        normalized_text, r"Limiar de toque\s*\(([\d.,]+)\s*mm\)"
    )

    protocol_description = extract_protocol_description(raw_text)
    interpretation = extract_section(
        raw_text, "Interpretação", "Observação metodológica:", "Referências"
    )
    methodology = extract_section(raw_text, "Observação metodológica:", "Referências")

    touch_achieved = final_distance <= touch_threshold
    asymmetry_ratio = round(right_oscillation / left_oscillation, 2) if left_oscillation else None
    dominant_side = "right" if right_oscillation >= left_oscillation else "left"
    asymmetry_status = (
        "ALERTA"
        if asymmetry_ratio is not None and asymmetry_ratio >= ASYMMETRY_ALERT_THRESHOLD
        else "OK"
    )
    patient_name_ascii = to_ascii(patient_name)
    dominant_side_label = "direita" if dominant_side == "right" else "esquerda"
    touch_label = "Toque dentro do limiar" if touch_achieved else "Toque fora do limiar"
    content = f"{touch_label}; assimetria com maior oscilacao na mao {dominant_side_label}."

    record = {
        "id": f"indexindex-{exam_id}-{performed_at.strftime('%Y%m%dT%H%M%S')}",
        "title": (
            f"Index-Index - {patient_name_ascii} - "
            f"{performed_at.strftime('%d/%m/%Y %H:%M')}"
        ),
        "sender": "Index-Index",
        "recipient": "RehabEasy",
        "created_at": performed_at.isoformat(),
        "summary": (
            f"Distancia final {final_distance:.1f} mm (limiar {touch_threshold:.1f} mm); "
            f"duracao {movement_duration:.2f} s; oscilacao E {left_oscillation:.1f} / "
            f"D {right_oscillation:.1f} / geral {overall_oscillation:.1f} mm."
        ),
        "content": content,
        "tags": ["index-index", "coordenacao-motora-fina", "vr", "dedos-indicadores"],
        "patient": {
            "name": patient_name_ascii,
            "age_years": age_years,
            "sex": to_ascii(sex),
            "external_id": exam_id,
        },
        "assessment": {
            "performed_at": performed_at.isoformat(),
            "exam_id": exam_id,
            "test_type": "INDEX_INDEX",
            "protocol": {
                "description": protocol_description,
                "closing_criterion": closing_criterion,
                "touch_threshold_mm": touch_threshold,
                "guide_line_length_mm": guide_line_length,
            },
            "metrics": {
                "final_fingertip_distance_mm": final_distance,
                "movement_duration_seconds": movement_duration,
                "guide_line_length_mm": guide_line_length,
                "left_hand_oscillation_sd_mm": left_oscillation,
                "right_hand_oscillation_sd_mm": right_oscillation,
                "overall_oscillation_sd_mm": overall_oscillation,
                "touch_threshold_mm": touch_threshold,
            },
            "derived_metrics": {
                "touch_achieved": touch_achieved,
                "asymmetry_ratio": asymmetry_ratio,
                "dominant_oscillation_side": dominant_side,
                "final_fingertip_distance_mm": final_distance,
                "overall_oscillation_sd_mm": overall_oscillation,
                "left_hand_oscillation_sd_mm": left_oscillation,
                "right_hand_oscillation_sd_mm": right_oscillation,
                "movement_duration_seconds": movement_duration,
            },
            "automated_flags": {
                "touch_within_threshold": touch_achieved,
                "hand_asymmetry": {
                    "status": asymmetry_status,
                    "ratio": asymmetry_ratio,
                    "threshold": ASYMMETRY_ALERT_THRESHOLD,
                    "dominant_side": dominant_side,
                },
            },
            "interpretation": interpretation,
            "methodology_notes": [methodology] if methodology else [],
            "evaluator": None if evaluator == "—" else to_ascii(evaluator),
        },
    }

    return {
        "source": "index-index",
        "schema_version": "1.0",
        "report_type": "INDEX_INDEX",
        "records": [record],
    }


def extract_protocol_description(raw_text: str) -> str:
    for line in raw_text.splitlines():
        cleaned = " ".join(line.split())
        if cleaned.lower().startswith("coordenação motora fina"):
            cleaned = re.sub(r"\s*[—-]\s*", " - ", cleaned, count=1)
            return to_ascii(cleaned)
    return "Coordenacao motora fina - aproximacao das pontas dos dedos indicadores (VR)"


def extract_section(raw_text: str, heading: str, *end_markers: str) -> str:
    normalized_lines = [" ".join(line.split()) for line in raw_text.splitlines()]
    start = next(
        (
            index
            for index, line in enumerate(normalized_lines)
            if line.lower().startswith(heading.lower())
        ),
        None,
    )
    if start is None:
        return ""

    collected: list[str] = []
    for line in normalized_lines[start:]:
        if collected and any(line.lower().startswith(marker.lower()) for marker in end_markers):
            break
        if not line:
            continue
        if line.lower().startswith(heading.lower()):
            remainder = line[len(heading) :].strip()
            if remainder:
                collected.append(remainder)
            continue
        collected.append(line)
    value = to_ascii(" ".join(collected).strip())
    return value[:1].upper() + value[1:] if value else ""


def normalize_spaces(value: str) -> str:
    return " ".join(value.split())


def capture(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        raise ValueError(f"Padrao nao encontrado: {pattern}")
    return match.group(1).strip()


def capture_float(text: str, pattern: str) -> float:
    return parse_float(capture(text, pattern))


def parse_float(value: str) -> float:
    if value.count(",") and value.count(".") and value.find(".") < value.find(","):
        normalized = value.replace(".", "").replace(",", ".")
    else:
        normalized = value.replace(",", ".")
    return float(normalized)


def parse_br_datetime(value: str) -> datetime:
    parsed = datetime.strptime(value.strip(), "%d/%m/%Y %H:%M")
    return parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)


def to_ascii(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return normalized.encode("ascii", "ignore").decode("ascii")
