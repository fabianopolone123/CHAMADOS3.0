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
- `solicitante_nome`
- `solicitante_email`
- `departamento`
- `categoria`
- `subcategoria`
- `prioridade`
- `status`
- `origem`
- `aberto_em_referencia`
- `ultima_atualizacao_referencia`
- `criado_em`
- `atualizado_em`

Observacoes:

- Neste momento os chamados continuam nascendo de dados mockados da dashboard.
- Ao abrir a dashboard, os mocks sao sincronizados com o banco via `update_or_create`.
- O campo `numero` e unico e serve como chave de referencia entre o Kanban e o backend.

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
