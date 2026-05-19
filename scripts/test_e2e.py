import argparse
import json
import os
import sys
import urllib.error
import urllib.request


DEFAULT_PAYLOAD = {
    "source": "sistema-a",
    "records": [
        {
            "id": "atendimento-ABC-999",
            "title": "Atendimento ABC-999",
            "sender": "sistema-a",
            "recipient": "RehabEasy",
            "created_at": "2026-05-19T10:00:00Z",
            "summary": "Registro de teste para importacao no RehabEasy",
            "content": "Paciente sincronizado pela API de transferencia.",
            "tags": ["e2e", "rehabeasy"],
        }
    ],
}

DEFAULT_SYSTEM_A_API_KEY = "rehabeasy-system-a"
DEFAULT_SYSTEM_B_API_KEY = "rehabeasy-system-b"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Testa criacao, consumo e consumo unico da RehabEasy Transfer API."
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
        "--system-b-key",
        default=os.getenv("SYSTEM_B_API_KEY", DEFAULT_SYSTEM_B_API_KEY),
        help="API key do Sistema B. Tambem pode usar SYSTEM_B_API_KEY.",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    try:
        print("1. Testando health check...")
        health = request_json("GET", f"{base_url}/api/health")
        assert health["status"] == "ok"
        print("   OK")

        print("2. Criando payload como Sistema A...")
        created = request_json(
            "POST",
            f"{base_url}/api/payloads",
            api_key=args.system_a_key,
            body=DEFAULT_PAYLOAD,
        )
        payload_id = created["id"]
        print(f"   OK: {payload_id}")

        print("3. Consultando status antes do consumo...")
        status_response = request_json(
            "GET",
            f"{base_url}/api/payloads/{payload_id}/status",
            api_key=args.system_b_key,
        )
        assert status_response["exists"] is True
        print(f"   OK: ttl_seconds={status_response['ttl_seconds']}")

        print("4. Consumindo payload como Sistema B...")
        consumed = request_json(
            "GET",
            f"{base_url}/api/payloads/{payload_id}",
            api_key=args.system_b_key,
        )
        assert consumed["id"] == payload_id
        assert consumed["payload"] == DEFAULT_PAYLOAD
        assert consumed["consumed"] is True
        print("   OK")

        print("5. Confirmando consumo unico...")
        try:
            request_json(
                "GET",
                f"{base_url}/api/payloads/{payload_id}",
                api_key=args.system_b_key,
            )
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
            print("   OK: segunda leitura retornou 404")
        else:
            raise AssertionError("A segunda leitura deveria retornar 404")

        print("6. Criando outro payload para testar consumo automatico...")
        created_next = request_json(
            "POST",
            f"{base_url}/api/payloads",
            api_key=args.system_a_key,
            body=DEFAULT_PAYLOAD,
        )
        next_payload_id = created_next["id"]
        print(f"   OK: {next_payload_id}")

        print("7. Consumindo proximo payload pendente...")
        consumed_next = request_json(
            "GET",
            f"{base_url}/api/payloads/next",
            api_key=args.system_b_key,
        )
        assert consumed_next["id"] == next_payload_id
        assert consumed_next["payload"] == DEFAULT_PAYLOAD
        assert consumed_next["consumed"] is True
        print("   OK")

    except Exception as exc:
        print(f"Teste falhou: {exc}", file=sys.stderr)
        return 1

    print("Teste E2E concluido com sucesso.")
    return 0


def request_json(
    method: str,
    url: str,
    api_key: str | None = None,
    body: dict | None = None,
) -> dict:
    data = None
    headers = {}

    if api_key:
        headers["X-API-KEY"] = api_key

    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
