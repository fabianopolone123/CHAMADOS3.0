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
