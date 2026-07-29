"""Importa os periodos de atendimento do sistema antigo (ERP-TI).

A migracao original trouxe os 757 chamados e as mensagens, mas **nao** a tabela
`chamados_ticketattendance` do banco antigo, onde esta o tempo trabalhado (891
periodos de 02/2026 a 07/2026). Sem eles, qualquer relatorio baseado em
`AtendimentoHistorico` - como a planilha mensal de atendimentos - so tem dados
de 15/07/2026 em diante, quando o controle de tempo do sistema novo entrou em
uso.

O banco antigo NAO e versionado: coloque uma copia em `seed/chamados_legado.sqlite3`
(a pasta `seed/` esta no `.gitignore`) e rode a migration; sem o arquivo, ela e
um no-op. Apague a copia depois de importar.

Mapeamento: **ticket antigo `id` N <-> chamado novo `CH-{N:06d}`**. As faixas nao
se cruzam (migrados CH-000003..CH-000799; os criados no sistema novo comecam em
CH-000800), e ainda assim cada registro e conferido antes de gravar.

Cuidados para nao mexer em chamado recente nem bagunçar o Kanban:

1. So anexa periodo a chamado com `origem="Migrado (sistema antigo)"` e cuja data
   de criacao **bate** com a do ticket antigo; qualquer divergencia e pulada.
2. **Nunca grava periodo sem fim.** Um `finalizado_em` nulo significa
   "atendimento ativo": sujaria o badge/contador do Kanban e bloquearia o Play do
   atendente (a regra de um atendimento ativo por atendente). Os 5 registros
   antigos sem fim (Plays abandonados no dia da virada) sao pulados.
3. Ignora periodo que tenha comecado a partir do primeiro periodo ja existente no
   banco novo - se algum dia os dois sistemas tiverem rodado em paralelo, nada e
   duplicado.
4. Idempotente: a chave (chamado, atendente, inicio) evita recriar.
5. **Nao altera nenhum campo de `Chamado`** - so insere historico.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.conf import settings

CAMINHO_PADRAO = settings.BASE_DIR / "seed" / "chamados_legado.sqlite3"

ORIGEM_MIGRADO = "Migrado (sistema antigo)"

# O banco antigo grava data/hora NAIVE em **UTC** (Django com USE_TZ). Conferido
# de duas formas: (1) o periodo de 04/05 aparece como 11:48->17:39 no banco e a
# planilha preenchida a mao registra 08:48->14:39, exatamente UTC-3; (2) a hora
# de abertura dos 757 tickets se concentra entre 11h e 21h, sem nada de manha -
# como UTC isso e o expediente 08h-18h local.
#
# ATENCAO: a migracao original dos chamados interpretou esses mesmos valores como
# hora LOCAL, entao os 757 chamados migrados ficaram com `criado_em`/`fechado_em`
# 3 horas adiantados no banco novo. Por isso a conferencia abaixo aceita as duas
# leituras: o objetivo dela e garantir que o periodo pertence aquele chamado, nao
# auditar o fuso do que ja foi gravado.
FUSO_LOCAL = ZoneInfo(settings.TIME_ZONE)

# Tolerancia ao comparar a data de criacao do ticket antigo com a do chamado.
TOLERANCIA = timedelta(seconds=2)

# Marcador tecnico que o migrador anterior deixou nas notas ("[ERP-TI-CYCLE:206]").
_MARCADOR = re.compile(r"\s*\[ERP-TI-[A-Z]+:\d+\]\s*$")

CONSULTA = """
    SELECT a.id, a.ticket_id, a.started_at, a.ended_at, a.end_action, a.note,
           u.username, t.created_at AS ticket_created_at
      FROM chamados_ticketattendance a
      JOIN chamados_ticket t ON t.id = a.ticket_id
      LEFT JOIN auth_user u ON u.id = a.attendant_id
     ORDER BY a.started_at, a.id
"""


def _naive(texto):
    if not texto:
        return None
    texto = texto.strip().replace("T", " ")
    formato = "%Y-%m-%d %H:%M:%S.%f" if "." in texto else "%Y-%m-%d %H:%M:%S"
    from datetime import datetime

    return datetime.strptime(texto, formato)


def _aware(texto):
    """Data/hora do banco antigo: naive em UTC (ver nota sobre o fuso acima)."""
    from datetime import timezone as tz_utc

    valor = _naive(texto)
    return valor.replace(tzinfo=tz_utc.utc) if valor else None


def _aware_como_local(texto):
    """A mesma data/hora lida como se fosse hora local.

    E assim que a migracao original dos chamados interpretou o banco antigo, e e
    o valor que esta gravado em `Chamado.criado_em` hoje.
    """
    valor = _naive(texto)
    return valor.replace(tzinfo=FUSO_LOCAL) if valor else None


def _descricao(note: str) -> str:
    return _MARCADOR.sub("", (note or "").strip()).strip()


def importar(caminho=None, *, Chamado=None, AtendimentoHistorico=None, User=None, gravar=True):
    """Importa os periodos do banco antigo. Devolve um relatorio (dict).

    `gravar=False` faz uma passada de conferencia, sem escrever nada.
    Os modelos podem ser injetados (a migration passa os historicos de `apps`).
    """
    from django.apps import apps as registro

    Chamado = Chamado or registro.get_model("core", "Chamado")
    AtendimentoHistorico = AtendimentoHistorico or registro.get_model("core", "AtendimentoHistorico")
    if User is None:
        User = registro.get_model(settings.AUTH_USER_MODEL)

    caminho = caminho or CAMINHO_PADRAO
    relatorio = {
        "arquivo": str(caminho),
        "lidos": 0,
        "criados": 0,
        "ja_existiam": 0,
        "sem_fim": 0,
        "sem_chamado": 0,
        "data_divergente": 0,
        "sem_usuario": 0,
        "apos_corte": 0,
    }

    conexao = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)
    conexao.row_factory = sqlite3.Row
    try:
        linhas = list(conexao.execute(CONSULTA))
    finally:
        conexao.close()

    usuarios = {u.username: u for u in User.objects.all()}
    chamados = {
        c.numero: c
        for c in Chamado.objects.filter(origem=ORIGEM_MIGRADO).only("id", "numero", "criado_em")
    }

    # Corte anti-duplicidade: nada do antigo entra a partir do primeiro periodo
    # que o SISTEMA NOVO ja registrou.
    #
    # O corte precisa ignorar os periodos que este proprio import criou numa
    # passada anterior - senao, na segunda execucao, o mais antigo deles viraria
    # o corte e tudo depois dele seria descartado (uma importacao interrompida
    # nunca terminaria). Por isso montamos primeiro as chaves dos registros
    # legados e calculamos o corte apenas sobre o que NAO e legado.
    chaves_legadas = {
        (f"CH-{linha['ticket_id']:06d}", linha["username"] or "", _aware(linha["started_at"]))
        for linha in linhas
    }
    primeiro_novo = None
    existentes = AtendimentoHistorico.objects.select_related("chamado", "atendente").only(
        "iniciado_em", "chamado__numero", "atendente__username"
    )
    for periodo in existentes:
        chave = (periodo.chamado.numero, periodo.atendente.username, periodo.iniciado_em)
        if chave in chaves_legadas:
            continue
        if primeiro_novo is None or periodo.iniciado_em < primeiro_novo:
            primeiro_novo = periodo.iniciado_em

    for linha in linhas:
        relatorio["lidos"] += 1
        inicio = _aware(linha["started_at"])
        fim = _aware(linha["ended_at"])

        # (2) periodo sem fim viraria "atendimento ativo" no Kanban
        if not inicio or not fim:
            relatorio["sem_fim"] += 1
            continue

        # (3) corte para nunca duplicar o que o sistema novo ja registra
        if primeiro_novo and inicio >= primeiro_novo:
            relatorio["apos_corte"] += 1
            continue

        chamado = chamados.get(f"CH-{linha['ticket_id']:06d}")
        if chamado is None:
            relatorio["sem_chamado"] += 1
            continue

        # (1) confere que e mesmo o chamado daquele ticket antigo. Aceita as duas
        # leituras do fuso porque o `criado_em` gravado hoje veio da leitura
        # "como local" feita pela migracao original (ver nota sobre o fuso).
        leituras = [_aware(linha["ticket_created_at"]), _aware_como_local(linha["ticket_created_at"])]
        if not any(
            leitura and abs(chamado.criado_em - leitura) <= TOLERANCIA for leitura in leituras
        ):
            relatorio["data_divergente"] += 1
            continue

        atendente = usuarios.get(linha["username"] or "")
        if atendente is None:
            relatorio["sem_usuario"] += 1
            continue

        # (4) idempotencia
        if AtendimentoHistorico.objects.filter(
            chamado=chamado, atendente=atendente, iniciado_em=inicio
        ).exists():
            relatorio["ja_existiam"] += 1
            continue

        if gravar:
            AtendimentoHistorico.objects.create(
                chamado=chamado,
                atendente=atendente,
                iniciado_em=inicio,
                finalizado_em=fim,
                duracao=fim - inicio,
                tipo_encerramento=(linha["end_action"] or "stop").strip() or "stop",
                descricao_atividade=_descricao(linha["note"]),
            )
        relatorio["criados"] += 1

    return relatorio
