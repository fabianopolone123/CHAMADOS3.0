# 03 - Modelos

## Situacao atual

O projeto agora possui dois modelos iniciais persistidos para sustentar o fluxo de atendimento:

- `Chamado`
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

Observacoes:

- Chamados abertos pelo portal do solicitante nascem com `solicitante`, `numero` gerado, `status = aberto` e `origem = "Portal do solicitante"`.
- Os chamados do Kanban ainda nascem de dados mockados sincronizados com o banco via `update_or_create` ao abrir a dashboard.
- O campo `numero` e unico e serve como chave de referencia entre o Kanban, o portal e o backend.
- `solicitante` usa `on_delete=SET_NULL` para preservar o chamado mesmo se o usuario for removido.

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

### ComentarioChamado

Modelo futuro para historico definitivo do chamado, separado do controle de tempo.

Campos esperados:

- chamado
- autor
- texto
- data de criacao

### AnexoChamado

Modelo futuro para arquivos enviados no chamado.

Campos esperados:

- chamado
- arquivo
- nome original
- data de envio

## Observacoes de modelagem

- O historico de atendimento foi criado primeiro para preparar relatorios e rastreabilidade.
- O dominio completo de chamado ainda sera refinado quando a abertura e a edicao reais forem implementadas.
- Novas evolucoes devem preservar a trilha historica de cada atendimento.
