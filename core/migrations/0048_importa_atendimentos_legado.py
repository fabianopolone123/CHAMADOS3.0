import logging
from pathlib import Path

from django.conf import settings
from django.db import migrations

logger = logging.getLogger(__name__)


def importa_atendimentos(apps, schema_editor):
    """Traz os periodos de atendimento do sistema antigo (ERP-TI).

    A migracao original dos chamados nao trouxe a tabela
    `chamados_ticketattendance`, onde esta o tempo trabalhado de 02/2026 a
    07/2026. Sem ela, a planilha mensal de atendimentos e a tela de Historico so
    tem dados de 15/07/2026 em diante.

    O banco antigo NAO e versionado: se `seed/chamados_legado.sqlite3` nao
    existir (clone limpo, CI), esta migracao nao faz nada. Toda a logica e as
    protecoes ficam em `core/importa_atendimentos_legado.py` - em resumo: nunca
    cria periodo sem fim (que viraria atendimento ativo no Kanban), confere que
    cada periodo pertence mesmo ao chamado migrado correspondente, ignora o que
    for a partir do primeiro periodo do sistema novo e nao altera nenhum campo de
    `Chamado`.
    """
    caminho = Path(settings.BASE_DIR) / "seed" / "chamados_legado.sqlite3"
    if not caminho.exists():
        return

    from core.importa_atendimentos_legado import importar

    relatorio = importar(
        caminho,
        Chamado=apps.get_model("core", "Chamado"),
        AtendimentoHistorico=apps.get_model("core", "AtendimentoHistorico"),
        User=apps.get_model(settings.AUTH_USER_MODEL),
    )
    logger.info("Atendimentos legados importados: %s", relatorio)
    print(f"  atendimentos legados: {relatorio}")


def desfaz(apps, schema_editor):
    """Sem volta automatica: os periodos importados nao sao distinguiveis por um
    campo proprio. Para desfazer, apagar pelo intervalo de datas na mao."""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0047_computador_glpi"),
    ]

    operations = [
        migrations.RunPython(importa_atendimentos, desfaz),
    ]
