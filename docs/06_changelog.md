# 06 - Changelog

## 2026-06-30

- Criada a base inicial do projeto Django.
- Implementada a tela visual de login.
- Criada a rota `/login/`.
- Criado redirecionamento da raiz `/` para login.
- Integrada autenticacao Active Directory/LDAP usando backend customizado.
- Configurado carregamento de variaveis LDAP a partir do `.env`.
- Implementado o fluxo autenticado com redirecionamento para `/chamados/`.
- Criado painel inicial Kanban para Atendente TI com dados mockados.
- Adicionado drag-and-drop visual com SortableJS.
- Mantido `TODO` explicito para futura persistencia da movimentacao no backend.
- Adicionados grupos `Administrador` e `Atendente TI` para controle inicial de acesso.
- Criada a tela `/permissoes/` para administradores.
- Definido `fabiano.polone` como administrador principal automatico.
- Criado componente global de notificacoes toast com animacao, fechamento manual e auto-dismiss.
- Criado modal global de detalhes do chamado no Kanban com dados mockados.
- Organizado o carregamento seguro dos dados do modal via `json_script` no template.
- Criados os modelos `Chamado` e `AtendimentoHistorico` para iniciar a persistencia do tempo de atendimento.
- Implementados os endpoints JSON para iniciar, pausar e finalizar periodos de atendimento.
- Adicionados Play, Pause, Stop e contador visual de atendimento nos cards do Kanban.
- Definida regra de processo para sempre registrar alteracoes com commit descritivo e push ao remoto.

## Convencao de registro

- Registrar aqui mudancas relevantes de produto, arquitetura e comportamento.
- Preferir entradas curtas, objetivas e datadas.
