import argparse
import os
import sys
from pathlib import Path

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Envia um PDF CvTUG, equilibrio ou Index-Index para POST /api/payloads/pdf."
    )
    parser.add_argument("pdf_file", help="Caminho do PDF a enviar.")
    parser.add_argument(
        "--base-url",
        default=os.getenv("API_BASE_URL", "https://telemedicinacc.vercel.app"),
        help="URL base da API.",
    )
    parser.add_argument(
        "--system-a-key",
        default=os.getenv("SYSTEM_A_API_KEY", ""),
        help="Credencial key_id.secret do Sistema A.",
    )
    args = parser.parse_args()
    if not args.system_a_key:
        print("Credencial ausente. Defina SYSTEM_A_API_KEY ou use --system-a-key.", file=sys.stderr)
        return 2

    pdf_path = Path(args.pdf_file).resolve()
    if not pdf_path.is_file():
        print(f"Arquivo nao encontrado: {pdf_path}", file=sys.stderr)
        return 1

    base_url = args.base_url.rstrip("/")
    with pdf_path.open("rb") as handle:
        response = httpx.post(
            f"{base_url}/api/payloads/pdf",
            headers={"X-API-KEY": args.system_a_key},
            files={"file": (pdf_path.name, handle, "application/pdf")},
            timeout=60,
        )

    print(f"HTTP {response.status_code}")
    print(response.text)
    return 0 if response.is_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
