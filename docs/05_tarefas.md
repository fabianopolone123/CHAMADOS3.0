# 05 - Tarefas

## Em andamento

- Permitir que a TI registre comentarios/acoes manuais no historico do chamado
- Evoluir a atribuicao para um fluxo formal de responsavel, se necessario

## Concluidas

- Registrado o atendente atual (quem movimenta o chamado) sem trata-lo como dono do chamado
- Criado o model ChamadoEvento e o log de eventos (criacao, mudanca de status, troca de atendente)
- Exibidos anexos (com data e usuario) e historico do chamado no detalhe, com download protegido de anexos
- Corrigido o badge do Kanban para atualizar texto e cor no drag sem refresh
- Migrado o Kanban da TI para chamados reais do banco, com colunas por status e persistencia da movimentacao
- Removidos os dados mockados/fixos do Kanban e os chamados-fixture do banco
- Criado o endpoint protegido de atualizacao de status com CSRF e permissao de TI
- Criado o portal do solicitante (visao do usuario comum) com abertura, listagem e detalhe de chamados
- Adicionado roteamento pos-login por perfil (TI para o Kanban, usuario comum para o portal)
- Vinculado o chamado ao usuario solicitante e adicionados choices de status e prioridade
- Criada tela de login visual
- Criada rota `/login/`
- Criado redirecionamento da raiz `/`
- Integrada autenticacao Active Directory/LDAP
- Criada interface inicial em `/chamados/`
- Implementado quadro Kanban visual para Atendente TI
- Adicionado drag-and-drop visual dos cards
- Implementada tela inicial de permissoes por grupos do Django
- Definido `fabiano.polone` como administrador principal
- Garantido fluxo de logout
- Criada documentacao inicial do projeto
- Atualizada a documentacao apos a interface inicial de chamados
- Criado modal global de detalhes do chamado no Kanban com dados mockados
- Criado o backend inicial de controle de tempo por atendimento
- Criada a tela inicial de Historico de Atendimentos com busca dinamica

## Proximas tarefas sugeridas

1. Persistir chamados reais no Kanban e substituir os dados mockados
2. Persistir a atribuicao dos cards no backend
3. Refletir no portal os status atualizados pelos atendentes durante o atendimento
4. Permitir que o solicitante complemente/comente o proprio chamado
5. Definir as transicoes formais de status do chamado
