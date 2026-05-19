# RehabEasy Transfer API

API FastAPI para transferir payloads temporarios entre sistemas. O Sistema A publica um payload, o RehabEasy consome uma vez como Sistema B e grava os dados no SQLite local do aplicativo.

## Endpoints

- `GET /api/health`
- `POST /api/payloads`
- `GET /api/payloads/{id}`
- `GET /api/payloads/{id}/status`

## Variaveis de ambiente

Copie `.env.example` e configure os valores na Vercel:

```env
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=
SYSTEM_A_API_KEY=
SYSTEM_B_API_KEY=
PAYLOAD_TTL_SECONDS=1800
MAX_PAYLOAD_BYTES=1048576
ENVIRONMENT=production
```

## Rodar localmente

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

Documentacao local:

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

Documentacao em producao:

- Swagger UI: `https://telemedicinacc.vercel.app/docs`
- OpenAPI JSON: `https://telemedicinacc.vercel.app/openapi.json`

## Exemplos

Criar payload:

```bash
curl -X POST http://127.0.0.1:8000/api/payloads \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: chave-do-sistema-a" \
  -d '{"source":"sistema-a","records":[{"id":"atendimento-ABC-999","title":"Atendimento ABC-999","sender":"sistema-a","recipient":"RehabEasy","created_at":"2026-05-19T10:00:00Z","summary":"Registro para importacao","content":"Paciente sincronizado pela API.","tags":["rehabeasy"]}]}'
```

Consumir payload:

```bash
curl http://127.0.0.1:8000/api/payloads/payload_ID \
  -H "X-API-KEY: chave-do-sistema-b"
```

## Teste E2E

O script abaixo cria um payload como Sistema A, consome como Sistema B e confirma que a segunda leitura retorna `404`.

```bash
python scripts/test_e2e.py \
  --base-url https://telemedicinacc.vercel.app \
  --system-a-key SUA_SYSTEM_A_API_KEY \
  --system-b-key SUA_SYSTEM_B_API_KEY
```

Tambem da para usar variaveis de ambiente:

```bash
API_BASE_URL=https://telemedicinacc.vercel.app \
SYSTEM_A_API_KEY=SUA_SYSTEM_A_API_KEY \
SYSTEM_B_API_KEY=SUA_SYSTEM_B_API_KEY \
python scripts/test_e2e.py
```
