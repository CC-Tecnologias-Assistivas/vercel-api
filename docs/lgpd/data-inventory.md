# Inventário e fluxo de dados

| Grupo | Exemplos | Finalidade | Local | Acesso | Retenção inicial |
|---|---|---|---|---|---|
| Identificação operacional | `payload.id`, `record.id`, `source`, `organization_id` | Entregar e rastrear a transferência | Supabase/Postgres | Serviço autenticado e equipe autorizada | Até limpeza da fila; metadados mínimos de auditoria depois |
| Referência do paciente | `patient.external_id` pseudonimizado e índice HMAC local | Associar exames sem expor o identificador em claro | Payload sanitizado e SQLite local | Organização correspondente; usuário autorizado no dispositivo | Fila conforme TTL; histórico conforme política aprovada |
| Dados clínicos | resumo, conteúdo, métricas e flags dos exames | Visualização e continuidade do cuidado | Supabase temporário e SQLite local cifrado | Publicador/consumidor da mesma organização | Fila conforme TTL; local sem expurgo automático enquanto configuração for 0 |
| Documento | PDF do exame | Visualizar o exame associado | Storage privado e disco local cifrado | URL assinada ou viewer local temporário | Fila conforme TTL; arquivo local conforme política aprovada |
| Segurança/auditoria | ação, resultado, horário, request ID, organização e credencial | Rastreabilidade e investigação | `audit_events` | Administrador autorizado | Prazo mínimo definido pelo controlador |

Campos desconhecidos, documentos auxiliares e conteúdo arbitrário fora do
schema não devem ser persistidos. Logs de aplicação não recebem payload,
PDF, nome, identificador de paciente ou token.

## Responsabilidades

| Papel | Responsável | Decisão pendente |
|---|---|---|
| Controlador | `<organização responsável pelo atendimento>` | Confirmar finalidade, base legal, transparência e canal |
| Operador de infraestrutura | `<Vercel/Supabase conforme contrato>` | Confirmar escopo, região, suboperadores e DPA |
| Encarregado | `<nome e contato>` | Publicar canal e fluxo de atendimento |
| Segurança/atendimento | `<responsável interno>` | Acompanhar acessos, incidentes, limpeza e solicitações |
