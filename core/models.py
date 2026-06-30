from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Chamado(models.Model):
    numero = models.CharField(max_length=30, unique=True)
    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    solicitante_nome = models.CharField(max_length=255, blank=True)
    solicitante_email = models.EmailField(blank=True)
    departamento = models.CharField(max_length=255, blank=True)
    categoria = models.CharField(max_length=120, blank=True)
    subcategoria = models.CharField(max_length=120, blank=True)
    prioridade = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=60, blank=True)
    origem = models.CharField(max_length=120, blank=True)
    aberto_em_referencia = models.CharField(max_length=60, blank=True)
    ultima_atualizacao_referencia = models.CharField(max_length=60, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["numero"]

    def __str__(self) -> str:
        return f"{self.numero} - {self.titulo}"


class AtendimentoHistorico(models.Model):
    TIPO_ENCERRAMENTO_PAUSE = "pause"
    TIPO_ENCERRAMENTO_STOP = "stop"
    TIPO_ENCERRAMENTO_CHOICES = [
        (TIPO_ENCERRAMENTO_PAUSE, "Pause"),
        (TIPO_ENCERRAMENTO_STOP, "Stop"),
    ]

    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name="atendimentos")
    atendente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="historico_atendimentos",
    )
    iniciado_em = models.DateTimeField()
    finalizado_em = models.DateTimeField(null=True, blank=True)
    duracao = models.DurationField(null=True, blank=True)
    tipo_encerramento = models.CharField(max_length=10, choices=TIPO_ENCERRAMENTO_CHOICES, blank=True)
    descricao_atividade = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-iniciado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["atendente"],
                condition=Q(finalizado_em__isnull=True),
                name="unique_active_attendance_per_user",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.atendente} - {self.chamado.numero}"

    @property
    def esta_ativo(self) -> bool:
        return self.finalizado_em is None

    def calcular_duracao(self) -> timedelta | None:
        if not self.finalizado_em:
            return None
        return max(self.finalizado_em - self.iniciado_em, timedelta())

    def clean(self):
        if self.finalizado_em and self.finalizado_em < self.iniciado_em:
            raise ValidationError("O fim do atendimento nao pode ser anterior ao inicio.")

        if self.finalizado_em and not self.tipo_encerramento:
            raise ValidationError("Informe o tipo de encerramento do atendimento.")

        if self.finalizado_em and not self.descricao_atividade.strip():
            raise ValidationError("Descreva o que foi feito antes de encerrar o atendimento.")

    def finalizar(self, *, tipo_encerramento: str, descricao_atividade: str):
        self.finalizado_em = timezone.now()
        self.tipo_encerramento = tipo_encerramento
        self.descricao_atividade = descricao_atividade.strip()
        self.duracao = self.calcular_duracao()
        self.full_clean()
