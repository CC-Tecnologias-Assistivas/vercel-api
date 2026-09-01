# Retenção e eliminação

## Fila temporária

- `PAYLOAD_TTL_SECONDS` inicia em 1.800 segundos.
- Payload consumido fica em janela de segurança de 30 minutos por
  `CONSUMED_PAYLOAD_GRACE_SECONDS`.
- A rotina protegida `GET/POST /api/internal/maintenance/purge` remove payloads
  expirados, payloads consumidos fora da janela e PDFs correspondentes.
- O `vercel.json` agenda essa rotina a cada 10 minutos. A Vercel envia
  `Authorization: Bearer <CRON_SECRET>`; a execução manual usa
  `X-MAINTENANCE-KEY`.
- A rotina pode ser executada repetidamente: remoção de linha e arquivo são
  tratadas de forma idempotente; PDFs órfãos também são removidos.
- Depois da remoção, a auditoria guarda apenas metadados mínimos da operação.

## Histórico local

`LOCAL_CLINICAL_RETENTION_DAYS=0` significa que o aplicativo não apaga
automaticamente registros clínicos, prontuários ou histórico. Quando o
controlador aprovar uma política, o valor pode ser definido positivamente e a
rotina administrativa local deve ser executada com registro de escopo,
responsável e resultado.

Qualquer exceção legal, bloqueio, preservação para investigação ou pedido do
titular deve suspender a eliminação correspondente e ser documentado.
