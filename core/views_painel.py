"""Painel do Titular: terminal de administracao do sistema.

Tela unica (`/painel/`) no estilo dos terminais de banco, navegada por teclado,
com quatro areas:

1. INTERFACE  - rotulo, ordem e visibilidade dos itens do menu lateral;
2. USUARIOS   - perfil (Administrador / Atendente TI) e situacao das contas;
3. DADOS      - consulta e alteracao dos registros de qualquer modulo;
4. OPERACAO   - contadores, manutencao e trilha do proprio painel.

O acesso e exclusivo do titular (`is_titular_user`) e **toda** acao que grava
passa por `PainelAuditoria`. As views abaixo respondem JSON; o desenho do
terminal fica em `static/js/painel.js`.
"""
from __future__ import annotations

import json
import platform
from functools import wraps
from io import StringIO
from pathlib import Path

import django
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.management import call_command
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from . import painel_dados
from .menu import ITEM_POR_CHAVE, itens_menu_para_painel
from .models import (
    AtendimentoHistorico,
    Chamado,
    ItemMenuConfig,
    PainelAuditoria,
    PausaAutomatica,
    PendenciaTI,
)
from .permissions import (
    PRIMARY_ADMIN_USERNAME,
    ensure_permission_groups,
    is_admin_user,
    is_attendant_user,
    is_titular_user,
)

POR_PAGINA = 14


def titular_required(view_func):
    """So o titular entra no painel; qualquer outro volta para a tela dele."""

    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_titular_user(request.user):
            if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.path.startswith("/painel/api/"):
                return JsonResponse({"ok": False, "message": "Acesso restrito ao titular."}, status=403)
            messages.error(request, "O Painel do Titular e restrito ao administrador principal.")
            return redirect("tickets_dashboard")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def _payload(request) -> dict:
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {}


def _erro(mensagem: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"ok": False, "message": mensagem}, status=status)


def _registrar(request, area: str, acao: str, alvo: str = "", detalhe: str = "") -> None:
    PainelAuditoria.registrar(request.user, area, acao, alvo, detalhe)


# ---------------------------------------------------------------- tela ------


@titular_required
@ensure_csrf_cookie
def painel_view(request):
    """Carrega o terminal. Os dados de cada area vem pelas rotas JSON.

    `ensure_csrf_cookie` garante o cookie de CSRF ja na primeira carga: a tela e
    montada por JavaScript e nao tem formulario nenhum para emiti-lo.
    """
    return render(request, "chamados/painel.html", {"operador": request.user.get_username()})


# --------------------------------------------------------- tela principal ---


@titular_required
@require_GET
def painel_estado_view(request):
    """Numeros da tela inicial: o que o titular precisa ver de relance."""
    agora = timezone.localtime()
    inicio_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    Usuario = get_user_model()

    abertos = Chamado.objects.exclude(status__in=Chamado.STATUS_ENCERRADOS).count()
    return JsonResponse(
        {
            "ok": True,
            "operador": request.user.get_username().upper(),
            "linhas": [
                {"rotulo": "CHAMADOS EM ABERTO", "valor": abertos},
                {"rotulo": "CHAMADOS NO TOTAL", "valor": Chamado.objects.count()},
                {"rotulo": "ATENDIMENTOS COM PLAY", "valor": AtendimentoHistorico.objects.filter(finalizado_em__isnull=True).count()},
                {"rotulo": "PAUSAS SEM COMPLEMENTO", "valor": PausaAutomatica.objects.filter(complementado_em__isnull=True).count()},
                {"rotulo": "PENDENCIAS ABERTAS", "valor": PendenciaTI.objects.filter(convertido_em_chamado=False).count()},
                {"rotulo": "USUARIOS CADASTRADOS", "valor": Usuario.objects.count()},
                {"rotulo": "ACESSOS HOJE", "valor": Usuario.objects.filter(last_login__gte=inicio_dia).count()},
                {"rotulo": "ITENS NO MENU", "valor": len([i for i in itens_menu_para_painel() if i["visivel"]])},
            ],
        }
    )


# ------------------------------------------------------------- interface ----


@titular_required
@require_GET
def painel_interface_view(request):
    return JsonResponse({"ok": True, "itens": itens_menu_para_painel()})


def _gravar_ordem_atual(itens: list[dict]) -> None:
    """Persiste a ordem exibida, item a item (0, 1, 2, ...)."""
    for posicao, item in enumerate(itens):
        config, _ = ItemMenuConfig.objects.get_or_create(chave=item["chave"])
        if config.ordem != posicao:
            config.ordem = posicao
            config.save(update_fields=["ordem", "atualizado_em"])


@titular_required
@require_POST
def painel_interface_salvar_view(request):
    """Acoes da area INTERFACE: alternar visibilidade, mover, renomear, restaurar."""
    dados = _payload(request)
    acao = (dados.get("acao") or "").strip()
    chave = (dados.get("chave") or "").strip()

    if acao == "restaurar_tudo":
        apagados = ItemMenuConfig.objects.count()
        ItemMenuConfig.objects.all().delete()
        _registrar(request, PainelAuditoria.AREA_INTERFACE, "restaurar padrao", "menu inteiro", f"{apagados} ajuste(s) removido(s)")
        return JsonResponse({"ok": True, "message": "Menu restaurado para o padrao de fabrica.", "itens": itens_menu_para_painel()})

    if chave not in ITEM_POR_CHAVE:
        return _erro("Item de menu inexistente.")

    padrao = ITEM_POR_CHAVE[chave]

    if acao == "restaurar":
        ItemMenuConfig.objects.filter(chave=chave).delete()
        _registrar(request, PainelAuditoria.AREA_INTERFACE, "restaurar padrao", chave)
        return JsonResponse({"ok": True, "message": f"{padrao.rotulo}: voltou ao padrao.", "itens": itens_menu_para_painel()})

    config, _ = ItemMenuConfig.objects.get_or_create(chave=chave)

    if acao == "visivel":
        config.visivel = not config.visivel
        config.save(update_fields=["visivel", "atualizado_em"])
        _registrar(
            request,
            PainelAuditoria.AREA_INTERFACE,
            "mostrar item" if config.visivel else "esconder item",
            chave,
        )
        estado = "visivel no menu" if config.visivel else "escondido do menu"
        return JsonResponse({"ok": True, "message": f"{padrao.rotulo}: {estado}.", "itens": itens_menu_para_painel()})

    if acao == "rotulo":
        novo = (dados.get("valor") or "").strip()
        if len(novo) > 40:
            return _erro("O rotulo pode ter no maximo 40 caracteres.")
        config.rotulo = "" if novo.lower() == padrao.rotulo.lower() else novo
        config.save(update_fields=["rotulo", "atualizado_em"])
        _registrar(request, PainelAuditoria.AREA_INTERFACE, "renomear item", chave, f"{padrao.rotulo} -> {novo or padrao.rotulo}")
        return JsonResponse({"ok": True, "message": f"Rotulo salvo: {novo or padrao.rotulo}.", "itens": itens_menu_para_painel()})

    if acao in {"subir", "descer"}:
        itens = itens_menu_para_painel()
        posicao = next((i for i, item in enumerate(itens) if item["chave"] == chave), None)
        if posicao is None:
            return _erro("Item de menu inexistente.")
        destino = posicao - 1 if acao == "subir" else posicao + 1
        if destino < 0 or destino >= len(itens):
            return _erro("O item ja esta na ponta da lista.")
        itens[posicao], itens[destino] = itens[destino], itens[posicao]
        _gravar_ordem_atual(itens)
        _registrar(request, PainelAuditoria.AREA_INTERFACE, f"mover item ({acao})", chave, f"posicao {posicao + 1} -> {destino + 1}")
        return JsonResponse({"ok": True, "message": f"{padrao.rotulo}: movido.", "itens": itens_menu_para_painel()})

    return _erro("Acao desconhecida.")


# -------------------------------------------------------------- usuarios ----


def _perfil(user) -> str:
    if is_admin_user(user):
        return "ADMINISTRADOR"
    if is_attendant_user(user):
        return "ATENDENTE TI"
    return "COMUM"


def _linha_usuario(user) -> dict:
    return {
        "pk": user.pk,
        "usuario": user.get_username(),
        "nome": (user.get_full_name() or "").strip() or "-",
        "perfil": _perfil(user),
        "admin": is_admin_user(user),
        "atendente": is_attendant_user(user),
        "ativo": user.is_active,
        "titular": user.get_username().lower() == PRIMARY_ADMIN_USERNAME.lower(),
        "ultimo_acesso": timezone.localtime(user.last_login).strftime("%d/%m/%Y %H:%M") if user.last_login else "nunca",
    }


@titular_required
@require_GET
def painel_usuarios_view(request):
    termo = (request.GET.get("q") or "").strip()
    pagina = max(int(request.GET.get("pagina") or 0), 0)

    qs = get_user_model().objects.all().order_by("username")
    if termo:
        from django.db.models import Q

        qs = qs.filter(
            Q(username__icontains=termo)
            | Q(first_name__icontains=termo)
            | Q(last_name__icontains=termo)
            | Q(email__icontains=termo)
        )

    total = qs.count()
    paginas = max((total + POR_PAGINA - 1) // POR_PAGINA, 1)
    pagina = min(pagina, paginas - 1)
    usuarios = [_linha_usuario(u) for u in qs[pagina * POR_PAGINA : (pagina + 1) * POR_PAGINA]]
    return JsonResponse(
        {
            "ok": True,
            "usuarios": usuarios,
            "total": total,
            "pagina": pagina,
            "paginas": paginas,
            "termo": termo,
        }
    )


@titular_required
@require_POST
def painel_usuario_acao_view(request, usuario_id: int):
    """Perfil e situacao de uma conta. O titular nunca pode se rebaixar aqui."""
    dados = _payload(request)
    acao = (dados.get("acao") or "").strip()

    Usuario = get_user_model()
    user = Usuario.objects.filter(pk=usuario_id).first()
    if not user:
        return _erro("Usuario nao encontrado.", status=404)

    if user.get_username().lower() == PRIMARY_ADMIN_USERNAME.lower():
        return _erro("A conta do titular nao pode ser alterada pelo painel.", status=409)

    grupos = ensure_permission_groups()

    if acao == "admin":
        entrando = not is_admin_user(user)
        if entrando:
            user.groups.add(grupos.admin)
        else:
            user.groups.remove(grupos.admin)
            user.is_superuser = False
            user.is_staff = False
            user.save(update_fields=["is_superuser", "is_staff"])
        _registrar(request, PainelAuditoria.AREA_USUARIOS, "grupo Administrador", user.get_username(), "incluido" if entrando else "removido")
        texto = "agora e Administrador" if entrando else "saiu do grupo Administrador"

    elif acao == "atendente":
        entrando = not is_attendant_user(user)
        (user.groups.add if entrando else user.groups.remove)(grupos.attendant)
        _registrar(request, PainelAuditoria.AREA_USUARIOS, "grupo Atendente TI", user.get_username(), "incluido" if entrando else "removido")
        texto = "agora e Atendente TI" if entrando else "saiu do grupo Atendente TI"

    elif acao == "ativo":
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        _registrar(request, PainelAuditoria.AREA_USUARIOS, "situacao da conta", user.get_username(), "ativada" if user.is_active else "desativada")
        texto = "conta ativada" if user.is_active else "conta desativada (nao entra mais)"

    else:
        return _erro("Acao desconhecida.")

    user.refresh_from_db()
    return JsonResponse({"ok": True, "message": f"{user.get_username()}: {texto}.", "usuario": _linha_usuario(user)})


# ----------------------------------------------------------------- dados ----


@titular_required
@require_GET
def painel_tabelas_view(request):
    return JsonResponse({"ok": True, "tabelas": painel_dados.resumo_tabelas()})


@titular_required
@require_GET
def painel_tabela_view(request, chave: str):
    tabela = painel_dados.TABELA_POR_CHAVE.get(chave)
    if not tabela:
        return _erro("Tabela inexistente.", status=404)
    return JsonResponse(
        {
            "ok": True,
            **painel_dados.listar(
                tabela,
                termo=request.GET.get("q") or "",
                pagina=max(int(request.GET.get("pagina") or 0), 0),
                por_pagina=POR_PAGINA,
            ),
        }
    )


@titular_required
@require_GET
def painel_registro_view(request, chave: str, pk: str):
    tabela = painel_dados.TABELA_POR_CHAVE.get(chave)
    if not tabela:
        return _erro("Tabela inexistente.", status=404)
    try:
        return JsonResponse({"ok": True, **painel_dados.detalhar(tabela, pk)})
    except ObjectDoesNotExist:
        return _erro("Registro nao encontrado.", status=404)


@titular_required
@require_POST
def painel_registro_alterar_view(request, chave: str, pk: str):
    tabela = painel_dados.TABELA_POR_CHAVE.get(chave)
    if not tabela:
        return _erro("Tabela inexistente.", status=404)

    dados = _payload(request)
    campo = (dados.get("campo") or "").strip()
    valor = dados.get("valor")

    try:
        obj, anterior, novo = painel_dados.alterar_campo(tabela, pk, campo, "" if valor is None else str(valor))
    except ObjectDoesNotExist:
        return _erro("Registro nao encontrado.", status=404)
    except ValidationError as exc:
        return _erro("; ".join(exc.messages))
    except Exception as exc:  # erro do proprio modelo (unique, regra de negocio)
        return _erro(f"Nao foi possivel salvar: {exc}")

    _registrar(
        request,
        PainelAuditoria.AREA_DADOS,
        f"alterar {campo}",
        f"{tabela.rotulo} #{pk}",
        f"{anterior} -> {novo}",
    )
    return JsonResponse(
        {
            "ok": True,
            "message": f"{campo.replace('_', ' ').upper()}: {anterior} -> {novo}",
            **painel_dados.detalhar(tabela, obj.pk),
        }
    )


@titular_required
@require_POST
def painel_registro_excluir_view(request, chave: str, pk: str):
    tabela = painel_dados.TABELA_POR_CHAVE.get(chave)
    if not tabela:
        return _erro("Tabela inexistente.", status=404)
    try:
        rotulo = painel_dados.excluir(tabela, pk)
    except ObjectDoesNotExist:
        return _erro("Registro nao encontrado.", status=404)
    except ValidationError as exc:
        return _erro("; ".join(exc.messages))
    except Exception as exc:
        return _erro(f"Nao foi possivel excluir: {exc}")

    _registrar(request, PainelAuditoria.AREA_DADOS, "excluir registro", f"{tabela.rotulo} #{pk}", rotulo)
    return JsonResponse({"ok": True, "message": f"Excluido: {rotulo}"})


# -------------------------------------------------------------- operacao ----


def _tamanho_legivel(bytes_totais: int) -> str:
    valor = float(bytes_totais)
    for unidade in ("B", "KB", "MB", "GB"):
        if valor < 1024 or unidade == "GB":
            return f"{valor:.1f} {unidade}".replace(".", ",")
        valor /= 1024
    return f"{valor:.1f} GB"


def _tamanho_pasta(caminho: Path) -> int:
    if not caminho.exists():
        return 0
    return sum(arquivo.stat().st_size for arquivo in caminho.rglob("*") if arquivo.is_file())


@titular_required
@require_GET
def painel_operacao_view(request):
    """Estado do sistema + as ultimas acoes feitas pelo proprio painel."""
    banco = Path(str(settings.DATABASES["default"].get("NAME") or ""))
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM django_migrations")
        migracoes = cursor.fetchone()[0]

    abertos = AtendimentoHistorico.objects.filter(finalizado_em__isnull=True).select_related("chamado", "atendente")
    agora = timezone.now()

    return JsonResponse(
        {
            "ok": True,
            "sistema": [
                {"rotulo": "PYTHON", "valor": platform.python_version()},
                {"rotulo": "DJANGO", "valor": django.get_version()},
                {"rotulo": "SERVIDOR", "valor": f"{platform.system()} {platform.release()}"},
                {"rotulo": "BANCO", "valor": f"{connection.vendor} · {_tamanho_legivel(banco.stat().st_size) if banco.is_file() else 'externo'}"},
                {"rotulo": "MIGRACOES APLICADAS", "valor": str(migracoes)},
                {"rotulo": "MEDIA (ANEXOS)", "valor": _tamanho_legivel(_tamanho_pasta(Path(settings.MEDIA_ROOT)))},
                {"rotulo": "DEBUG", "valor": "LIGADO" if settings.DEBUG else "DESLIGADO"},
                {"rotulo": "HORA DO SERVIDOR", "valor": timezone.localtime(agora).strftime("%d/%m/%Y %H:%M:%S")},
            ],
            "abertos": [
                {
                    "chamado": a.chamado.numero if a.chamado_id else "-",
                    "atendente": a.atendente.get_username() if a.atendente_id else "-",
                    "desde": timezone.localtime(a.iniciado_em).strftime("%d/%m %H:%M"),
                    "horas": round((agora - a.iniciado_em).total_seconds() / 3600, 1),
                }
                for a in abertos.order_by("iniciado_em")[:20]
            ],
            "pausas_pendentes": PausaAutomatica.objects.filter(complementado_em__isnull=True).count(),
            "auditoria": [
                {
                    "quando": timezone.localtime(linha.criado_em).strftime("%d/%m %H:%M"),
                    "area": linha.get_area_display().upper(),
                    "acao": linha.acao.upper(),
                    "alvo": linha.alvo,
                    "detalhe": linha.detalhe[:80],
                }
                for linha in PainelAuditoria.objects.select_related("usuario")[:20]
            ],
        }
    )


@titular_required
@require_POST
def painel_operacao_acao_view(request):
    """Acoes de manutencao. Cada uma e registrada na trilha do painel."""
    dados = _payload(request)
    acao = (dados.get("acao") or "").strip()

    if acao in {"pausar_expediente", "pausar_expediente_simulacao"}:
        simulacao = acao.endswith("simulacao")
        saida = StringIO()
        try:
            call_command("pausar_expediente", dry_run=simulacao, stdout=saida, stderr=saida)
        except Exception as exc:
            return _erro(f"O comando falhou: {exc}")
        texto = saida.getvalue().strip() or "Nada a pausar."
        if not simulacao:
            _registrar(request, PainelAuditoria.AREA_OPERACAO, "pausar expediente", "atendimentos com Play", texto[:400])
        return JsonResponse(
            {
                "ok": True,
                "message": "Simulacao concluida." if simulacao else "Expediente pausado.",
                "saida": texto.splitlines(),
            }
        )

    if acao == "limpar_sessoes":
        saida = StringIO()
        try:
            call_command("clearsessions", stdout=saida, stderr=saida)
        except Exception as exc:
            return _erro(f"O comando falhou: {exc}")
        _registrar(request, PainelAuditoria.AREA_OPERACAO, "limpar sessoes expiradas")
        return JsonResponse({"ok": True, "message": "Sessoes expiradas removidas.", "saida": saida.getvalue().splitlines()})

    if acao == "verificar":
        saida = StringIO()
        try:
            call_command("check", stdout=saida, stderr=saida)
        except Exception as exc:
            return _erro(f"A verificacao apontou problema: {exc}")
        return JsonResponse({"ok": True, "message": "Verificacao concluida.", "saida": (saida.getvalue().strip() or "Sem problemas.").splitlines()})

    return _erro("Acao desconhecida.")
