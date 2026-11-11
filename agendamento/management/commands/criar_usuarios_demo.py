import secrets

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from agendamento.models import Cliente, Perfil, Profissional, Recepcionista, Usuario


class Command(BaseCommand):
    help = (
        "Cria contas locais de demonstração para os quatro papéis e mostra "
        "senhas aleatórias de uso local."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        contas = (
            ("Cliente", "cliente@gmail.com"),
            ("Profissional", "profissional@gmail.com"),
            ("Recepcionista", "recepcionista@gmail.com"),
            ("Administrador", "admin@gmail.com"),
        )
        existentes = set(
            Usuario.objects.filter(email__in=[email for _, email in contas])
            .values_list("email", flat=True)
        )
        if existentes:
            lista = ", ".join(sorted(existentes))
            raise CommandError(
                "Contas de demonstração já existem: "
                f"{lista}. Nenhuma conta foi alterada."
            )

        credenciais = [
            (papel, email, secrets.token_urlsafe(24))
            for papel, email in contas
        ]
        Cliente.objects.create_user(
            email=credenciais[0][1],
            password=credenciais[0][2],
            nome="Cliente de demonstração",
        )
        Profissional.objects.create_user(
            email=credenciais[1][1],
            password=credenciais[1][2],
            nome="Profissional de demonstração",
            especialidade="Fisioterapia",
            modalidade=Profissional.Modalidade.PRESENCIAL,
        )
        Recepcionista.objects.create_user(
            email=credenciais[2][1],
            password=credenciais[2][2],
            nome="Recepcionista de demonstração",
        )
        Usuario.objects.create_superuser(
            email=credenciais[3][1],
            password=credenciais[3][2],
            nome="Administrador de demonstração",
        )

        self.stdout.write(self.style.SUCCESS("Contas criadas:"))
        for papel, email, senha in credenciais:
            self.stdout.write(f"{papel}: {email} | Senha: {senha}")
        self.stdout.write(
            self.style.WARNING(
                "Guarde as senhas agora: elas não podem ser recuperadas "
                "pelo sistema."
            )
        )
