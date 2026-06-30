from django.urls import path

from .views import (
    dashboard_redirect_view,
    finish_attendance_view,
    history_search_view,
    history_view,
    login_view,
    logout_view,
    permissions_view,
    start_attendance_view,
    tickets_dashboard_view,
    toggle_attendant_permission_view,
)

urlpatterns = [
    path("dashboard/", dashboard_redirect_view, name="dashboard"),
    path("chamados/", tickets_dashboard_view, name="tickets_dashboard"),
    path("chamados/atendimento/iniciar/", start_attendance_view, name="start_attendance"),
    path("chamados/atendimento/encerrar/", finish_attendance_view, name="finish_attendance"),
    path("historico/", history_view, name="history"),
    path("historico/buscar/", history_search_view, name="history_search"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("permissoes/", permissions_view, name="permissions"),
    path("permissoes/<int:user_id>/toggle-atendente/", toggle_attendant_permission_view, name="toggle_attendant_permission"),
]
