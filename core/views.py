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
from django.http import FileResponse, Http404, JsonResponse
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import AberturaChamadoForm, LoginForm
from .models import AtendimentoHistorico, Chamado, ChamadoAnexo, ChamadoEvento
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


def ti_required(view_func):
    """Restringe o acesso a administradores e atendentes de TI; usuario comum e redirecionado."""

    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not (is_admin_user(request.user) or is_attendant_user(request.user)):
            messages.error(request, "Apenas a equipe de TI pode acessar o quadro de atendimento.")
            return redirect("my_tickets")
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


def _attendant_users():
    """Usuarios do grupo Atendente TI, na ordem de exibicao das colunas."""
    User = get_user_model()
    return list(
        User.objects.filter(groups__name=ATTENDANT_GROUP_NAME)
        .order_by("first_name", "username")
        .distinct()
    )


def _requester_display(chamado: Chamado) -> str:
    if chamado.solicitante_nome:
        return chamado.solicitante_nome
    if chamado.solicitante:
        return chamado.solicitante.get_full_name() or chamado.solicitante.username
    return "-"


def _attendant_display(user):
    if not user:
        return ""
    return user.get_full_name() or user.username


def _serialize_kanban_card(chamado: Chamado, active_state):
    is_active = bool(active_state and active_state["ticket_number"] == chamado.numero)
    return {
        "number": chamado.numero,
        "title": chamado.titulo,
        "requester": _requester_display(chamado),
        "current_attendant": _attendant_display(chamado.atendente_atual),
        "opened_at": timezone.localtime(chamado.criado_em).strftime("%d/%m/%Y %H:%M"),
        "status": chamado.status,
        "status_label": chamado.status_label,
        "status_class": _STATUS_BADGE_CLASS.get(chamado.status, "status-muted"),
        "priority_label": chamado.prioridade_label,
        "priority_class": _PRIORIDADE_BADGE_CLASS.get(chamado.prioridade, "priority-medium"),
        "attendance": {
            "is_active": is_active,
            "started_at_iso": active_state["started_at_iso"] if is_active else "",
            "elapsed_display": active_state["elapsed_display"] if is_active else "",
        },
    }


@ti_required
def tickets_dashboard_view(request):
    active_attendance = (
        AtendimentoHistorico.objects.select_related("chamado")
        .filter(atendente=request.user, finalizado_em__isnull=True)
        .first()
    )
    active_state = _serialize_attendance_state(active_attendance)

    attendants = _attendant_users()
    attendant_ids = {user.id for user in attendants}
    by_attendant = {user.id: [] for user in attendants}
    abertos = []
    fechados = []

    chamados = Chamado.objects.select_related("solicitante", "atendente_atual").order_by("-criado_em")
    for chamado in chamados:
        card = _serialize_kanban_card(chamado, active_state)
        if chamado.status in Chamado.STATUS_ENCERRADOS:
            fechados.append(card)
        elif chamado.atendente_atual_id in attendant_ids:
            by_attendant[chamado.atendente_atual_id].append(card)
        else:
            abertos.append(card)

    attendant_columns = [
        {
            "attendant_id": user.id,
            "name": _attendant_display(user),
            "username": user.username,
            "tickets": by_attendant[user.id],
            "count": len(by_attendant[user.id]),
        }
        for user in attendants
    ]

    context = {
        "page_title": "Painel de Chamados TI",
        "open_column": {"tickets": abertos, "count": len(abertos)},
        "attendant_columns": attendant_columns,
        "closed_column": {"tickets": fechados, "count": len(fechados)},
        "is_admin": is_admin_user(request.user),
        "is_attendant": is_attendant_user(request.user),
        "can_view_history": True,
    }
    return render(request, "chamados/dashboard_atendente.html", context)


@login_required
@require_POST
def move_ticket_view(request):
    if not (is_admin_user(request.user) or is_attendant_user(request.user)):
        return _json_error("Voce nao tem permissao para movimentar chamados.", status=403)

    payload = _load_request_payload(request)
    if payload is None:
        return _json_error("Nao foi possivel ler os dados enviados.")

    ticket_number = (payload.get("ticket_number") or "").strip()
    target = (payload.get("target") or "").strip()

    if not ticket_number:
        return _json_error("Informe o chamado a movimentar.")
    if target not in {"aberto", "atendente", "fechado"}:
        return _json_error("Coluna de destino invalida.")

    chamado = Chamado.objects.select_related("atendente_atual").filter(numero=ticket_number).first()
    if not chamado:
        return _json_error("Chamado nao encontrado.", status=404)

    autor = _attendant_display(request.user)
    previous_status_label = chamado.status_label
    previous_attendant = chamado.atendente_atual
    previous_attendant_id = chamado.atendente_atual_id
    previous_closed = chamado.status in Chamado.STATUS_ENCERRADOS

    novo_atendente = None
    if target == "atendente":
        try:
            attendant_id = int(payload.get("attendant_id"))
        except (TypeError, ValueError):
            return _json_error("Atendente de destino invalido.")

        User = get_user_model()
        novo_atendente = (
            User.objects.filter(pk=attendant_id, groups__name=ATTENDANT_GROUP_NAME).first()
        )
        if not novo_atendente:
            return _json_error("O atendente de destino nao pertence ao perfil Atendente TI.", status=400)
        new_status = Chamado.STATUS_EM_ATENDIMENTO
    elif target == "aberto":
        new_status = Chamado.STATUS_ABERTO
    else:  # fechado
        new_status = Chamado.STATUS_FECHADO
        novo_atendente = request.user  # registra quem fechou como atendente atual

    status_changed = chamado.status != new_status
    attendant_changed = previous_attendant_id != (novo_atendente.id if novo_atendente else None)

    chamado.status = new_status
    chamado.atendente_atual = novo_atendente
    update_fields = ["status", "atendente_atual", "atualizado_em"]

    if new_status in Chamado.STATUS_ENCERRADOS and not chamado.fechado_em:
        chamado.fechado_em = timezone.now()
        update_fields.append("fechado_em")
    elif new_status not in Chamado.STATUS_ENCERRADOS and chamado.fechado_em:
        chamado.fechado_em = None
        update_fields.append("fechado_em")

    with transaction.atomic():
        chamado.save(update_fields=update_fields)

        if status_changed:
            ChamadoEvento.registrar(
                chamado=chamado,
                usuario=request.user,
                tipo=ChamadoEvento.TIPO_STATUS,
                descricao=f"Status alterado de {previous_status_label} para {chamado.status_label} por {autor}.",
            )

        if target == "atendente" and attendant_changed:
            destino = _attendant_display(novo_atendente)
            if previous_attendant is None:
                if novo_atendente.id == request.user.id:
                    descricao = f"Chamado puxado para atendimento por {autor}."
                else:
                    descricao = f"Chamado atribuido a {destino} por {autor}."
            else:
                descricao = (
                    f"Atendente alterado de {_attendant_display(previous_attendant)} para {destino} por {autor}."
                )
            ChamadoEvento.registrar(
                chamado=chamado,
                usuario=request.user,
                tipo=ChamadoEvento.TIPO_ATENDENTE,
                descricao=descricao,
            )
        elif target == "aberto" and previous_attendant is not None:
            ChamadoEvento.registrar(
                chamado=chamado,
                usuario=request.user,
                tipo=ChamadoEvento.TIPO_ATENDENTE,
                descricao=f"Atendente atual removido por {autor}; chamado devolvido para a fila de abertos.",
            )
        elif target == "fechado" and not previous_closed:
            ChamadoEvento.registrar(
                chamado=chamado,
                usuario=request.user,
                tipo=ChamadoEvento.TIPO_ATENDENTE,
                descricao=f"Chamado fechado por {autor}.",
            )

    return JsonResponse(
        {
            "ok": True,
            "message": f"Chamado {ticket_number} movido para {chamado.status_label}.",
            "ticket_number": ticket_number,
            "status": chamado.status,
            "status_label": chamado.status_label,
            "status_class": _STATUS_BADGE_CLASS.get(chamado.status, "status-muted"),
            "atendente_atual": _attendant_display(chamado.atendente_atual),
            "atendente_atual_id": chamado.atendente_atual_id,
        }
    )


@login_required
@require_POST
def create_ticket_kanban_view(request):
    if not (is_admin_user(request.user) or is_attendant_user(request.user)):
        return _json_error("Voce nao tem permissao para criar chamados pelo Kanban.", status=403)

    form = AberturaChamadoForm(request.POST, request.FILES)
    if not form.is_valid():
        first_errors = next(iter(form.errors.values()), None)
        message = first_errors[0] if first_errors else "Nao foi possivel validar o chamado."
        return _json_error(message)

    autor = _attendant_display(request.user)
    chamado = form.save(commit=False)
    chamado.solicitante = request.user
    chamado.solicitante_nome = autor
    chamado.solicitante_email = request.user.email or ""
    chamado.status = Chamado.STATUS_ABERTO
    chamado.atendente_atual = None
    chamado.origem = "Kanban TI"
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
                ChamadoEvento.registrar(
                    chamado=chamado,
                    usuario=request.user,
                    tipo=ChamadoEvento.TIPO_CRIACAO,
                    descricao=f"Chamado criado manualmente pelo atendente {autor}.",
                )
            break
        except IntegrityError:
            continue
    else:
        return _json_error("Nao foi possivel gerar o numero do chamado. Tente novamente.")

    active_attendance = (
        AtendimentoHistorico.objects.select_related("chamado")
        .filter(atendente=request.user, finalizado_em__isnull=True)
        .first()
    )
    card = _serialize_kanban_card(chamado, _serialize_attendance_state(active_attendance))
    card_html = render_to_string("partials/kanban_card.html", {"ticket": card}, request=request)

    return JsonResponse(
        {
            "ok": True,
            "message": f"Chamado {chamado.numero} criado com sucesso.",
            "ticket_number": chamado.numero,
            "card_html": card_html,
        }
    )


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
                    autor = request.user.get_full_name() or request.user.username
                    ChamadoEvento.registrar(
                        chamado=chamado,
                        usuario=request.user,
                        tipo=ChamadoEvento.TIPO_CRIACAO,
                        descricao=f"Chamado aberto por {autor}.",
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


def _serialize_ticket_events(chamado: Chamado):
    tipo_labels = dict(ChamadoEvento.TIPO_CHOICES)
    eventos = []
    for evento in chamado.eventos.select_related("usuario").all():
        eventos.append(
            {
                "author": _attendant_display(evento.usuario) or "Sistema",
                "tipo_label": tipo_labels.get(evento.tipo, evento.tipo),
                "descricao": evento.descricao,
                "timestamp": timezone.localtime(evento.criado_em).strftime("%d/%m/%Y %H:%M"),
            }
        )
    return eventos


def _user_can_access_ticket(user, chamado) -> bool:
    if is_admin_user(user) or is_attendant_user(user):
        return True
    return chamado.solicitante_id == user.id


@login_required
def ticket_detail_view(request, numero: str):
    chamado = get_object_or_404(
        Chamado.objects.select_related("solicitante", "atendente_atual"), numero=numero
    )

    if not _user_can_access_ticket(request.user, chamado):
        messages.error(request, "Voce nao tem acesso a este chamado.")
        return redirect("my_tickets")

    pode_ver_todos = is_admin_user(request.user) or is_attendant_user(request.user)
    context = {
        "page_title": f"Chamado {chamado.numero}",
        "chamado": chamado,
        "status_label": chamado.status_label,
        "status_class": _STATUS_BADGE_CLASS.get(chamado.status, "status-muted"),
        "priority_label": chamado.prioridade_label,
        "priority_class": _PRIORIDADE_BADGE_CLASS.get(chamado.prioridade, "priority-medium"),
        "current_attendant": _attendant_display(chamado.atendente_atual),
        "timeline": _serialize_ticket_timeline(chamado),
        "eventos": _serialize_ticket_events(chamado),
        "anexos": list(chamado.anexos.select_related("enviado_por").all()),
        "is_owner": chamado.solicitante_id == request.user.id,
        "is_admin": is_admin_user(request.user),
        "is_attendant": is_attendant_user(request.user),
        "can_view_history": pode_ver_todos,
    }
    return render(request, "chamados/detalhe_chamado.html", context)


@login_required
def download_anexo_view(request, numero: str, anexo_id: int):
    chamado = get_object_or_404(Chamado, numero=numero)

    if not _user_can_access_ticket(request.user, chamado):
        raise Http404("Anexo nao encontrado.")

    anexo = get_object_or_404(ChamadoAnexo, pk=anexo_id, chamado=chamado)
    try:
        return FileResponse(anexo.arquivo.open("rb"), as_attachment=True, filename=anexo.nome_original or anexo.arquivo.name)
    except FileNotFoundError:
        raise Http404("Arquivo nao encontrado no armazenamento.")


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
