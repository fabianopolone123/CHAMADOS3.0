import json
from pathlib import Path

from django.conf import settings
from django.db import migrations


def seed_ips(apps, schema_editor):
    """Cadastro inicial dos IPs a partir de um arquivo LOCAL, ignorado pelo Git
    (`seed/ips_seed.json`). Os dados contem MACs e credenciais de acesso da rede
    interna e por isso NAO ficam versionados no repositorio.

    Se o arquivo nao existir (ex.: em um clone limpo/CI), a migracao apenas nao
    faz nada. Idempotente: nao duplica se ja houver IPs cadastrados.
    """
    EnderecoIP = apps.get_model("core", "EnderecoIP")

    if EnderecoIP.objects.exists():
        return

    seed_path = Path(settings.BASE_DIR) / "seed" / "ips_seed.json"
    if not seed_path.exists():
        return

    try:
        registros = json.loads(seed_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return

    categorias_validas = {
        "servers", "switches", "idface_turnstiles", "printers", "wifi", "monitoring",
    }
    vistos = set()
    novos = []
    for reg in registros:
        ip = (reg.get("endereco_ip") or "").strip()
        if not ip or ip in vistos:
            continue
        vistos.add(ip)
        categoria = reg.get("categoria") or "servers"
        if categoria not in categorias_validas:
            categoria = "servers"
        novos.append(
            EnderecoIP(
                categoria=categoria,
                endereco_ip=ip,
                nome=reg.get("nome", "") or "",
                fabricante=reg.get("fabricante", "") or "",
                mac=reg.get("mac", "") or "",
                acesso=reg.get("acesso", "") or "",
                observacoes=reg.get("observacoes", "") or "",
            )
        )
    if novos:
        EnderecoIP.objects.bulk_create(novos)


def unseed_ips(apps, schema_editor):
    # Reversao segura: nao apaga nada automaticamente.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0016_enderecoip"),
    ]

    operations = [
        migrations.RunPython(seed_ips, unseed_ips),
    ]
