"""API para um sistema de fora conversar com o Chamados.

O desenho tem uma ideia central: **a API nao e um sistema paralelo**. Ela e a
mesma aplicacao, autenticada por um token no lugar da sessao do navegador.

- **Escrever** e feito nas **rotas que a tela ja usa** (`/chamados/criar/`,
  `/chamados/atendimento/iniciar/`, `/emprestimos/.../anexar-termo-assinado/`).
  Nao ha endpoint novo para cada acao — se houvesse, um dia a regra da API e a
  regra da tela divergiriam, e a divergencia apareceria como chamado sem evento
  na timeline ou estoque sem lancamento. Enviar arquivo tambem e por ali, em
  `multipart/form-data`, do mesmo jeito que o navegador manda.
- **Ler** e o que faltava: o navegador nao tem uma rota generica de consulta.
  Entao aqui existem endpoints de leitura montados sobre `painel_dados` — o
  mesmo catalogo do Painel do Titular, o que traz de graca a busca, a paginacao
  e, principalmente, a **barreira de segredo**: senha, hash e texto cifrado nao
  saem por aqui, como nao saem no painel.

Autenticacao: cabecalho `Authorization: Token <valor>`. O token aponta para uma
conta do sistema e o pedido roda com as permissoes **dela** — a API nao tem
permissao propria.
"""
from __future__ import annotations

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from . import painel_dados
from .models import TokenApi
from .permissions import is_admin_user, is_attendant_user

CABECALHO = "Authorization"
PREFIXO = "Token "

# Metodos que nao mudam nada: um token somente-leitura para aqui.
METODOS_LEITURA = {"GET", "HEAD", "OPTIONS"}


def token_do_pedido(request):
    """Le o token do cabecalho e devolve o registro, ou None."""
    bruto = request.headers.get(CABECALHO, "")
    if not bruto.startswith(PREFIXO):
        return None
    return TokenApi.autenticar(bruto[len(PREFIXO) :].strip())


class TokenApiMiddleware:
    """Deixa qualquer rota do sistema aceitar um token no lugar da sessao.

    E o que faz a API existir sem endpoint novo para escrita: o sistema de fora
    chama a mesma URL que o navegador chama, com o cabecalho do token, e a view
    nem sabe a diferenca — `request.user` chega resolvido do mesmo jeito.

    O CSRF e dispensado **apenas** para o pedido autenticado por token, e isso e
    seguro justamente porque nenhum navegador manda esse cabecalho sozinho: o
    ataque que o CSRF previne (o site malicioso reaproveitando o cookie da
    vitima) nao consegue produzir um `Authorization` valido.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = token_do_pedido(request)
        if token is not None:
            if token.somente_leitura and request.method not in METODOS_LEITURA:
                return JsonResponse(
                    {"ok": False, "message": "Este token e somente de leitura."}, status=403
                )
            request.user = token.usuario
            request.token_api = token
            request._dont_enforce_csrf_checks = True
            # Sem `update_fields` seria um `save()` inteiro a cada chamada.
            TokenApi.objects.filter(pk=token.pk).update(ultimo_uso=timezone.now())
        return self.get_response(request)


def _erro(mensagem: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"ok": False, "message": mensagem}, status=status)


def _guarda(request):
    """Confere token e perfil; devolve a resposta de erro ou None."""
    if getattr(request, "token_api", None) is None:
        return _erro("Informe o token no cabecalho: Authorization: Token <valor>.", status=401)
    if not (is_admin_user(request.user) or is_attendant_user(request.user)):
        return _erro("A conta deste token nao tem acesso aos dados da TI.", status=403)
    return None


@csrf_exempt
@require_GET
def api_tabelas(request):
    """Lista o que da para consultar, com as colunas de cada tabela."""
    erro = _guarda(request)
    if erro:
        return erro
    return JsonResponse(
        {
            "ok": True,
            "usuario": request.user.get_username(),
            "somente_leitura": request.token_api.somente_leitura,
            "tabelas": [
                {
                    "chave": t.chave,
                    "rotulo": t.rotulo,
                    "colunas": list(t.colunas),
                    "busca": list(t.busca),
                    "somente_leitura": t.somente_leitura,
                }
                for t in painel_dados.TABELAS
            ],
        }
    )


@csrf_exempt
@require_GET
def api_tabela(request, chave: str):
    """Registros da tabela, com busca e paginacao.

    `?q=` busca nos campos que a tabela declara, `?pagina=` (base 0) e
    `?por_pagina=` (ate 200) recortam. O total vem junto para o cliente saber
    quantas paginas existem sem adivinhar.
    """
    erro = _guarda(request)
    if erro:
        return erro
    tabela = painel_dados.TABELA_POR_CHAVE.get(chave)
    if not tabela:
        return _erro("Tabela inexistente.", status=404)

    try:
        pagina = max(int(request.GET.get("pagina") or 0), 0)
        por_pagina = min(max(int(request.GET.get("por_pagina") or 50), 1), 200)
    except (TypeError, ValueError):
        return _erro("Parametros de paginacao invalidos.")

    dados = painel_dados.listar(
        tabela, termo=request.GET.get("q") or "", pagina=pagina, por_pagina=por_pagina
    )
    return JsonResponse({"ok": True, **dados})


@csrf_exempt
@require_GET
def api_registro(request, chave: str, pk: str):
    """Um registro inteiro, campo a campo (segredos continuam de fora)."""
    erro = _guarda(request)
    if erro:
        return erro
    tabela = painel_dados.TABELA_POR_CHAVE.get(chave)
    if not tabela:
        return _erro("Tabela inexistente.", status=404)
    try:
        detalhe = painel_dados.detalhar(tabela, pk)
    except Exception:
        return _erro("Registro nao encontrado.", status=404)
    return JsonResponse({"ok": True, **detalhe})
