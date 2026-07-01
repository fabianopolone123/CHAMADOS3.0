from django.urls import path

from .views import (
    dashboard_redirect_view,
    download_anexo_view,
    finish_attendance_view,
    history_search_view,
    history_view,
    login_view,
    logout_view,
    move_ticket_view,
    my_tickets_view,
    open_ticket_view,
    permissions_view,
    start_attendance_view,
    ticket_detail_view,
    tickets_dashboard_view,
    toggle_attendant_permission_view,
)

urlpatterns = [
    path("dashboard/", dashboard_redirect_view, name="dashboard"),
    path("chamados/", tickets_dashboard_view, name="tickets_dashboard"),
    path("chamados/atendimento/iniciar/", start_attendance_view, name="start_attendance"),
    path("chamados/atendimento/encerrar/", finish_attendance_view, name="finish_attendance"),
    path("chamados/mover/", move_ticket_view, name="move_ticket"),
    path("meus-chamados/", my_tickets_view, name="my_tickets"),
    path("meus-chamados/novo/", open_ticket_view, name="open_ticket"),
    path("meus-chamados/<str:numero>/", ticket_detail_view, name="ticket_detail"),
    path("meus-chamados/<str:numero>/anexo/<int:anexo_id>/", download_anexo_view, name="download_anexo"),
    path("historico/", history_view, name="history"),
    path("historico/buscar/", history_search_view, name="history_search"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("permissoes/", permissions_view, name="permissions"),
    path("permissoes/<int:user_id>/toggle-atendente/", toggle_attendant_permission_view, name="toggle_attendant_permission"),
]
