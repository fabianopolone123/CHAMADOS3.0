# 02 - Regras de Negocio

## Situacao atual

O sistema possui autenticacao corporativa via Active Directory/LDAP e uma interface inicial de atendimento para a equipe de TI.

## Regras atuais de autenticacao

1. O usuario deve informar credenciais corporativas validas para acessar o sistema.
2. A autenticacao deve ocorrer via Active Directory usando LDAP.
3. Em caso de autenticacao valida, o usuario deve ser sincronizado localmente no Django.
4. Em caso de erro, o sistema deve exibir mensagem amigavel sem expor detalhes internos do AD.
5. O logout deve encerrar a sessao e retornar o usuario para a tela de login.

## Regras atuais do painel de atendimento (Kanban por atendente)

1. O Kanban e acessivel apenas para administrador e Atendente TI; o usuario comum e redirecionado para o portal.
2. O menu do Atendente TI mostra apenas "Chamados" (o Kanban) e "Permissoes".
3. O quadro lista os chamados reais do banco (model `Chamado`), sem dados mockados.
4. A primeira coluna e fixa: "Chamados abertos" (chamados nao encerrados e sem atendente atual); logo apos vem a coluna fixa "Pendencias" (ver secao de pendencias).
5. As colunas do meio sao dinamicas: uma para cada usuario do grupo `Atendente TI`, exibindo os chamados nao encerrados cujo `atendente_atual` e aquele usuario.
6. A ultima coluna e fixa: "Chamados fechados" (status `resolvido` ou `fechado`).
7. Cada card exibe numero, titulo, solicitante, data de abertura, status atual e atendente atual (quando existir).
8. Arrastar para a coluna de um atendente define o `atendente_atual` como aquele usuario e o status como "Em atendimento".
9. Arrastar entre atendentes atualiza o `atendente_atual`.
10. Nao e possivel arrastar um chamado para "Chamados fechados": o drop e recusado (o card volta para a coluna de origem) e o usuario recebe a mensagem "Para fechar o chamado, inicie o atendimento e finalize usando o botao Stop.". A coluna "Chamados fechados" so recebe chamados via acao Stop e serve apenas como lista/consulta. O bloqueio tambem e validado no backend (o endpoint de movimentacao recusa o destino `fechado` com `409`).
11. Arrastar para "Chamados abertos" volta o status para "Aberto" e limpa o `atendente_atual`.
12. O `atendente_atual` NAO torna o usuario dono do chamado; o dono e sempre o solicitante que abriu.
13. Toda movimentacao e salva no banco e gera registro em `ChamadoEvento`.
14. A movimentacao usa endpoint `POST` protegido por login e permissao de TI, com CSRF; usuario comum nao movimenta chamados.
15. O atendente de destino e validado no backend: precisa pertencer ao grupo `Atendente TI`.
16. Ao arrastar, o badge de status do card atualiza texto e cor imediatamente, sem refresh.
17. Clicar em um card abre a tela de detalhe do chamado.
18. Somente os cards em uma coluna de Atendente TI exibem o controle de tempo (iniciar/Play, pausar e finalizar); cards em "Chamados abertos" e "Chamados fechados" nao mostram esses botoes.
19. O detalhe do chamado exibe os anexos (nome, link de download, data e usuario que enviou) e o historico de eventos.
20. Anexos so podem ser baixados pelo dono do chamado ou por TI/admin.
21. A tela "Chamados" nao possui header superior; a criacao de chamado fica em um botao "+" no topo da coluna "Chamados abertos" (visivel apenas para TI/admin) que abre um modal para o atendente abrir um chamado em nome dele mesmo.
22. Chamado criado pelo Kanban entra com status "Aberto", solicitante = atendente logado e sem atendente atual (aparece na coluna "Chamados abertos").
23. O atendente atual do chamado criado so e definido quando o card e arrastado para a coluna de um atendente.
24. A criacao pelo Kanban registra em `ChamadoEvento`: "Chamado criado manualmente pelo atendente X."
25. O titulo "Chamados fechados" e clicavel e abre um modal de consulta dos chamados encerrados (lista + pesquisa e detalhe completo), acessivel apenas para Atendente TI/Admin (validado no backend); usuario comum nao acessa a lista geral de fechados e continua vendo apenas os proprios chamados pelo portal.
26. O modal comeca na lista compacta (ID e titulo) dos encerrados mais recentes e possui uma pesquisa inteligente, dinamica (debounce de ~300ms), case-insensitive e por partes do texto, que filtra por ID/numero, titulo, descricao, solicitante, atendente atual, mensagens da conversa e historico; sem resultados exibe "Nenhum chamado fechado encontrado.".
27. Clicar em um item abre o detalhe completo do chamado no proprio modal (numero, titulo, descricao, solicitante, atendente, status, data de criacao, data de fechamento, anexos, conversa e historico tecnico recolhido por padrao); o botao "Voltar" retorna a lista e "Fechar" encerra o modal.

## Regras atuais de controle de tempo

1. Um atendente pode ter apenas um atendimento ativo por vez.
2. O usuario logado e o atendente responsavel pelos registros de tempo.
3. Um chamado pode acumular varios periodos de atendimento ao longo da sua vida.
4. Pausar ou finalizar atendimento exige descricao obrigatoria do que foi feito.
4a. O "Play" (iniciar/continuar atendimento) so existe e so funciona para chamados que estao em uma coluna de Atendente TI: chamados em "Chamados abertos", em "Pendencias" e em "Chamados fechados" nao exibem o botao. Um chamado so pode receber Play depois de ser arrastado para a coluna de um atendente.
4b. Apenas Atendente TI/Admin executam o Play; usuario comum nunca ve nem executa. A regra e validada no frontend (o painel Play/Pause/Stop so aparece em coluna de atendente) e no backend (o endpoint nega usuario comum com `403` e bloqueia chamado aberto sem atendente ou encerrado com `409`).
4c. O historico de atendimento (registro de tempo) so e criado quando o Play e executado validamente; acoes bloqueadas nao geram registro e a regra de um unico atendimento ativo por atendente evita duplicidade.
5. Cada registro deve guardar inicio, fim, duracao, tipo de encerramento e descricao.
6. O backend deve validar as regras criticas mesmo que o frontend tambem faca bloqueios visuais.
7. Administrador pode consultar todos os historicos de atendimento.
8. Atendente TI pode consultar apenas o proprio historico na tela dedicada.
9. Apenas Atendente TI/Admin podem encerrar chamados; o endpoint de encerramento nega usuario comum no backend.
10. O fechamento de chamado acontece exclusivamente pela acao "Stop" (nao por drag). O Stop exige, validado no backend: usuario Atendente TI/Admin (`403` caso contrario), atendimento ativo/Play em andamento (`409` se nao houver), campo "O que foi feito" preenchido e chamado ainda nao encerrado.
11. Ao clicar em "Stop", abre-se o modal de encerramento com o titulo do chamado, o campo obrigatorio "O que foi feito", o botao "Finalizar chamado" e o botao "Cancelar". O campo nao pode ser vazio (validado no frontend e no backend).
12. Ao finalizar com "Stop": salva-se o texto informado, o status vai para "Fechado", `fechado_em` e preenchido, o atendente atual passa a ser quem finalizou, o card e movido automaticamente para "Chamados fechados" e o badge (texto e cor) e atualizado sem refresh. Se o Stop falhar, o card permanece na coluna atual.
13. "Pause" apenas encerra o periodo de atendimento e nao altera o status do chamado.
14. O encerramento pelo "Stop" registra no historico tecnico a mudanca de status e um evento de finalizacao com quem finalizou e o texto de "O que foi feito" (ex.: "Chamado finalizado por fabiano.polone. O que foi feito: atualizacao do driver e validacao com o usuario."), sem duplicar registros se o chamado ja estiver fechado. Esse texto e registro tecnico de encerramento, separado da conversa do usuario (`ChamadoMensagem`).

## Regras atuais de permissao

1. O usuario `fabiano.polone` deve ser administrador principal do sistema.
2. O sistema deve garantir automaticamente os grupos `Administrador` e `Atendente TI`.
3. Apenas administradores podem acessar `/permissoes/`.
4. Apenas administradores podem atribuir ou remover o perfil `Atendente TI`.
5. O grupo `Atendente TI` e a base inicial para a composicao das colunas do quadro Kanban.

## Regras atuais do portal do solicitante

1. O usuario comum e todo usuario autenticado que nao pertence aos grupos `Administrador` nem `Atendente TI`.
2. Apos o login, o usuario comum e direcionado para `/meus-chamados/` e a equipe de TI para o Kanban.
3. O usuario comum abre chamados informando apenas titulo, descricao e anexos (opcionais).
4. O usuario comum nao escolhe status, prioridade, atendente nem solicitante; esses campos sao definidos pelo sistema ou pela equipe de TI.
5. Cada chamado aberto pelo portal recebe numero unico gerado no formato `CH-000123`.
6. O chamado aberto nasce com status `aberto` e registra o usuario logado como solicitante automaticamente.
7. Os anexos enviados na abertura ficam vinculados ao chamado, sem restricao de tamanho ou extensao neste momento.
8. O usuario comum visualiza e acessa apenas os chamados que ele mesmo abriu.
9. Administrador e Atendente TI podem acessar o detalhe de qualquer chamado.
10. A tela de detalhe exibe a timeline real dos periodos de atendimento registrados no chamado.

## Regras atuais das pendencias (Kanban)

1. O Kanban possui a coluna "Pendencias" entre "Chamados abertos" e as colunas dos atendentes.
2. Apenas Atendente TI/Admin podem ver a coluna, criar pendencia, abrir o detalhe e converter em chamado; usuario comum nao acessa nenhum endpoint de pendencia (validado no backend).
3. A pendencia e criada pelo usuario logado, com titulo e descricao; na coluna exibe somente o titulo.
4. O clique na pendencia abre um modal com titulo, descricao, data de criacao e quem criou.
5. Arrastar uma pendencia para a coluna de um atendente a converte em um novo chamado; nao e permitido arrastar para "Chamados abertos" nem para "Chamados fechados" (destino invalido devolve a pendencia a coluna de origem).
6. O chamado gerado recebe: titulo e descricao da pendencia, `solicitante` = quem criou a pendencia, `atendente_atual` = atendente da coluna destino e status "Em atendimento".
7. Apos converter, a pendencia sai da coluna "Pendencias" e o novo chamado aparece na coluna do atendente, sem refresh.
8. A pendencia nao e apagada: fica marcada como convertida (rastreabilidade) e nao pode gerar chamado duplicado se arrastada novamente.
9. O atendente de destino e validado no backend (precisa pertencer ao grupo Atendente TI); a conversao usa POST com CSRF.
10. Se a conversao falhar, a pendencia volta para a coluna "Pendencias" e um erro e exibido.
11. A conversao registra no historico do chamado a criacao a partir da pendencia e a atribuicao ao atendente; quando quem criou e quem converteu sao a mesma pessoa, o registro permanece claro e sem duplicidade.

## Regras atuais da conversa do chamado

1. O detalhe do chamado possui uma area de conversa entre o solicitante e o Atendente TI/Admin, separada do historico tecnico.
2. O solicitante pode ver e enviar mensagens apenas nos proprios chamados.
3. Atendente TI e Admin podem ver e responder mensagens em qualquer chamado da visao de atendimento.
4. Usuario comum nao acessa nem envia mensagem em chamado de outro usuario; a permissao e validada no backend.
5. Cada mensagem fica vinculada ao chamado e pode ter zero ou mais anexos opcionais (sem limite de tamanho ou extensao neste momento).
6. Uma mensagem precisa ter texto ou pelo menos um anexo; mensagens totalmente vazias sao rejeitadas.
7. A conversa guarda o conteudo trocado; o historico tecnico guarda apenas o resumo da acao, sem duplicar o texto.
8. Ao enviar uma mensagem, o sistema registra um evento resumido em `ChamadoEvento` (ex.: "Mensagem enviada pelo solicitante Joao." ou "Mensagem enviada com 2 anexo(s) por fabiano.polone.").
9. As mensagens diferenciam visualmente autor solicitante e autor da equipe de TI.
10. Apos enviar, o usuario permanece no detalhe do chamado e ve uma notificacao de sucesso ou erro.
11. O historico tecnico aparece recolhido por padrao no detalhe e expande/recolhe ao ser clicado, sem trocar de tela e sem remover registros.

## Regras previstas para o sistema de chamados

1. Cada chamado deve ter status de acompanhamento com transicoes controladas.
2. O chamado deve registrar data de abertura e, quando aplicavel, data de fechamento.
3. O chamado deve ser atribuivel a uma equipe ou atendente com persistencia real no Kanban.
4. O historico de alteracoes deve ser preservado.
5. Comentarios e interacoes devem ficar vinculados ao chamado.
6. O solicitante deve poder complementar ou acompanhar interacoes do chamado.

## Regras de seguranca

- Credenciais reais nao devem ser gravadas em codigo.
- Variaveis como `AD_LDAP_BIND_PASSWORD` devem permanecer apenas no `.env` ou no ambiente do servidor.
- Caminhos de certificado devem ser validados por ambiente antes do deploy.
