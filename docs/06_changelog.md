# 06 - Changelog

## 2026-07-01

- Reorganizado o Kanban para funcionar por fila e por atendente: coluna fixa "Chamados abertos", colunas dinamicas por Atendente TI e coluna fixa "Chamados fechados".
- Substituido o endpoint de status por `POST /chamados/mover/`, que recebe a coluna de destino (aberto/atendente/fechado) e valida o atendente de destino.
- Movimentacao entre colunas atualiza status e `atendente_atual`, registra o historico (puxar, transferir, fechar, devolver) e responde com dados para o badge atualizar sem refresh.
- Simplificado o menu do perfil Atendente TI para apenas "Chamados" e "Permissoes".
- Adicionado o campo `atendente_atual` ao `Chamado` (usuario que realizou a ultima acao; nao e dono do chamado).
- Criado o model `ChamadoEvento` como log de eventos do chamado (criacao, mudanca de status, troca de atendente).
- Ao mover um card no Kanban, o sistema salva status e atendente atual e registra os eventos correspondentes, sem duplicar registros.
- Encerramentos (`resolvido`/`fechado`) preenchem `fechado_em` e mantem o ultimo atendente que agiu.
- Corrigido o badge de status do Kanban para atualizar texto e cor imediatamente no drag (sem refresh).
- Exibidos no detalhe do chamado o atendente atual, o historico de eventos e os anexos (nome, download, data e usuario).
- Criada a rota protegida de download de anexo (dono do chamado ou TI/admin), sem expor a URL direta de MEDIA.
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
