from datetime import datetime, time, timedelta
import re

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from agendamento.models import (
    Agendamento,
    Bloqueio,
    Cliente,
    Disponibilidade,
    Papel,
    Perfil,
    Profissional,
    Recepcionista,
    Sala,
    Servico,
    Usuario,
)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class LoginViewTests(TestCase):
    def setUp(self):
        papel = Papel.objects.create(nome="Cliente")
        self.usuario = Usuario.objects.create_user(
            email="cliente@exemplo.com",
            password="senha-segura-123",
            nome="Cliente",
            papel=papel,
        )

    def test_exibe_tela_de_login(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'type="email"')
        self.assertContains(response, "Esqueci minha senha")

    def test_exibe_erro_para_credenciais_invalidas(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.usuario.email, "password": "incorreta"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "E-mail ou senha inválidos.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_autentica_com_credenciais_validas(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": self.usuario.email,
                "password": "senha-segura-123",
            },
        )

        self.assertRedirects(response, reverse("login"))
        response = self.client.get(reverse("login"))
        self.assertContains(response, "Acesso realizado")
        self.assertContains(response, self.usuario.email)

    def test_permite_encerrar_sessao(self):
        self.client.force_login(self.usuario)

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CadastroViewTests(TestCase):
    def test_tela_de_cadastro_oferece_papeis_publicos(self):
        response = self.client.get(reverse("cadastro"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Criar conta")
        self.assertContains(response, "Nome completo")
        self.assertContains(response, 'value="cliente"')
        self.assertContains(response, 'value="profissional"')
        self.assertContains(response, 'value="recepcionista"')
        self.assertNotContains(response, 'value="administrador"')

    def test_cadastra_cliente_com_senha_valida(self):
        response = self.client.post(
            reverse("cadastro"),
            {
                "nome": "Nova Cliente",
                "email": "NOVA@EXEMPLO.COM",
                "papel": Perfil.Papel.CLIENTE,
                "senha": "Nuvem#Roxa39!Chuva",
                "confirmar_senha": "Nuvem#Roxa39!Chuva",
            },
            follow=True,
        )

        usuario = Usuario.objects.get(email="nova@exemplo.com")
        self.assertEqual(usuario.nome, "Nova Cliente")
        self.assertEqual(usuario.perfil.papel, Perfil.Papel.CLIENTE)
        self.assertTrue(Cliente.objects.filter(pk=usuario.pk).exists())
        self.assertTrue(usuario.check_password("Nuvem#Roxa39!Chuva"))
        self.assertContains(response, "Conta criada com sucesso")

    def test_rejeita_email_duplicado(self):
        papel = Papel.objects.create(nome="Cliente")
        Usuario.objects.create_user(
            email="cliente@exemplo.com",
            password="Nuvem#Roxa39!Chuva",
            nome="Cliente",
            papel=papel,
        )

        response = self.client.post(
            reverse("cadastro"),
            {
                "nome": "Outra Cliente",
                "email": "CLIENTE@EXEMPLO.COM",
                "papel": Perfil.Papel.CLIENTE,
                "senha": "Nuvem#Roxa39!Chuva",
                "confirmar_senha": "Nuvem#Roxa39!Chuva",
            },
        )

        self.assertContains(response, "Já existe uma conta com este e-mail.")
        self.assertEqual(Usuario.objects.count(), 1)

    def test_rejeita_senhas_diferentes(self):
        response = self.client.post(
            reverse("cadastro"),
            {
                "nome": "Nova Cliente",
                "email": "nova@exemplo.com",
                "papel": Perfil.Papel.CLIENTE,
                "senha": "Nuvem#Roxa39!Chuva",
                "confirmar_senha": "OutraSenha#123",
            },
        )

        self.assertContains(response, "As senhas não coincidem.")
        self.assertFalse(Usuario.objects.exists())

    def test_cadastra_profissional_com_especialidade(self):
        response = self.client.post(
            reverse("cadastro"),
            {
                "nome": "Nova Profissional",
                "email": "profissional@exemplo.com",
                "papel": Perfil.Papel.PROFISSIONAL,
                "especialidade": "Fisioterapia",
                "senha": "Nuvem#Roxa39!Chuva",
                "confirmar_senha": "Nuvem#Roxa39!Chuva",
            },
            follow=True,
        )

        profissional = Profissional.objects.get(
            email="profissional@exemplo.com"
        )
        self.assertEqual(
            profissional.perfil.papel,
            Perfil.Papel.PROFISSIONAL,
        )
        self.assertEqual(profissional.especialidade, "Fisioterapia")
        self.assertContains(response, "Conta criada com sucesso")

    def test_cadastra_recepcionista(self):
        response = self.client.post(
            reverse("cadastro"),
            {
                "nome": "Nova Recepcionista",
                "email": "recepcionista@exemplo.com",
                "papel": Perfil.Papel.RECEPCIONISTA,
                "senha": "Nuvem#Roxa39!Chuva",
                "confirmar_senha": "Nuvem#Roxa39!Chuva",
            },
            follow=True,
        )

        recepcionista = Recepcionista.objects.get(
            email="recepcionista@exemplo.com"
        )
        self.assertEqual(
            recepcionista.perfil.papel,
            Perfil.Papel.RECEPCIONISTA,
        )
        self.assertContains(response, "Conta criada com sucesso")

    def test_exige_especialidade_para_profissional(self):
        response = self.client.post(
            reverse("cadastro"),
            {
                "nome": "Nova Profissional",
                "email": "profissional@exemplo.com",
                "papel": Perfil.Papel.PROFISSIONAL,
                "senha": "Nuvem#Roxa39!Chuva",
                "confirmar_senha": "Nuvem#Roxa39!Chuva",
            },
        )

        self.assertContains(response, "Informe sua especialidade")
        self.assertFalse(Usuario.objects.exists())


class PerfilModelTests(TestCase):
    def test_todo_tipo_de_usuario_recebe_perfil_com_papel_correto(self):
        usuarios = [
            (
                Usuario,
                "usuario@exemplo.com",
                Perfil.Papel.CLIENTE,
                {},
            ),
            (
                Cliente,
                "cliente@exemplo.com",
                Perfil.Papel.CLIENTE,
                {},
            ),
            (
                Profissional,
                "profissional@exemplo.com",
                Perfil.Papel.PROFISSIONAL,
                {"especialidade": "Fisioterapia"},
            ),
        ]

        for model, email, papel, extra_fields in usuarios:
            with self.subTest(model=model.__name__):
                usuario = model.objects.create_user(
                    email=email,
                    password="Senha#Forte123",
                    nome=model.__name__,
                    **extra_fields,
                )

                self.assertEqual(usuario.perfil.papel, papel)
                self.assertEqual(usuario.perfil.usuario_id, usuario.pk)

        administrador = Usuario.objects.create_superuser(
            email="admin@exemplo.com",
            password="Senha#Forte123",
            nome="Administrador",
        )
        self.assertEqual(
            administrador.perfil.papel,
            Perfil.Papel.ADMINISTRADOR,
        )

        papel_recepcionista = Papel.objects.create(nome="Recepcionista")
        recepcionista = Recepcionista.objects.create_user(
            email="recepcionista@exemplo.com",
            password="Senha#Forte123",
            nome="Recepcionista",
            papel=papel_recepcionista,
        )
        self.assertEqual(
            recepcionista.perfil.papel,
            Perfil.Papel.RECEPCIONISTA,
        )

    def test_papel_do_perfil_e_editavel_no_admin(self):
        administrador = Usuario.objects.create_superuser(
            email="admin@exemplo.com",
            password="Senha#Forte123",
            nome="Administrador",
        )
        cliente = Cliente.objects.create_user(
            email="cliente@exemplo.com",
            password="Senha#Forte123",
            nome="Cliente",
        )
        self.client.force_login(administrador)
        url = reverse("admin:agendamento_perfil_change", args=[cliente.perfil.pk])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Profissional")

        response = self.client.post(
            url,
            {
                "usuario": cliente.pk,
                "papel": Perfil.Papel.PROFISSIONAL,
                "_save": "Salvar",
            },
        )

        self.assertEqual(response.status_code, 302)
        cliente.perfil.refresh_from_db()
        self.assertEqual(cliente.perfil.papel, Perfil.Papel.PROFISSIONAL)

    def test_usuario_criado_pelo_admin_recebe_perfil_cliente(self):
        administrador = Usuario.objects.create_superuser(
            email="admin@exemplo.com",
            password="Senha#Forte123",
            nome="Administrador",
        )
        self.client.force_login(administrador)
        response = self.client.post(
            reverse("admin:agendamento_usuario_add"),
            {
                "email": "novo@exemplo.com",
                "nome": "Novo Cliente",
                "password1": "Senha#Forte123",
                "password2": "Senha#Forte123",
                "_save": "Salvar",
            },
            follow=True,
        )

        usuario = Usuario.objects.get(email="novo@exemplo.com")
        self.assertEqual(usuario.perfil.papel, Perfil.Papel.CLIENTE)
        self.assertContains(response, "Novo Cliente")


class ControleAcessoTests(TestCase):
    def setUp(self):
        self.papel_cliente = Papel.objects.create(nome="Cliente")
        self.cliente = Cliente.objects.create_user(
            email="cliente@exemplo.com",
            password="Senha#Forte123",
            nome="Cliente",
        )
        self.profissional = Profissional.objects.create_user(
            email="profissional@exemplo.com",
            password="Senha#Forte123",
            nome="Profissional",
            especialidade="Fisioterapia",
        )
        self.recepcionista = Recepcionista.objects.create_user(
            email="recepcionista@exemplo.com",
            password="Senha#Forte123",
            nome="Recepcionista",
        )
        self.recepcionista.is_staff = True
        self.recepcionista.save(update_fields=["is_staff"])
        self.administrador = Usuario.objects.create_superuser(
            email="admin@exemplo.com",
            password="Senha#Forte123",
            nome="Administrador",
        )
        self.servico = Servico.objects.create(
            profissional=self.profissional,
            nome="Consulta",
            tipo="Atendimento",
            duracao_minutos=60,
        )
        self.sala = Sala.objects.create(nome="Sala 1", capacidade=2)
        inicio = timezone.now() + timedelta(days=2)
        self.agendamento_cliente = Agendamento.objects.create(
            cliente=self.cliente,
            profissional=self.profissional,
            servico=self.servico,
            data_hora_inicio=inicio,
            data_hora_fim=inicio + timedelta(hours=1),
        )
        outro_cliente = Cliente.objects.create_user(
            email="outro@exemplo.com",
            password="Senha#Forte123",
            nome="Outro cliente",
        )
        self.agendamento_alheio = Agendamento.objects.create(
            cliente=outro_cliente,
            profissional=self.profissional,
            servico=self.servico,
            data_hora_inicio=inicio + timedelta(days=1),
            data_hora_fim=inicio + timedelta(days=1, hours=1),
        )

    def test_usuario_comum_recebe_mensagem_de_acesso_negado_no_admin(self):
        self.client.force_login(self.cliente)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Acesso negado", status_code=403)

    def test_recepcionista_nao_acessa_cadastros_administrativos(self):
        self.client.force_login(self.recepcionista)

        for rota in (
            "admin:index",
            "admin:agendamento_profissional_changelist",
            "admin:agendamento_servico_changelist",
            "admin:agendamento_sala_changelist",
        ):
            with self.subTest(rota=rota):
                response = self.client.get(reverse(rota))
                self.assertEqual(response.status_code, 403)
                self.assertContains(response, "Acesso negado", status_code=403)

    def test_administrador_pode_gerenciar_profissional_servico_e_sala(self):
        self.client.force_login(self.administrador)

        for rota in (
            "admin:agendamento_profissional_changelist",
            "admin:agendamento_servico_changelist",
            "admin:agendamento_sala_changelist",
        ):
            with self.subTest(rota=rota):
                response = self.client.get(reverse(rota))
                self.assertEqual(response.status_code, 200)

    def test_administrador_pode_cadastrar_profissional(self):
        self.client.force_login(self.administrador)
        response = self.client.post(
            reverse("admin:agendamento_profissional_add"),
            {
                "email": "novo-profissional@exemplo.com",
                "nome": "Novo profissional",
                "especialidade": "Nutrição",
                "formacao": "Nutrição clínica",
                "apresentacao": "Atendimento nutricional.",
                "password1": "Senha#Segura984",
                "password2": "Senha#Segura984",
                "_save": "Salvar",
            },
            follow=True,
        )

        profissional = Profissional.objects.get(
            email="novo-profissional@exemplo.com"
        )
        self.assertEqual(
            profissional.perfil.papel,
            Perfil.Papel.PROFISSIONAL,
        )
        self.assertTrue(profissional.check_password("Senha#Segura984"))
        self.assertContains(response, "Novo profissional")

    def test_cliente_visualiza_apenas_sua_agenda(self):
        self.client.force_login(self.cliente)

        response = self.client.get(reverse("minha_agenda"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            timezone.localtime(
                self.agendamento_cliente.data_hora_inicio
            ).strftime("%d/%m/%Y"),
        )
        self.assertNotContains(
            response,
            timezone.localtime(
                self.agendamento_alheio.data_hora_inicio
            ).strftime("%d/%m/%Y"),
        )

    def test_cliente_nao_pode_cancelar_agendamento_de_outra_pessoa(self):
        self.client.force_login(self.cliente)

        response = self.client.post(
            reverse(
                "cancelar_agendamento",
                args=[self.agendamento_alheio.pk],
            )
        )

        self.assertEqual(response.status_code, 404)
        self.agendamento_alheio.refresh_from_db()
        self.assertEqual(
            self.agendamento_alheio.status,
            Agendamento.Status.AGENDADO,
        )

    def test_cliente_pode_cancelar_somente_agendamento_proprio(self):
        self.client.force_login(self.cliente)

        response = self.client.post(
            reverse(
                "cancelar_agendamento",
                args=[self.agendamento_cliente.pk],
            )
        )

        self.assertRedirects(response, reverse("minha_agenda"))
        self.agendamento_cliente.refresh_from_db()
        self.assertEqual(
            self.agendamento_cliente.status,
            Agendamento.Status.CANCELADO,
        )

    def test_profissional_e_recepcionista_nao_acessam_agenda_de_cliente(self):
        for usuario in (self.profissional, self.recepcionista):
            with self.subTest(papel=usuario.perfil.papel):
                self.client.force_login(usuario)
                response = self.client.get(reverse("minha_agenda"))
                self.assertEqual(response.status_code, 403)
                self.assertContains(response, "Acesso negado", status_code=403)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetViewTests(TestCase):
    def setUp(self):
        papel = Papel.objects.create(nome="Cliente")
        self.usuario = Usuario.objects.create_user(
            email="cliente@exemplo.com",
            password="SenhaAntiga#8391",
            nome="Cliente",
            papel=papel,
        )

    def test_envia_link_e_permite_redefinir_senha(self):
        response = self.client.post(
            reverse("password_reset"),
            {"email": self.usuario.email},
        )

        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.usuario.email, mail.outbox[0].body)

        reset_url = re.search(
            r"http://testserver(?P<path>\S+)",
            mail.outbox[0].body,
        )
        self.assertIsNotNone(reset_url)
        response = self.client.get(reset_url["path"], follow=True)
        self.assertContains(response, "Criar nova senha")

        response = self.client.post(
            response.request["PATH_INFO"],
            {
                "new_password1": "Manga&Sol72!Janela",
                "new_password2": "Manga&Sol72!Janela",
            },
            follow=True,
        )

        self.assertContains(response, "Sua senha foi alterada")
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("Manga&Sol72!Janela"))

    def test_nao_revela_se_email_nao_cadastrado(self):
        response = self.client.post(
            reverse("password_reset"),
            {"email": "desconhecido@exemplo.com"},
        )

        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)


class PerfilProfissionalTests(TestCase):
    def setUp(self):
        papel_profissional = Papel.objects.create(nome="Profissional")
        self.profissional = Profissional.objects.create_user(
            email="profissional@exemplo.com",
            password="Senha#Forte123",
            nome="Ana Silva",
            papel=papel_profissional,
            especialidade="Personal Trainer",
            formacao="Educação Física",
            apresentacao="Treinamento funcional e emagrecimento.",
        )
        self.servico = Servico.objects.create(
            profissional=self.profissional,
            nome="Avaliação Física",
            tipo="Avaliação",
            duracao_minutos=60,
        )
        self.horario_inicio = timezone.make_aware(
            datetime.combine(timezone.localdate() + timedelta(days=1), time(8))
        )
        Disponibilidade.objects.create(
            profissional=self.profissional,
            dia_semana=self.horario_inicio.weekday(),
            hora_inicio=time(8),
            hora_fim=time(12),
        )

    def test_lista_de_profissionais_abre_o_perfil(self):
        response = self.client.get(reverse("profissionais"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.profissional.nome)
        self.assertContains(
            response,
            reverse("profissional_detail", args=[self.profissional.pk]),
        )

    def test_perfil_exibe_dados_servicos_e_proximos_horarios(self):
        response = self.client.get(
            reverse("profissional_detail", args=[self.profissional.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Personal Trainer")
        self.assertContains(response, "Treinamento funcional e emagrecimento.")
        self.assertContains(response, "Avaliação Física")
        self.assertContains(response, "60 min")
        self.assertContains(
            response,
            timezone.localtime(self.horario_inicio).strftime(
                "%d/%m/%Y às %H:%M"
            ),
        )
        self.assertContains(
            response,
            reverse("novo_agendamento", args=[self.servico.pk]),
        )

    def test_perfil_omite_horarios_ocupados_e_bloqueados(self):
        papel_cliente = Papel.objects.create(nome="Cliente")
        cliente = Cliente.objects.create_user(
            email="cliente@exemplo.com",
            password="Senha#Forte123",
            nome="João Pereira",
            papel=papel_cliente,
        )
        Agendamento.objects.create(
            cliente=cliente,
            profissional=self.profissional,
            servico=self.servico,
            data_hora_inicio=self.horario_inicio + timedelta(hours=2),
            data_hora_fim=self.horario_inicio + timedelta(hours=3),
        )
        Bloqueio.objects.create(
            profissional=self.profissional,
            inicio=self.horario_inicio,
            fim=self.horario_inicio + timedelta(hours=1),
            motivo="Indisponível",
        )

        response = self.client.get(
            reverse("profissional_detail", args=[self.profissional.pk])
        )

        inicio = timezone.localtime(self.horario_inicio)
        self.assertNotContains(response, inicio.strftime("%d/%m/%Y às %H:%M"))
        self.assertNotContains(
            response,
            (inicio + timedelta(hours=2)).strftime("%d/%m/%Y às %H:%M"),
        )
        self.assertContains(
            response,
            (inicio + timedelta(hours=1)).strftime("%d/%m/%Y às %H:%M"),
        )
        self.assertContains(
            response,
            (inicio + timedelta(hours=3)).strftime("%d/%m/%Y às %H:%M"),
        )


class NovoAgendamentoViewTests(TestCase):
    def setUp(self):
        papel_profissional = Papel.objects.create(nome="Profissional")
        self.profissional = Profissional.objects.create_user(
            email="profissional@exemplo.com",
            password="Senha#Forte123",
            nome="Ana Silva",
            papel=papel_profissional,
            especialidade="Personal Trainer",
        )
        papel_cliente = Papel.objects.create(nome="Cliente")
        self.cliente = Cliente.objects.create_user(
            email="cliente@exemplo.com",
            password="Senha#Forte123",
            nome="João Pereira",
            papel=papel_cliente,
        )
        self.servico = Servico.objects.create(
            profissional=self.profissional,
            nome="Avaliação Física",
            tipo="Avaliação",
            duracao_minutos=60,
        )
        self.horario_inicio = timezone.make_aware(
            datetime.combine(timezone.localdate() + timedelta(days=1), time(8))
        )
        Disponibilidade.objects.create(
            profissional=self.profissional,
            dia_semana=self.horario_inicio.weekday(),
            hora_inicio=time(8),
            hora_fim=time(12),
        )

    def test_exige_login_para_iniciar_agendamento(self):
        response = self.client.get(
            reverse("novo_agendamento", args=[self.servico.pk])
        )

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('novo_agendamento', args=[self.servico.pk])}",
        )

    def test_confirma_agendamento_no_horario_escolhido(self):
        self.client.force_login(self.cliente)
        self.assertEqual(
            self.client.get(reverse("login")).status_code,
            200,
        )
        self.assertContains(self.client.get(reverse("login")), "Acesso realizado")
        horario = self.horario_inicio
        response = self.client.post(
            reverse("novo_agendamento", args=[self.servico.pk]),
            {"horario": horario.isoformat()},
            follow=True,
        )

        self.assertEqual(
            Agendamento.objects.count(),
            1,
            response.redirect_chain,
        )
        agendamento = Agendamento.objects.get()
        self.assertEqual(agendamento.cliente_id, self.cliente.pk)
        self.assertEqual(agendamento.profissional_id, self.profissional.pk)
        self.assertEqual(agendamento.servico_id, self.servico.pk)
        self.assertEqual(agendamento.data_hora_inicio, horario)
        self.assertContains(response, "Agendamento confirmado com sucesso.")

    def test_promove_conta_cliente_existente_ao_agendar(self):
        usuario = Usuario.objects.create_user(
            email="cliente-antigo@exemplo.com",
            password="Senha#Forte123",
            nome="Cliente antigo",
            papel=self.cliente.perfil.papel,
        )
        self.client.force_login(usuario)
        response = self.client.post(
            reverse("novo_agendamento", args=[self.servico.pk]),
            {"horario": self.horario_inicio.isoformat()},
            follow=True,
        )

        self.assertTrue(Cliente.objects.filter(pk=usuario.pk).exists())
        self.assertEqual(Agendamento.objects.get().cliente_id, usuario.pk)
        self.assertContains(response, "Agendamento confirmado com sucesso.")

    def test_nao_permite_confirmar_horario_que_foi_ocupado(self):
        self.client.force_login(self.cliente)
        outro_cliente = Cliente.objects.create_user(
            email="outro@exemplo.com",
            password="Senha#Forte123",
            nome="Outro Cliente",
            papel=self.cliente.perfil.papel,
        )
        horario = timezone.make_aware(datetime(2030, 1, 7, 8))
        Agendamento.objects.create(
            cliente=outro_cliente,
            profissional=self.profissional,
            servico=self.servico,
            data_hora_inicio=horario,
            data_hora_fim=horario + timedelta(hours=1),
        )

        response = self.client.post(
            reverse("novo_agendamento", args=[self.servico.pk]),
            {"horario": horario.isoformat()},
        )

        self.assertEqual(Agendamento.objects.count(), 1)
        self.assertContains(response, "não está mais disponível")
