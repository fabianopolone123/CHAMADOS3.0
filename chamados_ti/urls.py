from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.views import serve as staticfiles_serve
from django.shortcuts import redirect
from django.urls import include, path, re_path


def home_redirect(request):
    if request.user.is_authenticated:
        return redirect("tickets_dashboard")
    return redirect("login")


urlpatterns = [
    path("", home_redirect, name="home"),
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
]

def estatico_revalidado(request, path, **kwargs):
    """Serve o estatico mandando o navegador **conferir antes de reusar**.

    O `serve` do staticfiles manda `Last-Modified` e nada de `Cache-Control`.
    Sem essa instrucao o navegador usa cache heuristico: guarda o arquivo por um
    tempo que ele mesmo estima e nem pergunta se mudou. Na pratica, depois de um
    deploy o operador continuava com o JS antigo ate limpar o cache na mao — foi
    o que aconteceu com a numeracao da lista do painel.

    `no-cache` nao quer dizer "nao guarde": quer dizer "guarde, mas revalide".
    Com o `If-Modified-Since` que ja funciona, o custo e um `304` por arquivo, e
    o arquivo novo aparece no primeiro F5 depois do deploy.
    """
    resposta = staticfiles_serve(request, path, insecure=True, **kwargs)
    resposta.headers["Cache-Control"] = "no-cache"
    return resposta


if settings.SERVE_STATIC_WITH_DJANGO:
    urlpatterns += [
        re_path(r"^static/(?P<path>.*)$", estatico_revalidado),
    ]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
