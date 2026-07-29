"""Diagnostico (somente leitura) da base de atendimentos, para conferir de onde a
planilha mensal consegue tirar linhas.

Uso no servidor, dentro da pasta do projeto e com a venv ativa:

    python scripts/diagnostico_planilha.py

Nao altera nada no banco: apenas conta e imprime.
"""

import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chamados_ti.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.db.models import Count, Max, Min
from django.db.models.functions import TruncMonth

from core.models import AtendimentoHistorico, Chamado, ChamadoEvento

print("=" * 64)
print("CHAMADOS")
print("=" * 64)
print("total:", Chamado.objects.count())
print("encerrados:", Chamado.objects.filter(status__in=Chamado.STATUS_ENCERRADOS).count())
print("mais antigo (criado_em):", Chamado.objects.aggregate(v=Min("criado_em"))["v"])
print("mais recente (criado_em):", Chamado.objects.aggregate(v=Max("criado_em"))["v"])
print("\nencerrados por mes (por fechado_em):")
for linha in (
    Chamado.objects.filter(status__in=Chamado.STATUS_ENCERRADOS, fechado_em__isnull=False)
    .annotate(m=TruncMonth("fechado_em"))
    .values("m")
    .annotate(n=Count("id"))
    .order_by("m")
):
    print("   ", linha["m"].strftime("%m/%Y") if linha["m"] else "-", "->", linha["n"])
print("encerrados SEM fechado_em:", Chamado.objects.filter(status__in=Chamado.STATUS_ENCERRADOS, fechado_em__isnull=True).count())

print("\nchamados por origem:")
for linha in Chamado.objects.values("origem").annotate(n=Count("id")).order_by("-n"):
    print("   ", repr(linha["origem"]), "->", linha["n"])

print()
print("=" * 64)
print("PERIODOS DE ATENDIMENTO (Play -> Pause/Stop) - a fonte da planilha")
print("=" * 64)
print("total:", AtendimentoHistorico.objects.count())
print("mais antigo (iniciado_em):", AtendimentoHistorico.objects.aggregate(v=Min("iniciado_em"))["v"])
print("mais recente (iniciado_em):", AtendimentoHistorico.objects.aggregate(v=Max("iniciado_em"))["v"])
print("\nperiodos por mes (por iniciado_em):")
for linha in (
    AtendimentoHistorico.objects.annotate(m=TruncMonth("iniciado_em"))
    .values("m")
    .annotate(n=Count("id"))
    .order_by("m")
):
    print("   ", linha["m"].strftime("%m/%Y") if linha["m"] else "-", "->", linha["n"])

print("\nperiodos por atendente:")
for linha in (
    AtendimentoHistorico.objects.values("atendente__username").annotate(n=Count("id")).order_by("-n")
):
    print("   ", linha["atendente__username"], "->", linha["n"])

print()
print("=" * 64)
print("QUANTO A PLANILHA PERDE HOJE")
print("=" * 64)
encerrados = Chamado.objects.filter(status__in=Chamado.STATUS_ENCERRADOS)
sem_periodo = encerrados.filter(atendimentos__isnull=True).distinct()
print("encerrados SEM nenhum periodo de atendimento:", sem_periodo.count())
print("  -> estes NAO aparecem na planilha hoje (ela lista periodos, nao chamados)")
print("\nencerrados sem periodo, por mes (fechado_em):")
for linha in (
    sem_periodo.filter(fechado_em__isnull=False)
    .annotate(m=TruncMonth("fechado_em"))
    .values("m")
    .annotate(n=Count("id"))
    .order_by("m")
):
    print("   ", linha["m"].strftime("%m/%Y") if linha["m"] else "-", "->", linha["n"])

print("\neventos de encerramento direto (Stop sem Play):",
      ChamadoEvento.objects.filter(tipo="encerramento_direto").count())

print("\natendentes cadastrados:")
User = get_user_model()
for u in User.objects.filter(groups__name="Atendente TI"):
    print("   ", u.username, "|", u.get_full_name(), "|", u.email)

print("\n8 encerrados mais antigos (amostra):")
for c in encerrados.order_by("criado_em")[:8]:
    fechado = f"{c.fechado_em:%d/%m/%Y %H:%M}" if c.fechado_em else "sem data"
    print(
        f"    {c.numero} | criado {c.criado_em:%d/%m/%Y %H:%M} | fechado {fechado}"
        f" | origem={c.origem!r} | periodos={c.atendimentos.count()}"
    )
