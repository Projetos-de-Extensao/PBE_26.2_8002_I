"""Cria um conjunto de dados de demonstração para testar e apresentar o sistema.

O comando é idempotente: rodar de novo não duplica nada. As contas criadas
usam uma senha fixa de demonstração e só fazem sentido em ambiente local.
"""

from datetime import date, datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from agendamento.models import (
    Agendamento,
    Cliente,
    Disponibilidade,
    Profissional,
    Recepcionista,
    Recurso,
    Sala,
    Servico,
)

SENHA_EXEMPLO = "exemplo123"

CLIENTES = [
    ("ana.souza@exemplo.local", "Ana Souza"),
    ("bruno.lima@exemplo.local", "Bruno Lima"),
]

PROFISSIONAIS = [
    (
        "carla.dias@exemplo.local",
        "Carla Dias",
        "Personal Trainer",
        Profissional.Modalidade.PRESENCIAL,
        [("Treino individual", "Treino", 60), ("Avaliação física", "Avaliação", 30)],
        [0, 2, 4],
        (time(8), time(18)),
    ),
    (
        "diego.alves@exemplo.local",
        "Diego Alves",
        "Nutricionista",
        Profissional.Modalidade.HIBRIDO,
        [("Consulta nutricional", "Consulta", 50)],
        [1, 3],
        (time(9), time(17)),
    ),
    (
        "elisa.prado@exemplo.local",
        "Elisa Prado",
        "Fisioterapeuta",
        Profissional.Modalidade.PRESENCIAL,
        [("Sessão de fisioterapia", "Sessão", 45), ("Pilates clínico", "Sessão", 60)],
        [1, 3],
        (time(7), time(13)),
    ),
]

SALAS = [("Estúdio 1", 1), ("Consultório 1", 1), ("Sala de Pilates", 4)]
RECURSOS = [("Maca", True), ("Reformer", True), ("Colchonete", False)]


class Command(BaseCommand):
    help = (
        "Cria clientes, profissionais, serviços, salas, equipamentos, "
        "disponibilidades e agendamentos de demonstração."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--silencioso",
            action="store_true",
            help="Não escreve nada na saída (usado pelo iniciar.py).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.silencioso = options["silencioso"]

        salas = {
            nome: Sala.objects.get_or_create(
                nome=nome, defaults={"capacidade": capacidade}
            )[0]
            for nome, capacidade in SALAS
        }
        recursos = {
            nome: Recurso.objects.get_or_create(
                nome=nome, defaults={"exclusivo": exclusivo}
            )[0]
            for nome, exclusivo in RECURSOS
        }

        clientes = [self._cliente(email, nome) for email, nome in CLIENTES]
        self._recepcionista("fernanda.recepcao@exemplo.local", "Fernanda Recepção")

        servicos = {}
        profissionais = []
        for email, nome, especialidade, modalidade, lista, dias, faixa in PROFISSIONAIS:
            profissional = self._profissional(email, nome, especialidade, modalidade)
            profissionais.append(profissional)
            for dia in dias:
                Disponibilidade.objects.get_or_create(
                    profissional=profissional,
                    dia_semana=dia,
                    defaults={"hora_inicio": faixa[0], "hora_fim": faixa[1]},
                )
            for nome_servico, tipo, duracao in lista:
                servico, _ = Servico.objects.get_or_create(
                    profissional=profissional,
                    nome=nome_servico,
                    defaults={"tipo": tipo, "duracao_minutos": duracao},
                )
                servicos[nome_servico] = servico

        criados = self._agendamentos(clientes, servicos, salas, recursos)

        if not self.silencioso:
            self.stdout.write(
                self.style.SUCCESS(
                    "Dados de exemplo prontos: "
                    f"{Profissional.objects.count()} profissionais, "
                    f"{Servico.objects.count()} serviços, "
                    f"{Sala.objects.count()} salas, "
                    f"{Recurso.objects.count()} equipamentos e "
                    f"{Agendamento.objects.count()} agendamentos."
                )
            )
            if criados:
                self.stdout.write(
                    f"Contas de exemplo (senha {SENHA_EXEMPLO}): "
                    + ", ".join(email for email, _ in CLIENTES)
                )

    # -- criação de contas -------------------------------------------------

    def _cliente(self, email, nome):
        return self._usuario(Cliente, email, nome=nome)

    def _recepcionista(self, email, nome):
        return self._usuario(Recepcionista, email, nome=nome)

    def _profissional(self, email, nome, especialidade, modalidade):
        return self._usuario(
            Profissional,
            email,
            nome=nome,
            especialidade=especialidade,
            modalidade=modalidade,
        )

    def _usuario(self, modelo, email, **campos):
        existente = modelo.objects.filter(email=email).first()
        if existente:
            return existente
        return modelo.objects.create_user(
            email=email, password=SENHA_EXEMPLO, **campos
        )

    # -- agendamentos ------------------------------------------------------

    def _agendamentos(self, clientes, servicos, salas, recursos):
        """Cria alguns atendimentos na próxima semana, sem repetir."""
        if Agendamento.objects.exists():
            return False

        segunda = self._proxima_segunda()
        planos = [
            (clientes[0], "Treino individual", segunda, time(16), "Estúdio 1", None),
            (clientes[0], "Consulta nutricional", segunda + timedelta(days=1), time(14), "Consultório 1", None),
            (clientes[0], "Sessão de fisioterapia", segunda + timedelta(days=3), time(10), "Sala de Pilates", "Reformer"),
            (clientes[1], "Avaliação física", segunda, time(9), "Estúdio 1", "Colchonete"),
            (clientes[1], "Treino individual", segunda + timedelta(days=2), time(17), "Estúdio 1", None),
        ]

        for cliente, nome_servico, dia, hora, sala, recurso in planos:
            servico = servicos[nome_servico]
            inicio = timezone.make_aware(datetime.combine(dia, hora))
            agendamento = Agendamento(
                cliente=cliente,
                profissional=servico.profissional,
                servico=servico,
                sala=salas[sala],
                data_hora_inicio=inicio,
                data_hora_fim=servico.calcular_horario_fim(inicio),
                status=Agendamento.Status.CONFIRMADO,
            )
            agendamento.save()
            if recurso:
                agendamento.recursos.set([recursos[recurso]])
        return True

    @staticmethod
    def _proxima_segunda():
        hoje = date.today()
        return hoje + timedelta(days=(7 - hoje.weekday()) % 7 or 7)
