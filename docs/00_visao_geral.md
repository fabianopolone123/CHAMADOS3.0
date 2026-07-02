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
