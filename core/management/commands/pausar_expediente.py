"""Pausa em lote os atendimentos que ficaram com o Play aberto no fim do expediente.

Rodado por agendador (cron/systemd timer) no horario de encerramento (17:45 por
padrao). Fecha todo `AtendimentoHistorico` ativo, **sem descricao**, e cria uma
`PausaAutomatica` pendente: no proximo acesso o atendente e obrigado a dizer o que
foi feito naquele periodo antes de voltar a usar o Play/Pause/Stop.

Por que existe: sem isso, um Play esquecido aberto conta a noite e o fim de semana
como tempo trabalhado. Na base de producao havia 14 periodos de mais de 24h - o
maior com 7 dias (169h) - inflando o relatorio mensal.

Uso:

    python manage.py pausar_expediente                 # usa 17:45 de hoje
    python manage.py pausar_expediente --hora 18:00
    python manage.py pausar_expediente --dry-run       # so mostra o que faria
"""

from __future__ import annotations

from datetime import datetime, time

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import AtendimentoHistorico, Chamado, ChamadoEvento, PausaAutomatica

HORA_PADRAO = time(17, 45)

MENSAGEM_EVENTO = (
    "Atendimento pausado automaticamente no fim do expediente ({hora}). "
    "Pendente de complemento no proximo acesso."
)


class Command(BaseCommand):
    help = "Pausa os atendimentos com Play aberto no fim do expediente e abre a pendencia de complemento."

    def add_arguments(self, parser):
        parser.add_argument(
            "--hora",
            default=HORA_PADRAO.strftime("%H:%M"),
            help="Horario de encerramento do expediente (HH:MM). Padrao: 17:45.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas lista o que seria pausado, sem gravar.",
        )

    def handle(self, *args, **opcoes):
        try:
            hora = datetime.strptime(opcoes["hora"], "%H:%M").time()
        except (TypeError, ValueError):
            raise CommandError("Horario invalido. Use HH:MM (ex.: 17:45).")

        # O corte usa o horario do expediente, nao a hora em que o comando rodou:
        # um cron que dispara as 17:45:03 ainda grava o fim exatamente em 17:45.
        agora = timezone.localtime()
        corte = agora.replace(hour=hora.hour, minute=hora.minute, second=0, microsecond=0)

        ativos = list(
            AtendimentoHistorico.objects.filter(finalizado_em__isnull=True)
            .select_related("chamado", "atendente")
            .order_by("iniciado_em")
        )
        if not ativos:
            self.stdout.write("Nenhum atendimento aberto: nada a pausar.")
            return

        pausados = 0
        for atendimento in ativos:
            # Play iniciado DEPOIS do corte (alguem trabalhando fora do horario):
            # nao pausa, senao o fim ficaria antes do inicio.
            if atendimento.iniciado_em >= corte:
                self.stdout.write(
                    f"  - {atendimento.chamado.numero}: Play iniciado apos {opcoes['hora']}, mantido aberto."
                )
                continue

            rotulo = f"{atendimento.chamado.numero} ({atendimento.atendente})"
            if opcoes["dry_run"]:
                inicio = timezone.localtime(atendimento.iniciado_em)
                self.stdout.write(f"  [dry-run] pausaria {rotulo}: {inicio:%d/%m %H:%M} -> {corte:%H:%M}")
                pausados += 1
                continue

            with transaction.atomic():
                atendimento.finalizado_em = corte
                atendimento.tipo_encerramento = AtendimentoHistorico.TIPO_ENCERRAMENTO_PAUSE
                atendimento.duracao = atendimento.calcular_duracao()
                # Sem descricao de proposito: e o que o atendente vai complementar.
                atendimento.save(
                    update_fields=["finalizado_em", "tipo_encerramento", "duracao", "atualizado_em"]
                )

                chamado = atendimento.chamado
                # A pausa automatica nao e espera por terceiros: o chamado volta a
                # ser so "Atribuido" ao atendente.
                if chamado.status == Chamado.STATUS_EM_ATENDIMENTO:
                    chamado.status = Chamado.STATUS_ATRIBUIDO
                    chamado.save(update_fields=["status", "atualizado_em"])

                ChamadoEvento.registrar(
                    chamado=chamado,
                    usuario=atendimento.atendente,
                    tipo=ChamadoEvento.TIPO_PAUSA_AUTOMATICA,
                    descricao=MENSAGEM_EVENTO.format(hora=opcoes["hora"]),
                )
                PausaAutomatica.objects.get_or_create(atendimento=atendimento)

            self.stdout.write(self.style.SUCCESS(f"  - pausado {rotulo}"))
            pausados += 1

        resumo = f"{pausados} atendimento(s) pausado(s) no fim do expediente ({opcoes['hora']})."
        if opcoes["dry_run"]:
            resumo = f"[dry-run] {resumo} Nada foi gravado."
        self.stdout.write(self.style.SUCCESS(resumo))
