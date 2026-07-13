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
