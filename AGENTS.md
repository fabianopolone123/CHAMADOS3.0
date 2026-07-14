# AGENTS.md

Este arquivo orienta futuras implementacoes no projeto `CHAMADOS3.0`.

## Objetivo do projeto

Construir um sistema de chamados de TI em Django com foco em simplicidade, organizacao e evolucao incremental.

## Estado atual

- O projeto possui autenticacao no Active Directory via LDAP na tela `/login/`.
- O backend de autenticacao esta em `core/auth_backend.py`.
- O fluxo pos-login redireciona para `/chamados/`.
- A interface inicial autenticada e um quadro Kanban para a visao de Atendente TI.
- O sistema possui grupos iniciais `Administrador` e `Atendente TI`; usuario comum e quem nao pertence a nenhum deles.
- Apos o login, admin e Atendente TI vao para o Kanban e o usuario comum para o portal `/meus-chamados/`.
- O usuario `fabiano.polone` deve permanecer como administrador principal.
- O projeto ja possui os modelos `Chamado` e `AtendimentoHistorico` para sustentar o controle inicial de tempo por atendimento.
- O modelo `Chamado` possui vinculo `solicitante`, choices de `status`/`prioridade` e gerador de numero `CH-000123`.
- O projeto possui o portal do solicitante em `/meus-chamados/` com abertura, listagem e detalhe read-only dos proprios chamados.
- O projeto possui tela de Historico de Atendimentos em `/historico/` com busca dinamica por registros.
- O projeto possui o modulo Requisicoes em `/contratos/` (apenas TI/admin): requisicoes com orcamentos e suborcamentos (complementos), foto do produto, documentos anexos, captura de print e calculo de totais. Na interface chama-se "Requisicoes"; os nomes tecnicos internos (models, rotas, arquivos) mantem o prefixo `Contrato`. Ao excluir uma requisicao (ou item isolado), signals `post_delete` em `core/signals.py` removem os arquivos fisicos de `MEDIA_ROOT/contratos/...` do disco, evitando orfaos.
- O projeto possui o modulo Insumos em `/insumos/` (apenas TI/admin): controle simples de estoque de materiais de TI (models `InsumoTI` e `RetiradaInsumoTI`) com cadastro, retirada com baixa de estoque validada no backend e historico de retiradas.
- O projeto possui o modulo Documentos em `/documentos/` (apenas TI/admin): cadastro e armazenamento de documentos internos (models `DocumentoTI` e `DocumentoTIAnexo`) com nome, observacao e anexos multiplos servidos por rota protegida.
- O projeto possui o modulo Emprestimos em `/emprestimos/` (apenas TI/admin): comodato de equipamentos de TI (models `EmprestimoTI`, `EquipamentoEmprestimoTI`, `FotoEquipamentoEmprestimoTI`, `AssinaturaResponsavelTI`, `LogUsoAssinaturaTI`). Gera o termo de responsabilidade em PDF com ReportLab (`core/termo_pdf.py`), com assinatura do responsavel protegida por senha (hash), anexo do termo assinado e controle de status.
- O projeto possui o modulo Emails em `/emails/` (apenas TI/admin): lista das contas de e-mail corporativo (model `ContaEmail`) com busca dinamica, tabela responsiva e modal de detalhe. A atualizacao e feita importando o CSV exportado do Google Workspace (`/emails/importar/`), que faz upsert pela chave e-mail e notifica pelo toast classico (Django messages). A senha do export nunca e armazenada; a lista CSV nao e versionada (`.gitignore`).
- O projeto possui o modulo Ramais em `/ramais/` (apenas TI/admin): lista telefonica interna (model `Ramal`) com colaborador, setor, telefone, ramal e e-mail, busca dinamica, ordenacao por cabecalho, edicao/exclusao (modal com confirmacao) e cadastro cujo e-mail pode ser digitado ou escolhido de um `select` das contas ja cadastradas (`ContaEmail`), preenchendo o colaborador automaticamente. A lista inicial e semeada pela migration `0013` a partir de um arquivo local (`seed/ramais_seed.json`) ignorado pelo Git — os dados pessoais (nomes/telefones/e-mails) nao sao versionados.
- O projeto possui o modulo Starlinks em `/starlinks/` (apenas TI/admin): antenas/contas Starlink migradas do banco antigo (model `Starlink`). Nome, local, e-mail, ativo, forma de pagamento (pix/cartao), final do cartao, identificador, versao do software, numero de serie e numero do kit. Grade de cards responsiva com resumo, busca e filtro por status; CRUD por modal. NAO guarda senha (o campo foi removido na migration `0028`). Seed via migration `0027` a partir de `seed/starlinks_seed.json` (ignorado pelo Git).
- O projeto possui o modulo Dicas em `/dicas/` (apenas TI/admin): base de conhecimento da TI migrada do banco antigo (model `Dica`). Categoria (geral/configuracao/resolucao), titulo, conteudo livre e anexo opcional. Grade de cards com badge de categoria, chips de filtro por categoria + busca, modal de detalhe (conteudo com quebras de linha preservadas e URLs clicaveis, escapadas antes; anexo abre inline) e CRUD por modal (upload/substituicao/remocao do anexo). Seed via migration `0025` a partir de `seed/dicas_seed.json` (ignorado pelo Git); anexos em `media/dicas/` (nao versionados); anexo servido por rota protegida.
- O projeto possui o modulo Futura Digital em `/futura-digital/` (apenas TI/admin): faturas mensais da locacao de impressoras migradas do banco antigo (model `FuturaDigital`), com a regra de cobranca por impressoes. Campos: mes de referencia (normalizado para o 1o dia), nota fiscal, copias total/cor, franquia de copias/valor, taxas de excedente/cor, excedentes e valor pago calculados, documento. Regra: `excedentes = max(total - cor - franquia, 0)`; `valor = franquia_valor + excedentes*taxa_exc + cor*taxa_cor` (taxas/franquia editaveis por fatura; defaults 0,07 / 0,75 / 23000 / 1.610,00), calculada ao vivo no formulario e conferida no backend. A tela tem cartoes de resumo, um grafico de barras mes a mes (Valor pago / Copias / Excedentes, sem lib externa, via `json_script`), tabela responsiva com busca e ordenacao, e CRUD por modal com download do documento (rota protegida). Seed via migration `0023` a partir de `seed/futura_digital_seed.json` (ignorado pelo Git), preservando os valores historicos; documentos em `media/futura_digital/` (nao versionados).
- O projeto possui o modulo Contratos em `/contratos-ti/` (apenas TI/admin): contratos/assinaturas recorrentes de TI migrados do banco antigo, com dados e anexos (models `Contrato` e `ContratoAnexo`). Nome, observacoes, valor (formato brasileiro, opcional), forma de pagamento, final do cartao, periodicidade (mensal/anual/pagamento unico), vigencia (inicio/fim), `encerrado_em` (define status Ativo/Encerrado) e anexos multiplos. Tabela responsiva com busca e ordenacao por cabecalho, cartoes de resumo, modal de detalhe (download por rota protegida) e modal de cadastro/edicao com upload multiplo; exclusao de contrato (cascata + arquivos) e de anexo isolado, padrao classico (POST + Django messages + redirect). Seed via migration `0021` a partir de `seed/contratos_seed.json` (ignorado pelo Git); arquivos em `media/contratos_ti/` (nao versionados). IMPORTANTE: e distinto do modulo Requisicoes (menu "Requisicoes", `/contratos/`), que internamente usa o prefixo `Contrato` mas trata de requisicoes de compra.
- O projeto possui o modulo Servicos feitos em `/servicos-feitos/` (apenas TI/admin): registro de servicos de TI ja executados migrado do banco antigo, com seus cadastros e arquivos (models `ServicoFeito` e `ServicoFeitoAnexo`). Nome, empresa, descricao, data, valor (formato brasileiro) e anexos multiplos (NF/orcamento). Tabela responsiva com busca e ordenacao por cabecalho, cartoes de resumo, modal de detalhe (download dos anexos por rota protegida) e modal de cadastro/edicao com upload multiplo; exclusao de servico (cascata + arquivos do disco) e de anexo isolado, padrao classico (POST + Django messages + redirect). O seed vem da migration `0019` a partir de `seed/servicos_feitos_seed.json` (ignorado pelo Git); os PDFs ficam em `media/servicos_feitos/` (tambem nao versionados).
- O projeto possui o modulo IPs em `/ips/` (apenas TI/admin): inventario de IPs/equipamentos da rede interna migrado do banco antigo (model `EnderecoIP`). Categorias (servidores, switches, catracas/IdFace, impressoras, Wi-Fi, monitoramento), endereco IP unico, nome, fabricante, MAC, acesso e observacoes. Tabela responsiva com badge colorido por categoria, cartoes de resumo, busca inteligente e chips de filtro por categoria; CRUD por modal (create/edit/delete com confirmacao), padrao classico (POST + Django messages + redirect), com IP unico validado no backend. A lista inicial e semeada pela migration `0017` a partir de um arquivo local (`seed/ips_seed.json`) ignorado pelo Git — os MACs e credenciais de acesso NAO sao versionados.
- O projeto possui o modulo Licencas em `/licencas/` (apenas TI/admin): controle de licencas de software migrado do sistema antigo (models `LicencaSoftware` e `Licenca`). Softwares em cards expansiveis com badge `cadastradas/contratadas` e tabela responsiva das licencas (usuario, e-mail vinculado, serial, prazo, pagamento); cartoes de resumo e busca dinamica. CRUD completo de software e licenca por modais reutilizados (create/edit/delete com confirmacao inline), padrao classico (POST + Django messages + redirect); excluir um software apaga suas licencas em cascata. A lista inicial e semeada pela migration `0015` a partir de um arquivo local (`seed/licencas_seed.json`) ignorado pelo Git — os seriais/product keys e nomes de colaboradores NAO sao versionados.
- O layout autenticado e responsivo: o shell `.tickets-app` (sidebar + conteudo) usa breakpoint em 992px. Acima disso a sidebar fica lateral (290px); abaixo vira uma barra superior fina com menu recolhido atras de um hamburger (`static/js/sidebar.js`). Regras globais de responsividade e barras de rolagem discretas ficam em `static/css/base.css`; a pagina nunca deve gerar rolagem horizontal (conteudo largo rola dentro do proprio container).
- O arquivo `.env` na raiz concentra as configuracoes sensiveis de ambiente.
- A base de documentacao do projeto fica em `docs/`.

## Regras obrigatorias para novas implementacoes

1. Sempre manter a documentacao sincronizada com o codigo.
2. Ao criar, alterar ou remover funcionalidades, atualizar os arquivos correspondentes em `docs/`.
3. Ao adicionar novas rotas, atualizar `docs/04_rotas.md`.
4. Ao adicionar novos fluxos de negocio, atualizar `docs/02_regras_negocio.md`.
5. Ao criar ou modificar modelos, atualizar `docs/03_modelos.md`.
6. Ao adicionar tarefas planejadas ou concluidas, atualizar `docs/05_tarefas.md`.
7. Ao registrar mudancas relevantes, atualizar `docs/06_changelog.md`.
8. Ao alterar convencoes, padroes ou organizacao do codigo, atualizar `docs/07_padroes_codigo.md`.
9. Nunca expor credenciais, senhas, chaves ou conteudo do `.env` em codigo versionado ou documentacao.
10. Toda alteracao concluida no projeto deve ser subida para o Git com commit descritivo e push para o repositorio remoto.

## Diretrizes de implementacao

- Preferir views, URLs, templates e estaticos organizados por app.
- Manter a separacao entre apresentacao, regras de negocio e persistencia.
- Priorizar codigo legivel e simples antes de qualquer otimizacao prematura.
- Para funcionalidades novas, criar primeiro a estrutura minima e depois evoluir em etapas pequenas.
- Evitar misturar logica de autenticacao com a camada de template.
- Sempre validar se `AD_LDAP_CA_CERT_FILE` aponta para um caminho valido no ambiente de execucao.
- Em interacoes visuais temporarias, deixar `TODO` explicito quando faltar persistencia no backend.
- Regras de permissao inicial devem usar os grupos padrao do Django antes de qualquer sistema de roles mais complexo.
- Toda notificacao visual do sistema deve usar o componente global de toast integrado ao `Django messages`.
- Toda tela de detalhes de chamado deve usar um modal global reutilizavel preenchido por dados seguros vindos da view, sem criar um modal por card.
- O modal de detalhes deve continuar em formato temporario/mockateado ate a camada de persistencia e API estarem prontas.
- O controle de tempo deve manter a regra de um unico atendimento ativo por atendente, validada no backend.
- Encerramentos de atendimento por `pause` ou `stop` devem exigir descricao obrigatoria antes de salvar.
- A tela de Historico deve respeitar o recorte de permissao: administrador ve tudo e atendente ve apenas os proprios registros.

## Convencoes gerais

- Usar Django templates para paginas server-side.
- Manter arquivos CSS proprios quando a identidade visual exigir ajustes alem do Bootstrap.
- Configuracoes sensiveis devem vir de variaveis de ambiente carregadas do `.env`.
- Em ambientes Linux ou Docker, caminhos Windows de certificados devem ser convertidos para um caminho valido no host ou container.
