import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.db import migrations


def seed_servicos(apps, schema_editor):
    """Cadastro inicial dos servicos feitos a partir de um arquivo LOCAL,
    ignorado pelo Git (`seed/servicos_feitos_seed.json`). Os anexos (PDFs de
    NF/orcamento) ficam em `media/servicos_feitos/` (tambem fora do Git).

    Se o arquivo de seed nao existir (ex.: clone limpo/CI), a migracao nao faz
    nada. Idempotente: nao duplica se ja houver servicos cadastrados. Anexos
    cujo arquivo fisico nao existir sao ignorados.
    """
    ServicoFeito = apps.get_model("core", "ServicoFeito")
    ServicoFeitoAnexo = apps.get_model("core", "ServicoFeitoAnexo")

    if ServicoFeito.objects.exists():
        return

    seed_path = Path(settings.BASE_DIR) / "seed" / "servicos_feitos_seed.json"
    if not seed_path.exists():
        return

    try:
        registros = json.loads(seed_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return

    media_root = Path(settings.MEDIA_ROOT)
    for reg in registros:
        try:
            valor = Decimal(str(reg.get("valor") or "0"))
        except (InvalidOperation, ValueError):
            valor = Decimal("0")

        servico = ServicoFeito.objects.create(
            nome_servico=reg.get("nome_servico", "") or "",
            empresa=reg.get("empresa", "") or "",
            descricao=reg.get("descricao", "") or "",
            data_servico=reg.get("data_servico") or None,
            valor=valor,
        )
        anexos = []
        for nome_arquivo in reg.get("anexos", []) or []:
            nome_arquivo = (nome_arquivo or "").strip()
            if not nome_arquivo:
                continue
            caminho_rel = f"servicos_feitos/{nome_arquivo}"
            if not (media_root / caminho_rel).exists():
                continue
            anexos.append(
                ServicoFeitoAnexo(
                    servico=servico,
                    arquivo=caminho_rel,
                    nome_original=nome_arquivo,
                )
            )
        if anexos:
            ServicoFeitoAnexo.objects.bulk_create(anexos)


def unseed_servicos(apps, schema_editor):
    # Reversao segura: nao apaga nada automaticamente.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_servicofeito_servicofeitoanexo"),
    ]

    operations = [
        migrations.RunPython(seed_servicos, unseed_servicos),
    ]
