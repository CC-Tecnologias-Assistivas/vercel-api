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
