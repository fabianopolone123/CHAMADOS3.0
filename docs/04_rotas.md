# 04 - Rotas

## Rotas atuais

| Rota | Metodo | Descricao | Status |
|---|---|---|---|
| `/` | GET | Redireciona para login ou landing conforme a sessao e o perfil | Implementada |
| `/login/` | GET, POST | Tela de login com autenticacao AD/LDAP; roteia por perfil apos autenticar | Implementada |
| `/chamados/` | GET | Kanban por atendente: coluna de abertos, colunas por Atendente TI e coluna de fechados (apenas TI/admin) | Implementada |
| `/chamados/atendimento/iniciar/` | POST | Inicia um periodo de atendimento para o usuario logado | Implementada |
| `/chamados/atendimento/encerrar/` | POST | Pausa ou finaliza (Stop) o atendimento; o Stop encerra o chamado e o move para "Chamados fechados" (apenas TI/admin) | Implementada |
| `/chamados/mover/` | POST | Movimenta um chamado no Kanban (aberto/atendente/fechado); apenas TI/admin | Implementada |
| `/chamados/criar/` | POST | Cria um chamado pelo Kanban (modal), com o atendente logado como solicitante; apenas TI/admin | Implementada |
| `/meus-chamados/` | GET | Portal do solicitante: lista os chamados do proprio usuario | Implementada |
| `/meus-chamados/novo/` | GET, POST | Abertura de chamado pelo usuario comum | Implementada |
| `/meus-chamados/<numero>/` | GET | Detalhe do chamado com conversa, anexos, historico tecnico (recolhido) e timeline de atendimentos | Implementada |
| `/meus-chamados/<numero>/mensagens/` | POST | Envia uma mensagem na conversa do chamado, com anexos opcionais | Implementada |
| `/meus-chamados/<numero>/anexo/<anexo_id>/` | GET | Download protegido de anexo do chamado (solicitante ou TI/admin) | Implementada |
| `/meus-chamados/<numero>/mensagens/anexo/<anexo_id>/` | GET | Download protegido de anexo de mensagem (solicitante ou TI/admin) | Implementada |
| `/historico/` | GET | Tela de consulta do historico de atendimentos | Implementada |
| `/historico/buscar/` | GET | Busca dinamica no historico com recorte por permissao | Implementada |
| `/dashboard/` | GET | Redirecionamento por perfil (Kanban para TI, portal para usuario comum) | Implementada |
| `/permissoes/` | GET | Gestao inicial de grupos e perfis | Implementada |
| `/permissoes/<user_id>/toggle-atendente/` | POST | Adiciona ou remove o grupo `Atendente TI` | Implementada |
| `/logout/` | GET | Encerra a sessao do usuario | Implementada |
| `/admin/` | GET | Admin padrao do Django | Disponivel |

## Regras das rotas de atendimento

- As rotas de atendimento exigem `login_required`.
- O encerramento (`/chamados/atendimento/encerrar/`) exige tambem permissao de Atendente TI/Admin; usuario comum recebe `403`.
- O backend valida que o usuario nao pode iniciar dois atendimentos ativos ao mesmo tempo.
- O backend valida que `pause` e `stop` exigem descricao obrigatoria.
- O `stop` encerra o chamado na mesma transacao: status "Fechado", `fechado_em` preenchido, atendente atual = quem encerrou e registro no historico (`ChamadoEvento`: mudanca de status + "Chamado encerrado por X."), sem duplicar eventos.
- A resposta do `stop` inclui `ticket_closed`, `status`, `status_label`, `status_class` e `atendente_atual` para o Kanban mover o card para "Chamados fechados" e atualizar o badge sem refresh.
- As respostas dessas rotas sao em `JsonResponse` para consumo do JavaScript do Kanban.

## Regras do Kanban e da movimentacao de chamados

- `/chamados/` usa o decorator `ti_required`: administrador e Atendente TI acessam; usuario comum e redirecionado para `/meus-chamados/`.
- O Kanban lista chamados reais do banco (model `Chamado`), sem dados mockados.
- Colunas: "Chamados abertos" (fixa) + uma coluna por usuario do grupo `Atendente TI` + "Chamados fechados" (fixa).
- `/chamados/mover/` exige `login_required` e permissao de administrador ou Atendente TI (usuario comum recebe `403` em JSON) e aceita apenas `POST` (GET retorna `405`).
- Recebe em JSON: `ticket_number`, `target` (`aberto`, `atendente` ou `fechado`) e, quando `target=atendente`, `attendant_id`.
- Valida que o `attendant_id` pertence ao grupo `Atendente TI` (caso contrario retorna `400`).
- `target=atendente`: define `atendente_atual` e status "Em atendimento". `target=aberto`: status "Aberto" e limpa `atendente_atual`. `target=fechado`: status "Fechado", preenche `fechado_em` e registra quem fechou.
- O `atendente_atual` e apenas o atendente que agiu por ultimo; nao e dono do chamado.
- Toda movimentacao registra eventos em `ChamadoEvento` (mudanca de status e/ou troca de atendente).
- A resposta JSON retorna `status`, `status_label`, `status_class` e `atendente_atual` para o Kanban atualizar texto e cor do badge e o atendente do card sem recarregar a pagina.
- Usa CSRF via header `X-CSRFToken`.

## Regras da criacao de chamado pelo Kanban

- `/chamados/criar/` exige `login_required` e permissao de administrador ou Atendente TI (usuario comum recebe `403`), aceita apenas `POST` (GET retorna `405`) e usa CSRF.
- Reutiliza o `AberturaChamadoForm` (titulo, descricao e anexos), validando titulo e descricao no backend.
- Salva o chamado com `solicitante` = usuario logado, `status` = "Aberto", `atendente_atual` vazio e `origem` = "Kanban TI".
- Registra o evento de criacao ("Chamado criado manualmente pelo atendente X.") e retorna o HTML do card para insercao imediata na coluna "Chamados abertos" sem refresh.
- O fluxo de criacao do usuario comum (`/meus-chamados/novo/`) permanece inalterado.

## Regras da conversa do chamado

- `/meus-chamados/<numero>/mensagens/` exige `login_required`, aceita apenas `POST` e usa CSRF.
- A permissao de envio reutiliza a regra de acesso ao chamado: solicitante so envia nos proprios chamados; TI/admin enviam em qualquer chamado.
- O formulario usa `enctype="multipart/form-data"` e aceita multiplos anexos opcionais no campo `anexos`.
- Uma mensagem precisa ter texto ou pelo menos um anexo; caso contrario retorna ao detalhe com mensagem de erro.
- Cada envio cria a mensagem (e seus anexos) e registra um evento resumido em `ChamadoEvento` (tipo `comentario`), sem duplicar o texto da conversa.
- Apos o envio, o usuario e redirecionado de volta ao detalhe do chamado com notificacao de sucesso.

## Regras de acesso a anexos

- O download de anexos (do chamado e das mensagens) exige `login_required` e usa rotas dedicadas (nao expoe a URL direta de `MEDIA`).
- Usuario comum so acessa anexos dos chamados que ele mesmo abriu; administrador e Atendente TI acessam anexos de qualquer chamado.
- Acesso nao autorizado retorna `404`.

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
