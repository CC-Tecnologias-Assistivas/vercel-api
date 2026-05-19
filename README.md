# RehabEasy Transfer API

API FastAPI stateless para transferir payloads temporarios entre sistemas. O Sistema A publica um payload, a API devolve um token assinado no campo `id`, e o RehabEasy consome esse token como Sistema B para gravar os dados no SQLite local do aplicativo.

Sem banco externo, a API nao guarda estado e nao consegue garantir consumo unico real. A seguranca passa a ser assinatura HMAC + expiracao por TTL. O mesmo token pode ser lido novamente ate expirar, entao o controle de duplicidade fica no RehabEasy via SQLite.

## Endpoints

- `GET /api/health`
- `POST /api/payloads`
- `GET /api/payloads/{id}`
- `GET /api/payloads/{id}/status`

## Variaveis de ambiente

Copie `.env.example` e configure os valores na Vercel:

```env
SYSTEM_A_API_KEY=
SYSTEM_B_API_KEY=
TRANSFER_SIGNING_SECRET=
PAYLOAD_TTL_SECONDS=1800
MAX_PAYLOAD_BYTES=8192
ENVIRONMENT=production
```

`TRANSFER_SIGNING_SECRET` e recomendado. Se nao for definido, a API usa uma composicao de `SYSTEM_A_API_KEY` e `SYSTEM_B_API_KEY` para assinar os tokens.

Como o payload fica embutido no token retornado como `id`, mantenha payloads pequenos. O limite padrao e `8192` bytes.

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

O script abaixo cria um payload como Sistema A, consulta status e consome como Sistema B.

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
