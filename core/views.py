from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps
import json

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import FileResponse, Http404, JsonResponse
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import AberturaChamadoForm, LoginForm, MensagemChamadoForm
from .models import (
    AssinaturaResponsavelTI,
    AtendimentoHistorico,
    Chamado,
    ChamadoAnexo,
    ChamadoEvento,
    ChamadoMensagem,
    ChamadoMensagemAnexo,
    DocumentoTI,
    DocumentoTIAnexo,
    EmprestimoTI,
    EquipamentoEmprestimoTI,
    FotoEquipamentoEmprestimoTI,
    InsumoTI,
    LogUsoAssinaturaTI,
    OrcamentoContrato,
    OrcamentoDocumento,
    PendenciaTI,
    RequisicaoContrato,
    RetiradaInsumoTI,
    SuborcamentoContrato,
    SuborcamentoDocumento,
)
from .termo_pdf import gerar_termo_pdf_bytes
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

    pendencias = list(
        PendenciaTI.objects.filter(convertido_em_chamado=False).select_related("criado_por")
    )

    context = {
        "page_title": "Painel de Chamados TI",
        "open_column": {"tickets": abertos, "count": len(abertos)},
        "pendencia_column": {"pendencias": pendencias, "count": len(pendencias)},
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
    # O fechamento nao acontece mais por drag: a coluna "Chamados fechados" so
    # recebe chamados via acao Stop (encerramento de atendimento).
    if target == "fechado":
        return _json_error(
            "Para fechar o chamado, inicie o atendimento e finalize usando o botao Stop.",
            status=409,
        )
    if target not in {"aberto", "atendente"}:
        return _json_error("Coluna de destino invalida.")

    chamado = Chamado.objects.select_related("atendente_atual").filter(numero=ticket_number).first()
    if not chamado:
        return _json_error("Chamado nao encontrado.", status=404)

    autor = _attendant_display(request.user)
    previous_status_label = chamado.status_label
    previous_attendant = chamado.atendente_atual
    previous_attendant_id = chamado.atendente_atual_id

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
    else:  # aberto (unico destino restante; fechado ja foi barrado acima)
        new_status = Chamado.STATUS_ABERTO

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


def _render_pendencia_card(request, pendencia: PendenciaTI) -> str:
    return render_to_string("partials/pendencia_card.html", {"p": pendencia}, request=request)


@login_required
@require_POST
def pendencia_create_view(request):
    if not (is_admin_user(request.user) or is_attendant_user(request.user)):
        return _json_error("Voce nao tem permissao para criar pendencias.", status=403)

    payload = _load_request_payload(request)
    if payload is None:
        return _json_error("Nao foi possivel ler os dados enviados.")

    titulo = (payload.get("titulo") or "").strip()
    descricao = (payload.get("descricao") or "").strip()

    if len(titulo) < 3:
        return _json_error("Informe um titulo com pelo menos 3 caracteres.")
    if not descricao:
        return _json_error("Descreva a pendencia.")

    pendencia = PendenciaTI.objects.create(
        titulo=titulo,
        descricao=descricao,
        criado_por=request.user,
    )

    return JsonResponse(
        {
            "ok": True,
            "message": "Pendencia criada com sucesso.",
            "pendencia_id": pendencia.id,
            "card_html": _render_pendencia_card(request, pendencia),
        }
    )


@login_required
def pendencia_detail_view(request, pendencia_id: int):
    if not (is_admin_user(request.user) or is_attendant_user(request.user)):
        return _json_error("Voce nao tem permissao para ver pendencias.", status=403)

    pendencia = get_object_or_404(PendenciaTI, pk=pendencia_id)
    return JsonResponse(
        {
            "ok": True,
            "titulo": pendencia.titulo,
            "descricao": pendencia.descricao,
            "criado_em": timezone.localtime(pendencia.criado_em).strftime("%d/%m/%Y %H:%M"),
            "criado_por": _attendant_display(pendencia.criado_por) or "Usuario removido",
        }
    )


@login_required
@require_POST
def pendencia_convert_view(request, pendencia_id: int):
    if not (is_admin_user(request.user) or is_attendant_user(request.user)):
        return _json_error("Voce nao tem permissao para converter pendencias.", status=403)

    payload = _load_request_payload(request)
    if payload is None:
        return _json_error("Nao foi possivel ler os dados enviados.")

    try:
        attendant_id = int(payload.get("attendant_id"))
    except (TypeError, ValueError):
        return _json_error("Atendente de destino invalido.")

    User = get_user_model()
    attendant = User.objects.filter(pk=attendant_id, groups__name=ATTENDANT_GROUP_NAME).first()
    if not attendant:
        return _json_error("O atendente de destino nao pertence ao perfil Atendente TI.", status=400)

    pendencia = get_object_or_404(PendenciaTI, pk=pendencia_id)
    if pendencia.convertido_em_chamado:
        return _json_error("Esta pendencia ja foi convertida em chamado.", status=409)

    autor = _attendant_display(request.user)
    destino = _attendant_display(attendant)
    solicitante = pendencia.criado_por

    chamado = Chamado(
        titulo=pendencia.titulo,
        descricao=pendencia.descricao,
        solicitante=solicitante,
        solicitante_nome=_attendant_display(solicitante),
        solicitante_email=(getattr(solicitante, "email", "") or ""),
        status=Chamado.STATUS_EM_ATENDIMENTO,
        atendente_atual=attendant,
        origem="Pendencia TI",
    )

    for _attempt in range(3):
        chamado.numero = Chamado.gerar_numero()
        try:
            with transaction.atomic():
                chamado.save()
                pendencia.convertido_em_chamado = True
                pendencia.chamado_gerado = chamado
                pendencia.convertido_por = request.user
                pendencia.convertido_em = timezone.now()
                pendencia.save(
                    update_fields=[
                        "convertido_em_chamado",
                        "chamado_gerado",
                        "convertido_por",
                        "convertido_em",
                    ]
                )
                ChamadoEvento.registrar(
                    chamado=chamado,
                    usuario=request.user,
                    tipo=ChamadoEvento.TIPO_CRIACAO,
                    descricao=f"Chamado criado a partir da pendencia #{pendencia.id} por {autor}.",
                )
                ChamadoEvento.registrar(
                    chamado=chamado,
                    usuario=request.user,
                    tipo=ChamadoEvento.TIPO_ATENDENTE,
                    descricao=f"Pendencia atribuida para atendimento de {destino} por {autor}.",
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
            "message": f"Pendencia convertida no chamado {chamado.numero}.",
            "pendencia_id": pendencia.id,
            "chamado_id": chamado.id,
            "ticket_number": chamado.numero,
            "titulo": chamado.titulo,
            "status": chamado.status,
            "status_label": chamado.status_label,
            "status_class": _STATUS_BADGE_CLASS.get(chamado.status, "status-muted"),
            "atendente_atual": _attendant_display(chamado.atendente_atual),
            "atendente_atual_id": chamado.atendente_atual_id,
            "card_html": card_html,
        }
    )


def _is_ticket_in_attendant_column(chamado: Chamado) -> bool:
    """True quando o chamado esta em uma coluna de atendente no Kanban.

    Espelha a regra de montagem do quadro (`tickets_dashboard_view`): o chamado
    nao pode estar encerrado e o `atendente_atual` precisa pertencer ao grupo
    `Atendente TI`. Chamados em "Chamados abertos" (sem atendente) e em
    "Chamados fechados" (encerrados) ficam de fora.
    """
    if chamado.status in Chamado.STATUS_ENCERRADOS:
        return False
    if chamado.atendente_atual_id is None:
        return False
    return (
        get_user_model()
        .objects.filter(pk=chamado.atendente_atual_id, groups__name=ATTENDANT_GROUP_NAME)
        .exists()
    )


@login_required
@require_POST
def start_attendance_view(request):
    if not (is_admin_user(request.user) or is_attendant_user(request.user)):
        return _json_error("Voce nao tem permissao para iniciar atendimentos.", status=403)

    payload = _load_request_payload(request)
    if payload is None:
        return _json_error("Nao foi possivel ler os dados enviados.")

    ticket_number = (payload.get("ticket_number") or "").strip()
    if not ticket_number:
        return _json_error("Informe o chamado que deve iniciar atendimento.")

    chamado = Chamado.objects.select_related("atendente_atual").filter(numero=ticket_number).first()
    if not chamado:
        return _json_error("Chamado nao encontrado para iniciar atendimento.", status=404)

    # Play so vale para chamados em uma coluna de atendente: bloqueia chamados
    # em "Chamados abertos" (sem atendente) e em "Chamados fechados" (encerrados),
    # mesmo que a chamada venha direto pelo endpoint.
    if chamado.status in Chamado.STATUS_ENCERRADOS:
        return _json_error("Nao e possivel iniciar atendimento de um chamado encerrado.", status=409)
    if not _is_ticket_in_attendant_column(chamado):
        return _json_error(
            "Arraste o chamado para uma coluna de atendente antes de iniciar o atendimento.",
            status=409,
        )

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


def _close_chamado_on_stop(chamado: Chamado, user, descricao_atividade: str = "") -> bool:
    """Fecha o chamado ao finalizar o atendimento (Stop) e registra o historico.

    Idempotente: se o chamado ja estiver encerrado, nao duplica eventos.
    O fechamento define status Fechado, `fechado_em` e atendente atual = quem
    executou a acao (Stop e o unico caminho de fechamento). O registro tecnico
    guarda a mudanca de status e um evento de encerramento com quem finalizou e o
    texto de "O que foi feito"; esse texto e historico tecnico, separado da
    conversa do usuario (`ChamadoMensagem`).
    """
    autor = _attendant_display(user)
    previous_status_label = chamado.status_label
    previous_closed = chamado.status in Chamado.STATUS_ENCERRADOS
    status_changed = chamado.status != Chamado.STATUS_FECHADO

    chamado.status = Chamado.STATUS_FECHADO
    chamado.atendente_atual = user
    update_fields = ["status", "atendente_atual", "atualizado_em"]
    if not chamado.fechado_em:
        chamado.fechado_em = timezone.now()
        update_fields.append("fechado_em")
    chamado.save(update_fields=update_fields)

    if status_changed:
        ChamadoEvento.registrar(
            chamado=chamado,
            usuario=user,
            tipo=ChamadoEvento.TIPO_STATUS,
            descricao=f"Status alterado de {previous_status_label} para {chamado.status_label} por {autor}.",
        )
    if not previous_closed:
        texto = f"Chamado finalizado por {autor}."
        if descricao_atividade:
            texto += f" O que foi feito: {descricao_atividade}"
        ChamadoEvento.registrar(
            chamado=chamado,
            usuario=user,
            tipo=ChamadoEvento.TIPO_ATENDENTE,
            descricao=texto,
        )
    return True


@login_required
@require_POST
def finish_attendance_view(request):
    if not (is_admin_user(request.user) or is_attendant_user(request.user)):
        return _json_error("Voce nao tem permissao para encerrar chamados.", status=403)

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

    ticket_closed = False
    try:
        with transaction.atomic():
            attendance.finalizar(tipo_encerramento=action, descricao_atividade=description)
            attendance.save()
            if action == AtendimentoHistorico.TIPO_ENCERRAMENTO_STOP:
                ticket_closed = _close_chamado_on_stop(attendance.chamado, request.user, description)
    except ValidationError as exc:
        message = exc.messages[0] if exc.messages else "Nao foi possivel encerrar o atendimento."
        return _json_error(message)

    chamado = attendance.chamado
    duration_display = _format_duration(attendance.duracao)
    action_label = "pausado" if action == AtendimentoHistorico.TIPO_ENCERRAMENTO_PAUSE else "finalizado"

    response = {
        "ok": True,
        "message": f"Atendimento {action_label} no chamado {ticket_number}.",
        "ticket_number": ticket_number,
        "action": action,
        "duration_display": duration_display,
        "ticket_closed": ticket_closed,
        "history_entry": {
            "author": request.user.get_full_name() or request.user.username,
            "timestamp": timezone.localtime(attendance.finalizado_em).strftime("%d/%m/%Y %H:%M"),
            "message": description,
            "kind": "comment",
        },
    }

    if ticket_closed:
        response["message"] = f"Chamado {ticket_number} encerrado e movido para {chamado.status_label}."
        response["status"] = chamado.status
        response["status_label"] = chamado.status_label
        response["status_class"] = _STATUS_BADGE_CLASS.get(chamado.status, "status-muted")
        response["atendente_atual"] = _attendant_display(chamado.atendente_atual)
        response["atendente_atual_id"] = chamado.atendente_atual_id

    return JsonResponse(response)


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


def _serialize_ticket_messages(chamado: Chamado):
    """Serializa a conversa do chamado para o template.

    A origem da mensagem (solicitante x TI) e definida comparando o autor com o
    solicitante do chamado, o que e estavel mesmo que os grupos mudem depois.
    """
    mensagens = []
    for mensagem in chamado.mensagens.select_related("autor").prefetch_related("anexos"):
        from_requester = (
            mensagem.autor_id is not None and mensagem.autor_id == chamado.solicitante_id
        )
        mensagens.append(
            {
                "id": mensagem.id,
                "author": _attendant_display(mensagem.autor) or "Usuario removido",
                "from_requester": from_requester,
                "origin_label": "Solicitante" if from_requester else "Equipe de TI",
                "texto": mensagem.texto,
                "timestamp": timezone.localtime(mensagem.criado_em).strftime("%d/%m/%Y %H:%M"),
                "anexos": list(mensagem.anexos.all()),
            }
        )
    return mensagens


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
        "eventos_total": chamado.eventos.count(),
        "mensagens": _serialize_ticket_messages(chamado),
        "mensagem_form": MensagemChamadoForm(),
        "anexos": list(chamado.anexos.select_related("enviado_por").all()),
        "is_owner": chamado.solicitante_id == request.user.id,
        "is_admin": is_admin_user(request.user),
        "is_attendant": is_attendant_user(request.user),
        "can_view_history": pode_ver_todos,
    }
    return render(request, "chamados/detalhe_chamado.html", context)


_CLOSED_TICKETS_LIMIT = 100


def _serialize_closed_ticket_messages(chamado: Chamado):
    """Serializa a conversa de um chamado fechado para JSON (modal do Kanban)."""
    mensagens = []
    for mensagem in chamado.mensagens.select_related("autor").prefetch_related("anexos"):
        from_requester = (
            mensagem.autor_id is not None and mensagem.autor_id == chamado.solicitante_id
        )
        anexos = [
            {
                "nome": anexo.nome_original or anexo.arquivo.name,
                "url": reverse("download_message_anexo", args=[chamado.numero, anexo.id]),
            }
            for anexo in mensagem.anexos.all()
        ]
        mensagens.append(
            {
                "author": _attendant_display(mensagem.autor) or "Usuario removido",
                "from_requester": from_requester,
                "origin_label": "Solicitante" if from_requester else "Equipe de TI",
                "texto": mensagem.texto,
                "timestamp": timezone.localtime(mensagem.criado_em).strftime("%d/%m/%Y %H:%M"),
                "anexos": anexos,
            }
        )
    return mensagens


@login_required
def closed_tickets_search_view(request):
    """Lista/pesquisa chamados encerrados (resolvido/fechado) para o modal do Kanban.

    Sem `q` retorna os encerrados mais recentes (limitados). Com `q` filtra por
    numero, titulo, descricao, solicitante, atendente atual, mensagens e historico.
    Restrito a Atendente TI/Admin; usuario comum recebe 403.
    """
    if not (is_admin_user(request.user) or is_attendant_user(request.user)):
        return _json_error("Voce nao tem permissao para acessar chamados fechados.", status=403)

    query = (request.GET.get("q") or "").strip()
    queryset = (
        Chamado.objects.filter(status__in=Chamado.STATUS_ENCERRADOS)
        .order_by("-fechado_em", "-criado_em")
    )

    if query:
        filters = (
            Q(numero__icontains=query)
            | Q(titulo__icontains=query)
            | Q(descricao__icontains=query)
            | Q(solicitante_nome__icontains=query)
            | Q(solicitante__username__icontains=query)
            | Q(solicitante__first_name__icontains=query)
            | Q(solicitante__last_name__icontains=query)
            | Q(atendente_atual__username__icontains=query)
            | Q(atendente_atual__first_name__icontains=query)
            | Q(atendente_atual__last_name__icontains=query)
            | Q(mensagens__texto__icontains=query)
            | Q(eventos__descricao__icontains=query)
        )
        queryset = queryset.filter(filters).distinct()

    items = list(queryset[:_CLOSED_TICKETS_LIMIT])
    return JsonResponse(
        {
            "ok": True,
            "count": len(items),
            "results": [{"number": chamado.numero, "title": chamado.titulo} for chamado in items],
        }
    )


@login_required
def closed_ticket_detail_view(request, numero: str):
    """Detalhe completo de um chamado encerrado para o modal do Kanban.

    Restrito a Atendente TI/Admin; usuario comum recebe 403. Apenas chamados
    encerrados (resolvido/fechado) sao expostos por este endpoint.
    """
    if not (is_admin_user(request.user) or is_attendant_user(request.user)):
        return _json_error("Voce nao tem permissao para acessar chamados fechados.", status=403)

    chamado = (
        Chamado.objects.select_related("solicitante", "atendente_atual")
        .filter(numero=numero)
        .first()
    )
    if not chamado or chamado.status not in Chamado.STATUS_ENCERRADOS:
        return _json_error("Chamado fechado nao encontrado.", status=404)

    attachments = [
        {
            "nome": anexo.nome_original or anexo.arquivo.name,
            "url": reverse("download_anexo", args=[chamado.numero, anexo.id]),
        }
        for anexo in chamado.anexos.select_related("enviado_por").all()
    ]

    return JsonResponse(
        {
            "ok": True,
            "number": chamado.numero,
            "title": chamado.titulo,
            "description": chamado.descricao or "",
            "requester": _requester_display(chamado),
            "current_attendant": _attendant_display(chamado.atendente_atual) or "-",
            "status_label": chamado.status_label,
            "status_class": _STATUS_BADGE_CLASS.get(chamado.status, "status-muted"),
            "created_at": timezone.localtime(chamado.criado_em).strftime("%d/%m/%Y %H:%M"),
            "closed_at": (
                timezone.localtime(chamado.fechado_em).strftime("%d/%m/%Y %H:%M")
                if chamado.fechado_em
                else ""
            ),
            "attachments": attachments,
            "messages": _serialize_closed_ticket_messages(chamado),
            "events": _serialize_ticket_events(chamado),
        }
    )


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


@login_required
@require_POST
def ticket_message_create_view(request, numero: str):
    """Registra uma mensagem da conversa do chamado (com anexos opcionais).

    Mantem o usuario no detalhe do chamado apos o envio e grava apenas um resumo
    no historico tecnico, sem duplicar o conteudo da conversa.
    """
    chamado = get_object_or_404(Chamado, numero=numero)

    if not _user_can_access_ticket(request.user, chamado):
        messages.error(request, "Voce nao tem acesso a este chamado.")
        return redirect("my_tickets")

    form = MensagemChamadoForm(request.POST, request.FILES)
    if not form.is_valid():
        erro = next(iter(form.errors.values()))[0] if form.errors else "Nao foi possivel enviar a mensagem."
        messages.error(request, erro)
        return redirect("ticket_detail", numero=chamado.numero)

    texto = form.cleaned_data["texto"]
    anexos = form.cleaned_data.get("anexos") or []

    with transaction.atomic():
        mensagem = ChamadoMensagem.objects.create(
            chamado=chamado,
            autor=request.user,
            texto=texto,
        )
        for arquivo in anexos:
            ChamadoMensagemAnexo.objects.create(
                mensagem=mensagem,
                arquivo=arquivo,
                nome_original=arquivo.name,
            )

        autor = request.user.get_full_name() or request.user.username
        eh_solicitante = chamado.solicitante_id == request.user.id
        quem = f"pelo solicitante {autor}" if eh_solicitante else f"por {autor}"
        if anexos:
            resumo = f"Mensagem enviada com {len(anexos)} anexo(s) {quem}."
        else:
            resumo = f"Mensagem enviada {quem}."
        ChamadoEvento.registrar(
            chamado=chamado,
            usuario=request.user,
            tipo=ChamadoEvento.TIPO_COMENTARIO,
            descricao=resumo,
        )

    messages.success(request, "Mensagem enviada com sucesso.")
    return redirect("ticket_detail", numero=chamado.numero)


@login_required
def download_message_anexo_view(request, numero: str, anexo_id: int):
    chamado = get_object_or_404(Chamado, numero=numero)

    if not _user_can_access_ticket(request.user, chamado):
        raise Http404("Anexo nao encontrado.")

    anexo = get_object_or_404(ChamadoMensagemAnexo, pk=anexo_id, mensagem__chamado=chamado)
    try:
        return FileResponse(
            anexo.arquivo.open("rb"),
            as_attachment=True,
            filename=anexo.nome_original or anexo.arquivo.name,
        )
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


# ==========================================================================
# Modulo Contratos
# ==========================================================================


def _is_ti(user) -> bool:
    return is_admin_user(user) or is_attendant_user(user)


def _parse_money_field(raw, label: str) -> Decimal:
    """Converte um valor monetario do formulario, bloqueando negativos."""
    texto = (raw or "").strip().replace(" ", "")
    if texto == "":
        return Decimal("0.00")
    texto = texto.replace(".", "").replace(",", ".") if ("," in texto and "." in texto) else texto.replace(",", ".")
    try:
        valor = Decimal(texto)
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} invalido.")
    if valor < 0:
        raise ValueError(f"{label} nao pode ser negativo.")
    return valor.quantize(Decimal("0.01"))


def _parse_item_fields(post):
    """Valida e normaliza os campos comuns de orcamento/suborcamento.

    Retorna um dict de campos limpos ou levanta ValueError com mensagem amigavel.
    """
    titulo = (post.get("titulo") or "").strip()
    if len(titulo) < 2:
        raise ValueError("Informe um titulo com pelo menos 2 caracteres.")

    moeda = (post.get("moeda") or "").strip().upper()
    if moeda not in {OrcamentoContrato.MOEDA_BRL, OrcamentoContrato.MOEDA_USD}:
        raise ValueError("Moeda invalida. Use Real (BRL) ou Dolar (USD).")

    try:
        quantidade = int((post.get("quantidade") or "1").strip() or "1")
    except (TypeError, ValueError):
        raise ValueError("Quantidade invalida.")
    if quantidade < 1:
        raise ValueError("A quantidade deve ser pelo menos 1.")

    return {
        "titulo": titulo,
        "loja": (post.get("loja") or "").strip(),
        "moeda": moeda,
        "valor": _parse_money_field(post.get("valor"), "Valor"),
        "quantidade": quantidade,
        "frete": _parse_money_field(post.get("frete"), "Frete"),
        "desconto": _parse_money_field(post.get("desconto"), "Desconto"),
        "link": (post.get("link") or "").strip(),
    }


def _fmt_money(value, moeda: str) -> str:
    symbol = "R$" if moeda == OrcamentoContrato.MOEDA_BRL else "US$"
    quant = Decimal(value or 0).quantize(Decimal("0.01"))
    texto = f"{quant:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{symbol} {texto}"


def _serialize_orcamento_documento(doc: OrcamentoDocumento):
    return {"nome": doc.nome_original or doc.arquivo.name, "url": reverse("contrato_orcamento_documento", args=[doc.id])}


def _serialize_suborcamento_documento(doc: SuborcamentoDocumento):
    return {"nome": doc.nome_original or doc.arquivo.name, "url": reverse("contrato_suborcamento_documento", args=[doc.id])}


def _serialize_suborcamento(sub: SuborcamentoContrato):
    return {
        "id": sub.id,
        "titulo": sub.titulo,
        "loja": sub.loja or "-",
        "moeda": sub.moeda,
        "valor": f"{sub.valor:.2f}",
        "quantidade": sub.quantidade,
        "frete": f"{sub.frete:.2f}",
        "desconto": f"{sub.desconto:.2f}",
        "link": sub.link,
        "subtotal_display": _fmt_money(sub.subtotal, sub.moeda),
        "total_display": _fmt_money(sub.total, sub.moeda),
        "foto_url": reverse("contrato_suborcamento_foto", args=[sub.id]) if sub.foto_produto else "",
        "documentos": [_serialize_suborcamento_documento(d) for d in sub.documentos.all()],
    }


def _serialize_orcamento(orc: OrcamentoContrato):
    suborcamentos = list(orc.suborcamentos.all())
    total_com_sub = orc.total + sum((s.total for s in suborcamentos), Decimal("0"))
    return {
        "id": orc.id,
        "titulo": orc.titulo,
        "loja": orc.loja or "-",
        "moeda": orc.moeda,
        "valor": f"{orc.valor:.2f}",
        "quantidade": orc.quantidade,
        "frete": f"{orc.frete:.2f}",
        "desconto": f"{orc.desconto:.2f}",
        "link": orc.link,
        "subtotal_display": _fmt_money(orc.subtotal, orc.moeda),
        "total_display": _fmt_money(orc.total, orc.moeda),
        "total_com_suborcamentos_display": _fmt_money(total_com_sub, orc.moeda),
        "foto_url": reverse("contrato_orcamento_foto", args=[orc.id]) if orc.foto_produto else "",
        "documentos": [_serialize_orcamento_documento(d) for d in orc.documentos.all()],
        "suborcamentos": [_serialize_suborcamento(s) for s in suborcamentos],
    }


@ti_required
def contratos_dashboard_view(request):
    requisicoes = list(RequisicaoContrato.objects.select_related("criado_por").all())
    rows = [
        {
            "id": req.id,
            "titulo": req.titulo,
            "status": req.status,
            "status_label": req.status_label,
        }
        for req in requisicoes
    ]
    context = {
        "page_title": "Requisicoes",
        "requisicoes": rows,
        "requisicoes_total": len(rows),
        "is_admin": is_admin_user(request.user),
        "is_attendant": is_attendant_user(request.user),
        "can_view_history": True,
    }
    return render(request, "chamados/contratos.html", context)


@login_required
@require_POST
def requisicao_create_view(request):
    if not _is_ti(request.user):
        return _json_error("Voce nao tem permissao para acessar o modulo Contratos.", status=403)

    payload = _load_request_payload(request) or {}
    titulo = (payload.get("titulo") or "").strip()
    tipo = (payload.get("tipo") or "").strip().lower()
    texto = (payload.get("texto") or "").strip()

    if len(titulo) < 3:
        return _json_error("Informe um titulo com pelo menos 3 caracteres.")
    if tipo not in {RequisicaoContrato.TIPO_FISICA, RequisicaoContrato.TIPO_DIGITAL}:
        return _json_error("Selecione o tipo da requisicao (Fisica ou Digital).")

    requisicao = RequisicaoContrato.objects.create(
        titulo=titulo,
        tipo=tipo,
        texto=texto,
        status=RequisicaoContrato.STATUS_ABERTA,
        criado_por=request.user,
    )
    return JsonResponse(
        {
            "ok": True,
            "message": "Requisicao criada com sucesso.",
            "requisicao": {
                "id": requisicao.id,
                "titulo": requisicao.titulo,
                "status": requisicao.status,
                "status_label": requisicao.status_label,
            },
        }
    )


@login_required
def requisicao_detail_view(request, requisicao_id: int):
    if not _is_ti(request.user):
        return _json_error("Voce nao tem permissao para acessar o modulo Contratos.", status=403)

    requisicao = (
        RequisicaoContrato.objects.select_related("criado_por")
        .filter(pk=requisicao_id)
        .first()
    )
    if not requisicao:
        return _json_error("Requisicao nao encontrada.", status=404)

    orcamentos = (
        requisicao.orcamentos.prefetch_related("suborcamentos", "documentos", "suborcamentos__documentos")
    )
    return JsonResponse(
        {
            "ok": True,
            "requisicao": {
                "id": requisicao.id,
                "titulo": requisicao.titulo,
                "tipo": requisicao.tipo,
                "tipo_label": requisicao.tipo_label,
                "texto": requisicao.texto,
                "status": requisicao.status,
                "status_label": requisicao.status_label,
                "criado_por": _attendant_display(requisicao.criado_por) or "-",
                "criado_em": timezone.localtime(requisicao.criado_em).strftime("%d/%m/%Y %H:%M"),
            },
            "orcamentos": [_serialize_orcamento(orc) for orc in orcamentos],
        }
    )


@login_required
@require_POST
def requisicao_delete_view(request, requisicao_id: int):
    """Exclui uma requisicao e, por cascata, seus orcamentos, suborcamentos e
    documentos (FKs `on_delete=CASCADE`). Apenas TI/admin; somente via POST/CSRF.

    Observacao: os arquivos fisicos em MEDIA_ROOT nao sao removidos aqui (o
    projeto ainda nao possui rotina de limpeza de arquivos orfaos).
    """
    if not _is_ti(request.user):
        return _json_error("Voce nao tem permissao para excluir requisicoes.", status=403)

    requisicao = RequisicaoContrato.objects.filter(pk=requisicao_id).first()
    if not requisicao:
        return _json_error("Requisicao nao encontrada.", status=404)

    requisicao.delete()
    return JsonResponse(
        {
            "ok": True,
            "message": "Requisicao excluida com sucesso.",
            "requisicao_id": requisicao_id,
        }
    )


def _salvar_documentos(model_cls, fk_name, item, arquivos):
    for arquivo in arquivos:
        model_cls.objects.create(
            **{fk_name: item},
            arquivo=arquivo,
            nome_original=arquivo.name,
        )


@login_required
@require_POST
def orcamento_create_view(request, requisicao_id: int):
    if not _is_ti(request.user):
        return _json_error("Voce nao tem permissao para acessar o modulo Contratos.", status=403)

    requisicao = RequisicaoContrato.objects.filter(pk=requisicao_id).first()
    if not requisicao:
        return _json_error("Requisicao nao encontrada.", status=404)

    try:
        campos = _parse_item_fields(request.POST)
    except ValueError as exc:
        return _json_error(str(exc))

    foto = request.FILES.get("foto_produto")
    documentos = request.FILES.getlist("documentos")

    with transaction.atomic():
        orcamento = OrcamentoContrato.objects.create(
            requisicao=requisicao, criado_por=request.user, **campos
        )
        if foto:
            orcamento.foto_produto = foto
            orcamento.save(update_fields=["foto_produto", "atualizado_em"])
        _salvar_documentos(OrcamentoDocumento, "orcamento", orcamento, documentos)

    return JsonResponse(
        {"ok": True, "message": "Orcamento adicionado com sucesso.", "orcamento_id": orcamento.id}
    )


@login_required
@require_POST
def suborcamento_create_view(request, orcamento_id: int):
    if not _is_ti(request.user):
        return _json_error("Voce nao tem permissao para acessar o modulo Contratos.", status=403)

    orcamento = OrcamentoContrato.objects.filter(pk=orcamento_id).first()
    if not orcamento:
        return _json_error("Orcamento nao encontrado.", status=404)

    try:
        campos = _parse_item_fields(request.POST)
    except ValueError as exc:
        return _json_error(str(exc))

    foto = request.FILES.get("foto_produto")
    documentos = request.FILES.getlist("documentos")

    with transaction.atomic():
        suborcamento = SuborcamentoContrato.objects.create(
            orcamento_pai=orcamento, criado_por=request.user, **campos
        )
        if foto:
            suborcamento.foto_produto = foto
            suborcamento.save(update_fields=["foto_produto", "atualizado_em"])
        _salvar_documentos(SuborcamentoDocumento, "suborcamento", suborcamento, documentos)

    return JsonResponse(
        {
            "ok": True,
            "message": "Suborcamento adicionado com sucesso.",
            "suborcamento_id": suborcamento.id,
            "orcamento_id": orcamento.id,
        }
    )


def _serve_file(field_file, *, as_attachment: bool, filename: str):
    try:
        return FileResponse(field_file.open("rb"), as_attachment=as_attachment, filename=filename)
    except FileNotFoundError:
        raise Http404("Arquivo nao encontrado no armazenamento.")


@login_required
def contrato_orcamento_foto_view(request, orcamento_id: int):
    if not _is_ti(request.user):
        raise Http404("Nao encontrado.")
    orcamento = get_object_or_404(OrcamentoContrato, pk=orcamento_id)
    if not orcamento.foto_produto:
        raise Http404("Sem foto.")
    return _serve_file(orcamento.foto_produto, as_attachment=False, filename=orcamento.foto_produto.name)


@login_required
def contrato_suborcamento_foto_view(request, suborcamento_id: int):
    if not _is_ti(request.user):
        raise Http404("Nao encontrado.")
    sub = get_object_or_404(SuborcamentoContrato, pk=suborcamento_id)
    if not sub.foto_produto:
        raise Http404("Sem foto.")
    return _serve_file(sub.foto_produto, as_attachment=False, filename=sub.foto_produto.name)


@login_required
def contrato_orcamento_documento_view(request, documento_id: int):
    if not _is_ti(request.user):
        raise Http404("Nao encontrado.")
    doc = get_object_or_404(OrcamentoDocumento, pk=documento_id)
    return _serve_file(doc.arquivo, as_attachment=True, filename=doc.nome_original or doc.arquivo.name)


@login_required
def contrato_suborcamento_documento_view(request, documento_id: int):
    if not _is_ti(request.user):
        raise Http404("Nao encontrado.")
    doc = get_object_or_404(SuborcamentoDocumento, pk=documento_id)
    return _serve_file(doc.arquivo, as_attachment=True, filename=doc.nome_original or doc.arquivo.name)


# ==========================================================================
# Modulo Emprestimos
# ==========================================================================


_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _is_image_name(nome: str) -> bool:
    nome = (nome or "").lower()
    return any(nome.endswith(ext) for ext in _IMAGE_EXTS)


def _serialize_assinatura(assinatura: AssinaturaResponsavelTI):
    return {"id": assinatura.id, "nome_responsavel": assinatura.nome_responsavel}


def _serialize_emprestimo_row(emp: EmprestimoTI, equipamentos_count=None):
    count = equipamentos_count if equipamentos_count is not None else emp.equipamentos.count()
    primeiro = emp.equipamentos.first()
    return {
        "id": emp.id,
        "colaborador_nome": emp.colaborador_nome,
        "empresa": emp.empresa or "-",
        "equipamento_principal": primeiro.descricao_completa if primeiro else "-",
        "equipamentos_count": count,
        "data_emprestimo": emp.data_emprestimo.strftime("%d/%m/%Y") if emp.data_emprestimo else "-",
        "devolucao": emp.devolucao_display,
        "status": emp.status,
        "status_label": emp.status_label,
    }


@ti_required
def emprestimos_dashboard_view(request):
    emprestimos = (
        EmprestimoTI.objects.prefetch_related("equipamentos").select_related("assinatura_responsavel")
    )
    rows = [_serialize_emprestimo_row(emp) for emp in emprestimos]
    assinaturas = AssinaturaResponsavelTI.objects.filter(ativo=True)
    context = {
        "page_title": "Emprestimos",
        "emprestimos": rows,
        "assinaturas": [_serialize_assinatura(a) for a in assinaturas],
        "is_admin": is_admin_user(request.user),
        "is_attendant": is_attendant_user(request.user),
        "can_view_history": True,
    }
    return render(request, "chamados/emprestimos.html", context)


@login_required
@require_POST
def assinatura_create_view(request):
    if not _is_ti(request.user):
        return _json_error("Voce nao tem permissao para cadastrar assinaturas.", status=403)

    nome = (request.POST.get("nome_responsavel") or "").strip()
    senha = request.POST.get("senha") or ""
    imagem = request.FILES.get("imagem_assinatura")
    ativo = (request.POST.get("ativo") or "true").lower() not in {"false", "0", "nao", "no"}

    if len(nome) < 2:
        return _json_error("Informe o nome do responsavel.")
    if len(senha) < 4:
        return _json_error("Informe uma senha de autorizacao com pelo menos 4 caracteres.")

    assinatura = AssinaturaResponsavelTI(nome_responsavel=nome, ativo=ativo, criado_por=request.user)
    assinatura.set_senha(senha)
    if imagem:
        assinatura.imagem_assinatura = imagem
    assinatura.save()

    return JsonResponse(
        {
            "ok": True,
            "message": "Assinatura cadastrada com sucesso.",
            "assinatura": _serialize_assinatura(assinatura),
        }
    )


@login_required
def assinaturas_list_view(request):
    if not _is_ti(request.user):
        return _json_error("Voce nao tem permissao para acessar assinaturas.", status=403)
    assinaturas = AssinaturaResponsavelTI.objects.filter(ativo=True)
    return JsonResponse({"ok": True, "assinaturas": [_serialize_assinatura(a) for a in assinaturas]})


def _parse_equipamentos(request):
    """Le os blocos de equipamento enviados no multipart (equip_<i>_*)."""
    try:
        total = int(request.POST.get("equipamentos_count") or "0")
    except (TypeError, ValueError):
        total = 0

    equipamentos = []
    for indice in range(total):
        prefixo = f"equip_{indice}_"
        tipo = (request.POST.get(prefixo + "tipo") or "").strip()
        if not tipo:
            continue  # ignora blocos vazios
        equipamentos.append(
            {
                "tipo_equipamento": tipo,
                "marca": (request.POST.get(prefixo + "marca") or "").strip(),
                "modelo": (request.POST.get(prefixo + "modelo") or "").strip(),
                "numero_serie": (request.POST.get(prefixo + "serie") or "").strip(),
                "patrimonio_etiqueta": (request.POST.get(prefixo + "patrimonio") or "").strip(),
                "acessorios_entregues": (request.POST.get(prefixo + "acessorios") or "").strip(),
                "fotos": request.FILES.getlist(prefixo + "fotos"),
            }
        )
    return equipamentos


@login_required
@require_POST
def emprestimo_create_view(request):
    if not _is_ti(request.user):
        return _json_error("Voce nao tem permissao para criar emprestimos.", status=403)

    colaborador = (request.POST.get("colaborador_nome") or "").strip()
    if len(colaborador) < 2:
        return _json_error("Informe o nome do colaborador.")

    data_emprestimo = parse_date((request.POST.get("data_emprestimo") or "").strip())
    if not data_emprestimo:
        return _json_error("Informe uma data de emprestimo valida.")

    previsao = parse_date((request.POST.get("previsao_devolucao") or "").strip())
    prazo_indeterminado = previsao is None

    equipamentos = _parse_equipamentos(request)
    if not equipamentos:
        return _json_error("Adicione pelo menos um equipamento com o tipo preenchido.")

    # Assinatura (opcional): se selecionada, a senha e obrigatoria e deve conferir.
    assinatura = None
    aplicar_assinatura = False
    assinatura_id = (request.POST.get("assinatura_id") or "").strip()
    if assinatura_id:
        assinatura = AssinaturaResponsavelTI.objects.filter(pk=assinatura_id, ativo=True).first()
        if not assinatura:
            return _json_error("Assinatura selecionada invalida ou inativa.")
        senha = request.POST.get("senha_assinatura") or ""
        if not assinatura.conferir_senha(senha):
            return _json_error("Senha de autorizacao da assinatura incorreta.", status=403)
        aplicar_assinatura = True

    with transaction.atomic():
        emprestimo = EmprestimoTI.objects.create(
            colaborador_nome=colaborador,
            empresa=(request.POST.get("empresa") or "").strip(),
            cpf=(request.POST.get("cpf") or "").strip(),
            email=(request.POST.get("email") or "").strip(),
            telefone=(request.POST.get("telefone") or "").strip(),
            data_emprestimo=data_emprestimo,
            previsao_devolucao=previsao,
            prazo_indeterminado=prazo_indeterminado,
            observacoes_internas=(request.POST.get("observacoes_internas") or "").strip(),
            status=EmprestimoTI.STATUS_AGUARDANDO,
            assinatura_responsavel=assinatura,
            criado_por=request.user,
        )
        for dados in equipamentos:
            fotos = dados.pop("fotos")
            equip = EquipamentoEmprestimoTI.objects.create(emprestimo=emprestimo, **dados)
            for foto in fotos:
                FotoEquipamentoEmprestimoTI.objects.create(
                    equipamento=equip, imagem=foto, nome_original=foto.name, enviado_por=request.user
                )

        # Gera o termo em PDF e vincula ao emprestimo.
        pdf_bytes = gerar_termo_pdf_bytes(emprestimo, aplicar_assinatura=aplicar_assinatura)
        emprestimo.termo_pdf.save(f"termo_emprestimo_{emprestimo.id}.pdf", ContentFile(pdf_bytes), save=True)

        if aplicar_assinatura and assinatura:
            LogUsoAssinaturaTI.objects.create(
                assinatura=assinatura,
                emprestimo=emprestimo,
                usado_por=request.user,
                observacao="Assinatura aplicada na geracao do termo.",
            )

    return JsonResponse(
        {
            "ok": True,
            "message": "Emprestimo cadastrado e termo gerado com sucesso.",
            "emprestimo": _serialize_emprestimo_row(emprestimo, len(equipamentos)),
        }
    )


@login_required
def emprestimo_detail_view(request, emprestimo_id: int):
    if not _is_ti(request.user):
        return _json_error("Voce nao tem permissao para ver emprestimos.", status=403)

    emp = (
        EmprestimoTI.objects.select_related("assinatura_responsavel", "termo_assinado_por")
        .prefetch_related("equipamentos__fotos")
        .filter(pk=emprestimo_id)
        .first()
    )
    if not emp:
        return _json_error("Emprestimo nao encontrado.", status=404)

    equipamentos = []
    for equip in emp.equipamentos.all():
        equipamentos.append(
            {
                "tipo_equipamento": equip.tipo_equipamento,
                "marca": equip.marca,
                "modelo": equip.modelo,
                "numero_serie": equip.numero_serie or "-",
                "patrimonio_etiqueta": equip.patrimonio_etiqueta or "-",
                "acessorios_entregues": equip.acessorios_entregues or "-",
                "fotos": [
                    {
                        "url": reverse("emprestimo_foto", args=[foto.id]),
                        "nome": foto.nome_original or foto.imagem.name,
                        "is_image": _is_image_name(foto.nome_original or foto.imagem.name),
                    }
                    for foto in equip.fotos.all()
                ],
            }
        )

    return JsonResponse(
        {
            "ok": True,
            "id": emp.id,
            "colaborador_nome": emp.colaborador_nome,
            "empresa": emp.empresa or "-",
            "cpf": emp.cpf or "-",
            "email": emp.email or "-",
            "telefone": emp.telefone or "-",
            "data_emprestimo": emp.data_emprestimo.strftime("%d/%m/%Y") if emp.data_emprestimo else "-",
            "devolucao": emp.devolucao_display,
            "observacoes_internas": emp.observacoes_internas or "-",
            "status": emp.status,
            "status_label": emp.status_label,
            "assinatura_responsavel": emp.assinatura_responsavel.nome_responsavel if emp.assinatura_responsavel else "-",
            "termo_pdf_url": reverse("emprestimo_baixar_termo", args=[emp.id]) if emp.termo_pdf else "",
            "termo_assinado_url": reverse("emprestimo_termo_assinado", args=[emp.id]) if emp.termo_assinado else "",
            "termo_assinado_ok": emp.termo_assinado_ok,
            "termo_assinado_em": timezone.localtime(emp.termo_assinado_em).strftime("%d/%m/%Y %H:%M") if emp.termo_assinado_em else "",
            "termo_assinado_por": _attendant_display(emp.termo_assinado_por) or "",
            "equipamentos": equipamentos,
            "criado_por": _attendant_display(emp.criado_por) or "-",
        }
    )


@login_required
def emprestimo_baixar_termo_view(request, emprestimo_id: int):
    if not _is_ti(request.user):
        raise Http404("Nao encontrado.")
    emp = get_object_or_404(EmprestimoTI, pk=emprestimo_id)
    if not emp.termo_pdf:
        raise Http404("Termo ainda nao gerado.")
    try:
        return FileResponse(
            emp.termo_pdf.open("rb"),
            as_attachment=True,
            filename=f"termo_emprestimo_{emp.id}.pdf",
        )
    except FileNotFoundError:
        raise Http404("Arquivo do termo nao encontrado no armazenamento.")


@login_required
def emprestimo_foto_view(request, foto_id: int):
    """Serve a foto de um equipamento inline, por rota protegida (TI/admin).

    Necessario porque `MEDIA` so e servido diretamente com DEBUG=True; alem
    disso protege as fotos de acesso sem permissao.
    """
    if not _is_ti(request.user):
        raise Http404("Nao encontrado.")
    foto = get_object_or_404(FotoEquipamentoEmprestimoTI, pk=foto_id)
    try:
        return FileResponse(foto.imagem.open("rb"), filename=foto.nome_original or foto.imagem.name)
    except FileNotFoundError:
        raise Http404("Imagem nao encontrada no armazenamento.")


@login_required
def emprestimo_termo_assinado_view(request, emprestimo_id: int):
    """Serve o termo assinado anexado, por rota protegida (TI/admin)."""
    if not _is_ti(request.user):
        raise Http404("Nao encontrado.")
    emp = get_object_or_404(EmprestimoTI, pk=emprestimo_id)
    if not emp.termo_assinado:
        raise Http404("Termo assinado nao anexado.")
    try:
        return FileResponse(emp.termo_assinado.open("rb"), filename=emp.termo_assinado.name.split("/")[-1])
    except FileNotFoundError:
        raise Http404("Arquivo nao encontrado no armazenamento.")


@login_required
@require_POST
def emprestimo_anexar_termo_assinado_view(request, emprestimo_id: int):
    if not _is_ti(request.user):
        return _json_error("Voce nao tem permissao para anexar o termo assinado.", status=403)

    emp = EmprestimoTI.objects.filter(pk=emprestimo_id).first()
    if not emp:
        return _json_error("Emprestimo nao encontrado.", status=404)

    arquivo = request.FILES.get("termo_assinado")
    if not arquivo:
        return _json_error("Selecione o arquivo do termo assinado.")

    emp.termo_assinado = arquivo
    emp.termo_assinado_em = timezone.now()
    emp.termo_assinado_por = request.user
    emp.save(update_fields=["termo_assinado", "termo_assinado_em", "termo_assinado_por", "atualizado_em"])

    return JsonResponse(
        {
            "ok": True,
            "message": "Termo assinado anexado com sucesso.",
            "termo_assinado_url": reverse("emprestimo_termo_assinado", args=[emp.id]),
            "termo_assinado_em": timezone.localtime(emp.termo_assinado_em).strftime("%d/%m/%Y %H:%M"),
            "termo_assinado_por": _attendant_display(emp.termo_assinado_por) or "-",
        }
    )


@login_required
@require_POST
def emprestimo_marcar_ok_view(request, emprestimo_id: int):
    if not _is_ti(request.user):
        return _json_error("Voce nao tem permissao para marcar a documentacao.", status=403)

    emp = EmprestimoTI.objects.filter(pk=emprestimo_id).first()
    if not emp:
        return _json_error("Emprestimo nao encontrado.", status=404)
    if not emp.termo_assinado:
        return _json_error("Anexe o termo assinado antes de marcar como OK.", status=409)

    emp.termo_assinado_ok = True
    emp.status = EmprestimoTI.STATUS_ASSINADA_OK
    emp.save(update_fields=["termo_assinado_ok", "status", "atualizado_em"])

    return JsonResponse(
        {
            "ok": True,
            "message": "Documentacao marcada como assinada / OK.",
            "status": emp.status,
            "status_label": emp.status_label,
        }
    )


# ==========================================================================
# Modulo Documentos
# ==========================================================================


def _serialize_documento_anexo(anexo: DocumentoTIAnexo):
    return {
        "nome": anexo.nome_original or anexo.arquivo.name,
        "url": reverse("documento_anexo_download", args=[anexo.id]),
    }


def _serialize_documento_row(documento: DocumentoTI, anexos_count=None):
    count = anexos_count if anexos_count is not None else documento.anexos.count()
    return {
        "id": documento.id,
        "nome": documento.nome,
        "observacao": documento.observacao or "",
        "anexos_count": count,
        "criado_por": _attendant_display(documento.criado_por) or "-",
        "criado_em": timezone.localtime(documento.criado_em).strftime("%d/%m/%Y %H:%M"),
    }


@ti_required
def documentos_dashboard_view(request):
    documentos = (
        DocumentoTI.objects.filter(ativo=True)
        .select_related("criado_por")
        .annotate(anexos_total=Count("anexos"))
    )
    rows = [_serialize_documento_row(doc, doc.anexos_total) for doc in documentos]
    context = {
        "page_title": "Documentos",
        "documentos": rows,
        "is_admin": is_admin_user(request.user),
        "is_attendant": is_attendant_user(request.user),
        "can_view_history": True,
    }
    return render(request, "chamados/documentos.html", context)


@login_required
@require_POST
def documento_create_view(request):
    if not _is_ti(request.user):
        return _json_error("Voce nao tem permissao para cadastrar documentos.", status=403)

    nome = (request.POST.get("nome") or "").strip()
    observacao = (request.POST.get("observacao") or "").strip()
    anexos = request.FILES.getlist("anexos")

    if len(nome) < 2:
        return _json_error("Informe um nome com pelo menos 2 caracteres.")

    with transaction.atomic():
        documento = DocumentoTI.objects.create(
            nome=nome, observacao=observacao, criado_por=request.user
        )
        for arquivo in anexos:
            DocumentoTIAnexo.objects.create(
                documento=documento,
                arquivo=arquivo,
                nome_original=arquivo.name,
                enviado_por=request.user,
            )

    return JsonResponse(
        {
            "ok": True,
            "message": "Documento cadastrado com sucesso.",
            "documento": _serialize_documento_row(documento, len(anexos)),
        }
    )


@login_required
def documento_detail_view(request, documento_id: int):
    if not _is_ti(request.user):
        return _json_error("Voce nao tem permissao para ver documentos.", status=403)

    documento = (
        DocumentoTI.objects.select_related("criado_por").filter(pk=documento_id).first()
    )
    if not documento:
        return _json_error("Documento nao encontrado.", status=404)

    return JsonResponse(
        {
            "ok": True,
            "id": documento.id,
            "nome": documento.nome,
            "observacao": documento.observacao or "",
            "criado_por": _attendant_display(documento.criado_por) or "-",
            "criado_em": timezone.localtime(documento.criado_em).strftime("%d/%m/%Y %H:%M"),
            "anexos": [_serialize_documento_anexo(a) for a in documento.anexos.all()],
        }
    )


@login_required
def documento_anexo_download_view(request, anexo_id: int):
    if not _is_ti(request.user):
        raise Http404("Nao encontrado.")
    anexo = get_object_or_404(DocumentoTIAnexo, pk=anexo_id)
    try:
        return FileResponse(
            anexo.arquivo.open("rb"),
            as_attachment=True,
            filename=anexo.nome_original or anexo.arquivo.name,
        )
    except FileNotFoundError:
        raise Http404("Arquivo nao encontrado no armazenamento.")


# ==========================================================================
# Modulo Insumos
# ==========================================================================


def _serialize_insumo(insumo: InsumoTI):
    return {
        "id": insumo.id,
        "nome": insumo.nome,
        "descricao": insumo.descricao or "",
        "quantidade_atual": insumo.quantidade_atual,
        "observacao": insumo.observacao or "",
        "status": insumo.status_estoque,
        "status_label": insumo.status_label,
    }


def _serialize_retirada(retirada: RetiradaInsumoTI):
    return {
        "id": retirada.id,
        "insumo": retirada.insumo.nome,
        "quantidade": retirada.quantidade,
        "entregue_para": retirada.entregue_para,
        "motivo": retirada.motivo,
        "registrado_por": _attendant_display(retirada.registrado_por) or "-",
        "criado_em": timezone.localtime(retirada.criado_em).strftime("%d/%m/%Y %H:%M"),
    }


@ti_required
def insumos_dashboard_view(request):
    insumos = list(InsumoTI.objects.filter(ativo=True))
    retiradas = list(
        RetiradaInsumoTI.objects.select_related("insumo", "registrado_por")[:50]
    )
    context = {
        "page_title": "Insumos",
        "insumos": [_serialize_insumo(i) for i in insumos],
        "retiradas": [_serialize_retirada(r) for r in retiradas],
        "is_admin": is_admin_user(request.user),
        "is_attendant": is_attendant_user(request.user),
        "can_view_history": True,
    }
    return render(request, "chamados/insumos.html", context)


@login_required
@require_POST
def insumo_create_view(request):
    if not _is_ti(request.user):
        return _json_error("Voce nao tem permissao para cadastrar insumos.", status=403)

    payload = _load_request_payload(request) or {}
    nome = (payload.get("nome") or "").strip()
    descricao = (payload.get("descricao") or "").strip()
    observacao = (payload.get("observacao") or "").strip()

    if len(nome) < 2:
        return _json_error("Informe um nome com pelo menos 2 caracteres.")

    quantidade_raw = payload.get("quantidade_inicial")
    if quantidade_raw is None or str(quantidade_raw).strip() == "":
        return _json_error("Informe a quantidade inicial.")
    try:
        quantidade = int(quantidade_raw)
    except (TypeError, ValueError):
        return _json_error("Quantidade inicial invalida.")
    if quantidade < 0:
        return _json_error("A quantidade inicial nao pode ser negativa.")

    insumo = InsumoTI.objects.create(
        nome=nome,
        descricao=descricao,
        quantidade_atual=quantidade,
        observacao=observacao,
        criado_por=request.user,
    )
    return JsonResponse(
        {"ok": True, "message": "Insumo cadastrado com sucesso.", "insumo": _serialize_insumo(insumo)}
    )


@login_required
@require_POST
def retirada_create_view(request, insumo_id: int):
    if not _is_ti(request.user):
        return _json_error("Voce nao tem permissao para registrar retiradas.", status=403)

    payload = _load_request_payload(request) or {}
    entregue_para = (payload.get("entregue_para") or "").strip()
    motivo = (payload.get("motivo") or "").strip()

    try:
        quantidade = int(payload.get("quantidade"))
    except (TypeError, ValueError):
        return _json_error("Quantidade invalida.")

    if quantidade <= 0:
        return _json_error("A quantidade retirada deve ser maior que zero.")
    if not entregue_para:
        return _json_error("Informe para quem o insumo foi entregue.")
    if not motivo:
        return _json_error("Informe o motivo da retirada.")

    with transaction.atomic():
        insumo = InsumoTI.objects.select_for_update().filter(pk=insumo_id, ativo=True).first()
        if not insumo:
            return _json_error("Insumo nao encontrado.", status=404)
        if quantidade > insumo.quantidade_atual:
            return _json_error(
                f"Estoque insuficiente. Disponivel: {insumo.quantidade_atual}.", status=409
            )

        insumo.quantidade_atual -= quantidade
        insumo.save(update_fields=["quantidade_atual", "atualizado_em"])
        retirada = RetiradaInsumoTI.objects.create(
            insumo=insumo,
            quantidade=quantidade,
            entregue_para=entregue_para,
            motivo=motivo,
            registrado_por=request.user,
        )

    return JsonResponse(
        {
            "ok": True,
            "message": "Retirada registrada com sucesso.",
            "insumo": _serialize_insumo(insumo),
            "retirada": _serialize_retirada(retirada),
        }
    )


@login_required
def dashboard_redirect_view(request):
    return redirect(_landing_route_for_user(request.user))


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Sessao encerrada com sucesso.")
    return redirect("login")
