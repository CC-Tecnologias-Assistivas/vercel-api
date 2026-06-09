# RehabEasy Transfer API

API FastAPI para transferir payloads temporarios entre sistemas. O Sistema A publica um payload, o RehabEasy consome uma vez como Sistema B e grava os dados no SQLite local do aplicativo.

O armazenamento transacional fica no Supabase/Postgres. O consumo unico e feito por `PATCH` condicional: somente payloads nao consumidos e ainda dentro do TTL recebem `consumed_at`.

## Endpoints

- `GET /api/health`
- `POST /api/payloads`
- `GET /api/payloads/next`
- `GET /api/payloads/{id}`
- `GET /api/payloads/{id}/status`

## Fluxo recomendado

1. O sistema publicador monta um JSON com `source`, `schema_version` e `records`.
2. O sistema publicador envia para `POST /api/payloads` com `X-API-KEY` do Sistema A.
3. A API salva o payload no Supabase e devolve um `payload_id`.
4. O RehabEasy ou outro consumidor usa `GET /api/payloads/{id}` ou `GET /api/payloads/next` com a chave do Sistema B.
5. A primeira leitura bem-sucedida consome o payload. Leituras seguintes retornam `404`.

## Variaveis de ambiente

Copie `.env.example` e configure os valores na Vercel:

```env
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_PAYLOADS_TABLE=payloads
SYSTEM_A_API_KEY=sistema-mobile
SYSTEM_B_API_KEY=rehabeasy-sistema
PAYLOAD_TTL_SECONDS=1800
MAX_PAYLOAD_BYTES=1048576
ENVIRONMENT=production
```

Use a service role key somente no backend/Vercel. Nao exponha essa chave no RehabEasy nem em frontend.

Sugestao de nomes para as chaves:

- `SYSTEM_A_API_KEY=sistema-mobile`
- `SYSTEM_B_API_KEY=rehabeasy-sistema`

Nao existe migration SQL para essa troca. Basta atualizar as variaveis de ambiente na Vercel e a configuracao do consumidor.

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

Guias e contratos:

- Guia de integracao para terceiros: `docs/api-integration-guide.md`
- Schema generico recomendado: `docs/recommended_payload_schema.json`
- Exemplo generico: `examples/generic_payload_sample.json`
- Schema CvTUG: `docs/cvtug_payload_schema.json`
- Exemplo CvTUG: `examples/cvtug_payload_sample.json`

## Exemplos

Criar payload:

```bash
curl -X POST http://127.0.0.1:8000/api/payloads \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: chave-do-sistema-a" \
  -d '{"source":"sistema-a","schema_version":"1.0","entity":"clinical_report","records":[{"id":"atendimento-ABC-999","title":"Atendimento ABC-999","sender":"sistema-a","recipient":"RehabEasy","created_at":"2026-05-19T10:00:00Z","summary":"Registro para importacao","content":"Paciente sincronizado pela API.","tags":["rehabeasy"]}]}'
```

Consumir payload:

```bash
curl http://127.0.0.1:8000/api/payloads/payload_ID \
  -H "X-API-KEY: chave-do-sistema-b"
```

Consumir automaticamente o proximo payload pendente:

```bash
curl http://127.0.0.1:8000/api/payloads/next \
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

Com o RehabEasy aberto, clique em `Atualizar`. O RehabEasy sera o Sistema B, buscara automaticamente o proximo payload pendente e consumira esse payload uma unica vez.

Arquivos de referencia:

- Schema: `docs/cvtug_payload_schema.json`
- Exemplo baseado no PDF: `examples/cvtug_payload_sample.json`
- Extrator PDF -> JSON: `scripts/extract_cvtug_pdf.py`

Para extrair um payload estruturado diretamente de um PDF do CvTUG:

```bash
python scripts/extract_cvtug_pdf.py "C:/caminho/CvTUG_Report.pdf" --output cvtug_payload.json
```
