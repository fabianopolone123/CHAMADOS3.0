"""Ponte entre as telas classicas e o terminal do Painel do Titular.

Boa parte dos modulos foi escrita para tela: a view grava, chama
`messages.success(...)` e devolve um `redirect` para a listagem. Isso e otimo no
navegador e inutil para quem chama por `fetch` — o terminal segue o redirect,
recebe o HTML da listagem e nao tem como saber se deu certo. Pior: um erro de
validacao tambem redireciona, entao **falha e sucesso ficam iguais**.

A saida obvia seria uma rota paralela para o painel. Seria a saida errada: duas
rotas para a mesma regra e a origem certa de uma divergir da outra com o tempo.

Aqui o caminho e outro: a **mesma view**, e so a resposta muda quando o pedido
vem por `fetch` (`X-Requested-With: XMLHttpRequest`). O decorador deixa a view
rodar do jeito de sempre e, no fim, le os `messages` que ela mesma produziu para
montar o JSON — mensagem de erro vira `{"ok": false}` com o texto que a tela
mostraria; o resto vira `{"ok": true}`. A view nao sabe que o painel existe.
"""
from __future__ import annotations

from functools import wraps

from django.contrib import messages
from django.http import JsonResponse


def _pedido_por_fetch(request) -> bool:
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def json_quando_xhr(view_func):
    """Converte a resposta de tela (redirect + messages) em JSON para o `fetch`.

    Views que ja respondem JSON passam intactas, entao da para aplicar sem medo
    em uma view que venha a ser convertida depois.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        resposta = view_func(request, *args, **kwargs)
        if not _pedido_por_fetch(request) or isinstance(resposta, JsonResponse):
            return resposta

        # Consumir o storage aqui e proposital: a mensagem ja vai na resposta e
        # nao deve sobrar para aparecer solta na proxima pagina que o operador
        # abrir na tela classica.
        avisos = list(messages.get_messages(request))
        erro = next((m for m in avisos if m.level >= messages.ERROR), None)
        if erro is not None:
            return JsonResponse({"ok": False, "message": str(erro)}, status=400)

        aviso = next((m for m in avisos if m.level >= messages.SUCCESS), None)
        return JsonResponse({"ok": True, "message": str(aviso) if aviso else "Concluido."})

    return _wrapped_view
