"""Renumera os codigos das requisicoes por ordem de criacao.

Correcao de dados solicitada: a requisicao mais recente (ultima cadastrada)
deve receber `REQ-00051` e as anteriores recebem os numeros decrescendo por
data de criacao (`REQ-00050`, `REQ-00049`, ...). Roda uma unica vez por banco
(no proximo deploy/migrate). Em um banco sem requisicoes (ex.: dev/clone limpo)
nao faz nada.

Como a numeracao futura em `RequisicaoContrato.gerar_codigo` parte sempre do
maior codigo existente, apos esta correcao a proxima requisicao cadastrada
continua naturalmente a partir de `REQ-00052`.
"""

from django.db import migrations

PREFIXO = "REQ-"
# A requisicao mais recente (ultima por data de criacao) recebe este numero.
CODIGO_TOPO = 51


def renumerar_codigos(apps, schema_editor):
    Requisicao = apps.get_model("core", "RequisicaoContrato")
    # Ordena da mais antiga para a mais recente; a ultima recebe CODIGO_TOPO.
    requisicoes = list(Requisicao.objects.order_by("criado_em", "id"))
    total = len(requisicoes)
    if total == 0:
        return

    inicio = CODIGO_TOPO - (total - 1)  # a mais antiga recebe (topo - total + 1)

    # Zera os codigos primeiro para nao colidir com o `unique` durante a troca
    # (o campo `codigo` aceita NULL).
    Requisicao.objects.update(codigo=None)

    for indice, requisicao in enumerate(requisicoes):
        numero = inicio + indice
        requisicao.codigo = f"{PREFIXO}{numero:05d}"
        requisicao.save(update_fields=["codigo"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0041_alter_requisicaocontratoevento_tipo"),
    ]

    operations = [
        migrations.RunPython(renumerar_codigos, migrations.RunPython.noop),
    ]
