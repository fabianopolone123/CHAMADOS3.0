# 01 - Arquitetura

## Visao macro

Aplicacao web monolitica em Django, com renderizacao server-side por templates e autenticacao corporativa via Active Directory/LDAP.

## Componentes atuais

- `chamados_ti`: configuracao principal do projeto
- `core`: app responsavel pela autenticacao, rotas principais e quadro inicial
- `templates/core`: templates da autenticacao
- `templates/chamados`: templates da interface inicial de chamados
- `static/css`: estilos visuais separados por contexto
- `.env`: configuracao sensivel de ambiente, fora de versionamento

## Estrutura atual do fluxo autenticado

- A tela `/login/` recebe usuario e senha
- A view chama `django.contrib.auth.authenticate()`
- O Django delega ao backend `core.auth_backend.ActiveDirectoryBackend`
- O backend consulta o Active Directory via `ldap3`
- Em caso de sucesso, o usuario local e sincronizado e a sessao Django e aberta
- O usuario e redirecionado para `/chamados/`

## Estrutura atual do quadro Kanban

- A rota `/chamados/` e protegida com `login_required`
- A view monta dados mockados de atendentes e chamados
- O template usa `SortableJS` via CDN para drag-and-drop visual
- A movimentacao ainda nao persiste no backend

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
