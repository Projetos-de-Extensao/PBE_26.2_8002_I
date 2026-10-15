from datetime import date, time

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Agendamento, Profissional, Recurso, Sala


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
