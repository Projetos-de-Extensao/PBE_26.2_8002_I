from datetime import datetime, time, timedelta
from io import StringIO
import re

from django.core import mail
from django.core.management import call_command, CommandError
from django.conf import settings
from django.test import Client, TestCase, override_settings
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
    Recurso,
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

        self.assertRedirects(response, reverse("inicio"))
        response = self.client.get(reverse("login"))
        self.assertContains(response, "Acesso realizado")
        self.assertContains(response, self.usuario.email)

    @override_settings(ALLOWED_HOSTS=["localhost"])
    def test_login_aceita_origem_https_localhost_com_csrf_ativo(self):
        cliente = Client(enforce_csrf_checks=True)
        response = cliente.get(
            reverse("login"),
            secure=True,
            HTTP_HOST="localhost:8000",
        )
        self.assertEqual(response.status_code, 200)
        csrf_token = cliente.cookies[settings.CSRF_COOKIE_NAME].value
        cliente.cookies["csrftoken"] = "token-de-outro-projeto"

        response = cliente.post(
            reverse("login"),
            {
                "username": self.usuario.email,
                "password": "senha-segura-123",
            },
            secure=True,
            HTTP_HOST="localhost:8000",
            HTTP_ORIGIN="https://localhost:8000",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("inicio"))

    @override_settings(ALLOWED_HOSTS=["localhost"])
    def test_cookie_csrf_de_outro_projeto_nao_interfere_no_login(self):
        cliente = Client(enforce_csrf_checks=True)
        response = cliente.get(
            reverse("login"),
            secure=True,
            HTTP_HOST="localhost:8000",
        )

        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)
        self.assertNotIn("csrftoken", response.cookies)
        token = cliente.cookies[settings.CSRF_COOKIE_NAME].value
        cliente.cookies["csrftoken"] = "cookie-de-outra-aplicacao"

        response = cliente.post(
            reverse("login"),
            {
                "username": self.usuario.email,
                "password": "senha-segura-123",
            },
            secure=True,
            HTTP_HOST="localhost:8000",
            HTTP_ORIGIN="https://localhost:8000",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("inicio"))

    def test_login_redireciona_cada_papel_para_sua_tela_inicial(self):
        usuarios = [
            (
                Profissional,
                "profissional-login@exemplo.com",
                {"especialidade": "Nutrição"},
                "inicio",
            ),
            (
                Recepcionista,
                "recepcionista-login@exemplo.com",
                {},
                "inicio",
            ),
            (
                Usuario,
                "administrador-login@exemplo.com",
                {"superuser": True},
                "administracao",
            ),
        ]
        for modelo, email, extra, destino in usuarios:
            with self.subTest(papel=email):
                if extra.pop("superuser", False):
                    usuario = modelo.objects.create_superuser(
                        email=email,
                        password="Senha#Segura123",
                        nome="Conta de teste",
                    )
                else:
                    usuario = modelo.objects.create_user(
                        email=email,
                        password="Senha#Segura123",
                        nome="Conta de teste",
                        **extra,
                    )

                response = self.client.post(
                    reverse("login"),
                    {"username": email, "password": "Senha#Segura123"},
                    follow=True,
                )

                self.assertEqual(
                    response.redirect_chain[-1][0],
                    reverse(destino),
                )
                if destino == "administracao":
                    self.assertContains(response, "Painel")
                else:
                    self.assertContains(response, "Você entrou como")
                self.client.logout()

    def test_permite_encerrar_sessao(self):
        self.client.force_login(self.usuario)

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class DemoAccountsCommandTests(TestCase):
    def test_cria_conta_para_cada_papel_com_senha_aleatoria(self):
        output = StringIO()

        call_command("criar_usuarios_demo", stdout=output)

        credenciais = {}
        for linha in output.getvalue().splitlines():
            if ": " not in linha or " | Senha: " not in linha:
                continue
            papel, restante = linha.split(": ", 1)
            email, senha = restante.split(" | Senha: ", 1)
            credenciais[papel] = (email, senha)

        self.assertEqual(
            set(credenciais),
            {"Cliente", "Profissional", "Recepcionista", "Administrador"},
        )
        for papel, (email, senha) in credenciais.items():
            with self.subTest(papel=papel):
                usuario = Usuario.objects.get(email=email)
                self.assertGreaterEqual(len(senha), 24)
                self.assertTrue(usuario.check_password(senha))

        administrador = Usuario.objects.get(
            email=credenciais["Administrador"][0]
        )
        self.assertTrue(administrador.is_staff)
        self.assertTrue(administrador.is_superuser)
        self.assertEqual(
            administrador.perfil.papel,
            Perfil.Papel.ADMINISTRADOR,
        )

    def test_nao_sobrescreve_contas_demo_existentes(self):
        call_command("criar_usuarios_demo", stdout=StringIO())
        usuario = Usuario.objects.get(email="admin@gmail.com")
        senha_original = usuario.password

        with self.assertRaises(CommandError):
            call_command("criar_usuarios_demo", stdout=StringIO())

        usuario.refresh_from_db()
        self.assertEqual(usuario.password, senha_original)
        self.assertEqual(Usuario.objects.count(), 4)


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
        self.assertContains(response, "Modalidade de atendimento")
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
                "modalidade": Profissional.Modalidade.ONLINE,
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
        self.assertEqual(profissional.modalidade, Profissional.Modalidade.ONLINE)
        self.assertContains(response, "Conta criada com sucesso")

    def test_exige_modalidade_para_profissional(self):
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
        )

        self.assertContains(response, "Informe a modalidade de atendimento.")
        self.assertFalse(Profissional.objects.exists())

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
        response = self.client.post(reverse("admin:agendamento_sala_add"), {})
        self.assertEqual(response.status_code, 403)

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

        response = self.client.post(reverse("admin:agendamento_sala_add"), {})
        self.assertEqual(response.status_code, 403)

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
                "modalidade": Profissional.Modalidade.ONLINE,
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


class AdministracaoTests(TestCase):
    def setUp(self):
        self.administrador = Usuario.objects.create_superuser(
            email="admin-painel@exemplo.com",
            password="Senha#Admin984",
            nome="Administradora",
        )
        self.profissional = Profissional.objects.create_user(
            email="profissional-painel@exemplo.com",
            password="Senha#Prof984",
            nome="Profissional",
            especialidade="Fisioterapia",
        )
        self.cliente = Cliente.objects.create_user(
            email="cliente-painel@exemplo.com",
            password="Senha#Cliente984",
            nome="Cliente",
        )
        self.servico = Servico.objects.create(
            profissional=self.profissional,
            nome="Consulta",
            tipo="Atendimento",
            duracao_minutos=60,
        )
        self.sala = Sala.objects.create(nome="Sala A", capacidade=2)
        self.recurso = Recurso.objects.create(nome="Maca", exclusivo=True)
        self.client.force_login(self.administrador)

    def test_painel_mostra_cadastros_permissoes_e_ocupacao(self):
        inicio = timezone.make_aware(
            datetime.combine(timezone.localdate(), time(10))
        )
        agendamento = Agendamento.objects.create(
            cliente=self.cliente,
            profissional=self.profissional,
            servico=self.servico,
            sala=self.sala,
            data_hora_inicio=inicio,
            data_hora_fim=inicio + timedelta(hours=1),
        )
        agendamento.recursos.add(self.recurso)

        response = self.client.get(reverse("administracao"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Profissionais")
        self.assertContains(response, "Serviços")
        self.assertContains(response, "Salas e ocupação de hoje")
        self.assertContains(response, "Equipamentos e ocupação de hoje")
        self.assertContains(response, "Usuários e permissões")
        self.assertContains(response, "Agendamentos de hoje")
        self.assertContains(
            response,
            "<strong>1</strong> agendamentos ativos hoje",
            html=True,
        )
        self.assertContains(response, "Consulta")
        self.assertContains(response, "Atribuir papel a um usuário")

    def test_painel_exige_papel_administrador(self):
        cliente = Cliente.objects.create_user(
            email="cliente-sem-admin@exemplo.com",
            password="Senha#Cliente984",
            nome="Cliente sem acesso",
        )
        self.client.force_login(cliente)

        response = self.client.get(reverse("administracao"))

        self.assertEqual(response.status_code, 403)
        response = self.client.post(
            reverse("administracao_sala_nova"),
            {"nome": "Sala não autorizada", "capacidade": 2},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Sala.objects.filter(nome="Sala não autorizada").exists())

    def test_painel_exige_autenticacao(self):
        self.client.logout()

        response = self.client.get(reverse("administracao"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('administracao')}",
        )

    def test_administrador_cadastra_e_edita_os_quatro_tipos_de_item(self):
        senha = "Nuvem#Roxa39!Chuva"
        response = self.client.post(
            reverse("administracao_profissional_novo"),
            {
                "nome": "Nova profissional",
                "email": "nova-profissional@exemplo.com",
                "telefone": "(11) 99999-1234",
                "especialidade": "Nutrição",
                "modalidade": Profissional.Modalidade.ONLINE,
                "formacao": "Nutrição clínica",
                "apresentacao": "Atendimento remoto.",
                "is_active": "on",
                "senha": senha,
                "confirmar_senha": senha,
            },
        )
        self.assertRedirects(response, reverse("administracao"))
        nova_profissional = Profissional.objects.get(
            email="nova-profissional@exemplo.com"
        )
        self.assertTrue(nova_profissional.check_password(senha))
        self.assertEqual(
            nova_profissional.perfil.papel,
            Perfil.Papel.PROFISSIONAL,
        )

        response = self.client.post(
            reverse(
                "administracao_profissional_editar",
                args=[nova_profissional.pk],
            ),
            {
                "nome": "Profissional editada",
                "email": nova_profissional.email,
                "telefone": "(11) 98888-1111",
                "especialidade": "Nutrição esportiva",
                "modalidade": Profissional.Modalidade.ONLINE,
                "formacao": "Nutrição clínica",
                "apresentacao": "Novo atendimento remoto.",
                "is_active": "on",
                "senha": "",
                "confirmar_senha": "",
            },
        )
        self.assertRedirects(response, reverse("administracao"))
        nova_profissional.refresh_from_db()
        self.assertEqual(nova_profissional.nome, "Profissional editada")
        self.assertTrue(nova_profissional.check_password(senha))

        response = self.client.post(
            reverse("administracao_servico_novo"),
            {
                "profissional": self.profissional.pk,
                "nome": "Avaliação inicial",
                "tipo": "Avaliação",
                "duracao_minutos": 45,
            },
        )
        self.assertRedirects(response, reverse("administracao"))
        servico = Servico.objects.get(nome="Avaliação inicial")
        response = self.client.post(
            reverse("administracao_servico_editar", args=[servico.pk]),
            {
                "profissional": self.profissional.pk,
                "nome": "Avaliação completa",
                "tipo": "Avaliação",
                "duracao_minutos": 60,
            },
        )
        self.assertRedirects(response, reverse("administracao"))
        servico.refresh_from_db()
        self.assertEqual(servico.nome, "Avaliação completa")

        response = self.client.post(
            reverse("administracao_sala_nova"),
            {"nome": "Sala B", "capacidade": 4},
        )
        self.assertRedirects(response, reverse("administracao"))
        sala = Sala.objects.get(nome="Sala B")
        response = self.client.post(
            reverse("administracao_sala_editar", args=[sala.pk]),
            {"nome": "Sala B reformada", "capacidade": 5},
        )
        self.assertRedirects(response, reverse("administracao"))
        sala.refresh_from_db()
        self.assertEqual(sala.capacidade, 5)

        response = self.client.post(
            reverse("administracao_recurso_novo"),
            {"nome": "Bicicleta ergométrica", "exclusivo": "on"},
        )
        self.assertRedirects(response, reverse("administracao"))
        recurso = Recurso.objects.get(nome="Bicicleta ergométrica")
        response = self.client.post(
            reverse("administracao_recurso_editar", args=[recurso.pk]),
            {"nome": "Bicicleta", "exclusivo": ""},
        )
        self.assertRedirects(response, reverse("administracao"))
        recurso.refresh_from_db()
        self.assertEqual(recurso.nome, "Bicicleta")
        self.assertFalse(recurso.exclusivo)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PerfilEdicaoTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create_user(
            email="cliente-perfil@exemplo.com",
            password="Senha#Segura123",
            nome="Cliente",
        )
        self.profissional = Profissional.objects.create_user(
            email="profissional-perfil@exemplo.com",
            password="Senha#Segura123",
            nome="Profissional",
            especialidade="Fisioterapia",
        )

    def test_cliente_edita_apenas_nome_e_telefone(self):
        self.client.force_login(self.cliente)

        response = self.client.get(reverse("perfil"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Telefone")
        self.assertNotContains(response, "Especialidade")

        response = self.client.post(
            reverse("perfil"),
            {
                "nome": "Cliente Atualizado",
                "telefone": "(11) 99999-1234",
                "papel": Perfil.Papel.ADMINISTRADOR,
                "is_staff": "on",
            },
        )

        self.assertRedirects(response, reverse("inicio"))
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.nome, "Cliente Atualizado")
        self.assertEqual(self.cliente.telefone, "(11) 99999-1234")
        self.assertEqual(self.cliente.perfil.papel, Perfil.Papel.CLIENTE)
        self.assertFalse(self.cliente.is_staff)

    def test_profissional_edita_dados_profissionais(self):
        self.client.force_login(self.profissional)

        response = self.client.get(reverse("perfil"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Especialidade")
        self.assertContains(response, "Apresentação")

        response = self.client.post(
            reverse("perfil"),
            {
                "nome": "Profissional Atualizada",
                "telefone": "(21) 98888-4321",
                "especialidade": "Fisioterapia esportiva",
                "apresentacao": "Atendimento individualizado.",
            },
        )

        self.assertRedirects(response, reverse("inicio"))
        self.profissional.refresh_from_db()
        self.assertEqual(self.profissional.nome, "Profissional Atualizada")
        self.assertEqual(self.profissional.telefone, "(21) 98888-4321")
        self.assertEqual(
            self.profissional.especialidade,
            "Fisioterapia esportiva",
        )
        self.assertEqual(
            self.profissional.apresentacao,
            "Atendimento individualizado.",
        )

    def test_usuario_anônimo_precisa_entrar(self):
        response = self.client.get(reverse("perfil"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('perfil')}",
        )


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
        self.assertContains(response, "Buscar profissionais")
        self.assertContains(response, "Especialidade")
        self.assertContains(response, "Serviço")
        self.assertContains(response, "Modalidade")
        self.assertContains(response, self.profissional.nome)
        self.assertContains(
            response,
            reverse("profissional_detail", args=[self.profissional.pk]),
        )

    def test_filtros_de_especialidade_servico_e_modalidade(self):
        outro_profissional = Profissional.objects.create_user(
            email="nutricionista@exemplo.com",
            password="senha-segura-123",
            nome="Carla Nunes",
            papel=Perfil.Papel.PROFISSIONAL,
            especialidade="Nutricionista",
            modalidade=Profissional.Modalidade.ONLINE,
        )
        Servico.objects.create(
            profissional=outro_profissional,
            nome="Consulta Nutricional",
            tipo="Consulta",
            duracao_minutos=45,
        )

        response = self.client.get(
            reverse("profissionais"),
            {
                "especialidade": "Nutricionista",
                "servico": "Consulta Nutricional",
                "modalidade": Profissional.Modalidade.ONLINE,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(
            response.context["profissionais"],
            [outro_profissional],
        )
        self.assertContains(response, "Carla Nunes")
        self.assertContains(response, "Consulta Nutricional")
        self.assertContains(
            response,
            reverse("profissional_detail", args=[outro_profissional.pk]),
        )
        self.assertNotContains(response, "Ana Silva")

    def test_filtro_de_servico_nao_duplica_profissionais(self):
        outro_servico = Servico.objects.create(
            profissional=self.profissional,
            nome="Acompanhamento",
            tipo="Treinamento",
            duracao_minutos=30,
        )

        response = self.client.get(
            reverse("profissionais"),
            {"servico": outro_servico.nome},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["profissionais"]), 1)
        self.assertEqual(
            response.context["profissionais"][0],
            self.profissional,
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
        self.assertContains(response, "Agendar este serviço")

    def test_botao_do_perfil_abre_agendamento_do_servico(self):
        response = self.client.get(
            reverse("profissional_detail", args=[self.profissional.pk])
        )

        self.assertContains(
            response,
            f'href="{reverse("novo_agendamento", args=[self.servico.pk])}"',
        )
        self.assertContains(response, "Agendar este serviço")

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


# ---------------------------------------------------------------------------
# Etapa 1 da unificação: disponibilidade e bloqueios (UC10, UC11, RN05, RN13).
# Casos de modelo adaptados de src/agenda/tests.py (DisponibilidadeTests e
# BloqueioTests); casos de tela escritos para as views deste projeto.
# ---------------------------------------------------------------------------
from django.core.exceptions import ValidationError  # noqa: E402
from django.db import IntegrityError, transaction  # noqa: E402


def _aware(dia, hora):
    return timezone.make_aware(datetime.combine(dia, hora))


class DisponibilidadeModelTests(TestCase):
    def setUp(self):
        self.prof = Profissional.objects.create_user(
            email="prof-disp@exemplo.com",
            password="Senha#Forte123",
            nome="Nutri",
            especialidade="Nutrição",
            papel="profissional",
        )

    def test_hora_fim_deve_ser_posterior(self):
        faixa = Disponibilidade(
            profissional=self.prof,
            dia_semana=0,
            hora_inicio=time(10),
            hora_fim=time(9),
        )
        with self.assertRaises(ValidationError) as erro:
            faixa.full_clean()
        self.assertIn("hora_fim", erro.exception.message_dict)
        with self.assertRaises(IntegrityError), transaction.atomic():
            faixa.save()

    def test_str(self):
        faixa = Disponibilidade.objects.create(
            profissional=self.prof,
            dia_semana=0,
            hora_inicio=time(8),
            hora_fim=time(18),
        )
        self.assertIn("Segunda-feira", str(faixa))


class BloqueioModelTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create_user(
            email="cliente-bloq@exemplo.com",
            password="Senha#Forte123",
            nome="Cliente",
            papel="cliente",
        )
        self.prof = Profissional.objects.create_user(
            email="prof-bloq@exemplo.com",
            password="Senha#Forte123",
            nome="Nutri",
            especialidade="Nutrição",
            papel="profissional",
        )
        self.servico = Servico.objects.create(
            profissional=self.prof,
            nome="Consulta",
            tipo="Nutrição",
            duracao_minutos=60,
        )
        self.dia = timezone.localdate() + timedelta(days=7)

    def _agendar(self, dia, hora, **extra):
        return Agendamento.objects.create(
            cliente=self.cliente,
            profissional=self.prof,
            servico=self.servico,
            data_hora_inicio=_aware(dia, time(hora)),
            data_hora_fim=_aware(dia, time(hora + 1)),
            **extra,
        )

    def test_hora_fim_deve_ser_posterior(self):
        bloqueio = Bloqueio(
            profissional=self.prof,
            inicio=_aware(self.dia, time(10)),
            fim=_aware(self.dia, time(9)),
            motivo="Teste",
        )
        with self.assertRaises(ValidationError) as erro:
            bloqueio.full_clean()
        self.assertIn("fim", erro.exception.message_dict)
        with self.assertRaises(IntegrityError), transaction.atomic():
            bloqueio.save()

    def test_agendamentos_afetados_lista_atendimentos_no_periodo(self):
        agendamento = self._agendar(self.dia, 9)
        bloqueio = Bloqueio(
            profissional=self.prof,
            inicio=_aware(self.dia, time(8)),
            fim=_aware(self.dia, time(12)),
            motivo="Férias",
        )
        self.assertIn(agendamento, bloqueio.agendamentos_afetados())

    def test_agendamentos_afetados_ignora_outro_dia(self):
        self._agendar(self.dia + timedelta(days=1), 9)
        bloqueio = Bloqueio(
            profissional=self.prof,
            inicio=_aware(self.dia, time(8)),
            fim=_aware(self.dia, time(12)),
            motivo="Férias",
        )
        self.assertEqual(bloqueio.agendamentos_afetados().count(), 0)

    def test_agendamentos_afetados_ignora_cancelados(self):
        self._agendar(self.dia, 9, status=Agendamento.Status.CANCELADO)
        bloqueio = Bloqueio(
            profissional=self.prof,
            inicio=_aware(self.dia, time(8)),
            fim=_aware(self.dia, time(12)),
            motivo="Férias",
        )
        self.assertEqual(bloqueio.agendamentos_afetados().count(), 0)

    def test_agendamentos_afetados_ignora_horarios_adjacentes(self):
        self._agendar(self.dia, 12)
        bloqueio = Bloqueio(
            profissional=self.prof,
            inicio=_aware(self.dia, time(8)),
            fim=_aware(self.dia, time(12)),
            motivo="Manhã livre",
        )
        self.assertEqual(bloqueio.agendamentos_afetados().count(), 0)


class DisponibilidadeBloqueioViewTests(TestCase):
    def setUp(self):
        self.prof = Profissional.objects.create_user(
            email="prof-tela@exemplo.com",
            password="Senha#Forte123",
            nome="Ana Personal",
            especialidade="Personal Trainer",
            papel="profissional",
        )
        self.outro_prof = Profissional.objects.create_user(
            email="outro-prof@exemplo.com",
            password="Senha#Forte123",
            nome="Bruno Fisio",
            especialidade="Fisioterapia",
            papel="profissional",
        )
        self.cliente = Cliente.objects.create_user(
            email="cliente-tela@exemplo.com",
            password="Senha#Forte123",
            nome="Carla Cliente",
            papel="cliente",
        )
        self.servico = Servico.objects.create(
            profissional=self.prof,
            nome="Avaliação Física",
            tipo="Avaliação",
            duracao_minutos=60,
        )
        self.dia = timezone.localdate() + timedelta(days=7)
        self.url = reverse("disponibilidade_bloqueio")

    def _dados_bloqueio(self, **extra):
        dados = {
            "data": self.dia.isoformat(),
            "hora_inicio": "08:00",
            "hora_fim": "12:00",
            "motivo": "Curso",
        }
        dados.update(extra)
        return dados

    # Acesso (RN08) ---------------------------------------------------------
    def test_exige_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_cliente_nao_acessa(self):
        self.client.force_login(self.cliente)
        response = self.client.get(self.url)
        self.assertContains(response, "Acesso negado", status_code=403)
        response = self.client.post(reverse("criar_bloqueio"), self._dados_bloqueio())
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Bloqueio.objects.exists())

    def test_profissional_ve_apenas_suas_faixas_e_bloqueios(self):
        Disponibilidade.objects.create(
            profissional=self.prof, dia_semana=0, hora_inicio=time(7), hora_fim=time(11)
        )
        Disponibilidade.objects.create(
            profissional=self.outro_prof, dia_semana=2, hora_inicio=time(13), hora_fim=time(17)
        )
        Bloqueio.objects.create(
            profissional=self.outro_prof,
            inicio=_aware(self.dia, time(8)),
            fim=_aware(self.dia, time(9)),
            motivo="Motivo de outra pessoa",
        )
        self.client.force_login(self.prof)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Disponibilidade e bloqueios")
        self.assertEqual(len(response.context["faixas"]), 1)
        self.assertContains(response, "07:00")
        self.assertNotContains(response, "13:00")
        self.assertNotContains(response, "Motivo de outra pessoa")

    # Disponibilidade (UC10, RN05) -----------------------------------------
    def test_cadastra_faixa_de_disponibilidade(self):
        self.client.force_login(self.prof)
        response = self.client.post(
            self.url, {"dia_semana": 1, "hora_inicio": "08:00", "hora_fim": "12:00"}
        )
        self.assertRedirects(response, self.url)
        faixa = Disponibilidade.objects.get(profissional=self.prof)
        self.assertEqual((faixa.dia_semana, faixa.hora_inicio, faixa.hora_fim), (1, time(8), time(12)))

    def test_recusa_faixa_com_fim_antes_do_inicio(self):
        self.client.force_login(self.prof)
        response = self.client.post(
            self.url, {"dia_semana": 1, "hora_inicio": "12:00", "hora_fim": "08:00"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "O horário final deve ser posterior ao inicial.")
        self.assertFalse(Disponibilidade.objects.exists())

    def test_faixa_cadastrada_libera_horarios_no_perfil_publico(self):
        self.client.force_login(self.prof)
        self.client.post(
            self.url,
            {"dia_semana": self.dia.weekday(), "hora_inicio": "08:00", "hora_fim": "10:00"},
        )
        response = self.client.get(reverse("profissional_detail", args=[self.prof.pk]))
        self.assertContains(response, f"{self.dia:%d/%m/%Y} às 08:00")

    def test_remove_propria_faixa(self):
        faixa = Disponibilidade.objects.create(
            profissional=self.prof, dia_semana=0, hora_inicio=time(7), hora_fim=time(11)
        )
        self.client.force_login(self.prof)
        response = self.client.post(reverse("remover_disponibilidade", args=[faixa.pk]))
        self.assertRedirects(response, self.url)
        self.assertFalse(Disponibilidade.objects.exists())

    def test_nao_remove_faixa_de_outro_profissional(self):
        faixa = Disponibilidade.objects.create(
            profissional=self.outro_prof, dia_semana=0, hora_inicio=time(7), hora_fim=time(11)
        )
        self.client.force_login(self.prof)
        response = self.client.post(reverse("remover_disponibilidade", args=[faixa.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Disponibilidade.objects.filter(pk=faixa.pk).exists())

    def test_remocao_exige_post(self):
        faixa = Disponibilidade.objects.create(
            profissional=self.prof, dia_semana=0, hora_inicio=time(7), hora_fim=time(11)
        )
        self.client.force_login(self.prof)
        response = self.client.get(reverse("remover_disponibilidade", args=[faixa.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Disponibilidade.objects.filter(pk=faixa.pk).exists())

    # Bloqueios (UC11, RN13) -----------------------------------------------
    def test_cria_bloqueio_sem_atendimentos_afetados(self):
        self.client.force_login(self.prof)
        response = self.client.post(reverse("criar_bloqueio"), self._dados_bloqueio())
        self.assertRedirects(response, self.url)
        bloqueio = Bloqueio.objects.get(profissional=self.prof)
        self.assertEqual(bloqueio.inicio, _aware(self.dia, time(8)))
        self.assertEqual(bloqueio.fim, _aware(self.dia, time(12)))
        self.assertEqual(bloqueio.motivo, "Curso")

    def test_recusa_bloqueio_com_fim_antes_do_inicio(self):
        self.client.force_login(self.prof)
        response = self.client.post(
            reverse("criar_bloqueio"),
            self._dados_bloqueio(hora_inicio="12:00", hora_fim="08:00"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "O horário final deve ser posterior ao inicial.")
        self.assertFalse(Bloqueio.objects.exists())

    def test_motivo_e_obrigatorio(self):
        self.client.force_login(self.prof)
        response = self.client.post(reverse("criar_bloqueio"), self._dados_bloqueio(motivo=""))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Bloqueio.objects.exists())

    def test_bloqueio_com_atendimento_pede_confirmacao(self):
        Agendamento.objects.create(
            cliente=self.cliente,
            profissional=self.prof,
            servico=self.servico,
            data_hora_inicio=_aware(self.dia, time(9)),
            data_hora_fim=_aware(self.dia, time(10)),
        )
        self.client.force_login(self.prof)
        response = self.client.post(reverse("criar_bloqueio"), self._dados_bloqueio())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "agendamento/confirmar_bloqueio.html")
        self.assertContains(response, "Carla Cliente")
        self.assertContains(response, "Confirmar e bloquear mesmo assim")
        self.assertFalse(Bloqueio.objects.exists())

        response = self.client.post(
            reverse("criar_bloqueio"), self._dados_bloqueio(confirmar="1")
        )
        self.assertRedirects(response, self.url)
        self.assertEqual(Bloqueio.objects.count(), 1)

    def test_bloqueio_esconde_horario_no_perfil_publico(self):
        Disponibilidade.objects.create(
            profissional=self.prof,
            dia_semana=self.dia.weekday(),
            hora_inicio=time(8),
            hora_fim=time(10),
        )
        self.client.force_login(self.prof)
        self.client.post(
            reverse("criar_bloqueio"),
            self._dados_bloqueio(hora_inicio="08:00", hora_fim="09:00"),
        )
        response = self.client.get(reverse("profissional_detail", args=[self.prof.pk]))
        self.assertNotContains(response, f"{self.dia:%d/%m/%Y} às 08:00")
        self.assertContains(response, f"{self.dia:%d/%m/%Y} às 09:00")

    def test_origem_externa_e_ignorada(self):
        self.client.force_login(self.prof)
        response = self.client.post(
            reverse("criar_bloqueio"),
            self._dados_bloqueio(origem="https://exemplo-malicioso.com/"),
        )
        self.assertRedirects(response, self.url)

    def test_remove_proprio_bloqueio(self):
        bloqueio = Bloqueio.objects.create(
            profissional=self.prof,
            inicio=_aware(self.dia, time(8)),
            fim=_aware(self.dia, time(9)),
            motivo="Curso",
        )
        self.client.force_login(self.prof)
        response = self.client.post(reverse("remover_bloqueio", args=[bloqueio.pk]))
        self.assertRedirects(response, self.url)
        self.assertFalse(Bloqueio.objects.exists())

    def test_nao_remove_bloqueio_de_outro_profissional(self):
        bloqueio = Bloqueio.objects.create(
            profissional=self.outro_prof,
            inicio=_aware(self.dia, time(8)),
            fim=_aware(self.dia, time(9)),
            motivo="Curso",
        )
        self.client.force_login(self.prof)
        response = self.client.post(reverse("remover_bloqueio", args=[bloqueio.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Bloqueio.objects.filter(pk=bloqueio.pk).exists())

    def test_menu_do_profissional_leva_a_tela(self):
        self.client.force_login(self.prof)
        response = self.client.get(reverse("inicio"))
        self.assertContains(response, f'href="{self.url}"')


# ---------------------------------------------------------------------------
# Etapa 2 da unificação: validação de conflitos e sugestões de horários
# (RN01–RN07, RN13, RF09, RF26). Adaptados de src/agenda/tests.py
# (AgendamentoTests, HorariosLivresTests e NovoAgendamentoViewTests) para
# data_hora_inicio/data_hora_fim e para vários equipamentos por agendamento.
# ---------------------------------------------------------------------------
from agendamento.models import horarios_livres  # noqa: E402


class ConflitoAgendamentoModelTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create_user(
            email="c1@exemplo.com", password="Senha#Forte123", nome="Cliente 1", papel="cliente"
        )
        self.cliente2 = Cliente.objects.create_user(
            email="c2@exemplo.com", password="Senha#Forte123", nome="Cliente 2", papel="cliente"
        )
        self.prof = Profissional.objects.create_user(
            email="p1@exemplo.com", password="Senha#Forte123", nome="Prof 1",
            especialidade="Nutrição", papel="profissional",
        )
        self.prof2 = Profissional.objects.create_user(
            email="p2@exemplo.com", password="Senha#Forte123", nome="Prof 2",
            especialidade="Personal Trainer", papel="profissional",
        )
        self.dia = timezone.localdate() + timedelta(days=7)
        for profissional in (self.prof, self.prof2):
            Disponibilidade.objects.create(
                profissional=profissional,
                dia_semana=self.dia.weekday(),
                hora_inicio=time(8),
                hora_fim=time(20),
            )
        self.servico = Servico.objects.create(
            profissional=self.prof, nome="Consulta", tipo="Nutrição", duracao_minutos=60
        )
        self.sala = Sala.objects.create(nome="Sala 1", capacidade=2)
        self.sala2 = Sala.objects.create(nome="Sala 2", capacidade=2)
        self.maca = Recurso.objects.create(nome="Maca", exclusivo=True)
        self.colchonete = Recurso.objects.create(nome="Colchonete", exclusivo=False)

    def montar(self, cliente=None, profissional=None, inicio=time(9), fim=time(10), **kw):
        return Agendamento(
            cliente=cliente or self.cliente,
            profissional=profissional or self.prof,
            servico=kw.pop("servico", self.servico),
            data_hora_inicio=_aware(self.dia, inicio) if inicio else None,
            data_hora_fim=_aware(self.dia, fim) if fim else None,
            **kw,
        )

    def criar(self, recursos=(), **kw):
        """Cria validando como as views fazem (full_clean + equipamentos)."""
        agendamento = self.montar(**kw)
        motivos = agendamento.motivos_conflito(recursos=list(recursos))
        if motivos:
            raise ValidationError(motivos)
        agendamento.full_clean()
        agendamento.save()
        agendamento.recursos.set(recursos)
        return agendamento

    # RN07 -------------------------------------------------------------------
    def test_hora_fim_calculada_pelo_servico(self):
        agendamento = self.montar(inicio=time(16), fim=None)
        agendamento.clean()
        self.assertEqual(agendamento.data_hora_fim, _aware(self.dia, time(17)))

    def test_hora_fim_informada_prevalece(self):
        agendamento = self.criar(inicio=time(16), fim=time(16, 30))
        self.assertEqual(agendamento.data_hora_fim, _aware(self.dia, time(16, 30)))

    def test_hora_fim_deve_ser_posterior(self):
        for fim in (time(10), time(9)):
            with self.assertRaises(ValidationError):
                self.montar(inicio=time(10), fim=fim).full_clean()

    def test_servico_duracao_minima(self):
        with self.assertRaises(ValidationError):
            Servico(profissional=self.prof, nome="Rápido", tipo="X", duracao_minutos=0).full_clean()

    def test_status_inicial(self):
        self.assertEqual(self.criar().status, Agendamento.Status.AGENDADO)

    # RN03 / RN04 ------------------------------------------------------------
    def test_conflito_de_sala(self):
        self.criar(sala=self.sala)
        with self.assertRaisesMessage(ValidationError, "A sala Sala 1 já está reservada"):
            self.criar(cliente=self.cliente2, profissional=self.prof2,
                       inicio=time(9, 30), fim=time(10, 30), sala=self.sala)

    def test_salas_diferentes_nao_conflitam(self):
        self.criar(sala=self.sala)
        self.criar(cliente=self.cliente2, profissional=self.prof2,
                   inicio=time(9, 30), fim=time(10, 30), sala=self.sala2)

    def test_conflito_de_recurso_exclusivo(self):
        self.criar(recursos=[self.maca])
        with self.assertRaisesMessage(ValidationError, "O equipamento Maca já está reservado"):
            self.criar(cliente=self.cliente2, profissional=self.prof2,
                       inicio=time(9, 30), fim=time(10, 30), recursos=[self.maca])

    def test_recurso_compartilhado_nao_conflita(self):
        self.criar(recursos=[self.colchonete])
        self.criar(cliente=self.cliente2, profissional=self.prof2,
                   inicio=time(9, 30), fim=time(10, 30), recursos=[self.colchonete])

    def test_varios_equipamentos_so_o_exclusivo_ocupado_conflita(self):
        esteira = Recurso.objects.create(nome="Esteira", exclusivo=True)
        self.criar(recursos=[self.maca, self.colchonete])
        motivos = self.montar(cliente=self.cliente2, profissional=self.prof2).motivos_conflito(
            recursos=[esteira, self.colchonete, self.maca]
        )
        self.assertEqual(motivos, ["O equipamento Maca já está reservado neste horário."])

    def test_equipamentos_vinculados_sao_considerados_apos_salvar(self):
        self.criar(recursos=[self.maca])
        segundo = self.criar(cliente=self.cliente2, profissional=self.prof2,
                             inicio=time(11), fim=time(12), recursos=[self.maca])
        segundo.data_hora_inicio = _aware(self.dia, time(9, 30))
        segundo.data_hora_fim = _aware(self.dia, time(10, 30))
        with self.assertRaisesMessage(ValidationError, "Maca"):
            segundo.full_clean()

    def test_sala_livre_apos_cancelamento(self):
        self.criar(sala=self.sala, status=Agendamento.Status.CANCELADO)
        self.criar(sala=self.sala)

    # RN01 / RN02 ------------------------------------------------------------
    def test_conflito_do_profissional(self):
        self.criar()
        with self.assertRaisesMessage(ValidationError, "O profissional já possui"):
            self.criar(cliente=self.cliente2, inicio=time(9, 30), fim=time(10, 30))

    def test_conflito_do_cliente(self):
        self.criar()
        with self.assertRaisesMessage(ValidationError, "O cliente já possui"):
            self.criar(profissional=self.prof2, inicio=time(9, 30), fim=time(10, 30))

    def test_horarios_adjacentes_nao_conflitam(self):
        self.criar()
        self.criar(inicio=time(10), fim=time(11))

    def test_cancelado_nao_bloqueia(self):
        self.criar(status=Agendamento.Status.CANCELADO)
        self.criar()

    def test_editar_proprio_agendamento(self):
        agendamento = self.criar(sala=self.sala, recursos=[self.maca])
        agendamento.status = Agendamento.Status.CONFIRMADO
        agendamento.full_clean()
        agendamento.save()

    # RN05 / RN13 ------------------------------------------------------------
    def test_horario_fora_da_faixa_recusado(self):
        with self.assertRaisesMessage(ValidationError, "fora da disponibilidade"):
            self.criar(inicio=time(7), fim=time(8))

    def test_horario_que_ultrapassa_a_faixa_recusado(self):
        with self.assertRaisesMessage(ValidationError, "fora da disponibilidade"):
            self.criar(inicio=time(19, 30), fim=time(20, 30))

    def test_horario_dentro_da_faixa_aceito(self):
        self.criar(inicio=time(8), fim=time(9))

    def test_sem_disponibilidade_cadastrada_recusa(self):
        Disponibilidade.objects.filter(profissional=self.prof).delete()
        with self.assertRaises(ValidationError):
            self.criar()

    def test_bloqueio_recusa_horario(self):
        Bloqueio.objects.create(
            profissional=self.prof,
            inicio=_aware(self.dia, time(9)),
            fim=_aware(self.dia, time(10)),
            motivo="Consulta médica",
        )
        with self.assertRaisesMessage(ValidationError, "bloqueado pelo profissional"):
            self.criar(inicio=time(9, 30), fim=time(10, 30))

    # Motivos e compatibilidade ---------------------------------------------
    def test_motivos_lista_todas_as_regras_violadas(self):
        self.criar(sala=self.sala)
        motivos = self.montar(inicio=time(9), fim=time(10), sala=self.sala).motivos_conflito()
        self.assertEqual(
            motivos,
            [
                Agendamento.MSG_PROFISSIONAL_OCUPADO,
                Agendamento.MSG_CLIENTE_OCUPADO,
                "A sala Sala 1 já está reservada neste horário.",
            ],
        )

    def test_verificar_conflito_retorna_booleano(self):
        self.assertFalse(self.montar().verificar_conflito())
        self.criar()
        self.assertTrue(self.montar(cliente=self.cliente2).verificar_conflito())
        with self.assertRaises(ValueError):
            self.montar(inicio=time(10), fim=time(9)).verificar_conflito()

    def test_concluido_nao_e_revalidado(self):
        agendamento = self.criar()
        Disponibilidade.objects.filter(profissional=self.prof).delete()
        agendamento.status = Agendamento.Status.CONCLUIDO
        agendamento.full_clean()


class HorariosLivresTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create_user(
            email="c-livres@exemplo.com", password="Senha#Forte123", nome="Cliente", papel="cliente"
        )
        self.prof = Profissional.objects.create_user(
            email="p-livres@exemplo.com", password="Senha#Forte123", nome="Prof",
            especialidade="Nutrição", papel="profissional",
        )
        self.dia = timezone.localdate() + timedelta(days=7)
        Disponibilidade.objects.create(
            profissional=self.prof, dia_semana=self.dia.weekday(),
            hora_inicio=time(8), hora_fim=time(10),
        )
        self.servico = Servico.objects.create(
            profissional=self.prof, nome="Consulta", tipo="Nutrição", duracao_minutos=60
        )

    def horas(self, livres):
        return [timezone.localtime(h).time() for h in livres]

    def test_sem_ocupacao_devolve_todas_as_faixas(self):
        livres = horarios_livres(self.prof, self.dia, duracao_minutos=30)
        self.assertEqual(self.horas(livres), [time(8), time(8, 30), time(9), time(9, 30)])
        self.assertTrue(all(timezone.is_aware(h) for h in livres))

    def test_passo_diferente_da_duracao(self):
        livres = horarios_livres(self.prof, self.dia, duracao_minutos=60, passo_minutos=30)
        self.assertEqual(self.horas(livres), [time(8), time(8, 30), time(9)])

    def test_bloqueio_esconde_horario(self):
        Bloqueio.objects.create(
            profissional=self.prof, inicio=_aware(self.dia, time(9)),
            fim=_aware(self.dia, time(9, 30)), motivo="Almoço",
        )
        self.assertNotIn(time(9), self.horas(horarios_livres(self.prof, self.dia, 30)))

    def test_bloqueio_nao_atrapalha_outro_dia(self):
        outro_dia = self.dia + timedelta(days=1)
        Disponibilidade.objects.create(
            profissional=self.prof, dia_semana=outro_dia.weekday(),
            hora_inicio=time(8), hora_fim=time(10),
        )
        Bloqueio.objects.create(
            profissional=self.prof, inicio=_aware(self.dia, time(8)),
            fim=_aware(self.dia, time(10)), motivo="Férias",
        )
        livres = horarios_livres(self.prof, outro_dia, duracao_minutos=30)
        self.assertEqual(self.horas(livres), [time(8), time(8, 30), time(9), time(9, 30)])

    def test_atendimento_ativo_esconde_horario(self):
        Agendamento.objects.create(
            cliente=self.cliente, profissional=self.prof, servico=self.servico,
            data_hora_inicio=_aware(self.dia, time(8)), data_hora_fim=_aware(self.dia, time(9)),
        )
        horas = self.horas(horarios_livres(self.prof, self.dia, 30))
        self.assertNotIn(time(8), horas)
        self.assertNotIn(time(8, 30), horas)
        self.assertIn(time(9), horas)

    def test_atendimento_cancelado_nao_esconde_horario(self):
        Agendamento.objects.create(
            cliente=self.cliente, profissional=self.prof, servico=self.servico,
            data_hora_inicio=_aware(self.dia, time(8)), data_hora_fim=_aware(self.dia, time(9)),
            status=Agendamento.Status.CANCELADO,
        )
        self.assertIn(time(8), self.horas(horarios_livres(self.prof, self.dia, 30)))

    def test_dia_sem_faixa_devolve_vazio(self):
        self.assertEqual(horarios_livres(self.prof, self.dia + timedelta(days=1), 30), [])


class NovoAgendamentoConflitoViewTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create_user(
            email="cliente-conf@exemplo.com", password="Senha#Forte123",
            nome="João Pereira", papel="cliente",
        )
        self.outro_cliente = Cliente.objects.create_user(
            email="outro-conf@exemplo.com", password="Senha#Forte123",
            nome="Maria Souza", papel="cliente",
        )
        self.prof = Profissional.objects.create_user(
            email="prof-conf@exemplo.com", password="Senha#Forte123", nome="Ana Silva",
            especialidade="Personal Trainer", papel="profissional",
        )
        self.prof2 = Profissional.objects.create_user(
            email="prof2-conf@exemplo.com", password="Senha#Forte123", nome="Bruno Lima",
            especialidade="Fisioterapia", papel="profissional",
        )
        self.dia = timezone.localdate() + timedelta(days=1)
        for profissional in (self.prof, self.prof2):
            Disponibilidade.objects.create(
                profissional=profissional, dia_semana=self.dia.weekday(),
                hora_inicio=time(8), hora_fim=time(12),
            )
        self.servico = Servico.objects.create(
            profissional=self.prof, nome="Treino", tipo="Treinamento", duracao_minutos=60
        )
        self.servico2 = Servico.objects.create(
            profissional=self.prof2, nome="Sessão", tipo="Fisioterapia", duracao_minutos=60
        )
        self.sala = Sala.objects.create(nome="Estúdio 1", capacidade=4)
        self.maca = Recurso.objects.create(nome="Maca", exclusivo=True)
        self.url = reverse("novo_agendamento", args=[self.servico.pk])
        self.oito = _aware(self.dia, time(8))

    def ocupar(self, cliente, profissional, servico, inicio, sala=None, recursos=()):
        agendamento = Agendamento.objects.create(
            cliente=cliente, profissional=profissional, servico=servico, sala=sala,
            data_hora_inicio=inicio, data_hora_fim=inicio + timedelta(hours=1),
        )
        agendamento.recursos.set(recursos)
        return agendamento

    def test_tela_mostra_local_equipamentos_e_confirmacao(self):
        self.client.force_login(self.cliente)
        response = self.client.get(self.url)
        self.assertContains(response, "Local")
        self.assertContains(response, "Equipamentos")
        self.assertContains(response, "Estúdio 1")
        self.assertContains(response, 'data-confirm="Confirmar agendamento?"')
        self.assertNotContains(response, "Não foi possível reservar este horário")

    def test_sem_salas_e_equipamentos_os_campos_somem(self):
        Sala.objects.all().delete()
        Recurso.objects.all().delete()
        self.client.force_login(self.cliente)
        response = self.client.get(self.url)
        self.assertNotIn("sala", response.context["form"].fields)
        self.assertNotIn("recursos", response.context["form"].fields)

    def test_salva_sala_e_equipamentos(self):
        self.client.force_login(self.cliente)
        response = self.client.post(
            self.url,
            {"horario": self.oito.isoformat(), "sala": self.sala.pk, "recursos": [self.maca.pk]},
        )
        self.assertRedirects(response, reverse("profissionais"))
        agendamento = Agendamento.objects.get()
        self.assertEqual(agendamento.sala, self.sala)
        self.assertEqual(list(agendamento.recursos.all()), [self.maca])
        self.assertEqual(agendamento.data_hora_fim, self.oito + timedelta(hours=1))

    def test_conflito_do_cliente_mostra_motivo_e_sugestoes(self):
        self.ocupar(self.cliente, self.prof2, self.servico2, self.oito)
        self.client.force_login(self.cliente)
        response = self.client.post(self.url, {"horario": self.oito.isoformat()})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "O cliente já possui um agendamento neste horário.")
        self.assertContains(response, "não está mais disponível")
        self.assertEqual(Agendamento.objects.count(), 1)
        sugestoes = response.context["sugestoes"]
        self.assertTrue(sugestoes)
        self.assertNotIn(self.oito, sugestoes)
        self.assertNotIn(self.oito + timedelta(minutes=30), sugestoes)
        self.assertEqual(sugestoes[0], self.oito + timedelta(hours=1))
        self.assertContains(response, f'value="{sugestoes[0].isoformat()}"')

    def test_conflito_de_sala_sugere_horarios_com_a_sala_livre(self):
        self.ocupar(self.outro_cliente, self.prof2, self.servico2, self.oito, sala=self.sala)
        self.client.force_login(self.cliente)
        response = self.client.post(
            self.url, {"horario": self.oito.isoformat(), "sala": self.sala.pk}
        )
        self.assertContains(response, "A sala Estúdio 1 já está reservada neste horário.")
        self.assertFalse(Agendamento.objects.filter(cliente=self.cliente).exists())
        for sugestao in response.context["sugestoes"]:
            self.assertGreaterEqual(sugestao, self.oito + timedelta(hours=1))

    def test_conflito_de_equipamento_exclusivo(self):
        self.ocupar(self.outro_cliente, self.prof2, self.servico2, self.oito, recursos=[self.maca])
        self.client.force_login(self.cliente)
        response = self.client.post(
            self.url, {"horario": self.oito.isoformat(), "recursos": [self.maca.pk]}
        )
        self.assertContains(response, "O equipamento Maca já está reservado neste horário.")
        self.assertFalse(Agendamento.objects.filter(cliente=self.cliente).exists())

    def test_escolher_sugestao_agenda_com_as_mesmas_escolhas(self):
        self.ocupar(self.outro_cliente, self.prof2, self.servico2, self.oito, sala=self.sala)
        self.client.force_login(self.cliente)
        response = self.client.post(
            self.url, {"horario": self.oito.isoformat(), "sala": self.sala.pk}
        )
        sugestao = response.context["sugestoes"][0]
        # O botão da sugestão envia "horario" de novo, depois do <select>.
        response = self.client.post(
            self.url,
            {"horario": [self.oito.isoformat(), sugestao.isoformat()], "sala": self.sala.pk},
        )
        self.assertRedirects(response, reverse("profissionais"))
        agendamento = Agendamento.objects.get(cliente=self.cliente)
        self.assertEqual(agendamento.data_hora_inicio, sugestao)
        self.assertEqual(agendamento.sala, self.sala)

    def test_sem_sugestoes_explica_o_que_fazer(self):
        self.ocupar(self.outro_cliente, self.prof2, self.servico2, self.oito, recursos=[self.maca])
        # Maca ocupada em todos os outros horários da lista.
        outros_horarios = [h for h in self._horarios_da_tela() if h != self.oito]
        for indice, horario in enumerate(outros_horarios):
            cliente = Cliente.objects.create_user(
                email=f"extra{indice}@exemplo.com", password="Senha#Forte123",
                nome=f"Extra {indice}", papel="cliente",
            )
            Agendamento.objects.create(
                cliente=cliente, profissional=self.prof2, servico=self.servico2,
                data_hora_inicio=horario, data_hora_fim=horario + timedelta(minutes=30),
            ).recursos.set([self.maca])
        self.assertTrue(outros_horarios)
        self.client.force_login(self.cliente)
        response = self.client.post(
            self.url, {"horario": self.oito.isoformat(), "recursos": [self.maca.pk]}
        )
        self.assertEqual(response.context["sugestoes"], [])
        self.assertContains(response, "Não encontramos outro horário livre")

    def _horarios_da_tela(self):
        self.client.force_login(self.cliente)
        form = self.client.get(self.url).context["form"]
        self.client.logout()
        return [datetime.fromisoformat(valor) for valor, _ in form.fields["horario"].choices]


# ---------------------------------------------------------------------------
# Etapa 3 da unificação: cancelamento, reagendamento e agenda do cliente
# (UC7, UC8, UC9, RF11, RF12, RF17, RN10). Adaptados de src/agenda/tests.py
# (CancelamentoAgendamentoTests, ReagendamentoAgendamentoTests e
# AgendaClienteViewTests).
# ---------------------------------------------------------------------------
from agendamento.models import Recorrencia  # noqa: E402


class _BaseOperacaoAgenda(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create_user(
            email="cli-op@exemplo.com", password="Senha#Forte123", nome="Cliente Op", papel="cliente"
        )
        self.cliente2 = Cliente.objects.create_user(
            email="cli2-op@exemplo.com", password="Senha#Forte123", nome="Cliente Dois", papel="cliente"
        )
        self.prof = Profissional.objects.create_user(
            email="prof-op@exemplo.com", password="Senha#Forte123", nome="Prof Op",
            especialidade="Personal Trainer", papel="profissional",
        )
        self.outro_prof = Profissional.objects.create_user(
            email="prof2-op@exemplo.com", password="Senha#Forte123", nome="Prof Dois",
            especialidade="Nutrição", papel="profissional",
        )
        self.recepcao = Recepcionista.objects.create_user(
            email="recepcao-op@exemplo.com", password="Senha#Forte123", nome="Recepção",
            papel="recepcionista",
        )
        for dia in range(7):
            Disponibilidade.objects.create(
                profissional=self.prof, dia_semana=dia, hora_inicio=time(8), hora_fim=time(18)
            )
        self.servico = Servico.objects.create(
            profissional=self.prof, nome="Treino", tipo="Treinamento", duracao_minutos=60
        )
        self.sala = Sala.objects.create(nome="Sala Funcional", capacidade=4)
        self.halteres = Recurso.objects.create(nome="Halteres", exclusivo=True)
        self.dia = timezone.localdate() + timedelta(days=7)

    def agendar(self, cliente=None, dia=None, hora=time(9), recursos=(), **extra):
        inicio = _aware(dia or self.dia, hora)
        agendamento = Agendamento.objects.create(
            cliente=cliente or self.cliente,
            profissional=extra.pop("profissional", self.prof),
            servico=extra.pop("servico", self.servico),
            data_hora_inicio=inicio,
            data_hora_fim=inicio + timedelta(hours=1),
            **extra,
        )
        agendamento.recursos.set(recursos)
        return agendamento

    def livre_para(self, cliente, dia=None, hora=time(9), sala=None, recursos=()):
        inicio = _aware(dia or self.dia, hora)
        candidato = Agendamento(
            cliente=cliente, profissional=self.prof, servico=self.servico, sala=sala,
            data_hora_inicio=inicio, data_hora_fim=inicio + timedelta(hours=1),
        )
        return candidato.motivos_conflito(recursos=list(recursos)) == []


class CancelamentoAgendamentoTests(_BaseOperacaoAgenda):
    def test_exige_login_para_cancelar(self):
        agendamento = self.agendar()
        response = self.client.post(reverse("cancelar_agendamento", args=[agendamento.pk]))
        self.assertEqual(response.status_code, 302)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, Agendamento.Status.AGENDADO)

    def test_outro_cliente_nao_pode_cancelar(self):
        agendamento = self.agendar()
        self.client.force_login(self.cliente2)
        response = self.client.post(reverse("cancelar_agendamento", args=[agendamento.pk]))
        self.assertEqual(response.status_code, 404)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, Agendamento.Status.AGENDADO)

    def test_outro_profissional_nao_pode_cancelar(self):
        agendamento = self.agendar()
        self.client.force_login(self.outro_prof)
        response = self.client.post(reverse("cancelar_agendamento", args=[agendamento.pk]))
        self.assertEqual(response.status_code, 404)

    def test_profissional_responsavel_e_recepcao_podem_cancelar(self):
        for usuario in (self.prof, self.recepcao):
            with self.subTest(usuario=usuario.nome):
                agendamento = self.agendar(hora=time(10) if usuario == self.prof else time(11))
                self.client.force_login(usuario)
                response = self.client.post(reverse("cancelar_agendamento", args=[agendamento.pk]))
                self.assertRedirects(response, reverse("inicio"))
                agendamento.refresh_from_db()
                self.assertEqual(agendamento.status, Agendamento.Status.CANCELADO)

    def test_cancelar_libera_horario_sala_e_equipamento(self):
        agendamento = self.agendar(sala=self.sala, recursos=[self.halteres])
        self.assertFalse(
            self.livre_para(self.cliente2, sala=self.sala, recursos=[self.halteres])
        )
        self.client.force_login(self.cliente)
        response = self.client.post(
            reverse("cancelar_agendamento", args=[agendamento.pk]), {"escopo": "sessao"}, follow=True
        )
        self.assertContains(response, "Agendamento cancelado.")
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, Agendamento.Status.CANCELADO)
        self.assertTrue(
            self.livre_para(self.cliente2, sala=self.sala, recursos=[self.halteres])
        )

    def test_nao_cancela_atendimento_passado(self):
        agendamento = self.agendar(dia=timezone.localdate() - timedelta(days=1))
        self.client.force_login(self.cliente)
        response = self.client.post(
            reverse("cancelar_agendamento", args=[agendamento.pk]), follow=True
        )
        self.assertContains(response, "não pode mais ser cancelado")
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, Agendamento.Status.AGENDADO)

    def _serie(self):
        recorrencia = Recorrencia.objects.create(padrao="Semanal", data_termino=self.dia + timedelta(days=14))
        sessoes = [
            self.agendar(dia=self.dia + timedelta(days=7 * semana), recorrencia=recorrencia,
                         sala=self.sala, recursos=[self.halteres])
            for semana in range(3)
        ]
        return recorrencia, sessoes

    def test_cancelamento_recorrente_somente_esta_sessao(self):
        _, (primeira, segunda, terceira) = self._serie()
        self.client.force_login(self.cliente)
        self.client.post(reverse("cancelar_agendamento", args=[segunda.pk]), {"escopo": "sessao"})
        for sessao, status in ((primeira, "agendado"), (segunda, "cancelado"), (terceira, "agendado")):
            sessao.refresh_from_db()
            self.assertEqual(sessao.status, status)
        self.assertTrue(
            self.livre_para(self.cliente2, dia=self.dia + timedelta(days=7),
                            sala=self.sala, recursos=[self.halteres])
        )

    def test_cancelamento_recorrente_toda_a_serie(self):
        _, sessoes = self._serie()
        self.client.force_login(self.cliente)
        response = self.client.post(
            reverse("cancelar_agendamento", args=[sessoes[1].pk]), {"escopo": "serie"}, follow=True
        )
        self.assertContains(response, "Série cancelada: 3 sessão(ões)")
        for semana, sessao in enumerate(sessoes):
            sessao.refresh_from_db()
            self.assertEqual(sessao.status, Agendamento.Status.CANCELADO)
            self.assertTrue(
                self.livre_para(self.cliente2, dia=self.dia + timedelta(days=7 * semana),
                                sala=self.sala, recursos=[self.halteres])
            )

    def test_cancelar_serie_preserva_sessoes_passadas_e_concluidas(self):
        recorrencia = Recorrencia.objects.create(padrao="Semanal", data_termino=self.dia)
        passada = self.agendar(dia=timezone.localdate() - timedelta(days=7), recorrencia=recorrencia,
                               status=Agendamento.Status.CONCLUIDO)
        futura = self.agendar(recorrencia=recorrencia)
        self.assertEqual(recorrencia.cancelar(), 1)
        passada.refresh_from_db()
        futura.refresh_from_db()
        self.assertEqual(passada.status, Agendamento.Status.CONCLUIDO)
        self.assertEqual(futura.status, Agendamento.Status.CANCELADO)

    def test_escopo_serie_sem_recorrencia_cancela_so_a_sessao(self):
        agendamento = self.agendar()
        outro = self.agendar(hora=time(11))
        self.client.force_login(self.cliente)
        self.client.post(reverse("cancelar_agendamento", args=[agendamento.pk]), {"escopo": "serie"})
        outro.refresh_from_db()
        self.assertEqual(outro.status, Agendamento.Status.AGENDADO)

    def test_template_agenda_cliente_contem_modal_e_botoes(self):
        self._serie()
        self.client.force_login(self.cliente)
        response = self.client.get(reverse("minha_agenda"))
        self.assertContains(response, 'id="modal-cancelamento"')
        self.assertContains(response, "data-cancelar")
        self.assertContains(response, 'data-recorrente="1"')
        self.assertContains(response, 'id="bloco-escopo-recorrencia"')
        self.assertContains(response, 'name="escopo" value="sessao"')
        self.assertContains(response, 'value="serie"')
        self.assertContains(response, 'id="modal-reagendamento"')
        self.assertContains(response, "Série recorrente")


class ReagendamentoAgendamentoTests(_BaseOperacaoAgenda):
    def setUp(self):
        super().setUp()
        self.agendamento = self.agendar(sala=self.sala, recursos=[self.halteres])
        self.url = reverse("reagendar_agendamento", args=[self.agendamento.pk])
        self.url_horarios = reverse("horarios_reagendamento", args=[self.agendamento.pk])
        self.client.force_login(self.cliente)

    def test_reagendar_libera_horario_antigo_e_reserva_o_novo_com_recursos(self):
        response = self.client.post(self.url, {"data": self.dia.isoformat(), "hora_inicio": "11:00"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["hora_inicio"], "11:00")
        self.assertEqual(response.json()["hora_fim"], "12:00")
        self.agendamento.refresh_from_db()
        self.assertEqual(self.agendamento.data_hora_inicio, _aware(self.dia, time(11)))
        self.assertEqual(self.agendamento.data_hora_fim, _aware(self.dia, time(12)))
        self.assertEqual(self.agendamento.status, Agendamento.Status.AGENDADO)
        self.assertEqual(self.agendamento.sala, self.sala)
        self.assertEqual(list(self.agendamento.recursos.all()), [self.halteres])

        horas = [timezone.localtime(h).time() for h in horarios_livres(self.prof, self.dia, 60)]
        self.assertIn(time(9), horas)
        self.assertNotIn(time(11), horas)
        self.assertTrue(
            self.livre_para(self.cliente2, hora=time(9), sala=self.sala, recursos=[self.halteres])
        )
        self.assertFalse(
            self.livre_para(self.cliente2, hora=time(11), sala=self.sala, recursos=[self.halteres])
        )

    def test_mensagem_de_sucesso_na_agenda(self):
        self.client.post(self.url, {"data": self.dia.isoformat(), "hora_inicio": "11:00"})
        response = self.client.get(reverse("minha_agenda"))
        self.assertContains(response, f"Atendimento remarcado para {self.dia:%d/%m/%Y} às 11:00.")

    def test_recusa_horario_em_conflito_e_mantem_o_original(self):
        self.agendar(cliente=self.cliente2, hora=time(11), sala=self.sala)
        response = self.client.post(self.url, {"data": self.dia.isoformat(), "hora_inicio": "11:00"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("O profissional já possui", response.json()["erro"])
        self.agendamento.refresh_from_db()
        self.assertEqual(self.agendamento.data_hora_inicio, _aware(self.dia, time(9)))

    def test_recusa_conflito_de_equipamento_com_outro_profissional(self):
        outro_servico = Servico.objects.create(
            profissional=self.outro_prof, nome="Consulta", tipo="Nutrição", duracao_minutos=60
        )
        self.agendar(cliente=self.cliente2, hora=time(14), profissional=self.outro_prof,
                     servico=outro_servico, recursos=[self.halteres])
        response = self.client.post(self.url, {"data": self.dia.isoformat(), "hora_inicio": "14:00"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Halteres", response.json()["erro"])

    def test_recusa_horario_fora_da_disponibilidade(self):
        response = self.client.post(self.url, {"data": self.dia.isoformat(), "hora_inicio": "18:00"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("fora da disponibilidade", response.json()["erro"])

    def test_recusa_mesmo_horario_e_horario_passado(self):
        response = self.client.post(self.url, {"data": self.dia.isoformat(), "hora_inicio": "09:00"})
        self.assertEqual(response.status_code, 400)
        ontem = timezone.localdate() - timedelta(days=1)
        response = self.client.post(self.url, {"data": ontem.isoformat(), "hora_inicio": "10:00"})
        self.assertEqual(response.status_code, 400)

    def test_dados_invalidos(self):
        for dados in ({}, {"data": "amanha", "hora_inicio": "10:00"}, {"data": self.dia.isoformat(), "hora_inicio": "25:99"}):
            with self.subTest(dados=dados):
                self.assertEqual(self.client.post(self.url, dados).status_code, 400)

    def test_nao_reagenda_cancelado(self):
        self.agendamento.status = Agendamento.Status.CANCELADO
        self.agendamento.save()
        response = self.client.post(self.url, {"data": self.dia.isoformat(), "hora_inicio": "11:00"})
        self.assertEqual(response.status_code, 400)

    def test_outro_cliente_nao_reagenda(self):
        self.client.force_login(self.cliente2)
        response = self.client.post(self.url, {"data": self.dia.isoformat(), "hora_inicio": "11:00"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get(self.url_horarios, {"data": self.dia.isoformat()}).status_code, 404)

    def test_exige_post(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_horarios_inclui_o_atual_e_respeita_ocupacoes(self):
        self.agendar(cliente=self.cliente2, hora=time(11))
        response = self.client.get(self.url_horarios, {"data": self.dia.isoformat()})
        self.assertEqual(response.status_code, 200)
        horarios = response.json()["horarios"]
        self.assertIn("09:00", horarios)
        self.assertIn("08:00", horarios)
        self.assertNotIn("10:30", horarios)
        self.assertNotIn("11:00", horarios)
        self.assertNotIn("17:30", horarios)
        self.assertEqual(response.json()["duracao_minutos"], 60)

    def test_horarios_descarta_sala_ocupada(self):
        Agendamento.objects.create(
            cliente=self.cliente2, profissional=self.outro_prof,
            servico=Servico.objects.create(profissional=self.outro_prof, nome="X", tipo="X", duracao_minutos=60),
            sala=self.sala, data_hora_inicio=_aware(self.dia, time(14)), data_hora_fim=_aware(self.dia, time(15)),
        )
        horarios = self.client.get(self.url_horarios, {"data": self.dia.isoformat()}).json()["horarios"]
        self.assertNotIn("14:00", horarios)
        self.assertIn("15:00", horarios)

    def test_horarios_valida_parametro_data(self):
        self.assertEqual(self.client.get(self.url_horarios).status_code, 400)
        self.assertEqual(self.client.get(self.url_horarios, {"data": "x"}).status_code, 400)


class AgendaClienteViewTests(_BaseOperacaoAgenda):
    def setUp(self):
        super().setUp()
        self.url = reverse("minha_agenda")
        self.base = timezone.localdate() + timedelta(days=10)

    def test_exige_autenticacao(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_exibe_apenas_atendimentos_do_cliente_autenticado(self):
        meu = self.agendar()
        alheio = self.agendar(cliente=self.cliente2, hora=time(14))
        self.client.force_login(self.cliente)
        agendamentos = list(self.client.get(self.url).context["agendamentos"])
        self.assertIn(meu, agendamentos)
        self.assertNotIn(alheio, agendamentos)

    def test_exibe_detalhes_do_atendimento(self):
        self.agendar(hora=time(16), sala=self.sala, status=Agendamento.Status.CONFIRMADO)
        self.client.force_login(self.cliente)
        response = self.client.get(self.url)
        self.assertContains(response, f"{self.dia:%d/%m/%Y} às 16:00")
        self.assertContains(response, "Treino")
        self.assertContains(response, "Prof Op")
        self.assertContains(response, "Sala Funcional")
        self.assertContains(response, "Confirmado")

    def test_filtro_por_periodo(self):
        ag1 = self.agendar(dia=self.base)
        ag2 = self.agendar(dia=self.base + timedelta(days=5))
        ag3 = self.agendar(dia=self.base + timedelta(days=15))
        self.client.force_login(self.cliente)

        def filtrar(**params):
            return list(self.client.get(self.url, params).context["agendamentos"])

        self.assertEqual(
            filtrar(data_inicio=(self.base + timedelta(days=1)).isoformat(),
                    data_fim=(self.base + timedelta(days=10)).isoformat()),
            [ag2],
        )
        self.assertEqual(filtrar(data_inicio=(self.base + timedelta(days=5)).isoformat()), [ag2, ag3])
        self.assertEqual(filtrar(data_fim=(self.base + timedelta(days=5)).isoformat()), [ag1, ag2])

    def test_filtro_com_formato_invalido_ignorado(self):
        agendamento = self.agendar()
        self.client.force_login(self.cliente)
        response = self.client.get(self.url, {"data_inicio": "data-invalida", "data_fim": "outra"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["agendamentos"]), [agendamento])

    def test_ordenacao_cronologica(self):
        ag2 = self.agendar(dia=self.base + timedelta(days=2))
        ag0 = self.agendar(dia=self.base)
        ag1 = self.agendar(dia=self.base + timedelta(days=1))
        self.client.force_login(self.cliente)
        self.assertEqual(list(self.client.get(self.url).context["agendamentos"]), [ag0, ag1, ag2])

    def test_mensagem_quando_vazio(self):
        self.client.force_login(self.cliente)
        self.assertContains(self.client.get(self.url), "Você ainda não tem agendamentos.")
        self.agendar()
        response = self.client.get(self.url, {"data_inicio": (self.dia + timedelta(days=1)).isoformat()})
        self.assertContains(response, "Nenhum atendimento encontrado para o período informado.")


# ---------------------------------------------------------------------------
# Etapa 4 da unificação: recorrência semanal (UC6, RF16, RN11, RN12).
# Adaptados de src/agenda/tests.py (RecorrenciaModelTests,
# RecorrenciaGeracaoOcorrenciasTests, NovoAgendamentoRecorrenciaViewTests e
# PreviaRecorrenciaViewTests).
# ---------------------------------------------------------------------------
def _proxima(dia_semana, semanas_a_frente=1):
    """Próxima data com o dia da semana pedido, a partir da semana que vem."""
    base = timezone.localdate() + timedelta(days=7 * semanas_a_frente)
    return base + timedelta(days=(dia_semana - base.weekday()) % 7)


class _BaseRecorrencia(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create_user(
            email="cli-rec@exemplo.com", password="Senha#Forte123", nome="Cliente Rec", papel="cliente"
        )
        self.cliente2 = Cliente.objects.create_user(
            email="cli2-rec@exemplo.com", password="Senha#Forte123", nome="Cliente Rec 2", papel="cliente"
        )
        self.prof = Profissional.objects.create_user(
            email="prof-rec@exemplo.com", password="Senha#Forte123", nome="Prof Rec",
            especialidade="Personal Trainer", papel="profissional",
        )
        self.outro_prof = Profissional.objects.create_user(
            email="prof2-rec@exemplo.com", password="Senha#Forte123", nome="Prof Rec 2",
            especialidade="Nutrição", papel="profissional",
        )
        for profissional in (self.prof, self.outro_prof):
            for dia in range(5):
                Disponibilidade.objects.create(
                    profissional=profissional, dia_semana=dia, hora_inicio=time(8), hora_fim=time(18)
                )
        self.servico = Servico.objects.create(
            profissional=self.prof, nome="Treino", tipo="Treinamento", duracao_minutos=60
        )
        self.servico_outro = Servico.objects.create(
            profissional=self.outro_prof, nome="Nutri", tipo="Nutrição", duracao_minutos=60
        )
        self.sala = Sala.objects.create(nome="Estúdio A", capacidade=4)
        self.maca = Recurso.objects.create(nome="Maca", exclusivo=True)
        self.segunda = _proxima(0)

    def recorrencia(self, **campos):
        dados = dict(
            cliente=self.cliente, profissional=self.prof, servico=self.servico,
            dias_semana=[0], data_inicio=self.segunda,
            data_termino=self.segunda + timedelta(days=14), hora_inicio=time(9),
        )
        dados.update(campos)
        return Recorrencia(**dados)

    def criar_serie(self, recursos=(), **campos):
        rec = self.recorrencia(**campos)
        rec.full_clean()
        rec.save()
        rec.recursos.set(recursos)
        rec.gerar_ocorrencias(recursos=list(recursos))
        return rec

    def ocupar(self, dia, hora=time(9), cliente=None, profissional=None, servico=None, **extra):
        inicio = _aware(dia, hora)
        agendamento = Agendamento.objects.create(
            cliente=cliente or self.cliente2,
            profissional=profissional or self.prof,
            servico=servico or self.servico,
            data_hora_inicio=inicio,
            data_hora_fim=inicio + timedelta(hours=1),
            **{k: v for k, v in extra.items() if k != "recursos"},
        )
        agendamento.recursos.set(extra.get("recursos", []))
        return agendamento

    def datas(self, rec):
        return [
            timezone.localtime(a.data_hora_inicio).date()
            for a in rec.agendamentos.order_by("data_hora_inicio")
        ]


class RecorrenciaModelTests(_BaseRecorrencia):
    def test_str_e_atributos_basicos(self):
        rec = self.recorrencia(dias_semana=[0, 2])
        rec.full_clean()
        self.assertEqual(rec.padrao, "Semanal")
        self.assertIn("Segunda-feira, Quarta-feira", str(rec))
        self.assertIn("09:00", str(rec))

    def test_validacao_dias_semana_vazio(self):
        with self.assertRaises(ValidationError) as erro:
            self.recorrencia(dias_semana=[]).clean()
        self.assertIn("dias_semana", erro.exception.message_dict)

    def test_validacao_dia_invalido(self):
        with self.assertRaises(ValidationError):
            self.recorrencia(dias_semana=[7]).clean()

    def test_validacao_data_termino_anterior_a_data_inicio(self):
        with self.assertRaisesMessage(ValidationError, "A data final deve ser posterior"):
            self.recorrencia(data_termino=self.segunda - timedelta(days=1)).clean()

    def test_validacao_periodo_sem_dias_correspondentes(self):
        with self.assertRaisesMessage(ValidationError, "não contempla nenhum dos dias"):
            self.recorrencia(dias_semana=[0], data_inicio=self.segunda + timedelta(days=1),
                             data_termino=self.segunda + timedelta(days=2)).clean()

    def test_validacao_periodo_maximo(self):
        with self.assertRaisesMessage(ValidationError, "no máximo um ano"):
            self.recorrencia(data_termino=self.segunda + timedelta(days=400)).clean()

    def test_campos_obrigatorios(self):
        with self.assertRaises(ValidationError) as erro:
            Recorrencia(data_termino=self.segunda, dias_semana=[0]).clean()
        for campo in ("cliente", "profissional", "servico", "data_inicio", "hora_inicio"):
            self.assertIn(campo, erro.exception.message_dict)

    def test_normalizacao_dias_semana(self):
        rec = self.recorrencia(dias_semana="2, 0, 2")
        rec.clean()
        self.assertEqual(rec.dias_semana, [0, 2])

    def test_datas_do_periodo(self):
        rec = self.recorrencia(dias_semana=[0, 2])
        self.assertEqual(
            rec.datas_do_periodo(),
            [self.segunda, self.segunda + timedelta(days=2), self.segunda + timedelta(days=7),
             self.segunda + timedelta(days=9), self.segunda + timedelta(days=14)],
        )

    def test_recorrencia_antiga_sem_vinculos_continua_valida_no_banco(self):
        rec = Recorrencia.objects.create(padrao="Semanal", data_termino=self.segunda)
        self.assertIsNone(rec.cliente)
        self.assertEqual(rec.dias_semana, [])


class RecorrenciaGeracaoOcorrenciasTests(_BaseRecorrencia):
    def test_gera_todas_as_ocorrencias_com_sala_e_equipamento(self):
        rec = self.criar_serie(recursos=[self.maca], dias_semana=[0, 2], sala=self.sala)
        self.assertEqual(
            self.datas(rec),
            [self.segunda, self.segunda + timedelta(days=2), self.segunda + timedelta(days=7),
             self.segunda + timedelta(days=9), self.segunda + timedelta(days=14)],
        )
        for agendamento in rec.agendamentos.all():
            self.assertEqual(timezone.localtime(agendamento.data_hora_inicio).time(), time(9))
            self.assertEqual(timezone.localtime(agendamento.data_hora_fim).time(), time(10))
            self.assertEqual(agendamento.cliente_id, self.cliente.pk)
            self.assertEqual(agendamento.profissional_id, self.prof.pk)
            self.assertEqual(agendamento.servico, self.servico)
            self.assertEqual(agendamento.sala, self.sala)
            self.assertEqual(list(agendamento.recursos.all()), [self.maca])
            self.assertEqual(agendamento.status, Agendamento.Status.AGENDADO)

    def test_gerar_ocorrencias_sem_salvar(self):
        rec = self.recorrencia()
        validas, conflitos = rec.gerar_ocorrencias(salvar=False)
        self.assertEqual(len(validas), 3)
        self.assertEqual(conflitos, [])
        self.assertIsNone(rec.pk)
        self.assertEqual(Agendamento.objects.count(), 0)

    def test_rn11_e_rn12_conflito_individual_descartado_sem_sobrescrever(self):
        previo = self.ocupar(self.segunda + timedelta(days=7))
        rec = self.criar_serie()
        self.assertEqual(self.datas(rec), [self.segunda, self.segunda + timedelta(days=14)])
        previo.refresh_from_db()
        self.assertEqual(previo.cliente_id, self.cliente2.pk)
        self.assertIsNone(previo.recorrencia)

    def test_conflito_com_bloqueio_descartado(self):
        quarta = self.segunda + timedelta(days=2)
        Bloqueio.objects.create(
            profissional=self.prof, inicio=_aware(quarta, time(9)),
            fim=_aware(quarta, time(11)), motivo="Reunião",
        )
        rec = self.criar_serie(dias_semana=[0, 2], data_termino=self.segunda + timedelta(days=7))
        datas = self.datas(rec)
        self.assertNotIn(quarta, datas)
        self.assertIn(self.segunda, datas)
        self.assertIn(self.segunda + timedelta(days=7), datas)

    def test_conflito_com_agendamento_do_cliente_descartado(self):
        self.ocupar(self.segunda + timedelta(days=7), cliente=self.cliente,
                    profissional=self.outro_prof, servico=self.servico_outro)
        rec = self.criar_serie()
        self.assertEqual(self.datas(rec), [self.segunda, self.segunda + timedelta(days=14)])

    def test_conflito_de_sala_descartado(self):
        self.ocupar(self.segunda + timedelta(days=7), profissional=self.outro_prof,
                    servico=self.servico_outro, sala=self.sala)
        rec = self.criar_serie(sala=self.sala)
        self.assertEqual(self.datas(rec), [self.segunda, self.segunda + timedelta(days=14)])

    def test_conflito_de_equipamento_exclusivo_descartado(self):
        self.ocupar(self.segunda + timedelta(days=14), profissional=self.outro_prof,
                    servico=self.servico_outro, recursos=[self.maca])
        rec = self.criar_serie(recursos=[self.maca])
        self.assertEqual(self.datas(rec), [self.segunda, self.segunda + timedelta(days=7)])

    def test_data_ja_passada_e_descartada(self):
        rec = self.recorrencia(
            dias_semana=[0, 1, 2, 3, 4, 5, 6],
            data_inicio=timezone.localdate() - timedelta(days=2),
            data_termino=timezone.localdate() + timedelta(days=2),
        )
        validas, conflitos = rec.avaliar_ocorrencias()
        self.assertTrue(any("já passou" in motivo for _, motivo in conflitos))
        for agendamento in validas:
            self.assertGreater(agendamento.data_hora_inicio, timezone.now())

    def test_todas_ocorrencias_em_conflito_lanca_validacao(self):
        Bloqueio.objects.create(
            profissional=self.prof, inicio=_aware(self.segunda, time(8)),
            fim=_aware(self.segunda, time(12)), motivo="Curso",
        )
        rec = self.recorrencia(data_termino=self.segunda)
        rec.save()
        with self.assertRaisesMessage(ValidationError, "todas as datas do período"):
            rec.gerar_ocorrencias()
        self.assertEqual(Agendamento.objects.count(), 0)

    def test_cancelar_recorrencia(self):
        rec = self.criar_serie(data_termino=self.segunda + timedelta(days=7))
        self.assertEqual(rec.agendamentos.filter(status=Agendamento.Status.AGENDADO).count(), 2)
        self.assertEqual(rec.cancelar(), 2)
        self.assertEqual(rec.agendamentos.filter(status=Agendamento.Status.CANCELADO).count(), 2)


class NovoAgendamentoRecorrenciaViewTests(_BaseRecorrencia):
    def setUp(self):
        super().setUp()
        self.url = reverse("novo_agendamento", args=[self.servico.pk])
        self.client.force_login(self.cliente)
        self.horario = self._primeiro_horario()

    def _primeiro_horario(self):
        valor = self.client.get(self.url).context["form"].fields["horario"].choices[0][0]
        return datetime.fromisoformat(valor)

    def post(self, **extra):
        dados = {"horario": self.horario.isoformat(), "repetir_semanal": "on"}
        dados.update(extra)
        return self.client.post(self.url, dados)

    def test_tela_contem_campos_de_recorrencia_e_modal(self):
        response = self.client.get(self.url)
        for trecho in ("repetir_semanal", "dias_semana", "data_termino",
                       'id="modal-recorrencia"', 'id="metrica-total"', 'id="metrica-validas"',
                       'id="metrica-conflitos"', 'id="tabela-sessoes-recorrencia"',
                       'id="botao-confirmar-recorrencia"', 'id="botao-ver-previa"'):
            self.assertContains(response, trecho)

    def test_cria_serie_com_sucesso(self):
        dia = timezone.localtime(self.horario).date()
        response = self.post(dias_semana=[str(dia.weekday())],
                             data_termino=(dia + timedelta(days=14)).isoformat())
        self.assertRedirects(response, reverse("minha_agenda"))
        rec = Recorrencia.objects.get()
        self.assertEqual(rec.cliente_id, self.cliente.pk)
        self.assertEqual(rec.agendamentos.count(), 3)
        self.assertEqual(rec.hora_inicio, timezone.localtime(self.horario).time())

    def test_sem_marcar_dias_assume_dia_do_primeiro_horario(self):
        dia = timezone.localtime(self.horario).date()
        self.post(data_termino=(dia + timedelta(days=14)).isoformat())
        rec = Recorrencia.objects.get()
        self.assertEqual(rec.dias_semana, [dia.weekday()])
        self.assertEqual(rec.agendamentos.count(), 3)

    def test_conflito_parcial_cria_as_validas_e_avisa(self):
        dia = timezone.localtime(self.horario).date()
        self.ocupar(dia + timedelta(days=7), hora=timezone.localtime(self.horario).time())
        response = self.client.post(
            self.url,
            {"horario": self.horario.isoformat(), "repetir_semanal": "on",
             "data_termino": (dia + timedelta(days=14)).isoformat()},
            follow=True,
        )
        rec = Recorrencia.objects.get()
        self.assertEqual(rec.agendamentos.count(), 2)
        self.assertContains(response, "descartadas")

    def test_conflito_total_nao_cria_serie(self):
        dia = timezone.localtime(self.horario).date()
        self.ocupar(dia, hora=timezone.localtime(self.horario).time(), cliente=self.cliente,
                    profissional=self.outro_prof, servico=self.servico_outro)
        response = self.post(data_termino=dia.isoformat())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Recorrencia.objects.count(), 0)
        self.assertContains(response, "apresentaram conflito")

    def test_exige_data_de_termino(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Informe até quando o agendamento deve se repetir.")
        self.assertEqual(Recorrencia.objects.count(), 0)

    def test_sem_repetir_continua_criando_agendamento_avulso(self):
        response = self.client.post(self.url, {"horario": self.horario.isoformat()})
        self.assertRedirects(response, reverse("profissionais"))
        self.assertEqual(Recorrencia.objects.count(), 0)
        self.assertEqual(Agendamento.objects.count(), 1)


class PreviaRecorrenciaViewTests(_BaseRecorrencia):
    def setUp(self):
        super().setUp()
        self.url = reverse("previa_recorrencia", args=[self.servico.pk])
        self.url_tela = reverse("novo_agendamento", args=[self.servico.pk])

    def _horario(self):
        self.client.force_login(self.cliente)
        valor = self.client.get(self.url_tela).context["form"].fields["horario"].choices[0][0]
        return datetime.fromisoformat(valor)

    def test_exige_login(self):
        self.assertEqual(self.client.post(self.url, {}).status_code, 302)

    def test_metodo_get_recusado(self):
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_dados_invalidos_retornam_400(self):
        self.client.force_login(self.cliente)
        response = self.client.post(self.url, {"repetir_semanal": "on"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["valido"])

    def test_data_termino_anterior_retorna_400(self):
        horario = self._horario()
        dia = timezone.localtime(horario).date()
        response = self.client.post(self.url, {
            "horario": horario.isoformat(), "repetir_semanal": "on",
            "data_termino": (dia - timedelta(days=1)).isoformat(),
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("A data final deve ser posterior", response.json()["erro"])

    def test_calcula_datas_e_total_de_sessoes(self):
        horario = self._horario()
        dia = timezone.localtime(horario).date()
        response = self.client.post(self.url, {
            "horario": horario.isoformat(), "repetir_semanal": "on",
            "dias_semana": [str(dia.weekday())],
            "data_termino": (dia + timedelta(days=14)).isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        dados = response.json()
        self.assertTrue(dados["valido"])
        self.assertEqual((dados["total"], dados["total_validas"], dados["total_conflitos"]), (3, 3, 0))
        for sessao in dados["sessoes"]:
            self.assertFalse(sessao["conflito"])
            self.assertEqual(sessao["status"], "Disponível")
        self.assertEqual(Recorrencia.objects.count(), 0)
        self.assertEqual(Agendamento.objects.count(), 0)

    def test_identifica_conflito_com_motivo(self):
        horario = self._horario()
        dia = timezone.localtime(horario).date()
        self.ocupar(dia + timedelta(days=7), hora=timezone.localtime(horario).time())
        response = self.client.post(self.url, {
            "horario": horario.isoformat(), "repetir_semanal": "on",
            "data_termino": (dia + timedelta(days=14)).isoformat(),
        })
        dados = response.json()
        self.assertEqual((dados["total"], dados["total_validas"], dados["total_conflitos"]), (3, 2, 1))
        sessao = [s for s in dados["sessoes"] if s["data"] == (dia + timedelta(days=7)).isoformat()][0]
        self.assertTrue(sessao["conflito"])
        self.assertEqual(sessao["status"], "Conflito")
        self.assertIn("já possui um agendamento", sessao["motivo"])

    def test_profissional_nao_gera_previa(self):
        horario = self._horario()
        self.client.force_login(self.prof)
        response = self.client.post(self.url, {
            "horario": horario.isoformat(), "repetir_semanal": "on",
            "data_termino": timezone.localtime(horario).date().isoformat(),
        })
        self.assertEqual(response.status_code, 403)
