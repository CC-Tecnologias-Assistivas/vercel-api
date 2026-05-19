import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_PAYLOAD_PATH = Path(__file__).resolve().parents[1] / "examples" / "cvtug_payload_sample.json"
DEFAULT_SYSTEM_A_API_KEY = "rehabeasy-system-a"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Simula o Sistema A enviando um relatorio CvTUG para a API. "
            "O RehabEasy deve ser o Sistema B e consumira automaticamente pelo botao Atualizar."
        )
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("API_BASE_URL", "https://telemedicinacc.vercel.app"),
        help="URL base da API. Tambem pode usar API_BASE_URL.",
    )
    parser.add_argument(
        "--system-a-key",
        default=os.getenv("SYSTEM_A_API_KEY", DEFAULT_SYSTEM_A_API_KEY),
        help="API key do Sistema A. Tambem pode usar SYSTEM_A_API_KEY.",
    )
    parser.add_argument(
        "--payload-file",
        default=str(DEFAULT_PAYLOAD_PATH),
        help="Arquivo JSON com o payload CvTUG a enviar.",
    )
    args = parser.parse_args()

    payload_path = Path(args.payload_file)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    base_url = args.base_url.rstrip("/")

    try:
        response = request_json(
            "POST",
            f"{base_url}/api/payloads",
            api_key=args.system_a_key,
            body=payload,
        )
    except urllib.error.HTTPError as exc:
        print(f"Erro HTTP {exc.code}: {exc.read().decode('utf-8')}", file=sys.stderr)
        return 1

    payload_id = response["id"]
    print("Payload CvTUG enviado com sucesso.")
    print(f"payload_id: {payload_id}")
    print()
    print("No RehabEasy, clique em Atualizar para consumir automaticamente o proximo payload pendente.")
    return 0


def request_json(
    method: str,
    url: str,
    api_key: str,
    body: dict,
) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-API-KEY": api_key,
        },
        method=method,
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
