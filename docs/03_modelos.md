# 03 - Modelos

## Situacao atual

O projeto possui vinte e um modelos persistidos:

Fluxo de atendimento (Chamados):

- `Chamado`
- `ChamadoEvento`
- `ChamadoAnexo`
- `ChamadoMensagem`
- `ChamadoMensagemAnexo`
- `PendenciaTI`
- `AtendimentoHistorico`

Modulo Requisicoes (exibido como "Requisicoes" na interface; os models mantem o prefixo tecnico `Contrato`):

- `RequisicaoContrato`
- `OrcamentoContrato`
- `OrcamentoDocumento`
- `SuborcamentoContrato`
- `SuborcamentoDocumento`

Modulo Insumos:

- `InsumoTI`
- `RetiradaInsumoTI`

Modulo Documentos:

- `DocumentoTI`
- `DocumentoTIAnexo`

Modulo Emprestimos:

- `EmprestimoTI`
- `EquipamentoEmprestimoTI`
- `FotoEquipamentoEmprestimoTI`
- `AssinaturaResponsavelTI`
- `LogUsoAssinaturaTI`

## Modelos implementados

### Chamado

Representa o cadastro minimo de um chamado para permitir evolucao do dashboard mockado para persistencia real.

Campos atuais:

- `numero`
- `titulo`
- `descricao`
- `solicitante` (FK opcional para o usuario que abriu o chamado no portal)
- `solicitante_nome`
- `solicitante_email`
- `departamento`
- `categoria`
- `subcategoria`
- `prioridade` (choices: `baixa`, `media`, `alta`, `critica`)
- `status` (choices: `aberto`, `em_atendimento`, `aguardando_usuario`, `resolvido`, `fechado`; default `aberto`)
- `atendente_atual` (FK opcional para o usuario que realizou a ultima acao; **nao representa dono do chamado**)
- `origem`
- `aberto_em_referencia`
- `ultima_atualizacao_referencia`
- `fechado_em` (data de encerramento, quando aplicavel)
- `criado_em`
- `atualizado_em`

Metodos e propriedades:

- `Chamado.gerar_numero()` gera um numero sequencial unico no formato `CH-000123` para chamados abertos pelo portal do solicitante.
- `status_label` e `prioridade_label` retornam o rotulo legivel do valor armazenado.
- `STATUS_ENCERRADOS` agrupa os status `resolvido` e `fechado`.

Metodos e propriedades (continuacao):

- `atendente_atual` e distinto de `solicitante`: o solicitante e o dono/criador do chamado; o `atendente_atual` e apenas quem realizou a ultima acao de atendimento.

Observacoes:

- Chamados abertos pelo portal do solicitante nascem com `solicitante`, `numero` gerado, `status = aberto` e `origem = "Portal do solicitante"`.
- O Kanban da TI usa exclusivamente chamados reais do banco, agrupados pelo campo `status` (sem dados mockados).
- O Kanban e organizado por fila: coluna fixa de abertos, colunas dinamicas por usuario do grupo `Atendente TI` e coluna fixa de fechados.
- A movimentacao pelo Kanban grava `status` e `atendente_atual` conforme a coluna de destino; ao fechar, `fechado_em` e preenchido e o atendente que fechou e registrado; ao voltar para abertos, o `atendente_atual` e limpo.
- O campo `numero` e unico e serve como chave de referencia entre o Kanban, o portal e o backend.
- `solicitante` e `atendente_atual` usam `on_delete=SET_NULL` para preservar o chamado mesmo se o usuario for removido.

### ChamadoEvento

Log de eventos/acoes de um chamado ao longo da sua vida (historico do chamado, separado do controle de tempo).

Campos atuais:

- `chamado` (FK para `Chamado`, `on_delete=CASCADE`, related_name `eventos`)
- `usuario` (FK opcional para quem realizou a acao, `on_delete=SET_NULL`)
- `tipo` (choices: `criacao`, `mudanca_status`, `atendente_alterado`, `comentario`)
- `descricao` (texto claro da acao)
- `criado_em`

Eventos registrados atualmente:

- Criacao do chamado (`criacao`): "Chamado aberto por X."
- Mudanca de status (`mudanca_status`): "Status alterado de A para B por X."
- Atendente que assumiu/movimentou (`atendente_alterado`): "Chamado assumido por X." (registrado apenas quando o `atendente_atual` muda, evitando duplicidade)

### ChamadoAnexo

Armazena os arquivos anexados a um chamado no momento da abertura pelo portal do solicitante.

Campos atuais:

- `chamado` (FK para `Chamado`, `on_delete=CASCADE`, related_name `anexos`)
- `arquivo` (`FileField`, salvo em `MEDIA_ROOT/chamados/<numero>/<arquivo>`)
- `nome_original`
- `enviado_por` (FK opcional para o usuario, `on_delete=SET_NULL`)
- `enviado_em`

Regras atuais:

- Um chamado pode ter varios anexos.
- Nao ha restricao de tamanho nem de extensao de arquivo neste momento.
- Os arquivos ficam sob `MEDIA_ROOT` e sao servidos por `MEDIA_URL` (em desenvolvimento, servidos pelo proprio Django com `DEBUG=True`).

### ChamadoMensagem

Mensagem da conversa entre o solicitante e o Atendente TI dentro de um chamado. A conversa e separada do historico tecnico (`ChamadoEvento`): aqui fica o conteudo trocado; la fica apenas o resumo da acao.

Campos atuais:

- `chamado` (FK para `Chamado`, `on_delete=CASCADE`, related_name `mensagens`)
- `autor` (FK opcional para quem escreveu, `on_delete=SET_NULL`)
- `texto` (conteudo da mensagem)
- `criado_em`

Regras atuais:

- Uma mensagem precisa ter texto OU pelo menos um anexo (nao pode ser totalmente vazia); a validacao ocorre no backend.
- A origem da mensagem (solicitante x TI) e determinada comparando o `autor` com o `solicitante` do chamado.
- Cada mensagem enviada gera um `ChamadoEvento` do tipo `comentario` com um resumo (sem repetir o texto da conversa).

### ChamadoMensagemAnexo

Arquivo opcional vinculado a uma mensagem da conversa.

Campos atuais:

- `mensagem` (FK para `ChamadoMensagem`, `on_delete=CASCADE`, related_name `anexos`)
- `arquivo` (`FileField`, salvo em `MEDIA_ROOT/chamados/<numero>/mensagens/<arquivo>`)
- `nome_original`
- `enviado_em`

Regras atuais:

- Uma mensagem pode ter varios anexos, todos opcionais.
- Nao ha restricao de tamanho nem de extensao neste momento.
- O download usa rota dedicada e protegida (nao expoe a URL direta de `MEDIA`).

### PendenciaTI

Pendencia da equipe de TI exibida na coluna "Pendencias" do Kanban. Pode ser convertida em chamado ao ser arrastada para a coluna de um atendente. Apos a conversao e mantida como rastro (marcada como convertida, nao apagada).

Campos atuais:

- `titulo`
- `descricao`
- `criado_por` (FK opcional para quem criou, `on_delete=SET_NULL`, related_name `pendencias_criadas`)
- `criado_em`
- `convertido_em_chamado` (booleano, default `False`)
- `chamado_gerado` (FK opcional para o `Chamado` criado, `on_delete=SET_NULL`, related_name `pendencias_origem`)
- `convertido_por` (FK opcional para quem converteu, `on_delete=SET_NULL`, related_name `pendencias_convertidas`)
- `convertido_em`

Regras atuais:

- So Atendente TI/Admin criam, veem e convertem pendencias; usuario comum nao acessa.
- A coluna "Pendencias" lista apenas pendencias com `convertido_em_chamado = False`.
- Ao converter: cria um `Chamado` com titulo/descricao da pendencia, `solicitante` = quem criou a pendencia, `atendente_atual` = atendente da coluna destino e status "Em atendimento".
- A conversao e idempotente: uma pendencia ja convertida nao gera chamado duplicado.
- A conversao registra eventos no chamado (criacao a partir da pendencia e atribuicao ao atendente).

### AtendimentoHistorico

Registra cada periodo individual de trabalho de um atendente em um chamado.

Campos atuais:

- `chamado`
- `atendente`
- `iniciado_em`
- `finalizado_em`
- `duracao`
- `tipo_encerramento`
- `descricao_atividade`
- `criado_em`
- `atualizado_em`

Regras atuais:

- Um atendente pode ter apenas um atendimento ativo por vez.
- Um chamado pode acumular varios registros de atendimento ao longo do tempo.
- `tipo_encerramento` usa inicialmente os valores `pause` e `stop`.
- `descricao_atividade` e obrigatoria no encerramento do periodo.
- `duracao` e calculada ao pausar ou finalizar.

### RequisicaoContrato

Requisicao de contrato/compra do modulo Contratos. Agrupa varios orcamentos.

Campos atuais:

- `titulo`
- `tipo` (choices: `fisica`, `digital`; default `fisica`)
- `texto`
- `status` (choices: `aberta`, `em_cotacao`, `finalizada`, `cancelada`; default `aberta`, definido automaticamente na criacao)
- `criado_por` (FK opcional para o usuario, `on_delete=SET_NULL`)
- `criado_em`
- `atualizado_em`

Regras atuais:

- So Atendente TI/Admin criam/veem requisicoes (validado no backend).
- O status inicial e sempre `aberta`; o fluxo de aprovacao nao foi implementado (campo apenas preparado).

### OrcamentoContrato

Orcamento principal vinculado a uma requisicao. Pode ter varios suborcamentos.

Campos atuais:

- `requisicao` (FK para `RequisicaoContrato`, `on_delete=CASCADE`, related_name `orcamentos`)
- `titulo`, `loja`
- `moeda` (choices: `BRL`, `USD`; default `BRL`)
- `valor`, `frete`, `desconto` (Decimal, nao negativos)
- `quantidade` (inteiro positivo, minimo 1)
- `link` (URL opcional)
- `foto_produto` (`ImageField`, opcional; usa Pillow)
- `criado_por`, `criado_em`, `atualizado_em`

Regras de calculo:

- `subtotal = valor * quantidade`
- `total = subtotal + frete - desconto`
- `total_com_suborcamentos = total do orcamento + soma do total de todos os suborcamentos vinculados`

### OrcamentoDocumento

Documento anexo de um orcamento (sem restricao de tipo ou tamanho no codigo).

- `orcamento` (FK `on_delete=CASCADE`, related_name `documentos`)
- `arquivo` (`FileField`), `nome_original`, `enviado_em`

### SuborcamentoContrato

Complemento de um orcamento principal. Nao aparece como orcamento independente na lista.

Campos atuais: os mesmos de `OrcamentoContrato`, com `orcamento_pai` (FK para `OrcamentoContrato`, `on_delete=CASCADE`, related_name `suborcamentos`) no lugar de `requisicao`. Usa `subtotal`/`total` com a mesma regra de calculo.

### SuborcamentoDocumento

Documento anexo de um suborcamento.

- `suborcamento` (FK `on_delete=CASCADE`, related_name `documentos`)
- `arquivo` (`FileField`), `nome_original`, `enviado_em`

### Relacao entre os modelos de Contratos

- `RequisicaoContrato` 1--N `OrcamentoContrato` 1--N `SuborcamentoContrato`.
- Orcamentos e suborcamentos possuem 1--N documentos cada.
- Fotos e documentos ficam sob `MEDIA_ROOT/contratos/...` e sao servidos por rotas protegidas (nao expostos diretamente por `MEDIA` para quem nao tem permissao).

### InsumoTI

Item de estoque de TI (teclados, mouses, cabos, adaptadores, fontes, perifericos, etc.).

Campos atuais:

- `nome`
- `descricao`
- `quantidade_atual` (inteiro positivo; e o estoque atual)
- `observacao`
- `ativo` (booleano, default `True`; preparado para desativacao futura sem exclusao)
- `criado_por` (FK opcional, `on_delete=SET_NULL`)
- `criado_em`, `atualizado_em`

Regras atuais:

- So Atendente TI/Admin cadastram, veem e retiram insumos (validado no backend).
- Propriedade `status_estoque`/`status_label`: `disponivel`, `baixo` (quantidade <= `LIMITE_BAIXO_ESTOQUE`, hoje 5) ou `zerado` (quantidade 0).
- A quantidade inicial e obrigatoria e nao pode ser negativa.

### RetiradaInsumoTI

Registro historico de cada retirada/baixa de estoque de um insumo.

Campos atuais:

- `insumo` (FK para `InsumoTI`, `on_delete=CASCADE`, related_name `retiradas`)
- `quantidade` (inteiro positivo; > 0)
- `entregue_para`
- `motivo`
- `registrado_por` (FK opcional, `on_delete=SET_NULL`)
- `criado_em`

Regras atuais:

- Cada retirada valida no backend: quantidade > 0 e menor/igual ao estoque disponivel (`409` se insuficiente); campos `entregue_para` e `motivo` obrigatorios.
- Ao registrar a retirada, o `quantidade_atual` do insumo e abatido na mesma transacao (`select_for_update`).
- O historico de retiradas nao e apagado; os insumos nao sao excluidos automaticamente.

### DocumentoTI

Cadastro de um documento interno, com um ou mais anexos vinculados.

Campos atuais:

- `nome`
- `observacao`
- `ativo` (booleano, default `True`; preparado para desativacao futura sem exclusao)
- `criado_por` (FK opcional, `on_delete=SET_NULL`)
- `criado_em`, `atualizado_em`

Regras atuais:

- So Atendente TI/Admin cadastram, veem e baixam documentos/anexos (validado no backend).
- Um documento pode ter varios anexos; nome obrigatorio (minimo 2 caracteres).

### DocumentoTIAnexo

Arquivo anexado a um `DocumentoTI` (sem restricao de tipo ou tamanho no codigo).

Campos atuais:

- `documento` (FK para `DocumentoTI`, `on_delete=CASCADE`, related_name `anexos`)
- `arquivo` (`FileField`, salvo em `MEDIA_ROOT/documentos/<documento_id>/<arquivo>`)
- `nome_original`
- `enviado_por` (FK opcional, `on_delete=SET_NULL`)
- `enviado_em`

Regras atuais:

- Multiplos anexos por documento; download por rota dedicada e protegida (nao expoe a URL direta de `MEDIA`), acesso sem permissao retorna `404`.
- Documentos e anexos nao sao apagados automaticamente.

### EmprestimoTI

Emprestimo (comodato) de um ou mais equipamentos de TI a um colaborador.

Campos atuais:

- `colaborador_nome`, `empresa`, `cpf`, `email`, `telefone`
- `data_emprestimo`, `previsao_devolucao` (opcional), `prazo_indeterminado`
- `observacoes_internas`
- `status` (choices: `aguardando`, `assinada_ok`, `em_andamento`, `devolvido`, `cancelado`; inicial `aguardando`)
- `assinatura_responsavel` (FK opcional para `AssinaturaResponsavelTI`, `on_delete=SET_NULL`)
- `termo_pdf` (termo gerado pelo sistema), `termo_assinado` (arquivo devolvido)
- `termo_assinado_ok`, `termo_assinado_em`, `termo_assinado_por`
- `criado_por`, `criado_em`, `atualizado_em`

Regras/propriedades:

- `devolucao_display`: retorna "Indeterminada" quando `prazo_indeterminado` ou sem `previsao_devolucao`.
- Ao criar, o termo em PDF e gerado e vinculado; o status inicial e "Aguardando documentacao assinada".

### EquipamentoEmprestimoTI

Equipamento vinculado a um emprestimo (um emprestimo pode ter varios).

- `emprestimo` (FK `on_delete=CASCADE`, related_name `equipamentos`)
- `tipo_equipamento`, `marca`, `modelo`, `numero_serie`, `patrimonio_etiqueta`, `acessorios_entregues`, `criado_em`

### FotoEquipamentoEmprestimoTI

Foto de um equipamento (um equipamento pode ter varias).

- `equipamento` (FK `on_delete=CASCADE`, related_name `fotos`)
- `imagem` (`ImageField`), `nome_original`, `enviado_por`, `enviado_em`

### AssinaturaResponsavelTI

Assinatura cadastrada de um responsavel de TI, protegida por senha.

- `nome_responsavel`, `imagem_assinatura` (`ImageField`)
- `senha_hash` (hash Django via `make_password`; NUNCA em texto puro)
- `ativo`, `criado_por`, `criado_em`, `atualizado_em`
- Metodos `set_senha` / `conferir_senha` (usa `check_password`).

### LogUsoAssinaturaTI

Registro de cada uso autorizado de uma assinatura (rastreabilidade; nao e apagado).

- `assinatura` (FK `on_delete=CASCADE`, related_name `usos`)
- `emprestimo` (FK `on_delete=SET_NULL`), `usado_por`, `usado_em`, `observacao`

## Modelos previstos para proximas fases

> O antigo item previsto "ComentarioChamado" foi implementado como o modelo `ChamadoMensagem` (conversa do chamado, ver acima). O antigo item "AnexoChamado" foi implementado como `ChamadoAnexo`.

## Observacoes de modelagem

- O historico de atendimento foi criado primeiro para preparar relatorios e rastreabilidade.
- O dominio completo de chamado ainda sera refinado quando a abertura e a edicao reais forem implementadas.
- Novas evolucoes devem preservar a trilha historica de cada atendimento.
