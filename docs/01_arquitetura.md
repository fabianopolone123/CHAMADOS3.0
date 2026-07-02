# 01 - Arquitetura

## Visao macro

Aplicacao web monolitica em Django, com renderizacao server-side por templates e autenticacao corporativa via Active Directory/LDAP.

## Componentes atuais

- `chamados_ti`: configuracao principal do projeto
- `core`: app responsavel pela autenticacao, rotas principais, Kanban, portal do solicitante, permissoes, historico e modulo Contratos
- `templates/core`: templates da autenticacao e de permissoes
- `templates/chamados`: templates do Kanban, do portal do solicitante e do historico
- `templates/partials`: componentes reutilizaveis (menus laterais, modais e notificacoes)
- `static/css`: estilos visuais separados por contexto (inclui `sidebar.css` como fonte unica do menu lateral)
- `static/js`: scripts do front-end (`chamados.js` do Kanban, `contratos.js` do modulo Contratos e `notifications.js` dos toasts)
- `.env`: configuracao sensivel de ambiente, fora de versionamento

## Estrutura atual do fluxo autenticado

- A tela `/login/` recebe usuario e senha
- A view chama `django.contrib.auth.authenticate()`
- O Django delega ao backend `core.auth_backend.ActiveDirectoryBackend`
- O backend consulta o Active Directory via `ldap3`
- Em caso de sucesso, o usuario local e sincronizado e a sessao Django e aberta
- O usuario e redirecionado para `/chamados/`

## Estrutura atual do quadro Kanban

- A rota `/chamados/` e protegida pelo decorator `ti_required` (administrador e Atendente TI; usuario comum e redirecionado ao portal)
- A view monta o quadro a partir dos chamados reais do banco (model `Chamado`), agrupados em coluna de abertos, colunas por Atendente TI e coluna de fechados
- O template usa `SortableJS` via CDN para o drag-and-drop, controlado por `static/js/chamados.js`
- A movimentacao persiste no backend via `POST /chamados/mover/`, atualizando `status` e `atendente_atual` e registrando eventos em `ChamadoEvento`
- O front-end atualiza badge de status, atendente do card, contadores e mensagens de coluna vazia na hora, sem refresh; falhas no POST revertem a movimentacao visual
- O titulo da coluna "Chamados fechados" abre um modal de consulta (lista + pesquisa e detalhe completo) alimentado por dois endpoints somente-leitura (`GET /chamados/fechados/buscar/` e `GET /chamados/fechados/<numero>/`), com pesquisa dinamica (debounce) e recorte de permissao TI/admin validado no backend

## Tecnologias base

- Python
- Django
- SQLite em desenvolvimento local
- ldap3 para autenticacao LDAP
- Bootstrap via CDN
- SortableJS via CDN
- CSS proprio para refinamento visual

## Observacoes de infraestrutura

- O certificado definido em `AD_LDAP_CA_CERT_FILE` deve existir no ambiente em execucao
- Em Linux ou Docker, um caminho Windows pode precisar ser montado ou convertido para `/mnt/<drive>/...`
