import json
import tempfile

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
)
from .permissions import ATTENDANT_GROUP_NAME


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
        self.assertTrue(
            ChamadoEvento.objects.filter(chamado=self.chamado, descricao__icontains="encerrado").exists()
        )

    def test_pause_does_not_close_ticket(self):
        self.client.force_login(self.attendant)
        self._start_attendance(self.attendant)
        resp = self._finish("pause", "Aguardando peca de reposicao")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json().get("ticket_closed"))

        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, Chamado.STATUS_EM_ATENDIMENTO)

    def test_common_user_cannot_finish_attendance(self):
        self.client.force_login(self.owner)
        resp = self._finish("stop", "tentando encerrar")
        self.assertEqual(resp.status_code, 403)

        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, Chamado.STATUS_EM_ATENDIMENTO)
