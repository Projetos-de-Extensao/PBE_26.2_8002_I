from datetime import date, time

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import (
    Agendamento,
    Bloqueio,
    Disponibilidade,
    Profissional,
    Recurso,
    Sala,
    horarios_livres,
)


class SalaTests(TestCase):
    def test_str_e_capacidade_padrao(self):
        sala = Sala.objects.create(nome="Estúdio 1")
        self.assertEqual(str(sala), "Estúdio 1")
        self.assertEqual(sala.capacidade, 1)

    def test_capacidade_minima(self):
        with self.assertRaises(ValidationError):
            Sala(nome="Sala X", capacidade=0).full_clean()

    def test_nome_unico(self):
        Sala.objects.create(nome="Sala A")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Sala.objects.create(nome="Sala A")


class RecursoTests(TestCase):
    def test_exclusivo_por_padrao(self):
        recurso = Recurso.objects.create(nome="Maca")
        self.assertEqual(str(recurso), "Maca")
        self.assertTrue(recurso.exclusivo)

    def test_nome_unico(self):
        Recurso.objects.create(nome="Maca")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Recurso.objects.create(nome="Maca")


class AgendamentoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.cliente = User.objects.create_user("cliente1", password="x")
        self.cliente2 = User.objects.create_user("cliente2", password="x")
        self.prof = Profissional.objects.create(
            usuario=User.objects.create_user("prof1", password="x"),
            especialidade="NUTRICIONISTA",
        )
        self.prof2 = Profissional.objects.create(
            usuario=User.objects.create_user("prof2", password="x"),
            especialidade="PERSONAL",
        )
        dia_semana = date(2026, 11, 3).weekday()
        for profissional in (self.prof, self.prof2):
            Disponibilidade.objects.create(
                profissional=profissional,
                dia_semana=dia_semana,
                hora_inicio=time(8),
                hora_fim=time(20),
            )

    def criar(self, cliente=None, profissional=None, inicio=time(9), fim=time(10), **kw):
        return Agendamento.objects.create(
            cliente=cliente or self.cliente,
            profissional=profissional or self.prof,
            servico="Consulta",
            data=date(2026, 11, 3),
            hora_inicio=inicio,
            hora_fim=fim,
            **kw,
        )

    def test_profissional_str(self):
        self.assertEqual(str(self.prof), "prof1 - Nutricionista")
        self.assertTrue(self.prof.ativo)
        self.assertEqual(self.prof.modalidade, "PRESENCIAL")

    def test_criacao_e_str(self):
        ag = self.criar()
        self.assertEqual(ag.status, "AGENDADO")
        self.assertIsNotNone(ag.criado_em)
        self.assertEqual(str(ag), "cliente1 - prof1 - Nutricionista - 2026-11-03 09:00:00")

    def test_hora_fim_deve_ser_posterior(self):
        with self.assertRaises(ValidationError):
            self.criar(inicio=time(10), fim=time(10))
        with self.assertRaises(ValidationError):
            self.criar(inicio=time(10), fim=time(9))

    def test_conflito_do_profissional(self):
        self.criar()
        with self.assertRaises(ValidationError):
            self.criar(cliente=self.cliente2, inicio=time(9, 30), fim=time(10, 30))

    def test_conflito_do_cliente(self):
        self.criar()
        with self.assertRaises(ValidationError):
            self.criar(profissional=self.prof2, inicio=time(9, 30), fim=time(10, 30))

    def test_horarios_adjacentes_nao_conflitam(self):
        self.criar()
        self.criar(inicio=time(10), fim=time(11))

    def test_cancelado_nao_bloqueia(self):
        self.criar(status="CANCELADO")
        self.criar()

    def test_editar_proprio_agendamento(self):
        ag = self.criar()
        ag.observacao = "ok"
        ag.save()

    def test_horario_fora_da_faixa_recusado(self):
        with self.assertRaises(ValidationError):
            self.criar(inicio=time(7), fim=time(8))

    def test_horario_dentro_da_faixa_aceito(self):
        ag = self.criar(inicio=time(8), fim=time(9))
        self.assertEqual(ag.status, "AGENDADO")

    def test_sem_disponibilidade_cadastrada_recusa(self):
        Disponibilidade.objects.filter(profissional=self.prof).delete()
        with self.assertRaises(ValidationError):
            self.criar()

    def test_bloqueio_esconde_horario(self):
        Bloqueio.objects.create(
            profissional=self.prof,
            data=date(2026, 11, 3),
            hora_inicio=time(9),
            hora_fim=time(10),
            motivo="Consulta médica",
        )
        with self.assertRaises(ValidationError):
            self.criar(inicio=time(9, 30), fim=time(10, 30))


class DisponibilidadeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.prof = Profissional.objects.create(
            usuario=User.objects.create_user("prof1", password="x"),
            especialidade="NUTRICIONISTA",
        )

    def test_hora_fim_deve_ser_posterior(self):
        with self.assertRaises(ValidationError):
            Disponibilidade.objects.create(
                profissional=self.prof,
                dia_semana=0,
                hora_inicio=time(10),
                hora_fim=time(9),
            )

    def test_str(self):
        faixa = Disponibilidade.objects.create(
            profissional=self.prof, dia_semana=0, hora_inicio=time(8), hora_fim=time(18)
        )
        self.assertIn("Segunda-feira", str(faixa))


class BloqueioTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.cliente = User.objects.create_user("cliente1", password="x")
        self.prof = Profissional.objects.create(
            usuario=User.objects.create_user("prof1", password="x"),
            especialidade="NUTRICIONISTA",
        )
        Disponibilidade.objects.create(
            profissional=self.prof, dia_semana=1, hora_inicio=time(8), hora_fim=time(18)
        )

    def test_hora_fim_deve_ser_posterior(self):
        with self.assertRaises(ValidationError):
            Bloqueio.objects.create(
                profissional=self.prof,
                data=date(2026, 11, 3),
                hora_inicio=time(10),
                hora_fim=time(9),
            )

    def test_agendamentos_afetados_lista_atendimentos_confirmados(self):
        agendamento = Agendamento.objects.create(
            cliente=self.cliente,
            profissional=self.prof,
            servico="Consulta",
            data=date(2026, 11, 3),
            hora_inicio=time(9),
            hora_fim=time(10),
        )
        bloqueio = Bloqueio(
            profissional=self.prof,
            data=date(2026, 11, 3),
            hora_inicio=time(8),
            hora_fim=time(12),
            motivo="Férias",
        )
        self.assertIn(agendamento, bloqueio.agendamentos_afetados())

    def test_agendamentos_afetados_ignora_outro_dia(self):
        quarta = date(2026, 11, 4)
        Disponibilidade.objects.create(
            profissional=self.prof,
            dia_semana=quarta.weekday(),
            hora_inicio=time(8),
            hora_fim=time(18),
        )
        Agendamento.objects.create(
            cliente=self.cliente,
            profissional=self.prof,
            servico="Consulta",
            data=quarta,
            hora_inicio=time(9),
            hora_fim=time(10),
        )
        bloqueio = Bloqueio(
            profissional=self.prof,
            data=date(2026, 11, 3),
            hora_inicio=time(8),
            hora_fim=time(12),
            motivo="Férias",
        )
        self.assertEqual(bloqueio.agendamentos_afetados().count(), 0)


class HorariosLivresTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.cliente = User.objects.create_user("cliente1", password="x")
        self.prof = Profissional.objects.create(
            usuario=User.objects.create_user("prof1", password="x"),
            especialidade="NUTRICIONISTA",
        )
        self.terca = date(2026, 11, 3)
        self.assertEqual(self.terca.weekday(), 1)
        Disponibilidade.objects.create(
            profissional=self.prof, dia_semana=1, hora_inicio=time(8), hora_fim=time(10)
        )

    def test_sem_ocupacao_devolve_todas_as_faixas(self):
        livres = horarios_livres(self.prof, self.terca, duracao_minutos=30)
        self.assertEqual(
            livres, [time(8), time(8, 30), time(9), time(9, 30)]
        )

    def test_bloqueio_esconde_horario(self):
        Bloqueio.objects.create(
            profissional=self.prof,
            data=self.terca,
            hora_inicio=time(9),
            hora_fim=time(9, 30),
            motivo="Almoço",
        )
        livres = horarios_livres(self.prof, self.terca, duracao_minutos=30)
        self.assertNotIn(time(9), livres)

    def test_bloqueio_nao_atrapalha_outro_dia(self):
        quarta = date(2026, 11, 4)
        Disponibilidade.objects.create(
            profissional=self.prof, dia_semana=2, hora_inicio=time(8), hora_fim=time(10)
        )
        Bloqueio.objects.create(
            profissional=self.prof,
            data=self.terca,
            hora_inicio=time(8),
            hora_fim=time(10),
            motivo="Férias",
        )
        livres = horarios_livres(self.prof, quarta, duracao_minutos=30)
        self.assertEqual(livres, [time(8), time(8, 30), time(9), time(9, 30)])

    def test_atendimento_confirmado_esconde_horario(self):
        Agendamento.objects.create(
            cliente=self.cliente,
            profissional=self.prof,
            servico="Consulta",
            data=self.terca,
            hora_inicio=time(8),
            hora_fim=time(9),
        )
        livres = horarios_livres(self.prof, self.terca, duracao_minutos=30)
        self.assertNotIn(time(8), livres)
        self.assertNotIn(time(8, 30), livres)
