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
13. "Pause" encerra o periodo de atendimento. Com um motivo de "aguardando" (usuario/peca/autorizacao) marca esse status; sem motivo, devolve o chamado para "Atribuido" (deixa de ficar "Em atendimento", pois nao ha mais Play ativo), desde que nao haja outro atendimento ativo no mesmo chamado.
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
2. A tela principal lista as requisicoes cadastradas mostrando apenas titulo e status, com um botao "+ Adicionar" (responsivo: mostra apenas "+" em telas menores) para criar nova requisicao. O card superior e compacto, alinhando titulo, subtitulo e botao na mesma linha em telas maiores.
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
