# 03 - Modelos

## Situacao atual

O projeto possui trinta e tres modelos persistidos:

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

Modulo Emails / Ramais:

- `ContaEmail`
- `Ramal`

Modulo Licencas:

- `LicencaSoftware`
- `Licenca`

Modulo IPs:

- `EnderecoIP`

Modulo Servicos feitos:

- `ServicoFeito`
- `ServicoFeitoAnexo`

Modulo Contratos:

- `Contrato`
- `ContratoAnexo`

Modulo Futura Digital:

- `FuturaDigital`

Modulo Dicas:

- `Dica`

Modulo Starlinks:

- `Starlink`

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

### ContaEmail

Conta de e-mail corporativo, atualizada via importacao do CSV exportado do Google Workspace (modulo Emails). A importacao faz upsert pela chave `email` (unica). A senha do export NUNCA e armazenada.

- `email` (unico, chave de atualizacao), `primeiro_nome`, `sobrenome`, `status`, `org_unit_path`, `ultimo_acesso`
- Contato: `email_recuperacao`, `telefone_recuperacao`, `telefone_trabalho`, `telefone_residencial`, `telefone_celular`
- Organizacao: `employee_id`, `tipo_funcionario`, `cargo`, `email_gestor`, `departamento`, `centro_custo`
- Seguranca: `dois_fatores_inscrito`, `dois_fatores_forcado`, `gemini_status`
- Armazenamento: `uso_email`, `uso_drive`, `uso_fotos`, `limite_armazenamento`, `armazenamento_usado`, `licencas`
- `importado_por` (FK `on_delete=SET_NULL`), `importado_em`, `atualizado_em`
- Propriedades `nome_completo` e `is_ativo`. Migration `0011`.

### Ramal

Contato da lista telefonica interna (modulo Ramais). Seed inicial via migration de dados `0013`, que le um arquivo local ignorado pelo Git (`seed/ramais_seed.json`); os dados pessoais nao sao versionados.

- `colaborador`, `setor`, `telefone`, `ramal`, `email`
- `conta_email` (FK `ContaEmail` `on_delete=SET_NULL`, related_name `ramais`) — vinculo opcional com a conta de e-mail escolhida no cadastro
- `criado_por` (FK `on_delete=SET_NULL`), `criado_em`, `atualizado_em`. Migration `0012`.

### LicencaSoftware

Software cadastrado no modulo Licencas (ex.: AutoCAD, Gestarcad, Project). Agrupa a quantidade contratada e as licencas individuais. Seed inicial via migration de dados `0015`, que le um arquivo local ignorado pelo Git (`seed/licencas_seed.json`); os seriais/product keys e nomes de colaboradores NAO sao versionados.

- `nome`
- `quantidade_licencas` (inteiro positivo; quantidade contratada)
- `observacoes`
- `criado_por` (FK `on_delete=SET_NULL`, related_name `softwares_criados`), `criado_em`, `atualizado_em`
- Propriedade `licencas_cadastradas`: numero de licencas individuais vinculadas. Migration `0014`.

### Licenca

Licenca individual de um software (uma por usuario/serial). Um software 1--N licencas.

- `software` (FK para `LicencaSoftware`, `on_delete=CASCADE`, related_name `licencas`)
- `serial` (serial/product key), `email_vinculado`, `usuario_atribuido`
- `tipo_expiracao` (choices: `indeterminado`, `expira_em`; default `indeterminado`)
- `expira_em` (data, opcional; usada apenas quando `tipo_expiracao = expira_em`)
- `forma_pagamento`, `final_cartao` (ate 4 digitos)
- `observacoes`
- `criado_por` (FK `on_delete=SET_NULL`, related_name `licencas_criadas`), `criado_em`, `atualizado_em`
- Propriedade `expira_label`: "Indeterminado" ou a data formatada (dd/mm/aaaa). Migration `0014`.

Regras atuais:

- So Atendente TI/Admin acessam, cadastram, editam e excluem softwares e licencas (validado no backend; usuario comum e redirecionado).
- Excluir um software remove em cascata todas as suas licencas (`on_delete=CASCADE`).
- Ao escolher `tipo_expiracao = indeterminado`, a data de expiracao enviada e ignorada (fica nula).

### EnderecoIP

Endereco/equipamento da rede interna (modulo IPs), migrado do sistema antigo. Seed inicial via migration de dados `0017`, que le um arquivo local ignorado pelo Git (`seed/ips_seed.json`); os MACs e credenciais de acesso NAO sao versionados.

- `categoria` (choices: `servers` Servidores, `switches` Switchs, `idface_turnstiles` IdFace + Catracas, `printers` Impressoras, `wifi` Wi-Fi, `monitoring` Zabbix & Grafana)
- `endereco_ip` (unico)
- `nome`, `fabricante`, `mac`, `acesso` (usuario/senha do equipamento), `observacoes`
- `criado_por` (FK `on_delete=SET_NULL`, related_name `ips_criados`), `criado_em`, `atualizado_em`. Migration `0016`.

Regras atuais:

- So Atendente TI/Admin acessam, cadastram, editam e excluem IPs (validado no backend; usuario comum e redirecionado).
- `endereco_ip` e unico; a validacao no backend bloqueia duplicidade (na edicao, ignora o proprio registro) e exige uma categoria valida.

### ServicoFeito

Servico de TI ja executado (modulo Servicos feitos), migrado do banco antigo. Seed inicial via migration de dados `0019`, que le `seed/servicos_feitos_seed.json` (local, ignorado pelo Git); os PDFs ficam em `media/servicos_feitos/` (tambem fora do Git).

- `nome_servico`, `empresa`, `descricao`
- `data_servico` (data), `valor` (Decimal, padrao brasileiro na exibicao)
- `criado_por` (FK `on_delete=SET_NULL`, related_name `servicos_feitos_criados`), `criado_em`, `atualizado_em`. Migration `0018`.
- Propriedades `anexos_total` (qtd de anexos) e `valor_display` (valor formatado 1.234,56).

### ServicoFeitoAnexo

Arquivo anexado a um servico feito (NF, orcamento, relatorio). Um servico 1--N anexos.

- `servico` (FK `on_delete=CASCADE`, related_name `anexos`)
- `arquivo` (`FileField`, salvo em `MEDIA_ROOT/servicos_feitos/`), `nome_original`, `enviado_em`

Regras atuais:

- So Atendente TI/Admin acessam, cadastram, editam e excluem servicos e anexos (validado no backend; usuario comum e redirecionado, e endpoints de detalhe/download retornam `403`/`404`).
- O valor aceita formato brasileiro (1.234,56) ou com ponto decimal; e convertido para Decimal no backend. Excluir um servico remove seus anexos em cascata e apaga os arquivos fisicos; e possivel remover um anexo isolado. O download dos anexos usa rota protegida (nao expoe a URL direta de `MEDIA`).

### Contrato

Contrato/assinatura recorrente ou unico de TI (modulo Contratos), migrado do banco antigo. NAO confundir com o modulo Requisicoes (`RequisicaoContrato`), que trata de requisicoes de compra. Seed inicial via migration de dados `0021`, que le `seed/contratos_seed.json` (local, ignorado pelo Git); os anexos ficam em `media/contratos_ti/` (tambem fora do Git).

- `nome`, `observacoes`
- `valor` (Decimal, opcional; formato brasileiro na exibicao)
- `forma_pagamento`, `final_cartao`
- `periodicidade` (choices: `mensal`, `anual`, `pagamento_unico`; default `mensal`)
- `inicio`, `fim` (vigencia), `encerrado_em` (quando preenchido, o contrato e considerado encerrado)
- `criado_por` (FK `on_delete=SET_NULL`, related_name `contratos_criados`), `criado_em`, `atualizado_em`. Migration `0020`.
- Propriedades `anexos_total`, `esta_ativo` (True se `encerrado_em` vazio) e `valor_display` (1.234,56 ou "-").

### ContratoAnexo

Arquivo anexado a um contrato (NF, termo, invoice, comprovante). Um contrato 1--N anexos.

- `contrato` (FK `on_delete=CASCADE`, related_name `anexos`)
- `arquivo` (`FileField`, salvo em `MEDIA_ROOT/contratos_ti/`), `nome_original`, `enviado_em`

Regras atuais:

- So Atendente TI/Admin acessam, cadastram, editam e excluem contratos e anexos (validado no backend; usuario comum e redirecionado, e detalhe/download retornam `403`/`404`).
- O valor e opcional e aceita formato brasileiro; a periodicidade e validada. Excluir um contrato remove seus anexos em cascata e apaga os arquivos fisicos; e possivel remover um anexo isolado. O download usa rota protegida.

### FuturaDigital

Fatura mensal da locacao de impressoras (Futura Digital), migrada do banco antigo. Registra o consumo do mes e aplica a regra de cobranca. Seed inicial via migration de dados `0023`, que le `seed/futura_digital_seed.json` (local, ignorado pelo Git); os documentos ficam em `media/futura_digital/` (tambem fora do Git). O seed PRESERVA os valores historicos exatos (excedentes e valor pago), sem recalcular.

- `mes_referencia` (data; sempre normalizada para o 1o dia do mes)
- `nota_fiscal`
- `copias_total`, `copias_cor`
- `franquia_copias` (default 23000), `franquia_valor` (default 1610,00)
- `valor_copia_excedente` (default 0,07), `valor_copia_cor` (default 0,75)
- `copias_excedentes` e `valor_pago` (calculados no backend)
- `documento` (`FileField`, salvo em `MEDIA_ROOT/futura_digital/`)
- `criado_por` (FK `on_delete=SET_NULL`, related_name `futura_digital_criados`), `criado_em`, `atualizado_em`. Migration `0022`.

Regra de cobranca (aplicada no cadastro/edicao):

- `copias_excedentes = max(copias_total - copias_cor - franquia_copias, 0)` (excedente conta so as copias P&B alem da franquia).
- `valor_pago = franquia_valor + copias_excedentes * valor_copia_excedente + copias_cor * valor_copia_cor`.
- As taxas (excedente e cor) e a franquia sao editaveis por fatura (defaults acima). O calculo aparece ao vivo no formulario e e conferido no backend ao salvar.
- So Atendente TI/Admin acessam (usuario comum e redirecionado; download do documento retorna `404`). Metodos/propriedades: `recalcular()`, `mes_label`, `copias_pb`, `*_display`.

### Dica

Item da base de conhecimento da TI (modulo Dicas), migrado do banco antigo. Seed inicial via migration de dados `0025`, que le `seed/dicas_seed.json` (local, ignorado pelo Git); os anexos ficam em `media/dicas/` (tambem fora do Git).

- `categoria` (choices: `geral` Geral, `configuracao` Configuracao, `resolucao` Resolucao; default `geral`)
- `titulo`, `conteudo` (texto livre; quebras de linha preservadas na exibicao)
- `anexo` (`FileField`, salvo em `MEDIA_ROOT/dicas/`, opcional)
- `criado_por` (FK `on_delete=SET_NULL`, related_name `dicas_criadas`), `criado_em`, `atualizado_em`. Migration `0024`.

Regras atuais:

- So Atendente TI/Admin acessam, cadastram, editam e excluem dicas (validado no backend; usuario comum e redirecionado; download do anexo retorna `404`).
- O anexo pode ser substituido ou removido na edicao; excluir a dica apaga o arquivo do disco. O download/abertura do anexo usa rota protegida (imagens abrem inline).

### Starlink

Antena/conta Starlink da empresa (modulo Starlinks), migrada do banco antigo. Seed inicial via migration de dados `0027`, que le `seed/starlinks_seed.json` (local, ignorado pelo Git). No sistema antigo a senha era guardada cifrada (Fernet); na migracao ela foi decifrada com a chave do `.env` antigo e re-armazenada em texto no campo `senha` (o arquivo de seed com as credenciais NAO e versionado).

- `nome`, `local`, `email`, `senha`
- `ativo` (boolean), `forma_pagamento` (choices: `pix`, `cartao`; default `cartao`), `final_cartao`
- `identificador`, `versao_software`, `numero_serie`, `numero_kit` (dados do kit)
- `criado_por` (FK `on_delete=SET_NULL`, related_name `starlinks_criados`), `criado_em`, `atualizado_em`. Migration `0026`.

Regras atuais:

- So Atendente TI/Admin acessam, cadastram, editam e excluem Starlinks (validado no backend; usuario comum e redirecionado).
- Na edicao, deixar o campo senha em branco mantem a senha atual. A senha aparece mascarada na tela, com botoes para mostrar/ocultar e copiar.

## Modelos previstos para proximas fases

> O antigo item previsto "ComentarioChamado" foi implementado como o modelo `ChamadoMensagem` (conversa do chamado, ver acima). O antigo item "AnexoChamado" foi implementado como `ChamadoAnexo`.

## Observacoes de modelagem

- O historico de atendimento foi criado primeiro para preparar relatorios e rastreabilidade.
- O dominio completo de chamado ainda sera refinado quando a abertura e a edicao reais forem implementadas.
- Novas evolucoes devem preservar a trilha historica de cada atendimento.
