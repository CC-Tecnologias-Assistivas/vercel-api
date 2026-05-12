# Temporary Payload API

API FastAPI para armazenar payloads temporarios no Upstash Redis com TTL de 30 minutos e consumo unico via `GETDEL`.

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

- Swagger UI: `https://vercel-api-delta-topaz.vercel.app/docs`
- OpenAPI JSON: `https://vercel-api-delta-topaz.vercel.app/openapi.json`

## Exemplos

Criar payload:

```bash
curl -X POST http://127.0.0.1:8000/api/payloads \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: chave-do-sistema-a" \
  -d '{"evento":"pedido_criado","dados":{"pedido_id":"ABC-999"}}'
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
  --base-url https://vercel-api-delta-topaz.vercel.app \
  --system-a-key SUA_SYSTEM_A_API_KEY \
  --system-b-key SUA_SYSTEM_B_API_KEY
```

Tambem da para usar variaveis de ambiente:

```bash
API_BASE_URL=https://vercel-api-delta-topaz.vercel.app \
SYSTEM_A_API_KEY=SUA_SYSTEM_A_API_KEY \
SYSTEM_B_API_KEY=SUA_SYSTEM_B_API_KEY \
python scripts/test_e2e.py
```
