import json
from pathlib import Path

from django.conf import settings
from django.db import migrations


def seed_licencas(apps, schema_editor):
    """Cadastro inicial das licencas de software a partir de um arquivo LOCAL,
    ignorado pelo Git (`seed/licencas_seed.json`). Os dados contem seriais/
    product keys e nomes de colaboradores e por isso NAO ficam versionados.

    Se o arquivo nao existir (ex.: em um clone limpo/CI), a migracao apenas nao
    faz nada. Idempotente: nao duplica se ja houver softwares cadastrados.
    """
    LicencaSoftware = apps.get_model("core", "LicencaSoftware")
    Licenca = apps.get_model("core", "Licenca")

    if LicencaSoftware.objects.exists():
        return

    seed_path = Path(settings.BASE_DIR) / "seed" / "licencas_seed.json"
    if not seed_path.exists():
        return

    try:
        registros = json.loads(seed_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return

    tipos_validos = {"indeterminado", "expira_em"}
    for reg in registros:
        software = LicencaSoftware.objects.create(
            nome=reg.get("nome", ""),
            quantidade_licencas=reg.get("quantidade_licencas", 1) or 1,
            observacoes=reg.get("observacoes", "") or "",
        )
        licencas = []
        for lic in reg.get("licencas", []) or []:
            tipo = lic.get("tipo_expiracao") or "indeterminado"
            if tipo not in tipos_validos:
                tipo = "indeterminado"
            licencas.append(
                Licenca(
                    software=software,
                    serial=lic.get("serial", "") or "",
                    email_vinculado=lic.get("email_vinculado", "") or "",
                    tipo_expiracao=tipo,
                    expira_em=lic.get("expira_em") or None,
                    forma_pagamento=lic.get("forma_pagamento", "") or "",
                    final_cartao=lic.get("final_cartao", "") or "",
                    usuario_atribuido=lic.get("usuario_atribuido", "") or "",
                    observacoes=lic.get("observacoes", "") or "",
                )
            )
        if licencas:
            Licenca.objects.bulk_create(licencas)


def unseed_licencas(apps, schema_editor):
    # Reversao segura: nao apaga nada automaticamente.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_licencasoftware_licenca"),
    ]

    operations = [
        migrations.RunPython(seed_licencas, unseed_licencas),
    ]
