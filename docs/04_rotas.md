# 04 - Rotas

## Rotas atuais

| Rota | Metodo | Descricao | Status |
|---|---|---|---|
| `/` | GET | Redireciona para login ou landing conforme a sessao e o perfil | Implementada |
| `/login/` | GET, POST | Tela de login com autenticacao AD/LDAP; roteia por perfil apos autenticar | Implementada |
| `/chamados/` | GET | Kanban por atendente: coluna de abertos, colunas por Atendente TI e coluna de fechados (apenas TI/admin) | Implementada |
| `/chamados/atendimento/iniciar/` | POST | Inicia (Play) um periodo de atendimento; apenas TI/admin e apenas para chamado em coluna de atendente (bloqueia aberto/encerrado) | Implementada |
| `/chamados/atendimento/encerrar/` | POST | Pausa ou finaliza (Stop) o atendimento; o Stop encerra o chamado e o move para "Chamados fechados" (apenas TI/admin) | Implementada |
| `/chamados/mover/` | POST | Movimenta um chamado no Kanban entre "abertos" e colunas de atendente; o destino "fechado" e recusado (fechamento so via Stop); apenas TI/admin | Implementada |
| `/chamados/criar/` | POST | Cria um chamado pelo Kanban (botao "+" no topo da coluna "Chamados abertos"), com o atendente logado como solicitante; apenas TI/admin | Implementada |
| `/chamados/fechados/buscar/` | GET | Lista/pesquisa (JSON) os chamados encerrados para o modal do Kanban; sem `q` retorna os mais recentes, com `q` filtra por ID, titulo, descricao, solicitante, atendente, mensagens e historico (apenas TI/admin) | Implementada |
| `/chamados/fechados/<numero>/` | GET | Detalhe completo (JSON) de um chamado encerrado para o modal: dados, descricao, conversa, anexos e historico tecnico (apenas TI/admin) | Implementada |
| `/chamados/pendencias/criar/` | POST | Cria uma pendencia na coluna "Pendencias" (apenas TI/admin) | Implementada |
| `/chamados/pendencias/<id>/` | GET | Detalhe (JSON) da pendencia para o modal: titulo, descricao, data e autor (apenas TI/admin) | Implementada |
| `/chamados/pendencias/<id>/converter/` | POST | Converte a pendencia em chamado ao ser arrastada para um atendente (apenas TI/admin) | Implementada |
| `/meus-chamados/` | GET | Portal do solicitante: lista os chamados do proprio usuario | Implementada |
| `/meus-chamados/novo/` | GET, POST | Abertura de chamado pelo usuario comum | Implementada |
| `/meus-chamados/<numero>/` | GET | Detalhe do chamado com conversa, anexos, historico tecnico (recolhido) e timeline de atendimentos | Implementada |
| `/meus-chamados/<numero>/mensagens/` | POST | Envia uma mensagem na conversa do chamado, com anexos opcionais | Implementada |
| `/meus-chamados/<numero>/anexo/<anexo_id>/` | GET | Download protegido de anexo do chamado (solicitante ou TI/admin) | Implementada |
| `/meus-chamados/<numero>/mensagens/anexo/<anexo_id>/` | GET | Download protegido de anexo de mensagem (solicitante ou TI/admin) | Implementada |
| `/contratos/` | GET | Modulo Requisicoes (exibido como "Requisicoes"; rota mantem o prefixo tecnico): lista de requisicoes (titulo + status) e botao "+ Adicionar" (apenas TI/admin) | Implementada |
| `/contratos/requisicoes/criar/` | POST | Cria uma requisicao (titulo, tipo fisica/digital, texto); status inicial "Aberta" (apenas TI/admin) | Implementada |
| `/contratos/requisicoes/<id>/` | GET | Detalhe (JSON) da requisicao com orcamentos, suborcamentos e totais (apenas TI/admin) | Implementada |
| `/contratos/requisicoes/<id>/excluir/` | POST | Exclui a requisicao e, por cascata, orcamentos, suborcamentos e documentos vinculados (apenas TI/admin; POST/CSRF) | Implementada |
| `/contratos/requisicoes/<id>/orcamentos/criar/` | POST | Cria orcamento na requisicao (multipart: campos + foto + documentos) (apenas TI/admin) | Implementada |
| `/contratos/orcamentos/<id>/suborcamentos/criar/` | POST | Cria suborcamento vinculado ao orcamento (multipart) (apenas TI/admin) | Implementada |
| `/contratos/orcamentos/<id>/foto/` | GET | Serve a foto do orcamento (inline, protegida) (apenas TI/admin) | Implementada |
| `/contratos/suborcamentos/<id>/foto/` | GET | Serve a foto do suborcamento (inline, protegida) (apenas TI/admin) | Implementada |
| `/contratos/documentos/orcamento/<id>/` | GET | Download protegido de documento de orcamento (apenas TI/admin) | Implementada |
| `/contratos/documentos/suborcamento/<id>/` | GET | Download protegido de documento de suborcamento (apenas TI/admin) | Implementada |
| `/emprestimos/` | GET | Modulo Emprestimos: lista de emprestimos com botao "+ Adicionar" e acesso a assinaturas (apenas TI/admin) | Implementada |
| `/emprestimos/criar/` | POST | Cria emprestimo com 1+ equipamentos e fotos, valida senha da assinatura e gera o termo PDF (multipart) (apenas TI/admin) | Implementada |
| `/emprestimos/<id>/` | GET | Detalhe (JSON) do emprestimo: dados, equipamentos, fotos, termo e status (apenas TI/admin) | Implementada |
| `/emprestimos/<id>/baixar-termo/` | GET | Download do termo PDF gerado pelo sistema (apenas TI/admin) | Implementada |
| `/emprestimos/<id>/termo-assinado/` | GET | Serve o termo assinado anexado, por rota protegida (apenas TI/admin) | Implementada |
| `/emprestimos/fotos/<id>/` | GET | Serve a foto de um equipamento inline, por rota protegida (apenas TI/admin) | Implementada |
| `/emprestimos/<id>/anexar-termo-assinado/` | POST | Anexa o termo assinado devolvido pelo colaborador (apenas TI/admin) | Implementada |
| `/emprestimos/<id>/marcar-documentacao-ok/` | POST | Marca a documentacao como OK (status "Documentacao assinada / OK") (apenas TI/admin) | Implementada |
| `/emprestimos/assinaturas/` | GET | Lista (JSON) as assinaturas ativas (apenas TI/admin) | Implementada |
| `/emprestimos/assinaturas/criar/` | POST | Cadastra assinatura do responsavel (nome, imagem, senha com hash) (apenas TI/admin) | Implementada |
| `/documentos/` | GET | Modulo Documentos: lista de documentos (nome, observacao, qtd anexos, data, autor) e botao "+ Adicionar" (apenas TI/admin) | Implementada |
| `/documentos/criar/` | POST | Cadastra documento (nome, observacao, anexos multiplos, multipart) (apenas TI/admin) | Implementada |
| `/documentos/<id>/` | GET | Detalhe (JSON) do documento com observacao completa e anexos (apenas TI/admin) | Implementada |
| `/documentos/anexos/<id>/` | GET | Download protegido de anexo de documento (apenas TI/admin) | Implementada |
| `/insumos/` | GET | Modulo Insumos: estoque (cards) e ultimas retiradas, com botao "+ Adicionar" (apenas TI/admin) | Implementada |
| `/insumos/criar/` | POST | Cadastra um insumo (nome, descricao, quantidade inicial, observacao); quantidade obrigatoria e nao negativa (apenas TI/admin) | Implementada |
| `/insumos/<id>/retirar/` | POST | Registra retirada (quantidade, para quem, motivo), valida estoque e abate a quantidade (apenas TI/admin) | Implementada |
| `/emails/` | GET | Modulo Emails: lista das contas de e-mail (tabela responsiva + busca + cards de resumo) e botao "Importar lista" (apenas TI/admin) | Implementada |
| `/emails/importar/` | POST | Importa/atualiza a lista a partir do CSV do Google Workspace (upsert por e-mail), notifica via Django messages e redireciona (apenas TI/admin) | Implementada |
| `/emails/<id>/` | GET | Detalhe (JSON) de uma conta com todos os dados, usado pelo modal (apenas TI/admin) | Implementada |
| `/ramais/` | GET | Modulo Ramais: lista telefonica interna (colaborador, setor, telefone, ramal, e-mail) com busca dinamica e botao "Cadastrar novo" (apenas TI/admin) | Implementada |
| `/ramais/criar/` | POST | Cadastra um ramal; o e-mail pode ser digitado ou vir de uma `ContaEmail` selecionada; notifica via Django messages e redireciona (apenas TI/admin) | Implementada |
| `/ramais/<id>/editar/` | POST | Edita um ramal existente (apenas TI/admin) | Implementada |
| `/ramais/<id>/excluir/` | POST | Exclui um ramal (apenas TI/admin) | Implementada |
| `/historico/` | GET | Tela de consulta do historico de atendimentos | Implementada |
| `/historico/buscar/` | GET | Busca dinamica no historico com recorte por permissao | Implementada |
| `/dashboard/` | GET | Redirecionamento por perfil (Kanban para TI, portal para usuario comum) | Implementada |
| `/permissoes/` | GET | Gestao inicial de grupos e perfis | Implementada |
| `/permissoes/<user_id>/toggle-atendente/` | POST | Adiciona ou remove o grupo `Atendente TI` | Implementada |
| `/logout/` | GET | Encerra a sessao do usuario | Implementada |
| `/admin/` | GET | Admin padrao do Django | Disponivel |

## Regras das rotas de atendimento

- As rotas de atendimento exigem `login_required`.
- O inicio (`/chamados/atendimento/iniciar/`, o "Play") exige permissao de Atendente TI/Admin (usuario comum recebe `403`) e so vale para chamados em uma coluna de atendente: bloqueia com `409` chamado em "Chamados abertos" (sem `atendente_atual`) e chamado encerrado (resolvido/fechado). A regra "coluna de atendente" espelha o quadro: nao encerrado e `atendente_atual` pertencente ao grupo `Atendente TI`. O historico de tempo (`AtendimentoHistorico`) so e criado quando o Play passa em todas as validacoes; acoes bloqueadas nao geram registro. No frontend, o painel Play/Pause/Stop so aparece em cards dentro das colunas de atendente (regra em CSS reagindo ao `data-column-type`), some ao mover o card para abertos/fechados e ha uma checagem extra no clique antes de chamar o endpoint.
- O encerramento (`/chamados/atendimento/encerrar/`, a acao "Stop") exige permissao de Atendente TI/Admin (usuario comum recebe `403`) e e o unico caminho de fechamento de chamado. O backend so encerra quando existe atendimento ativo/Play em andamento do proprio usuario (`409` caso contrario) e com o campo "O que foi feito" preenchido; um chamado ja encerrado nao gera eventos repetidos (idempotente).
- O backend valida que o usuario nao pode iniciar dois atendimentos ativos ao mesmo tempo.
- O backend valida que `pause` e `stop` exigem descricao obrigatoria.
- O `stop` encerra o chamado na mesma transacao: status "Fechado", `fechado_em` preenchido, atendente atual = quem finalizou e registro no historico tecnico (`ChamadoEvento`: mudanca de status + evento de finalizacao com quem finalizou e o texto de "O que foi feito", ex.: "Chamado finalizado por X. O que foi feito: ..."), sem duplicar eventos. Esse texto e registro tecnico, separado da conversa do usuario.
- A resposta do `stop` inclui `ticket_closed`, `status`, `status_label`, `status_class` e `atendente_atual` para o Kanban mover o card para "Chamados fechados" e atualizar o badge sem refresh.
- As respostas dessas rotas sao em `JsonResponse` para consumo do JavaScript do Kanban.

## Regras do Kanban e da movimentacao de chamados

- `/chamados/` usa o decorator `ti_required`: administrador e Atendente TI acessam; usuario comum e redirecionado para `/meus-chamados/`.
- O Kanban lista chamados reais do banco (model `Chamado`), sem dados mockados.
- Colunas: "Chamados abertos" (fixa) + uma coluna por usuario do grupo `Atendente TI` + "Chamados fechados" (fixa).
- `/chamados/mover/` exige `login_required` e permissao de administrador ou Atendente TI (usuario comum recebe `403` em JSON) e aceita apenas `POST` (GET retorna `405`).
- Recebe em JSON: `ticket_number`, `target` (`aberto` ou `atendente`) e, quando `target=atendente`, `attendant_id`.
- O destino `fechado` e recusado com `409` e a mensagem "Para fechar o chamado, inicie o atendimento e finalize usando o botao Stop.": a coluna "Chamados fechados" so recebe chamados via acao Stop. No frontend o drop nessa coluna e cancelado (o card volta para a origem) com a mesma mensagem.
- Valida que o `attendant_id` pertence ao grupo `Atendente TI` (caso contrario retorna `400`).
- `target=atendente`: define `atendente_atual` e status "Em atendimento". `target=aberto`: status "Aberto" e limpa `atendente_atual`.
- O `atendente_atual` e apenas o atendente que agiu por ultimo; nao e dono do chamado.
- Toda movimentacao registra eventos em `ChamadoEvento` (mudanca de status e/ou troca de atendente).
- A resposta JSON retorna `status`, `status_label`, `status_class` e `atendente_atual` para o Kanban atualizar texto e cor do badge e o atendente do card sem recarregar a pagina.
- Usa CSRF via header `X-CSRFToken`.

## Regras da criacao de chamado pelo Kanban

- A acao e acionada pelo botao "+" no topo da coluna "Chamados abertos" (a tela nao tem mais header superior), que abre o modal de criacao.
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

## Regras do modal de chamados fechados

- O titulo "Chamados fechados" da coluna e clicavel e abre um modal com pesquisa e a lista dos chamados encerrados.
- `/chamados/fechados/buscar/` e `/chamados/fechados/<numero>/` exigem `login_required` e permissao de Atendente TI/Admin; usuario comum recebe `403` (validado no backend). O usuario comum continua acessando apenas os proprios chamados pelo fluxo do portal (`/meus-chamados/`).
- A busca (`buscar/`) aceita o parametro `q` e filtra chamados com status encerrado (`resolvido`/`fechado`) por: numero (ID), titulo, descricao, solicitante (nome/username/first/last), atendente atual (username/first/last), texto das mensagens e descricao dos eventos do historico. Sem `q` retorna os encerrados mais recentes. A busca e case-insensitive, aceita partes do texto, usa `distinct()` e limita o resultado a 100 registros; retorna apenas `number` e `title` por item.
- O detalhe (`<numero>/`) so expoe chamados encerrados (senao `404`) e retorna dados completos: numero, titulo, descricao, solicitante, atendente atual, status, data de criacao, data de fechamento (quando existir), anexos, conversa (mensagens com anexos) e historico tecnico (eventos). Os links de download reutilizam as rotas protegidas de anexo.
- No frontend o modal alterna entre lista e detalhe (botao "Voltar") e fecha pelo botao "Fechar"; a pesquisa e dinamica com debounce de ~300ms e requisicoes concorrentes anteriores sao canceladas. O historico tecnico aparece recolhido por padrao.

## Regras das rotas de pendencias

- Todas exigem `login_required` e permissao de Atendente TI/Admin; usuario comum recebe `403` (validado no backend, nao apenas no template).
- `criar/` e `converter/` aceitam apenas `POST` com CSRF (payload JSON); `detail` responde JSON para o modal.
- A criacao valida titulo (minimo de caracteres) e descricao obrigatoria e retorna o HTML do card para insercao imediata na coluna "Pendencias".
- A conversao valida que o `attendant_id` pertence ao grupo `Atendente TI` (senao `400`) e recusa pendencia ja convertida (`409`), evitando chamado duplicado.
- A conversao cria o chamado (titulo/descricao da pendencia, `solicitante` = criador, `atendente_atual` = atendente destino, status "Em atendimento"), marca a pendencia como convertida e registra os eventos no `ChamadoEvento`.
- A resposta da conversao retorna `ticket_number`, `status`, `status_label`, `status_class`, `atendente_atual` e `card_html` para o Kanban montar o card do chamado sem refresh.

## Regras de acesso a anexos

- O download de anexos (do chamado e das mensagens) exige `login_required` e usa rotas dedicadas (nao expoe a URL direta de `MEDIA`).
- Usuario comum so acessa anexos dos chamados que ele mesmo abriu; administrador e Atendente TI acessam anexos de qualquer chamado.
- Acesso nao autorizado retorna `404`.

## Regras do modulo Requisicoes

- Na interface o modulo se chama "Requisicoes"; as rotas (`/contratos/...`), views e models mantem o prefixo tecnico `Contrato` (nao renomeados para evitar migration/quebra). Nao ha mais o termo "Contratos" na interface.
- `/contratos/` usa `ti_required` (admin e Atendente TI acessam; usuario comum e redirecionado). O botao "Requisicoes" no menu lateral so aparece para TI/admin, e todas as rotas do modulo validam a permissao no backend (usuario comum recebe `403` nos endpoints JSON/POST e `404` ao tentar baixar arquivos).
- A criacao de requisicao (`requisicoes/criar/`) aceita `POST` JSON com CSRF: valida titulo (minimo 3 caracteres) e tipo (`fisica`/`digital`); grava `status=aberta`, `criado_por=usuario logado` e datas automaticas; retorna os dados para inserir o item na lista sem refresh.
- O detalhe (`requisicoes/<id>/`) retorna JSON com a requisicao, seus orcamentos e, aninhados, os suborcamentos de cada orcamento, alem dos totais formatados.
- A criacao de orcamento e de suborcamento usa `POST` multipart (`enctype="multipart/form-data"`) com CSRF. Campos: titulo, loja, moeda (`BRL`/`USD`), valor, quantidade, frete, desconto, link, `foto_produto` (imagem) e `documentos` (multiplos, sem restricao de tipo/tamanho no codigo). O backend valida a moeda, exige quantidade >= 1 e bloqueia valores negativos em valor/frete/desconto (mensagens amigaveis). O suborcamento e sempre vinculado ao orcamento pai e nao aparece como orcamento independente.
- Regra de calculo: `total do orcamento = valor*quantidade + frete - desconto`; `total com suborcamentos = total do orcamento + soma dos totais dos suborcamentos`.
- Foto do print: o botao "Tirar print" usa `navigator.mediaDevices.getDisplayMedia` no frontend, desenha o frame em canvas, permite recortar uma regiao e anexa o recorte como `foto_produto`. Se o navegador nao suportar, exibe mensagem e permite anexar imagem manualmente; cancelar a captura nao trava o formulario.
- Fotos e documentos sao servidos por rotas dedicadas e protegidas (nao expoem a URL direta de `MEDIA`); acesso sem permissao retorna `404`.
- A exclusao de requisicao (`requisicoes/<id>/excluir/`) exige `login_required` + permissao TI/admin (usuario comum recebe `403`), aceita apenas `POST` com CSRF (GET retorna `405`) e responde JSON. Remove a requisicao e, por cascata (`on_delete=CASCADE`), seus orcamentos, suborcamentos e os documentos vinculados. No frontend abre uma confirmacao obrigatoria antes de excluir; em caso de sucesso o item some da lista sem refresh. Observacao: os arquivos fisicos em `MEDIA_ROOT` nao sao apagados (pendencia registrada em `docs/05_tarefas.md`).

## Regras do modulo Emprestimos

- `/emprestimos/` usa `ti_required` (admin e Atendente TI; usuario comum e redirecionado). O botao "Emprestimos" no menu lateral so aparece para TI/admin e todas as rotas validam a permissao no backend (usuario comum recebe `403` nos endpoints e `404` no download do termo).
- Um emprestimo pode ter 1 ou varios equipamentos; os dados do colaborador, empresa, assinatura e senha sao preenchidos uma unica vez, e cada equipamento pode ter varias fotos. No formulario, "Adicionar mais um equipamento" gera novos blocos; no PDF os itens aparecem como Equipamento 1, 2, 3...
- A criacao (`criar/`) usa `POST` multipart com CSRF (GET retorna `405`): valida nome do colaborador, data do emprestimo e pelo menos um equipamento. Se a previsao de devolucao ficar em branco, o emprestimo fica com prazo indeterminado (o termo mostra "Indeterminada").
- Assinatura do responsavel: e cadastrada com nome, imagem e senha de autorizacao; a senha e guardada como hash Django (`make_password`), nunca em texto puro. Ao criar o emprestimo, se uma assinatura for selecionada, a senha e obrigatoria e conferida (`check_password`); se estiver correta, a assinatura e aplicada no PDF e o uso e registrado em `LogUsoAssinaturaTI`; se estiver errada, a geracao com assinatura e bloqueada (`403`).
- O termo em PDF e gerado por ReportLab (sem servico externo) espelhando o modelo institucional (cabecalho Sidertec / Departamento de TI, titulo, dados do colaborador, equipamentos, condicoes, responsabilidades, assinaturas, rubrica e data de geracao), fica salvo em `termo_pdf` e pode ser baixado.
- O termo assinado devolvido e anexado por `anexar-termo-assinado/` (registra data e usuario) e, por `marcar-documentacao-ok/`, o status muda para "Documentacao assinada / OK" (exige o termo assinado ja anexado, senao `409`). Status possiveis: Aguardando documentacao assinada (inicial), Documentacao assinada / OK, Em andamento, Devolvido, Cancelado.
- O historico de uso de assinatura nao e apagado.
- As fotos dos equipamentos e o termo assinado sao servidos por rotas protegidas (`/emprestimos/fotos/<id>/` e `/emprestimos/<id>/termo-assinado/`), nao pela URL crua de `MEDIA` (que so e servida com `DEBUG=True`); usuario sem permissao recebe `404`. No detalhe, as fotos aparecem como miniaturas e o clique abre a imagem ampliada em um lightbox.

## Regras do modulo Documentos

- `/documentos/` usa `ti_required` (admin e Atendente TI; usuario comum e redirecionado). O botao "Documentos" no menu lateral so aparece para TI/admin e todas as rotas validam a permissao no backend (usuario comum recebe `403` nos endpoints e `404` nos anexos).
- A tela lista os documentos cadastrados (nome, observacao resumida, quantidade de anexos, data de cadastro e usuario). Clicar em um documento abre um modal com nome, observacao completa, anexos e dados de cadastro.
- `criar/` usa `POST` multipart (`enctype="multipart/form-data"`) com CSRF (GET retorna `405`): valida nome (minimo 2 caracteres), cria o `DocumentoTI` e salva os anexos (`DocumentoTIAnexo`) sem restricao de tipo ou tamanho no codigo. O novo documento aparece na lista sem refresh.
- `<id>/` retorna JSON com o documento e a lista de anexos (nome + URL de download). `anexos/<id>/` faz o download protegido do arquivo (nao expoe a URL direta de `MEDIA`).
- Documentos e anexos nao sao apagados automaticamente (campo `ativo` preparado para desativacao futura, ainda nao usado na interface).

## Regras do modulo Insumos

- `/insumos/` usa `ti_required` (admin e Atendente TI; usuario comum e redirecionado). O botao "Insumos" no menu lateral so aparece para TI/admin e todas as rotas validam a permissao no backend (usuario comum recebe `403` nos endpoints).
- A tela mostra o estoque em cards (nome, descricao, quantidade e status: Disponivel/Baixo estoque/Sem estoque) e uma tabela com as ultimas retiradas (insumo, quantidade, entregue para, motivo, quem registrou, data/hora).
- `criar/` e `<id>/retirar/` usam `POST` JSON com CSRF (GET retorna `405`). O cadastro valida nome e quantidade inicial obrigatoria e nao negativa.
- A retirada valida no backend: quantidade > 0 (bloqueia zero/negativo com `400`) e menor/igual ao estoque (`409` se insuficiente); `entregue_para` e `motivo` obrigatorios. Em uma transacao com `select_for_update`, abate `quantidade_atual` e cria o registro em `RetiradaInsumoTI`. A resposta traz o insumo atualizado (quantidade e status) e a retirada, para atualizar o card e o historico sem refresh.
- O historico de retiradas nao e apagado e insumos nao sao excluidos automaticamente (campo `ativo` preparado para desativacao futura).

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
