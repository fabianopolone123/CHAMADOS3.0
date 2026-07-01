# 02 - Regras de Negocio

## Situacao atual

O sistema possui autenticacao corporativa via Active Directory/LDAP e uma interface inicial de atendimento para a equipe de TI.

## Regras atuais de autenticacao

1. O usuario deve informar credenciais corporativas validas para acessar o sistema.
2. A autenticacao deve ocorrer via Active Directory usando LDAP.
3. Em caso de autenticacao valida, o usuario deve ser sincronizado localmente no Django.
4. Em caso de erro, o sistema deve exibir mensagem amigavel sem expor detalhes internos do AD.
5. O logout deve encerrar a sessao e retornar o usuario para a tela de login.

## Regras atuais do painel de atendimento (Kanban por atendente)

1. O Kanban e acessivel apenas para administrador e Atendente TI; o usuario comum e redirecionado para o portal.
2. O menu do Atendente TI mostra apenas "Chamados" (o Kanban) e "Permissoes".
3. O quadro lista os chamados reais do banco (model `Chamado`), sem dados mockados.
4. A primeira coluna e fixa: "Chamados abertos" (chamados nao encerrados e sem atendente atual).
5. As colunas do meio sao dinamicas: uma para cada usuario do grupo `Atendente TI`, exibindo os chamados nao encerrados cujo `atendente_atual` e aquele usuario.
6. A ultima coluna e fixa: "Chamados fechados" (status `resolvido` ou `fechado`).
7. Cada card exibe numero, titulo, solicitante, data de abertura, status atual e atendente atual (quando existir).
8. Arrastar para a coluna de um atendente define o `atendente_atual` como aquele usuario e o status como "Em atendimento".
9. Arrastar entre atendentes atualiza o `atendente_atual`.
10. Arrastar para "Chamados fechados" marca o status como "Fechado", registra quem fechou e preenche `fechado_em`.
11. Arrastar para "Chamados abertos" volta o status para "Aberto" e limpa o `atendente_atual`.
12. O `atendente_atual` NAO torna o usuario dono do chamado; o dono e sempre o solicitante que abriu.
13. Toda movimentacao e salva no banco e gera registro em `ChamadoEvento`.
14. A movimentacao usa endpoint `POST` protegido por login e permissao de TI, com CSRF; usuario comum nao movimenta chamados.
15. O atendente de destino e validado no backend: precisa pertencer ao grupo `Atendente TI`.
16. Ao arrastar, o badge de status do card atualiza texto e cor imediatamente, sem refresh.
17. Clicar em um card abre a tela de detalhe do chamado.
18. Cada card permite iniciar, pausar e finalizar um periodo de atendimento (controle de tempo).
19. O detalhe do chamado exibe os anexos (nome, link de download, data e usuario que enviou) e o historico de eventos.
20. Anexos so podem ser baixados pelo dono do chamado ou por TI/admin.
21. A tela "Chamados" possui um botao "Criar chamado" (visivel apenas para TI/admin) que abre um modal para o atendente abrir um chamado em nome dele mesmo.
22. Chamado criado pelo Kanban entra com status "Aberto", solicitante = atendente logado e sem atendente atual (aparece na coluna "Chamados abertos").
23. O atendente atual do chamado criado so e definido quando o card e arrastado para a coluna de um atendente.
24. A criacao pelo Kanban registra em `ChamadoEvento`: "Chamado criado manualmente pelo atendente X."

## Regras atuais de controle de tempo

1. Um atendente pode ter apenas um atendimento ativo por vez.
2. O usuario logado e o atendente responsavel pelos registros de tempo.
3. Um chamado pode acumular varios periodos de atendimento ao longo da sua vida.
4. Pausar ou finalizar atendimento exige descricao obrigatoria do que foi feito.
5. Cada registro deve guardar inicio, fim, duracao, tipo de encerramento e descricao.
6. O backend deve validar as regras criticas mesmo que o frontend tambem faca bloqueios visuais.
7. Administrador pode consultar todos os historicos de atendimento.
8. Atendente TI pode consultar apenas o proprio historico na tela dedicada.

## Regras atuais de permissao

1. O usuario `fabiano.polone` deve ser administrador principal do sistema.
2. O sistema deve garantir automaticamente os grupos `Administrador` e `Atendente TI`.
3. Apenas administradores podem acessar `/permissoes/`.
4. Apenas administradores podem atribuir ou remover o perfil `Atendente TI`.
5. O grupo `Atendente TI` e a base inicial para a composicao das colunas do quadro Kanban.

## Regras atuais do portal do solicitante

1. O usuario comum e todo usuario autenticado que nao pertence aos grupos `Administrador` nem `Atendente TI`.
2. Apos o login, o usuario comum e direcionado para `/meus-chamados/` e a equipe de TI para o Kanban.
3. O usuario comum abre chamados informando apenas titulo, descricao e anexos (opcionais).
4. O usuario comum nao escolhe status, prioridade, atendente nem solicitante; esses campos sao definidos pelo sistema ou pela equipe de TI.
5. Cada chamado aberto pelo portal recebe numero unico gerado no formato `CH-000123`.
6. O chamado aberto nasce com status `aberto` e registra o usuario logado como solicitante automaticamente.
7. Os anexos enviados na abertura ficam vinculados ao chamado, sem restricao de tamanho ou extensao neste momento.
8. O usuario comum visualiza e acessa apenas os chamados que ele mesmo abriu.
9. Administrador e Atendente TI podem acessar o detalhe de qualquer chamado.
10. A tela de detalhe exibe a timeline real dos periodos de atendimento registrados no chamado.

## Regras previstas para o sistema de chamados

1. Cada chamado deve ter status de acompanhamento com transicoes controladas.
2. O chamado deve registrar data de abertura e, quando aplicavel, data de fechamento.
3. O chamado deve ser atribuivel a uma equipe ou atendente com persistencia real no Kanban.
4. O historico de alteracoes deve ser preservado.
5. Comentarios e interacoes devem ficar vinculados ao chamado.
6. O solicitante deve poder complementar ou acompanhar interacoes do chamado.

## Regras de seguranca

- Credenciais reais nao devem ser gravadas em codigo.
- Variaveis como `AD_LDAP_BIND_PASSWORD` devem permanecer apenas no `.env` ou no ambiente do servidor.
- Caminhos de certificado devem ser validados por ambiente antes do deploy.
