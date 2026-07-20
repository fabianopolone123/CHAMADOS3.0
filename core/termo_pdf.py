"""Geracao do Termo de Responsabilidade (guarda e uso de equipamento) em PDF.

Usa ReportLab (puro Python, sem dependencias nativas). O layout espelha o
modelo institucional da Sidertec: cabecalho escuro, dados do colaborador,
equipamentos emprestados, condicoes, responsabilidades e area de assinaturas.
"""
from __future__ import annotations

from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_NAVY = colors.HexColor("#0f172a")
_SLATE = colors.HexColor("#334155")
_MUTED = colors.HexColor("#64748b")
_LABEL_BG = colors.HexColor("#f1f5f9")
_BORDER = colors.HexColor("#cbd5e1")
_GREEN = colors.HexColor("#22c55e")

_HEADER_HEIGHT = 78
_MARGIN = 42


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("SecTitle", parent=styles["Heading4"], textColor=_NAVY,
                              fontSize=11, spaceBefore=7, spaceAfter=4))
    styles.add(ParagraphStyle("Intro", parent=styles["Normal"], fontSize=9.5,
                              textColor=_SLATE, leading=14))
    styles.add(ParagraphStyle("Cell", parent=styles["Normal"], fontSize=9, leading=13,
                              textColor=_SLATE))
    styles.add(ParagraphStyle("CellLabel", parent=styles["Normal"], fontSize=8.5,
                              leading=12, textColor=_NAVY, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle("Resp", parent=styles["Normal"], fontSize=9, leading=13,
                              textColor=_SLATE, spaceAfter=4))
    styles.add(ParagraphStyle("SignName", parent=styles["Normal"], fontSize=9.5,
                              textColor=_NAVY, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle("SignRole", parent=styles["Normal"], fontSize=8,
                              textColor=_MUTED))
    return styles


def _draw_header_footer(canvas, doc, gerado_em_str):
    canvas.saveState()
    largura, altura = A4

    # ---- Cabecalho (faixa escura) ----
    canvas.setFillColor(_NAVY)
    canvas.rect(0, altura - _HEADER_HEIGHT, largura, _HEADER_HEIGHT, fill=1, stroke=0)

    # Marca (texto, adaptando o logo Sidertec)
    canvas.setFillColor(_GREEN)
    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawString(_MARGIN, altura - 38, "SIDERTEC")
    canvas.setFillColor(colors.HexColor("#cbd5e1"))
    canvas.setFont("Helvetica", 6)
    canvas.drawString(_MARGIN, altura - 50, "TECNOLOGIA EM ESTRUTURAS METALICAS")

    # Titulo (direita)
    canvas.setFillColor(colors.HexColor("#cbd5e1"))
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(largura - _MARGIN, altura - 26, "Departamento de TI")
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawRightString(largura - _MARGIN, altura - 45, "TERMO DE RESPONSABILIDADE")
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawRightString(largura - _MARGIN, altura - 60, "GUARDA E USO DE EQUIPAMENTO")

    # ---- Rodape ----
    canvas.setStrokeColor(_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(_MARGIN, 52, largura - _MARGIN, 52)
    canvas.setFillColor(_MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(_MARGIN, 42, f"Termo gerado pelo sistema em {gerado_em_str}.")

    # Rubrica (direita)
    canvas.setStrokeColor(_BORDER)
    canvas.line(largura - _MARGIN - 130, 42, largura - _MARGIN, 42)
    canvas.setFillColor(_MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(largura - _MARGIN, 32, "Rubrica")
    canvas.restoreState()


def _info_table(styles, linhas):
    dados = []
    for label, valor in linhas:
        dados.append([
            Paragraph(label, styles["CellLabel"]),
            Paragraph(valor or "-", styles["Cell"]),
        ])
    tabela = Table(dados, colWidths=[135, None])
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), _LABEL_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, _BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, _BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tabela


def _assinatura_bloco(styles, nome, papel, imagem_flowable=None):
    linhas = []
    if imagem_flowable is not None:
        linhas.append([imagem_flowable])
    else:
        linhas.append([Spacer(1, 30)])
    linhas.append([Paragraph(nome, styles["SignName"])])
    linhas.append([Paragraph(papel, styles["SignRole"])])
    bloco = Table(linhas, colWidths=[230])
    bloco.setStyle(TableStyle([
        ("LINEABOVE", (0, 1), (0, 1), 0.7, _SLATE),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (0, 0), 0),
        ("TOPPADDING", (0, 1), (0, 1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
    ]))
    return bloco


def gerar_termo_pdf_bytes(emprestimo, aplicar_assinatura: bool = False) -> bytes:
    """Gera o PDF do termo e retorna os bytes.

    `aplicar_assinatura` embute a imagem da assinatura do responsavel (ja
    validada por senha na view). Caso contrario, deixa apenas a linha em branco.
    """
    styles = _styles()
    buffer = BytesIO()
    gerado_em = timezone.localtime(timezone.now()).strftime("%d/%m/%Y %H:%M")

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
        topMargin=_HEADER_HEIGHT + 22,
        bottomMargin=64,
        title=f"Termo de Responsabilidade - {emprestimo.colaborador_nome}",
    )

    elementos = []

    intro = (
        "Pelo presente termo, a Sidertec registra o emprestimo em comodato do equipamento "
        "abaixo ao colaborador identificado neste documento, que declara receber o bem em boas "
        "condicoes de uso e se compromete a zelar, conservar e devolver quando solicitado."
    )
    elementos.append(Paragraph(intro, styles["Intro"]))
    elementos.append(Spacer(1, 10))

    # Dados do colaborador
    elementos.append(Paragraph("Dados do colaborador", styles["SecTitle"]))
    elementos.append(_info_table(styles, [
        ("Nome", emprestimo.colaborador_nome),
        ("Empresa", emprestimo.empresa),
        ("Documento / CPF", emprestimo.cpf),
        ("E-mail", emprestimo.email),
        ("Telefone", emprestimo.telefone),
    ]))
    elementos.append(Spacer(1, 6))

    # Equipamentos emprestados (ativos) e, em seguida, os ja devolvidos.
    equipamentos = list(emprestimo.equipamentos.all())
    ativos = [e for e in equipamentos if e.data_devolucao is None]
    devolvidos = [e for e in equipamentos if e.data_devolucao is not None]

    def _detalhes_equip(equip, incluir_devolucao=False):
        detalhes = [f"<b>{equip.descricao_completa}</b>"]
        serie_patr = []
        if equip.numero_serie:
            serie_patr.append(f"Serie: {equip.numero_serie}")
        if equip.patrimonio_etiqueta:
            serie_patr.append(f"Patrimonio / etiqueta: {equip.patrimonio_etiqueta}")
        if serie_patr:
            detalhes.append(" | ".join(serie_patr))
        if equip.acessorios_entregues:
            detalhes.append(f"Acessorios: {equip.acessorios_entregues}")
        datas = f"Emprestado em {equip.data_emprestimo_display}"
        if incluir_devolucao:
            datas += f" | Devolvido em {equip.data_devolucao_display}"
        detalhes.append(datas)
        return "<br/>".join(detalhes)

    elementos.append(Paragraph("Equipamentos emprestados", styles["SecTitle"]))
    linhas_equip = []
    if not ativos:
        linhas_equip.append(("Equipamento", "-"))
    for indice, equip in enumerate(ativos, start=1):
        linhas_equip.append((f"Equipamento {indice}", _detalhes_equip(equip)))
    elementos.append(_info_table(styles, linhas_equip))
    elementos.append(Spacer(1, 6))

    if devolvidos:
        elementos.append(Paragraph("Equipamentos ja devolvidos", styles["SecTitle"]))
        linhas_dev = []
        for indice, equip in enumerate(devolvidos, start=1):
            linhas_dev.append((f"Devolvido {indice}", _detalhes_equip(equip, incluir_devolucao=True)))
        elementos.append(_info_table(styles, linhas_dev))
        elementos.append(Spacer(1, 6))

    # Condicoes do emprestimo
    elementos.append(Paragraph("Condicoes do emprestimo", styles["SecTitle"]))
    elementos.append(_info_table(styles, [
        ("Data do emprestimo", emprestimo.data_emprestimo.strftime("%d/%m/%Y") if emprestimo.data_emprestimo else "-"),
        ("Data prevista para devolucao", emprestimo.devolucao_display),
        ("Observacoes internas", emprestimo.observacoes_internas or "-"),
    ]))
    elementos.append(Spacer(1, 10))

    # Responsabilidades
    elementos.append(Paragraph("Responsabilidades do colaborador", styles["SecTitle"]))
    responsabilidades = [
        "1 - Se os equipamentos forem danificados ou inutilizados por mau uso, negligencia ou "
        "extravio, devera ressarcir a SIDERTEC o valor de mercado dos mesmos e sera de "
        "responsabilidade do colaborador a aquisicao imediata dos novos equipamentos;",
        "2 - Em caso de dano, inutilizacao ou extravio dos equipamentos, o colaborador devera "
        "comunicar imediatamente a SIDERTEC - TI.",
        "3 - Os equipamentos emprestados estarao sujeitos a acesso, monitoramento e inspecao "
        "pela SIDERTEC quando houver necessidade.",
    ]
    for texto in responsabilidades:
        elementos.append(Paragraph(texto, styles["Resp"]))
    elementos.append(Spacer(1, 16))

    # Assinaturas
    imagem_assinatura = None
    assinatura = emprestimo.assinatura_responsavel
    nome_responsavel = assinatura.nome_responsavel if assinatura else "Responsavel TI"
    if aplicar_assinatura and assinatura and assinatura.imagem_assinatura:
        try:
            img = RLImage(assinatura.imagem_assinatura.path, width=120, height=40, kind="proportional")
            imagem_assinatura = img
        except Exception:
            imagem_assinatura = None

    bloco_colab = _assinatura_bloco(styles, emprestimo.colaborador_nome, "Assinatura do colaborador")
    bloco_resp = _assinatura_bloco(styles, nome_responsavel, "Responsavel TI pelo emprestimo", imagem_assinatura)
    assinaturas = Table([[bloco_colab, bloco_resp]], colWidths=[250, 250])
    assinaturas.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("LEFTPADDING", (1, 0), (1, 0), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elementos.append(assinaturas)

    doc.build(
        elementos,
        onFirstPage=lambda c, d: _draw_header_footer(c, d, gerado_em),
        onLaterPages=lambda c, d: _draw_header_footer(c, d, gerado_em),
    )
    return buffer.getvalue()
