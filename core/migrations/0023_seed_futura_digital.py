import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.db import migrations


def _dec(valor, padrao="0"):
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(padrao)


def seed_futura(apps, schema_editor):
    """Cadastro inicial das faturas da Futura Digital a partir de um arquivo
    LOCAL, ignorado pelo Git (`seed/futura_digital_seed.json`). Os documentos
    (NFs/relatorios) ficam em `media/futura_digital/` (tambem fora do Git).

    Preserva os valores historicos exatos (copias_excedentes e valor_pago) como
    registrados no sistema antigo, sem recalcular. Idempotente.
    """
    FuturaDigital = apps.get_model("core", "FuturaDigital")

    if FuturaDigital.objects.exists():
        return

    seed_path = Path(settings.BASE_DIR) / "seed" / "futura_digital_seed.json"
    if not seed_path.exists():
        return

    try:
        registros = json.loads(seed_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return

    media_root = Path(settings.MEDIA_ROOT)
    for reg in registros:
        mes = reg.get("mes_referencia")
        if not mes:
            continue
        doc_nome = (reg.get("documento") or "").strip()
        doc_rel = ""
        if doc_nome:
            caminho_rel = f"futura_digital/{doc_nome}"
            if (media_root / caminho_rel).exists():
                doc_rel = caminho_rel

        FuturaDigital.objects.create(
            mes_referencia=mes,
            nota_fiscal=reg.get("nota_fiscal", "") or "",
            copias_total=int(reg.get("copias_total") or 0),
            copias_cor=int(reg.get("copias_cor") or 0),
            franquia_copias=int(reg.get("franquia_copias") or 23000),
            franquia_valor=_dec(reg.get("franquia_valor"), "1610.00"),
            valor_copia_excedente=_dec(reg.get("valor_copia_excedente"), "0.07"),
            valor_copia_cor=_dec(reg.get("valor_copia_cor"), "0.75"),
            copias_excedentes=int(reg.get("copias_excedentes") or 0),
            valor_pago=_dec(reg.get("valor_pago"), "0"),
            documento=doc_rel,
        )


def unseed_futura(apps, schema_editor):
    # Reversao segura: nao apaga nada automaticamente.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0022_futuradigital"),
    ]

    operations = [
        migrations.RunPython(seed_futura, unseed_futura),
    ]
