# 06 - Changelog

## 2026-07-01

- Migrado o Kanban da TI para usar chamados reais do banco, agrupados por status, removendo todo o dado mockado/fixo.
- Removidos os 9 chamados-fixture do banco (e os registros de atendimento vinculados) apos backup.
- Definidas as colunas do Kanban pelos status do model: Aberto, Em atendimento, Aguardando, Resolvido e Fechado.
- Criado o endpoint `POST /chamados/status/atualizar/` para alterar o status via drag-and-drop, com login, permissao de TI e CSRF.
- Restringido o acesso ao Kanban a administrador e Atendente TI; usuario comum e redirecionado ao portal.
- Cards do Kanban agora exibem numero, titulo, solicitante, data de abertura e status; clique abre o detalhe.
- Simplificada a abertura de chamado pelo usuario comum para apenas titulo, descricao e anexos.
- Criado o modelo `ChamadoAnexo` para vincular arquivos ao chamado, sem restricao de tamanho ou extensao.
- Adicionado suporte a upload de multiplos arquivos com `multipart/form-data`.
- Configurados `MEDIA_URL` e `MEDIA_ROOT` e o servico de media em desenvolvimento.
- Criado o portal do solicitante (visao do usuario comum) com as telas de abertura, listagem e detalhe de chamados.
- Adicionado o vinculo `solicitante` no modelo `Chamado` para associar o chamado ao usuario que o abriu.
- Definidos choices de `status` e `prioridade` no `Chamado`, com status default `aberto` e campo `fechado_em`.
- Criado o gerador de numero sequencial unico `CH-000123` para chamados abertos pelo portal.
- Adicionado o helper de permissao `is_common_user`.
- Implementado o roteamento pos-login por perfil: TI vai para o Kanban e usuario comum para `/meus-chamados/`.
- Adicionada a validacao de acesso para que o usuario comum veja apenas os proprios chamados.
- Criado o CSS `portal.css` e o sidebar reutilizavel do portal do solicitante.

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
- Criada a tela `/historico/` com busca dinamica de atendimentos e recorte por permissao.

## Convencao de registro

- Registrar aqui mudancas relevantes de produto, arquitetura e comportamento.
- Preferir entradas curtas, objetivas e datadas.
