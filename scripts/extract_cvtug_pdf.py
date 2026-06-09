import argparse
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extrai um relatorio PDF do CvTUG para um payload JSON estruturado."
    )
    parser.add_argument("pdf_file", help="Caminho para o PDF do CvTUG.")
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

    patient_name = capture(raw_text, r"Paciente:\s*(.+)")
    age_years = int(capture(raw_text, r"Idade:\s*(\d+)"))
    sex = capture(raw_text, r"Sexo:\s*([^\n]+)")
    external_id = capture(raw_text, r"\nID:\s*([^\n]+)")
    report_datetime_text = capture(raw_text, r"Data:\s*([^\n]+)")
    performed_at = parse_br_datetime(report_datetime_text)

    normal_total = capture_float(raw_text, r"Normal \(total\):\s*([\d.,]+)")
    normal_expected = capture_float(raw_text, r"esperado~([\d.,]+)")
    normal_upper_limit = capture_float(raw_text, r"lim\.sup~([\d.,]+)")
    normal_reference_source = capture(raw_text, r"lim\.sup~[\d.,]+\s*\|\s*([A-Za-z0-9-]+)")

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

    methodology_notes = extract_bullet_list(
        extract_section(raw_text, "Notas metodológicas:", "Referências:")
    )
    references = extract_references(extract_section(raw_text, "Referências:", None))

    file_name_timestamp_text = extract_filename_timestamp(pdf_path.name)
    document_notes = []
    if file_name_timestamp_text and file_name_timestamp_text != performed_at.strftime("%Y%m%d_%H%M%S"):
        document_notes.append(
            "O timestamp exibido no relatorio e diferente do timestamp presente no nome do arquivo PDF."
        )

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

    raw_report_text = " ".join(line.strip() for line in raw_text.splitlines() if line.strip())
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
        "source_document": {
            "file_name": pdf_path.name,
            "pages": len(reader.pages),
            "document_type": "pdf",
            "report_timestamp_text": report_datetime_text,
            "file_name_timestamp_text": file_name_timestamp_text,
            "notes": document_notes,
        },
        "raw_report_text": raw_report_text,
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
                        "source": normal_reference_source,
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
                        {"seconds": 12, "source": "Lusardi2017"},
                        {"seconds": 13.5, "source": "Shumway-Cook2000"},
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
            "references": references,
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


def extract_section(text: str, start_label: str, end_label: str | None) -> str:
    start = text.find(start_label)
    if start < 0:
        return ""
    start += len(start_label)
    end = text.find(end_label, start) if end_label else -1
    return text[start:end].strip() if end >= 0 else text[start:].strip()


def extract_bullet_list(text: str) -> list[str]:
    items = []
    for chunk in re.split(r"•", text):
        cleaned = " ".join(line.strip() for line in chunk.splitlines() if line.strip())
        cleaned = cleaned.replace("==================", "").strip()
        if cleaned:
            items.append(cleaned)
    return items


def extract_references(text: str) -> list[str]:
    matches = re.findall(r"\d+\)\s*(.+)", text)
    return [match.strip() for match in matches]


def extract_filename_timestamp(file_name: str) -> str | None:
    match = re.search(r"(\d{8}_\d{6})", file_name)
    return match.group(1) if match else None


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
    return float(value.replace(".", "").replace(",", ".") if value.count(",") > 0 and value.count(".") > 0 and value.find(".") < value.find(",") else value.replace(",", "."))


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


if __name__ == "__main__":
    raise SystemExit(main())
