import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.db import migrations


def seed_contratos(apps, schema_editor):
    """Cadastro inicial dos contratos a partir de um arquivo LOCAL, ignorado pelo
    Git (`seed/contratos_seed.json`). Os anexos (NFs, termos, invoices) ficam em
    `media/contratos_ti/` (tambem fora do Git).

    Se o arquivo de seed nao existir (ex.: clone limpo/CI), a migracao nao faz
    nada. Idempotente: nao duplica se ja houver contratos cadastrados. Anexos
    cujo arquivo fisico nao existir sao ignorados.
    """
    Contrato = apps.get_model("core", "Contrato")
    ContratoAnexo = apps.get_model("core", "ContratoAnexo")

    if Contrato.objects.exists():
        return

    seed_path = Path(settings.BASE_DIR) / "seed" / "contratos_seed.json"
    if not seed_path.exists():
        return

    try:
        registros = json.loads(seed_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return

    periodicidades = {"mensal", "anual", "pagamento_unico"}
    media_root = Path(settings.MEDIA_ROOT)
    for reg in registros:
        valor_raw = reg.get("valor")
        valor = None
        if valor_raw not in (None, ""):
            try:
                valor = Decimal(str(valor_raw))
            except (InvalidOperation, ValueError):
                valor = None

        periodicidade = reg.get("periodicidade") or "mensal"
        if periodicidade not in periodicidades:
            periodicidade = "mensal"

        contrato = Contrato.objects.create(
            nome=reg.get("nome", "") or "",
            observacoes=reg.get("observacoes", "") or "",
            valor=valor,
            forma_pagamento=reg.get("forma_pagamento", "") or "",
            final_cartao=(reg.get("final_cartao", "") or "")[:4],
            periodicidade=periodicidade,
            inicio=reg.get("inicio") or None,
            fim=reg.get("fim") or None,
            encerrado_em=reg.get("encerrado_em") or None,
        )
        anexos = []
        for nome_arquivo in reg.get("anexos", []) or []:
            nome_arquivo = (nome_arquivo or "").strip()
            if not nome_arquivo:
                continue
            caminho_rel = f"contratos_ti/{nome_arquivo}"
            if not (media_root / caminho_rel).exists():
                continue
            anexos.append(
                ContratoAnexo(
                    contrato=contrato,
                    arquivo=caminho_rel,
                    nome_original=nome_arquivo,
                )
            )
        if anexos:
            ContratoAnexo.objects.bulk_create(anexos)


def unseed_contratos(apps, schema_editor):
    # Reversao segura: nao apaga nada automaticamente.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0020_contrato_contratoanexo"),
    ]

    operations = [
        migrations.RunPython(seed_contratos, unseed_contratos),
    ]
