# RehabEasy Transfer API

API FastAPI para transferir payloads temporarios entre sistemas. O Sistema A publica um payload, o RehabEasy consome uma vez como Sistema B e grava os dados no SQLite local do aplicativo.

O armazenamento transacional fica no Supabase/Postgres. O consumo unico e feito por `PATCH` condicional: somente payloads nao consumidos e ainda dentro do TTL recebem `consumed_at`.

## Endpoints

- `GET /api/health`
- `POST /api/payloads`
- `GET /api/payloads/{id}`
- `GET /api/payloads/{id}/status`

## Variaveis de ambiente

Copie `.env.example` e configure os valores na Vercel:

```env
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_PAYLOADS_TABLE=payloads
SYSTEM_A_API_KEY=
SYSTEM_B_API_KEY=
PAYLOAD_TTL_SECONDS=1800
MAX_PAYLOAD_BYTES=1048576
ENVIRONMENT=production
```

Use a service role key somente no backend/Vercel. Nao exponha essa chave no RehabEasy nem em frontend.

## Tabela Supabase

Crie a tabela no SQL Editor do Supabase:

```sql
create table if not exists public.payloads (
  id text primary key,
  created_at timestamptz not null,
  expires_at timestamptz not null,
  consumed_at timestamptz null,
  source text not null,
  payload jsonb not null
);

create index if not exists idx_payloads_expires_at on public.payloads (expires_at);
create index if not exists idx_payloads_consumed_at on public.payloads (consumed_at);
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

## Teste Sistema A -> RehabEasy

Para simular somente o Sistema A enviando um relatorio CvTUG, use:

```bash
python scripts/send_cvtug_payload.py \
  --base-url https://telemedicinacc.vercel.app \
  --system-a-key SUA_SYSTEM_A_API_KEY
```

O script imprime um `payload_id`. Com o RehabEasy aberto, cole esse ID no campo de payload e clique em `Importar payload`. O RehabEasy sera o Sistema B e consumira esse payload uma unica vez.

Arquivos de referencia:

- Schema: `docs/cvtug_payload_schema.json`
- Exemplo baseado no PDF: `examples/cvtug_payload_sample.json`
