from django import forms
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView

from agendamento.models import Papel, Usuario


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label=_("E-mail"),
        widget=forms.EmailInput(
            attrs={"autofocus": True, "autocomplete": "email"}
        ),
    )
    password = forms.CharField(
        label=_("Senha"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password"}
        ),
    )
    error_messages = {
        "invalid_login": _("E-mail ou senha inválidos. Verifique os dados e tente novamente."),
        "inactive": _("Esta conta está inativa."),
    }


class LoginView(DjangoLoginView):
    authentication_form = EmailAuthenticationForm
    template_name = "agendamento/login.html"


class CadastroForm(forms.Form):
    nome = forms.CharField(label=_("Nome"), max_length=150)
    email = forms.EmailField(
        label=_("E-mail"),
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    senha = forms.CharField(
        label=_("Senha"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    confirmar_senha = forms.CharField(
        label=_("Confirme a senha"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("Já existe uma conta com este e-mail."))
        return email

    def clean(self):
        cleaned_data = super().clean()
        senha = cleaned_data.get("senha")
        confirmar_senha = cleaned_data.get("confirmar_senha")
        if senha and confirmar_senha and senha != confirmar_senha:
            self.add_error("confirmar_senha", _("As senhas não coincidem."))
        if senha and cleaned_data.get("email") and cleaned_data.get("nome"):
            usuario = Usuario(
                email=cleaned_data["email"],
                nome=cleaned_data["nome"],
            )
            try:
                validate_password(senha, user=usuario)
            except ValidationError as error:
                self.add_error("senha", error)
        return cleaned_data

    @transaction.atomic
    def save(self):
        papel, _ = Papel.objects.get_or_create(nome="Cliente")
        return Usuario.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["senha"],
            nome=self.cleaned_data["nome"],
            papel=papel,
        )


class CadastroView(FormView):
    form_class = CadastroForm
    template_name = "agendamento/cadastro.html"
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request,
            _("Conta criada com sucesso. Entre com seu e-mail e senha."),
        )
        return super().form_valid(form)
