from django.contrib import admin

from .models import (
    AssinaturaResponsavelTI,
    ContaEmail,
    CofreAuditoria,
    CofreConfig,
    CofreCredencial,
    Contrato,
    ContratoAnexo,
    Dica,
    DocumentoTI,
    DocumentoTIAnexo,
    EmailConfig,
    EnderecoIP,
    FuturaDigital,
    Licenca,
    LicencaSoftware,
    Ramal,
    EmprestimoTI,
    EquipamentoEmprestimoTI,
    FotoEquipamentoEmprestimoTI,
    InsumoTI,
    LogUsoAssinaturaTI,
    OrcamentoContrato,
    OrcamentoDocumento,
    RequisicaoContrato,
    RetiradaInsumoTI,
    ServicoFeito,
    ServicoFeitoAnexo,
    Starlink,
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


@admin.register(Ramal)
class RamalAdmin(admin.ModelAdmin):
    list_display = ("colaborador", "setor", "telefone", "ramal", "email", "atualizado_em")
    list_filter = ("setor",)
    search_fields = ("colaborador", "setor", "telefone", "ramal", "email")


class LicencaInline(admin.TabularInline):
    model = Licenca
    extra = 0
    fields = ("usuario_atribuido", "serial", "email_vinculado", "tipo_expiracao", "expira_em", "forma_pagamento", "final_cartao")


@admin.register(LicencaSoftware)
class LicencaSoftwareAdmin(admin.ModelAdmin):
    list_display = ("nome", "quantidade_licencas", "licencas_cadastradas", "atualizado_em")
    search_fields = ("nome", "observacoes")
    inlines = [LicencaInline]


@admin.register(Licenca)
class LicencaAdmin(admin.ModelAdmin):
    list_display = ("software", "usuario_atribuido", "email_vinculado", "tipo_expiracao", "expira_em", "atualizado_em")
    list_filter = ("tipo_expiracao", "software")
    search_fields = ("usuario_atribuido", "email_vinculado", "serial", "forma_pagamento")


@admin.register(EnderecoIP)
class EnderecoIPAdmin(admin.ModelAdmin):
    list_display = ("endereco_ip", "categoria", "nome", "fabricante", "mac", "atualizado_em")
    list_filter = ("categoria",)
    search_fields = ("endereco_ip", "nome", "fabricante", "mac", "acesso")


class ServicoFeitoAnexoInline(admin.TabularInline):
    model = ServicoFeitoAnexo
    extra = 0
    fields = ("arquivo", "nome_original", "enviado_em")
    readonly_fields = ("enviado_em",)


@admin.register(ServicoFeito)
class ServicoFeitoAdmin(admin.ModelAdmin):
    list_display = ("nome_servico", "empresa", "data_servico", "valor", "anexos_total", "atualizado_em")
    list_filter = ("empresa", "data_servico")
    search_fields = ("nome_servico", "empresa", "descricao")
    date_hierarchy = "data_servico"
    inlines = [ServicoFeitoAnexoInline]


class ContratoAnexoInline(admin.TabularInline):
    model = ContratoAnexo
    extra = 0
    fields = ("arquivo", "nome_original", "enviado_em")
    readonly_fields = ("enviado_em",)


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ("nome", "valor", "periodicidade", "forma_pagamento", "inicio", "fim", "encerrado_em", "anexos_total")
    list_filter = ("periodicidade", "forma_pagamento")
    search_fields = ("nome", "observacoes", "forma_pagamento")
    inlines = [ContratoAnexoInline]


@admin.register(FuturaDigital)
class FuturaDigitalAdmin(admin.ModelAdmin):
    list_display = ("mes_referencia", "copias_total", "copias_cor", "copias_excedentes", "valor_pago", "nota_fiscal")
    list_filter = ("mes_referencia",)
    search_fields = ("nota_fiscal",)
    date_hierarchy = "mes_referencia"


@admin.register(Dica)
class DicaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "categoria", "criado_por", "atualizado_em")
    list_filter = ("categoria",)
    search_fields = ("titulo", "conteudo")


@admin.register(Starlink)
class StarlinkAdmin(admin.ModelAdmin):
    list_display = ("nome", "local", "email", "ativo", "forma_pagamento", "numero_serie", "atualizado_em")
    list_filter = ("ativo", "forma_pagamento")
    search_fields = ("nome", "local", "email", "numero_serie", "numero_kit", "identificador")


@admin.register(CofreCredencial)
class CofreCredencialAdmin(admin.ModelAdmin):
    # NAO expoe a senha (nem cifrada nem em texto) na listagem/edicao.
    list_display = ("rotulo", "usuario", "criado_por", "atualizado_em")
    search_fields = ("rotulo", "usuario", "notas")
    exclude = ("senha_cifrada",)
    readonly_fields = ("criado_por", "criado_em", "atualizado_em")


@admin.register(CofreAuditoria)
class CofreAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("criado_em", "acao", "ator", "rotulo_credencial", "ip")
    list_filter = ("acao",)
    search_fields = ("rotulo_credencial", "detalhes")
    readonly_fields = ("criado_em", "acao", "ator", "credencial", "rotulo_credencial", "ip", "detalhes")

    def has_add_permission(self, request):
        return False


@admin.register(CofreConfig)
class CofreConfigAdmin(admin.ModelAdmin):
    list_display = ("__str__", "tentativas_falhas", "bloqueado_ate", "atualizado_em")
    readonly_fields = ("senha_mestra_hash", "atualizado_em")


@admin.register(EmailConfig)
class EmailConfigAdmin(admin.ModelAdmin):
    # NAO expoe a senha cifrada; a configuracao e feita pela tela /email-config/.
    list_display = ("__str__", "ativo", "host", "porta", "usuario", "atualizado_em")
    exclude = ("senha_cifrada",)
    readonly_fields = ("atualizado_em",)
