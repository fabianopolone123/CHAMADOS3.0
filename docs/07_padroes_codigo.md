# 07 - Padroes de Codigo

## Objetivo

Definir convencoes para manter o projeto consistente, legivel e facil de evoluir.

## Padroes gerais

- Usar nomes claros e descritivos.
- Manter funcoes pequenas e com responsabilidade unica.
- Preferir codigo simples e explicito.
- Evitar logica excessiva em templates.

## Django

- Views devem ficar em `views.py` ou modulos especificos por dominio quando crescerem.
- Rotas devem ficar em `urls.py`.
- Templates devem ser organizados por app quando fizer sentido.
- Arquivos estaticos devem ficar em `static/`.
- Backends de autenticacao customizados devem ficar no app que os utiliza.
- Controle de permissao inicial deve preferir `Group` do Django antes de introduzir estruturas mais complexas.
- Signals ficam em `core/signals.py`, registrados no `CoreConfig.ready()` (`apps.py`). Usar `post_delete` para limpar arquivos fisicos (`FileField`/`ImageField`) do `MEDIA_ROOT` quando o registro e apagado, evitando arquivos orfaos; a limpeza deve remover tambem diretorios vazios sem nunca ultrapassar o `MEDIA_ROOT`.

- O menu lateral de TI e dinamico: o catalogo (chave, rota, rotulo padrao e icone SVG) fica em `core/menu.py` e os ajustes do titular em `ItemMenuConfig`. **Modulo novo entra no menu cadastrando o item em `core/menu.py`**, nunca escrevendo `<a>` a mao em `templates/partials/ti_sidebar.html`, que so itera `menu_itens`.
- O Painel do Titular **nao reimplementa regra de modulo**: acao com fluxo (abrir chamado, Play/Pause/Stop, converter pendencia, aprovar orcamento) e declarada em `core/painel_acoes.py` apontando para a **rota que a tela classica ja usa**; o painel so monta o pedido e mostra a resposta. Escrever direto na tabela pela camada generica nesses casos pula evento de timeline, notificacao e validacao.
- Rota que a tela classica usa com `redirect` + `messages` e que o painel tambem precisa chamar deve responder **JSON quando o pedido vem por `fetch`** (`X-Requested-With: XMLHttpRequest`), mantendo o redirect para o formulario da tela. O caminho padrao e o decorador **`json_quando_xhr`** (`core/xhr.py`), que le os `messages` da propria view; so escreva a conversao na mao quando a resposta precisar levar dados (como o `mensagem_id` de `ticket_message_create`). Nao criar rota paralela so para o painel.
- Antes de anotar que algo "so existe na tela", verifique se e **regra** ou so **gesto**. Gesto (arrastar, clicar num botao de modal) se adapta a uma tecla do terminal; regra fica na rota. Quando a logica adaptada mora no front-end da tela (o texto de copia da requisicao, por exemplo), o caminho e **extrair para um arquivo compartilhado** pelos dois, nunca reescrever no painel.
- `colunas` de uma `TabelaPainel` e **identificacao, nao resumo**: uma coluna (duas se uma nao distingue). Campo que so serve para conferir vai para o registro, e o que serve para achar vai para `busca` — que nao precisa aparecer na lista.
- Tabela nova que mostre `FileField`/`ImageField` precisa de uma acao `abrir` apontando para a rota de download do modulo — anexo que so mostra o nome e pior do que nao aparecer. Ha teste que varre o catalogo e cobra isso.
- Cada `(tabela, escopo)` do painel usa **uma tecla por acao**, e `A` (atualizar) e `0` (voltar) sao reservadas pelo terminal; ha teste que falha se duas acoes colidirem.
- Campo cujo valor e consequencia de uma movimentacao (saldo de estoque, contador) entra em `campos_travados` na tabela do painel: aparece, mas so a rota dona dele escreve. A camada generica gravaria o numero sem o lancamento correspondente.
- Acao que chama uma rota de **edicao de tela** precisa espelhar os campos atuais do registro (`espelha_do_registro`), porque essas rotas reescrevem o registro inteiro a partir do POST — mandar so o arquivo apagaria o resto.
- Telas de administracao que alteram dados de varios modulos (Painel do Titular) devem: restringir por `titular_required`, responder JSON, registrar toda escrita em `PainelAuditoria` e manter a lista de campos de segredo (`_CAMPO_SECRETO` em `core/painel_dados.py`) como barreira — nenhuma tela generica pode expor senha, hash ou texto cifrado.

## Configuracao e seguranca

- Configuracoes sensiveis devem vir de variaveis de ambiente.
- O arquivo `.env` nao deve ser versionado.
- Nao fixar senha, secret key ou credenciais LDAP no codigo.
- Validar caminhos de certificado por ambiente antes do deploy.

## Front-end

- Para telas interativas, preferir bibliotecas leves e carregadas por CDN quando o projeto ainda estiver em fase inicial.
- Em interacoes temporarias sem persistencia, deixar `TODO` explicito no codigo.
- Separar estilos da autenticacao e da area autenticada quando a interface crescer.
- O estilo do menu lateral (sidebar) fica centralizado em `static/css/sidebar.css`, carregado uma unica vez em `base.html`; nao duplicar essas regras em outros CSS.
- A sidebar deve ter altura fixa e `position: sticky` para manter o menu estavel na mesma posicao vertical entre as telas.
- Regras globais de responsividade ficam em `static/css/base.css` (carregado em `base.html` antes dos CSS por contexto): rede de seguranca contra rolagem horizontal com `overflow-x: clip` no `body` (usar `clip`, nunca `hidden`, para nao quebrar o `position: sticky`) e barras de rolagem finas/discretas (`scrollbar-width: thin` + `::-webkit-scrollbar`). Nao criar rolagem horizontal na pagina inteira; quando um conteudo largo (tabela, faixa de colunas) precisar rolar, ele deve rolar dentro do proprio container (`overflow-x: auto`), nunca na pagina.
- O shell autenticado (`.tickets-app` = sidebar + conteudo) tem breakpoint unico em 992px: `>= 992px` a sidebar fica lateral (290px) e o Kanban usa altura cheia (100vh); `<= 991.98px` a sidebar vira uma barra superior fina com menu recolhido atras do hamburger (`static/js/sidebar.js`, que alterna a classe `is-open`). Ao mexer nesse breakpoint, manter os tres arquivos alinhados (`sidebar.css`, `chamados.css` e o JS).
- Em grids `repeat(auto-fill/auto-fit, minmax(Npx, 1fr))`, usar `minmax(min(Npx, 100%), 1fr)` para o grid nao estourar containers mais estreitos que `Npx`. Em itens de grid/flex que contem conteudo intrinsecamente largo (ex.: tabela `nowrap`), definir `min-width: 0` para o conteudo rolar internamente em vez de forcar a largura do pai.
- Toda mensagem visual do sistema deve usar o componente global de toast ligado ao `Django messages`, evitando blocos locais de alert repetidos.
- Detalhes de chamados devem usar um modal global reutilizavel preenchido por dados seguros da view, evitando um modal por card.
- Quando houver dados mockados para modais ou cards, preferir `json_script` ou outro carregamento seguro no template.
- Acoes interativas do Kanban devem usar `fetch` com `JsonResponse`, CSRF e validacao espelhada no backend.
- Regras criticas, como impedir mais de um atendimento ativo por atendente, devem ser garantidas no backend e apenas refletidas no frontend.
- Buscas dinamicas devem usar debounce no frontend e manter o recorte de permissao no backend antes de retornar JSON.

## Documentacao

- Qualquer funcionalidade nova exige atualizacao da documentacao.
- Mudancas de comportamento devem ser refletidas no `AGENTS.md` e nos documentos do `docs/` afetados.

## Versionamento

- Toda alteracao concluida deve gerar commit com mensagem descritiva.
- Apos cada commit, o projeto deve ser enviado com push para o repositorio remoto (`origin/main`).
- O push e obrigatorio e imediato: nenhuma funcionalidade e considerada finalizada enquanto nao estiver commitada e enviada ao remoto.
- Nao acumular varias funcionalidades em um unico commit; commitar em unidades coerentes de trabalho.
- Mensagens de commit devem seguir o padrao `tipo: descricao` (ex.: `feat:`, `fix:`, `docs:`, `refactor:`).
