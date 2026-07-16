from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0034_retiradainsumoti_tipo_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='orcamentocontrato',
            name='aprovado',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='orcamentocontrato',
            name='aprovado_em',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='orcamentocontrato',
            name='aprovado_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='orcamentos_aprovados',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
