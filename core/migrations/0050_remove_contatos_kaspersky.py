"""Apaga as tabelas dos modulos Contatos e Kaspersky, removidos para serem
refeitos do zero.

ATENCAO: e destrutivo e sem volta. Ao aplicar, vao embora os dados importados -
na base de producao eram 83 computadores do GLPI, 44 dispositivos do Kaspersky e
os vinculos colaborador/computador feitos a mao. Foi uma decisao consciente
("comecar do zero"); o backup de 30/07/2026 ficou em
`/opt/chamados/db.sqlite3.bak-antes-drop-20260730-131201`.

Quando os modulos forem refeitos, os arquivos de origem (CSV do GLPI e export.txt
do Kaspersky) reconstroem a lista - o que nao volta sao os ajustes manuais.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0049_pausa_automatica'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='computador',
            name='ramal',
        ),
        migrations.DeleteModel(
            name='KasperskyConfig',
        ),
        migrations.RemoveField(
            model_name='kasperskydispositivo',
            name='ramal',
        ),
        migrations.DeleteModel(
            name='Computador',
        ),
        migrations.DeleteModel(
            name='KasperskyDispositivo',
        ),
    ]
