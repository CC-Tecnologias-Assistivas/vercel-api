# Direitos do titular e canal de privacidade

Preencher antes da liberação:

- Canal de privacidade: `<e-mail/portal/telefone>`
- Encarregado: `<nome e contato>`
- Controlador responsável: `<nome jurídico>`
- Prazo operacional de triagem: `<prazo aprovado>`

## Procedimento

1. Registrar a solicitação sem colocar dados clínicos no log de aplicação.
2. Confirmar a identidade por procedimento aprovado pelo controlador.
3. Localizar a organização responsável usando a referência autorizada do
   titular; o índice HMAC local não deve ser exportado como identificador.
4. Exportar os dados em formato seguro, corrigir campos quando cabível,
   bloquear processamento ou eliminar registros conforme a decisão documentada.
5. Verificar a fila temporária, registros locais, PDFs, prontuário e histórico.
6. Registrar somente a ação, resultado, responsável, horário e request ID.
7. Responder pelo canal definido e guardar a evidência mínima necessária.

Pedidos de acesso, correção, eliminação, informação sobre compartilhamento e
oposição devem ser avaliados pelo controlador/encarregado conforme a LGPD e
eventuais obrigações de guarda clínica. O código fornece isolamento,
exportação/remoção em nível de armazenamento e auditoria mínima; a decisão
jurídica e a comunicação ao titular são administrativas.
