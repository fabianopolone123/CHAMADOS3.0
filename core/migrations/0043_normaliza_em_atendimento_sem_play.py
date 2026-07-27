"""Normaliza chamados marcados como "Em atendimento" sem nenhum Play ativo.

Desde 16/07/2026 o status "Em atendimento" so vale enquanto existe um
`AtendimentoHistorico` aberto (do Play ao Pause/Stop) — arrastar um chamado
para a coluna de um atendente apenas o marca como "Atribuido". Chamados
movidos ANTES dessa mudanca ficaram com `status = em_atendimento` gravado sem
nunca terem tido um Play, o que inflava o contador "em atend." da coluna do
atendente no Kanban (aparecia 2 com apenas 1 chamado realmente em play).

Esta migration corrige os registros antigos de uma vez: chamados nao
encerrados, com status "em_atendimento" e sem atendimento ativo, voltam para
"Atribuido" (quando tem atendente atual) ou "Aberto" (quando estao sem). Em um
banco limpo e no-op.
"""

from django.db import migrations

STATUS_EM_ATENDIMENTO = "em_atendimento"
STATUS_ATRIBUIDO = "atribuido"
STATUS_ABERTO = "aberto"
STATUS_ENCERRADOS = ["resolvido", "fechado"]


def normalizar_status(apps, schema_editor):
    Chamado = apps.get_model("core", "Chamado")
    AtendimentoHistorico = apps.get_model("core", "AtendimentoHistorico")

    com_play = set(
        AtendimentoHistorico.objects.filter(finalizado_em__isnull=True).values_list(
            "chamado_id", flat=True
        )
    )

    candidatos = Chamado.objects.filter(status=STATUS_EM_ATENDIMENTO).exclude(
        status__in=STATUS_ENCERRADOS
    )
    for chamado in candidatos:
        if chamado.id in com_play:
            continue  # tem Play ativo: o status esta correto
        chamado.status = STATUS_ATRIBUIDO if chamado.atendente_atual_id else STATUS_ABERTO
        chamado.save(update_fields=["status"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0042_renumera_codigos_requisicoes"),
    ]

    operations = [
        migrations.RunPython(normalizar_status, migrations.RunPython.noop),
    ]
