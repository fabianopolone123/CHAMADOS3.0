import json
from pathlib import Path

from django.conf import settings
from django.db import migrations


def seed_starlinks(apps, schema_editor):
    """Cadastro inicial das Starlinks a partir de um arquivo LOCAL, ignorado pelo
    Git (`seed/starlinks_seed.json`). Contem credenciais (e-mail/senha) e por isso
    NAO fica versionado. Se o arquivo nao existir, nao faz nada. Idempotente.
    """
    Starlink = apps.get_model("core", "Starlink")

    if Starlink.objects.exists():
        return

    seed_path = Path(settings.BASE_DIR) / "seed" / "starlinks_seed.json"
    if not seed_path.exists():
        return

    try:
        registros = json.loads(seed_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return

    formas = {"pix", "cartao"}
    novas = []
    for reg in registros:
        forma = reg.get("forma_pagamento") or "cartao"
        if forma not in formas:
            forma = "cartao"
        novas.append(
            Starlink(
                nome=reg.get("nome", "") or "",
                local=reg.get("local", "") or "",
                email=reg.get("email", "") or "",
                senha=reg.get("senha", "") or "",
                ativo=bool(reg.get("ativo", True)),
                forma_pagamento=forma,
                final_cartao=(reg.get("final_cartao", "") or "")[:4],
                identificador=reg.get("identificador", "") or "",
                versao_software=reg.get("versao_software", "") or "",
                numero_serie=reg.get("numero_serie", "") or "",
                numero_kit=reg.get("numero_kit", "") or "",
            )
        )
    if novas:
        Starlink.objects.bulk_create(novas)


def unseed_starlinks(apps, schema_editor):
    # Reversao segura: nao apaga nada automaticamente.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0026_starlink"),
    ]

    operations = [
        migrations.RunPython(seed_starlinks, unseed_starlinks),
    ]
