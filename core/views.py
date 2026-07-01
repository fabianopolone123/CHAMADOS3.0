from __future__ import annotations

from datetime import timedelta
from functools import wraps
import json

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import AberturaChamadoForm, LoginForm
from .models import AtendimentoHistorico, Chamado, ChamadoAnexo
from .permissions import (
    ATTENDANT_GROUP_NAME,
    PRIMARY_ADMIN_USERNAME,
    ensure_permission_groups,
    ensure_user_permission_defaults,
    is_admin_user,
    is_attendant_user,
)


def _landing_route_for_user(user) -> str:
    """Rota inicial pos-login de acordo com o perfil do usuario."""
    if is_admin_user(user) or is_attendant_user(user):
        return "tickets_dashboard"
    return "my_tickets"


def admin_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_admin_user(request.user):
            messages.error(request, "Apenas administradores podem acessar a tela de permissoes.")
            return redirect("tickets_dashboard")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def history_access_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not (is_admin_user(request.user) or is_attendant_user(request.user)):
            messages.error(request, "Voce nao possui permissao para acessar o historico de atendimentos.")
            return redirect("tickets_dashboard")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def _format_duration(duration: timedelta | None) -> str:
    if not duration:
        return "0m"

    total_seconds = max(int(duration.total_seconds()), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {seconds:02d}s"
    return f"{seconds}s"


def _parse_history_query_date(raw_value: str):
    normalized = (raw_value or "").strip()
    if not normalized:
        return None

    parsed = parse_date(normalized)
    if parsed:
        return parsed

    if "/" in normalized:
        parts = normalized.split("/")
        if len(parts) == 3:
            day, month, year = parts
            parsed = parse_date(f"{year}-{month.zfill(2)}-{day.zfill(2)}")
            if parsed:
                return parsed

    return None


def _get_history_queryset_for_user(user):
    queryset = AtendimentoHistorico.objects.select_related("chamado", "atendente").order_by("-iniciado_em")
    if is_admin_user(user):
        return queryset
    return queryset.filter(atendente=user)


def _serialize_history_item(item: AtendimentoHistorico):
    started_at = timezone.localtime(item.iniciado_em)
    finished_at = timezone.localtime(item.finalizado_em) if item.finalizado_em else None
    duration = item.duracao if item.duracao is not None else (timezone.now() - item.iniciado_em if item.iniciado_em else None)
    attendant_name = item.atendente.get_full_name() or item.atendente.username

    return {
        "id": item.id,
        "ticket_number": item.chamado.numero,
        "ticket_title": item.chamado.titulo,
        "attendant_name": attendant_name,
        "attendant_username": item.atendente.username,
        "started_at": started_at.strftime("%d/%m/%Y %H:%M"),
        "finished_at": finished_at.strftime("%d/%m/%Y %H:%M") if finished_at else "Em andamento",
        "duration": _format_duration(duration),
        "type": item.tipo_encerramento or "em andamento",
        "description": item.descricao_atividade or "-",
    }


def _build_mock_ticket(
    *,
    number,
    title,
    description,
    requester,
    requester_email,
    department,
    category,
    subcategory,
    priority,
    priority_class,
    status,
    status_class,
    responsible_attendant,
    opened_at,
    opened_time,
    last_update,
    source,
    attachments,
    history,
):
    return {
        "number": number,
        "title": title,
        "description": description,
        "requester": requester,
        "requester_email": requester_email,
        "department": department,
        "category": category,
        "subcategory": subcategory,
        "priority": priority,
        "priority_class": priority_class,
        "status": status,
        "status_class": status_class,
        "responsible_attendant": responsible_attendant,
        "opened_at": opened_at,
        "opened_time": opened_time,
        "last_update": last_update,
        "source": source,
        "attachments": attachments,
        "history": history,
    }


def _build_attachment(name, size, file_type):
    return {
        "name": name,
        "size": size,
        "file_type": file_type,
    }


def _build_history_entry(author, timestamp, message, kind="comment"):
    return {
        "author": author,
        "timestamp": timestamp,
        "message": message,
        "kind": kind,
    }


def _build_timeline_excerpt(ticket_number):
    return [
        _build_history_entry(
            "Sistema",
            "Hoje, 08:12",
            f"Chamado {ticket_number} criado e direcionado para triagem inicial.",
            kind="created",
        ),
        _build_history_entry(
            "Roberta Lima",
            "Hoje, 08:45",
            "Solicitante confirmou os detalhes adicionais do problema.",
        ),
        _build_history_entry(
            "Atendente TI",
            "Hoje, 09:03",
            "Aguardando verificacao do ambiente e resposta do usuario.",
        ),
    ]


def _default_ticket_payload(
    *,
    number,
    title,
    requester,
    requester_email,
    department,
    category,
    subcategory,
    priority,
    priority_class,
    status,
    status_class,
    responsible_attendant,
    opened_at,
    opened_time,
    last_update,
    source,
    description_suffix,
):
    return _build_mock_ticket(
        number=number,
        title=title,
        description=(
            f"{title}. {description_suffix} "
            "Esta descricao e um mock temporario para a interface de detalhes do chamado."
        ),
        requester=requester,
        requester_email=requester_email,
        department=department,
        category=category,
        subcategory=subcategory,
        priority=priority,
        priority_class=priority_class,
        status=status,
        status_class=status_class,
        responsible_attendant=responsible_attendant,
        opened_at=opened_at,
        opened_time=opened_time,
        last_update=last_update,
        source=source,
        attachments=[
            _build_attachment("print-erro-vpn.png", "248 KB", "Imagem"),
            _build_attachment("log-acesso.txt", "14 KB", "Texto"),
        ],
        history=_build_timeline_excerpt(number),
    )


def _build_default_attendant_tickets(user, position):
    display_name = user.get_full_name() or user.username.replace(".", " ").title()
    slug = user.username.lower()
    primary_ticket_number = f"INC-10{50 + position}"
    secondary_ticket_number = f"REQ-20{80 + position}"

    return [
        _default_ticket_payload(
            number=primary_ticket_number,
            title=f"Analise de acesso para {display_name}",
            requester="Equipe Corporativa",
            requester_email="suporte@empresa.local",
            department="Tecnologia da Informacao",
            category="Acesso",
            subcategory="VPN",
            priority="Alta",
            priority_class="priority-high",
            status="Em atendimento",
            status_class="status-warning",
            responsible_attendant=display_name,
            opened_at="30/06/2026 08:20",
            opened_time="1h 42m",
            last_update="30/06/2026 09:18",
            source="Portal de chamados",
            description_suffix=f"Fila atribuida automaticamente ao atendente {display_name}.",
        ),
        _default_ticket_payload(
            number=secondary_ticket_number,
            title=f"Solicitacao pendente para {display_name}",
            requester="Central de Operacoes",
            requester_email="operacoes@empresa.local",
            department="Operacoes",
            category="Cadastro",
            subcategory="Novo usuario",
            priority="Media",
            priority_class="priority-medium",
            status="Aguardando usuario",
            status_class="status-info",
            responsible_attendant=display_name,
            opened_at="30/06/2026 07:55",
            opened_time="2h 07m",
            last_update="30/06/2026 09:05",
            source="E-mail",
            description_suffix=f"Mock temporario associado ao usuario {slug}.",
        ),
    ]


def _build_attendant_columns():
    User = get_user_model()
    attendant_users = list(
        User.objects.filter(groups__name=ATTENDANT_GROUP_NAME).order_by("first_name", "username").distinct()
    )

    columns = []
    for position, user in enumerate(attendant_users, start=1):
        display_name = user.get_full_name() or user.username
        initials = "".join(part[0] for part in display_name.split()[:2]).upper() or user.username[:2].upper()
        ticket_list = _build_default_attendant_tickets(user, position)
        columns.append(
            {
                "id": f"attendant-{user.username}",
                "username": user.username,
                "name": display_name,
                "role": "Atendente TI",
                "avatar": initials[:2],
                "tickets": ticket_list,
            }
        )

    if columns:
        return columns

    return [
        {
            "id": "atendente-alex",
            "username": "alex.silva",
            "name": "Alex Silva",
            "role": "Infraestrutura",
            "avatar": "AS",
            "tickets": [
                _default_ticket_payload(
                    number="INC-1048",
                    title="Notebook sem acesso a VPN",
                    requester="Mariana Costa",
                    requester_email="mariana.costa@empresa.local",
                    department="Comercial",
                    category="Acesso remoto",
                    subcategory="VPN corporativa",
                    priority="Alta",
                    priority_class="priority-high",
                    status="Em atendimento",
                    status_class="status-warning",
                    responsible_attendant="Alex Silva",
                    opened_at="30/06/2026 07:40",
                    opened_time="1h 42m",
                    last_update="30/06/2026 08:58",
                    source="Portal de chamados",
                    description_suffix="O notebook apresenta falha de autenticacao ao conectar na VPN corporativa.",
                ),
                _default_ticket_payload(
                    number="INC-1039",
                    title="Erro no cliente de e-mail do financeiro",
                    requester="Carlos Mota",
                    requester_email="carlos.mota@empresa.local",
                    department="Financeiro",
                    category="E-mail",
                    subcategory="Cliente Outlook",
                    priority="Media",
                    priority_class="priority-medium",
                    status="Em atendimento",
                    status_class="status-warning",
                    responsible_attendant="Alex Silva",
                    opened_at="30/06/2026 06:58",
                    opened_time="3h 15m",
                    last_update="30/06/2026 08:50",
                    source="Telefone",
                    description_suffix="O cliente de e-mail abre, mas nao sincroniza a caixa de entrada.",
                ),
            ],
        },
        {
            "id": "atendente-bianca",
            "username": "bianca.torres",
            "name": "Bianca Torres",
            "role": "Suporte N1",
            "avatar": "BT",
            "tickets": [
                _default_ticket_payload(
                    number="REQ-2081",
                    title="Criacao de usuario para novo colaborador",
                    requester="RH Corporativo",
                    requester_email="rh@empresa.local",
                    department="Recursos Humanos",
                    category="Cadastro",
                    subcategory="Usuario novo",
                    priority="Baixa",
                    priority_class="priority-low",
                    status="Pendente de aprovacao",
                    status_class="status-info",
                    responsible_attendant="Bianca Torres",
                    opened_at="30/06/2026 04:58",
                    opened_time="5h 08m",
                    last_update="30/06/2026 08:32",
                    source="E-mail",
                    description_suffix="Solicitacao para preparar o acesso do novo colaborador da area de RH.",
                )
            ],
        },
        {
            "id": "atendente-diego",
            "username": "diego.rocha",
            "name": "Diego Rocha",
            "role": "Redes e Servidores",
            "avatar": "DR",
            "tickets": [
                _default_ticket_payload(
                    number="INC-1054",
                    title="Oscilacao de internet na filial",
                    requester="Unidade Campinas",
                    requester_email="campinas@empresa.local",
                    department="Operacoes",
                    category="Rede",
                    subcategory="Link principal",
                    priority="Critica",
                    priority_class="priority-critical",
                    status="Critico",
                    status_class="status-danger",
                    responsible_attendant="Diego Rocha",
                    opened_at="30/06/2026 09:08",
                    opened_time="27m",
                    last_update="30/06/2026 09:26",
                    source="Monitoramento",
                    description_suffix="Oscilacao recorrente no link principal da unidade, exigindo verificacao de redes.",
                )
            ],
        },
    ]


def _build_unassigned_tickets():
    return [
        _default_ticket_payload(
            number="INC-1058",
            title="Impressora do faturamento nao responde",
            requester="Patricia Gomes",
            requester_email="patricia.gomes@empresa.local",
            department="Financeiro",
            category="Impressao",
            subcategory="Driver da impressora",
            priority="Media",
            priority_class="priority-medium",
            status="Nao atribuido",
            status_class="status-muted",
            responsible_attendant=None,
            opened_at="30/06/2026 09:34",
            opened_time="18m",
            last_update="30/06/2026 09:41",
            source="Portal de chamados",
            description_suffix="A impressora do setor nao conclui a fila de impressao do fechamento.",
        ),
        _default_ticket_payload(
            number="INC-1056",
            title="Senha expirada no ERP",
            requester="Joao Pedro",
            requester_email="joao.pedro@empresa.local",
            department="Comercial",
            category="Acesso",
            subcategory="ERP",
            priority="Alta",
            priority_class="priority-high",
            status="Nao atribuido",
            status_class="status-muted",
            responsible_attendant=None,
            opened_at="30/06/2026 08:58",
            opened_time="52m",
            last_update="30/06/2026 09:22",
            source="Telefone",
            description_suffix="O usuario nao consegue redefinir a senha pelo fluxo de autoatendimento.",
        ),
        _default_ticket_payload(
            number="REQ-2084",
            title="Instalacao do pacote Adobe",
            requester="Time de Marketing",
            requester_email="marketing@empresa.local",
            department="Marketing",
            category="Software",
            subcategory="Licenca Adobe",
            priority="Baixa",
            priority_class="priority-low",
            status="Nao atribuido",
            status_class="status-muted",
            responsible_attendant=None,
            opened_at="30/06/2026 07:46",
            opened_time="2h 05m",
            last_update="30/06/2026 09:14",
            source="E-mail",
            description_suffix="Solicitacao de instalacao para criacao de materiais da campanha atual.",
        ),
    ]


def _collect_ticket_details(attendants, unassigned_tickets):
    ticket_details_map = {ticket["number"]: ticket for ticket in unassigned_tickets}
    for attendant in attendants:
        for ticket in attendant["tickets"]:
            ticket_details_map[ticket["number"]] = ticket
    return ticket_details_map


def _sync_mock_tickets(ticket_details_map):
    for payload in ticket_details_map.values():
        Chamado.objects.update_or_create(
            numero=payload["number"],
            defaults={
                "titulo": payload["title"],
                "descricao": payload["description"],
                "solicitante_nome": payload["requester"],
                "solicitante_email": payload["requester_email"],
                "departamento": payload["department"],
                "categoria": payload["category"],
                "subcategoria": payload["subcategory"] or "",
                "prioridade": payload["priority"],
                "status": payload["status"],
                "origem": payload["source"],
                "aberto_em_referencia": payload["opened_at"],
                "ultima_atualizacao_referencia": payload["last_update"],
            },
        )


def _serialize_attendance_state(attendance: AtendimentoHistorico | None):
    if not attendance:
        return None

    elapsed = timezone.now() - attendance.iniciado_em
    return {
        "history_id": attendance.id,
        "ticket_number": attendance.chamado.numero,
        "started_at_iso": attendance.iniciado_em.isoformat(),
        "started_at_display": timezone.localtime(attendance.iniciado_em).strftime("%d/%m/%Y %H:%M"),
        "elapsed_display": _format_duration(elapsed),
    }


def _append_attendance_state(ticket, active_state):
    is_active = bool(active_state and active_state["ticket_number"] == ticket["number"])
    ticket["attendance"] = {
        "is_active": is_active,
        "started_at_iso": active_state["started_at_iso"] if is_active else "",
        "started_at_display": active_state["started_at_display"] if is_active else "",
        "elapsed_display": active_state["elapsed_display"] if is_active else "",
    }
    return ticket


def _prepare_dashboard_payload_for_user(user):
    attendants = _build_attendant_columns()
    unassigned_tickets = _build_unassigned_tickets()
    ticket_details_map = _collect_ticket_details(attendants, unassigned_tickets)
    _sync_mock_tickets(ticket_details_map)

    active_attendance = (
        AtendimentoHistorico.objects.select_related("chamado")
        .filter(atendente=user, finalizado_em__isnull=True)
        .first()
    )
    active_state = _serialize_attendance_state(active_attendance)

    for ticket in unassigned_tickets:
        _append_attendance_state(ticket, active_state)
    for attendant in attendants:
        for ticket in attendant["tickets"]:
            _append_attendance_state(ticket, active_state)
    for ticket in ticket_details_map.values():
        _append_attendance_state(ticket, active_state)

    return attendants, unassigned_tickets, ticket_details_map, active_state


def _json_error(message, status=400, **extra):
    payload = {"ok": False, "message": message}
    payload.update(extra)
    return JsonResponse(payload, status=status)


def _load_request_payload(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return None


def login_view(request):
    if request.user.is_authenticated:
        return redirect(_landing_route_for_user(request.user))

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]
        user = authenticate(request, username=username, password=password)

        if user is not None:
            ensure_user_permission_defaults(user)
            login(request, user)
            messages.success(request, "Login realizado com sucesso.")
            return redirect(_landing_route_for_user(user))

        messages.error(request, "Usuario ou senha invalidos. Verifique suas credenciais corporativas.")

    context = {
        "page_title": "Sistema de Chamados TI",
        "form": form,
    }
    return render(request, "core/login.html", context)


@login_required
def tickets_dashboard_view(request):
    attendants, unassigned_tickets, ticket_details_map, active_attendance = _prepare_dashboard_payload_for_user(request.user)

    stats = {
        "total_open": sum(len(attendant["tickets"]) for attendant in attendants) + len(unassigned_tickets),
        "unassigned": len(unassigned_tickets),
        "attendants": len(attendants),
    }

    context = {
        "page_title": "Painel de Chamados TI",
        "attendants": attendants,
        "unassigned_tickets": unassigned_tickets,
        "ticket_details_map": ticket_details_map,
        "active_attendance": active_attendance,
        "stats": stats,
        "is_admin": is_admin_user(request.user),
        "can_view_history": is_admin_user(request.user) or is_attendant_user(request.user),
    }
    return render(request, "chamados/dashboard_atendente.html", context)


@login_required
@require_POST
def start_attendance_view(request):
    payload = _load_request_payload(request)
    if payload is None:
        return _json_error("Nao foi possivel ler os dados enviados.")

    ticket_number = (payload.get("ticket_number") or "").strip()
    if not ticket_number:
        return _json_error("Informe o chamado que deve iniciar atendimento.")

    chamado = Chamado.objects.filter(numero=ticket_number).first()
    if not chamado:
        return _json_error("Chamado nao encontrado para iniciar atendimento.", status=404)

    existing_active = (
        AtendimentoHistorico.objects.select_related("chamado")
        .filter(atendente=request.user, finalizado_em__isnull=True)
        .first()
    )
    if existing_active:
        if existing_active.chamado.numero == ticket_number:
            return _json_error(
                "Este chamado ja esta com atendimento ativo para voce.",
                status=409,
                active_ticket_number=existing_active.chamado.numero,
            )
        return _json_error(
            "Voce ja possui outro atendimento em andamento. Pause ou finalize antes de iniciar um novo.",
            status=409,
            active_ticket_number=existing_active.chamado.numero,
        )

    try:
        with transaction.atomic():
            attendance = AtendimentoHistorico.objects.create(
                chamado=chamado,
                atendente=request.user,
                iniciado_em=timezone.now(),
            )
    except IntegrityError:
        return _json_error(
            "Ja existe um atendimento ativo para este usuario. Atualize a tela e tente novamente.",
            status=409,
        )

    active_state = _serialize_attendance_state(attendance)
    return JsonResponse(
        {
            "ok": True,
            "message": f"Atendimento iniciado no chamado {ticket_number}.",
            "attendance": active_state,
        }
    )


@login_required
@require_POST
def finish_attendance_view(request):
    payload = _load_request_payload(request)
    if payload is None:
        return _json_error("Nao foi possivel ler os dados enviados.")

    ticket_number = (payload.get("ticket_number") or "").strip()
    action = (payload.get("action") or "").strip().lower()
    description = (payload.get("description") or "").strip()

    if not ticket_number:
        return _json_error("Informe o chamado do atendimento.")
    if action not in {
        AtendimentoHistorico.TIPO_ENCERRAMENTO_PAUSE,
        AtendimentoHistorico.TIPO_ENCERRAMENTO_STOP,
    }:
        return _json_error("Tipo de encerramento invalido.")
    if not description:
        return _json_error("Descreva o que foi feito neste atendimento.")

    attendance = (
        AtendimentoHistorico.objects.select_related("chamado")
        .filter(atendente=request.user, finalizado_em__isnull=True)
        .first()
    )
    if not attendance:
        return _json_error("Nao existe atendimento ativo para encerrar.", status=409)
    if attendance.chamado.numero != ticket_number:
        return _json_error(
            "O atendimento ativo pertence a outro chamado. Atualize a tela antes de continuar.",
            status=409,
            active_ticket_number=attendance.chamado.numero,
        )

    try:
        with transaction.atomic():
            attendance.finalizar(tipo_encerramento=action, descricao_atividade=description)
            attendance.save()
    except ValidationError as exc:
        message = exc.messages[0] if exc.messages else "Nao foi possivel encerrar o atendimento."
        return _json_error(message)

    duration_display = _format_duration(attendance.duracao)
    action_label = "pausado" if action == AtendimentoHistorico.TIPO_ENCERRAMENTO_PAUSE else "finalizado"

    return JsonResponse(
        {
            "ok": True,
            "message": f"Atendimento {action_label} no chamado {ticket_number}.",
            "ticket_number": ticket_number,
            "action": action,
            "duration_display": duration_display,
            "history_entry": {
                "author": request.user.get_full_name() or request.user.username,
                "timestamp": timezone.localtime(attendance.finalizado_em).strftime("%d/%m/%Y %H:%M"),
                "message": description,
                "kind": "comment",
            },
        }
    )


_STATUS_BADGE_CLASS = {
    Chamado.STATUS_ABERTO: "status-info",
    Chamado.STATUS_EM_ATENDIMENTO: "status-warning",
    Chamado.STATUS_AGUARDANDO_USUARIO: "status-muted",
    Chamado.STATUS_RESOLVIDO: "status-success",
    Chamado.STATUS_FECHADO: "status-neutral",
}

_PRIORIDADE_BADGE_CLASS = {
    Chamado.PRIORIDADE_BAIXA: "priority-low",
    Chamado.PRIORIDADE_MEDIA: "priority-medium",
    Chamado.PRIORIDADE_ALTA: "priority-high",
    Chamado.PRIORIDADE_CRITICA: "priority-critical",
}


def _serialize_my_ticket(chamado: Chamado):
    return {
        "number": chamado.numero,
        "title": chamado.titulo,
        "category": chamado.categoria or "-",
        "status_label": chamado.status_label,
        "status_class": _STATUS_BADGE_CLASS.get(chamado.status, "status-muted"),
        "priority_label": chamado.prioridade_label,
        "priority_class": _PRIORIDADE_BADGE_CLASS.get(chamado.prioridade, "priority-medium"),
        "created_at": timezone.localtime(chamado.criado_em).strftime("%d/%m/%Y %H:%M"),
        "updated_at": timezone.localtime(chamado.atualizado_em).strftime("%d/%m/%Y %H:%M"),
        "is_closed": chamado.status in Chamado.STATUS_ENCERRADOS,
    }


def _serialize_ticket_timeline(chamado: Chamado):
    timeline = []
    for item in chamado.atendimentos.select_related("atendente").order_by("iniciado_em"):
        author = item.atendente.get_full_name() or item.atendente.username
        if item.finalizado_em:
            action = (
                "finalizou o atendimento"
                if item.tipo_encerramento == AtendimentoHistorico.TIPO_ENCERRAMENTO_STOP
                else "pausou o atendimento"
            )
            message = item.descricao_atividade or "-"
            timestamp = timezone.localtime(item.finalizado_em)
        else:
            action = "iniciou o atendimento"
            message = "Atendimento em andamento."
            timestamp = timezone.localtime(item.iniciado_em)
        timeline.append(
            {
                "author": author,
                "action": action,
                "message": message,
                "timestamp": timestamp.strftime("%d/%m/%Y %H:%M"),
            }
        )
    return timeline


@login_required
def my_tickets_view(request):
    chamados = list(Chamado.objects.filter(solicitante=request.user).order_by("-criado_em"))
    rows = [_serialize_my_ticket(chamado) for chamado in chamados]

    stats = {
        "total": len(chamados),
        "em_aberto": sum(1 for c in chamados if c.status not in Chamado.STATUS_ENCERRADOS),
        "encerrados": sum(1 for c in chamados if c.status in Chamado.STATUS_ENCERRADOS),
    }

    context = {
        "page_title": "Meus Chamados",
        "tickets": rows,
        "stats": stats,
        "is_admin": is_admin_user(request.user),
        "is_attendant": is_attendant_user(request.user),
        "can_view_history": is_admin_user(request.user) or is_attendant_user(request.user),
    }
    return render(request, "chamados/meus_chamados.html", context)


@login_required
def open_ticket_view(request):
    form = AberturaChamadoForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        chamado = form.save(commit=False)
        chamado.solicitante = request.user
        chamado.solicitante_nome = request.user.get_full_name() or request.user.username
        chamado.solicitante_email = request.user.email or ""
        chamado.status = Chamado.STATUS_ABERTO
        chamado.origem = "Portal do solicitante"
        anexos = form.cleaned_data.get("anexos") or []

        for _attempt in range(3):
            chamado.numero = Chamado.gerar_numero()
            try:
                with transaction.atomic():
                    chamado.save()
                    for arquivo in anexos:
                        ChamadoAnexo.objects.create(
                            chamado=chamado,
                            arquivo=arquivo,
                            nome_original=arquivo.name,
                            enviado_por=request.user,
                        )
                break
            except IntegrityError:
                continue
        else:
            messages.error(request, "Nao foi possivel gerar o numero do chamado. Tente novamente.")
            context = {"page_title": "Abrir Chamado", "form": form, "can_view_history": False}
            return render(request, "chamados/abrir_chamado.html", context)

        messages.success(request, f"Chamado {chamado.numero} aberto com sucesso.")
        return redirect("ticket_detail", numero=chamado.numero)

    context = {
        "page_title": "Abrir Chamado",
        "form": form,
        "is_admin": is_admin_user(request.user),
        "is_attendant": is_attendant_user(request.user),
        "can_view_history": is_admin_user(request.user) or is_attendant_user(request.user),
    }
    return render(request, "chamados/abrir_chamado.html", context)


@login_required
def ticket_detail_view(request, numero: str):
    chamado = get_object_or_404(Chamado, numero=numero)

    pode_ver_todos = is_admin_user(request.user) or is_attendant_user(request.user)
    if not pode_ver_todos and chamado.solicitante_id != request.user.id:
        messages.error(request, "Voce nao tem acesso a este chamado.")
        return redirect("my_tickets")

    context = {
        "page_title": f"Chamado {chamado.numero}",
        "chamado": chamado,
        "status_label": chamado.status_label,
        "status_class": _STATUS_BADGE_CLASS.get(chamado.status, "status-muted"),
        "priority_label": chamado.prioridade_label,
        "priority_class": _PRIORIDADE_BADGE_CLASS.get(chamado.prioridade, "priority-medium"),
        "timeline": _serialize_ticket_timeline(chamado),
        "anexos": list(chamado.anexos.all()),
        "is_owner": chamado.solicitante_id == request.user.id,
        "is_admin": is_admin_user(request.user),
        "is_attendant": is_attendant_user(request.user),
        "can_view_history": pode_ver_todos,
    }
    return render(request, "chamados/detalhe_chamado.html", context)


@history_access_required
def history_view(request):
    history_items = list(_get_history_queryset_for_user(request.user)[:80])
    rows = [_serialize_history_item(item) for item in history_items]

    context = {
        "page_title": "Historico de Atendimentos",
        "history_rows": rows,
        "history_total": len(rows),
        "history_limit": 200,
        "is_admin": is_admin_user(request.user),
        "can_view_history": True,
    }
    return render(request, "chamados/historico_atendimentos.html", context)


@history_access_required
def history_search_view(request):
    query = (request.GET.get("q") or "").strip()
    queryset = _get_history_queryset_for_user(request.user)

    if query:
        filters = (
            Q(chamado__numero__icontains=query)
            | Q(chamado__titulo__icontains=query)
            | Q(atendente__username__icontains=query)
            | Q(atendente__first_name__icontains=query)
            | Q(atendente__last_name__icontains=query)
            | Q(descricao_atividade__icontains=query)
            | Q(tipo_encerramento__icontains=query)
        )

        query_date = _parse_history_query_date(query)
        if query_date:
            filters |= Q(iniciado_em__date=query_date) | Q(finalizado_em__date=query_date)

        queryset = queryset.filter(filters)

    items = list(queryset[:200])
    return JsonResponse(
        {
            "ok": True,
            "count": len(items),
            "results": [_serialize_history_item(item) for item in items],
        }
    )


@admin_required
def permissions_view(request):
    ensure_permission_groups()
    User = get_user_model()
    users = User.objects.all().order_by("username")

    rows = []
    for user in users:
        rows.append(
            {
                "id": user.id,
                "username": user.username,
                "name": user.get_full_name() or "-",
                "email": user.email or "-",
                "is_attendant": is_attendant_user(user),
                "is_admin": is_admin_user(user),
                "is_primary_admin": user.username.lower() == PRIMARY_ADMIN_USERNAME.lower(),
            }
        )

    context = {
        "page_title": "Permissoes do Sistema",
        "users": rows,
        "is_admin": True,
        "can_view_history": True,
    }
    return render(request, "core/permissions.html", context)


@admin_required
@require_POST
def toggle_attendant_permission_view(request, user_id: int):
    groups = ensure_permission_groups()
    User = get_user_model()
    user = get_object_or_404(User, pk=user_id)
    ensure_user_permission_defaults(user)

    if user.groups.filter(name=ATTENDANT_GROUP_NAME).exists():
        user.groups.remove(groups.attendant)
        messages.success(request, f"{user.username} removido do perfil Atendente TI.")
    else:
        user.groups.add(groups.attendant)
        messages.success(request, f"{user.username} adicionado ao perfil Atendente TI.")

    return redirect("permissions")


@login_required
def dashboard_redirect_view(request):
    return redirect(_landing_route_for_user(request.user))


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Sessao encerrada com sucesso.")
    return redirect("login")
