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
    # Campos que aparecem mas nao podem ser escritos pela camada generica porque
    # ha uma rota dona deles: mexer no saldo do insumo na mao, por exemplo, muda
    # o numero e deixa o extrato de movimentacoes mentindo. Quem altera e a acao
    # de fluxo (entrada/retirada), que grava o movimento junto.
    campos_travados: tuple[str, ...] = ()
    # Recorte fixo da tabela: pares (lookup, valor) aplicados sempre, para a
    # tabela existir por um proposito e nao como despejo do modelo. Usado nas
    # pausas automaticas, que so interessam enquanto falta complementar.
    filtro: tuple[tuple[str, object], ...] = ()
    nota: str = ""
    campos_ocultos: tuple[str, ...] = dataclass_field(default_factory=tuple)


TABELAS: tuple[TabelaPainel, ...] = (
    # --- Chamados ---------------------------------------------------------
    TabelaPainel(
        chave="chamados",
        rotulo="CHAMADOS",
        modelo=m.Chamado,
        colunas=("numero", "titulo"),
        busca=("numero", "titulo", "descricao", "solicitante__username", "solicitante__first_name"),
        ordem="-criado_em",
    ),
    TabelaPainel(
        chave="atendimentos",
        rotulo="ATENDIMENTOS (PLAY/STOP)",
        modelo=m.AtendimentoHistorico,
        colunas=("chamado", "iniciado_em"),
        busca=("chamado__numero", "atendente__username", "descricao_atividade"),
        ordem="-iniciado_em",
    ),
    TabelaPainel(
        chave="pausas",
        rotulo="PAUSAS A COMPLEMENTAR",
        modelo=m.PausaAutomatica,
        colunas=("atendimento__chamado", "atendimento__atendente", "criado_em"),
        busca=("atendimento__chamado__numero", "atendimento__atendente__username"),
        ordem="-criado_em",
        # So aparece o que falta preencher: pausa complementada virou historico,
        # e o texto dela ja esta na linha do tempo do chamado (evento) e na
        # planilha do mes. Aqui a lista e uma fila de trabalho.
        filtro=(("complementado_em__isnull", True),),
        nota="Lista so as pausas que ainda faltam complementar; a tecla C so aparece nas suas.",
    ),
    TabelaPainel(
        chave="pendencias",
        rotulo="PENDENCIAS DE TI",
        modelo=m.PendenciaTI,
        colunas=("titulo",),
        busca=("titulo", "descricao"),
        ordem="-criado_em",
    ),
    TabelaPainel(
        chave="mensagens",
        rotulo="MENSAGENS DE CHAMADO",
        modelo=m.ChamadoMensagem,
        colunas=("chamado", "criado_em"),
        busca=("chamado__numero", "texto", "autor__username"),
        ordem="-criado_em",
    ),
    TabelaPainel(
        chave="eventos",
        rotulo="EVENTOS DE CHAMADO",
        modelo=m.ChamadoEvento,
        colunas=("chamado", "criado_em", "descricao"),
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
        colunas=("codigo", "titulo"),
        busca=("codigo", "titulo", "texto"),
        ordem="-criado_em",
        # Titulo, tipo e texto passam pela rota do modulo (tecla E), que registra
        # a edicao na linha do tempo da requisicao.
        campos_travados=("titulo", "tipo", "texto"),
    ),
    TabelaPainel(
        chave="orcamentos",
        rotulo="ORCAMENTOS",
        modelo=m.OrcamentoContrato,
        colunas=("requisicao", "titulo"),
        busca=("titulo", "loja", "requisicao__codigo"),
    ),
    TabelaPainel(
        chave="suborcamentos",
        rotulo="SUBORCAMENTOS",
        modelo=m.SuborcamentoContrato,
        colunas=("orcamento_pai", "titulo"),
        busca=("titulo", "loja"),
    ),
    # --- Modulos de TI ----------------------------------------------------
    TabelaPainel(
        chave="ramais",
        rotulo="RAMAIS",
        modelo=m.Ramal,
        colunas=("colaborador",),
        busca=("colaborador", "setor", "telefone", "ramal", "email"),
        ordem="colaborador",
    ),
    TabelaPainel(
        chave="emails",
        rotulo="CONTAS DE E-MAIL",
        modelo=m.ContaEmail,
        colunas=("email",),
        busca=("email", "primeiro_nome", "sobrenome", "departamento", "cargo"),
        ordem="email",
    ),
    TabelaPainel(
        chave="ips",
        rotulo="ENDERECOS IP",
        modelo=m.EnderecoIP,
        colunas=("endereco_ip", "nome"),
        busca=("endereco_ip", "nome", "fabricante", "mac", "observacoes"),
        ordem="endereco_ip",
    ),
    TabelaPainel(
        chave="softwares",
        rotulo="SOFTWARES (LICENCAS)",
        modelo=m.LicencaSoftware,
        colunas=("nome",),
        busca=("nome",),
        ordem="nome",
    ),
    TabelaPainel(
        chave="licencas",
        rotulo="LICENCAS",
        modelo=m.Licenca,
        colunas=("software", "usuario_atribuido"),
        busca=("usuario_atribuido", "email_vinculado", "serial", "software__nome"),
    ),
    TabelaPainel(
        chave="insumos",
        rotulo="INSUMOS",
        modelo=m.InsumoTI,
        colunas=("nome", "quantidade_atual"),
        busca=("nome", "descricao", "observacao"),
        ordem="nome",
        campos_travados=("quantidade_atual",),
        nota="O saldo so muda por entrada ou retirada, que gravam o extrato junto.",
    ),
    TabelaPainel(
        chave="retiradas",
        rotulo="RETIRADAS DE INSUMO",
        modelo=m.RetiradaInsumoTI,
        colunas=("insumo", "tipo", "criado_em"),
        busca=("insumo__nome", "entregue_para", "motivo"),
        ordem="-criado_em",
    ),
    TabelaPainel(
        chave="documentos",
        rotulo="DOCUMENTOS",
        modelo=m.DocumentoTI,
        colunas=("nome",),
        busca=("nome", "observacao"),
        ordem="-criado_em",
    ),
    TabelaPainel(
        chave="emprestimos",
        rotulo="EMPRESTIMOS",
        modelo=m.EmprestimoTI,
        colunas=("colaborador_nome",),
        busca=("colaborador_nome", "empresa", "cpf", "email"),
        ordem="-criado_em",
    ),
    TabelaPainel(
        chave="equipamentos",
        rotulo="EQUIPAMENTOS EMPRESTADOS",
        modelo=m.EquipamentoEmprestimoTI,
        colunas=("emprestimo", "tipo_equipamento"),
        busca=("tipo_equipamento", "marca", "modelo", "numero_serie", "emprestimo__colaborador_nome"),
    ),
    TabelaPainel(
        chave="servicos",
        rotulo="SERVICOS FEITOS",
        modelo=m.ServicoFeito,
        colunas=("nome_servico",),
        busca=("nome_servico", "empresa", "descricao"),
        ordem="-data_servico",
    ),
    TabelaPainel(
        chave="contratos_ti",
        rotulo="CONTRATOS",
        modelo=m.Contrato,
        colunas=("nome",),
        busca=("nome", "observacoes"),
        ordem="nome",
    ),
    TabelaPainel(
        chave="futura",
        rotulo="FUTURA DIGITAL",
        modelo=m.FuturaDigital,
        colunas=("mes_referencia",),
        busca=("nota_fiscal",),
        ordem="-mes_referencia",
    ),
    TabelaPainel(
        chave="dicas",
        rotulo="DICAS",
        modelo=m.Dica,
        colunas=("titulo",),
        busca=("titulo", "conteudo"),
        ordem="-criado_em",
    ),
    TabelaPainel(
        chave="starlinks",
        rotulo="STARLINKS",
        modelo=m.Starlink,
        colunas=("nome",),
        busca=("nome", "local", "email", "identificador", "numero_serie"),
        ordem="nome",
    ),
    TabelaPainel(
        chave="assinaturas",
        rotulo="ASSINATURAS DE RESPONSAVEL",
        modelo=m.AssinaturaResponsavelTI,
        colunas=("nome_responsavel",),
        busca=("nome_responsavel",),
        ordem="nome_responsavel",
        nota="A senha de autorizacao e o hash dela nunca aparecem; cadastre pela acao N.",
    ),
    # --- Anexos (o arquivo em si abre pela rota do modulo, tecla T) --------
    # Estao aqui para o titular achar e abrir qualquer arquivo do sistema sem
    # sair do terminal. O campo do arquivo nunca e editavel (regra geral do
    # painel); excluir a linha apaga o arquivo do disco pelo signal post_delete.
    TabelaPainel(
        chave="chamado_anexos",
        rotulo="ANEXOS DE CHAMADO",
        modelo=m.ChamadoAnexo,
        colunas=("chamado", "nome_original"),
        busca=("nome_original", "chamado__numero"),
        ordem="-enviado_em",
    ),
    TabelaPainel(
        chave="mensagem_anexos",
        rotulo="ANEXOS DE MENSAGEM",
        modelo=m.ChamadoMensagemAnexo,
        colunas=("mensagem", "nome_original"),
        busca=("nome_original", "mensagem__chamado__numero"),
        ordem="-enviado_em",
    ),
    TabelaPainel(
        chave="documento_anexos",
        rotulo="ANEXOS DE DOCUMENTO",
        modelo=m.DocumentoTIAnexo,
        colunas=("documento", "nome_original"),
        busca=("nome_original", "documento__nome"),
        ordem="-enviado_em",
    ),
    TabelaPainel(
        chave="servico_anexos",
        rotulo="ANEXOS DE SERVICO FEITO",
        modelo=m.ServicoFeitoAnexo,
        colunas=("servico", "nome_original"),
        busca=("nome_original", "servico__nome_servico"),
        ordem="-enviado_em",
    ),
    TabelaPainel(
        chave="contrato_ti_anexos",
        rotulo="ANEXOS DE CONTRATO TI",
        modelo=m.ContratoAnexo,
        colunas=("contrato", "nome_original"),
        busca=("nome_original", "contrato__nome"),
        ordem="-enviado_em",
    ),
    TabelaPainel(
        chave="orcamento_documentos",
        rotulo="DOCUMENTOS DE ORCAMENTO",
        modelo=m.OrcamentoDocumento,
        colunas=("orcamento", "nome_original"),
        busca=("nome_original", "orcamento__titulo"),
        ordem="-enviado_em",
    ),
    TabelaPainel(
        chave="suborcamento_documentos",
        rotulo="DOCUMENTOS DE SUBORCAMENTO",
        modelo=m.SuborcamentoDocumento,
        colunas=("suborcamento", "nome_original"),
        busca=("nome_original", "suborcamento__titulo"),
        ordem="-enviado_em",
    ),
    TabelaPainel(
        chave="equipamento_fotos",
        rotulo="FOTOS DE EQUIPAMENTO",
        modelo=m.FotoEquipamentoEmprestimoTI,
        colunas=("equipamento__emprestimo", "equipamento", "nome_original"),
        busca=("nome_original", "equipamento__tipo_equipamento"),
        ordem="-enviado_em",
    ),
    # --- Seguranca e sistema (so leitura) ---------------------------------
    TabelaPainel(
        chave="cofre",
        rotulo="COFRE DE SENHAS",
        modelo=m.CofreCredencial,
        colunas=("rotulo",),
        busca=("rotulo", "usuario"),
        somente_leitura=True,
        pode_excluir=False,
        nota="A senha nao e campo da tabela: abre com a senha-mestra (Z) e cada revelacao vai para a auditoria.",
    ),
    TabelaPainel(
        chave="email_config",
        rotulo="CONFIGURACAO DE E-MAIL (SMTP)",
        modelo=m.EmailConfig,
        colunas=("host", "usuario"),
        busca=("host", "usuario", "remetente", "emails_ti"),
        pode_excluir=False,
        nota="A senha do SMTP nao e campo daqui: troque pela acao Y, que usa a rota da tela.",
    ),
    TabelaPainel(
        chave="cofre_auditoria",
        rotulo="AUDITORIA DO COFRE",
        modelo=m.CofreAuditoria,
        colunas=("criado_em", "acao", "ator"),
        busca=("acao", "ator__username", "rotulo_credencial"),
        ordem="-criado_em",
        somente_leitura=True,
    ),
    TabelaPainel(
        chave="painel_auditoria",
        rotulo="ACOES DO PAINEL",
        modelo=m.PainelAuditoria,
        colunas=("criado_em", "acao", "alvo"),
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
    if campo.name in tabela.campos_travados:
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
    """Texto de uma coluna da lista, aceitando caminho pelo vinculo.

    `atendimento__chamado` existe porque ha tabela cuja identidade mora no avo:
    a pausa automatica so faz sentido junto do **chamado**, que estava perdido
    dentro do texto do atendimento ("fabiano - CH-000888"), lido de relance como
    se fosse o nome de uma pessoa.
    """
    if "__" in nome:
        alvo = instancia
        for parte in nome.split("__")[:-1]:
            alvo = getattr(alvo, parte, None)
            if alvo is None:
                return "-"
        return _coluna_texto(alvo, nome.split("__")[-1])

    campo = None
    try:
        campo = instancia._meta.get_field(nome)
    except Exception:
        return formatar(getattr(instancia, nome, None))
    return valor_exibicao(instancia, campo)


def consulta_base(tabela: TabelaPainel):
    """Queryset da tabela ja com o recorte fixo dela.

    Fica num lugar so porque a contagem que aparece na area MODULOS tem de bater
    com o que a lista mostra — numero que nao fecha com a tela e pior do que
    numero nenhum.
    """
    qs = tabela.modelo.objects.all()
    if tabela.filtro:
        qs = qs.filter(**dict(tabela.filtro))
    return qs


def listar(tabela: TabelaPainel, termo: str = "", pagina: int = 0, por_pagina: int = 14) -> dict:
    qs = consulta_base(tabela)
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
        "colunas": [c.split("__")[-1].replace("_", " ").upper() for c in tabela.colunas],
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


def campos_para_criacao(tabela: TabelaPainel) -> list[dict]:
    """Campos que o terminal pede ao criar um registro.

    Os obrigatorios (sem branco, sem nulo e sem valor padrao) vem primeiro: sao
    os unicos perguntados no fluxo de criacao. O resto se preenche depois, na
    tela do registro, campo a campo.
    """
    saida = []
    for campo in campos_do_modelo(tabela):
        if not campo_editavel(tabela, campo) or campo.name in _campos_gerados(tabela.modelo):
            continue
        obrigatorio = not campo.blank and not campo.null and not campo.has_default()
        saida.append(
            {
                "nome": campo.name,
                "rotulo": campo.name.replace("_", " ").upper(),
                "tipo": _tipo_legivel(campo),
                "opcoes": [str(v) for v, _ in (campo.choices or [])] if getattr(campo, "choices", None) else [],
                "obrigatorio": obrigatorio,
            }
        )
    saida.sort(key=lambda c: (not c["obrigatorio"],))
    return saida


def _campos_gerados(modelo) -> set[str]:
    """Campos que o proprio sistema preenche e o painel nao deve perguntar."""
    gerados = set()
    if hasattr(modelo, "gerar_numero"):
        gerados.add("numero")
    if hasattr(modelo, "gerar_codigo"):
        gerados.add("codigo")
    return gerados


def criar(tabela: TabelaPainel, valores: dict, usuario=None) -> models.Model:
    """Cria um registro a partir dos valores digitados no terminal.

    Cuida sozinho do que o sistema gera: o numero do chamado (`gerar_numero`) e
    o codigo da requisicao (gerado no `save`), e o autor (`criado_por`), que
    passa a ser quem esta operando o painel.
    """
    if tabela.somente_leitura:
        raise ValidationError("Esta tabela e somente leitura.")

    obj = tabela.modelo()
    nomes = {c.name for c in tabela.modelo._meta.get_fields() if getattr(c, "concrete", False)}

    if "numero" in nomes and hasattr(tabela.modelo, "gerar_numero") and not getattr(obj, "numero", ""):
        obj.numero = tabela.modelo.gerar_numero()

    # O Django nao recusa sozinho um campo obrigatorio vazio no `save()` (o
    # `blank` so vale em formulario), entao a checagem e feita aqui: sem isso o
    # painel gravaria registro pela metade, como um IP sem endereco.
    faltando = [
        campo["rotulo"]
        for campo in campos_para_criacao(tabela)
        if campo["obrigatorio"] and not str((valores or {}).get(campo["nome"], "")).strip()
    ]
    if faltando:
        raise ValidationError("Faltou preencher: " + ", ".join(faltando) + ".")

    for nome, texto in (valores or {}).items():
        try:
            campo = obj._meta.get_field(nome)
        except Exception:
            raise ValidationError(f"Campo inexistente: {nome}.")
        if not campo_editavel(tabela, campo):
            raise ValidationError(f"O campo {nome} nao pode ser preenchido pelo painel.")
        valor = _converter(campo, "" if texto is None else str(texto), obj)
        if campo.is_relation:
            setattr(obj, campo.attname, valor)
        else:
            campo.clean(valor, obj)
            setattr(obj, campo.name, valor)

    if usuario is not None and "criado_por" in nomes and not getattr(obj, "criado_por_id", None):
        obj.criado_por = usuario

    obj.save()
    obj.refresh_from_db()
    return obj


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
