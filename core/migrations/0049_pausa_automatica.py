import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0048_importa_atendimentos_legado'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chamadoevento',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('criacao', 'Criacao'),
                    ('mudanca_status', 'Mudanca de status'),
                    ('atendente_alterado', 'Atendente alterado'),
                    ('comentario', 'Comentario'),
                    ('encerramento_direto', 'Encerramento sem atendimento ativo'),
                    ('pausa_automatica', 'Pausa automatica no fim do expediente'),
                    ('complemento_pausa', 'Complemento da pausa automatica'),
                ],
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name='PausaAutomatica',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('complementado_em', models.DateTimeField(blank=True, null=True)),
                ('atendimento', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='pausa_automatica', to='core.atendimentohistorico')),
                ('complementado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pausas_complementadas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Pausa automatica',
                'verbose_name_plural': 'Pausas automaticas',
                'ordering': ['criado_em', 'id'],
            },
        ),
    ]
