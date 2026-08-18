"""Catalogo dos itens do menu lateral de TI.

Fonte unica dos itens do menu: chave, rota, rotulo padrao e icone. O que o
titular altera no Painel (rotulo, ordem e visibilidade) fica em `ItemMenuConfig`
e e aplicado por `itens_menu_ti()`; este catalogo continua sendo o padrao de
fabrica, usado tambem para restaurar.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.utils.safestring import mark_safe


@dataclass(frozen=True)
class ItemMenu:
    chave: str
    url_name: str
    rotulo: str
    icone: str


ITENS_PADRAO: tuple[ItemMenu, ...] = (
    ItemMenu(
        chave="chamados",
        url_name="tickets_dashboard",
        rotulo="Chamados",
        icone="""
        <rect x="3" y="4" width="6" height="16" rx="1.5"></rect>
        <rect x="10.5" y="4" width="6" height="10" rx="1.5"></rect>
        <rect x="18" y="4" width="3" height="16" rx="1.5"></rect>
        """,
    ),
    ItemMenu(
        chave="contratos",
        url_name="contratos_dashboard",
        rotulo="Requisicoes",
        icone="""
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"></path>
        <path d="M14 2v6h6"></path>
        <path d="M9 13h6"></path>
        <path d="M9 17h4"></path>
        """,
    ),
    ItemMenu(
        chave="emprestimos",
        url_name="emprestimos_dashboard",
        rotulo="Emprestimos",
        icone="""
        <rect x="2" y="7" width="20" height="14" rx="2"></rect>
        <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
        """,
    ),
    ItemMenu(
        chave="documentos",
        url_name="documentos_dashboard",
        rotulo="Documentos",
        icone="""
        <path d="M4 4a2 2 0 0 1 2-2h7l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2Z"></path>
        <path d="M13 2v6h6"></path>
        """,
    ),
    ItemMenu(
        chave="insumos",
        url_name="insumos_dashboard",
        rotulo="Insumos",
        icone="""
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"></path>
        <path d="m3.3 7 8.7 5 8.7-5"></path>
        <path d="M12 22V12"></path>
        """,
    ),
    ItemMenu(
        chave="emails",
        url_name="emails_dashboard",
        rotulo="Emails",
        icone="""
        <rect x="3" y="5" width="18" height="14" rx="2"></rect>
        <path d="m3 7 9 6 9-6"></path>
        """,
    ),
    ItemMenu(
        chave="ramais",
        url_name="ramais_dashboard",
        rotulo="Ramais",
        icone="""
        <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.9.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92Z"></path>
        """,
    ),
    ItemMenu(
        chave="licencas",
        url_name="licencas_dashboard",
        rotulo="Licencas",
        icone="""
        <path d="M7.5 12.5 3 17a2.83 2.83 0 0 0 4 4l4.5-4.5"></path>
        <circle cx="16.5" cy="7.5" r="4.5"></circle>
        <path d="m13.3 10.7-2.8 2.8"></path>
        <path d="m9 13 2 2"></path>
        """,
    ),
    ItemMenu(
        chave="ips",
        url_name="ips_dashboard",
        rotulo="IPs",
        icone="""
        <rect x="2" y="3" width="20" height="8" rx="1.5"></rect>
        <rect x="2" y="13" width="20" height="8" rx="1.5"></rect>
        <path d="M6 7h.01"></path>
        <path d="M6 17h.01"></path>
        <path d="M10 7h8"></path>
        <path d="M10 17h8"></path>
        """,
    ),
    ItemMenu(
        chave="servicos_feitos",
        url_name="servicos_feitos_dashboard",
        rotulo="Servicos feitos",
        icone="""
        <path d="M9 11l3 3L22 4"></path>
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
        """,
    ),
    ItemMenu(
        chave="contratos_ti",
        url_name="contratos_ti_dashboard",
        rotulo="Contratos",
        icone="""
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"></path>
        <path d="M14 2v6h6"></path>
        <path d="M9 15l2 2 4-4"></path>
        """,
    ),
    ItemMenu(
        chave="futura_digital",
        url_name="futura_digital_dashboard",
        rotulo="Futura Digital",
        icone="""
        <path d="M6 9V2h12v7"></path>
        <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path>
        <rect x="6" y="14" width="12" height="8" rx="1"></rect>
        """,
    ),
    ItemMenu(
        chave="dicas",
        url_name="dicas_dashboard",
        rotulo="Dicas",
        icone="""
        <path d="M9 18h6"></path>
        <path d="M10 22h4"></path>
        <path d="M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.3 1 2.1v.2h6v-.2c0-.8.4-1.6 1-2.1A7 7 0 0 0 12 2Z"></path>
        """,
    ),
    ItemMenu(
        chave="starlinks",
        url_name="starlinks_dashboard",
        rotulo="Starlinks",
        icone="""
        <path d="M2 12a10 10 0 0 1 10-10"></path>
        <path d="M5 15a6 6 0 0 1 6-6"></path>
        <circle cx="6" cy="18" r="1.5"></circle>
        <path d="M14 4l6 6-8 8"></path>
        """,
    ),
    ItemMenu(
        chave="cofre",
        url_name="cofre_dashboard",
        rotulo="Cofre",
        icone="""
        <rect x="3" y="11" width="18" height="11" rx="2"></rect>
        <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
        <circle cx="12" cy="16" r="1"></circle>
        """,
    ),
    ItemMenu(
        chave="email_config",
        url_name="email_config",
        rotulo="E-mail",
        icone="""
        <rect x="3" y="5" width="18" height="14" rx="2"></rect>
        <path d="m3 7 9 6 9-6"></path>
        <circle cx="18" cy="6" r="3" fill="currentColor" stroke="none"></circle>
        """,
    ),
    ItemMenu(
        chave="permissoes",
        url_name="permissions",
        rotulo="Permissoes",
        icone="""
        <path d="M12 2 4 5v6c0 5 3.4 8.3 8 11 4.6-2.7 8-6 8-11V5l-8-3Z"></path>
        <path d="m9 12 2 2 4-4"></path>
        """,
    ),
)

ITEM_POR_CHAVE: dict[str, ItemMenu] = {item.chave: item for item in ITENS_PADRAO}
CHAVES_PADRAO: tuple[str, ...] = tuple(item.chave for item in ITENS_PADRAO)


def itens_menu_ti() -> list[dict]:
    """Menu lateral ja resolvido: padrao de fabrica + ajustes do titular.

    Devolve dicionarios prontos para o template (rotulo final, ordem final e
    apenas os itens visiveis). Chaves de configuracao que nao existem mais no
    catalogo sao ignoradas, entao remover um modulo do sistema nunca quebra o
    menu.
    """
    from .models import ItemMenuConfig

    config = {c.chave: c for c in ItemMenuConfig.objects.all()}
    resolvidos = []
    for ordem_padrao, item in enumerate(ITENS_PADRAO):
        ajuste = config.get(item.chave)
        if ajuste and not ajuste.visivel:
            continue
        resolvidos.append(
            {
                "chave": item.chave,
                "url_name": item.url_name,
                "rotulo": (ajuste.rotulo if ajuste and ajuste.rotulo else item.rotulo),
                "icone": mark_safe(item.icone),
                "ordem": (ajuste.ordem if ajuste and ajuste.ordem is not None else ordem_padrao),
                "ordem_padrao": ordem_padrao,
            }
        )

    resolvidos.sort(key=lambda i: (i["ordem"], i["ordem_padrao"]))
    return resolvidos


def itens_menu_para_painel() -> list[dict]:
    """Mesma lista do menu, mas com TODOS os itens (inclusive os escondidos),
    para a tela de Interface do Painel do Titular."""
    from .models import ItemMenuConfig

    config = {c.chave: c for c in ItemMenuConfig.objects.all()}
    linhas = []
    for ordem_padrao, item in enumerate(ITENS_PADRAO):
        ajuste = config.get(item.chave)
        linhas.append(
            {
                "chave": item.chave,
                "rotulo": (ajuste.rotulo if ajuste and ajuste.rotulo else item.rotulo),
                "rotulo_padrao": item.rotulo,
                "visivel": (ajuste.visivel if ajuste else True),
                "ordem": (ajuste.ordem if ajuste and ajuste.ordem is not None else ordem_padrao),
                "ordem_padrao": ordem_padrao,
                "alterado": bool(
                    ajuste
                    and (
                        not ajuste.visivel
                        or (ajuste.rotulo and ajuste.rotulo != item.rotulo)
                        or (ajuste.ordem is not None and ajuste.ordem != ordem_padrao)
                    )
                ),
            }
        )

    linhas.sort(key=lambda i: (i["ordem"], i["ordem_padrao"]))
    return linhas
