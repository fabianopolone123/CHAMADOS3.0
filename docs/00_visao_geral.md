# 00 - Visao Geral

## Resumo

Sistema de chamados de TI desenvolvido em Django para organizar solicitacoes, incidentes e atendimentos internos de suporte.

## Proposito

Centralizar a abertura e o acompanhamento de chamados tecnicos, com foco em padronizacao do atendimento, rastreabilidade e melhora da comunicacao entre usuarios e equipe de TI.

## Escopo atual

- Tela de login integrada ao Active Directory via LDAP
- Roteamento pos-login por perfil (TI/admin para o Kanban, usuario comum para o portal)
- Quadro Kanban por atendente em `/chamados/` com chamados reais do banco
- Drag-and-drop com persistencia da movimentacao (status e atendente atual) e registro de eventos
- Consulta de chamados encerrados pelo Kanban: modal com pesquisa inteligente (por ID, titulo, descricao, solicitante, atendente, mensagens e historico) e detalhe completo, restrito a TI/admin
- Controle de tempo por atendimento (iniciar, pausar, finalizar) e tela de historico
- Portal do solicitante: abertura, listagem e detalhe dos proprios chamados, com anexos
- Modulo Requisicoes (apenas TI/admin): requisicoes com orcamentos e suborcamentos (complementos), com foto do produto, documentos anexos, captura de print e calculo de totais
- Modulo Insumos (apenas TI/admin): controle simples de estoque de materiais de TI com cadastro, retirada com baixa de estoque e historico de retiradas
- Modulo Documentos (apenas TI/admin): cadastro e armazenamento de documentos internos com nome, observacao e anexos multiplos
- Modulo Emprestimos (apenas TI/admin): comodato de equipamentos de TI com multiplos equipamentos e fotos, assinatura protegida por senha, geracao do termo em PDF, anexo do termo assinado e controle de status
- Modulo Emails (apenas TI/admin): consulta das contas de e-mail corporativo com busca e detalhe, atualizadas pela importacao da lista CSV do Google Workspace (upsert por e-mail)
- Modulo Ramais (apenas TI/admin): lista telefonica interna (colaborador, setor, telefone, ramal, e-mail) com busca dinamica e cadastro cujo e-mail e escolhido entre as contas ja cadastradas
- Modulo Licencas (apenas TI/admin): controle de licencas de software agrupadas por software (serial, usuario, e-mail vinculado, prazo e forma de pagamento), com cartoes de resumo, busca dinamica e CRUD de software e licenca
- Modulo IPs (apenas TI/admin): inventario de IPs/equipamentos da rede interna (categoria, endereco, nome, fabricante, MAC, acesso), com cartoes de resumo, busca inteligente, filtro por categoria e CRUD
- Modulo Servicos feitos (apenas TI/admin): registro de servicos de TI executados (empresa, data, valor e anexos de NF/orcamento), com cartoes de resumo, busca, ordenacao, modal de detalhe com download e CRUD
- Modulo Contratos (apenas TI/admin): contratos/assinaturas recorrentes de TI (valor, forma de pagamento, periodicidade, vigencia, status e anexos), com cartoes de resumo, busca, ordenacao, modal de detalhe com download e CRUD (distinto do modulo Requisicoes)
- Modulo Futura Digital (apenas TI/admin): faturas mensais de impressao (locacao) com franquia, excedentes e copias coloridas, regra de cobranca com calculo automatico, grafico de consumo mes a mes e CRUD
- Gestao inicial de permissoes (grupos Administrador e Atendente TI)
- Logout funcional
- Documentacao tecnica e funcional do projeto

## Fora do escopo atual

- Edicao/complemento do chamado pelo proprio solicitante
- Modelo dedicado de comentarios e fluxo formal de interacao no chamado
- Transicoes de status totalmente formalizadas
- Relatorios e indicadores operacionais

## Publico-alvo

- Colaboradores da empresa
- Equipe de suporte de TI
- Administradores do sistema

## Objetivos de produto

- Simplificar o acesso ao portal com credenciais corporativas
- Dar visibilidade imediata ao quadro de atendimento da equipe de TI
- Preparar a base do sistema para funcionalidades autenticadas
