# 04 - Rotas

## Rotas atuais

| Rota | Metodo | Descricao | Status |
|---|---|---|---|
| `/` | GET | Redireciona para login ou quadro de chamados conforme a sessao | Implementada |
| `/login/` | GET, POST | Tela de login com autenticacao AD/LDAP | Implementada |
| `/chamados/` | GET | Painel inicial Kanban para Atendente TI | Implementada |
| `/chamados/atendimento/iniciar/` | POST | Inicia um periodo de atendimento para o usuario logado | Implementada |
| `/chamados/atendimento/encerrar/` | POST | Pausa ou finaliza o atendimento ativo com descricao obrigatoria | Implementada |
| `/dashboard/` | GET | Redirecionamento de compatibilidade para `/chamados/` | Implementada |
| `/permissoes/` | GET | Gestao inicial de grupos e perfis | Implementada |
| `/permissoes/<user_id>/toggle-atendente/` | POST | Adiciona ou remove o grupo `Atendente TI` | Implementada |
| `/logout/` | GET | Encerra a sessao do usuario | Implementada |
| `/admin/` | GET | Admin padrao do Django | Disponivel |

## Regras das rotas de atendimento

- As rotas de atendimento exigem `login_required`.
- O backend valida que o usuario nao pode iniciar dois atendimentos ativos ao mesmo tempo.
- O backend valida que `pause` e `stop` exigem descricao obrigatoria.
- As respostas dessas rotas sao em `JsonResponse` para consumo do JavaScript do Kanban.

## Rotas previstas

| Rota | Metodo | Descricao | Status |
|---|---|---|---|
| `/chamados/novo/` | GET, POST | Abertura de chamado | Planejada |
| `/chamados/<id>/` | GET | Detalhe completo de chamado | Planejada |
| `/chamados/<id>/editar/` | GET, POST | Edicao de chamado | Planejada |
| `/meus-chamados/` | GET | Visao do usuario comum | Planejada |
| `/atendimentos/` | GET | Tela futura de consulta do historico de atendimento | Planejada |

## Observacoes

- Novas rotas devem ser documentadas imediatamente apos a implementacao.
- Mudancas de comportamento em rotas existentes tambem devem ser refletidas aqui.
