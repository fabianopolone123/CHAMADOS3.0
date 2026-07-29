"""Planilha mensal de atendimentos por atendente (modelo "Atendimentos TI Sidertec").

Gera o arquivo no mesmo formato da planilha que a TI ja preenchia a mao, a
partir do modelo versionado em `core/planilhas/modelo_atendimentos.xlsx` (todo o
layout, cores, formulas de resumo e larguras vem dele).

Regra central: **uma linha por periodo de atendimento**, ou seja, por cada
Play -> Pause/Stop (`AtendimentoHistorico`). Um mesmo chamado trabalhado em tres
dias gera tres linhas, exatamente como a planilha era preenchida a mao.

Colunas (linha 7 do modelo):

| Col | Cabecalho        | Conteudo                                              |
|-----|------------------|-------------------------------------------------------|
| A   | Tk               | vazio (nao usado nas planilhas atuais)                |
| B   | Data             | inicio do periodo (hora do Play)                      |
| C   | Contato          | solicitante do chamado                                |
| D   | Setor            | setor do solicitante, casado com a lista de Ramais    |
| E   | Notificacao      | o pedido: descricao do chamado (titulo se faltar)     |
| F   | Prioridade       | "Programada" (trabalho da TI) ou "Baixa"              |
| G   | Falha            | "N/A"                                                 |
| H   | Acao / Correcao  | o que foi feito no periodo (descricao do Pause/Stop)  |
| I   | Fechado          | fim do periodo (hora do Pause/Stop)                   |
| J   | Tempo            | formula `=I{n}-B{n}`                                  |
| K   | Acao Eficaz      | vazio (preenchido a mao)                              |
"""

from __future__ import annotations

import io
import re
from copy import copy
from datetime import date

import openpyxl
from django.conf import settings
from django.utils import timezone

from .models import AtendimentoHistorico, Chamado

MODELO_PATH = settings.BASE_DIR / "core" / "planilhas" / "modelo_atendimentos.xlsx"

PRIMEIRA_LINHA = 8  # linha 7 e o cabecalho; os dados comecam na 8
ULTIMA_LINHA_MODELO = 152  # ate onde o modelo ja vem formatado

# Origens de chamado criadas pela propria TI: na planilha entram como
# "Programada" (trabalho planejado), nao como demanda de usuario.
ORIGENS_TI = {"Kanban TI", "Pendencia TI"}

# A planilha e preenchida com apenas dois rotulos, seguindo o criterio que a TI
# ja usava a mao: "Programada" para o trabalho da propria TI e "Baixa" para o que
# vem de usuario - independente da prioridade gravada no chamado. Conferido
# contra a planilha de 05/2026 preenchida a mao, onde chamados que o sistema
# marca como "alta"/"critica" aparecem como "Baixa".
PRIORIDADE_TI = "Programada"
PRIORIDADE_USUARIO = "Baixa"

# Metadados que a migracao do sistema antigo anexou ao fim da descricao
# ("\n\nTipo legado: programado | Falha legado: software\n[ERP-TI-ID:1]"): sao
# controle interno e nao devem aparecer na planilha.
_META_LEGADO = re.compile(r"\n{1,2}Tipo legado:.*\Z|\n?\[ERP-TI-ID:\d+\]\s*\Z", re.DOTALL)

MESES_PT = [
    "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

FORMATO_DATA = "dd/mm/yyyy hh:mm"


def _fim_do_mes(ano: int, mes: int) -> date:
    return date(ano + (mes // 12), (mes % 12) + 1, 1)


def periodos_do_mes(atendente, ano: int, mes: int):
    """Periodos de atendimento do atendente que **comecaram** no mes.

    O recorte usa o inicio (Play) porque e ele que define a data da linha na
    planilha; um periodo que comeca dia 31 e termina dia 1 pertence ao mes em
    que comecou. Chamados encerrados direto pelo Stop (sem Play) nao geram
    periodo e, por decisao de uso, nao entram na planilha.
    """
    inicio = date(ano, mes, 1)
    return (
        AtendimentoHistorico.objects.select_related("chamado", "chamado__solicitante")
        .filter(atendente=atendente, iniciado_em__date__gte=inicio, iniciado_em__date__lt=_fim_do_mes(ano, mes))
        .order_by("iniciado_em", "id")
    )


def _prioridade_planilha(chamado: Chamado) -> str:
    """"Programada" para trabalho da propria TI; "Baixa" para demanda de usuario."""
    if (chamado.origem or "").strip() in ORIGENS_TI:
        return PRIORIDADE_TI
    # O sistema antigo tinha o tipo "programado", que veio no campo prioridade.
    if (chamado.prioridade or "").strip().lower() == "programada":
        return PRIORIDADE_TI
    solicitante = chamado.solicitante
    if solicitante is not None:
        from .permissions import is_admin_user, is_attendant_user

        if is_admin_user(solicitante) or is_attendant_user(solicitante):
            return PRIORIDADE_TI
    return PRIORIDADE_USUARIO


def _notificacao(chamado: Chamado) -> str:
    """O pedido como o usuario escreveu (a planilha a mao usa a descricao).

    Cai para o titulo quando nao ha descricao. Remove os metadados que a migracao
    do sistema antigo anexou no fim do texto.
    """
    texto = _META_LEGADO.sub("", (chamado.descricao or "").strip()).strip()
    return texto or chamado.titulo


def _copiar_estilo_linha(ws, origem: int, destino: int) -> None:
    """Replica o estilo de uma linha do modelo em outra (meses mais cheios)."""
    for col in range(1, 12):
        base = ws.cell(row=origem, column=col)
        nova = ws.cell(row=destino, column=col)
        nova._style = copy(base._style)
    if origem in ws.row_dimensions:
        ws.row_dimensions[destino].height = ws.row_dimensions[origem].height


def gerar_planilha(atendente, ano: int, mes: int, setor_por_solicitante=None, telefone_atendente: str = "") -> bytes:
    """Devolve os bytes do .xlsx do atendente para o mes informado.

    `setor_por_solicitante`: dict {user_id: setor} resolvido pela camada de view
    (vem da lista de Ramais). `telefone_atendente`: telefone que vai no
    cabecalho, ao lado do nome.
    """
    setor_por_solicitante = setor_por_solicitante or {}

    wb = openpyxl.load_workbook(MODELO_PATH)
    ws = wb.active
    ws.title = MESES_PT[mes - 1]

    nome_atendente = atendente.get_full_name() or atendente.username
    ws["A4"] = f"Atendimentos TI Sidertec - {mes:02d}/{ano}"
    ws["A5"] = f"{nome_atendente} {telefone_atendente}".strip()

    linha = PRIMEIRA_LINHA
    for periodo in periodos_do_mes(atendente, ano, mes):
        if linha > ULTIMA_LINHA_MODELO:
            _copiar_estilo_linha(ws, PRIMEIRA_LINHA, linha)

        chamado = periodo.chamado
        solicitante_id = chamado.solicitante_id

        ws.cell(row=linha, column=2, value=timezone.localtime(periodo.iniciado_em).replace(tzinfo=None))
        ws.cell(row=linha, column=2).number_format = FORMATO_DATA
        ws.cell(row=linha, column=3, value=_contato(chamado))
        ws.cell(row=linha, column=4, value=setor_por_solicitante.get(solicitante_id, ""))
        ws.cell(row=linha, column=5, value=_notificacao(chamado))
        ws.cell(row=linha, column=6, value=_prioridade_planilha(chamado))
        ws.cell(row=linha, column=7, value="N/A")
        ws.cell(row=linha, column=8, value=periodo.descricao_atividade or "")

        # Periodo ainda em andamento (Play aberto): "Fechado" e "Tempo" ficam em
        # branco - a formula de tempo sem o fim daria resultado negativo.
        if periodo.finalizado_em:
            ws.cell(row=linha, column=9, value=timezone.localtime(periodo.finalizado_em).replace(tzinfo=None))
            ws.cell(row=linha, column=9).number_format = FORMATO_DATA
            ws.cell(row=linha, column=10, value=f"=I{linha}-B{linha}")

        linha += 1

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _contato(chamado: Chamado) -> str:
    if chamado.solicitante_nome:
        return chamado.solicitante_nome
    if chamado.solicitante:
        return chamado.solicitante.get_full_name() or chamado.solicitante.username
    return ""


def nome_arquivo(atendente, ano: int, mes: int) -> str:
    """Mesmo padrao dos arquivos que a TI ja salva: "05-2026 - Fabiano.xlsx"."""
    nome = (atendente.first_name or atendente.get_full_name() or atendente.username).split()[0]
    return f"{mes:02d}-{ano} - {nome}.xlsx"
