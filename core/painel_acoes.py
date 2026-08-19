"""Acoes de fluxo dos modulos, disponiveis dentro do Painel do Titular.

A camada generica de `painel_dados.py` escreve direto na tabela — serve para
cadastro e correcao, mas **pula as regras do modulo**: abrir um chamado por ali
nao registra o evento na timeline nem dispara a notificacao por e-mail.

Este arquivo resolve isso sem duplicar regra nenhuma: cada acao aqui aponta para
a **mesma rota que a tela classica ja usa**. O terminal so monta o pedido
(perguntando ao operador o que falta) e mostra a resposta. Se a regra mudar na
tela classica, muda aqui junto, porque e o mesmo endpoint.

Como declarar uma acao nova:

- `tabela` e `escopo` dizem onde ela aparece (`registro` = dentro de um registro;
  `tabela` = na lista);
- `url_name` e a rota existente, com `args_do_registro` quando ela leva o id;
- `campos` sao os valores perguntados no terminal, um por vez;
- `payload_do_registro` copia dados do proprio registro para o pedido;
- `formato` diz como o pedido sai do terminal:
  - `json` (padrao) e `form`, para as rotas que esperam formulario;
  - `arquivo`, que abre o **seletor de arquivo do proprio computador** e manda o
    escolhido no campo `campo_arquivo` (a rota recebe em `request.FILES`);
  - `abrir`, que nao envia nada: so abre a URL numa aba nova, para o navegador
    fazer o que ja sabe fazer com PDF, planilha e imagem.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import AtendimentoHistorico, Chamado, PendenciaTI


@dataclass(frozen=True)
class CampoAcao:
    nome: str
    rotulo: str
    obrigatorio: bool = True
    tipo: str = "TEXTO"
    opcoes: tuple[str, ...] = ()


@dataclass(frozen=True)
class AcaoPainel:
    chave: str
    tecla: str
    rotulo: str
    tabela: str
    escopo: str  # "registro" | "tabela"
    url_name: str
    formato: str = "json"  # json | form | arquivo | abrir
    # Nome do campo de arquivo esperado pela rota (so para `formato="arquivo"`).
    campo_arquivo: str = ""
    campos: tuple[CampoAcao, ...] = ()
    payload_do_registro: tuple[tuple[str, str], ...] = ()
    payload_fixo: tuple[tuple[str, str], ...] = ()
    args_do_registro: tuple[str, ...] = ()
    confirma: str = ""
    nota: str = ""
    condicao: str = ""  # nome de um teste em `_CONDICOES`
    # Campo da resposta que identifica o registro criado. Quando existe, o
    # terminal joga esse valor na busca da lista: o registro recem-criado fica
    # na primeira linha, pronto para abrir.
    busca_resposta: str = ""


# Motivos de pausa = os status de "aguardando" do chamado (o backend confere).
_MOTIVOS_PAUSA = tuple(sorted(Chamado.STATUS_AGUARDANDO))
# A prioridade da pendencia e o numero da cor do card (1 = urgente ... 5 = minima),
# nao os nomes usados no chamado: o terminal pergunta exatamente o que a rota espera.
_PRIORIDADES_PENDENCIA = tuple(str(valor) for valor, _rotulo in PendenciaTI.PRIORIDADE_CHOICES)
_ROTULO_PRIORIDADE = "PRIORIDADE (" + ", ".join(
    f"{valor}={rotulo.upper()}" for valor, rotulo in PendenciaTI.PRIORIDADE_CHOICES
) + ")"


ACOES: tuple[AcaoPainel, ...] = (
    # ------------------------------------------------------------ chamados --
    AcaoPainel(
        chave="chamado_abrir",
        tecla="N",
        rotulo="ABRIR CHAMADO",
        tabela="chamados",
        escopo="tabela",
        url_name="create_ticket_kanban",
        formato="form",
        # As duas exigencias vem do proprio `AberturaChamadoForm` (titulo com 5+
        # e descricao com 10+ caracteres): o terminal avisa antes para o
        # operador nao levar o erro so no fim.
        campos=(
            CampoAcao("titulo", "TITULO DO CHAMADO (5+ LETRAS)"),
            CampoAcao("descricao", "DESCRICAO (10+ LETRAS)"),
        ),
        nota="Abre pela mesma rota do Kanban: gera o numero, registra o evento e notifica por e-mail.",
        busca_resposta="ticket_number",
    ),
    AcaoPainel(
        chave="chamado_play",
        tecla="P",
        rotulo="INICIAR ATENDIMENTO (PLAY)",
        tabela="chamados",
        escopo="registro",
        url_name="start_attendance",
        payload_do_registro=(("ticket_number", "numero"),),
        condicao="chamado_aberto",
    ),
    AcaoPainel(
        chave="chamado_pause",
        tecla="U",
        rotulo="PAUSAR O ATENDIMENTO",
        tabela="chamados",
        escopo="registro",
        url_name="finish_attendance",
        payload_do_registro=(("ticket_number", "numero"),),
        payload_fixo=(("action", AtendimentoHistorico.TIPO_ENCERRAMENTO_PAUSE),),
        campos=(
            CampoAcao("description", "O QUE FOI FEITO"),
            CampoAcao("pause_reason", "MOTIVO (VAZIO = SO PAUSAR)", obrigatorio=False, tipo="OPCAO", opcoes=_MOTIVOS_PAUSA),
        ),
        condicao="chamado_aberto",
    ),
    AcaoPainel(
        chave="chamado_stop",
        tecla="F",
        rotulo="FINALIZAR O CHAMADO (STOP)",
        tabela="chamados",
        escopo="registro",
        url_name="finish_attendance",
        payload_do_registro=(("ticket_number", "numero"),),
        payload_fixo=(("action", AtendimentoHistorico.TIPO_ENCERRAMENTO_STOP),),
        campos=(CampoAcao("description", "O QUE FOI FEITO"),),
        confirma="FINALIZAR E FECHAR ESTE CHAMADO?",
        condicao="chamado_aberto",
    ),
    AcaoPainel(
        chave="chamado_mover_atendente",
        tecla="M",
        rotulo="ATRIBUIR A UM ATENDENTE",
        tabela="chamados",
        escopo="registro",
        url_name="move_ticket",
        payload_do_registro=(("ticket_number", "numero"),),
        payload_fixo=(("target", "atendente"),),
        campos=(CampoAcao("attendant_id", "ID DO ATENDENTE", tipo="NUMERO"),),
        nota="O ID do atendente aparece na area USUARIOS.",
        condicao="chamado_aberto",
    ),
    AcaoPainel(
        chave="chamado_devolver",
        tecla="D",
        rotulo="DEVOLVER PARA CHAMADOS ABERTOS",
        tabela="chamados",
        escopo="registro",
        url_name="move_ticket",
        payload_do_registro=(("ticket_number", "numero"),),
        payload_fixo=(("target", "aberto"),),
        condicao="chamado_aberto",
    ),
    AcaoPainel(
        chave="chamado_responder",
        tecla="R",
        rotulo="RESPONDER (MENSAGEM AO SOLICITANTE)",
        tabela="chamados",
        escopo="registro",
        url_name="ticket_message_create",
        formato="form",
        args_do_registro=("numero",),
        campos=(CampoAcao("texto", "SUA MENSAGEM"),),
        nota="Entra na conversa do chamado, registra o comentario na linha do tempo e notifica por e-mail.",
    ),
    # ------------------------------------------------------------- pausas --
    AcaoPainel(
        chave="pausa_complementar",
        tecla="C",
        rotulo="COMPLEMENTAR O QUE FOI FEITO",
        tabela="pausas",
        escopo="registro",
        url_name="pausa_complementar",
        args_do_registro=("pk",),
        campos=(CampoAcao("description", "O QUE FOI FEITO NO PERIODO"),),
        nota="A pendencia e do proprio atendente: pelo painel so da para complementar as suas.",
        condicao="pausa_minha_e_pendente",
    ),
    # ---------------------------------------------------------- pendencias --
    AcaoPainel(
        chave="pendencia_criar",
        tecla="N",
        rotulo="NOVA PENDENCIA",
        tabela="pendencias",
        escopo="tabela",
        url_name="pendencia_create",
        # Titulo (3+) e descricao sao exigidos pela propria rota; a prioridade
        # pode ficar vazia, e a pendencia nasce sem cor.
        campos=(
            CampoAcao("titulo", "TITULO DA PENDENCIA (3+ LETRAS)"),
            CampoAcao("descricao", "DESCRICAO"),
            CampoAcao("prioridade", _ROTULO_PRIORIDADE, obrigatorio=False, tipo="OPCAO", opcoes=_PRIORIDADES_PENDENCIA),
        ),
        # Sem `busca_resposta`: a lista de pendencias so busca por titulo/descricao,
        # e a nova ja aparece na primeira linha (a lista vem da mais recente).
    ),
    AcaoPainel(
        chave="pendencia_prioridade",
        tecla="R",
        rotulo="TROCAR A PRIORIDADE",
        tabela="pendencias",
        escopo="registro",
        url_name="pendencia_priority",
        args_do_registro=("pk",),
        campos=(CampoAcao("prioridade", f"NOVA {_ROTULO_PRIORIDADE}", tipo="OPCAO", opcoes=_PRIORIDADES_PENDENCIA),),
        condicao="pendencia_aberta",
    ),
    AcaoPainel(
        chave="pendencia_converter",
        tecla="C",
        rotulo="CONVERTER EM CHAMADO",
        tabela="pendencias",
        escopo="registro",
        url_name="pendencia_convert",
        args_do_registro=("pk",),
        campos=(CampoAcao("attendant_id", "ID DO ATENDENTE", tipo="NUMERO"),),
        confirma="CONVERTER ESTA PENDENCIA EM CHAMADO?",
        nota="Abre o chamado com a mesma regra da tela: evento na timeline e notificacao.",
        condicao="pendencia_aberta",
    ),
    # --------------------------------------------------------- requisicoes --
    AcaoPainel(
        chave="requisicao_entregue",
        tecla="G",
        rotulo="MARCAR COMO ENTREGUE",
        tabela="requisicoes",
        escopo="registro",
        url_name="requisicao_marcar_entregue",
        args_do_registro=("pk",),
        confirma="MARCAR ESTA REQUISICAO COMO ENTREGUE?",
    ),
    AcaoPainel(
        chave="requisicao_desaprovar",
        tecla="D",
        rotulo="DESAPROVAR (VOLTA PARA APROVACAO)",
        tabela="requisicoes",
        escopo="registro",
        url_name="requisicao_desaprovar",
        args_do_registro=("pk",),
        confirma="REMOVER A APROVACAO DOS ORCAMENTOS?",
    ),
    AcaoPainel(
        chave="requisicao_nao_aprovar",
        tecla="J",
        rotulo="NAO APROVAR A COMPRA",
        tabela="requisicoes",
        escopo="registro",
        url_name="requisicao_nao_aprovar",
        args_do_registro=("pk",),
        confirma="MARCAR A REQUISICAO COMO NAO APROVADA?",
    ),
    AcaoPainel(
        chave="orcamento_aprovar",
        tecla="V",
        rotulo="APROVAR ESTE ORCAMENTO",
        tabela="orcamentos",
        escopo="registro",
        url_name="orcamento_aprovar",
        args_do_registro=("pk",),
        confirma="APROVAR ESTE ORCAMENTO?",
        nota="Aprova este e remove a aprovacao dos outros da mesma requisicao.",
    ),
    # -------------------------------------------------------- emprestimos --
    AcaoPainel(
        chave="emprestimo_termo",
        tecla="T",
        rotulo="BAIXAR O TERMO EM PDF",
        tabela="emprestimos",
        escopo="registro",
        url_name="emprestimo_baixar_termo",
        formato="abrir",
        args_do_registro=("pk",),
        condicao="emprestimo_com_termo",
    ),
    AcaoPainel(
        chave="emprestimo_anexar_assinado",
        tecla="Y",
        rotulo="ANEXAR O TERMO ASSINADO",
        tabela="emprestimos",
        escopo="registro",
        url_name="emprestimo_anexar_termo_assinado",
        formato="arquivo",
        campo_arquivo="termo_assinado",
        args_do_registro=("pk",),
        nota="Abre o seletor de arquivo do computador; o termo digitalizado sobe pela mesma rota da tela.",
    ),
    AcaoPainel(
        chave="emprestimo_ver_assinado",
        tecla="V",
        rotulo="ABRIR O TERMO ASSINADO",
        tabela="emprestimos",
        escopo="registro",
        url_name="emprestimo_termo_assinado",
        formato="abrir",
        args_do_registro=("pk",),
        condicao="emprestimo_com_assinado",
    ),
    AcaoPainel(
        chave="emprestimo_documentacao_ok",
        tecla="K",
        rotulo="MARCAR DOCUMENTACAO COMO OK",
        tabela="emprestimos",
        escopo="registro",
        url_name="emprestimo_marcar_ok",
        args_do_registro=("pk",),
        confirma="CONFIRMAR QUE A DOCUMENTACAO ASSINADA ESTA OK?",
        condicao="emprestimo_assinado_pendente_de_ok",
    ),
)


# Cada teste recebe o registro e quem esta operando o painel — algumas regras
# sao do registro (chamado encerrado) e outras da pessoa (a pausa e de quem
# atendeu, ninguem complementa a do outro).
_CONDICOES = {
    # Chamado encerrado nao recebe mais Play/Pause/Stop nem movimentacao.
    "chamado_aberto": lambda obj, usuario: getattr(obj, "status", None) not in Chamado.STATUS_ENCERRADOS,
    # Pendencia ja convertida vira historico.
    "pendencia_aberta": lambda obj, usuario: not getattr(obj, "convertido_em_chamado", False),
    # A rota so aceita a pausa do proprio atendente, e uma vez so.
    "pausa_minha_e_pendente": lambda obj, usuario: bool(
        obj.pendente and usuario is not None and obj.atendimento.atendente_id == usuario.pk
    ),
    "emprestimo_com_termo": lambda obj, usuario: bool(obj.termo_pdf),
    "emprestimo_com_assinado": lambda obj, usuario: bool(obj.termo_assinado),
    # So faz sentido dar o OK depois que o assinado subiu (a rota recusa antes).
    "emprestimo_assinado_pendente_de_ok": lambda obj, usuario: bool(obj.termo_assinado)
    and not obj.termo_assinado_ok,
}


def acoes_da_tabela(chave_tabela: str, escopo: str) -> list[AcaoPainel]:
    return [a for a in ACOES if a.tabela == chave_tabela and a.escopo == escopo]


def acao_por_chave(chave: str) -> AcaoPainel | None:
    return next((a for a in ACOES if a.chave == chave), None)


def serializar(acao: AcaoPainel, obj=None, usuario=None) -> dict | None:
    """Descreve a acao para o terminal, ja resolvida para este registro.

    Devolve `None` quando a acao nao cabe no registro (chamado encerrado,
    pendencia ja convertida, termo que ainda nao foi gerado), para o terminal
    nem oferecer a tecla.
    """
    from django.urls import reverse

    if acao.condicao and obj is not None:
        teste = _CONDICOES.get(acao.condicao)
        if teste and not teste(obj, usuario):
            return None

    args = [getattr(obj, nome) for nome in acao.args_do_registro] if obj is not None else []
    payload = {chave: valor for chave, valor in acao.payload_fixo}
    if obj is not None:
        for chave, atributo in acao.payload_do_registro:
            payload[chave] = getattr(obj, atributo)

    return {
        "chave": acao.chave,
        "tecla": acao.tecla,
        "rotulo": acao.rotulo,
        "url": reverse(acao.url_name, args=args) if args else reverse(acao.url_name),
        "formato": acao.formato,
        "campo_arquivo": acao.campo_arquivo,
        "payload": payload,
        "campos": [
            {
                "nome": c.nome,
                "rotulo": c.rotulo,
                "obrigatorio": c.obrigatorio,
                "tipo": c.tipo,
                "opcoes": list(c.opcoes),
            }
            for c in acao.campos
        ],
        "confirma": acao.confirma,
        "nota": acao.nota,
        "busca_resposta": acao.busca_resposta,
    }


def acoes_serializadas(chave_tabela: str, escopo: str, obj=None, usuario=None) -> list[dict]:
    saida = []
    for acao in acoes_da_tabela(chave_tabela, escopo):
        dados = serializar(acao, obj, usuario)
        if dados:
            saida.append(dados)
    return saida
