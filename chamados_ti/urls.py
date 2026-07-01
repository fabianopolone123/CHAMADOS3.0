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

if settings.SERVE_STATIC_WITH_DJANGO:
    urlpatterns += [
        re_path(r"^static/(?P<path>.*)$", staticfiles_serve, {"insecure": True}),
    ]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
