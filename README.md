# RehabEasy Transfer API

API FastAPI para transferir payloads temporarios entre sistemas. O Sistema A publica um payload, o RehabEasy consome uma vez como Sistema B e grava os dados no SQLite local do aplicativo.

O armazenamento transacional fica no Supabase/Postgres. O consumo unico e feito por `PATCH` condicional: somente payloads nao consumidos e ainda dentro do TTL recebem `consumed_at`.

## Endpoints

- `GET /api/health`
- `POST /api/payloads`
- `POST /api/payloads/pdf`
- `GET /api/payloads/next`
- `GET /api/payloads/{id}`
- `GET /api/payloads/{id}/status`
- `POST /api/internal/maintenance/purge` (somente manutencao)

## Fluxo recomendado

### JSON (legado / compatibilidade)

1. O sistema publicador monta um JSON com `source`, `schema_version` e `records`.
2. O sistema publicador envia para `POST /api/payloads` com `X-API-KEY` do Sistema A.
3. A API salva o payload no Supabase e devolve um `payload_id`.
4. O RehabEasy ou outro consumidor usa `GET /api/payloads/{id}` ou `GET /api/payloads/next` com a chave do Sistema B.
5. A primeira leitura bem-sucedida consome o payload. Leituras seguintes retornam `404`.

### PDF (CvTUG / equilibrio / Index-Index)

1. O sistema publicador envia o PDF em `POST /api/payloads/pdf` (`multipart/form-data`, campo `file`).
2. A API detecta o tipo, extrai o JSON estruturado e guarda o PDF no Supabase Storage (`payload-pdfs`).
3. No consumo, a resposta inclui `payload` + `pdf_url` (URL assinada temporaria).
4. O RehabEasy baixa o PDF, exibe no viewer e monta os graficos a partir do JSON extraido.

## Variaveis de ambiente

Copie `.env.example` e configure os valores na Vercel:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_PAYLOADS_TABLE=payloads
SUPABASE_ORGANIZATIONS_TABLE=organizations
SUPABASE_CREDENTIALS_TABLE=api_credentials
SUPABASE_AUDIT_TABLE=audit_events
SUPABASE_PDF_BUCKET=payload-pdfs
CREDENTIAL_HASH_PEPPER=
PATIENT_PSEUDONYMIZATION_KEY=
MAINTENANCE_KEY=
CRON_SECRET=
PAYLOAD_TTL_SECONDS=1800
CONSUMED_PAYLOAD_GRACE_SECONDS=1800
MAX_PAYLOAD_BYTES=1048576
MAX_PDF_BYTES=10485760
PDF_SIGNED_URL_SECONDS=1800
LOCAL_CLINICAL_RETENTION_DAYS=0
ENVIRONMENT=production
```

Use a service role key somente no backend/Vercel. Nao exponha essa chave no RehabEasy nem em frontend.

As credenciais de integracao nao ficam em variaveis globais nem no codigo. Crie
uma organizacao e credenciais por funcao com
`python scripts/manage_credentials.py create --organization-id ... --role publisher`
e distribua o valor exibido uma unica vez ao sistema correspondente. O banco
guarda somente o hash Argon2id do segredo. Para revogar, use
`python scripts/manage_credentials.py revoke --credential-id ...`.

Os segredos de ambiente devem ser aleatorios; `CREDENTIAL_HASH_PEPPER`,
`PATIENT_PSEUDONYMIZATION_KEY` e `MAINTENANCE_KEY` têm pelo menos 32
caracteres. Nunca os exponha no frontend, nos clientes desktop ou em logs.
`CRON_SECRET` pode ter no mínimo 16 caracteres e é usado somente pelo cron da
Vercel. A limpeza roda a cada 10 minutos em produção; o mesmo endpoint aceita
execução manual com `X-MAINTENANCE-KEY`.

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

Para suporte completo, rode [`docs/sql/lgpd_hardening.sql`](docs/sql/lgpd_hardening.sql)
depois do schema original. Ele cria organizacoes, credenciais, auditoria,
colunas de isolamento e indices de limpeza. O bucket `payload-pdfs` deve ser
privado; a API tenta cria-lo automaticamente no primeiro upload.

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
- Schema Index-Index: `docs/indexindex_payload_schema.json`
- Exemplo Index-Index: `examples/indexindex_payload_sample.json`

## Exemplos

Criar payload:

```bash
curl -X POST http://127.0.0.1:8000/api/payloads \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: ${SYSTEM_A_API_KEY}" \
  -d '{"source":"sistema-a","schema_version":"1.0","entity":"clinical_report","records":[{"id":"atendimento-ABC-999","title":"Atendimento ABC-999","sender":"sistema-a","recipient":"RehabEasy","created_at":"2026-05-19T10:00:00Z","summary":"Registro para importacao","content":"Paciente sincronizado pela API.","tags":["rehabeasy"]}]}'
```

Consumir payload:

```bash
curl http://127.0.0.1:8000/api/payloads/payload_ID \
  -H "X-API-KEY: ${SYSTEM_B_API_KEY}"
```

Consumir automaticamente o proximo payload pendente:

```bash
curl http://127.0.0.1:8000/api/payloads/next \
  -H "X-API-KEY: ${SYSTEM_B_API_KEY}"
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

Para simular o envio de um relatorio de equilibrio (posturografia VR):

```bash
python scripts/send_equilibrio_payload.py \
  --base-url https://telemedicinacc.vercel.app \
  --system-a-key SUA_SYSTEM_A_API_KEY
```

Para enviar um PDF real (CvTUG, equilibrio ou Index-Index):

```bash
python scripts/send_pdf_payload.py "C:/caminho/relatorio.pdf" \
  --base-url https://telemedicinacc.vercel.app \
  --system-a-key SUA_SYSTEM_A_API_KEY
```

Com o RehabEasy aberto, clique em `Atualizar`. O RehabEasy sera o Sistema B, buscara automaticamente o proximo payload pendente e consumira esse payload uma unica vez.

Arquivos de referencia:

- Schema padrao CvTUG: `docs/cvtug_payload_schema.json`
- Exemplo padrao CvTUG: `examples/cvtug_payload_sample.json`
- Extrator CvTUG PDF -> JSON: `scripts/extract_cvtug_pdf.py`
- Schema equilibrio: `docs/equilibrio_payload_schema.json`
- Exemplo equilibrio: `examples/equilibrio_payload_sample.json`
- Extrator equilibrio PDF -> JSON: `scripts/extract_equilibrio_pdf.py`
- Envio equilibrio: `scripts/send_equilibrio_payload.py`
- Extrator Index-Index PDF -> JSON: `scripts/extract_indexindex_pdf.py`

Para extrair um payload estruturado diretamente de um PDF do CvTUG:

```bash
python scripts/extract_cvtug_pdf.py "C:/caminho/CvTUG_Report.pdf" --output cvtug_payload.json
```

Para extrair um payload de equilibrio a partir do PDF:

```bash
python scripts/extract_equilibrio_pdf.py "C:/caminho/relatorio_equilibrio.pdf" --output equilibrio_payload.json
```

Para extrair um payload de Index-Index a partir do PDF:

```bash
python scripts/extract_indexindex_pdf.py "C:/caminho/IndexIndex_Report.pdf" --output indexindex_payload.json
```
