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
8. Arrastar para a coluna de um atendente define o `atendente_atual` como aquele usuario e marca o status como "Atribuido" (o chamado foi atribuido, mas o periodo de atendimento so comeca no Play).
8c. **Nao e possivel mover um chamado que esta com atendimento ativo (Play).** O periodo em andamento pertence a quem deu o Play; mover trocaria o atendente atual (ou devolveria para "Chamados abertos") deixando o cronometro "orfao" — e o novo atendente nem conseguiria pausar/finalizar (o Play nao e dele). Por isso, enquanto houver Play ativo o drop e recusado: o card volta para a coluna de origem e o usuario recebe "Pause ou finalize o atendimento (Play) antes de mover o chamado.". A regra e validada no frontend (usa o `data-ticket-active` do card) e no backend (o endpoint de movimentacao recusa com `409` para qualquer destino enquanto houver atendimento ativo). Basta dar Pause (ou Stop) para liberar a movimentacao.
8a. O status "Em atendimento" so vale enquanto ha um atendimento ativo (do Play ao Pause/Stop). Play marca "Em atendimento"; Pause sem motivo devolve o chamado para "Atribuido"; Pause com motivo marca "Aguardando" (usuario/peca/autorizacao); Stop fecha o chamado.
8d. Como consequencia direta de 8a, o Kanban **so mostra "Em atendimento" quando existe de fato um Play ativo** naquele chamado (de qualquer atendente). Um chamado que esteja gravado com o status "em_atendimento" sem nenhum atendimento aberto (dado antigo, de quando arrastar para o atendente ja marcava "Em atendimento") aparece pelo que realmente e: "Atribuido" quando tem atendente atual e "Aberto" quando esta sem. Vale para o badge do card e para os contadores da coluna. A normalizacao dos registros antigos no banco foi feita pela migration `0043`.
8b. Ao ser arrastado (ou convertido de pendencia) para a coluna de um atendente, o card aparece no topo da coluna, logo abaixo dos que estao com Play ativo. No recarregamento, cada coluna de atendente ordena os cards com Play ativo no topo e, dentro de cada grupo, por atividade mais recente.
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
28. Os chamados em algum estado de **"aguardando"** (aguardando usuario, peca ou autorizacao) aparecem **esmaecidos** (semitransparentes) na coluna do atendente, sinalizando que estao parados esperando algo externo; ao passar o mouse ou focar, o card volta a opacidade cheia para leitura. O esmaecido acompanha as mudancas de status sem refresh (Play tira o esmaecido; Pause com motivo de "aguardando" aplica; Pause sem motivo ou mover deixa "Atribuido", sem esmaecido).
29. Cada coluna de atendente mostra, alem do **total** de chamados (contador do cabecalho), uma **quebra por status** logo abaixo: **Em atendimento** (laranja), **Aguardando** (cinza, soma dos tres tipos de "aguardando") e **Atribuido** (roxo). Os numeros sao calculados no backend na carga da pagina e recalculados no front (sem refresh) a cada Play/Pause/Stop, movimentacao e conversao de pendencia. Categorias com zero ficam discretas (esmaecidas), mantendo o layout estavel.
30. Os contadores da quebra sao **clicaveis**: clicar em um deles (ex.: "em atend.") faz um **preview temporario** na coluna, escondendo os demais cards e deixando so os do status escolhido; passados ~20 segundos a coluna volta sozinha a visualizacao padrao (todos os cards). Clicar de novo no mesmo contador, clicar em outro, ou comecar a arrastar um card volta imediatamente ao padrao. Contadores zerados nao sao clicaveis. E apenas um recorte visual no navegador: nao altera dados, status nem os numeros.

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
10a. **Excecao ao Play obrigatorio: chamado parado em "aguardando" (usuario/peca/autorizacao) pode ser encerrado direto pelo Stop, sem Play.** O que estava sendo esperado muitas vezes so se resolve sozinho (a peca nao veio mais, o usuario desistiu, a autorizacao saiu), e obrigar um Play so para fechar criaria um periodo de atendimento artificial. Por isso o card em "aguardando" sem Play mostra **Play e Stop** (o Pause fica oculto, pois nao ha atendimento rodando). Continua valendo tudo o mais: so TI/Admin (`403`), "O que foi feito" obrigatorio, chamado nao encerrado (`409` se ja estiver) e, fora de "aguardando" sem Play, o Stop e recusado com `409` ("Inicie o atendimento (Play) antes de finalizar este chamado."). O "Pause" sem Play continua bloqueado. No frontend, a guarda de clique dos botoes do card (`bindActionButton`) abre excecao para o Stop quando o card esta em "aguardando" sem Play (`isDirectClose`), espelhando a regra do backend — sem isso o botao aparecia mas o clique era barrado com "Este chamado nao possui atendimento ativo para voce." (corrigido em 29/07/2026).
10b. O encerramento direto **nao cria periodo em `AtendimentoHistorico`** (nao houve tempo de atendimento), mas registra tudo na linha do tempo do chamado: a mudanca de status (de qual "aguardando" ele saiu para Fechado) e um evento de encerramento do tipo `encerramento_direto` com quem fechou e o "O que foi feito" (ex.: "Chamado finalizado por fabiano.polone sem atendimento ativo (estava em Aguardando peca). O que foi feito: peca nao veio mais, usuario trocou de maquina."). Esse evento aparece tanto no "Historico do chamado" quanto no "Andamento do atendimento" do detalhe, junto dos periodos de atendimento anteriores, em ordem cronologica. A notificacao de fechamento por e-mail e disparada normalmente.
11. Ao clicar em "Stop", abre-se o modal de encerramento com o titulo do chamado, o campo obrigatorio "O que foi feito", o botao "Finalizar chamado" e o botao "Cancelar". O campo nao pode ser vazio (validado no frontend e no backend).
12. Ao finalizar com "Stop": salva-se o texto informado, o status vai para "Fechado", `fechado_em` e preenchido, o atendente atual passa a ser quem finalizou, o card e movido automaticamente para "Chamados fechados" e o badge (texto e cor) e atualizado sem refresh. Se o Stop falhar, o card permanece na coluna atual.
13. "Pause" encerra o periodo de atendimento. Com um motivo de "aguardando" (usuario/peca/autorizacao) marca esse status; sem motivo, devolve o chamado para "Atribuido" (deixa de ficar "Em atendimento", pois nao ha mais Play ativo), desde que nao haja outro atendimento ativo no mesmo chamado.
14. O encerramento pelo "Stop" registra no historico tecnico a mudanca de status e um evento de finalizacao com quem finalizou e o texto de "O que foi feito" (ex.: "Chamado finalizado por fabiano.polone. O que foi feito: atualizacao do driver e validacao com o usuario."), sem duplicar registros se o chamado ja estiver fechado. Esse texto e registro tecnico de encerramento, separado da conversa do usuario (`ChamadoMensagem`).

## Regras atuais da planilha mensal de atendimentos

1. O cabecalho de cada coluna de **Atendente TI** no Kanban tem um botao de **baixar planilha**. Ele abre um modal que pergunta o **mes** e baixa o `.xlsx` daquele atendente. A lista de meses traz **apenas os meses em que aquele atendente tem atendimento registrado**, com a contagem no rotulo ("Julho 2026 (23 atendimentos)"), mais o **mes atual**, que entra sempre e e o padrao. Meses anteriores ao inicio do controle de tempo nao aparecem, porque sairiam em branco: o sistema so tem periodos Play/Stop desde que essa etapa entrou em uso e os meses antigos foram preenchidos a mao fora dele.
2. A planilha sai no **mesmo modelo que a TI ja preenchia a mao** (`core/planilhas/modelo_atendimentos.xlsx`): mesmas colunas, cores, larguras e formulas de resumo por prioridade. O arquivo se chama `MM-AAAA - <PrimeiroNome>.xlsx`, a aba recebe o nome do mes, `A4` fica "Atendimentos TI Sidertec - MM/AAAA" e `A5` o nome do atendente com o telefone do ramal dele.
3. **Uma linha por atendimento, nao por chamado**: cada Play -> Pause/Stop (`AtendimentoHistorico`) gera uma linha. Um chamado trabalhado em tres dias aparece em tres linhas, exatamente como era preenchido a mao.
4. O mes e recortado pelo **inicio do periodo (Play)**: um atendimento que comeca dia 31 e termina dia 1 fica no mes em que comecou.
5. Preenchimento das colunas: **Data** = hora do Play; **Contato** = solicitante do chamado; **Setor** = setor do solicitante, casado com a lista de **Ramais** (pelo e-mail e, se nao achar, pelo nome, com o mesmo algoritmo do modulo Contatos) e em branco quando nao ha match; **Notificacao** = a **descricao** do chamado, o pedido como o usuario escreveu (vale para migrados e novos; cai para o titulo quando o chamado nao tem descricao, e os metadados que a migracao do sistema antigo anexou ao fim do texto sao removidos); **Prioridade** = **"Programada"** para trabalho da propria TI (criado no Kanban, convertido de pendencia, solicitante TI/admin, ou o tipo "programado" do sistema antigo) e **"Baixa"** para demanda de usuario - **independente da prioridade gravada no chamado**, que e controle interno; **Falha** = "N/A"; **Acao / Correcao** = o que foi feito naquele periodo (o texto obrigatorio do Pause/Stop); **Fechado** = hora do Pause/Stop; **Tempo** = a duracao do periodo, **calculada** e gravada como valor (nao como formula), no formato de tempo decorrido `[h]:mm:ss`. As colunas **Tk** e **Acao Eficaz** ficam vazias. Todas essas escolhas foram conferidas contra a planilha de 05/2026 preenchida a mao, linha por linha.
5a. O **bloco de resumo** do cabecalho (total de chamados e a contagem por prioridade) tambem vem **calculado**. O modelo trazia `SUM`/`COUNTIF` e a coluna Tempo trazia `=Fechado-Data`, mas o openpyxl grava formula **sem valor em cache**: o Excel abria essas celulas em branco e o grafico do resumo lia zero, mesmo com o arquivo pedindo recalculo (`fullCalcOnLoad`). Com o valor pronto, a planilha abre certa em qualquer leitor. Em troca, editar uma linha a mao nao atualiza mais o Tempo nem os contadores sozinho.
5b. O Tempo usa o formato **`[h]:mm:ss`** (tempo decorrido) e nao o `h:mm:ss AM/PM` do modelo, porque existem atendimentos de mais de 24 horas (Play esquecido aberto por dias): no formato antigo, 169 horas apareceriam como "1:37:03 AM".
6. Atendimento **ainda em andamento** (Play aberto na hora do download) entra com a Data preenchida e Fechado/Tempo em branco.
7. **Chamado encerrado direto pelo Stop (sem Play) nao gera linha**, porque nao existe periodo de atendimento (ver regra 10b do controle de tempo). O mesmo vale para chamado aberto no mes que nunca recebeu Play: a planilha e um registro de **tempo trabalhado**, nao de chamados abertos.
8. Qualquer Atendente TI/Admin pode baixar a planilha de **qualquer** atendente (o botao aparece em todas as colunas). E uma diferenca intencional em relacao a tela de Historico, que mostra ao atendente apenas os proprios registros.
9. A planilha e gerada **ao vivo** a partir do banco: se um chamado for editado depois, uma nova baixa do mesmo mes sai diferente. O arquivo baixado (que a TI salva na pasta do mes) e o registro definitivo daquele fechamento.
10. Nao existe hoje exclusao de chamado pela aplicacao (nao ha rota nem registro no admin do Django). Se ela for criada algum dia, `AtendimentoHistorico` tem `on_delete=CASCADE` para `chamado` **e** para `atendente`: apagar um chamado ou um usuario apagaria tambem os periodos de atendimento e mudaria retroativamente as planilhas dos meses ja fechados.

## Atendimentos importados do sistema antigo

1. A migracao original dos chamados trouxe os **757 chamados** e as mensagens, mas **nao** a tabela
   `chamados_ticketattendance` do banco antigo, onde estava o tempo trabalhado. Por isso, ate 07/2026, qualquer
   relatorio baseado em `AtendimentoHistorico` (planilha mensal, tela de Historico) so tinha dados de **15/07/2026**
   em diante, quando o controle de tempo do sistema novo entrou em uso.
2. A migration `0048` importa esses periodos (**886 de 891**; 5 sao descartados por nao ter fim). Ela le
   `seed/chamados_legado.sqlite3` - o banco antigo **nao e versionado**; sem o arquivo, a migration nao faz nada.
3. Mapeamento: **ticket antigo `id` N -> chamado `CH-{N:06d}`**. As faixas nao se cruzam (migrados
   `CH-000003`..`CH-000799`; os criados no sistema novo comecam em `CH-000800`), e cada registro ainda e conferido
   pela data de criacao do chamado antes de gravar.
4. Protecoes da importacao: **nunca cria periodo sem fim** (um `finalizado_em` nulo significa "atendimento ativo",
   sujaria os contadores do Kanban e bloquearia o Play do atendente); ignora periodo que comece a partir do primeiro
   periodo do sistema novo (nao duplica se algum dia os dois tiverem rodado em paralelo); e **idempotente** pela
   chave (chamado, atendente, inicio); e **nao altera nenhum campo de `Chamado`** - status, `atendente_atual` e
   `fechado_em` ficam intactos.
5. O banco antigo grava data/hora **naive em UTC**. Conferido de duas formas: o periodo de 04/05 aparece como
   11:48->17:39 no banco e a planilha preenchida a mao registra 08:48->14:39 (exatamente UTC-3); e a hora de abertura
   dos 757 tickets se concentra entre 11h e 21h, sem nada de manha - como UTC isso e o expediente 08h-18h local.
6. **Pendencia conhecida:** a migracao original leu esses mesmos valores como hora **local**, entao os 757 chamados
   migrados ficaram com `criado_em`/`fechado_em` **3 horas adiantados** no banco novo (afeta o "Aberto em" do Kanban
   e o modal de fechados, nao a planilha). A conferencia da importacao aceita as duas leituras justamente para nao
   depender disso.

## Regras atuais da pausa no fim do expediente

1. Todo dia no fim do expediente (**17:45** por padrao) o comando `pausar_expediente` **pausa em lote** os atendimentos que ficaram com o **Play aberto**. O fim gravado e o proprio horario do corte (17:45), nao a hora em que o comando rodou.
2. **Por que existe:** sem isso, um Play esquecido conta a noite e o fim de semana como tempo trabalhado. Na base de producao havia 14 periodos de mais de 24h - o maior com **7 dias (169h)** - inflando o relatorio mensal. Com a pausa diaria, cada dia trabalhado vira um periodo, e a planilha ganha **uma linha por dia**.
3. O periodo pausado nasce **sem descricao**, porque o atendente nao estava la para dizer o que foi feito. Cada pausa gera uma **pendencia de complemento** (`PausaAutomatica`).
4. **Travamento:** enquanto o atendente tiver pendencia, ele **nao consegue dar Play, pausar nem fechar chamado** - o backend recusa as tres acoes com `409` e a resposta traz `pausas_pendentes`, o que faz a tela abrir direto o modal de preenchimento. A trava e por atendente: a pendencia de um nao bloqueia o outro.
5. **Como o atendente ve:** ao abrir o Kanban com pendencia, aparece um **aviso ambar com ponto pulsante** no topo ("N atendimentos pausados no fim do expediente - o Play, o Pause e o Stop ficam bloqueados ate voce preencher"), uma **notificacao do navegador** (quando permitida) e o **modal abre sozinho**. O modal lista um bloco por atendimento (chamado, dia, periodo e duracao) com um campo obrigatorio "O que foi feito neste periodo?" e um botao Salvar por item; a contagem cai a cada um e, ao zerar, avisa que Play/Pause/Stop foram liberados.
6. O chamado volta para **"Atribuido"** na pausa automatica (nao e espera por terceiros, entao nao entra em "Aguardando").
7. Um Play **iniciado depois do corte** (alguem trabalhando fora do horario) nao e pausado - senao o fim ficaria antes do inicio.
8. **Historico:** a pausa registra `Atendimento pausado automaticamente no fim do expediente (17:45). Pendente de complemento no proximo acesso.` (tipo `pausa_automatica`) e o complemento registra `Complemento da pausa automatica por <atendente>: <texto>` (tipo `complemento_pausa`). Sao os mesmos textos do sistema antigo, para o historico importado e o novo ficarem comparaveis.
9. **Na planilha**, o periodo pausado aparece com a coluna Acao/Correcao preenchida pelo complemento. Enquanto ele nao vier, a celula mostra `Pausa automatica no fim do expediente (pendente de complemento)` - em vez de sair vazia, o que pareceria esquecimento.
10. Nao existe **retomada automatica** no dia seguinte: o atendente da Play quando volta ao chamado. Criar o Play sozinho lancaria horas em dias que ninguem tocou no chamado, que e justamente o problema que a pausa resolve.

## Regras atuais do controle de antivirus (coluna nos Ramais)

1. A lista de **Ramais** tem a coluna **Kaspersky**, com um tique por pessoa. E o controle do antivirus **feito a mao**: substituiu os modulos Contatos/Kaspersky, que cruzavam o inventario do GLPI com o export do portal e produziam numeros que nao fechavam.
2. O tique e clicado **direto na linha** e salva na hora (`POST /ramais/<id>/kaspersky/`, JSON), sem recarregar a pagina. Se o servidor recusar, o tique **volta ao estado anterior** para a tela nao mostrar algo que nao foi gravado.
3. O valor gravado e o que o navegador manda (`instalado: true/false`), nao uma inversao feita no servidor: assim dois cliques rapidos nao se cruzam deixando o registro invertido.
4. A linha inteira continua clicavel para **editar** o ramal; o clique no tique **nao** abre o modal. O checkbox tambem aparece no formulario de cadastro e de edicao.
5. Os cartoes do topo mostram **Com Kaspersky** e **Sem Kaspersky** e sao atualizados a cada tique, sem refresh.
6. A busca cobre os dois estados: digitar `sem kaspersky` (ou `com kaspersky`, `antivirus`) filtra a lista.
7. Somente Atendente TI/Admin alteram (`403` para usuario comum), e a rota aceita apenas `POST`.

## Modulos removidos

Os modulos **Contatos** e **Kaspersky** foram removidos em 30/07/2026 para serem refeitos do zero. As regras antigas deles sairam deste documento (o historico esta no `docs/06_changelog.md`). Os **dados e os models tambem foram apagados** (migration `0050`): eram 83 computadores do GLPI, 44 dispositivos do Kaspersky e os vinculos feitos a mao. Foi decisao consciente de comecar do zero; ha backup do banco de producao de 30/07/2026 no servidor. Os arquivos de origem (CSV do GLPI e export.txt do Kaspersky) reconstroem a lista quando os modulos forem refeitos - o que nao volta sao os ajustes manuais. O **casamento de nome com os Ramais** continua valendo, porque a planilha mensal de atendimentos usa para achar o setor do solicitante e o telefone do atendente.

## Regras atuais do Painel do Titular

- O painel (`/painel/`) e **exclusivo do titular**: apenas o usuario `fabiano.polone` (`PRIMARY_ADMIN_USERNAME`). Ser superusuario ou pertencer ao grupo Administrador **nao** da acesso, porque o painel mexe na interface e nos dados de todos os modulos.
- O botao de entrada fica ao lado da marca "TI" na barra lateral e so e renderizado para o titular.
- Quando o que identifica o registro mora no **vinculo** (a pausa so faz sentido junto do chamado), a coluna aceita o caminho: `atendimento__chamado`, com o rotulo saindo do ultimo pedaco (`CHAMADO`). Sem isso o chamado ficava escondido dentro do texto do atendimento ("fabiano - CH-000888"), lido de relance como nome de pessoa.
- **A lista identifica; o registro mostra tudo.** Cada tabela lista so o que distingue o registro (o titulo, o nome, o numero) — uma coluna, ou duas quando uma nao basta (o filho precisa do pai, o periodo precisa da data). Todos os demais campos aparecem ao abrir o registro, que ja mostra o modelo inteiro. **A busca continua cobrindo os campos que sairam da lista**: da para achar o ramal pelo setor ou pelo telefone mesmo sem essas colunas na tela. As excecoes sao as **trilhas** (eventos do chamado, auditoria do cofre e do painel), que ficam com tres colunas porque ali a lista **e** o conteudo: sao feitas para ler correndo, nao para abrir uma a uma.
- **Abrir registro nao usa ENTER.** O numero digitado abre na hora quando nao pode ser o comeco de outro da lista; quando pode (o `1` numa pagina que tem linha `10`), o terminal espera **um segundo** pelo segundo digito e abre sozinho se ele nao vier — tempo de quem digita olhando para a tela, nao de quem decora a lista. Na pratica so a linha `1` espera; as outras abrem na hora. O ENTER continua valendo para quem ja apertou por habito, e so e obrigatorio em campo de texto livre.
- A **lista numera 1, 2, 3... sem zero a esquerda**, porque `0` e a tecla de voltar: mostrar "01" convidava a digitar um zero que sai da tela em vez de abrir o registro. O numero da linha aparece exatamente como se digita.
- A navegacao e de terminal: a tecla executa na hora (sem ENTER e sem setas), ESC volta um nivel de cada vez (entrada de texto -> numero digitado -> selecao -> busca -> tela anterior) e o ENTER so vale em campo de texto livre. O clique do mouse repete a mesma acao da tecla.
- **Toda acao que grava** (interface, usuarios, dados, operacao) e registrada em `PainelAuditoria`, com quem fez, quando, o alvo e o antes/depois.
- **Modulos**: a area `[5] MODULOS` lista os mesmos botoes do menu lateral (na ordem e com o rotulo em uso) e abre cada um por dentro: as tabelas daquele modulo, para listar, buscar, criar, alterar e excluir sem sair do terminal. `T` pula para a tela classica do modulo. Modulo escondido do menu continua acessivel por aqui. O mapa fica em `core/painel_modulos.py`, e cada modulo avisa o que **so** existe na tela classica (upload de arquivo, PDF do termo, importacao de CSV, arrastar do Kanban, senha do Cofre).
- **Criar registro** (`N` na tela da tabela): o terminal pergunta **apenas os campos obrigatorios**, um por vez, mostrando o tipo aceito e as opcoes validas ao lado do cursor; grava e abre o registro para completar o resto campo a campo. O que o sistema gera nao e perguntado (numero do chamado, codigo da requisicao) e o autor (`criado_por`) passa a ser quem opera o painel. Campo obrigatorio vazio e recusado no backend — o `blank` do Django so vale em formulario, entao sem essa checagem o painel gravaria registro pela metade.
- **Acoes de fluxo**: alem da escrita generica na tabela, o terminal executa as acoes do proprio modulo — abrir chamado, Play, Pause, Stop, atribuir/devolver chamado, criar pendencia, trocar prioridade, converter pendencia em chamado, aprovar orcamento, marcar requisicao como entregue, desaprovar e nao aprovar. **A regra nao e repetida no painel**: cada acao chama a mesma rota que a tela classica usa, entao o chamado aberto por aqui nasce com evento na linha do tempo e com a notificacao por e-mail, igual ao Kanban. O terminal so pergunta o que falta (um campo por vez) e mostra a resposta. Quando existe acao de fluxo, ela **substitui** o `N` generico da tabela, que pularia essas regras. A acao so aparece quando cabe no registro (chamado encerrado nao recebe Play/Pause/Stop, mas continua aceitando mensagem, como na tela; pendencia ja convertida nao converte de novo; o OK da documentacao so depois que o termo assinado subiu) e o catalogo fica em `core/painel_acoes.py`.
- **Data no terminal** se digita como no resto do sistema (`DD/MM/AAAA`), inclusive nas acoes de fluxo: a conversao para o formato que a rota le (ISO) e feita no proprio terminal, para nao existirem dois formatos na cabeca de quem opera.
- **Assinatura do termo**: aplicar a rubrica do responsavel e a acao `S` do emprestimo (ID da assinatura + senha de autorizacao, mascarada); a rota confere a senha e refaz o termo, e a senha errada e recusada com `403`, como na tela. A rubrica em si abre pela acao `T` da tabela de Assinaturas.
- **Emprestimo**: o terminal cria o emprestimo **com o primeiro equipamento e o termo em PDF** (`N`), acrescenta equipamento (`Q`) e marca **devolucao** pelo registro do equipamento (`D`, com a data de hoje) — a rota que recebe e a do emprestimo, entao os dados dele voltam no POST e os outros equipamentos ficam como estao. Devolvido o ultimo, o emprestimo inteiro passa a **Devolvido**; qualquer alteracao refaz o termo e volta a aguardar assinatura, igual a tela. A **assinatura do responsavel** (que pede a senha de autorizacao) continua so na tela de Emprestimos.
- **O terminal usa os recursos do navegador**, porque e uma pagina como qualquer outra. Ha dois formatos de acao alem do envio comum: **`arquivo`**, que abre o **seletor de arquivo do proprio computador** e manda o escolhido pela rota da tela classica (`request.FILES`); e **`abrir`**, que nao envia nada — abre a URL numa aba nova e deixa o navegador fazer o que ja sabe com PDF, planilha e imagem. Nao ha visualizador proprio no painel, de proposito.
- **O que na tela e gesto, no terminal e tecla.** Interacao que nao cabe num terminal nao vira "so na tela": vira acao de menu. Arrastar o card do Kanban e `M` (atribuir) e `D` (devolver); o botao de copiar do modal da requisicao e `W` (WhatsApp) e `C` (e-mail em texto), montando a mensagem com o **mesmo arquivo** que a tela usa (`static/js/requisicao_texto.js`), nao com uma segunda copia da formatacao.
- **Requisicao**: `titulo`, `tipo` e `texto` **nao** se editam campo a campo — passam pela rota do modulo (`E`), que registra a edicao na linha do tempo da requisicao; criar tambem e pela rota (`N`), que gera o codigo `REQ-` e o evento de criacao.
- **Anexos**: cada tabela de anexo do sistema (chamado, mensagem, documento, servico feito, contrato TI, orcamento, suborcamento e foto de equipamento) esta no catalogo do painel, para **achar e abrir** qualquer arquivo sem sair do terminal (`T` abre em outra aba). O campo do arquivo **nunca** e editavel; excluir a linha do anexo apaga o arquivo do disco pelo signal `post_delete`. Enviar arquivo e sempre pela acao do modulo dono (`Y`), nunca pela camada generica.
- **Configuracao de e-mail**: os campos do SMTP se ajustam campo a campo, como qualquer tabela — e por isso **nao** existe o risco do formulario inteiro (a rota da tela le caixa nao marcada como desligada). A **senha do SMTP** nao e campo do painel: troca pela acao `Y`, que chama a rota da tela espelhando o resto da configuracao, e o **e-mail de teste** sai pela acao `T`.
- **Senha-mestra** se define e se troca pelo terminal (`M`, tres campos mascarados), pela mesma rota da tela — que exige a senha atual quando ja existe uma e continua sendo so do administrador.
- **Cofre pelo terminal**: a senha **nao e campo da tabela** e continua invisivel para a camada generica. O que existe sao as acoes do proprio Cofre: destravar com a **senha-mestra** (`Z`, digitada mascarada), travar (`L`), nova credencial (`N`), **revelar** (`V`), trocar a senha (`Y`) e excluir (`X`). Quem decide e a rota de sempre — cofre travado recusa, e **cada revelacao entra na auditoria**. O destrave vale para a sessao inteira, aqui e na tela do Cofre. A senha revelada aparece **literal** (sem caixa alta), porque so serve exatamente como foi guardada, e some na tecla seguinte.
- **Estoque de insumo**: o saldo (`quantidade_atual`) **aparece mas nao e editavel** pelo painel — quem mexe nele e a acao de **entrada** (`E`) ou **retirada** (`S`), que gravam o movimento no extrato junto. Alterar o numero na mao mudaria o saldo e deixaria o extrato mentindo; a trava vale tambem na criacao do insumo (o estoque inicial entra como entrada).
- **Rotas de tela no terminal**: modulo escrito para tela responde `redirect` + `messages`, e ai falha e sucesso ficam iguais para quem chama por `fetch`. Em vez de criar rota paralela, a **mesma view** responde JSON quando o pedido vem por XHR (`core/xhr.py`), lendo as mensagens que ela mesma produziu: mensagem de erro vira `ok: false` com o texto que a tela mostraria.
- **Pausas automaticas** entram no painel como **fila de trabalho**, nao como historico: a tabela lista **so as que faltam complementar** (`PAUSAS A COMPLEMENTAR`). Complementada, some da lista — o texto dela ja esta na linha do tempo do chamado e na planilha do mes. Continua abrindo pelo ID, se precisar. A contagem que aparece na area MODULOS usa o mesmo recorte, para o numero nao mentir em relacao a tela.
- **Pausa automatica**: o complemento so aparece para **quem atendeu**. A regra e da rota (o texto vai para o historico e para a planilha com o nome da pessoa), entao o painel nem oferece a tecla na pausa dos outros — o titular nao complementa pelo atendente.
- **Interface**: o titular pode esconder, renomear e reordenar os itens do menu lateral de TI; a mudanca vale para toda a equipe na proxima carga de pagina. "Voltar ao padrao" apaga o ajuste do item e "restaurar tudo" apaga todos, devolvendo o catalogo de fabrica (`core/menu.py`).
- **Usuarios**: da e tira os grupos Administrador e Atendente TI e ativa/desativa a conta. Tirar de Administrador tambem tira `is_staff`/`is_superuser`. **A conta do titular nao pode ser alterada pelo painel** (responde `409`), para nao existir caminho de auto-rebaixamento.
- **Dados**: lista, busca, abre, altera campo a campo e exclui registros das tabelas do catalogo. Regras fixas desta area:
  - campos de segredo (senha, hash, texto cifrado, token) **nunca** aparecem nem podem ser alterados — as credenciais do Cofre continuam so no Cofre, com a senha-mestra;
  - arquivos e imagens aparecem so pelo nome e nao sao editaveis (upload continua pela tela do modulo, que trata o disco);
  - `id` e campos automaticos (`auto_now`, `auto_now_add`) sao somente leitura;
  - tabelas marcadas como somente leitura (eventos de chamado, auditorias, Cofre) nao aceitam alteracao nem exclusao;
  - o valor digitado segue o padrao brasileiro: data `DD/MM/AAAA`, data e hora `DD/MM/AAAA HH:MM`, booleano `S`/`N`, vinculo pelo ID do registro.
- **Operacao**: mostra o estado do servidor (Python/Django, banco, migracoes, tamanho do `media`, DEBUG, hora), os atendimentos com Play em aberto, as pausas sem complemento e a trilha do painel; executa `pausar_expediente` (com confirmacao) e sua simulacao, `clearsessions` e o `check` do Django.
- Acoes destrutivas pedem confirmacao S/N e a confirmacao ignora teclas nos primeiros instantes, para que uma digitacao rapida nao confirme sozinha.

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
6. O chamado gerado recebe: titulo e descricao da pendencia, `solicitante` = quem criou a pendencia, `atendente_atual` = atendente da coluna destino e status "Atribuido" (ainda sem Play ativo).
7. Apos converter, a pendencia sai da coluna "Pendencias" e o novo chamado aparece no topo da coluna do atendente (abaixo dos que estao com Play), sem refresh.
7a. A coluna "Pendencias" lista as pendencias mais recentes no topo (ordenacao por data/hora de criacao decrescente); uma pendencia recem-criada entra no topo.
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

## Regras atuais do modulo Requisicoes

> Observacao: na interface o modulo se chama "Requisicoes". Os nomes tecnicos internos (models `RequisicaoContrato`/`OrcamentoContrato`/..., rotas `/contratos/...` e arquivos `contratos.*`) ainda usam o prefixo `Contrato` e foram mantidos para nao gerar migration/quebra; nao ha mais o termo "Contratos" na interface.

1. O modulo Requisicoes e acessivel apenas para Administrador e Atendente TI; o botao "Requisicoes" no menu lateral so aparece para esses perfis e todas as rotas validam a permissao no backend (usuario comum nao ve o botao, e redirecionado na tela e recebe `403`/`404` nos endpoints).
2. A tela principal lista as requisicoes cadastradas mostrando apenas codigo, titulo e status, com um botao "+ Adicionar" (responsivo: mostra apenas "+" em telas menores) para criar nova requisicao. O card superior e compacto, alinhando titulo, subtitulo e botao na mesma linha em telas maiores.
2a. Acima da lista ha uma **pesquisa inteligente** que filtra **a cada tecla digitada** (sem recarregar a pagina e sem ida ao servidor) e acha **qualquer coisa da requisicao**, nao so o que aparece na linha: codigo, titulo, tipo, status, descricao, quem criou, data de criacao, quem entregou e todos os **orcamentos e suborcamentos** (titulo, loja, link, valor unitario e total) com os **nomes dos documentos anexados**; orcamento aprovado tambem responde por "aprovado". A busca **ignora acentos e maiusculas** e aceita **varias palavras** (todas precisam bater, em qualquer ordem — ex.: "notebook rh"). Abaixo do campo fica o contador ("X de Y requisicao(oes) encontrada(s)"), sem resultado aparece "Nenhuma requisicao encontrada para esta pesquisa." e `Esc` limpa a pesquisa. O texto pesquisavel e montado no backend (`_requisicao_busca_texto`, no `data-search` de cada item) e e reconstruido no navegador sempre que o detalhe da requisicao e carregado, para a busca acompanhar o que foi criado/editado na sessao (novo orcamento, outra loja, mudanca de status) sem precisar recarregar.
3. A requisicao tem titulo, tipo (Fisica ou Digital) e texto; o status inicial e sempre "Aberta" (definido pelo sistema), com `criado_por` = usuario logado e data automatica. Status disponiveis: Aberta, Em cotacao, Finalizada, Cancelada (sem fluxo de aprovacao por enquanto).
4. Clicar em uma requisicao abre um modal com todos os seus dados e os orcamentos vinculados; cada orcamento exibe seus suborcamentos logo abaixo, indentados.
5. Uma requisicao pode ter varios orcamentos; cada orcamento pode ter varios suborcamentos (complementos). O suborcamento nunca aparece como orcamento independente.
6. Orcamento e suborcamento tem os mesmos campos: titulo, loja, moeda (Real/Dolar), valor, quantidade, frete, desconto, link, foto do produto e documentos anexos (multiplos, sem restricao de tipo/tamanho no codigo).
7. Regra de calculo: total do orcamento = valor x quantidade + frete - desconto; o total exibido do orcamento tambem considera a soma dos totais de todos os seus suborcamentos.
8. O backend valida a moeda, exige quantidade minima 1 e bloqueia valores negativos em valor, frete e desconto, com mensagens amigaveis.
9. O botao "Tirar print" captura a tela pelo navegador (`getDisplayMedia`), permite recortar uma regiao, pre-visualizar e refazer/remover; o recorte e salvo como foto do produto. Sem suporte do navegador, o sistema orienta a anexar imagem manualmente e nao trava o formulario se a captura for cancelada.
10. Fotos e documentos ficam em `MEDIA_ROOT/contratos/...` e sao servidos por rotas protegidas; usuario sem permissao nao acessa os arquivos.
11. Ao abrir o detalhe de uma requisicao, o Atendente TI/Admin ve a opcao "Excluir" (discreta, no rodape do modal). O clique abre uma confirmacao obrigatoria ("Tem certeza que deseja excluir esta requisicao? Esta acao nao podera ser desfeita.") com os botoes "Cancelar" e "Excluir definitivamente" (estilo perigoso); nada e excluido sem confirmacao.
12. A exclusao e feita via `POST` com CSRF (nunca por GET) e validada no backend (usuario comum recebe `403`). Ela remove a requisicao e, por cascata, todos os orcamentos, suborcamentos e documentos vinculados. Apos excluir, a requisicao some da lista sem refresh; em caso de erro, ela permanece visivel e uma mensagem e exibida. Os arquivos fisicos anexados nao sao removidos do disco (pendencia conhecida).
13. Cada orcamento no detalhe tem o botao "Aprovar orcamento". A aprovacao e exclusiva por requisicao: aprovar um orcamento remove a aprovacao dos demais e move a requisicao para "Aguardando entrega". Remover a aprovacao (botao "Remover aprovacao"), quando nenhum orcamento fica aprovado, volta a requisicao para "Esperando aprovacao". O orcamento aprovado fica destacado (borda verde + chip) e o badge de status atualiza na lista e no detalhe sem refresh. A acao e `POST` com CSRF, restrita a TI/admin (usuario comum recebe `403`), e alterna o estado do orcamento (`aprovado`/`aprovado_em`/`aprovado_por`).
14. Com a requisicao "Aguardando entrega", o orcamento aprovado passa a exibir o botao "Marcar entregue". Ao marcar (`POST /contratos/requisicoes/<id>/marcar-entregue/`, TI/admin), a requisicao vai para "Entregue" com `entregue_em`/`entregue_por` e o orcamento mostra o estado "Entregue". Depois de entregue nao e possivel alterar a aprovacao (retorna `409`); marcar entregue exige um orcamento aprovado (`409` se nao houver).
15. Cada requisicao tem um **codigo** sequencial (`REQ-00049`, ...), unico, gerado no cadastro, continuando a numeracao do sistema antigo (que parou em `REQ-00048`). O codigo aparece na lista e no cabecalho do detalhe.
16. O detalhe mostra o **historico** da requisicao (timeline, mais recentes no topo) com criacao, aprovacao/desaprovacao de orcamento e entrega, cada evento com autor e data/hora (`RequisicaoContratoEvento`).
17. A requisicao pode ser **editada** pelo botao "Editar requisicao" (rodape do detalhe, TI/admin), que reabre o formulario pre-preenchido para alterar titulo, tipo e texto (`POST /contratos/requisicoes/<id>/editar/`). A edicao registra um evento de edicao na timeline (`TIPO_EDICAO`) e nao altera status, aprovacao nem orcamentos.
18. Cada orcamento e cada suborcamento pode ser **editado** pelo botao "Editar" no card (TI/admin), que abre o mesmo formulario de cadastro em modo edicao. E possivel alterar todos os campos, **trocar ou remover a foto do produto** e **adicionar ou remover documentos** ja anexados. A edicao de orcamento/suborcamento e **bloqueada** (`409`) quando a requisicao ja foi entregue (mesma regra da aprovacao) e nao altera o estado de aprovacao do orcamento. Os arquivos removidos saem do disco pelos signals `post_delete` de `core/signals.py`.
19. A requisicao pode ser **desaprovada por inteiro** pelo botao "Desaprovar requisicao" (rodape do detalhe, TI/admin), que so aparece quando ha um orcamento aprovado (status "Aguardando entrega"). Ao desaprovar (`POST /contratos/requisicoes/<id>/desaprovar/`), a aprovacao de **todos os orcamentos** e removida (`aprovado`/`aprovado_em`/`aprovado_por` limpos) e a requisicao volta para "Esperando aprovacao", registrando um evento na timeline. Exige ao menos um orcamento aprovado (`409` se nao houver) e e bloqueado apos a entrega (`409`). Equivale a remover a aprovacao pelo botao do proprio orcamento, mas em nivel de requisicao.
19a. O rodape do detalhe tem dois botoes de copia, lado a lado (so frontend, nao alteram nada no sistema): **"Copiar p/ WhatsApp"** (texto com a marcacao do WhatsApp, sem links) e **"Copiar p/ e-mail"** (HTML formatado, pronto para colar no corpo do e-mail). Nenhuma das duas copias leva tipo nem status da requisicao (controle interno) nem assinatura/rodape do sistema — o conteudo termina no ultimo orcamento. A versao de e-mail leva cabecalho (codigo, titulo, solicitante/data e entrega quando houver), descricao e cada orcamento com **foto do produto embutida (data URI)**, loja, valor unitario, quantidade, frete, desconto, link clicavel, total, nomes dos documentos anexados e os suborcamentos indentados, alem do total com suborcamentos. Fotos acima de 3 MB nao entram no corpo (fica o aviso de que a foto esta no sistema). A area de transferencia recebe tambem uma versao em **texto puro** do mesmo conteudo. Os documentos anexados nao sao copiados como arquivo — apenas os nomes; quem precisar do arquivo baixa pelo sistema.
19b. A requisicao pode ser marcada como **"Nao aprovada"** pelo botao **"Nao aprovar"** (rodape do detalhe, TI/admin): a compra foi recusada e o assunto se encerra. Ao clicar (`POST /contratos/requisicoes/<id>/nao-aprovar/`), a requisicao entra no status **"Nao aprovada"** (badge vermelho na lista e no detalhe) e a aprovacao de qualquer orcamento e removida (nada sera comprado), com evento na timeline. O botao **alterna**: com a requisicao ja recusada ele vira **"Reabrir requisicao"** e devolve a requisicao para "Esperando aprovacao" (tambem registrado na timeline). Fica **bloqueado apos a entrega** (`409`) e oculto no detalhe de uma requisicao entregue. Nao confundir com "Desaprovar requisicao" (19), que apenas tira a aprovacao dos orcamentos de uma requisicao em "Aguardando entrega" e a devolve para "Esperando aprovacao", mantendo a compra em andamento.
20. Ao **criar** um suborcamento, o formulario mostra a opcao **"Criar este suborcamento em todos os orcamentos da requisicao"** (checkbox **desmarcado por padrao**, visivel apenas na criacao de suborcamento — nao aparece em orcamento nem na edicao). Desmarcado, o suborcamento entra so no orcamento atual (comportamento padrao). Marcado, o mesmo suborcamento (com os mesmos campos, **foto e documentos**) e criado em **cada orcamento principal** da requisicao, inclusive o atual; o backend envia `aplicar_todos_orcamentos` e replica os itens (arquivos reaproveitados com o ponteiro reposicionado). Restrito a TI/admin (`403` para usuario comum).

## Regras atuais do modulo Insumos

1. O modulo Insumos e acessivel apenas para Administrador e Atendente TI; o botao "Insumos" no menu lateral so aparece para esses perfis e todas as rotas validam a permissao no backend (usuario comum nao ve o botao e recebe `403`/redirecionamento).
2. A tela tem duas areas: "Estoque de insumos" (cards com nome, descricao, quantidade atual, status visual e botao "Retirar") e "Ultimas retiradas" (tabela com insumo, quantidade, entregue para, motivo, quem registrou e data/hora).
3. O status visual do insumo e: "Disponivel", "Baixo estoque" (quantidade <= 5) ou "Sem estoque" (quantidade 0), com destaque discreto por cor.
4. O cadastro de insumo pede nome, descricao, quantidade inicial (obrigatoria, nao negativa) e observacao; o insumo aparece no estoque sem refresh.
5. A retirada pede quantidade, para quem vai e motivo (todos obrigatorios). O backend valida que a quantidade e maior que zero e nao excede o estoque; caso contrario, bloqueia com mensagem.
6. Ao confirmar a retirada, o estoque e abatido, um registro e gravado no historico e o card e a tabela sao atualizados sem refresh.
7. O historico de retiradas nunca e apagado; insumos nao sao excluidos automaticamente (ha o campo `ativo` preparado para desativacao futura, ainda nao usado na interface).

## Regras atuais do modulo Documentos

1. O modulo Documentos e acessivel apenas para Administrador e Atendente TI; o botao "Documentos" no menu lateral so aparece para esses perfis e todas as rotas validam a permissao no backend (usuario comum nao ve o botao, recebe `403` nos endpoints e `404` ao tentar baixar anexos por URL direta).
2. A tela lista os documentos cadastrados mostrando nome, observacao resumida, quantidade de anexos, data de cadastro e quem cadastrou.
3. O cadastro pede nome (obrigatorio), observacao e permite anexar multiplos arquivos (sem restricao de tipo ou tamanho no codigo); ao salvar, o documento e seus anexos sao gravados e o item aparece na lista sem refresh.
4. Clicar em um documento abre um modal com nome, observacao completa, anexos vinculados (com link para abrir/baixar), data de cadastro e quem cadastrou.
5. Os anexos sao servidos por rota protegida; apenas TI/admin conseguem abrir/baixar. Documentos e anexos nao sao apagados automaticamente (ha o campo `ativo` preparado para desativacao futura, ainda nao usado na interface).

## Regras atuais do modulo Emprestimos

1. O modulo Emprestimos e acessivel apenas para Administrador e Atendente TI; o botao no menu lateral so aparece para esses perfis e todas as rotas validam a permissao no backend (usuario comum nao ve o botao, recebe `403`/redirecionamento e `404` no download do termo).
2. A tela lista os emprestimos (colaborador, empresa, equipamento principal, quantidade de equipamentos, data, previsao de devolucao e status). Clicar em um emprestimo abre um modal com todos os detalhes, equipamentos, fotos, termo e opcoes de documentacao.
3. Um emprestimo pode ter 1 ou varios equipamentos. Os dados do colaborador, empresa, assinatura e senha de autorizacao sao preenchidos uma unica vez; cada equipamento tem tipo, marca, modelo, numero de serie, patrimonio, acessorios e pode ter varias fotos. No termo os itens aparecem como Equipamento 1, 2, 3...
4. Se a previsao de devolucao ficar em branco, o emprestimo e tratado como prazo indeterminado e o termo exibe "Indeterminada".
5. A assinatura do responsavel de TI e cadastrada com nome, imagem e senha de autorizacao. A senha e guardada com hash seguro (nunca em texto puro). Para aplicar a assinatura no termo, e preciso informar a senha correta na criacao do emprestimo; senha errada bloqueia a aplicacao. Cada uso autorizado da assinatura e registrado (quem usou e quando) e esse historico nao e apagado.
6. Apos cadastrar o emprestimo, o sistema gera automaticamente o termo em PDF (modelo institucional da Sidertec), que fica vinculado ao emprestimo e pode ser baixado. O status inicial e "Aguardando documentacao assinada".
7. O termo assinado devolvido pelo colaborador pode ser anexado no detalhe (registrando data e usuario). Ao marcar a documentacao como OK, o status muda para "Documentacao assinada / OK" (exige o termo assinado ja anexado). Status disponiveis: Aguardando documentacao assinada, Documentacao assinada / OK, Em andamento, Devolvido, Cancelado.
8. Cada equipamento tem a **sua propria data de emprestimo** e uma **data de devolucao** (opcional). Isso permite manter um contrato unico por pessoa e ir adicionando equipamentos em momentos diferentes, com a data de cada um (linha do tempo). No termo, os equipamentos ativos aparecem com "Emprestado em <data>" e, quando ha itens ja devolvidos, uma secao "Equipamentos ja devolvidos" lista cada um com a data de emprestimo e de devolucao.
9. O emprestimo pode ser **editado** (botao "Editar emprestimo" no detalhe, apenas TI/admin): atualizar dados do colaborador, **adicionar** novos equipamentos, **marcar equipamentos como devolvidos** (com a data) ou **remover** equipamentos (apaga do registro e as fotos do disco). Nao e permitido ficar sem nenhum equipamento.
10. Qualquer edicao **regera o termo em PDF** e **descarta o termo assinado anterior** (o conteudo mudou). Se ainda houver equipamento em posse do colaborador, o status volta para "Aguardando documentacao assinada" (para colher a nova assinatura); se todos os equipamentos ficarem devolvidos, o status passa para "Devolvido". Assim como na criacao, e possivel aplicar a assinatura no novo termo informando a senha de autorizacao.
11. Toda a validacao (permissao, senha da assinatura, obrigatoriedade de equipamento e datas) e feita no backend.

## Regras atuais do modulo E-mail (notificacoes)

1. As notificacoes por e-mail sao configuradas em `/email-config/`, acessivel a Administrador e Atendente TI (o botao "E-mail" no menu lateral so aparece para esses perfis; as rotas validam a permissao no backend). O envio so acontece com a chave "Ativar notificacoes" ligada.
2. A configuracao (servidor SMTP, conta de envio, senha de app, remetente, e-mails da TI e quais eventos disparam) fica no banco em um registro unico (`EmailConfig`). Os defaults ja vem prontos para o Google/Gmail (`smtp.gmail.com`, porta 587, TLS). A **senha de app do Google e guardada cifrada** (Fernet, mesmo esquema do Cofre) — nunca em texto no banco, no codigo ou na doc.
3. Eventos que disparam e-mail (cada um com liga/desliga proprio):
   - **Novo chamado**: enviado ao **solicitante** (confirmacao de abertura) e aos **e-mails da TI**. Vale para chamados abertos pelo portal, criados no Kanban e gerados a partir de uma pendencia.
   - **Nova mensagem** na conversa: notifica a **outra parte** (se o solicitante escreveu, avisa a TI; se a TI escreveu, avisa o solicitante) mais os e-mails da TI, sem enviar copia para quem escreveu.
   - **Mudanca de status** do chamado (movimentacao no Kanban): notifica solicitante e TI.
   - **Fechamento** do chamado (acao Stop): notifica solicitante e TI, incluindo o "o que foi feito".
4. O envio e **tolerante a falhas**: se o SMTP estiver mal configurado ou fora do ar, o erro e apenas registrado em log e **nunca impede** abrir, mover, responder ou fechar o chamado. Ha um botao de **enviar e-mail de teste** que, ao contrario, mostra o erro real do servidor para ajudar a configurar.
5. **Solicitante que e da propria TI**: quando o solicitante do chamado e um Atendente TI/Admin (ex.: um atendente abre um chamado para si mesmo no Kanban ou converte uma pendencia que ele mesmo criou), ele **nao recebe a copia pessoal** (a confirmacao "solicitante") em nenhum dos eventos — recebe apenas pela lista de e-mails da TI. Isso evita receber a mesma acao duas vezes (uma como solicitante, no e-mail pessoal, e outra como equipe, pela lista `ti@...` que tambem chega nele). O dedup por endereco continua valendo para os demais casos.

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
