import re

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from agendamento.models import Papel, Usuario


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
    def test_cadastra_cliente_com_senha_valida(self):
        response = self.client.post(
            reverse("cadastro"),
            {
                "nome": "Nova Cliente",
                "email": "NOVA@EXEMPLO.COM",
                "senha": "Nuvem#Roxa39!Chuva",
                "confirmar_senha": "Nuvem#Roxa39!Chuva",
            },
            follow=True,
        )

        usuario = Usuario.objects.get(email="nova@exemplo.com")
        self.assertEqual(usuario.nome, "Nova Cliente")
        self.assertEqual(usuario.papel.nome, "Cliente")
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
                "senha": "Nuvem#Roxa39!Chuva",
                "confirmar_senha": "OutraSenha#123",
            },
        )

        self.assertContains(response, "As senhas não coincidem.")
        self.assertFalse(Usuario.objects.exists())


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
