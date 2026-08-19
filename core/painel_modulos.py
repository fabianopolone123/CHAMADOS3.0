"""Ponte entre os modulos do menu lateral e o Painel do Titular.

O painel nao e so uma tela de configuracao: ele e a **outra interface** do
sistema. Este arquivo diz, para cada botao do menu (`core/menu.py`), o que
existe dentro dele no terminal:

- `tabelas`: as tabelas do modulo (chaves de `core/painel_dados.py`), na ordem
  em que fazem sentido — a primeira e a principal;
- `nota`: o que ainda **so** existe na interface classica (upload de arquivo,
  geracao de PDF, aprovacao, importacao), para o operador nao ficar procurando.

Modulo sem tabela propria (Permissoes, E-mail) aponta para a area equivalente
do painel.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import painel_dados
from .menu import ITEM_POR_CHAVE, ITENS_PADRAO


@dataclass(frozen=True)
class ModuloPainel:
    chave: str
    tabelas: tuple[str, ...] = ()
    area: str = ""  # area do painel quando o modulo nao e uma tabela
    nota: str = ""


MODULOS: tuple[ModuloPainel, ...] = (
    ModuloPainel(
        chave="chamados",
        tabelas=(
            "chamados",
            "atendimentos",
            "mensagens",
            "eventos",
            "pendencias",
            "pausas",
            "chamado_anexos",
            "mensagem_anexos",
        ),
        nota="Mover o chamado aqui e por tecla (M atribui, D devolve) no lugar de arrastar o card.",
    ),
    ModuloPainel(
        chave="contratos",
        tabelas=(
            "requisicoes",
            "orcamentos",
            "suborcamentos",
            "orcamento_documentos",
            "suborcamento_documentos",
        ),
        nota="Fotos, documentos e as copias para WhatsApp/e-mail continuam na tela de Requisicoes.",
    ),
    ModuloPainel(
        chave="emprestimos",
        tabelas=("emprestimos", "equipamentos", "equipamento_fotos", "assinaturas"),
        nota="Termo em PDF, assinatura e anexos continuam na tela de Emprestimos.",
    ),
    ModuloPainel(chave="documentos", tabelas=("documentos", "documento_anexos"), nota="Os anexos continuam na tela de Documentos."),
    ModuloPainel(chave="insumos", tabelas=("insumos", "retiradas")),
    ModuloPainel(
        chave="emails",
        tabelas=("emails",),
        nota="A importacao do CSV do Google Workspace continua na tela de Emails.",
    ),
    ModuloPainel(chave="ramais", tabelas=("ramais",)),
    ModuloPainel(chave="licencas", tabelas=("softwares", "licencas")),
    ModuloPainel(chave="ips", tabelas=("ips",)),
    ModuloPainel(chave="servicos_feitos", tabelas=("servicos", "servico_anexos"), nota="Os anexos de NF/orcamento continuam na tela do modulo."),
    ModuloPainel(chave="contratos_ti", tabelas=("contratos_ti", "contrato_ti_anexos"), nota="Os anexos continuam na tela de Contratos."),
    ModuloPainel(chave="futura_digital", tabelas=("futura",), nota="O documento da fatura continua na tela da Futura Digital."),
    ModuloPainel(chave="dicas", tabelas=("dicas",), nota="O anexo da dica continua na tela de Dicas."),
    ModuloPainel(chave="starlinks", tabelas=("starlinks",)),
    ModuloPainel(
        chave="cofre",
        tabelas=("cofre", "cofre_auditoria"),
        nota="A senha continua so abrindo com a senha-mestra, e cada revelacao fica na auditoria do Cofre.",
    ),
    ModuloPainel(
        chave="email_config",
        tabelas=("email_config",),
        nota="A senha do SMTP e o e-mail de teste tem acao propria; o resto se ajusta campo a campo.",
    ),
    ModuloPainel(chave="permissoes", area="usuarios", nota="Perfis e acessos sao tratados na area USUARIOS do painel."),
)

MODULO_POR_CHAVE: dict[str, ModuloPainel] = {m.chave: m for m in MODULOS}


def modulos_para_painel() -> list[dict]:
    """Lista dos modulos na ordem do menu, com o rotulo em uso e o tamanho."""
    from .models import ItemMenuConfig

    ajustes = {c.chave: c for c in ItemMenuConfig.objects.all()}
    saida = []
    for item in ITENS_PADRAO:
        modulo = MODULO_POR_CHAVE.get(item.chave)
        if not modulo:
            continue
        ajuste = ajustes.get(item.chave)
        total = sum(
            painel_dados.TABELA_POR_CHAVE[c].modelo.objects.count()
            for c in modulo.tabelas
            if c in painel_dados.TABELA_POR_CHAVE
        )
        saida.append(
            {
                "chave": item.chave,
                "rotulo": (ajuste.rotulo if ajuste and ajuste.rotulo else item.rotulo),
                "tabelas": len(modulo.tabelas),
                "registros": total,
                "area": modulo.area,
                "no_menu": bool(ajuste.visivel) if ajuste else True,
            }
        )

    ordem = {c.chave: i for i, c in enumerate(ITENS_PADRAO)}
    posicao = {
        chave: (ajustes[chave].ordem if chave in ajustes and ajustes[chave].ordem is not None else ordem[chave])
        for chave in ordem
    }
    saida.sort(key=lambda m: (posicao[m["chave"]], ordem[m["chave"]]))
    return saida


def detalhar_modulo(chave: str) -> dict | None:
    """Tabelas e avisos de um modulo, para a tela do modulo no terminal."""
    modulo = MODULO_POR_CHAVE.get(chave)
    if not modulo:
        return None

    item = ITEM_POR_CHAVE[chave]
    from .models import ItemMenuConfig

    ajuste = ItemMenuConfig.objects.filter(chave=chave).first()
    tabelas = []
    for indice, tabela_chave in enumerate(modulo.tabelas):
        tabela = painel_dados.TABELA_POR_CHAVE.get(tabela_chave)
        if not tabela:
            continue
        tabelas.append(
            {
                "chave": tabela.chave,
                "rotulo": tabela.rotulo,
                "total": tabela.modelo.objects.count(),
                "principal": indice == 0,
                "somente_leitura": tabela.somente_leitura,
            }
        )

    return {
        "chave": chave,
        "rotulo": (ajuste.rotulo if ajuste and ajuste.rotulo else item.rotulo),
        "url_name": item.url_name,
        "tabelas": tabelas,
        "area": modulo.area,
        "nota": modulo.nota,
    }
