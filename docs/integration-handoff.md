# Handoff de integração Sistema A -> RehabEasy

Este documento deve ser entregue ao responsável pelo sistema que publica os
exames. A API mantém o contrato atual, mas a autenticação agora usa uma
credencial exclusiva por organização e função.

## 1. Valores que precisam ser configurados

O integrador precisa receber, por canal seguro:

- `API_BASE_URL`: `https://telemedicinacc.vercel.app`
- `SYSTEM_A_API_KEY`: credencial da organização com função `publisher`

O aplicativo RehabEasy precisa de outra credencial, da mesma organização, com
função `consumer`:

- `REHABEASY_API_BASE_URL`: `https://telemedicinacc.vercel.app`
- `REHABEASY_SYSTEM_B_API_KEY`: credencial do RehabEasy

As chaves têm o formato `<key_id>.<secret>`. Não usar as chaves antigas, não
enviar `X-Tenant-ID` e não registrar a chave em logs, código-fonte ou arquivos
versionados.

## 2. Criar as duas credenciais

Depois de aplicar `docs/sql/lgpd_hardening.sql`, configure no ambiente
administrativo `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` e
`CREDENTIAL_HASH_PEPPER` com pelo menos 32 caracteres. Se a organização ainda
não existir, crie-a no SQL Editor:

```sql
insert into public.organizations (id, name)
values ('org-rehabeasy', 'Organizacao RehabEasy');
```

Use o mesmo `id` nos dois comandos abaixo:

```bash
python scripts/manage_credentials.py create \
  --organization-id ORGANIZACAO_ID \
  --role publisher \
  --name sistema-origem
```

Guarde o valor exibido em `X-API-KEY` como `SYSTEM_A_API_KEY`.

```bash
python scripts/manage_credentials.py create \
  --organization-id ORGANIZACAO_ID \
  --role consumer \
  --name rehabeasy
```

Guarde o valor exibido em `X-API-KEY` como
`REHABEASY_SYSTEM_B_API_KEY`. O segredo completo é exibido somente nessa
criação. Entregue-o por um cofre de secrets ou canal seguro, nunca por commit.

## 3. Enviar JSON

O sistema de origem envia JSON para:

```http
POST /api/payloads
Content-Type: application/json
X-API-KEY: <SYSTEM_A_API_KEY>
```

Exemplo:

```bash
curl --fail-with-body -X POST "$API_BASE_URL/api/payloads" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: $SYSTEM_A_API_KEY" \
  --data-binary @payload.json
```

Resposta esperada (`201`):

```json
{
  "id": "payload_...",
  "expires_in_seconds": 1800,
  "expires_in_minutes": 30
}
```

O payload deve seguir um dos contratos documentados para genérico, CvTUG,
equilíbrio ou Index-Index. Campos desconhecidos são descartados e o payload
fora do schema retorna `400` sem ser persistido.

## 4. Enviar PDF — fluxo recomendado

O envio do PDF é uma requisição `multipart/form-data` para:

```http
POST /api/payloads/pdf
X-API-KEY: <SYSTEM_A_API_KEY>
```

O único campo obrigatório do formulário é `file`. Não converter o PDF para
Base64, não colocá-lo dentro de JSON e não definir manualmente o boundary do
multipart.

```bash
curl --fail-with-body -X POST "$API_BASE_URL/api/payloads/pdf" \
  -H "X-API-KEY: $SYSTEM_A_API_KEY" \
  -F "file=@C:/relatorios/exame.pdf;type=application/pdf"
```

Regras do PDF:

- enviar por HTTPS;
- usar extensão `.pdf` e MIME `application/pdf`;
- limite padrão da API: 10 MiB, ajustável por `MAX_PDF_BYTES`;
- o PDF precisa ser CvTUG, equilíbrio ou Index-Index reconhecível pelo extrator;
- não enviar dados auxiliares, documentos extras ou identificadores fora do
  contrato;
- guardar o `id` retornado para rastreamento operacional.

Resposta esperada (`201`):

```json
{
  "id": "payload_...",
  "expires_in_seconds": 1800,
  "expires_in_minutes": 30
}
```

O `POST` não retorna o PDF de volta. A API extrai o JSON, guarda o PDF no
Storage privado e associa ambos ao mesmo `id`. O Sistema B receberá o PDF por
URL assinada temporária no momento do consumo.

Exemplo equivalente em C# para o sistema publicador:

```csharp
using var client = new HttpClient { BaseAddress = new Uri(apiBaseUrl) };
using var form = new MultipartFormDataContent();
await using var stream = File.OpenRead(pdfPath);
using var content = new StreamContent(stream);
content.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("application/pdf");
form.Add(content, "file", Path.GetFileName(pdfPath));

using var request = new HttpRequestMessage(HttpMethod.Post, "api/payloads/pdf");
request.Headers.Add("X-API-KEY", systemAApiKey);
request.Content = form;
using var response = await client.SendAsync(request);
var body = await response.Content.ReadAsStringAsync();
response.EnsureSuccessStatusCode();
```

## 5. Consumir no RehabEasy

O RehabEasy configura `REHABEASY_SYSTEM_B_API_KEY` e chama:

```http
GET /api/payloads/next
X-API-KEY: <REHABEASY_SYSTEM_B_API_KEY>
```

Quando não houver payload pendente, a resposta é `404`. Quando houver, a
resposta contém:

```json
{
  "id": "payload_...",
  "payload": { "...": "..." },
  "consumed": true,
  "pdf_url": "https://...url-assinada-temporaria..."
}
```

O PDF deve ser baixado imediatamente pela `pdf_url`. A URL é temporária; o
cliente C# ou Java salva somente a versão criptografada localmente e exibe o
arquivo por um temporário descriptografado.

Uma leitura bem-sucedida consome o payload. Uma segunda tentativa do mesmo ID
retorna `404`. Não fazer polling agressivo; tratar `404` como fila vazia.

## 6. Tratamento de erros

- `400`: JSON inválido, schema inválido ou PDF não reconhecido; corrigir o
  conteúdo e não repetir indefinidamente;
- `401`: chave ausente, inválida, expirada ou revogada;
- `403`: credencial sem a função necessária;
- `404`: payload expirado, já consumido ou fila vazia;
- `413`: tamanho acima do limite;
- `503`: indisponibilidade do Supabase/API; aplicar retry com backoff apenas
  quando a operação não tiver sido confirmada.

O contrato atual não possui idempotency key. Depois de um timeout no `POST`, o
integrador deve registrar o caso para reconciliação antes de reenviar, pois um
retry cego pode criar dois payloads.

## 7. Checklist antes do primeiro envio

- [ ] credencial `publisher` criada para a organização correta;
- [ ] credencial `consumer` separada criada para o RehabEasy;
- [ ] nenhum `X-Tenant-ID` sendo enviado;
- [ ] PDF sintético de teste com menos de 10 MiB;
- [ ] teste do `POST /api/payloads/pdf` retornando `201`;
- [ ] RehabEasy consumindo `GET /api/payloads/next` com `200`;
- [ ] PDF sendo exibido e armazenado localmente;
- [ ] segunda leitura retornando `404`;
- [ ] secrets fora de logs, commits e mensagens não protegidas.
