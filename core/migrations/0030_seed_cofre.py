import json
from pathlib import Path

from django.conf import settings
from django.db import migrations


def seed_cofre(apps, schema_editor):
    """Cadastro inicial das credenciais do cofre a partir de um arquivo LOCAL,
    ignorado pelo Git (`seed/cofre_seed.json`), com as SENHAS EM TEXTO. Aqui elas
    sao cifradas com a chave atual (VAULT_ENCRYPTION_KEY ou fallback de dev) e
    gravadas ja cifradas no banco.

    Nao define senha-mestra (o admin define no primeiro acesso). Se o arquivo nao
    existir (clone limpo/producao), nao faz nada. Idempotente.

    IMPORTANTE: apague `seed/cofre_seed.json` depois de semear (contem senhas em
    texto). Em producao, gere a VAULT_ENCRYPTION_KEY no servidor antes de semear.
    """
    CofreCredencial = apps.get_model("core", "CofreCredencial")

    if CofreCredencial.objects.exists():
        return

    seed_path = Path(settings.BASE_DIR) / "seed" / "cofre_seed.json"
    if not seed_path.exists():
        return

    try:
        registros = json.loads(seed_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return

    # Importa a funcao de cifra do app (nao ha metodo no modelo historico).
    from core.crypto import encrypt_text

    for reg in registros:
        rotulo = (reg.get("rotulo") or "").strip()
        if not rotulo:
            continue
        CofreCredencial.objects.create(
            rotulo=rotulo,
            usuario=reg.get("usuario", "") or "",
            senha_cifrada=encrypt_text(reg.get("senha", "") or ""),
            notas=reg.get("notas", "") or "",
        )


def unseed_cofre(apps, schema_editor):
    # Reversao segura: nao apaga nada automaticamente.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0029_cofreconfig_cofrecredencial_cofreauditoria"),
    ]

    operations = [
        migrations.RunPython(seed_cofre, unseed_cofre),
    ]
