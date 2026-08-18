"""Catalogo e camada generica de dados do Painel do Titular.

O painel navega pelas tabelas do sistema como um terminal de banco: escolhe a
tabela, lista os registros, abre um registro e altera campo a campo. Para isso
existe aqui:

- `TABELAS`: quais modelos aparecem no painel, com rotulo, colunas da lista e
  campos de busca;
- leitura generica (`listar`, `detalhar`) e escrita generica (`alterar_campo`,
  `excluir`), montadas em cima do `_meta` do proprio modelo.

Regras de seguranca desta camada (valem para todas as tabelas):

- campos de segredo NUNCA saem daqui (senha, hash, texto cifrado, token) —
  ver `_CAMPO_SECRETO`; as credenciais do Cofre continuam so no Cofre, com a
  senha-mestra;
- arquivos e imagens aparecem apenas pelo nome e nao sao editaveis pelo painel
  (upload e por tela do modulo, que trata o disco);
- campos automaticos (id, `auto_now`, `auto_now_add`) sao somente leitura.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from . import models as m


@dataclass(frozen=True)
class TabelaPainel:
    chave: str
    rotulo: str
    modelo: type[models.Model]
    colunas: tuple[str, ...]
    busca: tuple[str, ...] = ()
    ordem: str = "-id"
    somente_leitura: bool = False
    pode_excluir: bool = True
    nota: str = ""
    campos_ocultos: tuple[str, ...] = dataclass_field(default_factory=tuple)


TABELAS: tuple[TabelaPainel, ...] = (
    # --- Chamados ---------------------------------------------------------
    TabelaPainel(
        chave="chamados",
        rotulo="CHAMADOS",
        modelo=m.Chamado,
        colunas=("numero", "titulo", "status", "prioridade", "solicitante", "atendente_atual"),
        busca=("numero", "titulo", "descricao", "solicitante__username", "solicitante__first_name"),
        ordem="-criado_em",
    ),
    TabelaPainel(
        chave="atendimentos",
        rotulo="ATENDIMENTOS (PLAY/STOP)",
        modelo=m.AtendimentoHistorico,
        colunas=("chamado", "atendente", "iniciado_em", "finalizado_em", "duracao", "tipo_encerramento"),
        busca=("chamado__numero", "atendente__username", "descricao_atividade"),
        ordem="-iniciado_em",
    ),
    TabelaPainel(
        chave="pausas",
        rotulo="PAUSAS AUTOMATICAS",
        modelo=m.PausaAutomatica,
        colunas=("atendimento", "criado_em", "complementado_em", "complementado_por"),
        busca=("atendimento__chamado__numero", "atendimento__atendente__username"),
        ordem="-criado_em",
    ),
    TabelaPainel(
        chave="pendencias",
        rotulo="PENDENCIAS DE TI",
        modelo=m.PendenciaTI,
        colunas=("titulo", "prioridade", "criado_por", "criado_em", "convertido_em_chamado"),
        busca=("titulo", "descricao"),
        ordem="-criado_em",
    ),
    TabelaPainel(
        chave="mensagens",
        rotulo="MENSAGENS DE CHAMADO",
        modelo=m.ChamadoMensagem,
        colunas=("chamado", "autor", "criado_em"),
        busca=("chamado__numero", "texto", "autor__username"),
        ordem="-criado_em",
    ),
    TabelaPainel(
        chave="eventos",
        rotulo="EVENTOS DE CHAMADO",
        modelo=m.ChamadoEvento,
        colunas=("chamado", "tipo", "usuario", "criado_em"),
        busca=("chamado__numero", "descricao"),
        ordem="-criado_em",
        somente_leitura=True,
        nota="Trilha do chamado: so leitura.",
    ),
    # --- Requisicoes ------------------------------------------------------
    TabelaPainel(
        chave="requisicoes",
        rotulo="REQUISICOES DE COMPRA",
        modelo=m.RequisicaoContrato,
        colunas=("codigo", "titulo", "tipo", "status", "criado_por", "criado_em"),
        busca=("codigo", "titulo", "texto"),
        ordem="-criado_em",
    ),
    TabelaPainel(
        chave="orcamentos",
        rotulo="ORCAMENTOS",
        modelo=m.OrcamentoContrato,
        colunas=("requisicao", "titulo", "loja", "valor", "quantidade", "aprovado"),
        busca=("titulo", "loja", "requisicao__codigo"),
    ),
    TabelaPainel(
        chave="suborcamentos",
        rotulo="SUBORCAMENTOS",
        modelo=m.SuborcamentoContrato,
        colunas=("orcamento_pai", "titulo", "loja", "valor", "quantidade"),
        busca=("titulo", "loja"),
    ),
    # --- Modulos de TI ----------------------------------------------------
    TabelaPainel(
        chave="ramais",
        rotulo="RAMAIS",
        modelo=m.Ramal,
        colunas=("colaborador", "setor", "telefone", "ramal", "email", "kaspersky_instalado"),
        busca=("colaborador", "setor", "telefone", "ramal", "email"),
        ordem="colaborador",
    ),
    TabelaPainel(
        chave="emails",
        rotulo="CONTAS DE E-MAIL",
        modelo=m.ContaEmail,
        colunas=("email", "primeiro_nome", "sobrenome", "departamento", "status", "ultimo_acesso"),
        busca=("email", "primeiro_nome", "sobrenome", "departamento", "cargo"),
        ordem="email",
    ),
    TabelaPainel(
        chave="ips",
        rotulo="ENDERECOS IP",
        modelo=m.EnderecoIP,
        colunas=("endereco_ip", "nome", "categoria", "fabricante", "mac"),
        busca=("endereco_ip", "nome", "fabricante", "mac", "observacoes"),
        ordem="endereco_ip",
    ),
    TabelaPainel(
        chave="softwares",
        rotulo="SOFTWARES (LICENCAS)",
        modelo=m.LicencaSoftware,
        colunas=("nome", "quantidade_licencas", "observacoes"),
        busca=("nome",),
        ordem="nome",
    ),
    TabelaPainel(
        chave="licencas",
        rotulo="LICENCAS",
        modelo=m.Licenca,
        colunas=("software", "usuario_atribuido", "email_vinculado", "tipo_expiracao", "expira_em", "forma_pagamento"),
        busca=("usuario_atribuido", "email_vinculado", "serial", "software__nome"),
    ),
    TabelaPainel(
        chave="insumos",
        rotulo="INSUMOS",
        modelo=m.InsumoTI,
        colunas=("nome", "quantidade_atual", "ativo", "atualizado_em"),
        busca=("nome", "descricao", "observacao"),
        ordem="nome",
    ),
    TabelaPainel(
        chave="retiradas",
        rotulo="RETIRADAS DE INSUMO",
        modelo=m.RetiradaInsumoTI,
        colunas=("insumo", "tipo", "quantidade", "entregue_para", "criado_em"),
        busca=("insumo__nome", "entregue_para", "motivo"),
        ordem="-criado_em",
    ),
    TabelaPainel(
        chave="documentos",
        rotulo="DOCUMENTOS",
        modelo=m.DocumentoTI,
        colunas=("nome", "ativo", "criado_em"),
        busca=("nome", "observacao"),
        ordem="-criado_em",
    ),
    TabelaPainel(
        chave="emprestimos",
        rotulo="EMPRESTIMOS",
        modelo=m.EmprestimoTI,
        colunas=("colaborador_nome", "empresa", "status", "data_emprestimo", "criado_em"),
        busca=("colaborador_nome", "empresa", "cpf", "email"),
        ordem="-criado_em",
    ),
    TabelaPainel(
        chave="equipamentos",
        rotulo="EQUIPAMENTOS EMPRESTADOS",
        modelo=m.EquipamentoEmprestimoTI,
        colunas=("emprestimo", "tipo_equipamento", "marca", "modelo", "numero_serie", "data_devolucao"),
        busca=("tipo_equipamento", "marca", "modelo", "numero_serie", "emprestimo__colaborador_nome"),
    ),
    TabelaPainel(
        chave="servicos",
        rotulo="SERVICOS FEITOS",
        modelo=m.ServicoFeito,
        colunas=("nome_servico", "empresa", "data_servico", "valor"),
        busca=("nome_servico", "empresa", "descricao"),
        ordem="-data_servico",
    ),
    TabelaPainel(
        chave="contratos_ti",
        rotulo="CONTRATOS",
        modelo=m.Contrato,
        colunas=("nome", "valor", "periodicidade", "inicio", "fim", "encerrado_em"),
        busca=("nome", "observacoes"),
        ordem="nome",
    ),
    TabelaPainel(
        chave="futura",
        rotulo="FUTURA DIGITAL",
        modelo=m.FuturaDigital,
        colunas=("mes_referencia", "nota_fiscal", "copias_total", "copias_cor", "copias_excedentes", "valor_pago"),
        busca=("nota_fiscal",),
        ordem="-mes_referencia",
    ),
    TabelaPainel(
        chave="dicas",
        rotulo="DICAS",
        modelo=m.Dica,
        colunas=("titulo", "categoria", "criado_em"),
        busca=("titulo", "conteudo"),
        ordem="-criado_em",
    ),
    TabelaPainel(
        chave="starlinks",
        rotulo="STARLINKS",
        modelo=m.Starlink,
        colunas=("nome", "local", "ativo", "forma_pagamento", "identificador"),
        busca=("nome", "local", "email", "identificador", "numero_serie"),
        ordem="nome",
    ),
    # --- Seguranca e sistema (so leitura) ---------------------------------
    TabelaPainel(
        chave="cofre",
        rotulo="COFRE (SO METADADOS)",
        modelo=m.CofreCredencial,
        colunas=("rotulo", "usuario", "criado_em", "atualizado_em"),
        busca=("rotulo", "usuario"),
        somente_leitura=True,
        pode_excluir=False,
        nota="As senhas ficam cifradas e so abrem no Cofre, com a senha-mestra.",
    ),
    TabelaPainel(
        chave="cofre_auditoria",
        rotulo="AUDITORIA DO COFRE",
        modelo=m.CofreAuditoria,
        colunas=("criado_em", "acao", "ator", "rotulo_credencial", "ip"),
        busca=("acao", "ator__username", "rotulo_credencial"),
        ordem="-criado_em",
        somente_leitura=True,
    ),
    TabelaPainel(
        chave="painel_auditoria",
        rotulo="ACOES DO PAINEL",
        modelo=m.PainelAuditoria,
        colunas=("criado_em", "area", "acao", "alvo"),
        busca=("acao", "alvo", "detalhe"),
        ordem="-criado_em",
        somente_leitura=True,
        nota="Trilha do proprio painel: so leitura.",
    ),
)

TABELA_POR_CHAVE: dict[str, TabelaPainel] = {t.chave: t for t in TABELAS}

# Pedacos de nome que marcam campo de segredo: nunca sao mostrados nem editados.
_CAMPO_SECRETO = ("senha", "password", "hash", "cifrad", "token", "secret")


def _e_secreto(nome: str) -> bool:
    nome = nome.lower()
    return any(p in nome for p in _CAMPO_SECRETO)


def _e_arquivo(campo) -> bool:
    return isinstance(campo, (models.FileField, models.ImageField))


def campos_do_modelo(tabela: TabelaPainel) -> list:
    """Campos concretos que o painel pode mostrar (segredos ja fora)."""
    saida = []
    for campo in tabela.modelo._meta.get_fields():
        if not getattr(campo, "concrete", False) or campo.many_to_many:
            continue
        if campo.name in tabela.campos_ocultos or _e_secreto(campo.name):
            continue
        saida.append(campo)
    return saida


def campo_editavel(tabela: TabelaPainel, campo) -> bool:
    if tabela.somente_leitura:
        return False
    if campo.name == "id" or isinstance(campo, models.AutoField):
        return False
    if _e_arquivo(campo) or _e_secreto(campo.name):
        return False
    if getattr(campo, "auto_now", False) or getattr(campo, "auto_now_add", False):
        return False
    return True


def formatar(valor, campo=None) -> str:
    """Texto curto de um valor, no padrao do terminal (nunca None cru)."""
    if valor is None:
        return "-"
    if isinstance(valor, bool):
        return "SIM" if valor else "NAO"
    if isinstance(valor, datetime):
        return timezone.localtime(valor).strftime("%d/%m/%Y %H:%M") if timezone.is_aware(valor) else valor.strftime("%d/%m/%Y %H:%M")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, Decimal):
        return f"{valor:.2f}".replace(".", ",")
    if campo is not None and _e_arquivo(campo):
        return valor.name.rsplit("/", 1)[-1] if getattr(valor, "name", "") else "-"
    texto = str(valor).strip()
    return texto if texto else "-"


def valor_exibicao(instancia, campo) -> str:
    if campo.is_relation:
        alvo = getattr(instancia, campo.name, None)
        return f"{alvo} #{alvo.pk}" if alvo is not None else "-"
    if getattr(campo, "choices", None):
        metodo = getattr(instancia, f"get_{campo.name}_display", None)
        if metodo:
            return formatar(metodo(), campo)
    return formatar(getattr(instancia, campo.name, None), campo)


def _coluna_texto(instancia, nome: str) -> str:
    campo = None
    try:
        campo = instancia._meta.get_field(nome)
    except Exception:
        return formatar(getattr(instancia, nome, None))
    return valor_exibicao(instancia, campo)


def listar(tabela: TabelaPainel, termo: str = "", pagina: int = 0, por_pagina: int = 14) -> dict:
    qs = tabela.modelo.objects.all()
    termo = (termo or "").strip()
    if termo and tabela.busca:
        filtro = models.Q()
        for campo in tabela.busca:
            filtro |= models.Q(**{f"{campo}__icontains": termo})
        qs = qs.filter(filtro)
    if tabela.ordem:
        qs = qs.order_by(tabela.ordem)

    total = qs.count()
    paginas = max((total + por_pagina - 1) // por_pagina, 1)
    pagina = max(0, min(pagina, paginas - 1))
    recorte = qs.select_related()[pagina * por_pagina : (pagina + 1) * por_pagina]

    linhas = [
        {"pk": obj.pk, "valores": [_coluna_texto(obj, c) for c in tabela.colunas]}
        for obj in recorte
    ]
    return {
        "chave": tabela.chave,
        "rotulo": tabela.rotulo,
        "colunas": [c.replace("_", " ").upper() for c in tabela.colunas],
        "linhas": linhas,
        "total": total,
        "pagina": pagina,
        "paginas": paginas,
        "termo": termo,
        "somente_leitura": tabela.somente_leitura,
        "pode_excluir": tabela.pode_excluir and not tabela.somente_leitura,
        "nota": tabela.nota,
    }


def detalhar(tabela: TabelaPainel, pk) -> dict:
    obj = tabela.modelo.objects.get(pk=pk)
    campos = []
    for campo in campos_do_modelo(tabela):
        campos.append(
            {
                "nome": campo.name,
                "rotulo": campo.name.replace("_", " ").upper(),
                "valor": valor_exibicao(obj, campo),
                "editavel": campo_editavel(tabela, campo),
                "tipo": _tipo_legivel(campo),
                "opcoes": [str(v) for v, _ in (campo.choices or [])] if getattr(campo, "choices", None) else [],
            }
        )
    return {
        "chave": tabela.chave,
        "rotulo": tabela.rotulo,
        "pk": obj.pk,
        "titulo": str(obj),
        "campos": campos,
        "somente_leitura": tabela.somente_leitura,
        "pode_excluir": tabela.pode_excluir and not tabela.somente_leitura,
        "nota": tabela.nota,
    }


def _tipo_legivel(campo) -> str:
    if campo.is_relation:
        return f"VINCULO ({campo.related_model.__name__}) - informe o ID"
    if isinstance(campo, models.BooleanField):
        return "SIM/NAO"
    if isinstance(campo, models.DateTimeField):
        return "DATA E HORA (DD/MM/AAAA HH:MM)"
    if isinstance(campo, models.DateField):
        return "DATA (DD/MM/AAAA)"
    if isinstance(campo, models.DecimalField):
        return "VALOR (use virgula ou ponto)"
    if isinstance(campo, (models.IntegerField, models.FloatField)):
        return "NUMERO"
    if _e_arquivo(campo):
        return "ARQUIVO (so pela tela do modulo)"
    if getattr(campo, "choices", None):
        return "OPCAO"
    return "TEXTO"


def _converter(campo, texto: str, instancia):
    """Texto digitado no terminal -> valor do campo, no jeitinho brasileiro."""
    texto = (texto or "").strip()

    if texto == "":
        if campo.null:
            return None
        if getattr(campo, "blank", False) and isinstance(campo, (models.CharField, models.TextField)):
            return ""
        raise ValidationError("Este campo nao aceita vazio.")

    if isinstance(campo, models.BooleanField):
        positivo = texto.upper() in {"S", "SIM", "1", "V", "TRUE", "X"}
        negativo = texto.upper() in {"N", "NAO", "0", "F", "FALSE"}
        if not positivo and not negativo:
            raise ValidationError("Responda SIM ou NAO (S/N).")
        return positivo

    if campo.is_relation:
        if not texto.isdigit():
            raise ValidationError("Informe o ID do registro vinculado (numero).")
        if not campo.related_model.objects.filter(pk=int(texto)).exists():
            raise ValidationError(f"Nao existe {campo.related_model.__name__} com ID {texto}.")
        return int(texto)

    if isinstance(campo, models.DateTimeField):
        return _converter_datahora(texto)

    if isinstance(campo, models.DateField):
        return _converter_data(texto)

    if isinstance(campo, models.DecimalField):
        try:
            return Decimal(texto.replace(".", "").replace(",", ".") if "," in texto else texto)
        except (InvalidOperation, ValueError):
            raise ValidationError("Valor invalido.")

    return campo.to_python(texto)


def _converter_data(texto: str) -> date:
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ValidationError("Data invalida. Use DD/MM/AAAA.")


def _converter_datahora(texto: str) -> datetime:
    for formato in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%d/%m/%Y"):
        try:
            bruto = datetime.strptime(texto, formato)
            break
        except ValueError:
            continue
    else:
        raise ValidationError("Data/hora invalida. Use DD/MM/AAAA HH:MM.")
    return timezone.make_aware(bruto, timezone.get_current_timezone()) if timezone.is_naive(bruto) else bruto


def alterar_campo(tabela: TabelaPainel, pk, nome_campo: str, texto: str) -> tuple[models.Model, str, str]:
    """Altera um campo e devolve (registro, valor anterior, valor novo).

    Levanta `ValidationError` quando a tabela e so leitura, o campo nao pode ser
    editado ou o texto digitado nao serve para o campo.
    """
    if tabela.somente_leitura:
        raise ValidationError("Esta tabela e somente leitura.")

    obj = tabela.modelo.objects.get(pk=pk)
    try:
        campo = obj._meta.get_field(nome_campo)
    except Exception:
        raise ValidationError("Campo inexistente.")

    if not campo_editavel(tabela, campo):
        raise ValidationError("Este campo nao pode ser editado pelo painel.")

    anterior = valor_exibicao(obj, campo)
    valor = _converter(campo, texto, obj)

    if campo.is_relation:
        setattr(obj, campo.attname, valor)
    else:
        campo.clean(valor, obj)
        setattr(obj, campo.name, valor)

    obj.save()
    obj.refresh_from_db()
    return obj, anterior, valor_exibicao(obj, campo)


def excluir(tabela: TabelaPainel, pk) -> str:
    if tabela.somente_leitura or not tabela.pode_excluir:
        raise ValidationError("Esta tabela nao permite exclusao pelo painel.")
    obj = tabela.modelo.objects.get(pk=pk)
    rotulo = f"{obj} #{obj.pk}"
    obj.delete()
    return rotulo


def resumo_tabelas() -> list[dict]:
    """Lista das tabelas com a contagem de registros (tela inicial de DADOS)."""
    saida = []
    for tabela in TABELAS:
        saida.append(
            {
                "chave": tabela.chave,
                "rotulo": tabela.rotulo,
                "total": tabela.modelo.objects.count(),
                "somente_leitura": tabela.somente_leitura,
            }
        )
    return saida


def contagem_usuarios() -> int:
    return get_user_model().objects.count()
