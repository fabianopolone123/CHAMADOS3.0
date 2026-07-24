import json
import os
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    AtendimentoHistorico,
    Chamado,
    ChamadoEvento,
    ChamadoMensagem,
    ChamadoMensagemAnexo,
    CofreAuditoria,
    CofreConfig,
    CofreCredencial,
    ContaEmail,
    Contrato,
    ContratoAnexo,
    Dica,
    EmprestimoTI,
    EquipamentoEmprestimoTI,
    EnderecoIP,
    FuturaDigital,
    Licenca,
    LicencaSoftware,
    OrcamentoContrato,
    OrcamentoDocumento,
    PendenciaTI,
    Ramal,
    RequisicaoContrato,
    RequisicaoContratoEvento,
    ServicoFeito,
    ServicoFeitoAnexo,
    Starlink,
    SuborcamentoContrato,
    SuborcamentoDocumento,
)
from .permissions import ADMIN_GROUP_NAME, ATTENDANT_GROUP_NAME


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ChamadoMensagemTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username="joao", password="x")
        self.other = User.objects.create_user(username="maria", password="x")
        self.attendant = User.objects.create_user(username="ti", password="x")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        self.attendant.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))

        self.chamado = Chamado.objects.create(
            numero="CH-000001",
            titulo="Impressora sem tinta",
            descricao="Nao imprime nada",
            solicitante=self.owner,
            solicitante_nome="Joao",
            status=Chamado.STATUS_ABERTO,
        )

    def _post_message(self, data):
        return self.client.post(
            reverse("ticket_message_create", args=[self.chamado.numero]), data
        )

    def test_owner_sends_message_without_attachment(self):
        self.client.force_login(self.owner)
        resp = self._post_message({"texto": "Bom dia, alguma novidade?"})
        self.assertEqual(resp.status_code, 302)

        mensagem = ChamadoMensagem.objects.get(chamado=self.chamado)
        self.assertEqual(mensagem.texto, "Bom dia, alguma novidade?")
        self.assertEqual(mensagem.autor, self.owner)

        # historico tecnico guarda apenas o resumo, nao o texto da mensagem
        evento = ChamadoEvento.objects.get(chamado=self.chamado, tipo=ChamadoEvento.TIPO_COMENTARIO)
        self.assertIn("Mensagem enviada pelo solicitante", evento.descricao)
        self.assertNotIn("Bom dia", evento.descricao)

    def test_owner_sends_message_with_attachment(self):
        self.client.force_login(self.owner)
        arquivo = SimpleUploadedFile("erro.txt", b"conteudo", content_type="text/plain")
        resp = self._post_message({"texto": "Segue print", "anexos": [arquivo]})
        self.assertEqual(resp.status_code, 302)

        mensagem = ChamadoMensagem.objects.get(chamado=self.chamado)
        self.assertEqual(mensagem.anexos.count(), 1)

        evento = ChamadoEvento.objects.get(chamado=self.chamado, tipo=ChamadoEvento.TIPO_COMENTARIO)
        self.assertIn("1 anexo(s)", evento.descricao)

    def test_empty_message_is_rejected(self):
        self.client.force_login(self.owner)
        resp = self._post_message({"texto": "   "})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(ChamadoMensagem.objects.filter(chamado=self.chamado).exists())

    def test_other_common_user_cannot_send_message(self):
        self.client.force_login(self.other)
        resp = self._post_message({"texto": "invadindo"})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(ChamadoMensagem.objects.filter(chamado=self.chamado).exists())

    def test_attendant_can_reply_on_any_ticket(self):
        self.client.force_login(self.attendant)
        resp = self._post_message({"texto": "Estamos verificando."})
        self.assertEqual(resp.status_code, 302)

        mensagem = ChamadoMensagem.objects.get(chamado=self.chamado)
        self.assertEqual(mensagem.autor, self.attendant)
        evento = ChamadoEvento.objects.get(chamado=self.chamado, tipo=ChamadoEvento.TIPO_COMENTARIO)
        self.assertIn("Mensagem enviada por", evento.descricao)
        self.assertNotIn("solicitante", evento.descricao)

    def test_other_common_user_cannot_access_detail(self):
        self.client.force_login(self.other)
        resp = self.client.get(reverse("ticket_detail", args=[self.chamado.numero]))
        self.assertEqual(resp.status_code, 302)  # redirecionado, sem acesso

    def test_message_attachment_download_permission(self):
        self.client.force_login(self.owner)
        arquivo = SimpleUploadedFile("nota.txt", b"abc", content_type="text/plain")
        self._post_message({"texto": "arquivo", "anexos": [arquivo]})
        anexo = ChamadoMensagemAnexo.objects.get()

        url = reverse("download_message_anexo", args=[self.chamado.numero, anexo.id])
        self.assertEqual(self.client.get(url).status_code, 200)

        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class EncerramentoChamadoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username="joao", password="x")
        self.attendant = User.objects.create_user(username="ti", password="x")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        self.attendant.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))

        self.chamado = Chamado.objects.create(
            numero="CH-000010",
            titulo="Rede caiu",
            descricao="Sem internet no setor",
            solicitante=self.owner,
            status=Chamado.STATUS_EM_ATENDIMENTO,
            atendente_atual=self.attendant,
        )

    def _start_attendance(self, user):
        return AtendimentoHistorico.objects.create(
            chamado=self.chamado, atendente=user, iniciado_em=timezone.now()
        )

    def _finish(self, action, description="Feito"):
        return self.client.post(
            reverse("finish_attendance"),
            data=json.dumps(
                {"ticket_number": self.chamado.numero, "action": action, "description": description}
            ),
            content_type="application/json",
        )

    def test_stop_closes_and_moves_ticket(self):
        self.client.force_login(self.attendant)
        self._start_attendance(self.attendant)
        resp = self._finish("stop", "Resolvido e testado com o usuario")
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertTrue(data["ticket_closed"])
        self.assertEqual(data["status"], Chamado.STATUS_FECHADO)
        self.assertEqual(data["status_class"], "status-neutral")

        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, Chamado.STATUS_FECHADO)
        self.assertIsNotNone(self.chamado.fechado_em)
        self.assertEqual(self.chamado.atendente_atual, self.attendant)

        self.assertTrue(
            ChamadoEvento.objects.filter(chamado=self.chamado, tipo=ChamadoEvento.TIPO_STATUS).exists()
        )
        # O historico tecnico registra a finalizacao com quem finalizou e o texto
        # de "O que foi feito" (registro tecnico, separado da conversa do usuario).
        self.assertTrue(
            ChamadoEvento.objects.filter(
                chamado=self.chamado, descricao__icontains="finalizado"
            ).exists()
        )
        self.assertTrue(
            ChamadoEvento.objects.filter(
                chamado=self.chamado,
                descricao__icontains="O que foi feito: Resolvido e testado com o usuario",
            ).exists()
        )

    def test_pause_does_not_close_ticket(self):
        self.client.force_login(self.attendant)
        self._start_attendance(self.attendant)
        resp = self._finish("pause", "Aguardando peca de reposicao")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json().get("ticket_closed"))

        # Pause sem motivo encerra o periodo de atendimento e devolve o chamado
        # para "Atribuido" (nao fica "Em atendimento" sem Play ativo).
        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, Chamado.STATUS_ATRIBUIDO)

    def test_common_user_cannot_finish_attendance(self):
        self.client.force_login(self.owner)
        resp = self._finish("stop", "tentando encerrar")
        self.assertEqual(resp.status_code, 403)

        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, Chamado.STATUS_EM_ATENDIMENTO)

    def test_drag_to_fechado_is_blocked(self):
        # O fechamento so acontece via Stop: o endpoint de movimentacao recusa o
        # destino "fechado" e nao altera o chamado.
        self.client.force_login(self.attendant)
        resp = self.client.post(
            reverse("move_ticket"),
            data=json.dumps({"ticket_number": self.chamado.numero, "target": "fechado"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 409)

        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, Chamado.STATUS_EM_ATENDIMENTO)
        self.assertIsNone(self.chamado.fechado_em)

    def test_dashboard_stats_por_atendente(self):
        # A coluna do atendente traz a quebra por status: em atendimento,
        # aguardando (soma dos 3) e atribuido. self.chamado ja esta "em_atendimento".
        Chamado.objects.create(
            numero="CH-000020", titulo="Peca", solicitante=self.owner,
            status=Chamado.STATUS_AGUARDANDO_PECA, atendente_atual=self.attendant,
        )
        Chamado.objects.create(
            numero="CH-000021", titulo="Usuario", solicitante=self.owner,
            status=Chamado.STATUS_AGUARDANDO_USUARIO, atendente_atual=self.attendant,
        )
        Chamado.objects.create(
            numero="CH-000022", titulo="Atribuido", solicitante=self.owner,
            status=Chamado.STATUS_ATRIBUIDO, atendente_atual=self.attendant,
        )
        self.client.force_login(self.attendant)
        resp = self.client.get(reverse("tickets_dashboard"))
        self.assertEqual(resp.status_code, 200)
        coluna = next(
            c for c in resp.context["attendant_columns"] if c["attendant_id"] == self.attendant.id
        )
        self.assertEqual(coluna["count"], 4)
        self.assertEqual(coluna["stats"]["em_atendimento"], 1)
        self.assertEqual(coluna["stats"]["aguardando"], 2)
        self.assertEqual(coluna["stats"]["atribuido"], 1)

    def test_mover_chamado_com_play_ativo_e_bloqueado(self):
        # Com um atendimento ativo (Play), o chamado nao pode ser movido: o
        # endpoint recusa com 409 e nada muda (atendente/status preservados).
        User = get_user_model()
        outro = User.objects.create_user(username="ti2", password="x")
        outro.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))
        self._start_attendance(self.attendant)  # Play ativo do self.attendant

        self.client.force_login(self.attendant)
        resp = self.client.post(
            reverse("move_ticket"),
            data=json.dumps(
                {"ticket_number": self.chamado.numero, "target": "atendente", "attendant_id": outro.id}
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 409)

        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.atendente_atual, self.attendant)  # nao mudou
        self.assertEqual(self.chamado.status, Chamado.STATUS_EM_ATENDIMENTO)
        # O Play continua sendo do atendente original.
        self.assertTrue(
            AtendimentoHistorico.objects.filter(
                chamado=self.chamado, atendente=self.attendant, finalizado_em__isnull=True
            ).exists()
        )

    def test_mover_para_abertos_com_play_ativo_e_bloqueado(self):
        # A regra vale para qualquer destino: nem devolver para "Chamados abertos"
        # e permitido enquanto ha Play ativo.
        self._start_attendance(self.attendant)
        self.client.force_login(self.attendant)
        resp = self.client.post(
            reverse("move_ticket"),
            data=json.dumps({"ticket_number": self.chamado.numero, "target": "aberto"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 409)
        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.atendente_atual, self.attendant)

    def test_move_liberado_apos_pausar_o_atendimento(self):
        # Depois de pausar o Play, o chamado volta a poder ser movido.
        User = get_user_model()
        outro = User.objects.create_user(username="ti3", password="x")
        outro.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))
        self._start_attendance(self.attendant)
        self.client.force_login(self.attendant)
        self.assertEqual(self._finish("pause", "pausando para repassar").status_code, 200)

        resp = self.client.post(
            reverse("move_ticket"),
            data=json.dumps(
                {"ticket_number": self.chamado.numero, "target": "atendente", "attendant_id": outro.id}
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.atendente_atual, outro)
        self.assertEqual(self.chamado.status, Chamado.STATUS_ATRIBUIDO)

    def test_stop_requires_active_attendance(self):
        # Sem Play ativo, o Stop e recusado e o chamado nao e fechado.
        self.client.force_login(self.attendant)
        resp = self._finish("stop", "sem play ativo")
        self.assertEqual(resp.status_code, 409)

        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, Chamado.STATUS_EM_ATENDIMENTO)

    def test_play_em_varios_chamados_ao_mesmo_tempo(self):
        # Multiplos atendimentos ativos sao permitidos: dar Play em dois chamados
        # mantem os dois ativos (nao pausa nem bloqueia).
        self.client.force_login(self.attendant)
        ch2 = Chamado.objects.create(
            numero="CH-000011", titulo="Outro chamado", solicitante=self.owner,
            status=Chamado.STATUS_EM_ATENDIMENTO, atendente_atual=self.attendant,
        )

        def _play(numero):
            return self.client.post(
                reverse("start_attendance"),
                data=json.dumps({"ticket_number": numero}),
                content_type="application/json",
            )

        self.assertEqual(_play(self.chamado.numero).status_code, 200)
        self.assertEqual(_play(ch2.numero).status_code, 200)

        ativos = AtendimentoHistorico.objects.filter(
            atendente=self.attendant, finalizado_em__isnull=True
        )
        self.assertEqual(ativos.count(), 2)  # os dois ativos ao mesmo tempo

        # Play repetido no MESMO chamado ainda e bloqueado (nao duplica).
        self.assertEqual(_play(ch2.numero).status_code, 409)

    def test_stop_age_no_chamado_especifico(self):
        # Com varios ativos, o Stop/Pause encerra o atendimento do chamado informado.
        self.client.force_login(self.attendant)
        ch2 = Chamado.objects.create(
            numero="CH-000012", titulo="Segundo", solicitante=self.owner,
            status=Chamado.STATUS_EM_ATENDIMENTO, atendente_atual=self.attendant,
        )
        self._start_attendance(self.attendant)  # ativo no self.chamado
        AtendimentoHistorico.objects.create(chamado=ch2, atendente=self.attendant, iniciado_em=timezone.now())

        resp = self.client.post(
            reverse("finish_attendance"),
            data=json.dumps({"ticket_number": ch2.numero, "action": "pause", "description": "pausando o 2"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        # so o ch2 foi finalizado; o self.chamado continua ativo
        self.assertFalse(
            AtendimentoHistorico.objects.filter(chamado=ch2, finalizado_em__isnull=True).exists()
        )
        self.assertTrue(
            AtendimentoHistorico.objects.filter(chamado=self.chamado, finalizado_em__isnull=True).exists()
        )

    def test_pause_com_motivo_marca_aguardando_e_registra_historico(self):
        self.client.force_login(self.attendant)
        self._start_attendance(self.attendant)
        resp = self.client.post(
            reverse("finish_attendance"),
            data=json.dumps({
                "ticket_number": self.chamado.numero, "action": "pause",
                "description": "peca pedida ao fornecedor", "pause_reason": "aguardando_peca",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, Chamado.STATUS_AGUARDANDO_PECA)
        # pausa registrada no historico do chamado
        self.assertTrue(
            ChamadoEvento.objects.filter(chamado=self.chamado, descricao__icontains="pausado").exists()
        )

    def test_move_para_atendente_marca_atribuido_nao_em_atendimento(self):
        # Arrastar para um atendente apenas atribui o chamado; "Em atendimento"
        # so vale com Play ativo. Depois o Play muda o status para em_atendimento.
        self.chamado.status = Chamado.STATUS_ABERTO
        self.chamado.atendente_atual = None
        self.chamado.save()
        self.client.force_login(self.attendant)

        resp = self.client.post(
            reverse("move_ticket"),
            data=json.dumps(
                {"ticket_number": self.chamado.numero, "target": "atendente", "attendant_id": self.attendant.id}
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], Chamado.STATUS_ATRIBUIDO)
        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, Chamado.STATUS_ATRIBUIDO)
        self.assertFalse(
            AtendimentoHistorico.objects.filter(chamado=self.chamado, finalizado_em__isnull=True).exists()
        )

        # Play inicia o periodo de atendimento e move para "Em atendimento".
        resp = self.client.post(
            reverse("start_attendance"),
            data=json.dumps({"ticket_number": self.chamado.numero}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, Chamado.STATUS_EM_ATENDIMENTO)

    def test_play_registra_historico_e_retoma_em_atendimento(self):
        self.chamado.status = Chamado.STATUS_AGUARDANDO_PECA
        self.chamado.save()
        self.client.force_login(self.attendant)
        resp = self.client.post(
            reverse("start_attendance"),
            data=json.dumps({"ticket_number": self.chamado.numero}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, Chamado.STATUS_EM_ATENDIMENTO)
        self.assertTrue(
            ChamadoEvento.objects.filter(
                chamado=self.chamado, descricao__icontains="Atendimento iniciado"
            ).exists()
        )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PendenciaTITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.common = User.objects.create_user(username="comum", password="x")
        self.creator = User.objects.create_user(username="ti1", password="x")
        self.attendant = User.objects.create_user(username="ti2", password="x")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        grupo = Group.objects.get(name=ATTENDANT_GROUP_NAME)
        self.creator.groups.add(grupo)
        self.attendant.groups.add(grupo)

    def _create_pendencia(self, autor):
        return PendenciaTI.objects.create(
            titulo="Trocar switch", descricao="Switch do 2o andar", criado_por=autor
        )

    def test_attendant_creates_pendencia(self):
        self.client.force_login(self.creator)
        resp = self.client.post(
            reverse("pendencia_create"),
            data=json.dumps({"titulo": "Comprar toner", "descricao": "Impressora sala 3"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(PendenciaTI.objects.filter(titulo="Comprar toner").exists())

    def test_common_user_cannot_create_or_view_pendencia(self):
        self.client.force_login(self.common)
        resp = self.client.post(
            reverse("pendencia_create"),
            data=json.dumps({"titulo": "Invadindo", "descricao": "nao pode"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

        pend = self._create_pendencia(self.creator)
        resp = self.client.get(reverse("pendencia_detail", args=[pend.id]))
        self.assertEqual(resp.status_code, 403)

    def test_convert_pendencia_creates_chamado(self):
        pend = self._create_pendencia(self.creator)
        self.client.force_login(self.attendant)
        resp = self.client.post(
            reverse("pendencia_convert", args=[pend.id]),
            data=json.dumps({"attendant_id": self.attendant.id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        chamado = Chamado.objects.get(numero=data["ticket_number"])
        self.assertEqual(chamado.titulo, "Trocar switch")
        self.assertEqual(chamado.solicitante, self.creator)  # solicitante = quem criou a pendencia
        self.assertEqual(chamado.atendente_atual, self.attendant)  # atendente da coluna destino
        # Convertida para a coluna do atendente = atribuida (sem Play ativo ainda).
        self.assertEqual(chamado.status, Chamado.STATUS_ATRIBUIDO)

        pend.refresh_from_db()
        self.assertTrue(pend.convertido_em_chamado)
        self.assertEqual(pend.chamado_gerado, chamado)
        self.assertEqual(pend.convertido_por, self.attendant)

        self.assertTrue(
            ChamadoEvento.objects.filter(chamado=chamado, descricao__icontains="pendencia").exists()
        )

    def test_convert_twice_does_not_duplicate(self):
        pend = self._create_pendencia(self.creator)
        self.client.force_login(self.attendant)
        url = reverse("pendencia_convert", args=[pend.id])
        body = json.dumps({"attendant_id": self.attendant.id})

        first = self.client.post(url, data=body, content_type="application/json")
        self.assertEqual(first.status_code, 200)
        second = self.client.post(url, data=body, content_type="application/json")
        self.assertEqual(second.status_code, 409)

        self.assertEqual(Chamado.objects.filter(pendencias_origem=pend).count(), 1)

    def test_convert_rejects_non_attendant_target(self):
        pend = self._create_pendencia(self.creator)
        self.client.force_login(self.attendant)
        resp = self.client.post(
            reverse("pendencia_convert", args=[pend.id]),
            data=json.dumps({"attendant_id": self.common.id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        pend.refresh_from_db()
        self.assertFalse(pend.convertido_em_chamado)

    def test_common_user_cannot_convert(self):
        pend = self._create_pendencia(self.creator)
        self.client.force_login(self.common)
        resp = self.client.post(
            reverse("pendencia_convert", args=[pend.id]),
            data=json.dumps({"attendant_id": self.attendant.id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_attendant_deletes_pendencia(self):
        pend = self._create_pendencia(self.creator)
        self.client.force_login(self.attendant)
        resp = self.client.post(reverse("pendencia_delete", args=[pend.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(PendenciaTI.objects.filter(id=pend.id).exists())

    def test_common_user_cannot_delete_pendencia(self):
        pend = self._create_pendencia(self.creator)
        self.client.force_login(self.common)
        resp = self.client.post(reverse("pendencia_delete", args=[pend.id]))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(PendenciaTI.objects.filter(id=pend.id).exists())

    def test_delete_pendencia_requires_post(self):
        pend = self._create_pendencia(self.creator)
        self.client.force_login(self.attendant)
        resp = self.client.get(reverse("pendencia_delete", args=[pend.id]))
        self.assertEqual(resp.status_code, 405)

    def test_create_pendencia_without_priority_is_colorless(self):
        self.client.force_login(self.creator)
        resp = self.client.post(
            reverse("pendencia_create"),
            data=json.dumps({"titulo": "Sem prioridade", "descricao": "sem cor"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        pend = PendenciaTI.objects.get(titulo="Sem prioridade")
        self.assertIsNone(pend.prioridade)
        self.assertEqual(pend.cor, "")

    def test_create_pendencia_with_priority(self):
        self.client.force_login(self.creator)
        resp = self.client.post(
            reverse("pendencia_create"),
            data=json.dumps(
                {"titulo": "Urgente", "descricao": "vermelho", "prioridade": 1}
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        pend = PendenciaTI.objects.get(titulo="Urgente")
        self.assertEqual(pend.prioridade, 1)

    def test_create_pendencia_invalid_priority_is_colorless(self):
        self.client.force_login(self.creator)
        resp = self.client.post(
            reverse("pendencia_create"),
            data=json.dumps(
                {"titulo": "Invalida", "descricao": "fora da escala", "prioridade": 99}
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        pend = PendenciaTI.objects.get(titulo="Invalida")
        self.assertIsNone(pend.prioridade)

    def test_detail_returns_priority_and_color(self):
        pend = self._create_pendencia(self.creator)
        pend.prioridade = 2
        pend.save(update_fields=["prioridade"])
        self.client.force_login(self.attendant)
        resp = self.client.get(reverse("pendencia_detail", args=[pend.id]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["prioridade"], 2)
        self.assertEqual(data["cor"], PendenciaTI.PRIORIDADE_CORES[2])

    def test_update_priority(self):
        pend = self._create_pendencia(self.creator)
        self.client.force_login(self.attendant)
        resp = self.client.post(
            reverse("pendencia_priority", args=[pend.id]),
            data=json.dumps({"prioridade": 5}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        pend.refresh_from_db()
        self.assertEqual(pend.prioridade, 5)
        self.assertEqual(resp.json()["cor"], PendenciaTI.PRIORIDADE_CORES[5])

    def test_update_priority_requires_post(self):
        pend = self._create_pendencia(self.creator)
        self.client.force_login(self.attendant)
        resp = self.client.get(reverse("pendencia_priority", args=[pend.id]))
        self.assertEqual(resp.status_code, 405)

    def test_common_user_cannot_update_priority(self):
        pend = self._create_pendencia(self.creator)
        self.client.force_login(self.common)
        resp = self.client.post(
            reverse("pendencia_priority", args=[pend.id]),
            data=json.dumps({"prioridade": 1}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_priority_ordering_red_first_colorless_last(self):
        sem_cor = PendenciaTI.objects.create(
            titulo="Sem cor", descricao="branco", criado_por=self.creator
        )
        baixa = PendenciaTI.objects.create(
            titulo="Baixa", descricao="verde", criado_por=self.creator, prioridade=5
        )
        urgente = PendenciaTI.objects.create(
            titulo="Urgente", descricao="vermelho", criado_por=self.creator, prioridade=1
        )
        media = PendenciaTI.objects.create(
            titulo="Media", descricao="amarelo", criado_por=self.creator, prioridade=3
        )
        # Vermelho no topo, verde depois, e as sem cor por ultimo.
        ordenadas = list(PendenciaTI.objects.all())
        self.assertEqual(ordenadas, [urgente, media, baixa, sem_cor])


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class RequisicaoDeleteFilesTests(TestCase):
    """Ao excluir uma requisicao, os arquivos fisicos (fotos e documentos dos
    orcamentos e suborcamentos) devem ser removidos do disco pelos signals."""

    def setUp(self):
        User = get_user_model()
        self.ti = User.objects.create_user(username="ti", password="x")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        self.ti.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))

    def _img(self, nome):
        # PNG 1x1 minimo valido para o ImageField aceitar.
        conteudo = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
            b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return SimpleUploadedFile(nome, conteudo, content_type="image/png")

    def test_delete_removes_physical_files(self):
        requisicao = RequisicaoContrato.objects.create(titulo="Notebooks", criado_por=self.ti)
        orcamento = OrcamentoContrato.objects.create(
            requisicao=requisicao, titulo="Loja A", foto_produto=self._img("orc.png")
        )
        orc_doc = OrcamentoDocumento.objects.create(
            orcamento=orcamento,
            arquivo=SimpleUploadedFile("orc.pdf", b"pdf", content_type="application/pdf"),
            nome_original="orc.pdf",
        )
        suborcamento = SuborcamentoContrato.objects.create(
            orcamento_pai=orcamento, titulo="Complemento", foto_produto=self._img("sub.png")
        )
        sub_doc = SuborcamentoDocumento.objects.create(
            suborcamento=suborcamento,
            arquivo=SimpleUploadedFile("sub.pdf", b"pdf", content_type="application/pdf"),
            nome_original="sub.pdf",
        )

        caminhos = [
            orcamento.foto_produto.path,
            orc_doc.arquivo.path,
            suborcamento.foto_produto.path,
            sub_doc.arquivo.path,
        ]
        for caminho in caminhos:
            self.assertTrue(os.path.exists(caminho), f"arquivo deveria existir: {caminho}")

        self.client.force_login(self.ti)
        resp = self.client.post(reverse("requisicao_delete", args=[requisicao.id]))
        self.assertEqual(resp.status_code, 200)

        self.assertFalse(RequisicaoContrato.objects.filter(id=requisicao.id).exists())
        for caminho in caminhos:
            self.assertFalse(os.path.exists(caminho), f"arquivo orfao nao removido: {caminho}")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class OrcamentoAprovacaoTests(TestCase):
    """Aprovacao exclusiva de orcamento dentro de uma requisicao."""

    def setUp(self):
        User = get_user_model()
        self.common = User.objects.create_user(username="comum", password="x")
        self.ti = User.objects.create_user(username="ti", password="x")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        self.ti.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))

        self.requisicao = RequisicaoContrato.objects.create(
            titulo="Notebooks", criado_por=self.ti, status=RequisicaoContrato.STATUS_EM_COTACAO
        )
        self.orc_a = OrcamentoContrato.objects.create(requisicao=self.requisicao, titulo="Loja A")
        self.orc_b = OrcamentoContrato.objects.create(requisicao=self.requisicao, titulo="Loja B")

    def _aprovar(self, orcamento):
        return self.client.post(reverse("orcamento_aprovar", args=[orcamento.id]))

    def test_aprovar_e_exclusivo_e_aguarda_entrega(self):
        self.client.force_login(self.ti)
        resp = self._aprovar(self.orc_a)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["aprovado"])

        self.orc_a.refresh_from_db()
        self.orc_b.refresh_from_db()
        self.requisicao.refresh_from_db()
        self.assertTrue(self.orc_a.aprovado)
        self.assertEqual(self.orc_a.aprovado_por, self.ti)
        self.assertFalse(self.orc_b.aprovado)
        # Aprovar move a requisicao para "Aguardando entrega" (nao "Finalizada").
        self.assertEqual(self.requisicao.status, RequisicaoContrato.STATUS_AGUARDANDO_ENTREGA)
        # Historico registra a aprovacao.
        self.assertTrue(
            self.requisicao.eventos.filter(tipo=RequisicaoContratoEvento.TIPO_APROVACAO).exists()
        )

        # Aprovar o B remove a aprovacao do A (exclusiva).
        self._aprovar(self.orc_b)
        self.orc_a.refresh_from_db()
        self.orc_b.refresh_from_db()
        self.assertFalse(self.orc_a.aprovado)
        self.assertTrue(self.orc_b.aprovado)

    def test_remover_aprovacao_volta_para_esperando(self):
        self.client.force_login(self.ti)
        self._aprovar(self.orc_a)  # aprova
        resp = self._aprovar(self.orc_a)  # alterna: desaprova
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["aprovado"])

        self.orc_a.refresh_from_db()
        self.requisicao.refresh_from_db()
        self.assertFalse(self.orc_a.aprovado)
        self.assertEqual(self.requisicao.status, RequisicaoContrato.STATUS_EM_COTACAO)

    def test_marcar_entregue(self):
        self.client.force_login(self.ti)
        self._aprovar(self.orc_a)  # precisa estar aprovada primeiro
        resp = self.client.post(reverse("requisicao_marcar_entregue", args=[self.requisicao.id]))
        self.assertEqual(resp.status_code, 200)

        self.requisicao.refresh_from_db()
        self.assertEqual(self.requisicao.status, RequisicaoContrato.STATUS_ENTREGUE)
        self.assertIsNotNone(self.requisicao.entregue_em)
        self.assertEqual(self.requisicao.entregue_por, self.ti)
        self.assertTrue(
            self.requisicao.eventos.filter(tipo=RequisicaoContratoEvento.TIPO_ENTREGA).exists()
        )

        # Nao pode marcar entregue de novo, nem alterar aprovacao depois de entregue.
        self.assertEqual(
            self.client.post(reverse("requisicao_marcar_entregue", args=[self.requisicao.id])).status_code,
            409,
        )
        self.assertEqual(self._aprovar(self.orc_a).status_code, 409)

    def test_marcar_entregue_exige_orcamento_aprovado(self):
        self.client.force_login(self.ti)
        resp = self.client.post(reverse("requisicao_marcar_entregue", args=[self.requisicao.id]))
        self.assertEqual(resp.status_code, 409)  # nenhum orcamento aprovado

    def test_codigo_gerado_continua_do_sistema_antigo(self):
        # Sem requisicoes anteriores no setUp com codigo, a primeira criada aqui
        # deve seguir a numeracao a partir de REQ-00049.
        RequisicaoContrato.objects.all().delete()
        req = RequisicaoContrato.objects.create(titulo="Primeira", criado_por=self.ti)
        self.assertEqual(req.codigo, "REQ-00049")
        req2 = RequisicaoContrato.objects.create(titulo="Segunda", criado_por=self.ti)
        self.assertEqual(req2.codigo, "REQ-00050")

    def test_common_user_cannot_approve(self):
        self.client.force_login(self.common)
        resp = self._aprovar(self.orc_a)
        self.assertEqual(resp.status_code, 403)
        self.orc_a.refresh_from_db()
        self.assertFalse(self.orc_a.aprovado)

    def test_aprovar_requires_post(self):
        self.client.force_login(self.ti)
        resp = self.client.get(reverse("orcamento_aprovar", args=[self.orc_a.id]))
        self.assertEqual(resp.status_code, 405)

    def test_desaprovar_requisicao_limpa_todos_e_volta_para_esperando(self):
        self.client.force_login(self.ti)
        self._aprovar(self.orc_a)  # aprova A -> requisicao "Aguardando entrega"
        self.requisicao.refresh_from_db()
        self.assertEqual(self.requisicao.status, RequisicaoContrato.STATUS_AGUARDANDO_ENTREGA)

        resp = self.client.post(reverse("requisicao_desaprovar", args=[self.requisicao.id]))
        self.assertEqual(resp.status_code, 200)

        self.orc_a.refresh_from_db()
        self.orc_b.refresh_from_db()
        self.requisicao.refresh_from_db()
        self.assertFalse(self.orc_a.aprovado)
        self.assertIsNone(self.orc_a.aprovado_em)
        self.assertIsNone(self.orc_a.aprovado_por)
        self.assertFalse(self.orc_b.aprovado)
        self.assertEqual(self.requisicao.status, RequisicaoContrato.STATUS_EM_COTACAO)
        self.assertTrue(
            self.requisicao.eventos.filter(tipo=RequisicaoContratoEvento.TIPO_APROVACAO).exists()
        )

    def test_desaprovar_sem_orcamento_aprovado_retorna_409(self):
        self.client.force_login(self.ti)
        resp = self.client.post(reverse("requisicao_desaprovar", args=[self.requisicao.id]))
        self.assertEqual(resp.status_code, 409)

    def test_desaprovar_bloqueado_apos_entregue(self):
        self.client.force_login(self.ti)
        self._aprovar(self.orc_a)
        self.client.post(reverse("requisicao_marcar_entregue", args=[self.requisicao.id]))
        resp = self.client.post(reverse("requisicao_desaprovar", args=[self.requisicao.id]))
        self.assertEqual(resp.status_code, 409)
        self.orc_a.refresh_from_db()
        self.assertTrue(self.orc_a.aprovado)  # continua aprovado

    def test_common_user_cannot_desaprovar(self):
        self.client.force_login(self.ti)
        self._aprovar(self.orc_a)
        self.client.logout()
        self.client.force_login(self.common)
        resp = self.client.post(reverse("requisicao_desaprovar", args=[self.requisicao.id]))
        self.assertEqual(resp.status_code, 403)

    def test_desaprovar_requires_post(self):
        self.client.force_login(self.ti)
        resp = self.client.get(reverse("requisicao_desaprovar", args=[self.requisicao.id]))
        self.assertEqual(resp.status_code, 405)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class RequisicaoEdicaoTests(TestCase):
    """Edicao de requisicao e de seus orcamentos/suborcamentos."""

    def setUp(self):
        User = get_user_model()
        self.common = User.objects.create_user(username="comum", password="x")
        self.ti = User.objects.create_user(username="ti", password="x")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        self.ti.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))

        self.requisicao = RequisicaoContrato.objects.create(
            titulo="Notebooks", tipo=RequisicaoContrato.TIPO_FISICA, criado_por=self.ti
        )
        self.orcamento = OrcamentoContrato.objects.create(
            requisicao=self.requisicao, titulo="Loja A", valor=Decimal("100.00"), quantidade=1
        )
        self.suborcamento = SuborcamentoContrato.objects.create(
            orcamento_pai=self.orcamento, titulo="Complemento", valor=Decimal("10.00"), quantidade=1
        )

    # ----- requisicao -----
    def test_ti_edita_requisicao(self):
        self.client.force_login(self.ti)
        resp = self.client.post(
            reverse("requisicao_edit", args=[self.requisicao.id]),
            data=json.dumps({"titulo": "Notebooks Dell", "tipo": "digital", "texto": "Atualizado"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.requisicao.refresh_from_db()
        self.assertEqual(self.requisicao.titulo, "Notebooks Dell")
        self.assertEqual(self.requisicao.tipo, RequisicaoContrato.TIPO_DIGITAL)
        self.assertEqual(self.requisicao.texto, "Atualizado")
        self.assertTrue(
            self.requisicao.eventos.filter(tipo=RequisicaoContratoEvento.TIPO_EDICAO).exists()
        )

    def test_edita_requisicao_titulo_curto(self):
        self.client.force_login(self.ti)
        resp = self.client.post(
            reverse("requisicao_edit", args=[self.requisicao.id]),
            data=json.dumps({"titulo": "N", "tipo": "fisica", "texto": ""}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.requisicao.refresh_from_db()
        self.assertEqual(self.requisicao.titulo, "Notebooks")

    def test_common_nao_edita_requisicao(self):
        self.client.force_login(self.common)
        resp = self.client.post(
            reverse("requisicao_edit", args=[self.requisicao.id]),
            data=json.dumps({"titulo": "Hack", "tipo": "fisica", "texto": ""}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_edita_requisicao_requires_post(self):
        self.client.force_login(self.ti)
        resp = self.client.get(reverse("requisicao_edit", args=[self.requisicao.id]))
        self.assertEqual(resp.status_code, 405)

    # ----- orcamento -----
    def test_ti_edita_orcamento(self):
        self.client.force_login(self.ti)
        resp = self.client.post(
            reverse("orcamento_edit", args=[self.orcamento.id]),
            data={
                "titulo": "Loja B",
                "loja": "Kabum",
                "moeda": "BRL",
                "valor": "250,50",
                "quantidade": "3",
                "frete": "10",
                "desconto": "5",
                "link": "",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.orcamento.refresh_from_db()
        self.assertEqual(self.orcamento.titulo, "Loja B")
        self.assertEqual(self.orcamento.loja, "Kabum")
        self.assertEqual(self.orcamento.valor, Decimal("250.50"))
        self.assertEqual(self.orcamento.quantidade, 3)

    def test_edita_orcamento_bloqueado_apos_entregue(self):
        self.requisicao.status = RequisicaoContrato.STATUS_ENTREGUE
        self.requisicao.save(update_fields=["status"])
        self.client.force_login(self.ti)
        resp = self.client.post(
            reverse("orcamento_edit", args=[self.orcamento.id]),
            data={"titulo": "Nova", "moeda": "BRL", "valor": "1", "quantidade": "1"},
        )
        self.assertEqual(resp.status_code, 409)
        self.orcamento.refresh_from_db()
        self.assertEqual(self.orcamento.titulo, "Loja A")

    def test_common_nao_edita_orcamento(self):
        self.client.force_login(self.common)
        resp = self.client.post(
            reverse("orcamento_edit", args=[self.orcamento.id]),
            data={"titulo": "Nova", "moeda": "BRL", "valor": "1", "quantidade": "1"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_edita_orcamento_remove_documento(self):
        doc = OrcamentoDocumento.objects.create(
            orcamento=self.orcamento,
            arquivo=SimpleUploadedFile("orc.pdf", b"pdf", content_type="application/pdf"),
            nome_original="orc.pdf",
        )
        caminho = doc.arquivo.path
        self.assertTrue(os.path.exists(caminho))
        self.client.force_login(self.ti)
        resp = self.client.post(
            reverse("orcamento_edit", args=[self.orcamento.id]),
            data={
                "titulo": "Loja A",
                "moeda": "BRL",
                "valor": "100",
                "quantidade": "1",
                "remover_documentos": str(doc.id),
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(OrcamentoDocumento.objects.filter(id=doc.id).exists())
        self.assertFalse(os.path.exists(caminho))

    # ----- suborcamento -----
    def test_ti_edita_suborcamento(self):
        self.client.force_login(self.ti)
        resp = self.client.post(
            reverse("suborcamento_edit", args=[self.suborcamento.id]),
            data={"titulo": "Complemento X", "moeda": "BRL", "valor": "20", "quantidade": "2"},
        )
        self.assertEqual(resp.status_code, 200)
        self.suborcamento.refresh_from_db()
        self.assertEqual(self.suborcamento.titulo, "Complemento X")
        self.assertEqual(self.suborcamento.valor, Decimal("20.00"))
        self.assertEqual(self.suborcamento.quantidade, 2)

    def test_edita_suborcamento_bloqueado_apos_entregue(self):
        self.requisicao.status = RequisicaoContrato.STATUS_ENTREGUE
        self.requisicao.save(update_fields=["status"])
        self.client.force_login(self.ti)
        resp = self.client.post(
            reverse("suborcamento_edit", args=[self.suborcamento.id]),
            data={"titulo": "Nova", "moeda": "BRL", "valor": "1", "quantidade": "1"},
        )
        self.assertEqual(resp.status_code, 409)


class RequisicaoRenumeracaoTests(TestCase):
    """Migration 0042: renumera os codigos por ordem de criacao (mais recente = 51)."""

    def _renumerar(self):
        import importlib

        from django.apps import apps as global_apps

        mod = importlib.import_module("core.migrations.0042_renumera_codigos_requisicoes")
        mod.renumerar_codigos(global_apps, None)

    def test_renumera_por_ordem_de_criacao(self):
        User = get_user_model()
        ti = User.objects.create_user(username="ti", password="x")

        # Cria 3 requisicoes e força datas de criacao crescentes e codigos "errados".
        base = timezone.now()
        antiga = RequisicaoContrato.objects.create(titulo="Antiga", criado_por=ti)
        meio = RequisicaoContrato.objects.create(titulo="Meio", criado_por=ti)
        recente = RequisicaoContrato.objects.create(titulo="Recente", criado_por=ti)
        RequisicaoContrato.objects.filter(pk=antiga.pk).update(
            criado_em=base - timezone.timedelta(days=2), codigo="REQ-00099"
        )
        RequisicaoContrato.objects.filter(pk=meio.pk).update(
            criado_em=base - timezone.timedelta(days=1), codigo="REQ-00098"
        )
        RequisicaoContrato.objects.filter(pk=recente.pk).update(
            criado_em=base, codigo="REQ-00097"
        )

        self._renumerar()

        antiga.refresh_from_db()
        meio.refresh_from_db()
        recente.refresh_from_db()
        self.assertEqual(antiga.codigo, "REQ-00049")
        self.assertEqual(meio.codigo, "REQ-00050")
        self.assertEqual(recente.codigo, "REQ-00051")

        # A proxima requisicao continua a partir de REQ-00052.
        proxima = RequisicaoContrato.objects.create(titulo="Proxima", criado_por=ti)
        self.assertEqual(proxima.codigo, "REQ-00052")

    def test_renumera_sem_requisicoes_nao_falha(self):
        self._renumerar()  # banco vazio: nao deve levantar erro
        self.assertEqual(RequisicaoContrato.objects.count(), 0)


class ContaEmailImportTests(TestCase):
    """Importacao da lista de contas de e-mail (upsert por e-mail) e permissoes."""

    def setUp(self):
        User = get_user_model()
        self.common = User.objects.create_user(username="comum", password="x")
        self.ti = User.objects.create_user(username="ti", password="x")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        self.ti.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))

    def _csv(self, deptos):
        header = (
            "First Name [Required],Last Name [Required],Email Address [Required],"
            "Status [READ ONLY],Department,2sv Enrolled [READ ONLY]\n"
        )
        linhas = [
            f"Joao,Silva,joao.silva@x.com,Active,{deptos[0]},True",
            f"Maria,Souza,maria.souza@x.com,Suspended,{deptos[1]},False",
        ]
        conteudo = (header + "\n".join(linhas)).encode("utf-8")
        return SimpleUploadedFile("lista.csv", conteudo, content_type="text/csv")

    def test_ti_import_creates_and_upserts(self):
        self.client.force_login(self.ti)
        resp = self.client.post(reverse("email_import"), {"arquivo": self._csv(["TI", "RH"])})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ContaEmail.objects.count(), 2)

        joao = ContaEmail.objects.get(email="joao.silva@x.com")
        self.assertEqual(joao.primeiro_nome, "Joao")
        self.assertEqual(joao.departamento, "TI")
        self.assertTrue(joao.dois_fatores_inscrito)
        self.assertTrue(joao.is_ativo)
        self.assertFalse(ContaEmail.objects.get(email="maria.souza@x.com").is_ativo)

        # Reimportar com o mesmo e-mail atualiza (nao duplica).
        self.client.post(reverse("email_import"), {"arquivo": self._csv(["Infra", "RH"])})
        self.assertEqual(ContaEmail.objects.count(), 2)
        joao.refresh_from_db()
        self.assertEqual(joao.departamento, "Infra")

    def test_common_user_cannot_import(self):
        self.client.force_login(self.common)
        resp = self.client.post(reverse("email_import"), {"arquivo": self._csv(["TI", "RH"])})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ContaEmail.objects.count(), 0)

    def test_common_user_cannot_access_dashboard(self):
        self.client.force_login(self.common)
        resp = self.client.get(reverse("emails_dashboard"))
        self.assertEqual(resp.status_code, 302)  # redirecionado (sem permissao TI)


class RamalCreateTests(TestCase):
    """Cadastro de ramal (e-mail vindo de uma ContaEmail) e permissoes.

    Obs.: o banco de teste ja vem com os ramais do seed (migration 0013), por
    isso os testes comparam a contagem antes/depois em vez de assumir zero.
    """

    def setUp(self):
        User = get_user_model()
        self.common = User.objects.create_user(username="comum", password="x")
        self.ti = User.objects.create_user(username="ti", password="x")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        self.ti.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))
        self.conta = ContaEmail.objects.create(
            email="novo.contato@x.com", primeiro_nome="Novo", sobrenome="Contato"
        )

    def test_ti_creates_ramal_with_selected_email(self):
        self.client.force_login(self.ti)
        antes = Ramal.objects.count()
        resp = self.client.post(
            reverse("ramal_create"),
            {"colaborador": "Zzz Teste", "setor": "TI", "telefone": "123", "ramal": "9000", "conta_email": self.conta.id},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Ramal.objects.count(), antes + 1)

        ramal = Ramal.objects.get(colaborador="Zzz Teste")
        self.assertEqual(ramal.email, "novo.contato@x.com")  # puxado da conta selecionada
        self.assertEqual(ramal.conta_email, self.conta)
        self.assertEqual(ramal.ramal, "9000")

    def test_create_requires_colaborador(self):
        self.client.force_login(self.ti)
        antes = Ramal.objects.count()
        resp = self.client.post(reverse("ramal_create"), {"colaborador": "", "setor": "TI"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Ramal.objects.count(), antes)  # nada criado

    def test_common_user_cannot_create(self):
        self.client.force_login(self.common)
        antes = Ramal.objects.count()
        resp = self.client.post(
            reverse("ramal_create"), {"colaborador": "Hacker", "setor": "X"}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Ramal.objects.count(), antes)

    def test_common_user_cannot_access_dashboard(self):
        self.client.force_login(self.common)
        resp = self.client.get(reverse("ramais_dashboard"))
        self.assertEqual(resp.status_code, 302)

    def test_create_with_free_email(self):
        """E-mail digitado livremente (sem conta selecionada) e aceito."""
        self.client.force_login(self.ti)
        self.client.post(
            reverse("ramal_create"),
            {"colaborador": "Sala Teste", "setor": "Reuniao", "email": "livre@x.com"},
        )
        ramal = Ramal.objects.get(colaborador="Sala Teste")
        self.assertEqual(ramal.email, "livre@x.com")
        self.assertIsNone(ramal.conta_email)

    def test_ti_updates_ramal(self):
        self.client.force_login(self.ti)
        ramal = Ramal.objects.create(colaborador="Antigo", setor="X", ramal="1000")
        resp = self.client.post(
            reverse("ramal_update", args=[ramal.id]),
            {"colaborador": "Novo Nome", "setor": "TI", "telefone": "9", "ramal": "1001", "conta_email": self.conta.id},
        )
        self.assertEqual(resp.status_code, 302)
        ramal.refresh_from_db()
        self.assertEqual(ramal.colaborador, "Novo Nome")
        self.assertEqual(ramal.ramal, "1001")
        self.assertEqual(ramal.email, self.conta.email)  # veio da conta selecionada
        self.assertEqual(ramal.conta_email, self.conta)

    def test_ti_deletes_ramal(self):
        self.client.force_login(self.ti)
        ramal = Ramal.objects.create(colaborador="Excluir", setor="X")
        antes = Ramal.objects.count()
        resp = self.client.post(reverse("ramal_delete", args=[ramal.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Ramal.objects.count(), antes - 1)
        self.assertFalse(Ramal.objects.filter(id=ramal.id).exists())

    def test_common_user_cannot_update_or_delete(self):
        ramal = Ramal.objects.create(colaborador="Protegido", setor="X")
        self.client.force_login(self.common)
        self.client.post(reverse("ramal_update", args=[ramal.id]), {"colaborador": "Hack"})
        self.client.post(reverse("ramal_delete", args=[ramal.id]))
        ramal.refresh_from_db()
        self.assertEqual(ramal.colaborador, "Protegido")  # inalterado
        self.assertTrue(Ramal.objects.filter(id=ramal.id).exists())  # nao excluido


class LicencaTests(TestCase):
    """Modulo Licencas: CRUD de software e licenca, prazos e permissoes.

    Obs.: o banco de teste ja vem com os softwares/licencas do seed (migration
    0015), por isso os testes comparam contagem antes/depois.
    """

    def setUp(self):
        User = get_user_model()
        self.common = User.objects.create_user(username="comum", password="x")
        self.ti = User.objects.create_user(username="ti", password="x")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        self.ti.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))

    def test_ti_creates_software(self):
        self.client.force_login(self.ti)
        antes = LicencaSoftware.objects.count()
        resp = self.client.post(
            reverse("licenca_software_create"),
            {"nome": "Photoshop 2026", "quantidade_licencas": 4, "observacoes": "Assinatura"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(LicencaSoftware.objects.count(), antes + 1)
        soft = LicencaSoftware.objects.get(nome="Photoshop 2026")
        self.assertEqual(soft.quantidade_licencas, 4)
        self.assertEqual(soft.criado_por, self.ti)

    def test_software_create_requires_name(self):
        self.client.force_login(self.ti)
        antes = LicencaSoftware.objects.count()
        resp = self.client.post(reverse("licenca_software_create"), {"nome": "", "quantidade_licencas": 1})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(LicencaSoftware.objects.count(), antes)  # nada criado

    def test_ti_creates_license_and_expiration(self):
        self.client.force_login(self.ti)
        soft = LicencaSoftware.objects.create(nome="CorelDRAW", quantidade_licencas=2, criado_por=self.ti)
        resp = self.client.post(
            reverse("licenca_create"),
            {
                "software": soft.id,
                "usuario_atribuido": "Fulano",
                "serial": "ABC-123",
                "email_vinculado": "fulano@x.com",
                "tipo_expiracao": "expira_em",
                "expira_em": "2027-01-01",
                "forma_pagamento": "Boleto",
                "final_cartao": "9999",
            },
        )
        self.assertEqual(resp.status_code, 302)
        lic = Licenca.objects.get(serial="ABC-123")
        self.assertEqual(lic.software, soft)
        self.assertEqual(lic.expira_label, "01/01/2027")
        self.assertEqual(lic.final_cartao, "9999")

    def test_indeterminado_clears_expira(self):
        """Prazo indeterminado ignora a data enviada."""
        self.client.force_login(self.ti)
        soft = LicencaSoftware.objects.create(nome="Zoom", quantidade_licencas=1, criado_por=self.ti)
        self.client.post(
            reverse("licenca_create"),
            {"software": soft.id, "tipo_expiracao": "indeterminado", "expira_em": "2027-05-05", "usuario_atribuido": "X"},
        )
        lic = Licenca.objects.get(software=soft, usuario_atribuido="X")
        self.assertIsNone(lic.expira_em)
        self.assertEqual(lic.expira_label, "Indeterminado")

    def test_license_requires_valid_software(self):
        self.client.force_login(self.ti)
        antes = Licenca.objects.count()
        resp = self.client.post(reverse("licenca_create"), {"software": 999999, "usuario_atribuido": "X"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Licenca.objects.count(), antes)  # nada criado

    def test_ti_updates_and_deletes_license(self):
        self.client.force_login(self.ti)
        soft = LicencaSoftware.objects.create(nome="Slack", quantidade_licencas=1, criado_por=self.ti)
        lic = Licenca.objects.create(software=soft, usuario_atribuido="Antes", criado_por=self.ti)
        self.client.post(
            reverse("licenca_update", args=[lic.id]),
            {"software": soft.id, "usuario_atribuido": "Depois", "tipo_expiracao": "indeterminado"},
        )
        lic.refresh_from_db()
        self.assertEqual(lic.usuario_atribuido, "Depois")

        resp = self.client.post(reverse("licenca_delete", args=[lic.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Licenca.objects.filter(id=lic.id).exists())

    def test_delete_software_cascades_licenses(self):
        self.client.force_login(self.ti)
        soft = LicencaSoftware.objects.create(nome="Trello", quantidade_licencas=1, criado_por=self.ti)
        lic = Licenca.objects.create(software=soft, usuario_atribuido="Y", criado_por=self.ti)
        resp = self.client.post(reverse("licenca_software_delete", args=[soft.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(LicencaSoftware.objects.filter(id=soft.id).exists())
        self.assertFalse(Licenca.objects.filter(id=lic.id).exists())  # cascata

    def test_common_user_cannot_access_or_change(self):
        soft = LicencaSoftware.objects.create(nome="Protegido", quantidade_licencas=1, criado_por=self.ti)
        self.client.force_login(self.common)
        # Dashboard redireciona
        self.assertEqual(self.client.get(reverse("licencas_dashboard")).status_code, 302)
        # Nao cria software nem licenca
        antes_s = LicencaSoftware.objects.count()
        antes_l = Licenca.objects.count()
        self.client.post(reverse("licenca_software_create"), {"nome": "Hack", "quantidade_licencas": 1})
        self.client.post(reverse("licenca_create"), {"software": soft.id, "usuario_atribuido": "Hack"})
        self.assertEqual(LicencaSoftware.objects.count(), antes_s)
        self.assertEqual(Licenca.objects.count(), antes_l)
        # Nao exclui
        self.client.post(reverse("licenca_software_delete", args=[soft.id]))
        self.assertTrue(LicencaSoftware.objects.filter(id=soft.id).exists())

    def test_dashboard_lists_seeded_software(self):
        self.client.force_login(self.ti)
        resp = self.client.get(reverse("licencas_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "AutoCAD 2014 Full")


class EnderecoIPTests(TestCase):
    """Modulo IPs: CRUD, unicidade do IP, categoria e permissoes.

    Obs.: o banco de teste ja vem com os IPs do seed (migration 0017).
    """

    def setUp(self):
        User = get_user_model()
        self.common = User.objects.create_user(username="comum", password="x")
        self.ti = User.objects.create_user(username="ti", password="x")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        self.ti.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))

    def test_ti_creates_ip(self):
        self.client.force_login(self.ti)
        antes = EnderecoIP.objects.count()
        resp = self.client.post(
            reverse("ip_create"),
            {"categoria": "servers", "endereco_ip": "10.0.0.9", "nome": "SRV-TESTE", "mac": "AA:BB:CC:DD:EE:FF"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(EnderecoIP.objects.count(), antes + 1)
        ip = EnderecoIP.objects.get(endereco_ip="10.0.0.9")
        self.assertEqual(ip.categoria, "servers")
        self.assertEqual(ip.criado_por, self.ti)

    def test_create_requires_ip_and_valid_category(self):
        self.client.force_login(self.ti)
        antes = EnderecoIP.objects.count()
        # sem endereco
        self.client.post(reverse("ip_create"), {"categoria": "servers", "endereco_ip": ""})
        # categoria invalida
        self.client.post(reverse("ip_create"), {"categoria": "xpto", "endereco_ip": "10.0.0.10"})
        self.assertEqual(EnderecoIP.objects.count(), antes)  # nada criado

    def test_duplicate_ip_is_rejected(self):
        self.client.force_login(self.ti)
        EnderecoIP.objects.create(categoria="wifi", endereco_ip="10.0.0.20", criado_por=self.ti)
        antes = EnderecoIP.objects.count()
        resp = self.client.post(
            reverse("ip_create"), {"categoria": "servers", "endereco_ip": "10.0.0.20"}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(EnderecoIP.objects.count(), antes)  # nao duplicou

    def test_ti_updates_and_deletes_ip(self):
        self.client.force_login(self.ti)
        ip = EnderecoIP.objects.create(categoria="printers", endereco_ip="10.0.0.30", nome="Antes", criado_por=self.ti)
        resp = self.client.post(
            reverse("ip_update", args=[ip.id]),
            {"categoria": "printers", "endereco_ip": "10.0.0.30", "nome": "Depois"},
        )
        self.assertEqual(resp.status_code, 302)
        ip.refresh_from_db()
        self.assertEqual(ip.nome, "Depois")

        resp = self.client.post(reverse("ip_delete", args=[ip.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(EnderecoIP.objects.filter(id=ip.id).exists())

    def test_update_keeps_own_ip_without_duplicate_error(self):
        """Editar mantendo o mesmo IP nao dispara falso positivo de duplicidade."""
        self.client.force_login(self.ti)
        ip = EnderecoIP.objects.create(categoria="switches", endereco_ip="10.0.0.40", criado_por=self.ti)
        resp = self.client.post(
            reverse("ip_update", args=[ip.id]),
            {"categoria": "switches", "endereco_ip": "10.0.0.40", "nome": "Switch Novo"},
        )
        self.assertEqual(resp.status_code, 302)
        ip.refresh_from_db()
        self.assertEqual(ip.nome, "Switch Novo")

    def test_common_user_cannot_access_or_change(self):
        ip = EnderecoIP.objects.create(categoria="wifi", endereco_ip="10.0.0.50", criado_por=self.ti)
        self.client.force_login(self.common)
        self.assertEqual(self.client.get(reverse("ips_dashboard")).status_code, 302)
        antes = EnderecoIP.objects.count()
        self.client.post(reverse("ip_create"), {"categoria": "servers", "endereco_ip": "10.0.0.99"})
        self.assertEqual(EnderecoIP.objects.count(), antes)
        self.client.post(reverse("ip_delete", args=[ip.id]))
        self.assertTrue(EnderecoIP.objects.filter(id=ip.id).exists())

    def test_dashboard_renders_with_seeded_data(self):
        self.client.force_login(self.ti)
        resp = self.client.get(reverse("ips_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ips-table")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ServicoFeitoTests(TestCase):
    """Modulo Servicos feitos: CRUD, anexos, valor BR e permissoes.

    Obs.: o banco de teste ja vem com os servicos do seed (migration 0019),
    por isso os testes comparam contagem antes/depois.
    """

    def setUp(self):
        User = get_user_model()
        self.common = User.objects.create_user(username="comum", password="x")
        self.ti = User.objects.create_user(username="ti", password="x")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        self.ti.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))

    def _arquivo(self, nome="nota.pdf"):
        return SimpleUploadedFile(nome, b"%PDF-1.4 conteudo", content_type="application/pdf")

    def test_ti_creates_service_with_attachments(self):
        self.client.force_login(self.ti)
        antes = ServicoFeito.objects.count()
        resp = self.client.post(
            reverse("servico_feito_create"),
            {
                "nome_servico": "Troca de switch",
                "empresa": "Acme",
                "data_servico": "2026-05-10",
                "valor": "1.234,56",
                "descricao": "Substituicao do switch principal",
                "anexos": [self._arquivo("nf1.pdf"), self._arquivo("nf2.pdf")],
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ServicoFeito.objects.count(), antes + 1)
        servico = ServicoFeito.objects.get(nome_servico="Troca de switch")
        self.assertEqual(str(servico.valor), "1234.56")  # valor BR convertido
        self.assertEqual(servico.anexos.count(), 2)
        self.assertEqual(servico.criado_por, self.ti)

    def test_create_requires_name(self):
        self.client.force_login(self.ti)
        antes = ServicoFeito.objects.count()
        resp = self.client.post(reverse("servico_feito_create"), {"nome_servico": "", "valor": "10"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ServicoFeito.objects.count(), antes)

    def test_valor_display_pt_br(self):
        s = ServicoFeito.objects.create(nome_servico="X", valor="20796.01", criado_por=self.ti)
        self.assertEqual(s.valor_display, "20.796,01")

    def test_ti_updates_and_adds_attachment(self):
        self.client.force_login(self.ti)
        s = ServicoFeito.objects.create(nome_servico="Antes", valor="100", criado_por=self.ti)
        resp = self.client.post(
            reverse("servico_feito_update", args=[s.id]),
            {"nome_servico": "Depois", "valor": "200", "data_servico": "2026-06-01", "anexos": [self._arquivo()]},
        )
        self.assertEqual(resp.status_code, 302)
        s.refresh_from_db()
        self.assertEqual(s.nome_servico, "Depois")
        self.assertEqual(str(s.valor), "200.00")
        self.assertEqual(s.anexos.count(), 1)

    def test_delete_service_cascades_attachments(self):
        self.client.force_login(self.ti)
        s = ServicoFeito.objects.create(nome_servico="Apagar", valor="1", criado_por=self.ti)
        a = ServicoFeitoAnexo.objects.create(servico=s, arquivo=self._arquivo(), nome_original="x.pdf")
        resp = self.client.post(reverse("servico_feito_delete", args=[s.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(ServicoFeito.objects.filter(id=s.id).exists())
        self.assertFalse(ServicoFeitoAnexo.objects.filter(id=a.id).exists())

    def test_delete_single_attachment(self):
        self.client.force_login(self.ti)
        s = ServicoFeito.objects.create(nome_servico="Com anexo", valor="1", criado_por=self.ti)
        a = ServicoFeitoAnexo.objects.create(servico=s, arquivo=self._arquivo(), nome_original="x.pdf")
        resp = self.client.post(reverse("servico_feito_anexo_delete", args=[a.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(ServicoFeitoAnexo.objects.filter(id=a.id).exists())
        self.assertTrue(ServicoFeito.objects.filter(id=s.id).exists())  # servico permanece

    def test_detail_json_and_download(self):
        self.client.force_login(self.ti)
        s = ServicoFeito.objects.create(nome_servico="Detalhe", empresa="Y", valor="50", criado_por=self.ti)
        a = ServicoFeitoAnexo.objects.create(servico=s, arquivo=self._arquivo(), nome_original="doc.pdf")
        resp = self.client.get(reverse("servico_feito_detail", args=[s.id]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["valor_display"], "50,00")
        self.assertEqual(len(data["anexos"]), 1)
        # Download protegido funciona para TI
        dl = self.client.get(reverse("servico_feito_anexo_download", args=[a.id]))
        self.assertEqual(dl.status_code, 200)

    def test_common_user_blocked(self):
        s = ServicoFeito.objects.create(nome_servico="Protegido", valor="1", criado_por=self.ti)
        a = ServicoFeitoAnexo.objects.create(servico=s, arquivo=self._arquivo(), nome_original="x.pdf")
        self.client.force_login(self.common)
        self.assertEqual(self.client.get(reverse("servicos_feitos_dashboard")).status_code, 302)
        self.assertEqual(self.client.get(reverse("servico_feito_detail", args=[s.id])).status_code, 403)
        self.assertEqual(self.client.get(reverse("servico_feito_anexo_download", args=[a.id])).status_code, 404)
        antes = ServicoFeito.objects.count()
        self.client.post(reverse("servico_feito_create"), {"nome_servico": "Hack", "valor": "1"})
        self.assertEqual(ServicoFeito.objects.count(), antes)
        self.client.post(reverse("servico_feito_delete", args=[s.id]))
        self.assertTrue(ServicoFeito.objects.filter(id=s.id).exists())


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ContratoTests(TestCase):
    """Modulo Contratos: CRUD, anexos, valor BR, periodicidade e permissoes.

    Obs.: o banco de teste ja vem com os contratos do seed (migration 0021).
    """

    def setUp(self):
        User = get_user_model()
        self.common = User.objects.create_user(username="comum", password="x")
        self.ti = User.objects.create_user(username="ti", password="x")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        self.ti.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))

    def _arquivo(self, nome="contrato.pdf"):
        return SimpleUploadedFile(nome, b"%PDF-1.4 x", content_type="application/pdf")

    def test_ti_creates_contract_with_attachments(self):
        self.client.force_login(self.ti)
        antes = Contrato.objects.count()
        resp = self.client.post(
            reverse("contrato_ti_create"),
            {
                "nome": "Contrato Teste Unico",
                "valor": "4.798,03",
                "periodicidade": "mensal",
                "forma_pagamento": "Boleto",
                "inicio": "2026-02-28",
                "fim": "2029-02-28",
                "anexos": [self._arquivo("nf.pdf")],
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Contrato.objects.count(), antes + 1)
        ctr = Contrato.objects.get(nome="Contrato Teste Unico")
        self.assertEqual(str(ctr.valor), "4798.03")
        self.assertEqual(ctr.periodicidade, "mensal")
        self.assertEqual(ctr.anexos.count(), 1)
        self.assertTrue(ctr.esta_ativo)
        self.assertEqual(ctr.criado_por, self.ti)

    def test_create_requires_name(self):
        self.client.force_login(self.ti)
        antes = Contrato.objects.count()
        self.client.post(reverse("contrato_ti_create"), {"nome": "", "valor": "10"})
        self.assertEqual(Contrato.objects.count(), antes)

    def test_valor_display_and_optional_value(self):
        c1 = Contrato.objects.create(nome="Com valor", valor="1716.20", criado_por=self.ti)
        self.assertEqual(c1.valor_display, "1.716,20")
        c2 = Contrato.objects.create(nome="Sem valor", criado_por=self.ti)
        self.assertEqual(c2.valor_display, "-")

    def test_encerrado_marks_inactive(self):
        self.client.force_login(self.ti)
        c = Contrato.objects.create(nome="Ativo", valor="1", criado_por=self.ti)
        self.assertTrue(c.esta_ativo)
        self.client.post(
            reverse("contrato_ti_update", args=[c.id]),
            {"nome": "Ativo", "valor": "1", "periodicidade": "mensal", "encerrado_em": "2026-05-26"},
        )
        c.refresh_from_db()
        self.assertFalse(c.esta_ativo)

    def test_delete_cascades_attachments(self):
        self.client.force_login(self.ti)
        c = Contrato.objects.create(nome="Apagar", valor="1", criado_por=self.ti)
        a = ContratoAnexo.objects.create(contrato=c, arquivo=self._arquivo(), nome_original="x.pdf")
        resp = self.client.post(reverse("contrato_ti_delete", args=[c.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Contrato.objects.filter(id=c.id).exists())
        self.assertFalse(ContratoAnexo.objects.filter(id=a.id).exists())

    def test_delete_single_attachment(self):
        self.client.force_login(self.ti)
        c = Contrato.objects.create(nome="Com anexo", valor="1", criado_por=self.ti)
        a = ContratoAnexo.objects.create(contrato=c, arquivo=self._arquivo(), nome_original="x.pdf")
        resp = self.client.post(reverse("contrato_ti_anexo_delete", args=[a.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(ContratoAnexo.objects.filter(id=a.id).exists())
        self.assertTrue(Contrato.objects.filter(id=c.id).exists())

    def test_detail_json_and_download(self):
        self.client.force_login(self.ti)
        c = Contrato.objects.create(nome="Detalhe", valor="50", periodicidade="anual", criado_por=self.ti)
        a = ContratoAnexo.objects.create(contrato=c, arquivo=self._arquivo(), nome_original="doc.pdf")
        resp = self.client.get(reverse("contrato_ti_detail", args=[c.id]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["valor_display"], "50,00")
        self.assertEqual(data["periodicidade"], "Anual")
        self.assertEqual(len(data["anexos"]), 1)
        dl = self.client.get(reverse("contrato_ti_anexo_download", args=[a.id]))
        self.assertEqual(dl.status_code, 200)

    def test_common_user_blocked(self):
        c = Contrato.objects.create(nome="Protegido", valor="1", criado_por=self.ti)
        a = ContratoAnexo.objects.create(contrato=c, arquivo=self._arquivo(), nome_original="x.pdf")
        self.client.force_login(self.common)
        self.assertEqual(self.client.get(reverse("contratos_ti_dashboard")).status_code, 302)
        self.assertEqual(self.client.get(reverse("contrato_ti_detail", args=[c.id])).status_code, 403)
        self.assertEqual(self.client.get(reverse("contrato_ti_anexo_download", args=[a.id])).status_code, 404)
        antes = Contrato.objects.count()
        self.client.post(reverse("contrato_ti_create"), {"nome": "Hack", "valor": "1"})
        self.assertEqual(Contrato.objects.count(), antes)
        self.client.post(reverse("contrato_ti_delete", args=[c.id]))
        self.assertTrue(Contrato.objects.filter(id=c.id).exists())


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FuturaDigitalTests(TestCase):
    """Modulo Futura Digital: regra de cobranca, CRUD e permissoes.

    Obs.: o banco de teste ja vem com as faturas do seed (migration 0023).
    """

    def setUp(self):
        User = get_user_model()
        self.common = User.objects.create_user(username="comum", password="x")
        self.ti = User.objects.create_user(username="ti", password="x")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        self.ti.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))

    def test_billing_rule(self):
        """valor = franquia + excedentes*rate_exc + cor*rate_cor;
        excedentes = (total - cor) - franquia."""
        self.client.force_login(self.ti)
        resp = self.client.post(
            reverse("futura_digital_create"),
            {
                "mes_referencia": "2026-07",
                "copias_total": "34744",
                "copias_cor": "317",
                "franquia_copias": "23000",
                "franquia_valor": "1610,00",
                "valor_copia_excedente": "0,07",
                "valor_copia_cor": "0,75",
            },
        )
        self.assertEqual(resp.status_code, 302)
        f = FuturaDigital.objects.get(mes_referencia="2026-07-01")
        # (34744 - 317) - 23000 = 11427
        self.assertEqual(f.copias_excedentes, 11427)
        # 1610 + 11427*0.07 + 317*0.75 = 2647.64
        self.assertEqual(str(f.valor_pago), "2647.64")
        self.assertEqual(f.criado_por, self.ti)

    def test_month_normalized_to_first_day(self):
        self.client.force_login(self.ti)
        self.client.post(
            reverse("futura_digital_create"),
            {"mes_referencia": "2026-08", "copias_total": "1000", "copias_cor": "0"},
        )
        f = FuturaDigital.objects.get(mes_referencia="2026-08-01")
        self.assertEqual(f.mes_referencia.day, 1)

    def test_no_excess_when_below_franchise(self):
        self.client.force_login(self.ti)
        self.client.post(
            reverse("futura_digital_create"),
            {"mes_referencia": "2026-09", "copias_total": "10000", "copias_cor": "0", "franquia_copias": "23000"},
        )
        f = FuturaDigital.objects.get(mes_referencia="2026-09-01")
        self.assertEqual(f.copias_excedentes, 0)
        self.assertEqual(str(f.valor_pago), "1610.00")  # so a franquia

    def test_create_requires_month(self):
        self.client.force_login(self.ti)
        antes = FuturaDigital.objects.count()
        self.client.post(reverse("futura_digital_create"), {"mes_referencia": "", "copias_total": "10"})
        self.assertEqual(FuturaDigital.objects.count(), antes)

    def test_update_recalculates(self):
        self.client.force_login(self.ti)
        f = FuturaDigital.objects.create(mes_referencia="2027-01-01", copias_total=1000, copias_cor=0)
        f.recalcular(); f.save()
        self.client.post(
            reverse("futura_digital_update", args=[f.id]),
            {"mes_referencia": "2027-01", "copias_total": "60000", "copias_cor": "500", "franquia_copias": "23000"},
        )
        f.refresh_from_db()
        # (60000 - 500) - 23000 = 36500
        self.assertEqual(f.copias_excedentes, 36500)

    def test_delete(self):
        self.client.force_login(self.ti)
        f = FuturaDigital.objects.create(mes_referencia="2027-02-01", copias_total=1000)
        resp = self.client.post(reverse("futura_digital_delete", args=[f.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(FuturaDigital.objects.filter(id=f.id).exists())

    def test_common_user_blocked(self):
        f = FuturaDigital.objects.create(mes_referencia="2027-03-01", copias_total=1000)
        self.client.force_login(self.common)
        self.assertEqual(self.client.get(reverse("futura_digital_dashboard")).status_code, 302)
        antes = FuturaDigital.objects.count()
        self.client.post(reverse("futura_digital_create"), {"mes_referencia": "2027-04", "copias_total": "1"})
        self.assertEqual(FuturaDigital.objects.count(), antes)
        self.client.post(reverse("futura_digital_delete", args=[f.id]))
        self.assertTrue(FuturaDigital.objects.filter(id=f.id).exists())

    def test_dashboard_renders_chart_data(self):
        self.client.force_login(self.ti)
        resp = self.client.get(reverse("futura_digital_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "fdSerie")
        self.assertContains(resp, "fd-chart")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DicaTests(TestCase):
    """Modulo Dicas: CRUD, categorias, anexo e permissoes.

    Obs.: o banco de teste ja vem com as dicas do seed (migration 0025).
    """

    def setUp(self):
        User = get_user_model()
        self.common = User.objects.create_user(username="comum", password="x")
        self.ti = User.objects.create_user(username="ti", password="x")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        self.ti.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))

    def _img(self, nome="print.png"):
        return SimpleUploadedFile(nome, b"\x89PNG\r\n\x1a\n fake", content_type="image/png")

    def test_ti_creates_dica(self):
        self.client.force_login(self.ti)
        antes = Dica.objects.count()
        resp = self.client.post(
            reverse("dica_create"),
            {"categoria": "resolucao", "titulo": "Reset do servidor X", "conteudo": "Passo 1\nPasso 2", "anexo": self._img()},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Dica.objects.count(), antes + 1)
        d = Dica.objects.get(titulo="Reset do servidor X")
        self.assertEqual(d.categoria, "resolucao")
        self.assertTrue(d.anexo)
        self.assertEqual(d.criado_por, self.ti)

    def test_create_requires_title(self):
        self.client.force_login(self.ti)
        antes = Dica.objects.count()
        self.client.post(reverse("dica_create"), {"categoria": "geral", "titulo": ""})
        self.assertEqual(Dica.objects.count(), antes)

    def test_invalid_category_falls_back_to_geral(self):
        self.client.force_login(self.ti)
        self.client.post(reverse("dica_create"), {"categoria": "xpto", "titulo": "Dica Z"})
        self.assertEqual(Dica.objects.get(titulo="Dica Z").categoria, "geral")

    def test_update_and_remove_attachment(self):
        self.client.force_login(self.ti)
        d = Dica.objects.create(categoria="geral", titulo="Antes", conteudo="x", anexo=self._img())
        self.assertTrue(d.anexo)
        self.client.post(
            reverse("dica_update", args=[d.id]),
            {"categoria": "configuracao", "titulo": "Depois", "conteudo": "y", "remover_anexo": "1"},
        )
        d.refresh_from_db()
        self.assertEqual(d.titulo, "Depois")
        self.assertEqual(d.categoria, "configuracao")
        self.assertFalse(d.anexo)

    def test_delete(self):
        self.client.force_login(self.ti)
        d = Dica.objects.create(categoria="geral", titulo="Apagar")
        resp = self.client.post(reverse("dica_delete", args=[d.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Dica.objects.filter(id=d.id).exists())

    def test_anexo_download_protected(self):
        d = Dica.objects.create(categoria="geral", titulo="Com anexo", anexo=self._img())
        self.client.force_login(self.ti)
        self.assertEqual(self.client.get(reverse("dica_anexo", args=[d.id])).status_code, 200)
        self.client.force_login(self.common)
        self.assertEqual(self.client.get(reverse("dica_anexo", args=[d.id])).status_code, 404)

    def test_common_user_blocked(self):
        d = Dica.objects.create(categoria="geral", titulo="Protegida")
        self.client.force_login(self.common)
        self.assertEqual(self.client.get(reverse("dicas_dashboard")).status_code, 302)
        antes = Dica.objects.count()
        self.client.post(reverse("dica_create"), {"categoria": "geral", "titulo": "Hack"})
        self.assertEqual(Dica.objects.count(), antes)
        self.client.post(reverse("dica_delete", args=[d.id]))
        self.assertTrue(Dica.objects.filter(id=d.id).exists())

    def test_dashboard_renders_seeded(self):
        self.client.force_login(self.ti)
        resp = self.client.get(reverse("dicas_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "dica-card")


class StarlinkTests(TestCase):
    """Modulo Starlinks: CRUD, senha (manter na edicao) e permissoes.

    Obs.: o banco de teste ja vem com as Starlinks do seed (migration 0027).
    """

    def setUp(self):
        User = get_user_model()
        self.common = User.objects.create_user(username="comum", password="x")
        self.ti = User.objects.create_user(username="ti", password="x")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        self.ti.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))

    def test_ti_creates_starlink(self):
        self.client.force_login(self.ti)
        antes = Starlink.objects.count()
        resp = self.client.post(
            reverse("starlink_create"),
            {
                "nome": "Star99", "local": "Obra X", "email": "star99@sidertec.com.br",
                "ativo": "1", "forma_pagamento": "cartao",
                "final_cartao": "1234", "numero_serie": "SN123", "numero_kit": "KIT123",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Starlink.objects.count(), antes + 1)
        s = Starlink.objects.get(nome="Star99")
        self.assertTrue(s.ativo)
        self.assertEqual(s.numero_serie, "SN123")
        self.assertEqual(s.criado_por, self.ti)

    def test_create_requires_name(self):
        self.client.force_login(self.ti)
        antes = Starlink.objects.count()
        self.client.post(reverse("starlink_create"), {"nome": "", "email": "x@x.com"})
        self.assertEqual(Starlink.objects.count(), antes)

    def test_inactive_when_unchecked(self):
        self.client.force_login(self.ti)
        self.client.post(reverse("starlink_create"), {"nome": "Inativa", "forma_pagamento": "pix"})
        s = Starlink.objects.get(nome="Inativa")
        self.assertFalse(s.ativo)  # sem 'ativo' no POST => inativa
        self.assertEqual(s.forma_pagamento, "pix")

    def test_update_changes_fields(self):
        self.client.force_login(self.ti)
        s = Starlink.objects.create(nome="Star", local="Antigo", ativo=True)
        self.client.post(
            reverse("starlink_update", args=[s.id]),
            {"nome": "Star", "local": "Novo", "ativo": "1", "forma_pagamento": "cartao"},
        )
        s.refresh_from_db()
        self.assertEqual(s.local, "Novo")

    def test_delete(self):
        self.client.force_login(self.ti)
        s = Starlink.objects.create(nome="Apagar")
        resp = self.client.post(reverse("starlink_delete", args=[s.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Starlink.objects.filter(id=s.id).exists())

    def test_common_user_blocked(self):
        s = Starlink.objects.create(nome="Protegida")
        self.client.force_login(self.common)
        self.assertEqual(self.client.get(reverse("starlinks_dashboard")).status_code, 302)
        antes = Starlink.objects.count()
        self.client.post(reverse("starlink_create"), {"nome": "Hack"})
        self.assertEqual(Starlink.objects.count(), antes)
        self.client.post(reverse("starlink_delete", args=[s.id]))
        self.assertTrue(Starlink.objects.filter(id=s.id).exists())

    def test_dashboard_renders_seeded(self):
        self.client.force_login(self.ti)
        resp = self.client.get(reverse("starlinks_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "star-card")


class CofreCryptoTests(TestCase):
    """Cifra/decifra das credenciais do cofre."""

    def test_encrypt_decrypt_round_trip(self):
        from core.crypto import decrypt_text, encrypt_text
        token = encrypt_text("segredo-super-secreto")
        self.assertNotEqual(token, "segredo-super-secreto")  # cifrado
        self.assertEqual(decrypt_text(token), "segredo-super-secreto")
        self.assertEqual(decrypt_text(""), "")

    def test_credencial_set_get_password(self):
        c = CofreCredencial(rotulo="X")
        c.definir_senha("minha-senha")
        self.assertNotIn("minha-senha", c.senha_cifrada)  # nao fica em texto
        self.assertEqual(c.obter_senha(), "minha-senha")


class CofreTests(TestCase):
    """Cofre: senha-mestra, destrave, revelar sob demanda, auditoria e permissoes."""

    def setUp(self):
        User = get_user_model()
        self.common = User.objects.create_user(username="comum", password="x")
        self.ti = User.objects.create_user(username="ti", password="x")
        self.admin = User.objects.create_user(username="adm", password="x")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
        att = Group.objects.get(name=ATTENDANT_GROUP_NAME)
        adm = Group.objects.get(name=ADMIN_GROUP_NAME)
        self.ti.groups.add(att)
        self.admin.groups.add(adm, att)
        # Zera qualquer config de seed para comecar do estado 'setup'.
        CofreConfig.objects.all().delete()

    def test_dashboard_setup_state_without_master(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("cofre_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Configurar o cofre")

    def test_common_user_blocked(self):
        self.client.force_login(self.common)
        self.assertEqual(self.client.get(reverse("cofre_dashboard")).status_code, 302)

    def test_only_admin_sets_master(self):
        # TI (nao admin) nao pode definir senha-mestra
        self.client.force_login(self.ti)
        self.client.post(reverse("cofre_set_master"), {"nova_senha": "abcdef", "confirma_senha": "abcdef"})
        self.assertFalse(CofreConfig.load().tem_senha_mestra)
        # Admin pode
        self.client.force_login(self.admin)
        self.client.post(reverse("cofre_set_master"), {"nova_senha": "abcdef", "confirma_senha": "abcdef"})
        self.assertTrue(CofreConfig.load().tem_senha_mestra)

    def test_unlock_flow_and_reveal_requires_unlock(self):
        cfg = CofreConfig.load()
        cfg.definir_senha_mestra("chave123")
        cfg.save()
        cred = CofreCredencial(rotulo="Roteador", usuario="admin")
        cred.definir_senha("root123")
        cred.save()

        self.client.force_login(self.ti)
        # Travado: revelar deve dar 403
        r = self.client.post(reverse("cofre_credencial_reveal", args=[cred.id]))
        self.assertEqual(r.status_code, 403)

        # Senha-mestra errada
        self.client.post(reverse("cofre_unlock"), {"senha_mestra": "errada"})
        r = self.client.post(reverse("cofre_credencial_reveal", args=[cred.id]))
        self.assertEqual(r.status_code, 403)

        # Senha-mestra certa -> destrava
        self.client.post(reverse("cofre_unlock"), {"senha_mestra": "chave123"})
        r = self.client.post(reverse("cofre_credencial_reveal", args=[cred.id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["senha"], "root123")
        # Revelacao auditada
        self.assertTrue(CofreAuditoria.objects.filter(acao=CofreAuditoria.ACAO_CRED_REVELADA, credencial=cred).exists())

    def test_lockout_after_max_attempts(self):
        cfg = CofreConfig.load()
        cfg.definir_senha_mestra("chave123")
        cfg.save()
        self.client.force_login(self.ti)
        for _ in range(5):
            self.client.post(reverse("cofre_unlock"), {"senha_mestra": "errada"})
        cfg.refresh_from_db()
        self.assertTrue(cfg.esta_bloqueado())
        # Mesmo com a senha certa, bloqueado nao destrava
        self.client.post(reverse("cofre_unlock"), {"senha_mestra": "chave123"})
        r = self.client.post(reverse("cofre_credencial_reveal", args=[CofreCredencial.objects.create(rotulo="Y").id]))
        self.assertEqual(r.status_code, 403)

    def test_credential_crud_requires_unlock(self):
        cfg = CofreConfig.load()
        cfg.definir_senha_mestra("chave123")
        cfg.save()
        self.client.force_login(self.ti)
        # Travado: criar credencial nao funciona
        antes = CofreCredencial.objects.count()
        self.client.post(reverse("cofre_credencial_create"), {"rotulo": "Nova", "senha": "s"})
        self.assertEqual(CofreCredencial.objects.count(), antes)
        # Destrava e cria
        self.client.post(reverse("cofre_unlock"), {"senha_mestra": "chave123"})
        self.client.post(reverse("cofre_credencial_create"), {"rotulo": "Nova", "usuario": "u", "senha": "s3nha"})
        cred = CofreCredencial.objects.get(rotulo="Nova")
        self.assertEqual(cred.obter_senha(), "s3nha")
        # Atualiza mantendo senha (branco)
        self.client.post(reverse("cofre_credencial_update", args=[cred.id]), {"rotulo": "Nova2", "senha": ""})
        cred.refresh_from_db()
        self.assertEqual(cred.rotulo, "Nova2")
        self.assertEqual(cred.obter_senha(), "s3nha")
        # Exclui
        self.client.post(reverse("cofre_credencial_delete", args=[cred.id]))
        self.assertFalse(CofreCredencial.objects.filter(id=cred.id).exists())

    def test_lock_clears_session(self):
        cfg = CofreConfig.load()
        cfg.definir_senha_mestra("chave123")
        cfg.save()
        self.client.force_login(self.ti)
        self.client.post(reverse("cofre_unlock"), {"senha_mestra": "chave123"})
        cred = CofreCredencial.objects.create(rotulo="Z")
        self.assertEqual(self.client.post(reverse("cofre_credencial_reveal", args=[cred.id])).status_code, 200)
        self.client.post(reverse("cofre_lock"))
        self.assertEqual(self.client.post(reverse("cofre_credencial_reveal", args=[cred.id])).status_code, 403)


_LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(), EMAIL_BACKEND_OVERRIDE=_LOCMEM)
class EmailNotificacaoTests(TestCase):
    """Notificacoes por e-mail: disparo nos eventos e configuracao (SMTP)."""

    def setUp(self):
        from .models import EmailConfig

        User = get_user_model()
        self.owner = User.objects.create_user(username="joao", password="x", email="joao@empresa.com")
        self.attendant = User.objects.create_user(username="ti", password="x", email="atendente@empresa.com")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        self.attendant.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))

        self.config = EmailConfig.load()
        self.config.ativo = True
        self.config.usuario = "chamados@empresa.com"
        self.config.remetente = "chamados@empresa.com"
        self.config.emails_ti = "suporte@empresa.com, ti@empresa.com"
        self.config.save()

    # --- Disparo dos eventos ---------------------------------------------
    def test_novo_chamado_portal_notifica_solicitante_e_ti(self):
        from django.core import mail

        mail.outbox = []
        self.client.force_login(self.owner)
        resp = self.client.post(
            reverse("open_ticket"), {"titulo": "PC nao liga", "descricao": "O computador nao liga de jeito nenhum"}
        )
        self.assertEqual(resp.status_code, 302)
        destinos = {d for m in mail.outbox for d in m.to}
        self.assertIn("joao@empresa.com", destinos)
        self.assertIn("suporte@empresa.com", destinos)
        self.assertIn("ti@empresa.com", destinos)

    def test_solicitante_da_ti_nao_recebe_copia_pessoal(self):
        # Quando o solicitante e da propria TI (ex.: atendente abre/converte um
        # chamado para si), ele so recebe pela lista da TI, sem a confirmacao
        # pessoal — evitando dois e-mails da mesma acao.
        from django.core import mail
        from .emails import notificar_novo_chamado

        chamado = Chamado.objects.create(
            numero="CH-000210", titulo="Meu proprio chamado", solicitante=self.attendant,
            solicitante_nome="TI", solicitante_email="atendente@empresa.com",
            status=Chamado.STATUS_ABERTO,
        )
        mail.outbox = []
        notificar_novo_chamado(chamado)
        destinos = {d for m in mail.outbox for d in m.to}
        # Recebe apenas pela lista da TI; nada de copia pessoal (um unico e-mail).
        self.assertNotIn("atendente@empresa.com", destinos)
        self.assertIn("suporte@empresa.com", destinos)
        self.assertIn("ti@empresa.com", destinos)

    def test_notificacoes_desligadas_nao_enviam(self):
        from django.core import mail

        self.config.ativo = False
        self.config.save()
        mail.outbox = []
        self.client.force_login(self.owner)
        resp = self.client.post(
            reverse("open_ticket"),
            {"titulo": "Sem rede", "descricao": "Nao tenho acesso a internet aqui"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_mensagem_do_solicitante_notifica_so_ti(self):
        from django.core import mail

        chamado = Chamado.objects.create(
            numero="CH-000201", titulo="T", solicitante=self.owner,
            solicitante_email="joao@empresa.com", status=Chamado.STATUS_ABERTO,
        )
        mail.outbox = []
        self.client.force_login(self.owner)
        resp = self.client.post(
            reverse("ticket_message_create", args=[chamado.numero]), {"texto": "Ola"}
        )
        self.assertEqual(resp.status_code, 302)
        destinos = {d for m in mail.outbox for d in m.to}
        # O proprio autor (solicitante) nao recebe copia.
        self.assertNotIn("joao@empresa.com", destinos)
        self.assertIn("suporte@empresa.com", destinos)

    def test_mensagem_da_ti_notifica_solicitante(self):
        from django.core import mail

        chamado = Chamado.objects.create(
            numero="CH-000202", titulo="T", solicitante=self.owner,
            solicitante_email="joao@empresa.com", status=Chamado.STATUS_EM_ATENDIMENTO,
        )
        mail.outbox = []
        self.client.force_login(self.attendant)
        self.client.post(reverse("ticket_message_create", args=[chamado.numero]), {"texto": "resolvendo"})
        destinos = {d for m in mail.outbox for d in m.to}
        self.assertIn("joao@empresa.com", destinos)
        self.assertNotIn("atendente@empresa.com", destinos)

    def test_mudanca_status_notifica(self):
        from django.core import mail

        chamado = Chamado.objects.create(
            numero="CH-000203", titulo="T", solicitante=self.owner,
            solicitante_email="joao@empresa.com", status=Chamado.STATUS_ABERTO,
        )
        mail.outbox = []
        self.client.force_login(self.attendant)
        resp = self.client.post(
            reverse("move_ticket"),
            data=json.dumps(
                {"ticket_number": chamado.numero, "target": "atendente", "attendant_id": self.attendant.id}
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(mail.outbox), 1)
        assunto = " ".join(m.subject for m in mail.outbox)
        self.assertIn(chamado.numero, assunto)

    def test_fechamento_stop_notifica(self):
        from django.core import mail

        chamado = Chamado.objects.create(
            numero="CH-000204", titulo="T", solicitante=self.owner,
            solicitante_email="joao@empresa.com", status=Chamado.STATUS_EM_ATENDIMENTO,
            atendente_atual=self.attendant,
        )
        AtendimentoHistorico.objects.create(
            chamado=chamado, atendente=self.attendant, iniciado_em=timezone.now()
        )
        mail.outbox = []
        self.client.force_login(self.attendant)
        resp = self.client.post(
            reverse("finish_attendance"),
            data=json.dumps({"ticket_number": chamado.numero, "action": "stop", "description": "trocado o cabo"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        corpos = " ".join(m.body for m in mail.outbox)
        self.assertIn("trocado o cabo", corpos)
        self.assertIn("joao@empresa.com", {d for m in mail.outbox for d in m.to})

    def test_falha_de_envio_nao_quebra_o_chamado(self):
        # Sem remetente configurado, o envio e ignorado silenciosamente.
        self.config.usuario = ""
        self.config.remetente = ""
        self.config.save()
        self.client.force_login(self.owner)
        resp = self.client.post(
            reverse("open_ticket"),
            {"titulo": "Teste sem remetente", "descricao": "Deve abrir mesmo sem e-mail"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Chamado.objects.filter(titulo="Teste sem remetente").exists())

    # --- Tela de configuracao --------------------------------------------
    def test_config_screen_ti_ok_comum_bloqueado(self):
        self.client.force_login(self.attendant)
        self.assertEqual(self.client.get(reverse("email_config")).status_code, 200)

        comum = get_user_model().objects.create_user(username="c", password="x")
        self.client.force_login(comum)
        resp = self.client.get(reverse("email_config"))
        self.assertEqual(resp.status_code, 302)

    def test_salvar_config_cifra_a_senha(self):
        from .models import EmailConfig

        self.client.force_login(self.attendant)
        resp = self.client.post(
            reverse("email_config_save"),
            {
                "ativo": "on", "host": "smtp.gmail.com", "porta": "587", "usar_tls": "on",
                "timeout": "15", "usuario": "conta@gmail.com", "remetente_nome": "Chamados TI",
                "emails_ti": "ti@empresa.com", "senha": "abcd efgh ijkl mnop",
                "notif_novo_chamado": "on",
            },
        )
        self.assertEqual(resp.status_code, 302)
        cfg = EmailConfig.load()
        self.assertTrue(cfg.tem_senha)
        # Espacos removidos e senha recuperavel (cifrada em repouso).
        self.assertEqual(cfg.obter_senha(), "abcdefghijklmnop")
        # A senha em texto nao aparece no campo cifrado do banco.
        self.assertNotIn("abcdefghijklmnop", cfg.senha_cifrada)

    def test_salvar_sem_senha_mantem_a_atual(self):
        from .models import EmailConfig

        self.config.definir_senha("segredo123")
        self.config.save()
        self.client.force_login(self.attendant)
        self.client.post(
            reverse("email_config_save"),
            {"ativo": "on", "host": "smtp.gmail.com", "porta": "587", "usar_tls": "on",
             "usuario": "conta@gmail.com", "emails_ti": "ti@empresa.com", "senha": ""},
        )
        self.assertEqual(EmailConfig.load().obter_senha(), "segredo123")

    def test_comum_nao_salva_config(self):
        comum = get_user_model().objects.create_user(username="c2", password="x")
        self.client.force_login(comum)
        resp = self.client.post(reverse("email_config_save"), {"host": "x"})
        self.assertEqual(resp.status_code, 302)  # redirecionado, sem salvar

    def test_email_de_teste(self):
        from django.core import mail

        mail.outbox = []
        self.client.force_login(self.attendant)
        resp = self.client.post(reverse("email_config_test"), {"email_teste": "quem@empresa.com"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("quem@empresa.com", mail.outbox[0].to)

    def test_tls_e_ssl_juntos_sao_rejeitados(self):
        from .models import EmailConfig

        self.client.force_login(self.attendant)
        self.client.post(
            reverse("email_config_save"),
            {"host": "smtp.gmail.com", "porta": "587", "usar_tls": "on", "usar_ssl": "on",
             "usuario": "c@g.com", "emails_ti": "ti@e.com"},
        )
        # Nao deve ter ligado ssl junto com tls (rejeitado).
        cfg = EmailConfig.load()
        self.assertFalse(cfg.usar_tls and cfg.usar_ssl)


class InsumoUpdateTests(TestCase):
    """Edicao de insumo (ajuste de estoque) do modulo Insumos."""

    def setUp(self):
        from .models import InsumoTI

        User = get_user_model()
        self.ti = User.objects.create_user(username="ti_ins", password="x")
        self.common = User.objects.create_user(username="comum_ins", password="x")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        self.ti.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))
        self.insumo = InsumoTI.objects.create(nome="Bateria", quantidade_atual=0)

    def _post(self, name, data):
        return self.client.post(
            reverse(name, args=[self.insumo.id]),
            data=json.dumps(data),
            content_type="application/json",
        )

    def test_editar_nao_altera_quantidade(self):
        self.insumo.quantidade_atual = 10
        self.insumo.save()
        self.client.force_login(self.ti)
        resp = self._post("insumo_update", {"nome": "Bateria AA", "descricao": "recarregavel", "observacao": ""})
        self.assertEqual(resp.status_code, 200)
        self.insumo.refresh_from_db()
        self.assertEqual(self.insumo.nome, "Bateria AA")
        self.assertEqual(self.insumo.descricao, "recarregavel")
        self.assertEqual(self.insumo.quantidade_atual, 10)  # inalterada pela edicao

    def test_entrada_soma_ao_estoque(self):
        self.insumo.quantidade_atual = 5
        self.insumo.save()
        self.client.force_login(self.ti)
        resp = self._post("insumo_entrada", {"quantidade": 8})
        self.assertEqual(resp.status_code, 200)
        self.insumo.refresh_from_db()
        self.assertEqual(self.insumo.quantidade_atual, 13)

    def test_entrada_invalida_rejeitada(self):
        self.client.force_login(self.ti)
        self.assertEqual(self._post("insumo_entrada", {"quantidade": 0}).status_code, 400)
        self.assertEqual(self._post("insumo_entrada", {"quantidade": -3}).status_code, 400)

    def test_entrada_registra_movimento_no_extrato(self):
        from .models import RetiradaInsumoTI

        self.client.force_login(self.ti)
        self._post("insumo_entrada", {"quantidade": 3})
        self.assertTrue(
            RetiradaInsumoTI.objects.filter(
                insumo=self.insumo, tipo=RetiradaInsumoTI.TIPO_ENTRADA, quantidade=3
            ).exists()
        )

    def test_excluir_insumo(self):
        from .models import InsumoTI

        self.client.force_login(self.ti)
        resp = self._post("insumo_delete", {})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(InsumoTI.objects.filter(id=self.insumo.id).exists())

    def test_comum_nao_edita_nem_entrada_nem_exclui(self):
        self.client.force_login(self.common)
        self.assertEqual(self._post("insumo_update", {"nome": "X"}).status_code, 403)
        self.assertEqual(self._post("insumo_entrada", {"quantidade": 5}).status_code, 403)
        self.assertEqual(self._post("insumo_delete", {}).status_code, 403)

    def test_busca_retiradas(self):
        from .models import RetiradaInsumoTI

        RetiradaInsumoTI.objects.create(
            insumo=self.insumo, quantidade=1, entregue_para="Joao Silva", motivo="Departamento: RH")
        self.client.force_login(self.ti)
        resp = self.client.get(reverse("retiradas_search"), {"q": "joao"})
        self.assertEqual(resp.status_code, 200)
        res = resp.json()["resultados"]
        self.assertTrue(any("Joao" in x["entregue_para"] for x in res))
        # termo sem correspondencia
        vazio = self.client.get(reverse("retiradas_search"), {"q": "zzznaoexiste"})
        self.assertEqual(len(vazio.json()["resultados"]), 0)

    def test_busca_retiradas_comum_bloqueado(self):
        self.client.force_login(self.common)
        self.assertEqual(self.client.get(reverse("retiradas_search")).status_code, 403)


class NotificacoesStreamTests(TestCase):
    """Endpoint SSE de notificacoes (permissao e cabecalhos). Nao consome o
    stream (loop infinito) — valida apenas o handshake."""

    def setUp(self):
        User = get_user_model()
        self.ti = User.objects.create_user(username="ti_sse", password="x")
        self.common = User.objects.create_user(username="comum_sse", password="x")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        self.ti.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))

    def test_ti_recebe_event_stream(self):
        self.client.force_login(self.ti)
        resp = self.client.get(reverse("notificacoes_stream"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/event-stream", resp["Content-Type"])
        self.assertEqual(resp["X-Accel-Buffering"], "no")

    def test_comum_bloqueado(self):
        self.client.force_login(self.common)
        resp = self.client.get(reverse("notificacoes_stream"))
        self.assertEqual(resp.status_code, 403)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class EmprestimoEdicaoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.common = User.objects.create_user(username="comum", password="x")
        self.ti = User.objects.create_user(username="ti", password="x")
        Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
        self.ti.groups.add(Group.objects.get(name=ATTENDANT_GROUP_NAME))

    def _novo_emprestimo(self):
        emp = EmprestimoTI.objects.create(
            colaborador_nome="Fulano",
            data_emprestimo="2026-01-10",
            status=EmprestimoTI.STATUS_ASSINADA_OK,
            termo_assinado_ok=True,
            criado_por=self.ti,
        )
        equip = EquipamentoEmprestimoTI.objects.create(
            emprestimo=emp, tipo_equipamento="Notebook", data_emprestimo="2026-01-10"
        )
        return emp, equip

    def test_adicionar_equipamento_volta_para_aguardando(self):
        emp, equip = self._novo_emprestimo()
        self.client.force_login(self.ti)
        resp = self.client.post(
            reverse("emprestimo_editar", args=[emp.id]),
            {
                "colaborador_nome": "Fulano",
                "data_emprestimo": "2026-01-10",
                f"acao_equip_{equip.id}": "manter",
                "equipamentos_count": "1",
                "equip_0_tipo": "Monitor",
                "equip_0_data": "2026-07-05",
            },
        )
        self.assertEqual(resp.status_code, 200)
        emp.refresh_from_db()
        self.assertEqual(emp.equipamentos.count(), 2)
        self.assertEqual(emp.status, EmprestimoTI.STATUS_AGUARDANDO)
        self.assertFalse(emp.termo_assinado_ok)
        self.assertTrue(emp.termo_pdf)
        novo = emp.equipamentos.get(tipo_equipamento="Monitor")
        self.assertEqual(novo.data_emprestimo.isoformat(), "2026-07-05")

    def test_devolver_unico_equipamento_marca_devolvido(self):
        emp, equip = self._novo_emprestimo()
        self.client.force_login(self.ti)
        resp = self.client.post(
            reverse("emprestimo_editar", args=[emp.id]),
            {
                "colaborador_nome": "Fulano",
                "data_emprestimo": "2026-01-10",
                f"acao_equip_{equip.id}": "devolver",
                f"devolver_data_{equip.id}": "2026-07-08",
                "equipamentos_count": "0",
            },
        )
        self.assertEqual(resp.status_code, 200)
        equip.refresh_from_db()
        emp.refresh_from_db()
        self.assertEqual(equip.data_devolucao.isoformat(), "2026-07-08")
        self.assertEqual(emp.status, EmprestimoTI.STATUS_DEVOLVIDO)

    def test_nao_remove_todos_os_equipamentos(self):
        emp, equip = self._novo_emprestimo()
        self.client.force_login(self.ti)
        resp = self.client.post(
            reverse("emprestimo_editar", args=[emp.id]),
            {
                "colaborador_nome": "Fulano",
                "data_emprestimo": "2026-01-10",
                f"acao_equip_{equip.id}": "remover",
                "equipamentos_count": "0",
            },
        )
        self.assertEqual(resp.status_code, 400)
        emp.refresh_from_db()
        self.assertEqual(emp.equipamentos.count(), 1)

    def test_comum_bloqueado(self):
        emp, equip = self._novo_emprestimo()
        self.client.force_login(self.common)
        resp = self.client.post(
            reverse("emprestimo_editar", args=[emp.id]),
            {"colaborador_nome": "Fulano", "data_emprestimo": "2026-01-10", "equipamentos_count": "0"},
        )
        self.assertEqual(resp.status_code, 403)
