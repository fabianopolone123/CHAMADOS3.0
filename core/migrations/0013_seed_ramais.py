import json
from pathlib import Path

from django.conf import settings
from django.db import migrations


def seed_ramais(apps, schema_editor):
    """Cadastro inicial dos ramais a partir de um arquivo LOCAL, ignorado pelo
    Git (`seed/ramais_seed.json`). Os dados sao pessoais (nomes, telefones e
    e-mails de colaboradores) e por isso NAO ficam versionados no repositorio.

    Se o arquivo nao existir (ex.: em um clone limpo/CI), a migracao apenas nao
    faz nada. Idempotente: nao duplica se ja houver ramais cadastrados.
    """
    Ramal = apps.get_model("core", "Ramal")
    ContaEmail = apps.get_model("core", "ContaEmail")

    if Ramal.objects.exists():
        return

    seed_path = Path(settings.BASE_DIR) / "seed" / "ramais_seed.json"
    if not seed_path.exists():
        return

    try:
        registros = json.loads(seed_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return

    contas = {c.email.lower(): c for c in ContaEmail.objects.all()}
    novos = []
    for reg in registros:
        email = (reg.get("email") or "").strip()
        novos.append(
            Ramal(
                colaborador=reg.get("colaborador", ""),
                setor=reg.get("setor", ""),
                telefone=reg.get("telefone", ""),
                ramal=reg.get("ramal", ""),
                email=email,
                conta_email=contas.get(email.lower()) if email else None,
            )
        )
    if novos:
        Ramal.objects.bulk_create(novos)


def unseed_ramais(apps, schema_editor):
    # Reversao segura: nao apaga nada automaticamente.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_ramal"),
    ]

    operations = [
        migrations.RunPython(seed_ramais, unseed_ramais),
    ]
