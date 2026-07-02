# 03 - Modelos

## Situacao atual

O projeto possui seis modelos persistidos para sustentar o fluxo de atendimento:

- `Chamado`
- `ChamadoEvento`
- `ChamadoAnexo`
- `ChamadoMensagem`
- `ChamadoMensagemAnexo`
- `AtendimentoHistorico`

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

## Modelos previstos para proximas fases

> O antigo item previsto "ComentarioChamado" foi implementado como o modelo `ChamadoMensagem` (conversa do chamado, ver acima). O antigo item "AnexoChamado" foi implementado como `ChamadoAnexo`.

## Observacoes de modelagem

- O historico de atendimento foi criado primeiro para preparar relatorios e rastreabilidade.
- O dominio completo de chamado ainda sera refinado quando a abertura e a edicao reais forem implementadas.
- Novas evolucoes devem preservar a trilha historica de cada atendimento.
