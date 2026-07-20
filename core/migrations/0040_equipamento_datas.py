from django.db import migrations, models


def backfill_data_emprestimo(apps, schema_editor):
    """Preenche data_emprestimo de cada equipamento com a data do proprio
    emprestimo (equipamentos antigos foram cadastrados junto do emprestimo)."""
    Equipamento = apps.get_model("core", "EquipamentoEmprestimoTI")
    for equip in Equipamento.objects.select_related("emprestimo").all():
        if equip.data_emprestimo is None and equip.emprestimo and equip.emprestimo.data_emprestimo:
            equip.data_emprestimo = equip.emprestimo.data_emprestimo
            equip.save(update_fields=["data_emprestimo"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0039_alter_pendenciati_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="equipamentoemprestimoti",
            name="data_emprestimo",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="equipamentoemprestimoti",
            name="data_devolucao",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_data_emprestimo, migrations.RunPython.noop),
    ]
