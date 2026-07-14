import json
from pathlib import Path

from django.conf import settings
from django.db import migrations


def seed_dicas(apps, schema_editor):
    """Cadastro inicial das dicas a partir de um arquivo LOCAL, ignorado pelo Git
    (`seed/dicas_seed.json`). Os anexos ficam em `media/dicas/` (tambem fora do
    Git). Se o arquivo nao existir, nao faz nada. Idempotente.
    """
    Dica = apps.get_model("core", "Dica")

    if Dica.objects.exists():
        return

    seed_path = Path(settings.BASE_DIR) / "seed" / "dicas_seed.json"
    if not seed_path.exists():
        return

    try:
        registros = json.loads(seed_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return

    categorias = {"geral", "configuracao", "resolucao"}
    media_root = Path(settings.MEDIA_ROOT)
    novas = []
    for reg in registros:
        categoria = reg.get("categoria") or "geral"
        if categoria not in categorias:
            categoria = "geral"
        anexo_nome = (reg.get("anexo") or "").strip()
        anexo_rel = ""
        if anexo_nome:
            caminho_rel = f"dicas/{anexo_nome}"
            if (media_root / caminho_rel).exists():
                anexo_rel = caminho_rel
        novas.append(
            Dica(
                categoria=categoria,
                titulo=reg.get("titulo", "") or "",
                conteudo=reg.get("conteudo", "") or "",
                anexo=anexo_rel,
            )
        )
    if novas:
        Dica.objects.bulk_create(novas)


def unseed_dicas(apps, schema_editor):
    # Reversao segura: nao apaga nada automaticamente.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0024_dica"),
    ]

    operations = [
        migrations.RunPython(seed_dicas, unseed_dicas),
    ]
