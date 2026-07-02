# 05 - Tarefas

## Em andamento

- Evoluir a atribuicao para um fluxo formal de responsavel, se necessario

## Concluidas

- Corrigida a regra do "Play" no Kanban: iniciar atendimento passou a valer somente para chamados em coluna de Atendente TI (oculto em abertos/fechados via CSS por `data-column-type`), com validacao no backend (`403` para usuario comum; `409` para chamado aberto sem atendente ou encerrado) e historico registrado apenas quando o Play e valido
- Adicionado modal de "Chamados fechados" (aberto pelo titulo clicavel da coluna) com pesquisa inteligente dinamica (debounce ~300ms; filtra por ID, titulo, descricao, solicitante, atendente, mensagens e historico), lista compacta e detalhe completo do chamado; endpoints `GET /chamados/fechados/buscar/` e `GET /chamados/fechados/<numero>/` restritos a TI/admin
- Removido o header superior da tela "Chamados" e movida a criacao de chamado para um botao "+" no topo da coluna "Chamados abertos", liberando mais altura para o Kanban
- Adicionada a coluna "Pendencias" no Kanban com cadastro (modal), detalhe (modal) e conversao em chamado por drag-and-drop para a coluna do atendente (model `PendenciaTI`), restrito a TI/admin
- Tornados responsivos os cards e colunas do Kanban (largura/altura fluidas, scroll por coluna, ellipsis para textos longos) para melhor aproveitamento do monitor
- Compactado o header da tela "Chamados" (Quadro de Atendimento) para liberar mais espaco vertical ao Kanban, sem afetar os headers das demais telas
- Ajustado o "Stop" para encerrar o chamado (status Fechado), registrar quem encerrou no historico e mover o card automaticamente para "Chamados fechados" no Kanban sem refresh; encerramento restrito a TI/admin
- Adicionada area de conversa no detalhe do chamado (solicitante x TI) com anexos opcionais por mensagem, resumo no historico tecnico e historico recolhido por padrao (models `ChamadoMensagem` e `ChamadoMensagemAnexo`)
- Corrigida a instabilidade vertical do menu lateral e padronizado seu visual; CSS do menu centralizado em `static/css/sidebar.css`
- Adicionado botao "Criar chamado" no Kanban com modal para o atendente abrir chamado em nome proprio (entra em "Chamados abertos", sem atendente atual)
- Padronizado o menu lateral da area de TI em um include reutilizavel (Chamados + Permissoes)
- Reorganizado o Kanban por fila: coluna de abertos, colunas por Atendente TI e coluna de fechados
- Simplificado o menu do Atendente TI para apenas Chamados e Permissoes
- Criado o endpoint de movimentacao por coluna de destino (aberto/atendente/fechado) com validacao do atendente
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
4. Definir as transicoes formais de status do chamado
5. Atualizar a conversa sem recarregar a pagina (envio assincrono/AJAX)
