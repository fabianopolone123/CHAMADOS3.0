from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0036_requisicao_codigo_entrega_evento"),
    ]

    operations = [
        migrations.AddField(
            model_name="pendenciati",
            name="prioridade",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (1, "Urgente"),
                    (2, "Alta"),
                    (3, "Media"),
                    (4, "Baixa"),
                    (5, "Minima"),
                ],
                default=3,
                help_text="1 = mais urgente (vermelho), 5 = menos urgente (verde).",
            ),
        ),
    ]
