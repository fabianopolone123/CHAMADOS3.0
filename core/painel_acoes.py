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
    fazer o que ja sabe fazer com PDF, planilha e imagem;
  - `copiar`, que le o JSON do modulo e monta o texto com o **mesmo codigo da
    tela** (`montador`), jogando o resultado na area de transferencia.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from .models import AtendimentoHistorico, Chamado, PendenciaTI, RequisicaoContrato


@dataclass(frozen=True)
class CampoAcao:
    nome: str
    rotulo: str
    obrigatorio: bool = True
    tipo: str = "TEXTO"
    opcoes: tuple[str, ...] = ()
    # Senha nao aparece enquanto e digitada (o painel fica em tela grande).
    mascara: bool = False


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
    # Para `formato="copiar"`: qual montador de texto do modulo o terminal usa
    # (o mesmo codigo da tela, em `static/js/requisicao_texto.js`).
    montador: str = ""
    # Deixa seguir sem arquivo (cadastro que aceita anexo, mas nao exige).
    arquivo_opcional: bool = False
    campos: tuple[CampoAcao, ...] = ()
    payload_do_registro: tuple[tuple[str, str], ...] = ()
    # Campos que vao no pedido com o valor que o registro tem hoje, sob o mesmo
    # nome. Rota de edicao de tela reescreve o registro inteiro a partir do POST
    # (e o que o modal faz, ja preenchido); mandar so o arquivo apagaria o resto.
    espelha_do_registro: tuple[str, ...] = ()
    payload_fixo: tuple[tuple[str, str], ...] = ()
    args_do_registro: tuple[str, ...] = ()
    confirma: str = ""
    nota: str = ""
    condicao: str = ""  # nome de um teste em `_CONDICOES`
    # Campo da resposta que identifica o registro criado. Quando existe, o
    # terminal joga esse valor na busca da lista: o registro recem-criado fica
    # na primeira linha, pronto para abrir.
    busca_resposta: str = ""
    # Campo da resposta que deve ser mostrado **literalmente** (sem caixa alta):
    # a senha revelada pelo Cofre so serve se vier exatamente como foi guardada.
    revela_resposta: str = ""


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
        chave="requisicao_criar",
        tecla="N",
        rotulo="NOVA REQUISICAO",
        tabela="requisicoes",
        escopo="tabela",
        url_name="requisicao_create",
        campos=(
            CampoAcao("titulo", "TITULO DA REQUISICAO (3+ LETRAS)"),
            CampoAcao(
                "tipo",
                "TIPO",
                tipo="OPCAO",
                opcoes=(RequisicaoContrato.TIPO_FISICA, RequisicaoContrato.TIPO_DIGITAL),
            ),
            CampoAcao("texto", "DESCRICAO", obrigatorio=False),
        ),
        nota="Gera o codigo REQ- e registra a criacao na linha do tempo da requisicao.",
        busca_resposta="codigo",
    ),
    AcaoPainel(
        chave="requisicao_editar",
        tecla="E",
        rotulo="EDITAR TITULO / TIPO / DESCRICAO",
        tabela="requisicoes",
        escopo="registro",
        url_name="requisicao_edit",
        args_do_registro=("pk",),
        espelha_do_registro=("titulo", "tipo", "texto"),
        campos=(
            CampoAcao("titulo", "TITULO (3+ LETRAS)"),
            CampoAcao(
                "tipo",
                "TIPO",
                tipo="OPCAO",
                opcoes=(RequisicaoContrato.TIPO_FISICA, RequisicaoContrato.TIPO_DIGITAL),
            ),
            CampoAcao("texto", "DESCRICAO", obrigatorio=False),
        ),
        nota="Passa pela rota do modulo para a edicao entrar na linha do tempo da requisicao.",
    ),
    # Copiar a requisicao: na tela e um botao no modal; aqui e tecla. O texto e
    # montado pelo mesmo arquivo nos dois lugares.
    AcaoPainel(
        chave="requisicao_copiar_whatsapp",
        tecla="W",
        rotulo="COPIAR PARA O WHATSAPP",
        tabela="requisicoes",
        escopo="registro",
        url_name="requisicao_detail",
        formato="copiar",
        montador="requisicao_whatsapp",
        args_do_registro=("pk",),
    ),
    AcaoPainel(
        chave="requisicao_copiar_email",
        tecla="C",
        rotulo="COPIAR PARA O E-MAIL (TEXTO)",
        tabela="requisicoes",
        escopo="registro",
        url_name="requisicao_detail",
        formato="copiar",
        montador="requisicao_email",
        args_do_registro=("pk",),
        nota="A versao com fotos e formatacao rica continua no botao da tela de Requisicoes.",
    ),
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
    # --------------------------------------------------------- atendimentos --
    AcaoPainel(
        chave="planilha_do_atendente",
        tecla="W",
        rotulo="BAIXAR A PLANILHA DO MES",
        tabela="atendimentos",
        escopo="registro",
        url_name="atendimentos_planilha",
        formato="abrir",
        args_do_registro=("atendente_id",),
        campos=(CampoAcao("mes", "MES AAAA-MM (VAZIO = MES ATUAL)", obrigatorio=False),),
        nota="A mesma planilha da tela de Historico, do atendente deste periodo.",
        condicao="atendimento_com_atendente",
    ),
    # -------------------------------------------------------------- dicas --
    AcaoPainel(
        chave="dica_abrir_anexo",
        tecla="T",
        rotulo="ABRIR O ANEXO",
        tabela="dicas",
        escopo="registro",
        url_name="dica_anexo",
        formato="abrir",
        args_do_registro=("pk",),
        condicao="dica_com_anexo",
    ),
    AcaoPainel(
        chave="dica_enviar_anexo",
        tecla="Y",
        rotulo="ENVIAR / TROCAR O ANEXO",
        tabela="dicas",
        escopo="registro",
        url_name="dica_update",
        formato="arquivo",
        campo_arquivo="anexo",
        args_do_registro=("pk",),
        espelha_do_registro=("titulo", "categoria", "conteudo"),
        nota="Abre o seletor do computador. Os demais campos vao como estao hoje, como no modal da tela.",
    ),
    # ----------------------------------------------------- futura digital --
    AcaoPainel(
        chave="futura_abrir_documento",
        tecla="T",
        rotulo="ABRIR O DOCUMENTO DA FATURA",
        tabela="futura",
        escopo="registro",
        url_name="futura_digital_documento",
        formato="abrir",
        args_do_registro=("pk",),
        condicao="futura_com_documento",
    ),
    AcaoPainel(
        chave="futura_enviar_documento",
        tecla="Y",
        rotulo="ENVIAR / TROCAR O DOCUMENTO",
        tabela="futura",
        escopo="registro",
        url_name="futura_digital_update",
        formato="arquivo",
        campo_arquivo="documento",
        args_do_registro=("pk",),
        espelha_do_registro=(
            "mes_referencia",
            "nota_fiscal",
            "copias_total",
            "copias_cor",
            "franquia_copias",
            "franquia_valor",
            "valor_copia_excedente",
            "valor_copia_cor",
        ),
        nota="A fatura e recalculada pela propria rota, com os valores que ela ja tem.",
    ),
    # ----------------------------------------------------- servicos feitos --
    AcaoPainel(
        chave="servico_anexar",
        tecla="Y",
        rotulo="ANEXAR ARQUIVO (NF / ORCAMENTO)",
        tabela="servicos",
        escopo="registro",
        url_name="servico_feito_update",
        formato="arquivo",
        campo_arquivo="anexos",
        args_do_registro=("pk",),
        espelha_do_registro=("nome_servico", "empresa", "descricao", "data_servico", "valor"),
        nota="O anexo e somado aos que ja existem; os campos vao como estao hoje.",
    ),
    # -------------------------------------------------------- contratos ti --
    AcaoPainel(
        chave="contrato_ti_anexar",
        tecla="Y",
        rotulo="ANEXAR ARQUIVO AO CONTRATO",
        tabela="contratos_ti",
        escopo="registro",
        url_name="contrato_ti_update",
        formato="arquivo",
        campo_arquivo="anexos",
        args_do_registro=("pk",),
        espelha_do_registro=(
            "nome",
            "observacoes",
            "valor",
            "forma_pagamento",
            "final_cartao",
            "periodicidade",
            "inicio",
            "fim",
            "encerrado_em",
        ),
        nota="O anexo e somado aos que ja existem; os campos vao como estao hoje.",
    ),
    # --------------------------------------------------------- documentos --
    AcaoPainel(
        chave="documento_criar",
        tecla="N",
        rotulo="NOVO DOCUMENTO (COM ANEXO)",
        tabela="documentos",
        escopo="tabela",
        url_name="documento_create",
        formato="arquivo",
        campo_arquivo="anexos",
        arquivo_opcional=True,
        campos=(
            CampoAcao("nome", "NOME DO DOCUMENTO (2+ LETRAS)"),
            CampoAcao("observacao", "OBSERVACAO", obrigatorio=False),
        ),
        nota="Anexar so acontece na criacao, como na tela. Fechar o seletor sem escolher cria sem anexo.",
    ),
    # -------------------------------------------------------- assinaturas --
    AcaoPainel(
        chave="assinatura_criar",
        tecla="N",
        rotulo="NOVA ASSINATURA DE RESPONSAVEL",
        tabela="assinaturas",
        escopo="tabela",
        url_name="assinatura_create",
        formato="arquivo",
        campo_arquivo="imagem_assinatura",
        arquivo_opcional=True,
        campos=(
            CampoAcao("nome_responsavel", "NOME DO RESPONSAVEL"),
            CampoAcao("senha", "SENHA DE AUTORIZACAO (4+ LETRAS)", mascara=True),
        ),
        nota="A senha e a que o termo pede na hora de assinar; a imagem e a rubrica que sai no PDF.",
    ),
    # ------------------------------------------------------------- anexos --
    # Uma acao por tabela de anexo, todas iguais: a rota de download do modulo,
    # aberta em outra aba. Quem cuida do tipo de arquivo e o navegador.
    AcaoPainel(
        chave="chamado_anexo_abrir",
        tecla="T",
        rotulo="ABRIR O ANEXO",
        tabela="chamado_anexos",
        escopo="registro",
        url_name="download_anexo",
        formato="abrir",
        args_do_registro=("chamado.numero", "pk"),
    ),
    AcaoPainel(
        chave="mensagem_anexo_abrir",
        tecla="T",
        rotulo="ABRIR O ANEXO",
        tabela="mensagem_anexos",
        escopo="registro",
        url_name="download_message_anexo",
        formato="abrir",
        args_do_registro=("mensagem.chamado.numero", "pk"),
    ),
    AcaoPainel(
        chave="documento_anexo_abrir",
        tecla="T",
        rotulo="ABRIR O ANEXO",
        tabela="documento_anexos",
        escopo="registro",
        url_name="documento_anexo_download",
        formato="abrir",
        args_do_registro=("pk",),
    ),
    AcaoPainel(
        chave="servico_anexo_abrir",
        tecla="T",
        rotulo="ABRIR O ANEXO",
        tabela="servico_anexos",
        escopo="registro",
        url_name="servico_feito_anexo_download",
        formato="abrir",
        args_do_registro=("pk",),
    ),
    AcaoPainel(
        chave="contrato_ti_anexo_abrir",
        tecla="T",
        rotulo="ABRIR O ANEXO",
        tabela="contrato_ti_anexos",
        escopo="registro",
        url_name="contrato_ti_anexo_download",
        formato="abrir",
        args_do_registro=("pk",),
    ),
    AcaoPainel(
        chave="orcamento_documento_abrir",
        tecla="T",
        rotulo="ABRIR O DOCUMENTO",
        tabela="orcamento_documentos",
        escopo="registro",
        url_name="contrato_orcamento_documento",
        formato="abrir",
        args_do_registro=("pk",),
    ),
    AcaoPainel(
        chave="suborcamento_documento_abrir",
        tecla="T",
        rotulo="ABRIR O DOCUMENTO",
        tabela="suborcamento_documentos",
        escopo="registro",
        url_name="contrato_suborcamento_documento",
        formato="abrir",
        args_do_registro=("pk",),
    ),
    AcaoPainel(
        chave="equipamento_foto_abrir",
        tecla="T",
        rotulo="ABRIR A FOTO",
        tabela="equipamento_fotos",
        escopo="registro",
        url_name="emprestimo_foto",
        formato="abrir",
        args_do_registro=("pk",),
    ),
    # ---------------------------------------------------- configuracao smtp --
    AcaoPainel(
        chave="email_config_teste",
        tecla="T",
        rotulo="ENVIAR UM E-MAIL DE TESTE",
        tabela="email_config",
        escopo="registro",
        url_name="email_config_test",
        formato="form",
        campos=(CampoAcao("email_teste", "PARA QUAL E-MAIL (VAZIO = O SEU)", obrigatorio=False),),
        nota="Usa a configuracao gravada e mostra aqui o erro do servidor, se houver.",
    ),
    AcaoPainel(
        chave="email_config_senha",
        tecla="Y",
        rotulo="TROCAR A SENHA DO SMTP",
        tabela="email_config",
        escopo="registro",
        url_name="email_config_save",
        formato="form",
        # A rota grava o formulario inteiro e le caixa nao marcada como desligada:
        # sem espelhar tudo, trocar a senha desligaria as notificacoes.
        espelha_do_registro=(
            "ativo",
            "host",
            "porta",
            "usar_tls",
            "usar_ssl",
            "timeout",
            "usuario",
            "remetente",
            "remetente_nome",
            "emails_ti",
            "notif_novo_chamado",
            "notif_nova_mensagem",
            "notif_mudanca_status",
            "notif_fechamento",
        ),
        campos=(CampoAcao("senha", "SENHA DO SMTP (APP PASSWORD)", mascara=True),),
        nota="A senha e cifrada pela rota; os espacos da senha de app do Google saem sozinhos.",
    ),
    # -------------------------------------------------------------- cofre --
    # O painel nao decifra nada por conta propria: quem abre e a rota do Cofre,
    # com a senha-mestra e o registro na auditoria de cada revelacao. A camada
    # generica continua cega para campo de segredo.
    AcaoPainel(
        chave="cofre_destravar",
        tecla="Z",
        rotulo="DESTRAVAR O COFRE",
        tabela="cofre",
        escopo="tabela",
        url_name="cofre_unlock",
        formato="form",
        campos=(CampoAcao("senha_mestra", "SENHA-MESTRA", mascara=True),),
        nota="Vale para a sessao inteira, aqui e na tela do Cofre.",
    ),
    AcaoPainel(
        chave="cofre_senha_mestra",
        tecla="M",
        rotulo="DEFINIR / TROCAR A SENHA-MESTRA",
        tabela="cofre",
        escopo="tabela",
        url_name="cofre_set_master",
        formato="form",
        campos=(
            CampoAcao("senha_atual", "SENHA-MESTRA ATUAL (VAZIO SE AINDA NAO HA)", obrigatorio=False, mascara=True),
            CampoAcao("nova_senha", "NOVA SENHA-MESTRA", mascara=True),
            CampoAcao("confirma_senha", "REPITA A NOVA SENHA", mascara=True),
        ),
        nota="So o administrador troca. Perder a senha-mestra e perder o conteudo do cofre.",
    ),
    AcaoPainel(
        chave="cofre_travar",
        tecla="L",
        rotulo="TRAVAR O COFRE",
        tabela="cofre",
        escopo="tabela",
        url_name="cofre_lock",
        formato="form",
    ),
    AcaoPainel(
        chave="cofre_nova_credencial",
        tecla="N",
        rotulo="NOVA CREDENCIAL",
        tabela="cofre",
        escopo="tabela",
        url_name="cofre_credencial_create",
        formato="form",
        campos=(
            CampoAcao("rotulo", "ROTULO (2+ LETRAS)"),
            CampoAcao("usuario", "USUARIO", obrigatorio=False),
            CampoAcao("senha", "SENHA", mascara=True),
            CampoAcao("notas", "NOTAS", obrigatorio=False),
        ),
        nota="A senha e cifrada pela rota do Cofre; o painel nao guarda nada.",
    ),
    AcaoPainel(
        chave="cofre_revelar",
        tecla="V",
        rotulo="REVELAR A SENHA",
        tabela="cofre",
        escopo="registro",
        url_name="cofre_credencial_reveal",
        args_do_registro=("pk",),
        revela_resposta="senha",
        nota="Cada revelacao entra na auditoria do Cofre, como na tela.",
    ),
    AcaoPainel(
        chave="cofre_trocar_senha",
        tecla="Y",
        rotulo="TROCAR A SENHA",
        tabela="cofre",
        escopo="registro",
        url_name="cofre_credencial_update",
        formato="form",
        args_do_registro=("pk",),
        espelha_do_registro=("rotulo", "usuario", "notas"),
        campos=(CampoAcao("senha", "NOVA SENHA", mascara=True),),
    ),
    AcaoPainel(
        chave="cofre_excluir",
        tecla="X",
        rotulo="EXCLUIR A CREDENCIAL",
        tabela="cofre",
        escopo="registro",
        url_name="cofre_credencial_delete",
        formato="form",
        args_do_registro=("pk",),
        confirma="EXCLUIR ESTA CREDENCIAL DO COFRE? NAO TEM VOLTA.",
    ),
    # ------------------------------------------------------------- emails --
    AcaoPainel(
        chave="emails_importar",
        tecla="I",
        rotulo="IMPORTAR O CSV DO GOOGLE WORKSPACE",
        tabela="emails",
        escopo="tabela",
        url_name="email_import",
        formato="arquivo",
        campo_arquivo="arquivo",
        nota="Mesma importacao da tela de E-mails: atualiza pelo e-mail, sem duplicar conta.",
    ),
    # ------------------------------------------------------------ insumos --
    AcaoPainel(
        chave="insumo_entrada",
        tecla="E",
        rotulo="DAR ENTRADA NO ESTOQUE",
        tabela="insumos",
        escopo="registro",
        url_name="insumo_entrada",
        args_do_registro=("pk",),
        campos=(
            CampoAcao("quantidade", "QUANTIDADE QUE ENTROU", tipo="NUMERO"),
            CampoAcao("observacao", "OBSERVACAO (OPCIONAL)", obrigatorio=False),
        ),
        nota="Soma ao saldo e lanca a entrada no extrato. Mexer no saldo a mao nao lanca nada.",
    ),
    AcaoPainel(
        chave="insumo_retirada",
        tecla="S",
        rotulo="REGISTRAR RETIRADA (SAIDA)",
        tabela="insumos",
        escopo="registro",
        url_name="retirada_create",
        args_do_registro=("pk",),
        campos=(
            CampoAcao("quantidade", "QUANTIDADE RETIRADA", tipo="NUMERO"),
            CampoAcao("entregue_para", "ENTREGUE PARA QUEM"),
            CampoAcao("motivo", "MOTIVO DA RETIRADA"),
        ),
        nota="Desconta do saldo e lanca a saida no extrato; o estoque nao fica negativo.",
        condicao="insumo_ativo",
    ),
    AcaoPainel(
        chave="orcamento_documento",
        tecla="Y",
        rotulo="ANEXAR DOCUMENTO AO ORCAMENTO",
        tabela="orcamentos",
        escopo="registro",
        url_name="orcamento_edit",
        formato="arquivo",
        campo_arquivo="documentos",
        args_do_registro=("pk",),
        espelha_do_registro=("titulo", "loja", "moeda", "valor", "quantidade", "frete", "desconto", "link"),
        condicao="orcamento_editavel",
    ),
    AcaoPainel(
        chave="orcamento_foto",
        tecla="P",
        rotulo="ENVIAR / TROCAR A FOTO DO PRODUTO",
        tabela="orcamentos",
        escopo="registro",
        url_name="orcamento_edit",
        formato="arquivo",
        campo_arquivo="foto_produto",
        args_do_registro=("pk",),
        espelha_do_registro=("titulo", "loja", "moeda", "valor", "quantidade", "frete", "desconto", "link"),
        condicao="orcamento_editavel",
    ),
    AcaoPainel(
        chave="orcamento_ver_foto",
        tecla="T",
        rotulo="ABRIR A FOTO DO PRODUTO",
        tabela="orcamentos",
        escopo="registro",
        url_name="contrato_orcamento_foto",
        formato="abrir",
        args_do_registro=("pk",),
        condicao="item_com_foto",
    ),
    AcaoPainel(
        chave="suborcamento_documento",
        tecla="Y",
        rotulo="ANEXAR DOCUMENTO AO SUBORCAMENTO",
        tabela="suborcamentos",
        escopo="registro",
        url_name="suborcamento_edit",
        formato="arquivo",
        campo_arquivo="documentos",
        args_do_registro=("pk",),
        espelha_do_registro=("titulo", "loja", "moeda", "valor", "quantidade", "frete", "desconto", "link"),
    ),
    AcaoPainel(
        chave="suborcamento_foto",
        tecla="P",
        rotulo="ENVIAR / TROCAR A FOTO DO PRODUTO",
        tabela="suborcamentos",
        escopo="registro",
        url_name="suborcamento_edit",
        formato="arquivo",
        campo_arquivo="foto_produto",
        args_do_registro=("pk",),
        espelha_do_registro=("titulo", "loja", "moeda", "valor", "quantidade", "frete", "desconto", "link"),
    ),
    AcaoPainel(
        chave="suborcamento_ver_foto",
        tecla="T",
        rotulo="ABRIR A FOTO DO PRODUTO",
        tabela="suborcamentos",
        escopo="registro",
        url_name="contrato_suborcamento_foto",
        formato="abrir",
        args_do_registro=("pk",),
        condicao="item_com_foto",
    ),
    # -------------------------------------------------------- emprestimos --
    AcaoPainel(
        chave="emprestimo_criar",
        tecla="N",
        rotulo="NOVO EMPRESTIMO",
        tabela="emprestimos",
        escopo="tabela",
        url_name="emprestimo_create",
        formato="form",
        # A rota exige pelo menos um equipamento; o terminal cadastra o primeiro
        # aqui e os outros entram pela acao do proprio emprestimo.
        payload_fixo=(("equipamentos_count", "1"),),
        campos=(
            CampoAcao("colaborador_nome", "NOME DO COLABORADOR"),
            CampoAcao("data_emprestimo", "DATA DO EMPRESTIMO", tipo="DATA"),
            CampoAcao("equip_0_tipo", "TIPO DO EQUIPAMENTO"),
            CampoAcao("equip_0_marca", "MARCA", obrigatorio=False),
            CampoAcao("equip_0_modelo", "MODELO", obrigatorio=False),
            CampoAcao("equip_0_serie", "NUMERO DE SERIE", obrigatorio=False),
            CampoAcao("previsao_devolucao", "PREVISAO DE DEVOLUCAO (VAZIO = SEM PRAZO)", obrigatorio=False, tipo="DATA"),
            CampoAcao("empresa", "EMPRESA", obrigatorio=False),
        ),
        nota="Gera o termo em PDF na hora, como a tela. A assinatura do responsavel continua na tela de Emprestimos.",
    ),
    AcaoPainel(
        chave="emprestimo_add_equipamento",
        tecla="Q",
        rotulo="ADICIONAR EQUIPAMENTO",
        tabela="emprestimos",
        escopo="registro",
        url_name="emprestimo_editar",
        formato="form",
        args_do_registro=("pk",),
        payload_fixo=(("equipamentos_count", "1"),),
        espelha_do_registro=(
            "colaborador_nome",
            "empresa",
            "cpf",
            "email",
            "telefone",
            "data_emprestimo",
            "previsao_devolucao",
            "observacoes_internas",
        ),
        campos=(
            CampoAcao("equip_0_tipo", "TIPO DO EQUIPAMENTO"),
            CampoAcao("equip_0_marca", "MARCA", obrigatorio=False),
            CampoAcao("equip_0_modelo", "MODELO", obrigatorio=False),
            CampoAcao("equip_0_serie", "NUMERO DE SERIE", obrigatorio=False),
        ),
        nota="O termo e refeito e o emprestimo volta a aguardar assinatura, igual a tela.",
    ),
    # ------------------------------------------------------- equipamentos --
    AcaoPainel(
        chave="equipamento_devolver",
        tecla="D",
        rotulo="MARCAR COMO DEVOLVIDO (HOJE)",
        tabela="equipamentos",
        escopo="registro",
        url_name="emprestimo_editar",
        formato="form",
        args_do_registro=("emprestimo_id",),
        # Quem recebe o pedido e o emprestimo: os dados dele voltam no POST e os
        # outros equipamentos ficam como estao (a rota assume "manter").
        payload_fixo=(("acao_equip_{pk}", "devolver"),),
        payload_do_registro=(
            ("colaborador_nome", "emprestimo.colaborador_nome"),
            ("empresa", "emprestimo.empresa"),
            ("cpf", "emprestimo.cpf"),
            ("email", "emprestimo.email"),
            ("telefone", "emprestimo.telefone"),
            ("data_emprestimo", "emprestimo.data_emprestimo"),
            ("previsao_devolucao", "emprestimo.previsao_devolucao"),
            ("observacoes_internas", "emprestimo.observacoes_internas"),
        ),
        confirma="MARCAR ESTE EQUIPAMENTO COMO DEVOLVIDO HOJE?",
        nota="Devolvendo o ultimo equipamento, o emprestimo inteiro passa a Devolvido.",
        condicao="equipamento_em_posse",
    ),
    AcaoPainel(
        chave="emprestimo_assinar",
        tecla="S",
        rotulo="APLICAR A ASSINATURA NO TERMO",
        tabela="emprestimos",
        escopo="registro",
        url_name="emprestimo_editar",
        formato="form",
        args_do_registro=("pk",),
        espelha_do_registro=(
            "colaborador_nome",
            "empresa",
            "cpf",
            "email",
            "telefone",
            "data_emprestimo",
            "previsao_devolucao",
            "observacoes_internas",
        ),
        campos=(
            CampoAcao("assinatura_id", "ID DA ASSINATURA (VEJA EM ASSINATURAS)", tipo="NUMERO"),
            CampoAcao("senha_assinatura", "SENHA DE AUTORIZACAO", mascara=True),
        ),
        nota="Refaz o termo com a rubrica do responsavel. A senha errada e recusada pela rota, como na tela.",
    ),
    AcaoPainel(
        chave="assinatura_abrir_imagem",
        tecla="T",
        rotulo="ABRIR A RUBRICA",
        tabela="assinaturas",
        escopo="registro",
        url_name="assinatura_imagem",
        formato="abrir",
        args_do_registro=("pk",),
        condicao="assinatura_com_imagem",
    ),
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
    # A rota de retirada so acha insumo ativo; entrada continua valendo, para
    # dar para reativar e repor sem perder o lancamento.
    "insumo_ativo": lambda obj, usuario: bool(getattr(obj, "ativo", True)),
    "dica_com_anexo": lambda obj, usuario: bool(obj.anexo),
    "futura_com_documento": lambda obj, usuario: bool(obj.documento),
    # Periodo importado do sistema antigo pode ter ficado sem atendente.
    "atendimento_com_atendente": lambda obj, usuario: obj.atendente_id is not None,
    "item_com_foto": lambda obj, usuario: bool(obj.foto_produto),
    # Requisicao entregue nao aceita mais edicao de orcamento (regra da rota).
    "orcamento_editavel": lambda obj, usuario: obj.requisicao.status != RequisicaoContrato.STATUS_ENTREGUE,
    "equipamento_em_posse": lambda obj, usuario: obj.data_devolucao is None,
    "assinatura_com_imagem": lambda obj, usuario: bool(obj.imagem_assinatura),
    "emprestimo_com_termo": lambda obj, usuario: bool(obj.termo_pdf),
    "emprestimo_com_assinado": lambda obj, usuario: bool(obj.termo_assinado),
    # So faz sentido dar o OK depois que o assinado subiu (a rota recusa antes).
    "emprestimo_assinado_pendente_de_ok": lambda obj, usuario: bool(obj.termo_assinado)
    and not obj.termo_assinado_ok,
}


def _atributo(obj, caminho: str):
    """Le `campo` ou `pai.campo` do registro.

    O caminho com ponto existe porque ha rota que pertence ao registro pai: para
    marcar um equipamento como devolvido, quem recebe o pedido e o emprestimo, e
    ele quer os proprios dados de volta no POST.
    """
    valor = obj
    for parte in caminho.split("."):
        valor = getattr(valor, parte, None)
        if valor is None:
            return None
    return valor


def _valor_para_pedido(valor):
    """Valor do registro no formato que a rota da tela sabe reler.

    Vazio no lugar de `None` importa: as rotas tratam campo em branco como "sem
    valor", mas o texto "None" viraria zero ou data invalida. Data sai em ISO e
    decimal com ponto — os dois formatos que os leitores de formulario aceitam.
    """
    if valor is None:
        return ""
    if isinstance(valor, bool):
        # Rota de tela le checkbox: marcada chega como "on", desmarcada nao chega.
        return "on" if valor else ""
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()[:10] if not isinstance(valor, datetime) else valor.date().isoformat()
    if isinstance(valor, Decimal):
        return f"{valor}"
    return str(valor)


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

    args = [_atributo(obj, nome) for nome in acao.args_do_registro] if obj is not None else []
    # A chave pode depender do registro: a rota de emprestimo recebe a acao de
    # cada equipamento como `acao_equip_<id>`.
    payload = {
        (chave.format(pk=obj.pk) if obj is not None and "{pk}" in chave else chave): valor
        for chave, valor in acao.payload_fixo
    }
    if obj is not None:
        for chave, atributo in acao.payload_do_registro:
            payload[chave] = _valor_para_pedido(_atributo(obj, atributo))
        for nome in acao.espelha_do_registro:
            payload[nome] = _valor_para_pedido(_atributo(obj, nome))

    return {
        "chave": acao.chave,
        "tecla": acao.tecla,
        "rotulo": acao.rotulo,
        "url": reverse(acao.url_name, args=args) if args else reverse(acao.url_name),
        "formato": acao.formato,
        "campo_arquivo": acao.campo_arquivo,
        "montador": acao.montador,
        "arquivo_opcional": acao.arquivo_opcional,
        "payload": payload,
        "campos": [
            {
                "nome": c.nome,
                "rotulo": c.rotulo,
                "obrigatorio": c.obrigatorio,
                "tipo": c.tipo,
                "opcoes": list(c.opcoes),
                "mascara": c.mascara,
            }
            for c in acao.campos
        ],
        "confirma": acao.confirma,
        "nota": acao.nota,
        "busca_resposta": acao.busca_resposta,
        "revela_resposta": acao.revela_resposta,
    }


def acoes_serializadas(chave_tabela: str, escopo: str, obj=None, usuario=None) -> list[dict]:
    saida = []
    for acao in acoes_da_tabela(chave_tabela, escopo):
        dados = serializar(acao, obj, usuario)
        if dados:
            saida.append(dados)
    return saida
