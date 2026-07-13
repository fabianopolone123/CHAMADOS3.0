# 05 - Tarefas

## Em andamento

- Evoluir a atribuicao para um fluxo formal de responsavel, se necessario

## Pendencias conhecidas

- (nenhuma no momento)

## Concluidas

- Deixado o sistema responsivo em todos os tamanhos de tela sem barras de rolagem indesejadas: menu lateral vira barra superior com hamburger (`sidebar.js`) abaixo de 992px, `base.css` global (anti-rolagem-horizontal com `overflow-x: clip` + barras finas), Kanban de altura cheia a partir de 992px, correcao de overflow do Insumos e blindagem dos grids `auto-fit/auto-fill`. Validado com capturas Playwright em 390/768/1024/1440px
- Resolvida a limpeza de arquivos orfaos do modulo Requisicoes: signals `post_delete` (`core/signals.py`) removem do disco as fotos e documentos de orcamentos/suborcamentos ao excluir a requisicao (ou um item isolado), e apagam os diretorios que ficarem vazios sem ultrapassar o `MEDIA_ROOT`. Teste `RequisicaoDeleteFilesTests` cobrindo o cenario
- Criado o modulo "Emprestimos" (apenas TI/admin): controle de comodato de equipamentos de TI com lista, cadastro (colaborador + 1..N equipamentos com fotos, blocos dinamicos), geracao automatica do termo em PDF (ReportLab, espelhando o modelo institucional), download do termo, anexar termo assinado e marcar documentacao OK (fluxo de status). Assinatura do responsavel cadastrada com senha protegida por hash (nunca em texto puro), validada na geracao do termo e com log de uso (rastreabilidade). Models `EmprestimoTI`, `EquipamentoEmprestimoTI`, `FotoEquipamentoEmprestimoTI`, `AssinaturaResponsavelTI`, `LogUsoAssinaturaTI` (migration `0010`); rotas sob `/emprestimos/`; validacoes e permissoes no backend
- Criado o modulo "Documentos" (apenas TI/admin): tela com lista de documentos (nome, observacao resumida, qtd de anexos, data e autor), modal de cadastro (nome, observacao e anexos multiplos, multipart, sem restricao de tipo/tamanho no codigo) e modal de detalhe com anexos para abrir/baixar. Models `DocumentoTI` e `DocumentoTIAnexo` (migration `0009`), registrados no admin; rotas `/documentos/`, `/documentos/criar/`, `/documentos/<id>/`, `/documentos/anexos/<id>/`; anexos servidos por rota protegida e permissao validada no backend
- Criado o modulo "Insumos" (apenas TI/admin): controle simples de estoque com cards (nome, descricao, quantidade, status Disponivel/Baixo/Sem estoque) e tabela de ultimas retiradas. Cadastro de insumo (nome, descricao, quantidade inicial obrigatoria/nao negativa, observacao) e retirada (quantidade, para quem, motivo) com validacao de estoque no backend (bloqueia zero/negativo e quantidade acima do estoque), abatendo o estoque em transacao e registrando o historico. Models `InsumoTI` e `RetiradaInsumoTI` (migration `0008`), registrados no admin; rotas `/insumos/`, `/insumos/criar/`, `/insumos/<id>/retirar/`
- Adicionada a exclusao de requisicao no modulo Requisicoes: botao "Excluir" no rodape do modal de detalhe (apenas TI/admin) com confirmacao obrigatoria ("Excluir definitivamente"); exclusao via `POST /contratos/requisicoes/<id>/excluir/` com CSRF (GET retorna `405`), permissao validada no backend (`403` para comum), remocao em cascata de orcamentos/suborcamentos/documentos e remocao do item da lista sem refresh
- Renomeado o modulo para "Requisicoes" na interface (menu, titulo, card e modal), removendo as referencias visuais a "Contratos"; botao "+ Adicionar" responsivo e card superior compactado. Nomes tecnicos internos (models/rotas/arquivos com prefixo `Contrato`) mantidos para evitar migration/quebra
- Criado o modulo "Contratos" (apenas TI/admin): menu lateral, tela de requisicoes (lista + botao "+"), modal de detalhe com orcamentos e suborcamentos indentados e totais. Models `RequisicaoContrato`, `OrcamentoContrato`, `OrcamentoDocumento`, `SuborcamentoContrato`, `SuborcamentoDocumento` (migration `0007`), com foto do produto, documentos multiplos, botao "Tirar print" (`getDisplayMedia` + recorte), calculo de totais (orcamento + suborcamentos), validacoes no backend e arquivos servidos por rotas protegidas
- Bloqueado o fechamento de chamado por drag: a coluna "Chamados fechados" nao aceita mais drop (card volta com mensagem no frontend; `move_ticket` recusa `target=fechado` com `409` no backend) e passou a ser so lista/consulta. O fechamento acontece somente via Stop, que exige Play ativo, "O que foi feito" preenchido e permissao TI/admin; o encerramento registra no historico tecnico quem finalizou e o texto digitado
- Corrigida a regra do "Play" no Kanban: iniciar atendimento passou a valer somente para chamados em coluna de Atendente TI (oculto em abertos/fechados via CSS por `data-column-type`), com validacao no backend (`403` para usuario comum; `409` para chamado aberto sem atendente ou encerrado) e historico registrado apenas quando o Play e valido
- Adicionado modal de "Chamados fechados" (aberto pelo titulo clicavel da coluna) com pesquisa inteligente dinamica (debounce ~300ms; filtra por ID, titulo, descricao, solicitante, atendente, mensagens e historico), lista compacta e detalhe completo do chamado; endpoints `GET /chamados/fechados/buscar/` e `GET /chamados/fechados/<numero>/` restritos a TI/admin
- Removido o header superior da tela "Chamados" e movida a criacao de chamado para um botao "+" no topo da coluna "Chamados abertos", liberando mais altura para o Kanban
- Adicionada a coluna "Pendencias" no Kanban com cadastro (modal), detalhe (modal) e conversao em chamado por drag-and-drop para a coluna do atendente (model `PendenciaTI`), restrito a TI/admin
- Tornados responsivos os cards e colunas do Kanban (largura/altura fluidas, scroll por coluna, ellipsis para textos longos) para melhor aproveitamento do monitor
- Compactado o header da tela "Chamados" (Quadro de Atendimento) para liberar mais espaco vertical ao Kanban, sem afetar os headers das demais telas
- Ajustado o "Stop" para encerrar o chamado (status Fechado), registrar quem encerrou no historico e mover o card automaticamente para "Chamados fechados" no Kanban sem refresh; encerramento restrito a TI/admin
- Adicionada area de conversa no detalhe do chamado (solicitante x TI) com anexos opcionais por mensagem, resumo no historico tecnico e historico recolhido por padrao (models `ChamadoMensagem` e `ChamadoMensagemAnexo`)
- Corrigida a instabilidade vertical do menu lateral e padronizado seu visual; CSS do menu centralizado em `static/css/sidebar.css`
- Adicionado botao "Criar chamado" no Kanban com modal para o atendente abrir chamado em nome proprio (entra em "Chamados abertos", sem atendente atual)
- Padronizado o menu lateral da area de TI em um include reutilizavel (Chamados + Permissoes)
- Reorganizado o Kanban por fila: coluna de abertos, colunas por Atendente TI e coluna de fechados
- Simplificado o menu do Atendente TI para apenas Chamados e Permissoes
- Criado o endpoint de movimentacao por coluna de destino (aberto/atendente/fechado) com validacao do atendente
- Registrado o atendente atual (quem movimenta o chamado) sem trata-lo como dono do chamado
- Criado o model ChamadoEvento e o log de eventos (criacao, mudanca de status, troca de atendente)
- Exibidos anexos (com data e usuario) e historico do chamado no detalhe, com download protegido de anexos
- Corrigido o badge do Kanban para atualizar texto e cor no drag sem refresh
- Migrado o Kanban da TI para chamados reais do banco, com colunas por status e persistencia da movimentacao
- Removidos os dados mockados/fixos do Kanban e os chamados-fixture do banco
- Criado o endpoint protegido de atualizacao de status com CSRF e permissao de TI
- Criado o portal do solicitante (visao do usuario comum) com abertura, listagem e detalhe de chamados
- Adicionado roteamento pos-login por perfil (TI para o Kanban, usuario comum para o portal)
- Vinculado o chamado ao usuario solicitante e adicionados choices de status e prioridade
- Criada tela de login visual
- Criada rota `/login/`
- Criado redirecionamento da raiz `/`
- Integrada autenticacao Active Directory/LDAP
- Criada interface inicial em `/chamados/`
- Implementado quadro Kanban visual para Atendente TI
- Adicionado drag-and-drop visual dos cards
- Implementada tela inicial de permissoes por grupos do Django
- Definido `fabiano.polone` como administrador principal
- Garantido fluxo de logout
- Criada documentacao inicial do projeto
- Atualizada a documentacao apos a interface inicial de chamados
- Criado modal global de detalhes do chamado no Kanban com dados mockados
- Criado o backend inicial de controle de tempo por atendimento
- Criada a tela inicial de Historico de Atendimentos com busca dinamica

## Proximas tarefas sugeridas

1. Persistir chamados reais no Kanban e substituir os dados mockados
2. Persistir a atribuicao dos cards no backend
3. Refletir no portal os status atualizados pelos atendentes durante o atendimento
4. Definir as transicoes formais de status do chamado
5. Atualizar a conversa sem recarregar a pagina (envio assincrono/AJAX)
