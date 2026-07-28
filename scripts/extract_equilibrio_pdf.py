import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.pdf_extractors.equilibrio import build_payload_from_pdf


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


if __name__ == "__main__":
    raise SystemExit(main())
