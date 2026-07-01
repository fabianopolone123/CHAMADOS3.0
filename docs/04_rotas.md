# 04 - Rotas

## Rotas atuais

| Rota | Metodo | Descricao | Status |
|---|---|---|---|
| `/` | GET | Redireciona para login ou landing conforme a sessao e o perfil | Implementada |
| `/login/` | GET, POST | Tela de login com autenticacao AD/LDAP; roteia por perfil apos autenticar | Implementada |
| `/chamados/` | GET | Painel inicial Kanban para Atendente TI | Implementada |
| `/chamados/atendimento/iniciar/` | POST | Inicia um periodo de atendimento para o usuario logado | Implementada |
| `/chamados/atendimento/encerrar/` | POST | Pausa ou finaliza o atendimento ativo com descricao obrigatoria | Implementada |
| `/meus-chamados/` | GET | Portal do solicitante: lista os chamados do proprio usuario | Implementada |
| `/meus-chamados/novo/` | GET, POST | Abertura de chamado pelo usuario comum | Implementada |
| `/meus-chamados/<numero>/` | GET | Detalhe read-only do chamado com timeline de atendimentos | Implementada |
| `/historico/` | GET | Tela de consulta do historico de atendimentos | Implementada |
| `/historico/buscar/` | GET | Busca dinamica no historico com recorte por permissao | Implementada |
| `/dashboard/` | GET | Redirecionamento por perfil (Kanban para TI, portal para usuario comum) | Implementada |
| `/permissoes/` | GET | Gestao inicial de grupos e perfis | Implementada |
| `/permissoes/<user_id>/toggle-atendente/` | POST | Adiciona ou remove o grupo `Atendente TI` | Implementada |
| `/logout/` | GET | Encerra a sessao do usuario | Implementada |
| `/admin/` | GET | Admin padrao do Django | Disponivel |

## Regras das rotas de atendimento

- As rotas de atendimento exigem `login_required`.
- O backend valida que o usuario nao pode iniciar dois atendimentos ativos ao mesmo tempo.
- O backend valida que `pause` e `stop` exigem descricao obrigatoria.
- As respostas dessas rotas sao em `JsonResponse` para consumo do JavaScript do Kanban.

## Regras das rotas de historico

- As rotas de historico exigem `login_required`.
- Administrador pode visualizar todos os registros.
- Atendente TI visualiza apenas os proprios registros.
- A busca dinamica aceita o parametro `q` e consulta chamado, atendente, descricao, tipo e data.

## Regras das rotas do portal do solicitante

- As rotas do portal exigem `login_required`.
- Apos o login, admin e Atendente TI sao roteados para o Kanban (`/chamados/`); os demais usuarios vao para `/meus-chamados/`.
- O usuario comum ve e acessa apenas os chamados em que e o `solicitante`.
- Admin e Atendente TI podem abrir o detalhe de qualquer chamado pela mesma rota.
- A abertura gera numero unico no formato `CH-000123` e grava o usuario logado como solicitante.

## Rotas previstas

| Rota | Metodo | Descricao | Status |
|---|---|---|---|
| `/meus-chamados/<numero>/editar/` | GET, POST | Edicao/complemento do chamado pelo solicitante | Planejada |
| `/chamados/<numero>/` | GET | Detalhe completo de chamado na visao de atendimento | Planejada |
| `/atendimentos/` | GET | Tela futura de consolidacao avancada do historico de atendimento | Planejada |

## Observacoes

- Novas rotas devem ser documentadas imediatamente apos a implementacao.
- Mudancas de comportamento em rotas existentes tambem devem ser refletidas aqui.
