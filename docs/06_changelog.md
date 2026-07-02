# 06 - Changelog

## 2026-07-02

- Adicionado o modulo "Documentos" (menu lateral, apenas TI/admin) para cadastro e armazenamento de documentos internos. A tela lista os documentos (nome, observacao resumida, quantidade de anexos, data e quem cadastrou); o botao "+ Adicionar" abre um modal de cadastro (nome, observacao e anexos multiplos, `multipart/form-data`, sem restricao de tipo/tamanho no codigo) e clicar em um item abre um modal de detalhe com a observacao completa e os anexos (link para abrir/baixar). Tudo por `fetch`/`JsonResponse` com CSRF, sem refresh.
- Criados os models `DocumentoTI` (nome, observacao, ativo, criado_por, datas) e `DocumentoTIAnexo` (documento, arquivo, nome_original, enviado_por, enviado_em), migration `0009`, registrados no admin com `list_display` util e inline de anexos. Rotas: `/documentos/`, `/documentos/criar/`, `/documentos/<id>/`, `/documentos/anexos/<id>/`, todas restritas a TI/admin no backend (comum recebe `403` nos endpoints e `404` nos anexos). Os arquivos ficam em `MEDIA_ROOT/documentos/<id>/` e sao servidos por rota protegida. Documentos/anexos nao sao apagados automaticamente (campo `ativo` preparado).
- Adicionado o modulo "Insumos" (menu lateral, apenas TI/admin) para controle simples de estoque e retirada de materiais de TI. A tela tem duas areas: "Estoque de insumos" (cards com nome, descricao, quantidade e status Disponivel/Baixo estoque/Sem estoque, com botao "Retirar") e "Ultimas retiradas" (tabela com insumo, quantidade, entregue para, motivo, quem registrou e data/hora). Botao "+ Adicionar" abre modal de cadastro; tudo por `fetch`/`JsonResponse` com CSRF, sem refresh.
- Criados os models `InsumoTI` (nome, descricao, quantidade_atual, observacao, ativo, criado_por, datas) e `RetiradaInsumoTI` (insumo, quantidade, entregue_para, motivo, registrado_por, criado_em), migration `0008`, registrados no admin com `list_display` util e inline de retiradas.
- Regras: cadastro exige quantidade inicial obrigatoria e nao negativa; a retirada valida no backend quantidade > 0 (bloqueia zero/negativo) e menor/igual ao estoque (`409` se insuficiente), com `entregue_para` e `motivo` obrigatorios. A baixa de estoque e o registro do historico ocorrem em uma transacao (`select_for_update`); o card (quantidade + status) e a tabela de retiradas sao atualizados sem refresh. Historico de retiradas nao e apagado e insumos nao sao excluidos automaticamente (campo `ativo` preparado). Rotas: `/insumos/`, `/insumos/criar/`, `/insumos/<id>/retirar/`, todas restritas a TI/admin no backend (comum recebe `403`).
- Adicionada a exclusao de requisicao no modulo Requisicoes. O modal de detalhe passou a ter um botao "Excluir" discreto (rodape) que abre uma confirmacao obrigatoria ("Tem certeza que deseja excluir esta requisicao? Esta acao nao podera ser desfeita." + aviso de que remove orcamentos, suborcamentos e documentos), com "Cancelar" e "Excluir definitivamente" (estilo perigoso). Cancelar nao faz nada; confirmar envia `POST /contratos/requisicoes/<id>/excluir/` com CSRF.
- O endpoint de exclusao valida permissao TI/admin no backend (usuario comum recebe `403`), aceita apenas `POST` (GET retorna `405`) e remove a requisicao com seus orcamentos, suborcamentos e documentos por cascata (`on_delete=CASCADE`). Em caso de sucesso o item some da lista sem refresh; em erro permanece visivel com mensagem. Sem alteracao de model (nenhuma migration criada). Pendencia registrada: os arquivos fisicos em `MEDIA_ROOT` nao sao removidos do disco (sem rotina de limpeza de orfaos ainda).
- Renomeado o modulo na interface de "Contratos" para "Requisicoes": menu lateral, `<title>`, card superior (titulo "Requisicoes", subtitulo "Cadastro de requisicoes" e descricao curta) e kicker do modal de criacao. Removidas as referencias visuais a "Contratos"/"Requisicoes de contrato". Os nomes tecnicos internos (models `*Contrato`, rotas `/contratos/...`, arquivos `contratos.css`/`contratos.js` e classes CSS) foram mantidos para nao gerar migration nem risco de quebra; nenhuma migration foi criada (mudanca apenas visual/textual).
- Melhorado o botao de nova requisicao: virou uma pill "+ Adicionar" (icone + rotulo) com hover/transicao; responsivo, mostrando apenas "+" em telas menores (<=640px). Abre o mesmo modal de cadastro.
- Compactado o card superior da tela de Requisicoes: menos padding e margens, titulo menor, e alinhamento de titulo/subtitulo/botao na mesma linha em telas maiores (com quebra responsiva em telas menores), liberando area util para a lista.
- Adicionado o modulo "Contratos" (menu lateral, apenas TI/admin). Tela principal lista as requisicoes (titulo + status) com botao "+" para cadastro em modal; clicar em uma requisicao abre um modal com todos os dados e seus orcamentos, cada um com os suborcamentos indentados abaixo e os totais destacados. Toda a interacao e por `fetch`/`JsonResponse` com CSRF, sem refresh.
- Criados os models `RequisicaoContrato`, `OrcamentoContrato`, `OrcamentoDocumento`, `SuborcamentoContrato` e `SuborcamentoDocumento` (migration `0007`). Requisicao 1--N orcamento 1--N suborcamento; orcamentos e suborcamentos tem 1--N documentos. Requisicao nasce com status "Aberta" e `criado_por` = usuario logado.
- Regra de calculo: total do orcamento = valor x quantidade + frete - desconto; o total exibido considera tambem a soma dos totais dos suborcamentos. O backend valida moeda (BRL/USD), exige quantidade >= 1 e bloqueia valores negativos em valor/frete/desconto.
- Orcamento e suborcamento aceitam foto do produto (imagem) e multiplos documentos anexos (sem restricao de tipo/tamanho no codigo), via `multipart/form-data`. Botao "Tirar print" captura a tela pelo navegador (`getDisplayMedia`), recorta uma regiao no canvas, pre-visualiza e anexa o recorte como foto do produto; com navegador sem suporte, orienta anexar imagem manualmente e nao trava se a captura for cancelada.
- Rotas criadas: `/contratos/`, `/contratos/requisicoes/criar/`, `/contratos/requisicoes/<id>/`, `/contratos/requisicoes/<id>/orcamentos/criar/`, `/contratos/orcamentos/<id>/suborcamentos/criar/`, alem de rotas protegidas para servir fotos e baixar documentos. Todas validam permissao TI/admin no backend (usuario comum: `403` nos endpoints e `404` nos arquivos). Models registrados no `admin.py` com `list_display` util e inlines. Adicionado `Pillow` ao `requirements.txt` (dependencia do `ImageField`).
- O fechamento de chamado deixou de ser possivel por drag: a coluna "Chamados fechados" nao aceita mais o drop direto. No frontend, ao soltar um card nessa coluna o movimento e cancelado (o card volta para a coluna de origem) com a mensagem "Para fechar o chamado, inicie o atendimento e finalize usando o botao Stop."; no backend, o endpoint `POST /chamados/mover/` recusa o destino `fechado` com `409` (nao aceita mais `target=fechado`). A coluna passou a ser apenas lista/consulta e so recebe chamados via Stop.
- O fechamento agora acontece exclusivamente pela acao "Stop": o backend (`POST /chamados/atendimento/encerrar/`) exige Atendente TI/Admin (`403` para usuario comum), atendimento ativo/Play em andamento do proprio usuario (`409` se nao houver), o campo "O que foi feito" preenchido e chamado ainda nao encerrado. Ao finalizar, salva o status "Fechado", `fechado_em`, atendente = quem finalizou, move o card para "Chamados fechados" e atualiza o badge (texto/cor) sem refresh. O botao de envio do modal passou a se chamar "Finalizar chamado".
- O historico tecnico do encerramento passou a registrar quem finalizou e o texto de "O que foi feito" (ex.: "Chamado finalizado por fabiano.polone. O que foi feito: atualizacao do driver e validacao com o usuario."), alem da mudanca de status, sem duplicar eventos e sem misturar com a conversa do usuario (`ChamadoMensagem`). Sem alteracao de model/banco (sem migration). Testes automatizados atualizados/adicionados (`core/tests.py`): fechamento via Stop registra o texto, drag para "fechado" e bloqueado e Stop exige Play ativo.
- Corrigida a regra do "Play" (iniciar atendimento) no Kanban: o botao passou a existir e funcionar somente para chamados em uma coluna de Atendente TI. Cards em "Chamados abertos" e "Chamados fechados" nao mostram mais o painel Play/Pause/Stop (regra em CSS que reage ao `data-column-type` da coluna, entao ao arrastar o card entre colunas o botao aparece/some sem refresh e sem alterar o drag-and-drop). Pendencias seguem sem Play (card proprio, sem o painel).
- O endpoint `POST /chamados/atendimento/iniciar/` passou a validar no backend: exige permissao de Atendente TI/Admin (usuario comum recebe `403`) e bloqueia com `409` o Play em chamado aberto sem atendente atual e em chamado encerrado (resolvido/fechado), mesmo se chamado direto pela URL. A regra "coluna de atendente" espelha o quadro (nao encerrado e `atendente_atual` no grupo `Atendente TI`). O `AtendimentoHistorico` so e criado quando o Play e valido; acoes bloqueadas nao geram historico e a regra de um unico atendimento ativo por atendente evita duplicidade. Sem alteracao de model/banco (sem migration).
- O titulo "Chamados fechados" no Kanban ficou clicavel (hover discreto com icone de lupa) e abre um modal moderno e responsivo, com animacao de entrada, para consultar os chamados encerrados sem sair da tela. O drag-and-drop, a criacao de chamados/pendencias e as demais colunas nao foram alterados.
- O modal tem dois estados: (1) barra de pesquisa inteligente + lista compacta (ID e titulo) e (2) detalhe completo do chamado. A lista inicial mostra os encerrados mais recentes; clicar em um item abre o detalhe (numero, titulo, descricao, solicitante, atendente, status, data de criacao, data de fechamento, anexos, conversa e historico tecnico recolhido). Botoes "Voltar" (retorna a lista) e "Fechar".
- A pesquisa e dinamica (enquanto digita), com debounce de ~300ms e cancelamento das requisicoes anteriores (AbortController); e case-insensitive, aceita partes do texto e filtra por ID/numero, titulo, descricao, solicitante, atendente atual, mensagens da conversa e descricao dos eventos do historico. Sem resultados exibe "Nenhum chamado fechado encontrado."; a busca usa `distinct()` e limita a 100 registros para nao pesar.
- Criadas as rotas `GET /chamados/fechados/buscar/` (lista/pesquisa em JSON) e `GET /chamados/fechados/<numero>/` (detalhe completo em JSON), ambas restritas a Atendente TI/Admin (usuario comum recebe `403`, validado no backend). O detalhe so expoe chamados encerrados (senao `404`) e reaproveita as rotas protegidas para download de anexos. Nao houve alteracao de model (sem migration).
- Corrigida a altura responsiva das colunas do Kanban para evitar rolagem interna antes de ocupar a altura disponivel da tela. A causa era o `max-height: calc(100vh - 5rem)` fixo (estimativa que rolava cedo e deixava espaco embaixo). Substituido por uma cadeia flex de altura no desktop (>=1200px): a tela do Kanban usa `100vh`, a area do Kanban recebe `flex: 1`, as colunas usam `height: 100%` e apenas a lista de cards rola (`overflow-y: auto` com `min-height: 0`). Assim a rolagem interna so aparece quando os cards realmente ultrapassam a coluna; em telas menores/empilhadas mantem o comportamento natural.
- Removido o card/header superior da tela "Chamados" (titulo, descricao e botao "Criar chamado"), liberando mais altura vertical para o Kanban (colunas passaram a usar `max-height: calc(100vh - 5rem)`).
- A criacao de chamado passou para um botao "+" redondo no topo da coluna "Chamados abertos", que abre o mesmo modal de criacao (titulo, descricao e anexos). Reutiliza a rota `POST /chamados/criar/` (apenas TI/admin, CSRF): chamado com solicitante = usuario logado, status "Aberto", sem atendente atual, entrando na coluna "Chamados abertos" sem refresh e registrando "Chamado criado manualmente pelo atendente X." no historico. Botao "+" padronizado com a coluna "Pendencias" (classe `column-add-btn`).
- Corrigido o texto de coluna vazia da coluna "Pendencias": a mensagem "Nenhuma pendencia cadastrada." deixava de sumir ao criar uma pendencia porque a funcao de recalculo do estado vazio so varria as colunas de chamados (`.js-ticket-list`), ignorando a coluna de pendencias (`.js-pendencia-list`). A funcao passou a cobrir tambem a coluna de pendencias, entao o texto some ao criar e reaparece apenas quando a ultima pendencia sai da coluna (ex.: convertida em chamado), sem refresh.
- Adicionada a coluna "Pendencias" no Kanban (entre "Chamados abertos" e as colunas dos atendentes) com botao "+" para cadastro em modal, card compacto exibindo so o titulo e modal de detalhe (titulo, descricao, data e autor). Criado o model `PendenciaTI` e a migration `0006_pendenciati`.
- Arrastar uma pendencia para a coluna de um atendente a converte em chamado (titulo/descricao da pendencia, solicitante = criador, atendente atual = atendente destino, status "Em atendimento"); a pendencia sai da coluna, o novo card aparece sem refresh e o historico registra a criacao a partir da pendencia e a atribuicao ao atendente. Conversao idempotente (sem chamado duplicado) e restrita a TI/admin; usuario comum recebe 403.
- Criadas as rotas `POST /chamados/pendencias/criar/`, `GET /chamados/pendencias/<id>/` e `POST /chamados/pendencias/<id>/converter/`. Regras de drag: pendencia so vai para colunas de atendente; chamado normal nao entra na coluna de pendencias; destino invalido devolve o card.
- Ajuste responsivo dos cards e colunas do Kanban para melhor adaptacao ao tamanho do monitor: colunas passaram de largura fixa (teto de 340px) para flex fluido (crescem em telas grandes, encolhem ate um minimo legivel e rolam horizontalmente quando ha muitas); cada coluna usa a altura do navegador com scroll interno da lista de cards (sem scroll vertical desnecessario da pagina); cards com padding/espacamento fluidos (clamp), titulo limitado a 2 linhas com reticencias e solicitante/atendente com ellipsis para nomes longos. Drag-and-drop, clique no card, botao "Criar chamado" e mensagens de coluna vazia preservados.
- Reduzida a altura do header da tela "Chamados" (Quadro de Atendimento) para melhorar o espaco util do Kanban: header compacto (menos padding e margem), titulo "Quadro de Atendimento" menor, descricao em linha unica e botao "Criar chamado" alinhado a direita no mesmo card. Aplicado via modificador `tickets-topbar--compact`, sem afetar os headers das outras telas.
- Ajustado o encerramento pelo botao "Stop": alem de finalizar o periodo de atendimento, o chamado agora e encerrado (status "Fechado", `fechado_em` preenchido, atendente atual = quem encerrou) e o card e movido automaticamente para a coluna "Chamados fechados" no Kanban, com badge atualizado sem refresh. Em caso de falha, o card permanece na coluna original.
- O encerramento passou a exigir permissao de Atendente TI/Admin (`/chamados/atendimento/encerrar/` retorna `403` para usuario comum) e registra no historico tecnico a mudanca de status e o evento "Chamado encerrado por X.", sem duplicar registros. O "Pause" continua apenas encerrando o periodo, sem mudar o status.
- Adicionada a area de conversa no detalhe do chamado, permitindo troca de mensagens entre solicitante e Atendente TI/Admin, com anexos opcionais por mensagem (multiplos arquivos, sem limite de tamanho/extensao).
- Criados os models `ChamadoMensagem` (texto da conversa) e `ChamadoMensagemAnexo` (anexos da mensagem) e a migration `0005_chamadomensagem_chamadomensagemanexo`.
- Criadas as rotas `POST /meus-chamados/<numero>/mensagens/` (envio, com permissao validada no backend) e `GET /meus-chamados/<numero>/mensagens/anexo/<id>/` (download protegido de anexo de mensagem).
- Cada mensagem gera um evento resumido no historico tecnico (`ChamadoEvento` tipo `comentario`), sem duplicar o texto; a conversa guarda o conteudo e o historico guarda so o resumo.
- O historico tecnico do chamado passou a aparecer recolhido por padrao (elemento `details/summary`), expandindo e recolhendo ao clique, sem trocar de tela nem remover registros.
- Mensagens do solicitante e da equipe de TI sao diferenciadas visualmente; apos enviar, o usuario permanece no detalhe com notificacao de sucesso ou erro.
- Adicionados testes automatizados (`core/tests.py`) para envio de mensagem, anexos, resumo no historico e permissoes de acesso.
- Sincronizada a documentacao com o estado real do projeto: `01_arquitetura.md` (Kanban com dados reais, movimentacao persistida, `ti_required`, `static/js` e `sidebar.css`), `03_modelos.md` (quatro modelos: `Chamado`, `ChamadoEvento`, `ChamadoAnexo` e `AtendimentoHistorico`; `AnexoChamado` deixou de ser "previsto") e `00_visao_geral.md` (escopo atual e fora de escopo atualizados).
- Corrigido o texto de coluna vazia no Kanban apos movimentacao de cards: a mensagem de vazio (ex.: "Sem chamados em atendimento.") deixou de aparecer junto com os cards. O estado de vazio agora e recalculado na hora, no drag-and-drop, removendo a mensagem quando a coluna recebe um card e recriando-a (via `data-empty-text`) quando a coluna fica sem cards; em caso de falha no POST o card volta e a mensagem e recalculada.
- Corrigida a instabilidade vertical do menu lateral: os botoes mudavam de posicao ao trocar de tela (ex.: entre "Chamados" e "Permissoes") porque a `.tickets-sidebar` esticava ate a altura do conteudo e o `space-between` distribuia os blocos de forma diferente em cada pagina. A sidebar passou a ter altura fixa (`100vh`) e `position: sticky`, mantendo o menu sempre na mesma posicao.
- Centralizado o CSS do menu lateral em `static/css/sidebar.css` (fonte unica, carregada em `base.html`), removendo as regras duplicadas de `chamados.css` e a responsividade da sidebar do media query.
- Padronizado o visual do menu: espacamento interno consistente, bordas arredondadas, hover suave, estado ativo com destaque (barra de acento) e transicoes leves.
- Adicionados icones inline (SVG) aos itens do menu de TI e do portal, sem depender de biblioteca externa de icones.

## 2026-07-01

- Adicionado o botao "Criar chamado" na tela "Chamados" (Kanban) com modal responsivo, visivel apenas para TI/admin.
- Criado o endpoint `POST /chamados/criar/` (TI/admin, CSRF) que abre chamado com o atendente logado como solicitante, status "Aberto" e sem atendente atual.
- O card recem-criado e inserido na coluna "Chamados abertos" sem refresh; a criacao registra evento "Chamado criado manualmente pelo atendente X.".
- Padronizado o menu lateral da area de TI em um unico include reutilizavel (`partials/ti_sidebar.html`), eliminando a inconsistencia entre as telas de Kanban, Permissoes e Historico.
- Menu da area de TI passa a exibir apenas "Chamados" (Kanban) e "Permissoes"; removidos os itens antigos "Quadro de Atendimento", "Historico", "Chamados do Usuario" e "Relatorios".
- Padronizado o nome do botao principal para "Chamados" (apontando para o Kanban) em todas as telas.
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
