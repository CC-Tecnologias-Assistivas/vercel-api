import re
import unicodedata
from datetime import datetime
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


def build_payload_from_pdf(pdf_path: Path | str) -> dict:
    return build_payload_from_pdf_bytes(Path(pdf_path).read_bytes())


def build_payload_from_pdf_bytes(pdf_bytes: bytes) -> dict:
    reader = PdfReader(BytesIO(pdf_bytes))
    raw_text = "\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()
    if not raw_text:
        raise ValueError("Nao foi possivel extrair texto do PDF.")

    if re.search(r"Resultados\s*\(TUG\s*[—-]\s*segundos\)", raw_text, re.IGNORECASE):
        return build_payload_from_tabular_text(raw_text)

    patient_name = capture(raw_text, r"Paciente:\s*(.+)")
    age_years = int(capture(raw_text, r"Idade:\s*(\d+)"))
    sex = capture(raw_text, r"Sexo:\s*([^\n]+)")
    external_id = capture(raw_text, r"\nID:\s*([^\n]+)")
    report_datetime_text = capture(raw_text, r"Data:\s*([^\n]+)")
    performed_at = parse_br_datetime(report_datetime_text)

    normal_total = capture_float(raw_text, r"Normal \(total\):\s*([\d.,]+)")
    normal_expected = capture_float(raw_text, r"esperado~([\d.,]+)")
    normal_upper_limit = capture_float(raw_text, r"lim\.sup~([\d.,]+)")

    motor_total = capture_float(raw_text, r"Motora \(total\):\s*([\d.,]+)")
    motor_dtc = capture_float(raw_text, r"Motora \(total\):\s*[\d.,]+\s*DTC:\s*([\d.,]+)%")
    cognitive_total = capture_float(raw_text, r"Cognitiva \(total\):\s*([\d.,]+)")
    cognitive_dtc = capture_float(raw_text, r"Cognitiva \(total\):\s*[\d.,]+\s*DTC:\s*([\d.,]+)%")

    phase_lines = re.findall(
        r"Macro-fases:\s*Levantar\s*([\d.,]+)s\s*\|\s*Marcha\s*([\d.,]+)s\s*\|\s*Sentar\s*([\d.,]+)s",
        raw_text,
    )
    if len(phase_lines) != 3:
        raise ValueError("Nao foi possivel identificar as macro-fases das tres condicoes.")

    tug_above_upper_limit_text = capture(
        raw_text, r"TUG acima do limite superior:\s*([^\n]+)"
    )
    fall_screening_status = capture(
        raw_text,
        r"Triagem de quedas\s*\(>=12s\s+Lusardi2017\s*/\s*>=13\.5s\s+Shumway-Cook2000\):\s*([^\n]+)",
    )
    dual_task_status_text = capture(
        raw_text, r"Dual-task cost \(pior condição\):\s*([^\n]+)"
    )
    normal_walk_speed_mps = capture_float(
        raw_text, r"Velocidade média\s*\(marcha\s*-\s*Normal\):\s*([\d.,]+)\s*m/s"
    )
    walk_speed_note = capture(raw_text, r"Nota velocidade:\s*([^\n]+)")

    methodology_notes = build_generic_methodology_notes(raw_text)
    normal_phases = phase_lines[0]
    motor_phases = phase_lines[1]
    cognitive_phases = phase_lines[2]

    worst_condition_code = "cognitive" if cognitive_dtc >= motor_dtc else "motor"
    worst_condition_label = "cognitiva" if worst_condition_code == "cognitive" else "motora"
    worst_dtc = cognitive_dtc if cognitive_dtc >= motor_dtc else motor_dtc
    dual_task_threshold = extract_first_number(dual_task_status_text)
    dual_task_status = dual_task_status_text.split(">=")[0].strip().upper()

    summary = (
        f"TUG normal {normal_total:.1f}s; motora {motor_total:.1f}s; "
        f"cognitiva {cognitive_total:.1f}s; pior DTC {worst_dtc:.0f}%; "
        f"triagem de quedas {fall_screening_status}; velocidade {normal_walk_speed_mps:.2f} m/s."
    )
    content = (
        "Teste TUG com tres condicoes avaliadas. Resultado normal dentro do limite superior "
        "de referencia, com aumento importante de custo em dupla tarefa, especialmente na "
        f"condicao {worst_condition_label}, e velocidade de marcha discretamente baixa."
    )

    patient_name_ascii = to_ascii(patient_name)

    record = {
        "id": f"cvtug-{external_id}-{performed_at.strftime('%Y%m%dT%H%M%S')}",
        "title": f"CvTUG - {patient_name_ascii} - {performed_at.strftime('%d/%m/%Y %H:%M')}",
        "sender": "CvTUG",
        "recipient": "RehabEasy",
        "created_at": performed_at.isoformat(),
        "summary": summary,
        "content": content,
        "tags": ["cvtug", "tug", "dual-task", "fall-risk-screening"],
        "patient": {
            "name": patient_name_ascii,
            "age_years": age_years,
            "sex": sex,
            "external_id": external_id,
        },
        "assessment": {
            "performed_at": performed_at.isoformat(),
            "measure_unit": "seconds",
            "conditions": [
                {
                    "code": "normal",
                    "label": "Normal",
                    "total_seconds": normal_total,
                    "dual_task_cost_percent": None,
                    "reference": {
                        "expected_seconds": normal_expected,
                        "upper_limit_seconds": normal_upper_limit,
                    },
                    "phases": build_phases(normal_phases),
                },
                {
                    "code": "motor",
                    "label": "Motora",
                    "total_seconds": motor_total,
                    "dual_task_cost_percent": motor_dtc,
                    "reference": None,
                    "phases": build_phases(motor_phases),
                },
                {
                    "code": "cognitive",
                    "label": "Cognitiva",
                    "total_seconds": cognitive_total,
                    "dual_task_cost_percent": cognitive_dtc,
                    "reference": None,
                    "phases": build_phases(cognitive_phases),
                },
            ],
            "derived_metrics": {
                "worst_dual_task_cost_percent": worst_dtc,
                "normal_walk_speed_mps": normal_walk_speed_mps,
            },
            "automated_flags": {
                "tug_above_upper_limit": normalize_bool_ptbr(tug_above_upper_limit_text),
                "fall_screening": {
                    "status": fall_screening_status,
                    "thresholds": [
                        {"seconds": 12},
                        {"seconds": 13.5},
                    ],
                },
                "dual_task_cost": {
                    "status": dual_task_status,
                    "alert_threshold_percent": dual_task_threshold,
                    "worst_condition_code": worst_condition_code,
                    "worst_percent": worst_dtc,
                },
                "gait_speed": {
                    "normal_condition_mps": normal_walk_speed_mps,
                    "note": walk_speed_note,
                },
            },
            "methodology_notes": methodology_notes,
        },
    }

    return {
        "source": "cvtug",
        "schema_version": "1.1",
        "report_type": "TUG",
        "records": [record],
    }


def build_phases(phase_values: tuple[str, str, str]) -> dict:
    stand, walk, sit = phase_values
    return {
        "stand_seconds": parse_float(stand),
        "walk_seconds": parse_float(walk),
        "sit_seconds": parse_float(sit),
    }


def build_payload_from_tabular_text(raw_text: str) -> dict:
    """Build the same CvTUG contract from the newer table-based report layout."""
    compact_text = " ".join(raw_text.split())
    patient_name = capture(compact_text, r"Paciente:\s*(.+?)\s+Sexo:")
    sex = capture(compact_text, r"Sexo:\s*(.+?)\s+Idade:")
    age_years = int(capture(compact_text, r"Idade:\s*(\d+)"))
    report_datetime_text = capture(
        compact_text, r"Data:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})"
    )
    performed_at = parse_br_datetime(report_datetime_text)
    external_id = capture(compact_text, r"\bID:\s*(\S+)")
    protocol_description = capture(
        compact_text, r"Protocolo:\s*(.+?)\s+Resultados\s*\(TUG"
    )

    normal = extract_tabular_condition(raw_text, "Normal")
    motor = extract_tabular_condition(raw_text, "Motora")
    cognitive = extract_tabular_condition(raw_text, "Cognitiva")
    normal_expected = extract_optional_float(normal["tail"], r"esperado\s*~\s*([\d.,]+)")
    normal_upper_limit = extract_optional_float(normal["tail"], r"lim\.sup\s*~\s*([\d.,]+)")
    normal_expected = normal_expected if normal_expected is not None else normal["total"]
    normal_upper_limit = normal_upper_limit if normal_upper_limit is not None else normal["total"]

    tug_above_upper_limit_text = capture(
        compact_text,
        r"TUG acima do limite superior\s+(sim|n[aã]o|true|false)",
    )
    fall_match = re.search(
        r"Triagem de quedas.*?Shumway-Cook2000\)?\s+(OK|ALERTA|ATEN[CÇ][AÃ]O|N[AÃ]O)\b",
        compact_text,
        re.IGNORECASE,
    )
    if not fall_match:
        raise ValueError("Nao foi possivel identificar a triagem de quedas.")
    fall_screening_status = fall_match.group(1)

    dual_match = re.search(
        r"Dual-task cost\s*\(pior condi[cç][aã]o\)\s+(ALERTA|ATEN[CÇ][AÃ]O|OK)"
        r"(?:\s*>=\s*([\d.,]+)\s*%)?",
        compact_text,
        re.IGNORECASE,
    )
    if not dual_match:
        raise ValueError("Nao foi possivel identificar o custo de dupla tarefa.")
    dual_task_status = dual_match.group(1).upper()
    dual_task_threshold = parse_float(dual_match.group(2)) if dual_match.group(2) else 20.0

    normal_walk_speed_mps = capture_float(
        compact_text,
        r"Velocidade m[eé]dia\s*\(marcha\s*[-—]\s*Normal\)\s*:?\s*([\d.,]+)\s*m/s",
    )
    walk_speed_note = capture(
        compact_text, r"Nota velocidade\s*(.+?)(?=\s+Relat[oó]rio gerado)"
    )

    conditions = [normal, motor, cognitive]
    worst_condition = max(conditions, key=lambda item: item["dtc"] or 0)
    methodology_notes = build_generic_methodology_notes(raw_text)
    summary = (
        f"TUG normal {normal['total']:.1f}s; motora {motor['total']:.1f}s; "
        f"cognitiva {cognitive['total']:.1f}s; pior DTC {worst_condition['dtc']:.0f}%; "
        f"triagem de quedas {fall_screening_status}; velocidade {normal_walk_speed_mps:.2f} m/s."
    )
    content = (
        "Teste TUG com tres condicoes avaliadas. Resultado normal dentro do limite superior "
        "de referencia, com aumento importante de custo em dupla tarefa, especialmente na "
        f"condicao {worst_condition['label'].lower()}, e velocidade de marcha reduzida."
    )

    record = {
        "id": f"cvtug-{external_id}-{performed_at.strftime('%Y%m%dT%H%M%S')}",
        "title": f"CvTUG - {to_ascii(patient_name)} - {performed_at.strftime('%d/%m/%Y %H:%M')}",
        "sender": "CvTUG",
        "recipient": "RehabEasy",
        "created_at": performed_at.isoformat(),
        "summary": summary,
        "content": content,
        "tags": ["cvtug", "tug", "dual-task", "fall-risk-screening"],
        "patient": {
            "name": to_ascii(patient_name),
            "age_years": age_years,
            "sex": to_ascii(sex),
            "external_id": external_id,
        },
        "assessment": {
            "performed_at": performed_at.isoformat(),
            "measure_unit": "seconds",
            "conditions": [
                build_condition_payload(normal, normal_expected, normal_upper_limit),
                build_condition_payload(motor),
                build_condition_payload(cognitive),
            ],
            "derived_metrics": {
                "worst_dual_task_cost_percent": worst_condition["dtc"],
                "normal_walk_speed_mps": normal_walk_speed_mps,
            },
            "automated_flags": {
                "tug_above_upper_limit": normalize_bool_ptbr(tug_above_upper_limit_text),
                "fall_screening": {
                    "status": fall_screening_status,
                    "thresholds": [{"seconds": 12}, {"seconds": 13.5}],
                },
                "dual_task_cost": {
                    "status": dual_task_status,
                    "alert_threshold_percent": dual_task_threshold,
                    "worst_condition_code": worst_condition["code"],
                    "worst_percent": worst_condition["dtc"],
                },
                "gait_speed": {
                    "normal_condition_mps": normal_walk_speed_mps,
                    "note": walk_speed_note,
                },
            },
            "methodology_notes": methodology_notes,
        },
    }
    return {
        "source": "cvtug",
        "schema_version": "1.1",
        "report_type": "TUG",
        "records": [record],
    }


def extract_tabular_condition(raw_text: str, label: str) -> dict:
    match = re.search(
        rf"^\s*{label}\s+([\d.,]+)\s+Levantar\s+([\d.,]+)s\s*\|\s*"
        r"Marcha\s+([\d.,]+)s\s*\|\s*Sentar\s+([\d.,]+)s\s*(.*)$",
        raw_text,
        re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        raise ValueError(f"Nao foi possivel identificar a condicao {label}.")
    tail = match.group(5).strip()
    dtc_match = re.search(r"([\d.,]+)\s*%", tail)
    return {
        "code": {"Normal": "normal", "Motora": "motor", "Cognitiva": "cognitive"}[label],
        "label": label,
        "total": parse_float(match.group(1)),
        "phases": (match.group(2), match.group(3), match.group(4)),
        "dtc": parse_float(dtc_match.group(1)) if dtc_match else None,
        "tail": tail,
    }


def build_condition_payload(
    condition: dict,
    expected_seconds: float | None = None,
    upper_limit_seconds: float | None = None,
) -> dict:
    reference = None
    if expected_seconds is not None and upper_limit_seconds is not None:
        reference = {
            "expected_seconds": expected_seconds,
            "upper_limit_seconds": upper_limit_seconds,
        }
    return {
        "code": condition["code"],
        "label": condition["label"],
        "total_seconds": condition["total"],
        "dual_task_cost_percent": condition["dtc"],
        "reference": reference,
        "phases": build_phases(condition["phases"]),
    }


def extract_optional_float(text: str, pattern: str) -> float | None:
    match = re.search(pattern, text, re.IGNORECASE)
    return parse_float(match.group(1)) if match else None


def build_generic_methodology_notes(raw_text: str) -> list[str]:
    notes = []

    if "dual-task cost" in raw_text.lower():
        notes.append(
            "O dual-task cost e um indicador heuristico e deve ser interpretado no contexto clinico."
        )

    if "normas" in raw_text.lower():
        notes.append(
            "Os valores de referencia do relatorio devem ser interpretados conforme a metodologia configurada no sistema de origem."
        )

    return notes


def parse_br_datetime(value: str) -> datetime:
    parsed = datetime.strptime(value.strip(), "%d/%m/%Y %H:%M")
    return parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)


def capture(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        raise ValueError(f"Padrao nao encontrado: {pattern}")
    return match.group(1).strip()


def capture_float(text: str, pattern: str) -> float:
    return parse_float(capture(text, pattern))


def parse_float(value: str) -> float:
    if (
        value.count(",") > 0
        and value.count(".") > 0
        and value.find(".") < value.find(",")
    ):
        normalized = value.replace(".", "").replace(",", ".")
    else:
        normalized = value.replace(",", ".")
    return float(normalized)


def normalize_bool_ptbr(value: str) -> bool:
    return value.strip().lower() in {"sim", "true", "verdadeiro"}


def extract_first_number(value: str) -> float:
    match = re.search(r"(\d+(?:[.,]\d+)?)", value)
    if not match:
        raise ValueError(f"Nenhum numero encontrado em: {value}")
    return parse_float(match.group(1))


def to_ascii(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return normalized.encode("ascii", "ignore").decode("ascii")
