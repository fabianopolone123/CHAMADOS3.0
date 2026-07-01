# 02 - Regras de Negocio

## Situacao atual

O sistema possui autenticacao corporativa via Active Directory/LDAP e uma interface inicial de atendimento para a equipe de TI.

## Regras atuais de autenticacao

1. O usuario deve informar credenciais corporativas validas para acessar o sistema.
2. A autenticacao deve ocorrer via Active Directory usando LDAP.
3. Em caso de autenticacao valida, o usuario deve ser sincronizado localmente no Django.
4. Em caso de erro, o sistema deve exibir mensagem amigavel sem expor detalhes internos do AD.
5. O logout deve encerrar a sessao e retornar o usuario para a tela de login.

## Regras atuais do painel de atendimento

1. A interface inicial apos login deve abrir em `/chamados/`.
2. A visao inicial atual e exclusiva para Atendente TI.
3. O quadro deve possuir uma coluna fixa de chamados nao atribuidos.
4. O quadro deve possuir uma coluna para cada atendente de TI exibido.
5. Os cards devem ser arrastaveis entre as colunas.
6. A movimentacao atual e apenas visual e ainda nao deve salvar no banco.
7. O sistema deve deixar claro no codigo que a persistencia ficara para uma etapa futura.
8. Cada card deve permitir iniciar, pausar e finalizar um periodo de atendimento.

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
