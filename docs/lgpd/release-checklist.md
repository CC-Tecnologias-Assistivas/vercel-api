# Checklist de liberação para dados reais

O estado padrão é **BLOQUEADO**. Marcar cada item com responsável, data e
evidência antes de liberar produção.

## Técnico

- [ ] `docs/sql/lgpd_hardening.sql` aplicado no projeto correto.
- [ ] Não existem linhas sem `organization_id`/credencial; a migração antiga
      foi revisada.
- [ ] Bucket de PDFs está privado.
- [ ] `SUPABASE_SERVICE_ROLE_KEY`, `CREDENTIAL_HASH_PEPPER`,
      `PATIENT_PSEUDONYMIZATION_KEY`, `MAINTENANCE_KEY` e `CRON_SECRET` foram
      definidos somente na Vercel/gerenciador de segredos.
- [ ] Credencial publisher e consumer foram criadas por organização e testadas;
      as chaves anteriores foram revogadas.
- [ ] Testes de isolamento A/B, expiração, revogação, limpeza e PDF foram
      executados em staging.
- [ ] Instalação Windows piloto validou DPAPI, ACL, criptografia SQLite/PDF,
      migração de base antiga e limpeza de arquivo temporário.
- [ ] `dotnet build` e `mvn test` passaram no commit candidato.

## Operacional

- [ ] Inventário, matriz controlador/operador e responsáveis preenchidos.
- [ ] Política de retenção aprovada; enquanto não houver aprovação,
      `LOCAL_CLINICAL_RETENTION_DAYS=0` permanece configurado.
- [ ] Canal de privacidade e encarregado publicados.
- [ ] Procedimento de atendimento, exportação, correção, bloqueio e eliminação
      testado com fixture sintética.
- [ ] Plano de incidentes e contatos de plantão testados.

## Jurídico/fornecedores

- [ ] Finalidades e bases legais revisadas pelo controlador.
- [ ] Contratos/DPA, suboperadores e região da Vercel/Supabase registrados.
- [ ] Transferência internacional analisada conforme a Resolução ANPD nº
      19/2024.
- [ ] Critérios de comunicação à ANPD e aos titulares aprovados.

Somente após todos os itens críticos acima estarem evidenciados o bloqueio
pode ser removido. O código não substitui a decisão do controlador, do
encarregado ou da assessoria jurídica.
