# Controles LGPD do RehabEasy

Este conjunto de documentos descreve os controles técnicos e operacionais da
pipeline. O ambiente atual não contém dados reais de pacientes e permanece
bloqueado para uso clínico até o checklist de liberação ser aprovado.

## Estado de liberação

- Fixtures e PDFs de teste devem ser sintéticos.
- As credenciais antigas e chaves de exemplo não são aceitas.
- O schema `docs/sql/lgpd_hardening.sql` deve ser aplicado no Supabase antes
  do staging.
- A credencial de cada organização é criada, distribuída e revogada pelo
  comando `scripts/manage_credentials.py`.
- `LOCAL_CLINICAL_RETENTION_DAYS=0` mantém o histórico clínico local sem
  expurgo automático. Alterar esse valor exige política aprovada e registro
  de decisão.

## Documentos

- [Inventário e fluxo de dados](data-inventory.md)
- [Retenção e eliminação](retention.md)
- [Direitos do titular e canal de privacidade](rights-and-privacy.md)
- [Resposta a incidentes](incident-response.md)
- [Revisão de fornecedores e transferências](vendor-review.md)
- [Checklist de liberação](release-checklist.md)

Os documentos são modelos operacionais: responsáveis, prazos internos,
canal de privacidade, bases legais e contratos devem ser preenchidos pelo
controlador com o encarregado e a assessoria jurídica.

Referências oficiais: [LGPD compilada](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm),
[direitos dos titulares da ANPD](https://www.gov.br/anpd/pt-br/assuntos/titular-de-dados-1/direito-dos-titulares),
[Resolução ANPD nº 19/2024](https://www.gov.br/anpd/pt-br/assuntos/assuntos-internacionais/transferencia-internacional-de-dados)
e [comunicação de incidentes da ANPD](https://www.gov.br/anpd/pt-br/canais_atendimento/agente-de-tratamento/comunicado-de-incidente-de-seguranca-cis).
