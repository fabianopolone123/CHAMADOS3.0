"""Cria um token de API para um sistema de fora.

O valor gerado aparece **uma vez**, aqui na tela: o banco guarda so o hash.
Perdeu, gera outro e desative o antigo.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from core.models import TokenApi


class Command(BaseCommand):
    help = "Cria um token de API vinculado a uma conta do sistema."

    def add_arguments(self, parser):
        parser.add_argument("rotulo", help="Para que serve o token (ex.: 'Sistema do PC do Fabiano').")
        parser.add_argument("usuario", help="Username da conta cujas permissoes o token usa.")
        parser.add_argument(
            "--escrita",
            action="store_true",
            help="Permite gravar. Sem isso o token so le, que e o padrao de proposito.",
        )

    def handle(self, *args, **opcoes):
        User = get_user_model()
        usuario = User.objects.filter(username=opcoes["usuario"]).first()
        if not usuario:
            raise CommandError(f"Usuario nao encontrado: {opcoes['usuario']}")
        if not usuario.is_active:
            raise CommandError(f"A conta {usuario.username} esta desativada.")

        token, valor = TokenApi.gerar(
            rotulo=opcoes["rotulo"],
            usuario=usuario,
            somente_leitura=not opcoes["escrita"],
        )

        permissao = "LE E GRAVA" if opcoes["escrita"] else "SOMENTE LEITURA"
        self.stdout.write(self.style.SUCCESS(f"Token criado: {token.rotulo} ({permissao})"))
        self.stdout.write(f"Conta usada nos pedidos: {usuario.username}")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Guarde agora — este valor nao aparece de novo:"))
        self.stdout.write("")
        self.stdout.write(f"  {valor}")
        self.stdout.write("")
        self.stdout.write("Use assim, em cada pedido:")
        self.stdout.write(f"  Authorization: Token {valor}")
