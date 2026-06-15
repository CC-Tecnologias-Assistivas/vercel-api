import argparse
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader


INDEX_SPECS = [
    (
        "spl",
        "Comprimento de trajetoria (SPL)",
        r"Comprimento de trajet[oó]ria \(SPL\)\s*([\d.,]+)\s*mm",
        "mm",
        r"Comprimento de trajet[oó]ria \(SPL\)\s*[\d.,]+\s*mm\s*([\d.,]+)\s*±\s*([\d.,]+)",
    ),
    (
        "confidence_ellipse_95_area",
        "Area da elipse de confianca 95%",
        r"[ÁA]rea da elipse de confian[cç]a 95%\s*([\d.,]+)\s*mm",
        "mm2",
        r"[ÁA]rea da elipse de confian[cç]a 95%\s*[\d.,]+\s*mm²?\s*([\d.,]+)\s*±\s*([\d.,]+)",
    ),
    (
        "mean_oscillation_velocity",
        "Velocidade media de oscilacao",
        r"Velocidade m[eé]dia de oscila[cç][aã]o\s*([\d.,]+)\s*mm/s",
        "mm/s",
        r"Velocidade m[eé]dia de oscila[cç][aã]o\s*[\d.,]+\s*mm/s\s*([\d.,]+)\s*±\s*([\d.,]+)",
    ),
    (
        "mdist",
        "Deslocamento radial medio (MDIST)",
        r"Deslocamento radial m[eé]dio \(MDIST\)\s*([\d.,]+)",
        None,
        None,
    ),
    (
        "rdist",
        "RMS radial (RDIST)",
        r"RMS radial \(RDIST\)\s*([\d.,]+)",
        None,
        None,
    ),
    (
        "rms_ap",
        "RMS antero-posterior (AP)",
        r"RMS [âa]ntero-posterior \(AP\)\s*([\d.,]+)\s*mm",
        "mm",
        None,
    ),
    (
        "rms_ml",
        "RMS medio-lateral (ML)",
        r"RMS m[eé]dio-lateral \(ML\)\s*([\d.,]+)\s*mm",
        "mm",
        None,
    ),
    (
        "amplitude_ap",
        "Amplitude AP (pico-a-pico)",
        r"Amplitude AP \(pico-a-pico\)\s*([\d.,]+)\s*mm",
        "mm",
        None,
    ),
    (
        "amplitude_ml",
        "Amplitude ML (pico-a-pico)",
        r"Amplitude ML \(pico-a-pico\)\s*([\d.,]+)\s*mm",
        "mm",
        None,
    ),
    (
        "ap_ml_ratio",
        "Razao direcional AP/ML",
        r"Raz[aã]o direcional AP/ML\s*([\d.,]+)",
        None,
        None,
    ),
    (
        "mean_frequency",
        "Frequencia media",
        r"Frequ[eê]ncia m[eé]dia\s*([\d.,]+)\s*Hz",
        "Hz",
        None,
    ),
    (
        "vertical_head_rms",
        "Oscilacao vertical da cabeca (RMS)",
        r"Oscila[cç][aã]o vertical da cabe[cç]a \(RMS\)\s*([\d.,]+)\s*mm",
        "mm",
        None,
    ),
    (
        "angular_pitch",
        "Oscilacao angular — inclinacao (pitch)",
        r"Oscila[cç][aã]o angular [—-] inclina[cç][aã]o \(pitch\)\s*([\d.,]+)\s*°",
        "deg",
        None,
    ),
    (
        "angular_roll",
        "Oscilacao angular — lateral (roll)",
        r"Oscila[cç][aã]o angular [—-] lateral \(roll\)\s*([\d.,]+)\s*°",
        "deg",
        None,
    ),
    (
        "angular_yaw",
        "Oscilacao angular — rotacao (yaw)",
        r"Oscila[cç][aã]o angular [—-] rota[cç][aã]o \(yaw\)\s*([\d.,]+)\s*°",
        "deg",
        None,
    ),
]

ROMBERG_SPECS = [
    (
        "area",
        "Quociente de Romberg — area (OF/OA)",
        r"Quociente de Romberg [—-] [áa]rea \(OF/OA\)\s*([\d.,]+)",
    ),
    (
        "trajectory",
        "Quociente de Romberg — trajetoria (OF/OA)",
        r"Quociente de Romberg [—-] trajet[oó]ria \(OF/OA\)\s*([\d.,]+)",
    ),
    (
        "velocity",
        "Quociente de Romberg — velocidade",
        r"Quociente de Romberg [—-] velocidade\s*(?:\n|\s)*\(OF/OA\)\s*([\d.,]+)",
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extrai um relatorio PDF de avaliacao de equilibrio "
            "(posturografia VR) para um payload JSON estruturado."
        )
    )
    parser.add_argument("pdf_file", help="Caminho para o PDF do relatorio.")
    parser.add_argument(
        "--output",
        help="Arquivo de saida JSON. Se omitido, imprime no stdout.",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf_file).resolve()
    payload = build_payload_from_pdf(pdf_path)
    output = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)

    return 0


def build_payload_from_pdf(pdf_path: Path) -> dict:
    reader = PdfReader(str(pdf_path))
    raw_text = "\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()
    if not raw_text:
        raise ValueError("Nao foi possivel extrair texto do PDF.")

    normalized_text = normalize_text(raw_text)

    patient_name = capture(raw_text, r"Paciente:\s*([^\n]+?)\s+Sexo:")
    sex = capture(raw_text, r"Sexo:\s*([^\n]+)")
    age_years = int(capture(raw_text, r"Idade:\s*(\d+)"))
    report_datetime_text = capture(raw_text, r"Data:\s*([^\n]+)")
    performed_at = parse_br_datetime(report_datetime_text)
    exam_id = capture(raw_text, r"ID exame:\s*([^\n]+)")
    protocol_description = capture(
        raw_text, r"Protocolo:\s*([^\n]+(?:\n[^\n]+)?)"
    ).replace("\n", " ").strip()

    posturographic_indices = build_posturographic_indices(normalized_text, raw_text)
    romberg_quotients = build_romberg_quotients(normalized_text, raw_text)

    above_count = sum(
        1
        for item in posturographic_indices
        if item["classification"] == "above_expected"
    )
    borderline_count = sum(
        1
        for item in posturographic_indices
        if item["classification"] == "borderline"
    )

    spl = find_index_value(posturographic_indices, "spl")
    ellipse_area = find_index_value(posturographic_indices, "confidence_ellipse_95_area")
    velocity = find_index_value(posturographic_indices, "mean_oscillation_velocity")
    ap_ml_ratio = find_index_value(posturographic_indices, "ap_ml_ratio")
    romberg_area = find_romberg_value(romberg_quotients, "area")

    visual_status = "ALERTA" if romberg_area is not None and romberg_area >= 2.0 else "OK"
    acquisition_warnings = extract_acquisition_warnings(raw_text)
    interpretation = extract_interpretation(raw_text)
    methodology_notes = build_methodology_notes(raw_text)

    summary = (
        f"SPL {spl:.1f} mm; area {ellipse_area:.1f} mm2; "
        f"velocidade {velocity:.2f} mm/s; Romberg area {romberg_area:.2f}; "
        f"{above_count} parametros acima do esperado"
    )
    if ap_ml_ratio is not None:
        summary += f"; predominio ML (AP/ML {ap_ml_ratio:.2f})."
    else:
        summary += "."

    content = interpretation or (
        "Avaliacao posturografica por trajetoria de headset VR com olhos abertos "
        "e fechados."
    )

    patient_name_ascii = to_ascii(patient_name.split(" Sexo")[0].strip())

    record = {
        "id": f"equilibrio-{exam_id}-{performed_at.strftime('%Y%m%dT%H%M%S')}",
        "title": (
            f"Equilibrio - {patient_name_ascii} - "
            f"{performed_at.strftime('%d/%m/%Y %H:%M')}"
        ),
        "sender": "Posturografia VR",
        "recipient": "RehabEasy",
        "created_at": performed_at.isoformat(),
        "summary": summary,
        "content": content,
        "tags": ["posturografia", "equilibrio", "vr", "romberg", "meta-quest"],
        "patient": {
            "name": patient_name_ascii,
            "age_years": age_years,
            "sex": sex.strip(),
            "external_id": exam_id,
        },
        "assessment": {
            "performed_at": performed_at.isoformat(),
            "exam_id": exam_id,
            "evaluator": extract_evaluator(raw_text),
            "protocol": {
                "description": protocol_description,
                "eyes_conditions": ["open", "closed"],
                "stance": "normal",
                "target_duration_seconds": 30,
                "actual_duration_seconds": extract_actual_duration(raw_text),
            },
            "device": {
                "type": "vr_headset",
                "model": extract_device_model(raw_text),
            },
            "posturographic_indices": posturographic_indices,
            "romberg_quotients": romberg_quotients,
            "derived_metrics": {
                "ap_ml_ratio": ap_ml_ratio,
                "parameters_above_expected_count": above_count,
                "parameters_borderline_count": borderline_count,
                "spl_mm": spl,
                "confidence_ellipse_95_area_mm2": ellipse_area,
                "mean_oscillation_velocity_mm_s": velocity,
                "romberg_area_quotient": romberg_area,
            },
            "automated_flags": {
                "increased_postural_sway": above_count > 0,
                "visual_dependency": {
                    "status": visual_status,
                    "romberg_area_quotient": romberg_area,
                    "threshold": 2.0,
                },
                "lateral_predominance": ap_ml_ratio is not None and ap_ml_ratio < 1.0,
                "acquisition_warnings": acquisition_warnings,
            },
            "interpretation": interpretation,
            "methodology_notes": methodology_notes,
        },
    }

    return {
        "source": "posturografia-vr",
        "schema_version": "1.0",
        "report_type": "EQUILIBRIO",
        "records": [record],
    }


def build_posturographic_indices(normalized_text: str, raw_text: str) -> list[dict]:
    indices = []

    for code, label, value_pattern, unit, reference_pattern in INDEX_SPECS:
        value_match = re.search(value_pattern, normalized_text, re.IGNORECASE)
        if not value_match:
            continue

        value = parse_float(value_match.group(1))
        reference = None
        if reference_pattern:
            reference_match = re.search(reference_pattern, normalized_text, re.IGNORECASE)
            if reference_match:
                reference = {
                    "mean": parse_float(reference_match.group(1)),
                    "sd": parse_float(reference_match.group(2)),
                }

        classification = extract_classification_near_match(normalized_text, value_match) or (
            "not_classified" if reference is None else "within_expected"
        )

        indices.append(
            {
                "code": code,
                "label": label,
                "value": value,
                "unit": unit,
                "reference": reference,
                "classification": classification,
            }
        )

    if not indices:
        raise ValueError("Nao foi possivel identificar indices posturograficos no PDF.")

    return indices


def build_romberg_quotients(normalized_text: str, raw_text: str) -> list[dict]:
    quotients = []

    for code, label, value_pattern in ROMBERG_SPECS:
        value_match = re.search(value_pattern, normalized_text, re.IGNORECASE | re.DOTALL)
        if not value_match:
            continue

        value = parse_float(value_match.group(1))
        classification = extract_classification_near_match(normalized_text, value_match) or (
            "above_expected" if value >= 2.0 else "within_expected"
        )

        quotients.append(
            {
                "code": code,
                "label": label,
                "value": value,
                "upper_limit": 2.0,
                "classification": classification,
            }
        )

    if not quotients:
        raise ValueError("Nao foi possivel identificar quocientes de Romberg no PDF.")

    return quotients


def extract_classification_near_match(text: str, value_match: re.Match[str]) -> str | None:
    tail = text[value_match.end() : value_match.end() + 120]
    match = re.search(
        r"(Dentro do esperado|Acima do esperado|Abaixo do esperado|faixa limitr[oó]fe)",
        tail,
        re.IGNORECASE,
    )
    if not match:
        return None

    value = normalize_text(match.group(1)).lower()
    if "dentro" in value:
        return "within_expected"
    if "acima" in value:
        return "above_expected"
    if "abaixo" in value:
        return "below_expected"
    if "limitrofe" in value:
        return "borderline"
    return None


def extract_classification_for_line(raw_text: str, label_prefix: str) -> str | None:
    pattern = re.escape(label_prefix[:20]) + r".{0,120}?(Dentro do esperado|Acima do esperado|Abaixo do esperado|faixa limitr[oó]fe)"
    match = re.search(pattern, raw_text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None

    value = normalize_text(match.group(1)).lower()
    if "dentro" in value:
        return "within_expected"
    if "acima" in value:
        return "above_expected"
    if "abaixo" in value:
        return "below_expected"
    if "limitrofe" in value:
        return "borderline"
    return None


def extract_acquisition_warnings(raw_text: str) -> list[str]:
    warnings = []
    section_match = re.search(
        r"Avisos de aquisi[cç][aã]o\s*(.+?)(?:Estatocinesiograma|Interpreta[cç][aã]o)",
        raw_text,
        re.IGNORECASE | re.DOTALL,
    )
    if not section_match:
        return warnings

    for line in section_match.group(1).splitlines():
        cleaned = line.strip().lstrip("•").strip()
        if cleaned:
            warnings.append(cleaned)

    return warnings


def extract_interpretation(raw_text: str) -> str:
    match = re.search(
        r"Interpreta[cç][aã]o\s*(.+?)(?:Observa[cç][aã]o metodol[oó]gica|Refer[eê]ncias)",
        raw_text,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return ""

    return " ".join(line.strip() for line in match.group(1).splitlines() if line.strip())


def build_methodology_notes(raw_text: str) -> list[str]:
    notes = []
    match = re.search(
        r"Observa[cç][aã]o metodol[oó]gica:\s*(.+?)(?:Refer[eê]ncias|Relat[oó]rio gerado)",
        raw_text,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        notes.append(" ".join(line.strip() for line in match.group(1).splitlines() if line.strip()))

    if "headset vr" in raw_text.lower() or "meta quest" in raw_text.lower():
        notes.append("A aquisicao foi feita a partir da trajetoria da cabeca (headset VR).")

    if "indicativos" in raw_text.lower():
        notes.append(
            "Os limiares normativos de plataforma de forca devem ser tratados como INDICATIVOS; "
            "priorizar indices relativos (Romberg, razao AP/ML)."
        )

    return notes


def extract_evaluator(raw_text: str) -> str | None:
    match = re.search(r"Avaliador:\s*([^\n]+)", raw_text)
    if not match:
        return None

    value = re.split(r"\s+ID exame:", match.group(1), flags=re.IGNORECASE)[0].strip()
    return None if value in {"—", "-", ""} else value


def extract_device_model(raw_text: str) -> str:
    if "Meta Quest 3" in raw_text:
        return "Meta Quest 3"
    match = re.search(r"headset \(([^)]+)\)", raw_text, re.IGNORECASE)
    return match.group(1).strip() if match else "VR Headset"


def extract_actual_duration(raw_text: str) -> int | None:
    match = re.search(r"Dura[cç][aã]o abaixo do recomendado \((\d+)\s*s\)", raw_text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def find_index_value(indices: list[dict], code: str) -> float | None:
    for item in indices:
        if item["code"] == code:
            return item["value"]
    return None


def find_romberg_value(quotients: list[dict], code: str) -> float | None:
    for item in quotients:
        if item["code"] == code:
            return item["value"]
    return None


def normalize_text(value: str) -> str:
    return unicodedata.normalize("NFKC", value)


def parse_br_datetime(value: str) -> datetime:
    parsed = datetime.strptime(value.strip(), "%d/%m/%Y %H:%M")
    return parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)


def capture(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
    if not match:
        raise ValueError(f"Padrao nao encontrado: {pattern}")
    return match.group(1).strip()


def parse_float(value: str) -> float:
    if value.count(",") > 0 and value.count(".") > 0 and value.find(".") < value.find(","):
        normalized = value.replace(".", "").replace(",", ".")
    else:
        normalized = value.replace(",", ".")
    return float(normalized)


def to_ascii(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return normalized.encode("ascii", "ignore").decode("ascii")


if __name__ == "__main__":
    raise SystemExit(main())
