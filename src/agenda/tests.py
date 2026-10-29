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
    Recorrencia,
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


class FixtureExemploTests(TestCase):
    """Garante que os dados de demonstração continuam carregando (#25)."""

    fixtures = ["exemplo.json"]

    def test_carrega_os_dados(self):
        self.assertEqual(Sala.objects.count(), 3)
        self.assertEqual(Recurso.objects.count(), 3)
        self.assertEqual(Profissional.objects.count(), 3)
        self.assertEqual(Servico.objects.count(), 4)
        self.assertEqual(Disponibilidade.objects.count(), 7)
        self.assertEqual(Bloqueio.objects.count(), 1)
        self.assertEqual(Agendamento.objects.count(), 5)

    def test_tem_agendamento_com_sala_e_recurso(self):
        agendamento = Agendamento.objects.get(pk=3)
        self.assertEqual(agendamento.sala.nome, "Sala de Pilates")
        self.assertEqual(agendamento.recurso.nome, "Reformer")


class RecorrenciaModelTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.cliente = User.objects.create_user("cliente_rec", password="x")
        self.prof = Profissional.objects.create(
            usuario=User.objects.create_user("prof_rec", password="x"),
            especialidade="PERSONAL",
        )
        self.servico = Servico.objects.create(
            profissional=self.prof, nome="Personal 60min", duracao_minutos=60
        )
        self.sala = Sala.objects.create(nome="Estúdio A")
        self.recurso = Recurso.objects.create(nome="Kettlebell")
        for dia in range(7):
            Disponibilidade.objects.create(
                profissional=self.prof,
                dia_semana=dia,
                hora_inicio=time(8),
                hora_fim=time(18),
            )

    def test_str_e_atributos_basicos(self):
        rec = Recorrencia.objects.create(
            cliente=self.cliente,
            profissional=self.prof,
            servico=self.servico,
            dias_semana=[0, 2],
            data_inicio=date(2026, 11, 2),
            data_fim=date(2026, 11, 16),
            hora_inicio=time(9),
        )
        self.assertEqual(rec.padrao, "SEMANAL")
        self.assertEqual(rec.data_termino, date(2026, 11, 16))
        self.assertIn("Segunda-feira, Quarta-feira", str(rec))
        self.assertIn("09:00:00", str(rec))

    def test_setter_data_termino(self):
        rec = Recorrencia(
            cliente=self.cliente,
            profissional=self.prof,
            servico=self.servico,
            dias_semana=[0],
            data_inicio=date(2026, 11, 2),
            hora_inicio=time(9),
        )
        rec.data_termino = date(2026, 11, 30)
        self.assertEqual(rec.data_fim, date(2026, 11, 30))

    def test_validacao_dias_semana_vazio(self):
        rec = Recorrencia(
            cliente=self.cliente,
            profissional=self.prof,
            servico=self.servico,
            dias_semana=[],
            data_inicio=date(2026, 11, 2),
            data_fim=date(2026, 11, 16),
            hora_inicio=time(9),
        )
        with self.assertRaises(ValidationError):
            rec.clean()

    def test_validacao_data_fim_anterior_a_data_inicio(self):
        rec = Recorrencia(
            cliente=self.cliente,
            profissional=self.prof,
            servico=self.servico,
            dias_semana=[0],
            data_inicio=date(2026, 11, 16),
            data_fim=date(2026, 11, 2),
            hora_inicio=time(9),
        )
        with self.assertRaises(ValidationError):
            rec.clean()

    def test_validacao_periodo_sem_dias_correspondentes(self):
        rec = Recorrencia(
            cliente=self.cliente,
            profissional=self.prof,
            servico=self.servico,
            dias_semana=[0],
            data_inicio=date(2026, 11, 7),
            data_fim=date(2026, 11, 8),
            hora_inicio=time(9),
        )
        with self.assertRaises(ValidationError):
            rec.clean()

    def test_calculo_automatico_hora_fim(self):
        rec = Recorrencia(
            cliente=self.cliente,
            profissional=self.prof,
            servico=self.servico,
            dias_semana=[0],
            data_inicio=date(2026, 11, 2),
            data_fim=date(2026, 11, 9),
            hora_inicio=time(9),
        )
        rec.clean()
        self.assertEqual(rec.hora_fim, time(10))

    def test_validacao_hora_fim_menor_ou_igual_hora_inicio(self):
        rec = Recorrencia(
            cliente=self.cliente,
            profissional=self.prof,
            servico=self.servico,
            dias_semana=[0],
            data_inicio=date(2026, 11, 2),
            data_fim=date(2026, 11, 9),
            hora_inicio=time(9),
            hora_fim=time(8),
        )
        with self.assertRaises(ValidationError):
            rec.clean()

    def test_normalizacao_dias_semana(self):
        rec = Recorrencia(
            cliente=self.cliente,
            profissional=self.prof,
            servico=self.servico,
            dias_semana="2, 0, 2",
            data_inicio=date(2026, 11, 2),
            data_fim=date(2026, 11, 9),
            hora_inicio=time(9),
        )
        rec.clean()
        self.assertEqual(rec.dias_semana, [0, 2])


class RecorrenciaGeracaoOcorrenciasTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.cliente = User.objects.create_user("cliente_ger", password="x")
        self.cliente2 = User.objects.create_user("cliente_ger2", password="x")
        self.prof = Profissional.objects.create(
            usuario=User.objects.create_user("prof_ger", password="x"),
            especialidade="PERSONAL",
        )
        for dia in range(5):
            Disponibilidade.objects.create(
                profissional=self.prof,
                dia_semana=dia,
                hora_inicio=time(8),
                hora_fim=time(18),
            )
        self.servico = Servico.objects.create(
            profissional=self.prof, nome="Treino", duracao_minutos=60
        )
        self.sala = Sala.objects.create(nome="Sala Recorrente")
        self.maca = Recurso.objects.create(nome="Maca Recorrente", exclusivo=True)

    def test_geracao_automatica_no_save(self):
        rec = Recorrencia.objects.create(
            cliente=self.cliente,
            profissional=self.prof,
            servico=self.servico,
            dias_semana=[0, 2],
            data_inicio=date(2026, 11, 2),
            data_fim=date(2026, 11, 16),
            hora_inicio=time(9),
            sala=self.sala,
            recurso=self.maca,
        )
        self.assertEqual(rec.agendamentos.count(), 5)
        for ag in rec.agendamentos.all():
            self.assertEqual(ag.recorrencia, rec)
            self.assertEqual(ag.hora_inicio, time(9))
            self.assertEqual(ag.hora_fim, time(10))
            self.assertEqual(ag.cliente, self.cliente)
            self.assertEqual(ag.profissional, self.prof)
            self.assertEqual(ag.sala, self.sala)
            self.assertEqual(ag.recurso, self.maca)
            self.assertTrue(ag.eh_recorrente)

    def test_gerar_ocorrencias_sem_salvar(self):
        rec = Recorrencia(
            cliente=self.cliente,
            profissional=self.prof,
            servico=self.servico,
            dias_semana=[0],
            data_inicio=date(2026, 11, 2),
            data_fim=date(2026, 11, 16),
            hora_inicio=time(9),
        )
        ocorrencias = rec.gerar_ocorrencias(salvar=False)
        self.assertEqual(len(ocorrencias), 3)
        self.assertIsNone(rec.pk)
        self.assertEqual(Agendamento.objects.count(), 0)

    def test_rn11_e_rn12_conflito_individual_descartado_sem_sobrescrever(self):
        ag_previo = Agendamento.objects.create(
            cliente=self.cliente2,
            profissional=self.prof,
            servico=self.servico,
            data=date(2026, 11, 9),
            hora_inicio=time(9),
            hora_fim=time(10),
        )

        rec = Recorrencia.objects.create(
            cliente=self.cliente,
            profissional=self.prof,
            servico=self.servico,
            dias_semana=[0],
            data_inicio=date(2026, 11, 2),
            data_fim=date(2026, 11, 16),
            hora_inicio=time(9),
        )

        datas_criadas = list(rec.agendamentos.values_list("data", flat=True).order_by("data"))
        self.assertEqual(datas_criadas, [date(2026, 11, 2), date(2026, 11, 16)])

        ag_previo.refresh_from_db()
        self.assertEqual(ag_previo.cliente, self.cliente2)
        self.assertIsNone(ag_previo.recorrencia)

    def test_conflito_com_bloqueio_profissional_descartado(self):
        Bloqueio.objects.create(
            profissional=self.prof,
            data=date(2026, 11, 4),
            hora_inicio=time(9),
            hora_fim=time(11),
            motivo="Reunião",
        )

        rec = Recorrencia.objects.create(
            cliente=self.cliente,
            profissional=self.prof,
            servico=self.servico,
            dias_semana=[0, 2],
            data_inicio=date(2026, 11, 2),
            data_fim=date(2026, 11, 9),
            hora_inicio=time(9),
        )
        datas = list(rec.agendamentos.values_list("data", flat=True).order_by("data"))
        self.assertNotIn(date(2026, 11, 4), datas)
        self.assertIn(date(2026, 11, 2), datas)
        self.assertIn(date(2026, 11, 9), datas)

    def test_conflito_com_agendamento_existente_do_cliente_descartado(self):
        prof_outro = Profissional.objects.create(
            usuario=get_user_model().objects.create_user("prof_outro", password="x"),
            especialidade="NUTRICIONISTA",
        )
        Disponibilidade.objects.create(
            profissional=prof_outro,
            dia_semana=0,
            hora_inicio=time(8),
            hora_fim=time(18),
        )
        Agendamento.objects.create(
            cliente=self.cliente,
            profissional=prof_outro,
            servico=Servico.objects.create(profissional=prof_outro, nome="Nutri", duracao_minutos=60),
            data=date(2026, 11, 9),
            hora_inicio=time(9),
            hora_fim=time(10),
        )

        rec = Recorrencia.objects.create(
            cliente=self.cliente,
            profissional=self.prof,
            servico=self.servico,
            dias_semana=[0],
            data_inicio=date(2026, 11, 2),
            data_fim=date(2026, 11, 16),
            hora_inicio=time(9),
        )
        datas = list(rec.agendamentos.values_list("data", flat=True).order_by("data"))
        self.assertEqual(datas, [date(2026, 11, 2), date(2026, 11, 16)])

    def test_conflito_de_sala_descartado(self):
        prof_outro = Profissional.objects.create(
            usuario=get_user_model().objects.create_user("prof_sala", password="x"),
            especialidade="NUTRICIONISTA",
        )
        Disponibilidade.objects.create(
            profissional=prof_outro, dia_semana=0, hora_inicio=time(8), hora_fim=time(18)
        )
        Agendamento.objects.create(
            cliente=self.cliente2,
            profissional=prof_outro,
            servico=Servico.objects.create(profissional=prof_outro, nome="Nutri", duracao_minutos=60),
            sala=self.sala,
            data=date(2026, 11, 9),
            hora_inicio=time(9),
            hora_fim=time(10),
        )

        rec = Recorrencia.objects.create(
            cliente=self.cliente,
            profissional=self.prof,
            servico=self.servico,
            sala=self.sala,
            dias_semana=[0],
            data_inicio=date(2026, 11, 2),
            data_fim=date(2026, 11, 16),
            hora_inicio=time(9),
        )
        datas = list(rec.agendamentos.values_list("data", flat=True).order_by("data"))
        self.assertEqual(datas, [date(2026, 11, 2), date(2026, 11, 16)])

    def test_todas_ocorrencias_em_conflito_lanca_validacao(self):
        Bloqueio.objects.create(
            profissional=self.prof,
            data=date(2026, 11, 2),
            hora_inicio=time(8),
            hora_fim=time(12),
        )
        with self.assertRaises(ValidationError):
            Recorrencia.objects.create(
                cliente=self.cliente,
                profissional=self.prof,
                servico=self.servico,
                dias_semana=[0],
                data_inicio=date(2026, 11, 2),
                data_fim=date(2026, 11, 2),
                hora_inicio=time(9),
            )

    def test_cancelar_recorrencia(self):
        rec = Recorrencia.objects.create(
            cliente=self.cliente,
            profissional=self.prof,
            servico=self.servico,
            dias_semana=[0],
            data_inicio=date(2026, 11, 2),
            data_fim=date(2026, 11, 9),
            hora_inicio=time(9),
        )
        self.assertEqual(rec.agendamentos.filter(status="AGENDADO").count(), 2)
        rec.cancelar()
        self.assertEqual(rec.agendamentos.filter(status="CANCELADO").count(), 2)


class NovoAgendamentoRecorrenciaViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.cliente = User.objects.create_user("cliente_view", password="123")
        self.prof = Profissional.objects.create(
            usuario=User.objects.create_user("prof_view", password="x"),
            especialidade="PERSONAL",
        )
        for dia in range(5):
            Disponibilidade.objects.create(
                profissional=self.prof,
                dia_semana=dia,
                hora_inicio=time(8),
                hora_fim=time(18),
            )
        self.servico = Servico.objects.create(
            profissional=self.prof, nome="Treino", duracao_minutos=60
        )
        self.url = reverse("agenda:novo_agendamento")

    def test_get_tela_contem_campos_de_recorrencia(self):
        self.client.login(username="cliente_view", password="123")
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "repetir_semanal")
        self.assertContains(resposta, "dias_semana")
        self.assertContains(resposta, "data_fim")

    def test_post_cria_recorrencia_com_sucesso(self):
        self.client.login(username="cliente_view", password="123")
        resposta = self.client.post(self.url, {
            "servico": self.servico.pk,
            "profissional": self.prof.pk,
            "data": "2026-11-02",
            "hora_inicio": "10:00",
            "repetir_semanal": "on",
            "dias_semana": ["0", "2"],
            "data_fim": "2026-11-09",
        })
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(Recorrencia.objects.count(), 1)
        rec = Recorrencia.objects.first()
        self.assertEqual(rec.agendamentos.count(), 3)

    def test_post_recorrencia_sem_marcar_dias_assume_dia_da_data(self):
        self.client.login(username="cliente_view", password="123")
        resposta = self.client.post(self.url, {
            "servico": self.servico.pk,
            "profissional": self.prof.pk,
            "data": "2026-11-03",
            "hora_inicio": "10:00",
            "repetir_semanal": "on",
            "data_fim": "2026-11-17",
        })
        self.assertEqual(resposta.status_code, 302)
        rec = Recorrencia.objects.first()
        self.assertEqual(rec.dias_semana, [1])
        self.assertEqual(rec.agendamentos.count(), 3)

    def test_post_recorrencia_com_conflito_parcial_exibe_aviso(self):
        user_outro = get_user_model().objects.create_user("outro", password="x")
        Agendamento.objects.create(
            cliente=user_outro,
            profissional=self.prof,
            servico=self.servico,
            data=date(2026, 11, 9),
            hora_inicio=time(10),
            hora_fim=time(11),
        )
        self.client.login(username="cliente_view", password="123")
        resposta = self.client.post(self.url, {
            "servico": self.servico.pk,
            "profissional": self.prof.pk,
            "data": "2026-11-02",
            "hora_inicio": "10:00",
            "repetir_semanal": "on",
            "dias_semana": ["0"],
            "data_fim": "2026-11-16",
        }, follow=True)
        self.assertEqual(resposta.status_code, 200)
        rec = Recorrencia.objects.first()
        self.assertEqual(rec.agendamentos.count(), 2)
        self.assertContains(resposta, "descartadas")

    def test_post_recorrencia_com_conflito_total_exibe_erro(self):
        Bloqueio.objects.create(
            profissional=self.prof,
            data=date(2026, 11, 2),
            hora_inicio=time(8),
            hora_fim=time(18),
        )
        self.client.login(username="cliente_view", password="123")
        resposta = self.client.post(self.url, {
            "servico": self.servico.pk,
            "profissional": self.prof.pk,
            "data": "2026-11-02",
            "hora_inicio": "10:00",
            "repetir_semanal": "on",
            "dias_semana": ["0"],
            "data_fim": "2026-11-02",
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Recorrencia.objects.count(), 0)
        self.assertContains(resposta, "apresentaram conflito")


class PreviaRecorrenciaViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.cliente = User.objects.create_user("cliente_prev", password="123")
        self.cliente2 = User.objects.create_user("cliente_prev2", password="123")
        self.prof = Profissional.objects.create(
            usuario=User.objects.create_user("prof_prev", password="x"),
            especialidade="PERSONAL",
        )
        for dia in range(5):
            Disponibilidade.objects.create(
                profissional=self.prof,
                dia_semana=dia,
                hora_inicio=time(8),
                hora_fim=time(18),
            )
        self.servico = Servico.objects.create(
            profissional=self.prof, nome="Treino", duracao_minutos=60
        )
        self.url = reverse("agenda:previa_recorrencia")

    def test_exige_login(self):
        resposta = self.client.post(self.url, {})
        self.assertEqual(resposta.status_code, 302)

    def test_metodo_get_recusado(self):
        self.client.login(username="cliente_prev", password="123")
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 405)

    def test_previa_dados_invalidos_retorna_400(self):
        self.client.login(username="cliente_prev", password="123")
        resposta = self.client.post(self.url, {
            "servico": self.servico.pk,
            # Faltam profissional, data, etc.
        })
        self.assertEqual(resposta.status_code, 400)
        dados = resposta.json()
        self.assertFalse(dados["valido"])

    def test_previa_data_fim_anterior_retorna_400(self):
        self.client.login(username="cliente_prev", password="123")
        resposta = self.client.post(self.url, {
            "servico": self.servico.pk,
            "profissional": self.prof.pk,
            "data": "2026-11-16",
            "data_fim": "2026-11-02",
            "hora_inicio": "10:00",
        })
        self.assertEqual(resposta.status_code, 400)
        dados = resposta.json()
        self.assertFalse(dados["valido"])
        self.assertIn("A data final deve ser posterior", dados["erro"])

    def test_previa_calcula_datas_e_total_sessoes(self):
        self.client.login(username="cliente_prev", password="123")
        resposta = self.client.post(self.url, {
            "servico": self.servico.pk,
            "profissional": self.prof.pk,
            "data": "2026-11-02",  # Seg
            "data_fim": "2026-11-16",  # Seg (3 segundas: 02, 09, 16)
            "hora_inicio": "10:00",
            "dias_semana": ["0"],
        })
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.json()
        self.assertTrue(dados["valido"])
        self.assertEqual(dados["total"], 3)
        self.assertEqual(dados["total_validas"], 3)
        self.assertEqual(dados["total_conflitos"], 0)
        self.assertEqual(len(dados["sessoes"]), 3)
        for s in dados["sessoes"]:
            self.assertFalse(s["conflito"])
            self.assertEqual(s["status"], "Disponível")

    def test_previa_identifica_conflito_com_motivo(self):
        # Cria conflito no dia 2026-11-09 às 10:00
        Agendamento.objects.create(
            cliente=self.cliente2,
            profissional=self.prof,
            servico=self.servico,
            data=date(2026, 11, 9),
            hora_inicio=time(10),
            hora_fim=time(11),
        )
        self.client.login(username="cliente_prev", password="123")
        resposta = self.client.post(self.url, {
            "servico": self.servico.pk,
            "profissional": self.prof.pk,
            "data": "2026-11-02",
            "data_fim": "2026-11-16",
            "hora_inicio": "10:00",
            "dias_semana": ["0"],
        })
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.json()
        self.assertTrue(dados["valido"])
        self.assertEqual(dados["total"], 3)
        self.assertEqual(dados["total_validas"], 2)
        self.assertEqual(dados["total_conflitos"], 1)

        # Encontra a sessão do dia 09
        s_09 = [s for s in dados["sessoes"] if s["data"] == "2026-11-09"][0]
        self.assertTrue(s_09["conflito"])
        self.assertEqual(s_09["status"], "Conflito")
        self.assertIn("já possui um agendamento", s_09["motivo"])

    def test_template_contem_modal_recorrencia_e_elementos(self):
        self.client.login(username="cliente_prev", password="123")
        resposta = self.client.get(reverse("agenda:novo_agendamento"))
        self.assertContains(resposta, 'id="modal-recorrencia"')
        self.assertContains(resposta, 'id="metrica-total"')
        self.assertContains(resposta, 'id="metrica-validas"')
        self.assertContains(resposta, 'id="metrica-conflitos"')
        self.assertContains(resposta, 'id="tabela-sessoes-recorrencia"')
        self.assertContains(resposta, 'id="botao-confirmar-recorrencia"')
        self.assertContains(resposta, 'id="botao-ver-previa"')
