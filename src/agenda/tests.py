from datetime import date, time

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .models import (
    Agendamento,
    Bloqueio,
    Disponibilidade,
    Profissional,
    Recurso,
    Sala,
    Servico,
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
        self.servico = Servico.objects.create(
            profissional=self.prof, nome="Consulta", duracao_minutos=60
        )
        self.sala = Sala.objects.create(nome="Sala 1")
        self.sala2 = Sala.objects.create(nome="Sala 2")
        self.maca = Recurso.objects.create(nome="Maca")
        self.colchonete = Recurso.objects.create(nome="Colchonete", exclusivo=False)

    def criar(self, cliente=None, profissional=None, inicio=time(9), fim=time(10), **kw):
        return Agendamento.objects.create(
            cliente=cliente or self.cliente,
            profissional=profissional or self.prof,
            servico=kw.pop("servico", self.servico),
            data=date(2026, 11, 3),
            hora_inicio=inicio,
            hora_fim=fim,
            **kw,
        )

    def test_profissional_str(self):
        self.assertEqual(str(self.prof), "prof1 - Nutricionista")
        self.assertTrue(self.prof.ativo)
        self.assertEqual(self.prof.modalidade, "PRESENCIAL")

    def test_servico_str_e_duracao(self):
        self.assertEqual(str(self.servico), "Consulta (60 min)")
        self.assertTrue(self.servico.ativo)

    def test_servico_duracao_minima(self):
        with self.assertRaises(ValidationError):
            Servico(
                profissional=self.prof, nome="Rápido", duracao_minutos=0
            ).full_clean()

    def test_hora_fim_calculada_pelo_servico(self):
        ag = Agendamento.objects.create(
            cliente=self.cliente,
            profissional=self.prof,
            servico=self.servico,
            data=date(2026, 11, 3),
            hora_inicio=time(16),
        )
        self.assertEqual(ag.hora_fim, time(17))

    def test_hora_fim_informada_prevalece(self):
        ag = self.criar(inicio=time(16), fim=time(16, 30))
        self.assertEqual(ag.hora_fim, time(16, 30))

    def test_sem_servico_e_sem_hora_fim_da_erro(self):
        with self.assertRaises(ValidationError):
            Agendamento.objects.create(
                cliente=self.cliente,
                profissional=self.prof,
                data=date(2026, 11, 3),
                hora_inicio=time(16),
            )

    def test_conflito_de_sala(self):
        self.criar(sala=self.sala)
        with self.assertRaises(ValidationError):
            self.criar(
                cliente=self.cliente2,
                profissional=self.prof2,
                inicio=time(9, 30),
                fim=time(10, 30),
                sala=self.sala,
            )

    def test_salas_diferentes_nao_conflitam(self):
        self.criar(sala=self.sala)
        self.criar(
            cliente=self.cliente2,
            profissional=self.prof2,
            inicio=time(9, 30),
            fim=time(10, 30),
            sala=self.sala2,
        )

    def test_conflito_de_recurso_exclusivo(self):
        self.criar(recurso=self.maca)
        with self.assertRaises(ValidationError):
            self.criar(
                cliente=self.cliente2,
                profissional=self.prof2,
                inicio=time(9, 30),
                fim=time(10, 30),
                recurso=self.maca,
            )

    def test_recurso_compartilhado_nao_conflita(self):
        self.criar(recurso=self.colchonete)
        self.criar(
            cliente=self.cliente2,
            profissional=self.prof2,
            inicio=time(9, 30),
            fim=time(10, 30),
            recurso=self.colchonete,
        )

    def test_sala_livre_apos_cancelamento(self):
        self.criar(sala=self.sala, status="CANCELADO")
        self.criar(sala=self.sala)

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
        self.servico = Servico.objects.create(
            profissional=self.prof, nome="Consulta", duracao_minutos=60
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
            servico=self.servico,
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
            servico=self.servico,
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
        self.servico = Servico.objects.create(
            profissional=self.prof, nome="Consulta", duracao_minutos=60
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
            servico=self.servico,
            data=self.terca,
            hora_inicio=time(8),
            hora_fim=time(9),
        )
        livres = horarios_livres(self.prof, self.terca, duracao_minutos=30)
        self.assertNotIn(time(8), livres)
        self.assertNotIn(time(8, 30), livres)


class NovoAgendamentoViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.cliente = User.objects.create_user("cliente1", password="segredo")
        self.prof = Profissional.objects.create(
            usuario=User.objects.create_user("prof1", password="x"),
            especialidade="PERSONAL",
        )
        self.data = date(2026, 11, 10)
        Disponibilidade.objects.create(
            profissional=self.prof,
            dia_semana=self.data.weekday(),
            hora_inicio=time(8),
            hora_fim=time(20),
        )
        self.servico = Servico.objects.create(
            profissional=self.prof, nome="Treino", duracao_minutos=60
        )
        self.url = reverse("agenda:novo_agendamento")

    def test_exige_login(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_abre_a_tela(self):
        self.client.login(username="cliente1", password="segredo")
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Novo agendamento")

    def test_cria_agendamento(self):
        self.client.login(username="cliente1", password="segredo")
        resposta = self.client.post(self.url, {
            "servico": self.servico.pk,
            "profissional": self.prof.pk,
            "data": self.data.isoformat(),
            "hora_inicio": "16:00",
        })
        self.assertEqual(resposta.status_code, 302)
        ag = Agendamento.objects.get()
        self.assertEqual(ag.cliente, self.cliente)
        self.assertEqual(ag.hora_fim, time(17))

    def test_tela_tem_modal_de_confirmacao(self):
        self.client.login(username="cliente1", password="segredo")
        resposta = self.client.get(self.url)
        self.assertContains(resposta, 'id="modal-confirmacao"')
        self.assertContains(resposta, "Confirmar agendamento")

    def test_mostra_modal_de_conflito_com_sugestoes(self):
        self.client.login(username="cliente1", password="segredo")
        dados = {
            "servico": self.servico.pk,
            "profissional": self.prof.pk,
            "data": self.data.isoformat(),
            "hora_inicio": "16:00",
        }
        self.client.post(self.url, dados)
        resposta = self.client.post(self.url, dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "já possui um agendamento")
        self.assertContains(resposta, 'id="modal-conflito" data-abrir="1"')
        self.assertEqual(Agendamento.objects.count(), 1)
        sugestoes = resposta.context["sugestoes"]
        self.assertTrue(sugestoes)
        self.assertNotIn(time(16), sugestoes)

    def test_sem_conflito_o_modal_fica_fechado(self):
        self.client.login(username="cliente1", password="segredo")
        resposta = self.client.get(self.url)
        self.assertNotContains(resposta, 'data-abrir="1"')
