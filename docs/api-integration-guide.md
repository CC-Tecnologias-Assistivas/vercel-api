# Guia de Integracao da RehabEasy Transfer API

Este documento mostra como conectar um terceiro sistema a API que publica payloads para o RehabEasy.

## Visao geral

Fluxo esperado:

1. O sistema de origem monta um JSON.
2. O sistema de origem envia esse JSON para `POST /api/payloads`.
3. A API salva o payload no Supabase com TTL.
4. O RehabEasy ou outro Sistema B consome uma unica vez com `GET /api/payloads/{id}` ou `GET /api/payloads/next`.

## Autenticacao

- Header obrigatorio: `X-API-KEY`
- `SYSTEM_A_API_KEY`: chave para publicar payloads
- `SYSTEM_B_API_KEY`: chave para consumir payloads

Nao reutilize a chave do Sistema B no sistema publicador.

Padrao sugerido:

- `SYSTEM_A_API_KEY=sistema-mobile`
- `SYSTEM_B_API_KEY=rehabeasy-sistema`

Essa troca nao exige migration no Supabase porque as chaves nao ficam no banco. A mudanca e apenas de configuracao.

## Contrato recomendado

A API aceita qualquer JSON valido no corpo, mas o formato recomendado para integracoes novas e:

```json
{
  "source": "nome-do-sistema",
  "schema_version": "1.0",
  "entity": "clinical_report",
  "records": [
    {
      "id": "registro-001",
      "title": "Titulo do registro",
      "sender": "Sistema Origem",
      "recipient": "RehabEasy",
      "created_at": "2026-06-09T12:00:00Z",
      "summary": "Resumo curto",
      "content": "Conteudo completo em texto",
      "tags": ["tag-a", "tag-b"]
    }
  ]
}
```

Campos recomendados:

- `source`: identifica o sistema de origem.
- `schema_version`: facilita evolucao de contrato.
- `entity`: classifica o tipo de dado enviado.
- `records`: lista de registros transportados no mesmo payload.
- `records[].id`: ID estavel do registro no sistema de origem.
- `records[].created_at`: usar ISO 8601 com timezone.
- `records[].summary`: texto curto para listagem.
- `records[].content`: texto completo do registro.

Para payloads do CvTUG:

- Use `content` como interpretacao curta legivel por humano.
- Guarde estatisticas em `assessment.conditions`, `assessment.derived_metrics` e `assessment.automated_flags`.
- Nao inclua `source_document`, `references` ou citacoes academicas no payload padrao.
- Se houver necessidade de auditoria, trate isso como extensao interna do sistema de origem, nao como parte do modelo padrao.

Arquivos de apoio:

- Schema generico recomendado: [docs/recommended_payload_schema.json](/C:/Users/Chari/dev/CC/vercel-api/docs/recommended_payload_schema.json)
- Exemplo generico: [examples/generic_payload_sample.json](/C:/Users/Chari/dev/CC/vercel-api/examples/generic_payload_sample.json)
- Schema CvTUG: [docs/cvtug_payload_schema.json](/C:/Users/Chari/dev/CC/vercel-api/docs/cvtug_payload_schema.json)
- Exemplo CvTUG: [examples/cvtug_payload_sample.json](/C:/Users/Chari/dev/CC/vercel-api/examples/cvtug_payload_sample.json)
- Extrator CvTUG PDF -> JSON: [scripts/extract_cvtug_pdf.py](/C:/Users/Chari/dev/CC/vercel-api/scripts/extract_cvtug_pdf.py)

## Publicacao do payload

Exemplo com `curl`:

```bash
curl -X POST https://telemedicinacc.vercel.app/api/payloads \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: SUA_SYSTEM_A_API_KEY" \
  -d @examples/generic_payload_sample.json
```

Resposta esperada:

```json
{
  "id": "payload_...",
  "expires_in_seconds": 1800,
  "expires_in_minutes": 30
}
```

Guarde o `id` retornado se o sistema precisar rastrear o payload depois.

## Consulta de status

Se o consumidor quiser confirmar se o payload ainda existe antes de ler:

```bash
curl https://telemedicinacc.vercel.app/api/payloads/payload_ID/status \
  -H "X-API-KEY: SUA_SYSTEM_B_API_KEY"
```

## Consumo do payload

Consumir um payload conhecido:

```bash
curl https://telemedicinacc.vercel.app/api/payloads/payload_ID \
  -H "X-API-KEY: SUA_SYSTEM_B_API_KEY"
```

Consumir o proximo pendente:

```bash
curl https://telemedicinacc.vercel.app/api/payloads/next \
  -H "X-API-KEY: SUA_SYSTEM_B_API_KEY"
```

Importante:

- Leitura bem-sucedida consome o payload.
- Segunda leitura do mesmo `id` retorna `404`.
- Payload expirado tambem retorna `404`.

## Exemplo em JavaScript

```js
const payload = {
  source: "sistema-origem",
  schema_version: "1.0",
  entity: "clinical_report",
  records: [
    {
      id: "registro-001",
      title: "Titulo do registro",
      sender: "Sistema Origem",
      recipient: "RehabEasy",
      created_at: new Date().toISOString(),
      summary: "Resumo curto",
      content: "Conteudo completo",
      tags: ["api", "rehabeasy"]
    }
  ]
};

const response = await fetch("https://telemedicinacc.vercel.app/api/payloads", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-API-KEY": process.env.SYSTEM_A_API_KEY
  },
  body: JSON.stringify(payload)
});

if (!response.ok) {
  throw new Error(`Falha ao publicar payload: ${response.status} ${await response.text()}`);
}

const created = await response.json();
console.log(created.id);
```

## Checklist para novos integradores

- Usar `application/json`.
- Enviar `X-API-KEY` correto.
- Incluir `source`, `schema_version` e `records`.
- Garantir `records[].id` estavel no sistema de origem.
- Usar datas em ISO 8601 com timezone.
- Tratar `404` como payload expirado, consumido ou inexistente.
- Tratar `413` como payload acima do limite.
- Tratar `503` como indisponibilidade do Supabase.
