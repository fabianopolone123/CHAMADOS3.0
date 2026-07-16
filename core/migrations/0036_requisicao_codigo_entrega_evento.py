from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_codigos(apps, schema_editor):
    """Atribui codigos as requisicoes existentes, continuando do sistema antigo
    (ultimo REQ-00048), na ordem de criacao."""
    Requisicao = apps.get_model("core", "RequisicaoContrato")
    numero = 48  # ultimo codigo do sistema antigo
    for req in Requisicao.objects.filter(codigo__isnull=True).order_by("criado_em", "id"):
        numero += 1
        req.codigo = f"REQ-{numero:05d}"
        req.save(update_fields=["codigo"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0035_orcamentocontrato_aprovado"),
    ]

    operations = [
        migrations.AddField(
            model_name="requisicaocontrato",
            name="codigo",
            field=models.CharField(blank=True, max_length=24, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="requisicaocontrato",
            name="entregue_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="requisicaocontrato",
            name="entregue_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="requisicoes_entregues",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="requisicaocontrato",
            name="status",
            field=models.CharField(
                choices=[
                    ("aberta", "Aberta"),
                    ("em_cotacao", "Esperando aprovacao"),
                    ("aguardando_entrega", "Aguardando entrega"),
                    ("entregue", "Entregue"),
                    ("finalizada", "Finalizada"),
                    ("cancelada", "Cancelada"),
                ],
                default="aberta",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="RequisicaoContratoEvento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("criacao", "Criacao"), ("aprovacao", "Aprovacao de orcamento"), ("entrega", "Entrega"), ("status", "Mudanca de status")], max_length=20)),
                ("descricao", models.TextField()),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                (
                    "requisicao",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="eventos",
                        to="core.requisicaocontrato",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="eventos_requisicao",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Evento de requisicao",
                "verbose_name_plural": "Eventos de requisicao",
                "ordering": ["-criado_em", "-id"],
            },
        ),
        migrations.RunPython(backfill_codigos, noop),
    ]
