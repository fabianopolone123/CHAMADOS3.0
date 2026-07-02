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
    STATUS_EM_ATENDIMENTO = "em_atendimento"
    STATUS_AGUARDANDO_USUARIO = "aguardando_usuario"
    STATUS_RESOLVIDO = "resolvido"
    STATUS_FECHADO = "fechado"
    STATUS_CHOICES = [
        (STATUS_ABERTO, "Aberto"),
        (STATUS_EM_ATENDIMENTO, "Em atendimento"),
        (STATUS_AGUARDANDO_USUARIO, "Aguardando usuario"),
        (STATUS_RESOLVIDO, "Resolvido"),
        (STATUS_FECHADO, "Fechado"),
    ]
    STATUS_ENCERRADOS = {STATUS_RESOLVIDO, STATUS_FECHADO}

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

    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
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
        ordering = ["criado_em", "id"]

    def __str__(self) -> str:
        return f"Pendencia #{self.pk} - {self.titulo}"


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
    STATUS_FINALIZADA = "finalizada"
    STATUS_CANCELADA = "cancelada"
    STATUS_CHOICES = [
        (STATUS_ABERTA, "Aberta"),
        (STATUS_EM_COTACAO, "Em cotacao"),
        (STATUS_FINALIZADA, "Finalizada"),
        (STATUS_CANCELADA, "Cancelada"),
    ]

    titulo = models.CharField(max_length=255)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default=TIPO_FISICA)
    texto = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ABERTA)
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
        return self.titulo

    @property
    def status_label(self) -> str:
        return dict(self.STATUS_CHOICES).get(self.status, self.status or "-")

    @property
    def tipo_label(self) -> str:
        return dict(self.TIPO_CHOICES).get(self.tipo, self.tipo or "-")


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
    """Registro historico de uma retirada/baixa de estoque de um insumo."""

    insumo = models.ForeignKey(InsumoTI, on_delete=models.CASCADE, related_name="retiradas")
    quantidade = models.PositiveIntegerField()
    entregue_para = models.CharField(max_length=255)
    motivo = models.TextField()
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
        return f"{self.quantidade}x {self.insumo.nome} -> {self.entregue_para}"


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
