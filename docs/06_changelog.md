# 06 - Changelog

## 2026-07-02

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
