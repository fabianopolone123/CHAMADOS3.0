# 09 - API para sistemas de fora

Como um sistema instalado em outra maquina (o PC da TI, por exemplo) le e grava
no Chamados.

## A ideia em uma frase

**A API nao e um sistema paralelo.** E a mesma aplicacao, autenticada por um
token no lugar da sessao do navegador:

- **gravar** e nas **mesmas rotas que a tela usa** (`/chamados/criar/`,
  `/chamados/atendimento/iniciar/`...). Assim o chamado aberto pelo seu sistema
  nasce com evento na linha do tempo e com notificacao por e-mail, igual ao
  Kanban — nao existe uma "regra da API" para divergir da regra da tela;
- **ler** tem endpoints proprios (`/api/v1/tabelas/...`), porque consulta
  generica e o que o navegador nao tem. Eles usam o catalogo do Painel do
  Titular, entao herdam busca, paginacao e a barreira de segredo: **senha, hash e
  texto cifrado nunca saem**.

## 1. Criar o token (no servidor)

```bash
cd /opt/chamados
.venv/bin/python manage.py criar_token_api "Sistema do PC do Fabiano" fabiano.polone
# para permitir gravar tambem:
.venv/bin/python manage.py criar_token_api "Sistema do PC do Fabiano" fabiano.polone --escrita
```

O valor aparece **uma unica vez**: o banco guarda so o hash (mesmo raciocinio da
senha). Perdeu, gere outro e desative o antigo.

O token aponta para uma **conta do sistema** e o pedido roda com as permissoes
dela — o que aquele usuario pode fazer pela tela, pode pela API; o que nao pode,
tambem nao pode por aqui. Comece **somente leitura** (padrao) e libere escrita
quando precisar.

## 2. Endereco e certificado

Base: `https://192.168.22.17/` (o nginx redireciona HTTP para HTTPS).

O certificado e emitido pela **CA do AD** (`SIDERTEC-SRV-AD-CA`). Maquina no
dominio confia sozinha; fora dele, aponte o cliente para o certificado da CA ou
(so em rede interna e sabendo o que faz) desligue a verificacao.

## 3. Ler

| Rota | O que devolve |
| --- | --- |
| `GET /api/v1/tabelas/` | as tabelas disponiveis, com colunas e campos de busca |
| `GET /api/v1/tabelas/<chave>/` | registros, com `?q=` (busca), `?pagina=` (base 0) e `?por_pagina=` (ate 200) |
| `GET /api/v1/tabelas/<chave>/<id>/` | um registro inteiro, campo a campo |

A lista traz `total`, `pagina` e `paginas`, entao da para percorrer tudo sem
adivinhar quantas paginas existem.

## 4. Gravar

Use a rota do modulo, com o mesmo token. As mais uteis:

| Acao | Rota | Como manda |
| --- | --- | --- |
| Abrir chamado | `POST /chamados/criar/` | formulario: `titulo`, `descricao` |
| Responder chamado | `POST /meus-chamados/<numero>/mensagens/` | formulario: `texto` (+ `anexos`) |
| Play | `POST /chamados/atendimento/iniciar/` | JSON: `ticket_number` |
| Pause / Stop | `POST /chamados/atendimento/encerrar/` | JSON: `ticket_number`, `action`, `description` |
| Nova pendencia | `POST /chamados/pendencias/criar/` | JSON: `titulo`, `descricao`, `prioridade` |
| Entrada de insumo | `POST /insumos/<id>/entrada/` | JSON: `quantidade`, `observacao` |
| Retirada de insumo | `POST /insumos/<id>/retirar/` | JSON: `quantidade`, `entregue_para`, `motivo` |
| Nova requisicao | `POST /contratos/requisicoes/criar/` | JSON: `titulo`, `tipo`, `texto` |

O catalogo completo, com os campos de cada uma, esta em `core/painel_acoes.py` —
e o mesmo que o terminal do painel usa.

Todas respondem `{"ok": true, "message": "..."}` ou `{"ok": false, "message":
"..."}` com o status HTTP correspondente. Para as rotas de tela (que no navegador
redirecionam), mande tambem `X-Requested-With: XMLHttpRequest` para receber JSON.

## 5. Arquivos

Arquivo trafega como bytes na propria API — seu sistema **nao** toca o disco do
servidor.

- **Enviar:** `multipart/form-data` na rota do modulo, no campo que ela espera
  (`anexos` em documentos e servicos, `arquivo` na importacao de e-mails,
  `termo_assinado` no emprestimo, `foto_produto` no orcamento).
- **Baixar:** `GET` na rota do anexo; a resposta e o arquivo. Os ids dos anexos
  saem nas tabelas `*_anexos` da API de leitura.
- Limite por pedido: **100 MB** (`client_max_body_size` do nginx).

## 6. Exemplo (Python)

```python
import requests

BASE = "https://192.168.22.17"
TOKEN = "<o valor gerado no passo 1>"
SESSAO = requests.Session()
SESSAO.headers["Authorization"] = f"Token {TOKEN}"
SESSAO.headers["X-Requested-With"] = "XMLHttpRequest"
SESSAO.verify = "/caminho/da/ca-sidertec.crt"   # ou False, so em rede interna

# ler: chamados abertos hoje
lista = SESSAO.get(f"{BASE}/api/v1/tabelas/chamados/", params={"q": "impressora"}).json()
for linha in lista["linhas"]:
    print(linha["pk"], linha["valores"])

# gravar: abrir um chamado (nasce com evento na timeline e notificacao)
novo = SESSAO.post(
    f"{BASE}/chamados/criar/",
    data={"titulo": "Impressora do RH", "descricao": "Nao imprime desde hoje."},
).json()
print(novo["ticket_number"])

# arquivo: anexar um documento
with open("contrato.pdf", "rb") as f:
    SESSAO.post(f"{BASE}/documentos/criar/", data={"nome": "Contrato"}, files={"anexos": f})
```

## 7. Seguranca

- O token vale como a **conta** que ele carrega: trate como senha. Guarde fora do
  codigo (variavel de ambiente), nunca no Git.
- Token **somente leitura** e o padrao. So gere com `--escrita` o que precisa
  gravar, e prefira dois tokens a um que faz tudo.
- Para revogar: desative o registro em `TokenApi` (`ativo=False`) — o token para
  de valer no pedido seguinte.
- O CSRF e dispensado **apenas** no pedido autenticado por token. Isso e seguro
  porque nenhum navegador manda o cabecalho `Authorization` sozinho: o ataque que
  o CSRF previne (site malicioso reusando o cookie da vitima) nao consegue
  produzir um token valido.
- `ultimo_uso` fica gravado a cada chamada — serve para achar token esquecido.
