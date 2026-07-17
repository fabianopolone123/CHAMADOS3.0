from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Chamado(models.Model):
    STATUS_ABERTO = "aberto"
    STATUS_ATRIBUIDO = "atribuido"
    STATUS_EM_ATENDIMENTO = "em_atendimento"
    STATUS_AGUARDANDO_USUARIO = "aguardando_usuario"
    STATUS_AGUARDANDO_PECA = "aguardando_peca"
    STATUS_AGUARDANDO_AUTORIZACAO = "aguardando_autorizacao"
    STATUS_RESOLVIDO = "resolvido"
    STATUS_FECHADO = "fechado"
    STATUS_CHOICES = [
        (STATUS_ABERTO, "Aberto"),
        (STATUS_ATRIBUIDO, "Atribuido"),
        (STATUS_EM_ATENDIMENTO, "Em atendimento"),
        (STATUS_AGUARDANDO_USUARIO, "Aguardando usuario"),
        (STATUS_AGUARDANDO_PECA, "Aguardando peca"),
        (STATUS_AGUARDANDO_AUTORIZACAO, "Aguardando autorizacao"),
        (STATUS_RESOLVIDO, "Resolvido"),
        (STATUS_FECHADO, "Fechado"),
    ]
    STATUS_ENCERRADOS = {STATUS_RESOLVIDO, STATUS_FECHADO}
    # Status de "aguardando" que uma pausa pode marcar.
    STATUS_AGUARDANDO = {STATUS_AGUARDANDO_USUARIO, STATUS_AGUARDANDO_PECA, STATUS_AGUARDANDO_AUTORIZACAO}

    PRIORIDADE_BAIXA = "baixa"
    PRIORIDADE_MEDIA = "media"
    PRIORIDADE_ALTA = "alta"
    PRIORIDADE_CRITICA = "critica"
    PRIORIDADE_CHOICES = [
        (PRIORIDADE_BAIXA, "Baixa"),
        (PRIORIDADE_MEDIA, "Media"),
        (PRIORIDADE_ALTA, "Alta"),
        (PRIORIDADE_CRITICA, "Critica"),
    ]

    NUMERO_PREFIXO = "CH-"

    numero = models.CharField(max_length=30, unique=True)
    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chamados_abertos",
    )
    solicitante_nome = models.CharField(max_length=255, blank=True)
    solicitante_email = models.EmailField(blank=True)
    departamento = models.CharField(max_length=255, blank=True)
    categoria = models.CharField(max_length=120, blank=True)
    subcategoria = models.CharField(max_length=120, blank=True)
    prioridade = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=60, blank=True, default=STATUS_ABERTO)
    atendente_atual = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chamados_em_atendimento",
        help_text="Atendente que realizou a ultima acao no chamado. Nao representa dono do chamado.",
    )
    origem = models.CharField(max_length=120, blank=True)
    aberto_em_referencia = models.CharField(max_length=60, blank=True)
    ultima_atualizacao_referencia = models.CharField(max_length=60, blank=True)
    fechado_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["numero"]

    def __str__(self) -> str:
        return f"{self.numero} - {self.titulo}"

    @classmethod
    def gerar_numero(cls) -> str:
        """Gera um numero sequencial unico no formato CH-000123."""
        ultimo = (
            cls.objects.filter(numero__startswith=cls.NUMERO_PREFIXO)
            .order_by("-numero")
            .values_list("numero", flat=True)
            .first()
        )
        proximo = 1
        if ultimo:
            try:
                proximo = int(ultimo.replace(cls.NUMERO_PREFIXO, "")) + 1
            except ValueError:
                proximo = cls.objects.count() + 1
        return f"{cls.NUMERO_PREFIXO}{proximo:06d}"

    @property
    def status_label(self) -> str:
        return dict(self.STATUS_CHOICES).get(self.status, self.status or "-")

    @property
    def prioridade_label(self) -> str:
        return dict(self.PRIORIDADE_CHOICES).get(self.prioridade, self.prioridade or "-")


def anexo_upload_path(instance, filename):
    """Organiza os anexos por chamado dentro de MEDIA_ROOT."""
    numero = instance.chamado.numero or "sem-numero"
    return f"chamados/{numero}/{filename}"


class ChamadoAnexo(models.Model):
    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name="anexos")
    arquivo = models.FileField(upload_to=anexo_upload_path)
    nome_original = models.CharField(max_length=255, blank=True)
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="anexos_enviados",
    )
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["enviado_em"]

    def __str__(self) -> str:
        return f"{self.chamado.numero} - {self.nome_original or self.arquivo.name}"


def mensagem_anexo_upload_path(instance, filename):
    """Organiza os anexos de mensagens por chamado dentro de MEDIA_ROOT."""
    numero = instance.mensagem.chamado.numero or "sem-numero"
    return f"chamados/{numero}/mensagens/{filename}"


class ChamadoMensagem(models.Model):
    """Mensagem da conversa entre solicitante e Atendente TI dentro de um chamado.

    A conversa e separada do historico tecnico (`ChamadoEvento`): aqui fica o
    conteudo trocado; la fica apenas o resumo da acao.
    """

    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name="mensagens")
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mensagens_chamado",
    )
    texto = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em", "id"]

    def __str__(self) -> str:
        return f"{self.chamado.numero} - mensagem #{self.pk}"


class ChamadoMensagemAnexo(models.Model):
    """Arquivo opcional vinculado a uma mensagem da conversa do chamado."""

    mensagem = models.ForeignKey(ChamadoMensagem, on_delete=models.CASCADE, related_name="anexos")
    arquivo = models.FileField(upload_to=mensagem_anexo_upload_path)
    nome_original = models.CharField(max_length=255, blank=True)
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["enviado_em"]

    def __str__(self) -> str:
        return f"{self.mensagem.chamado.numero} - {self.nome_original or self.arquivo.name}"


class ChamadoEvento(models.Model):
    """Log de eventos/acoes de um chamado ao longo da sua vida."""

    TIPO_CRIACAO = "criacao"
    TIPO_STATUS = "mudanca_status"
    TIPO_ATENDENTE = "atendente_alterado"
    TIPO_COMENTARIO = "comentario"
    TIPO_CHOICES = [
        (TIPO_CRIACAO, "Criacao"),
        (TIPO_STATUS, "Mudanca de status"),
        (TIPO_ATENDENTE, "Atendente alterado"),
        (TIPO_COMENTARIO, "Comentario"),
    ]

    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name="eventos")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_chamado",
    )
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    descricao = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em", "id"]

    def __str__(self) -> str:
        return f"{self.chamado.numero} - {self.tipo}"

    @classmethod
    def registrar(cls, *, chamado, usuario, tipo, descricao):
        return cls.objects.create(chamado=chamado, usuario=usuario, tipo=tipo, descricao=descricao)


class PendenciaTI(models.Model):
    """Pendencia da equipe de TI no Kanban, convertivel em chamado ao ser
    arrastada para a coluna de um atendente. Mantida como rastro apos a
    conversao (marcada como convertida, nao apagada)."""

    # Escala de prioridade por cor: 1 = mais urgente (vermelho) ... 5 = menos
    # urgente (verde). Cada nivel guarda rotulo e cor (fonte unica de verdade,
    # usada no card, nos swatches e na API).
    PRIORIDADES = (
        (1, "Urgente", "#dc3545"),
        (2, "Alta", "#fd7e14"),
        (3, "Media", "#f5c518"),
        (4, "Baixa", "#7cb342"),
        (5, "Minima", "#2e9e5b"),
    )
    PRIORIDADE_CHOICES = tuple((valor, rotulo) for valor, rotulo, _cor in PRIORIDADES)
    PRIORIDADE_CORES = {valor: cor for valor, _rotulo, cor in PRIORIDADES}
    PRIORIDADE_PADRAO = 3

    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    prioridade = models.PositiveSmallIntegerField(
        choices=PRIORIDADE_CHOICES,
        default=PRIORIDADE_PADRAO,
        help_text="1 = mais urgente (vermelho), 5 = menos urgente (verde).",
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pendencias_criadas",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    convertido_em_chamado = models.BooleanField(default=False)
    chamado_gerado = models.ForeignKey(
        Chamado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pendencias_origem",
    )
    convertido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pendencias_convertidas",
    )
    convertido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        # Mais urgentes (prioridade menor = vermelho) no topo; dentro do mesmo
        # nivel, os mais recentes primeiro.
        ordering = ["prioridade", "-criado_em", "-id"]

    def __str__(self) -> str:
        return f"Pendencia #{self.pk} - {self.titulo}"

    @property
    def cor(self) -> str:
        return self.PRIORIDADE_CORES.get(
            self.prioridade, self.PRIORIDADE_CORES[self.PRIORIDADE_PADRAO]
        )

    @property
    def prioridade_label(self) -> str:
        return dict(self.PRIORIDADE_CHOICES).get(self.prioridade, "")

    @classmethod
    def prioridade_opcoes(cls):
        """Lista de niveis para renderizar os swatches nos modais."""
        return [
            {"valor": valor, "rotulo": rotulo, "cor": cor}
            for valor, rotulo, cor in cls.PRIORIDADES
        ]


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
        # Um atendente pode ter varios atendimentos ativos ao mesmo tempo (Play em
        # mais de um chamado). A unicidade e apenas por (atendente, chamado) ativo,
        # garantida na view (nao duplica Play no mesmo chamado).

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


# ==========================================================================
# Modulo Contratos: requisicoes, orcamentos e suborcamentos (complementos)
# ==========================================================================


class RequisicaoContrato(models.Model):
    """Requisicao de contrato/compra. Agrupa varios orcamentos."""

    TIPO_FISICA = "fisica"
    TIPO_DIGITAL = "digital"
    TIPO_CHOICES = [
        (TIPO_FISICA, "Fisica"),
        (TIPO_DIGITAL, "Digital"),
    ]

    STATUS_ABERTA = "aberta"
    STATUS_EM_COTACAO = "em_cotacao"
    STATUS_AGUARDANDO_ENTREGA = "aguardando_entrega"
    STATUS_ENTREGUE = "entregue"
    STATUS_FINALIZADA = "finalizada"
    STATUS_CANCELADA = "cancelada"
    STATUS_CHOICES = [
        (STATUS_ABERTA, "Aberta"),
        (STATUS_EM_COTACAO, "Esperando aprovacao"),
        (STATUS_AGUARDANDO_ENTREGA, "Aguardando entrega"),
        (STATUS_ENTREGUE, "Entregue"),
        (STATUS_FINALIZADA, "Finalizada"),
        (STATUS_CANCELADA, "Cancelada"),
    ]

    # Codigo sequencial (REQ-00049, ...). Continua a numeracao do sistema antigo,
    # que parou em REQ-00048; por isso as novas requisicoes comecam em 49.
    CODIGO_PREFIXO = "REQ-"
    CODIGO_BASE_ANTERIOR = 48

    codigo = models.CharField(max_length=24, unique=True, null=True, blank=True)
    titulo = models.CharField(max_length=255)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default=TIPO_FISICA)
    texto = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ABERTA)
    entregue_em = models.DateTimeField(null=True, blank=True)
    entregue_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requisicoes_entregues",
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requisicoes_contrato",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em", "-id"]

    def __str__(self) -> str:
        return f"{self.codigo or 'REQ'} - {self.titulo}"

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        # Gera o codigo apos o insert (idempotente): so quando ainda nao existe.
        if creating and not self.codigo:
            codigo = self.gerar_codigo()
            type(self).objects.filter(pk=self.pk).update(codigo=codigo)
            self.codigo = codigo

    @classmethod
    def gerar_codigo(cls) -> str:
        """Proximo codigo sequencial, continuando do sistema antigo (REQ-00049...)."""
        ultimo = cls.CODIGO_BASE_ANTERIOR
        for codigo in cls.objects.filter(codigo__startswith=cls.CODIGO_PREFIXO).values_list(
            "codigo", flat=True
        ):
            try:
                ultimo = max(ultimo, int((codigo or "").replace(cls.CODIGO_PREFIXO, "")))
            except (TypeError, ValueError):
                continue
        return f"{cls.CODIGO_PREFIXO}{ultimo + 1:05d}"

    @property
    def status_label(self) -> str:
        return dict(self.STATUS_CHOICES).get(self.status, self.status or "-")

    @property
    def tipo_label(self) -> str:
        return dict(self.TIPO_CHOICES).get(self.tipo, self.tipo or "-")


class RequisicaoContratoEvento(models.Model):
    """Historico/timeline de uma requisicao (criacao, aprovacao, entrega, etc.)."""

    TIPO_CRIACAO = "criacao"
    TIPO_APROVACAO = "aprovacao"
    TIPO_ENTREGA = "entrega"
    TIPO_STATUS = "status"
    TIPO_CHOICES = [
        (TIPO_CRIACAO, "Criacao"),
        (TIPO_APROVACAO, "Aprovacao de orcamento"),
        (TIPO_ENTREGA, "Entrega"),
        (TIPO_STATUS, "Mudanca de status"),
    ]

    requisicao = models.ForeignKey(
        RequisicaoContrato, on_delete=models.CASCADE, related_name="eventos"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_requisicao",
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descricao = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em", "-id"]
        verbose_name = "Evento de requisicao"
        verbose_name_plural = "Eventos de requisicao"

    def __str__(self) -> str:
        return f"{self.requisicao_id} - {self.tipo}"

    @classmethod
    def registrar(cls, *, requisicao, usuario, tipo, descricao):
        return cls.objects.create(
            requisicao=requisicao, usuario=usuario, tipo=tipo, descricao=descricao
        )


class _ItemOrcamentoBase(models.Model):
    """Campos e regras de calculo comuns a orcamento e suborcamento.

    Regra de calculo:
    - subtotal = valor * quantidade
    - total    = subtotal + frete - desconto
    """

    MOEDA_BRL = "BRL"
    MOEDA_USD = "USD"
    MOEDA_CHOICES = [
        (MOEDA_BRL, "Real (BRL)"),
        (MOEDA_USD, "Dolar (USD)"),
    ]

    titulo = models.CharField(max_length=255)
    loja = models.CharField(max_length=255, blank=True)
    moeda = models.CharField(max_length=3, choices=MOEDA_CHOICES, default=MOEDA_BRL)
    valor = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(Decimal("0"))]
    )
    quantidade = models.PositiveIntegerField(default=1)
    frete = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(Decimal("0"))]
    )
    desconto = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(Decimal("0"))]
    )
    link = models.URLField(max_length=1000, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    @property
    def subtotal(self) -> Decimal:
        return (self.valor or Decimal("0")) * (self.quantidade or 0)

    @property
    def total(self) -> Decimal:
        return self.subtotal + (self.frete or Decimal("0")) - (self.desconto or Decimal("0"))


def orcamento_foto_path(instance, filename):
    return f"contratos/orcamentos/{instance.pk or 'novo'}/foto/{filename}"


def orcamento_doc_path(instance, filename):
    return f"contratos/orcamentos/{instance.orcamento_id}/docs/{filename}"


def suborcamento_foto_path(instance, filename):
    return f"contratos/suborcamentos/{instance.pk or 'novo'}/foto/{filename}"


def suborcamento_doc_path(instance, filename):
    return f"contratos/suborcamentos/{instance.suborcamento_id}/docs/{filename}"


class OrcamentoContrato(_ItemOrcamentoBase):
    """Orcamento principal vinculado a uma requisicao. Pode ter suborcamentos."""

    requisicao = models.ForeignKey(
        RequisicaoContrato, on_delete=models.CASCADE, related_name="orcamentos"
    )
    foto_produto = models.ImageField(upload_to=orcamento_foto_path, null=True, blank=True)
    aprovado = models.BooleanField(default=False)
    aprovado_em = models.DateTimeField(null=True, blank=True)
    aprovado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orcamentos_aprovados",
    )

    class Meta:
        ordering = ["criado_em", "id"]

    def __str__(self) -> str:
        return f"{self.titulo} ({self.requisicao_id})"

    @property
    def total_suborcamentos(self) -> Decimal:
        return sum((sub.total for sub in self.suborcamentos.all()), Decimal("0"))

    @property
    def total_com_suborcamentos(self) -> Decimal:
        """Total do orcamento principal somado ao total de todos os suborcamentos."""
        return self.total + self.total_suborcamentos


class OrcamentoDocumento(models.Model):
    orcamento = models.ForeignKey(
        OrcamentoContrato, on_delete=models.CASCADE, related_name="documentos"
    )
    arquivo = models.FileField(upload_to=orcamento_doc_path)
    nome_original = models.CharField(max_length=255, blank=True)
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["enviado_em", "id"]

    def __str__(self) -> str:
        return self.nome_original or self.arquivo.name


class SuborcamentoContrato(_ItemOrcamentoBase):
    """Complemento de um orcamento principal. Nao aparece como orcamento independente."""

    orcamento_pai = models.ForeignKey(
        OrcamentoContrato, on_delete=models.CASCADE, related_name="suborcamentos"
    )
    foto_produto = models.ImageField(upload_to=suborcamento_foto_path, null=True, blank=True)

    class Meta:
        ordering = ["criado_em", "id"]

    def __str__(self) -> str:
        return f"{self.titulo} (sub de {self.orcamento_pai_id})"


class SuborcamentoDocumento(models.Model):
    suborcamento = models.ForeignKey(
        SuborcamentoContrato, on_delete=models.CASCADE, related_name="documentos"
    )
    arquivo = models.FileField(upload_to=suborcamento_doc_path)
    nome_original = models.CharField(max_length=255, blank=True)
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["enviado_em", "id"]

    def __str__(self) -> str:
        return self.nome_original or self.arquivo.name


# ==========================================================================
# Modulo Insumos: controle simples de estoque e retirada de materiais de TI
# ==========================================================================


class InsumoTI(models.Model):
    """Item de estoque de TI (teclados, mouses, cabos, adaptadores, etc.)."""

    # Abaixo (ou igual a) este valor, o insumo entra em "baixo estoque".
    LIMITE_BAIXO_ESTOQUE = 5

    STATUS_DISPONIVEL = "disponivel"
    STATUS_BAIXO = "baixo"
    STATUS_ZERADO = "zerado"

    nome = models.CharField(max_length=255)
    descricao = models.CharField(max_length=255, blank=True)
    quantidade_atual = models.PositiveIntegerField(default=0)
    observacao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="insumos_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome", "id"]

    def __str__(self) -> str:
        return f"{self.nome} ({self.quantidade_atual})"

    @property
    def status_estoque(self) -> str:
        if self.quantidade_atual <= 0:
            return self.STATUS_ZERADO
        if self.quantidade_atual <= self.LIMITE_BAIXO_ESTOQUE:
            return self.STATUS_BAIXO
        return self.STATUS_DISPONIVEL

    @property
    def status_label(self) -> str:
        return {
            self.STATUS_DISPONIVEL: "Disponivel",
            self.STATUS_BAIXO: "Baixo estoque",
            self.STATUS_ZERADO: "Sem estoque",
        }.get(self.status_estoque, "Disponivel")


class RetiradaInsumoTI(models.Model):
    """Movimentacao de estoque de um insumo (extrato): entrada (+) ou saida (-)."""

    TIPO_ENTRADA = "entrada"
    TIPO_SAIDA = "saida"
    TIPO_CHOICES = [
        (TIPO_ENTRADA, "Entrada"),
        (TIPO_SAIDA, "Saida"),
    ]

    insumo = models.ForeignKey(InsumoTI, on_delete=models.CASCADE, related_name="retiradas")
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default=TIPO_SAIDA)
    quantidade = models.PositiveIntegerField()
    entregue_para = models.CharField(max_length=255, blank=True)
    motivo = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="retiradas_registradas",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em", "-id"]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} {self.quantidade}x {self.insumo.nome}"

    @property
    def tipo_label(self) -> str:
        return dict(self.TIPO_CHOICES).get(self.tipo, self.tipo or "-")


# ==========================================================================
# Modulo Documentos: cadastro e armazenamento de documentos internos
# ==========================================================================


class DocumentoTI(models.Model):
    """Cadastro de um documento interno, com um ou mais anexos vinculados."""

    nome = models.CharField(max_length=255)
    observacao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_ti_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em", "-id"]

    def __str__(self) -> str:
        return self.nome


def documento_ti_anexo_path(instance, filename):
    return f"documentos/{instance.documento_id}/{filename}"


class DocumentoTIAnexo(models.Model):
    documento = models.ForeignKey(DocumentoTI, on_delete=models.CASCADE, related_name="anexos")
    arquivo = models.FileField(upload_to=documento_ti_anexo_path)
    nome_original = models.CharField(max_length=255, blank=True)
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_ti_anexos_enviados",
    )
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["enviado_em", "id"]

    def __str__(self) -> str:
        return self.nome_original or self.arquivo.name


# ==========================================================================
# Modulo Emprestimos: comodato de equipamentos de TI com termo em PDF
# ==========================================================================


def assinatura_upload_path(instance, filename):
    return f"emprestimos/assinaturas/{instance.pk or 'nova'}/{filename}"


class AssinaturaResponsavelTI(models.Model):
    """Assinatura cadastrada de um responsavel de TI, protegida por senha.

    A senha de autorizacao e guardada como hash (Django), nunca em texto puro.
    """

    nome_responsavel = models.CharField(max_length=255)
    imagem_assinatura = models.ImageField(upload_to=assinatura_upload_path, null=True, blank=True)
    senha_hash = models.CharField(max_length=255)
    ativo = models.BooleanField(default=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assinaturas_ti_criadas",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome_responsavel", "id"]

    def __str__(self) -> str:
        return self.nome_responsavel

    def set_senha(self, senha_plana: str) -> None:
        from django.contrib.auth.hashers import make_password

        self.senha_hash = make_password(senha_plana)

    def conferir_senha(self, senha_plana: str) -> bool:
        from django.contrib.auth.hashers import check_password

        if not self.senha_hash:
            return False
        return check_password(senha_plana, self.senha_hash)


def termo_pdf_upload_path(instance, filename):
    return f"emprestimos/{instance.pk}/termo/{filename}"


def termo_assinado_upload_path(instance, filename):
    return f"emprestimos/{instance.pk}/assinado/{filename}"


class EmprestimoTI(models.Model):
    """Emprestimo (comodato) de um ou mais equipamentos de TI a um colaborador."""

    STATUS_AGUARDANDO = "aguardando"
    STATUS_ASSINADA_OK = "assinada_ok"
    STATUS_EM_ANDAMENTO = "em_andamento"
    STATUS_DEVOLVIDO = "devolvido"
    STATUS_CANCELADO = "cancelado"
    STATUS_CHOICES = [
        (STATUS_AGUARDANDO, "Aguardando documentacao assinada"),
        (STATUS_ASSINADA_OK, "Documentacao assinada / OK"),
        (STATUS_EM_ANDAMENTO, "Em andamento"),
        (STATUS_DEVOLVIDO, "Devolvido"),
        (STATUS_CANCELADO, "Cancelado"),
    ]

    colaborador_nome = models.CharField(max_length=255)
    empresa = models.CharField(max_length=255, blank=True)
    cpf = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=40, blank=True)
    data_emprestimo = models.DateField()
    previsao_devolucao = models.DateField(null=True, blank=True)
    prazo_indeterminado = models.BooleanField(default=False)
    observacoes_internas = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AGUARDANDO)
    assinatura_responsavel = models.ForeignKey(
        AssinaturaResponsavelTI,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emprestimos",
    )
    termo_pdf = models.FileField(upload_to=termo_pdf_upload_path, null=True, blank=True)
    termo_assinado = models.FileField(upload_to=termo_assinado_upload_path, null=True, blank=True)
    termo_assinado_ok = models.BooleanField(default=False)
    termo_assinado_em = models.DateTimeField(null=True, blank=True)
    termo_assinado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emprestimos_termo_anexado",
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emprestimos_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em", "-id"]

    def __str__(self) -> str:
        return f"Emprestimo #{self.pk} - {self.colaborador_nome}"

    @property
    def status_label(self) -> str:
        return dict(self.STATUS_CHOICES).get(self.status, self.status or "-")

    @property
    def devolucao_display(self) -> str:
        if self.prazo_indeterminado or not self.previsao_devolucao:
            return "Indeterminada"
        return self.previsao_devolucao.strftime("%d/%m/%Y")


class EquipamentoEmprestimoTI(models.Model):
    emprestimo = models.ForeignKey(
        EmprestimoTI, on_delete=models.CASCADE, related_name="equipamentos"
    )
    tipo_equipamento = models.CharField(max_length=255)
    marca = models.CharField(max_length=255, blank=True)
    modelo = models.CharField(max_length=255, blank=True)
    numero_serie = models.CharField(max_length=255, blank=True)
    patrimonio_etiqueta = models.CharField(max_length=255, blank=True)
    acessorios_entregues = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.tipo_equipamento} ({self.marca} {self.modelo})".strip()

    @property
    def descricao_completa(self) -> str:
        partes = [p for p in [self.marca, self.modelo] if p]
        titulo = self.tipo_equipamento
        if partes:
            titulo = f"{titulo} {' '.join(partes)}".strip()
        return titulo


def foto_equipamento_upload_path(instance, filename):
    return f"emprestimos/{instance.equipamento.emprestimo_id}/equipamentos/{instance.equipamento_id}/{filename}"


class FotoEquipamentoEmprestimoTI(models.Model):
    equipamento = models.ForeignKey(
        EquipamentoEmprestimoTI, on_delete=models.CASCADE, related_name="fotos"
    )
    imagem = models.ImageField(upload_to=foto_equipamento_upload_path)
    nome_original = models.CharField(max_length=255, blank=True)
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fotos_equipamento_enviadas",
    )
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["enviado_em", "id"]

    def __str__(self) -> str:
        return self.nome_original or self.imagem.name


class LogUsoAssinaturaTI(models.Model):
    """Registro de cada uso autorizado de uma assinatura (rastreabilidade)."""

    assinatura = models.ForeignKey(
        AssinaturaResponsavelTI, on_delete=models.CASCADE, related_name="usos"
    )
    emprestimo = models.ForeignKey(
        EmprestimoTI, on_delete=models.SET_NULL, null=True, blank=True, related_name="usos_assinatura"
    )
    usado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usos_assinatura_ti",
    )
    usado_em = models.DateTimeField(auto_now_add=True)
    observacao = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-usado_em", "-id"]

    def __str__(self) -> str:
        return f"Uso da assinatura {self.assinatura_id} em {self.usado_em:%d/%m/%Y %H:%M}"


# ==========================================================================
# Modulo Emails: cadastro das contas de e-mail (importadas de uma lista CSV
# exportada do Google Workspace). A importacao faz upsert por e-mail.
# ==========================================================================


class ContaEmail(models.Model):
    """Conta de e-mail corporativo e seus dados, atualizada via importacao CSV.

    A chave de identificacao/atualizacao e o proprio e-mail (unico). A senha
    do export nunca e armazenada.
    """

    email = models.EmailField(unique=True)
    primeiro_nome = models.CharField(max_length=255, blank=True)
    sobrenome = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=40, blank=True)
    org_unit_path = models.CharField(max_length=255, blank=True)
    ultimo_acesso = models.CharField(max_length=40, blank=True)

    email_recuperacao = models.CharField(max_length=255, blank=True)
    telefone_recuperacao = models.CharField(max_length=40, blank=True)
    telefone_trabalho = models.CharField(max_length=40, blank=True)
    telefone_residencial = models.CharField(max_length=40, blank=True)
    telefone_celular = models.CharField(max_length=40, blank=True)

    employee_id = models.CharField(max_length=64, blank=True)
    tipo_funcionario = models.CharField(max_length=120, blank=True)
    cargo = models.CharField(max_length=255, blank=True)
    email_gestor = models.CharField(max_length=255, blank=True)
    departamento = models.CharField(max_length=255, blank=True)
    centro_custo = models.CharField(max_length=120, blank=True)

    dois_fatores_inscrito = models.BooleanField(default=False)
    dois_fatores_forcado = models.BooleanField(default=False)

    uso_email = models.CharField(max_length=40, blank=True)
    uso_drive = models.CharField(max_length=40, blank=True)
    uso_fotos = models.CharField(max_length=40, blank=True)
    limite_armazenamento = models.CharField(max_length=40, blank=True)
    armazenamento_usado = models.CharField(max_length=40, blank=True)

    licencas = models.TextField(blank=True)
    gemini_status = models.CharField(max_length=120, blank=True)

    importado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contas_email_importadas",
    )
    importado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["primeiro_nome", "sobrenome", "email"]
        verbose_name = "Conta de e-mail"
        verbose_name_plural = "Contas de e-mail"

    def __str__(self) -> str:
        return self.email

    @property
    def nome_completo(self) -> str:
        return f"{self.primeiro_nome} {self.sobrenome}".strip() or self.email

    @property
    def is_ativo(self) -> bool:
        return (self.status or "").strip().lower() == "active"


# ==========================================================================
# Modulo Ramais: lista telefonica interna (colaborador, setor, telefone,
# ramal e e-mail). O e-mail pode ser vinculado a uma ContaEmail existente.
# ==========================================================================


class Ramal(models.Model):
    """Contato da lista de ramais/telefones interna."""

    colaborador = models.CharField(max_length=255, blank=True)
    setor = models.CharField(max_length=255, blank=True)
    telefone = models.CharField(max_length=60, blank=True)
    ramal = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    conta_email = models.ForeignKey(
        ContaEmail,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ramais",
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ramais_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["colaborador", "setor", "id"]
        verbose_name = "Ramal"
        verbose_name_plural = "Ramais"

    def __str__(self) -> str:
        return f"{self.colaborador or self.setor} ({self.ramal or '-'})"


class LicencaSoftware(models.Model):
    """Software cadastrado no controle de licencas (ex.: AutoCAD, Project).

    Reune o nome, a quantidade de licencas contratadas e observacoes; cada
    licenca individual (serial, usuario, prazo) fica em `Licenca`.
    """

    nome = models.CharField(max_length=180)
    quantidade_licencas = models.PositiveIntegerField(default=1)
    observacoes = models.TextField(blank=True, default="")
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="softwares_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome", "id"]
        verbose_name = "Software"
        verbose_name_plural = "Softwares"

    def __str__(self) -> str:
        return self.nome

    @property
    def licencas_cadastradas(self) -> int:
        return self.licencas.count()


class Licenca(models.Model):
    """Licenca individual de um software (serial, usuario, prazo, pagamento)."""

    class TipoExpiracao(models.TextChoices):
        INDETERMINADO = "indeterminado", "Indeterminado"
        EXPIRA_EM = "expira_em", "Prazo para expirar"

    software = models.ForeignKey(
        LicencaSoftware,
        on_delete=models.CASCADE,
        related_name="licencas",
    )
    serial = models.CharField(max_length=240, blank=True, default="")
    email_vinculado = models.EmailField(max_length=254, blank=True, default="")
    tipo_expiracao = models.CharField(
        max_length=20,
        choices=TipoExpiracao.choices,
        default=TipoExpiracao.INDETERMINADO,
    )
    expira_em = models.DateField(null=True, blank=True)
    forma_pagamento = models.CharField(max_length=80, blank=True, default="")
    final_cartao = models.CharField(max_length=4, blank=True, default="")
    usuario_atribuido = models.CharField(max_length=180, blank=True, default="")
    observacoes = models.TextField(blank=True, default="")
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="licencas_criadas",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["software__nome", "usuario_atribuido", "email_vinculado", "id"]
        verbose_name = "Licenca de software"
        verbose_name_plural = "Licencas de software"

    def __str__(self) -> str:
        dono = self.usuario_atribuido or self.email_vinculado or self.serial or "Sem identificacao"
        return f"{self.software.nome} - {dono}"

    @property
    def expira_label(self) -> str:
        if self.tipo_expiracao == self.TipoExpiracao.INDETERMINADO:
            return "Indeterminado"
        if self.expira_em:
            return self.expira_em.strftime("%d/%m/%Y")
        return "Prazo nao informado"


class EnderecoIP(models.Model):
    """IP/equipamento da rede interna (modulo IPs): servidores, switches,
    catracas/IdFace, impressoras, Wi-Fi e monitoramento."""

    class Categoria(models.TextChoices):
        SERVIDORES = "servers", "Servidores"
        SWITCHES = "switches", "Switchs"
        IDFACE_CATRACAS = "idface_turnstiles", "IdFace + Catracas"
        IMPRESSORAS = "printers", "Impressoras"
        WIFI = "wifi", "Wi-Fi"
        MONITORAMENTO = "monitoring", "Zabbix & Grafana"

    categoria = models.CharField(max_length=30, choices=Categoria.choices)
    endereco_ip = models.CharField(max_length=45, unique=True)
    nome = models.CharField(max_length=180, blank=True, default="")
    fabricante = models.CharField(max_length=180, blank=True, default="")
    mac = models.CharField(max_length=80, blank=True, default="")
    acesso = models.TextField(blank=True, default="")
    observacoes = models.TextField(blank=True, default="")
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ips_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["categoria", "endereco_ip"]
        verbose_name = "IP"
        verbose_name_plural = "IPs"

    def __str__(self) -> str:
        rotulo = self.nome or self.fabricante or self.endereco_ip
        return f"{self.endereco_ip} - {rotulo}"


class ServicoFeito(models.Model):
    """Servico de TI ja executado, com empresa, valor, data e anexos (NFs,
    orcamentos, relatorios). Migrado do modulo 'Servicos feitos' antigo."""

    nome_servico = models.CharField(max_length=180)
    empresa = models.CharField(max_length=180, blank=True, default="")
    descricao = models.TextField(blank=True, default="")
    data_servico = models.DateField(default=timezone.localdate)
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="servicos_feitos_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data_servico", "-id"]
        verbose_name = "Servico feito"
        verbose_name_plural = "Servicos feitos"

    def __str__(self) -> str:
        return f"{self.nome_servico} - {self.empresa}"

    @property
    def anexos_total(self) -> int:
        return self.anexos.count()

    @property
    def valor_display(self) -> str:
        """Valor formatado no padrao brasileiro (1.234,56)."""
        valor = self.valor if isinstance(self.valor, Decimal) else Decimal(str(self.valor or "0"))
        inteiro, decimal = f"{valor:.2f}".split(".")
        inteiro = f"{int(inteiro):,}".replace(",", ".")
        return f"{inteiro},{decimal}"


class ServicoFeitoAnexo(models.Model):
    """Arquivo anexado a um servico feito (NF, orcamento, relatorio, etc.)."""

    servico = models.ForeignKey(
        ServicoFeito,
        on_delete=models.CASCADE,
        related_name="anexos",
    )
    arquivo = models.FileField(upload_to="servicos_feitos/")
    nome_original = models.CharField(max_length=255, blank=True, default="")
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Anexo de servico feito"
        verbose_name_plural = "Anexos de servicos feitos"

    def __str__(self) -> str:
        return self.nome_original or self.arquivo.name


class Contrato(models.Model):
    """Contrato de TI (recorrente ou unico): assinaturas, links, licencas anuais,
    etc., com valor, forma de pagamento, vigencia e anexos. Migrado do modulo
    'Contratos' antigo. Nao confundir com o modulo Requisicoes (RequisicaoContrato)."""

    class Periodicidade(models.TextChoices):
        MENSAL = "mensal", "Mensal"
        ANUAL = "anual", "Anual"
        PAGAMENTO_UNICO = "pagamento_unico", "Pagamento unico"

    nome = models.CharField(max_length=180)
    observacoes = models.TextField(blank=True, default="")
    valor = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    forma_pagamento = models.CharField(max_length=80, blank=True, default="")
    final_cartao = models.CharField(max_length=4, blank=True, default="")
    periodicidade = models.CharField(
        max_length=20,
        choices=Periodicidade.choices,
        default=Periodicidade.MENSAL,
    )
    inicio = models.DateField(null=True, blank=True)
    fim = models.DateField(null=True, blank=True)
    encerrado_em = models.DateField(null=True, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contratos_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome", "id"]
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"

    def __str__(self) -> str:
        return self.nome

    @property
    def anexos_total(self) -> int:
        return self.anexos.count()

    @property
    def esta_ativo(self) -> bool:
        return self.encerrado_em is None

    @property
    def valor_display(self) -> str:
        """Valor formatado no padrao brasileiro (1.234,56); '-' se sem valor."""
        if self.valor is None:
            return "-"
        valor = self.valor if isinstance(self.valor, Decimal) else Decimal(str(self.valor))
        inteiro, decimal = f"{valor:.2f}".split(".")
        inteiro = f"{int(inteiro):,}".replace(",", ".")
        return f"{inteiro},{decimal}"


class ContratoAnexo(models.Model):
    """Arquivo anexado a um contrato (NF, termo, invoice, comprovante)."""

    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name="anexos",
    )
    arquivo = models.FileField(upload_to="contratos_ti/")
    nome_original = models.CharField(max_length=255, blank=True, default="")
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Anexo de contrato"
        verbose_name_plural = "Anexos de contratos"

    def __str__(self) -> str:
        return self.nome_original or self.arquivo.name


class FuturaDigital(models.Model):
    """Fatura mensal da Futura Digital (locacao de impressoras): franquia de
    copias, excedentes e copias coloridas, com a regra de cobranca.

    Regra: valor_pago = franquia_valor
                        + copias_excedentes * valor_copia_excedente
                        + copias_cor * valor_copia_cor
    onde copias_excedentes = max(copias_total - copias_cor - franquia_copias, 0).
    """

    FRANQUIA_COPIAS_PADRAO = 23000
    FRANQUIA_VALOR_PADRAO = Decimal("1610.00")
    VALOR_EXCEDENTE_PADRAO = Decimal("0.07")
    VALOR_COR_PADRAO = Decimal("0.75")

    mes_referencia = models.DateField(help_text="Use o primeiro dia do mes de referencia.")
    nota_fiscal = models.CharField(max_length=80, blank=True, default="")
    copias_total = models.PositiveIntegerField(default=0)
    copias_cor = models.PositiveIntegerField(default=0)
    franquia_copias = models.PositiveIntegerField(default=FRANQUIA_COPIAS_PADRAO)
    franquia_valor = models.DecimalField(max_digits=12, decimal_places=2, default=FRANQUIA_VALOR_PADRAO)
    valor_copia_excedente = models.DecimalField(max_digits=8, decimal_places=4, default=VALOR_EXCEDENTE_PADRAO)
    valor_copia_cor = models.DecimalField(max_digits=8, decimal_places=4, default=VALOR_COR_PADRAO)
    copias_excedentes = models.PositiveIntegerField(default=0)
    valor_pago = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    documento = models.FileField(upload_to="futura_digital/", null=True, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="futura_digital_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-mes_referencia", "-id"]
        verbose_name = "Futura Digital"
        verbose_name_plural = "Futura Digital"

    def __str__(self) -> str:
        return f"Futura Digital - {self.mes_referencia:%m/%Y}"

    def calcular_excedentes(self) -> int:
        return max(int(self.copias_total) - int(self.copias_cor) - int(self.franquia_copias), 0)

    def calcular_valor(self) -> Decimal:
        excedentes = Decimal(self.copias_excedentes or 0)
        cor = Decimal(self.copias_cor or 0)
        return (
            Decimal(self.franquia_valor or 0)
            + excedentes * Decimal(self.valor_copia_excedente or 0)
            + cor * Decimal(self.valor_copia_cor or 0)
        ).quantize(Decimal("0.01"))

    def recalcular(self) -> None:
        """Atualiza excedentes e valor_pago a partir dos demais campos."""
        self.copias_excedentes = self.calcular_excedentes()
        self.valor_pago = self.calcular_valor()

    @property
    def mes_label(self) -> str:
        return self.mes_referencia.strftime("%m/%Y") if self.mes_referencia else "-"

    @property
    def copias_pb(self) -> int:
        return max(int(self.copias_total) - int(self.copias_cor), 0)

    @staticmethod
    def _num(valor) -> str:
        return f"{int(valor):,}".replace(",", ".")

    @staticmethod
    def _brl(valor) -> str:
        valor = valor if isinstance(valor, Decimal) else Decimal(str(valor or "0"))
        inteiro, decimal = f"{valor:.2f}".split(".")
        return f"{int(inteiro):,}".replace(",", ".") + f",{decimal}"

    @property
    def copias_total_display(self) -> str:
        return self._num(self.copias_total)

    @property
    def copias_excedentes_display(self) -> str:
        return self._num(self.copias_excedentes)

    @property
    def valor_pago_display(self) -> str:
        return self._brl(self.valor_pago)

    @property
    def franquia_valor_display(self) -> str:
        return self._brl(self.franquia_valor)


class Dica(models.Model):
    """Dica / base de conhecimento da TI: resolucoes, configuracoes e
    procedimentos gerais, com conteudo livre e anexo opcional."""

    class Categoria(models.TextChoices):
        GERAL = "geral", "Geral"
        CONFIGURACAO = "configuracao", "Configuracao"
        RESOLUCAO = "resolucao", "Resolucao"

    categoria = models.CharField(
        max_length=20,
        choices=Categoria.choices,
        default=Categoria.GERAL,
    )
    titulo = models.CharField(max_length=200)
    conteudo = models.TextField(blank=True, default="")
    anexo = models.FileField(upload_to="dicas/", null=True, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dicas_criadas",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["categoria", "titulo", "id"]
        verbose_name = "Dica"
        verbose_name_plural = "Dicas"

    def __str__(self) -> str:
        return self.titulo


class Starlink(models.Model):
    """Antena/plano Starlink da empresa: local, conta, credenciais e dados do
    kit (identificador, serial, versao). Migrado do modulo Starlinks antigo."""

    class FormaPagamento(models.TextChoices):
        PIX = "pix", "Pix"
        CARTAO = "cartao", "Cartao"

    nome = models.CharField(max_length=160)
    local = models.CharField(max_length=180, blank=True, default="")
    email = models.EmailField(max_length=254, blank=True, default="")
    ativo = models.BooleanField(default=True)
    forma_pagamento = models.CharField(
        max_length=12,
        choices=FormaPagamento.choices,
        default=FormaPagamento.CARTAO,
    )
    final_cartao = models.CharField(max_length=4, blank=True, default="")
    identificador = models.CharField(max_length=80, blank=True, default="")
    versao_software = models.CharField(max_length=80, blank=True, default="")
    numero_serie = models.CharField(max_length=120, blank=True, default="")
    numero_kit = models.CharField(max_length=120, blank=True, default="")
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="starlinks_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome", "id"]
        verbose_name = "Starlink"
        verbose_name_plural = "Starlinks"

    def __str__(self) -> str:
        return self.nome


class CofreConfig(models.Model):
    """Configuracao unica do Cofre: senha-mestra (hash) e anti-brute-force.

    A senha-mestra destrava o cofre na sessao; e guardada apenas como hash
    (make_password), nunca em texto. O acesso ainda exige ser Atendente TI/Admin.
    """

    senha_mestra_hash = models.CharField(max_length=255, blank=True, default="")
    tentativas_falhas = models.PositiveSmallIntegerField(default=0)
    bloqueado_ate = models.DateTimeField(null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuracao do Cofre"
        verbose_name_plural = "Configuracoes do Cofre"

    def __str__(self) -> str:
        return "Configuracao do Cofre"

    @classmethod
    def load(cls) -> "CofreConfig":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def tem_senha_mestra(self) -> bool:
        return bool(self.senha_mestra_hash)

    def definir_senha_mestra(self, raw_password: str) -> None:
        from django.contrib.auth.hashers import make_password

        self.senha_mestra_hash = make_password(raw_password)
        self.tentativas_falhas = 0
        self.bloqueado_ate = None

    def conferir_senha_mestra(self, raw_password: str) -> bool:
        from django.contrib.auth.hashers import check_password

        if not self.senha_mestra_hash:
            return False
        return check_password(raw_password, self.senha_mestra_hash)

    def esta_bloqueado(self) -> bool:
        return bool(self.bloqueado_ate and self.bloqueado_ate > timezone.now())

    def segundos_bloqueio_restante(self) -> int:
        if not self.bloqueado_ate:
            return 0
        return max(int((self.bloqueado_ate - timezone.now()).total_seconds()), 0)

    def registrar_falha(self) -> None:
        from django.conf import settings as dj_settings

        maximo = int(getattr(dj_settings, "VAULT_MAX_FAILED_ATTEMPTS", 5) or 5)
        bloqueio = int(getattr(dj_settings, "VAULT_LOCKOUT_SECONDS", 300) or 300)
        self.tentativas_falhas += 1
        if self.tentativas_falhas >= maximo:
            self.bloqueado_ate = timezone.now() + timedelta(seconds=bloqueio)
            self.tentativas_falhas = 0
        self.save(update_fields=["tentativas_falhas", "bloqueado_ate", "atualizado_em"])

    def resetar_falhas(self) -> None:
        self.tentativas_falhas = 0
        self.bloqueado_ate = None
        self.save(update_fields=["tentativas_falhas", "bloqueado_ate", "atualizado_em"])


class CofreCredencial(models.Model):
    """Credencial guardada no cofre. A senha e cifrada em repouso (Fernet)."""

    rotulo = models.CharField(max_length=160)
    usuario = models.CharField(max_length=180, blank=True, default="")
    senha_cifrada = models.TextField(blank=True, default="")
    notas = models.TextField(blank=True, default="")
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cofre_credenciais_criadas",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["rotulo", "id"]
        verbose_name = "Credencial do Cofre"
        verbose_name_plural = "Credenciais do Cofre"

    def __str__(self) -> str:
        return self.rotulo

    def definir_senha(self, raw_password: str) -> None:
        from .crypto import encrypt_text

        self.senha_cifrada = encrypt_text(raw_password or "")

    def obter_senha(self) -> str:
        from .crypto import decrypt_text

        return decrypt_text(self.senha_cifrada)


class CofreAuditoria(models.Model):
    """Trilha de auditoria do cofre: destrave, falhas, visualizacao/copia, CRUD."""

    ACAO_UNLOCK_OK = "unlock_ok"
    ACAO_UNLOCK_FALHA = "unlock_falha"
    ACAO_BLOQUEIO = "bloqueio"
    ACAO_LOCK = "lock"
    ACAO_SENHA_MESTRA = "senha_mestra"
    ACAO_CRED_CRIADA = "cred_criada"
    ACAO_CRED_ATUALIZADA = "cred_atualizada"
    ACAO_CRED_EXCLUIDA = "cred_excluida"
    ACAO_CRED_REVELADA = "cred_revelada"

    ACAO_CHOICES = [
        (ACAO_UNLOCK_OK, "Destravou o cofre"),
        (ACAO_UNLOCK_FALHA, "Falha ao destravar"),
        (ACAO_BLOQUEIO, "Bloqueio temporario"),
        (ACAO_LOCK, "Travou o cofre"),
        (ACAO_SENHA_MESTRA, "Senha-mestra definida/alterada"),
        (ACAO_CRED_CRIADA, "Credencial criada"),
        (ACAO_CRED_ATUALIZADA, "Credencial atualizada"),
        (ACAO_CRED_EXCLUIDA, "Credencial excluida"),
        (ACAO_CRED_REVELADA, "Senha revelada/copiada"),
    ]

    criado_em = models.DateTimeField(auto_now_add=True)
    acao = models.CharField(max_length=32, choices=ACAO_CHOICES)
    ator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cofre_auditorias",
    )
    credencial = models.ForeignKey(
        CofreCredencial,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="auditorias",
    )
    rotulo_credencial = models.CharField(max_length=160, blank=True, default="")
    ip = models.GenericIPAddressField(null=True, blank=True)
    detalhes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-criado_em", "-id"]
        verbose_name = "Auditoria do Cofre"
        verbose_name_plural = "Auditoria do Cofre"

    def __str__(self) -> str:
        ator = self.ator.username if self.ator else "?"
        return f"{self.criado_em:%d/%m/%Y %H:%M} - {self.acao} - {ator}"


class EmailConfig(models.Model):
    """Configuracao unica (singleton) das notificacoes por e-mail (SMTP).

    Guarda os dados do servidor SMTP e para onde enviar as notificacoes de
    chamado. A senha (senha de app do Google, por padrao) e cifrada em repouso
    com Fernet (mesmo esquema do Cofre, `core/crypto.py`) — no banco so ha texto
    cifrado. Os defaults ja vem prontos para o Google (smtp.gmail.com / 587 / TLS).
    """

    ativo = models.BooleanField(
        default=False,
        help_text="Liga/desliga o envio de e-mails de notificacao.",
    )

    # Servidor SMTP (defaults do Google/Gmail).
    host = models.CharField(max_length=255, blank=True, default="smtp.gmail.com")
    porta = models.PositiveIntegerField(default=587)
    usar_tls = models.BooleanField(default=True)
    usar_ssl = models.BooleanField(default=False)
    timeout = models.PositiveIntegerField(default=15, help_text="Tempo limite (segundos) da conexao SMTP.")

    # Conta de envio.
    usuario = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Conta que autentica no SMTP (ex.: seu-email@gmail.com).",
    )
    senha_cifrada = models.TextField(blank=True, default="")
    remetente = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="E-mail que aparece como remetente. Em branco usa a conta de envio.",
    )
    remetente_nome = models.CharField(max_length=160, blank=True, default="Chamados TI")

    # Destino das notificacoes para a equipe de TI (aceita varios, separados por
    # virgula, ponto-e-virgula ou quebra de linha).
    emails_ti = models.TextField(
        blank=True,
        default="",
        help_text="E-mail(s) da equipe de TI que recebem as notificacoes.",
    )

    # Quais eventos disparam e-mail.
    notif_novo_chamado = models.BooleanField(default=True)
    notif_nova_mensagem = models.BooleanField(default=True)
    notif_mudanca_status = models.BooleanField(default=True)
    notif_fechamento = models.BooleanField(default=True)

    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuracao de E-mail"
        verbose_name_plural = "Configuracao de E-mail"

    def __str__(self) -> str:
        return "Configuracao de E-mail (SMTP)"

    @classmethod
    def load(cls) -> "EmailConfig":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def tem_senha(self) -> bool:
        return bool(self.senha_cifrada)

    def definir_senha(self, raw_password: str) -> None:
        from .crypto import encrypt_text

        self.senha_cifrada = encrypt_text(raw_password or "")

    def obter_senha(self) -> str:
        from .crypto import decrypt_text

        return decrypt_text(self.senha_cifrada)

    @property
    def remetente_efetivo(self) -> str:
        return (self.remetente or self.usuario or "").strip()

    def destinatarios_ti(self) -> list[str]:
        """Lista de e-mails da TI (normalizada e sem duplicados)."""
        bruto = (self.emails_ti or "").replace(";", ",").replace("\n", ",")
        vistos: list[str] = []
        for parte in bruto.split(","):
            email = parte.strip()
            if email and email.lower() not in {v.lower() for v in vistos}:
                vistos.append(email)
        return vistos
