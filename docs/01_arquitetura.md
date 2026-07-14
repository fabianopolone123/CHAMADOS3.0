# 01 - Arquitetura

## Visao macro

Aplicacao web monolitica em Django, com renderizacao server-side por templates e autenticacao corporativa via Active Directory/LDAP.

## Componentes atuais

- `chamados_ti`: configuracao principal do projeto
- `core`: app unico que concentra autenticacao, rotas, Kanban, portal do solicitante, permissoes, historico e todos os modulos de TI. Modulos atuais: Requisicoes (nomes tecnicos internos com prefixo `Contrato`), Insumos, Documentos, Emprestimos (termo em PDF via `core/termo_pdf.py`), Emails, Ramais, Licencas, IPs, Servicos feitos, Contratos (`/contratos-ti/`, distinto de Requisicoes), Futura Digital, Dicas, Starlinks e Cofre (cifra em `core/crypto.py`)
- `core/crypto.py`: cifra simetrica (Fernet) do Cofre de senhas; a chave vem de `VAULT_ENCRYPTION_KEY` (env)
- `templates/core`: templates da autenticacao e de permissoes
- `templates/chamados`: templates das telas autenticadas (Kanban, portal e cada modulo)
- `templates/partials`: componentes reutilizaveis (menus laterais, modais e notificacoes)
- `static/css`: estilos visuais separados por contexto (inclui `sidebar.css` como fonte unica do menu lateral, e um CSS por modulo)
- `static/js`: um script por modulo (ex.: `chamados.js`, `ramais.js`, `ips.js`, `futura_digital.js`, `cofre.js`, etc.) alem de `sidebar.js` (menu responsivo) e `notifications.js` (toasts)
- `seed/`: arquivos locais de seed com dados/credenciais reais, IGNORADOS pelo Git (nao versionados)
- `media/`: uploads e anexos, tambem fora de versionamento
- `.env`: configuracao sensivel de ambiente (inclui `VAULT_ENCRYPTION_KEY`), fora de versionamento

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
- ReportLab para geracao do termo de emprestimo em PDF (sem dependencia nativa)
- Pillow para campos de imagem (`ImageField`)
- cryptography (Fernet) para a cifra das credenciais do Cofre
- CSS proprio para refinamento visual

## Observacoes de infraestrutura

- O certificado definido em `AD_LDAP_CA_CERT_FILE` deve existir no ambiente em execucao
- Em Linux ou Docker, um caminho Windows pode precisar ser montado ou convertido para `/mnt/<drive>/...`
