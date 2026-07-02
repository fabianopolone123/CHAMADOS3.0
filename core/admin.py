from django.contrib import admin

from .models import (
    OrcamentoContrato,
    OrcamentoDocumento,
    RequisicaoContrato,
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
