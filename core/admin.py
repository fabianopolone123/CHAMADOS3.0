from django.contrib import admin

from .models import (
    AssinaturaResponsavelTI,
    ContaEmail,
    DocumentoTI,
    DocumentoTIAnexo,
    EmprestimoTI,
    EquipamentoEmprestimoTI,
    FotoEquipamentoEmprestimoTI,
    InsumoTI,
    LogUsoAssinaturaTI,
    OrcamentoContrato,
    OrcamentoDocumento,
    RequisicaoContrato,
    RetiradaInsumoTI,
    SuborcamentoContrato,
    SuborcamentoDocumento,
)


class OrcamentoDocumentoInline(admin.TabularInline):
    model = OrcamentoDocumento
    extra = 0


class SuborcamentoDocumentoInline(admin.TabularInline):
    model = SuborcamentoDocumento
    extra = 0


class SuborcamentoContratoInline(admin.TabularInline):
    model = SuborcamentoContrato
    extra = 0
    fields = ("titulo", "loja", "moeda", "valor", "quantidade", "frete", "desconto")
    show_change_link = True


@admin.register(RequisicaoContrato)
class RequisicaoContratoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "status", "criado_por", "criado_em")
    list_filter = ("status", "tipo")
    search_fields = ("titulo", "texto")
    date_hierarchy = "criado_em"


@admin.register(OrcamentoContrato)
class OrcamentoContratoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "requisicao", "loja", "moeda", "valor", "quantidade", "total_com_suborcamentos", "criado_por")
    list_filter = ("moeda",)
    search_fields = ("titulo", "loja")
    inlines = [SuborcamentoContratoInline, OrcamentoDocumentoInline]


@admin.register(SuborcamentoContrato)
class SuborcamentoContratoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "orcamento_pai", "loja", "moeda", "valor", "quantidade", "total", "criado_por")
    list_filter = ("moeda",)
    search_fields = ("titulo", "loja")
    inlines = [SuborcamentoDocumentoInline]


class RetiradaInsumoTIInline(admin.TabularInline):
    model = RetiradaInsumoTI
    extra = 0
    fields = ("quantidade", "entregue_para", "motivo", "registrado_por", "criado_em")
    readonly_fields = ("criado_em",)


@admin.register(InsumoTI)
class InsumoTIAdmin(admin.ModelAdmin):
    list_display = ("nome", "quantidade_atual", "ativo", "atualizado_em")
    list_filter = ("ativo",)
    search_fields = ("nome", "descricao")
    inlines = [RetiradaInsumoTIInline]


@admin.register(RetiradaInsumoTI)
class RetiradaInsumoTIAdmin(admin.ModelAdmin):
    list_display = ("insumo", "quantidade", "entregue_para", "registrado_por", "criado_em")
    search_fields = ("insumo__nome", "entregue_para", "motivo")
    date_hierarchy = "criado_em"


class DocumentoTIAnexoInline(admin.TabularInline):
    model = DocumentoTIAnexo
    extra = 0
    fields = ("arquivo", "nome_original", "enviado_por", "enviado_em")
    readonly_fields = ("enviado_em",)


@admin.register(DocumentoTI)
class DocumentoTIAdmin(admin.ModelAdmin):
    list_display = ("nome", "criado_por", "ativo", "criado_em", "atualizado_em")
    list_filter = ("ativo",)
    search_fields = ("nome", "observacao")
    date_hierarchy = "criado_em"
    inlines = [DocumentoTIAnexoInline]


@admin.register(DocumentoTIAnexo)
class DocumentoTIAnexoAdmin(admin.ModelAdmin):
    list_display = ("nome_original", "documento", "enviado_por", "enviado_em")
    search_fields = ("nome_original", "documento__nome")
    date_hierarchy = "enviado_em"


class FotoEquipamentoInline(admin.TabularInline):
    model = FotoEquipamentoEmprestimoTI
    extra = 0
    readonly_fields = ("enviado_em",)


class EquipamentoEmprestimoInline(admin.TabularInline):
    model = EquipamentoEmprestimoTI
    extra = 0
    fields = ("tipo_equipamento", "marca", "modelo", "numero_serie", "patrimonio_etiqueta")
    show_change_link = True


@admin.register(EmprestimoTI)
class EmprestimoTIAdmin(admin.ModelAdmin):
    list_display = ("id", "colaborador_nome", "empresa", "status", "data_emprestimo", "termo_assinado_ok", "criado_por")
    list_filter = ("status", "termo_assinado_ok")
    search_fields = ("colaborador_nome", "empresa", "cpf", "email")
    date_hierarchy = "data_emprestimo"
    inlines = [EquipamentoEmprestimoInline]


@admin.register(EquipamentoEmprestimoTI)
class EquipamentoEmprestimoTIAdmin(admin.ModelAdmin):
    list_display = ("tipo_equipamento", "marca", "modelo", "numero_serie", "patrimonio_etiqueta", "emprestimo")
    search_fields = ("tipo_equipamento", "marca", "modelo", "numero_serie", "patrimonio_etiqueta")
    inlines = [FotoEquipamentoInline]


@admin.register(AssinaturaResponsavelTI)
class AssinaturaResponsavelTIAdmin(admin.ModelAdmin):
    list_display = ("nome_responsavel", "ativo", "criado_por", "criado_em", "atualizado_em")
    list_filter = ("ativo",)
    search_fields = ("nome_responsavel",)
    exclude = ("senha_hash",)


@admin.register(LogUsoAssinaturaTI)
class LogUsoAssinaturaTIAdmin(admin.ModelAdmin):
    list_display = ("assinatura", "emprestimo", "usado_por", "usado_em")
    date_hierarchy = "usado_em"


@admin.register(ContaEmail)
class ContaEmailAdmin(admin.ModelAdmin):
    list_display = ("email", "primeiro_nome", "sobrenome", "status", "departamento", "cargo", "atualizado_em")
    list_filter = ("status", "departamento", "dois_fatores_inscrito")
    search_fields = ("email", "primeiro_nome", "sobrenome", "departamento", "cargo", "employee_id")
    date_hierarchy = "atualizado_em"
