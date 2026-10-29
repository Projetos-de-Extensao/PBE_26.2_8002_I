from django import forms
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, TemplateView, UpdateView

from agendamento.models import (
    Agendamento,
    Perfil,
    Profissional,
    Recurso,
    Sala,
    Servico,
    Usuario,
)


class AdministradorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy("login")
    raise_exception = True

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect_to_login(
                self.request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )
        return super().handle_no_permission()

    def test_func(self):
        return (
            self.request.user.is_active
            and self.request.user.is_staff
            and Perfil.objects.filter(
                usuario_id=self.request.user.pk,
                papel=Perfil.Papel.ADMINISTRADOR,
            ).exists()
        )


class ProfissionalForm(forms.ModelForm):
    senha = forms.CharField(
        label=_("Senha"),
        strip=False,
        required=False,
        widget=forms.PasswordInput,
    )
    confirmar_senha = forms.CharField(
        label=_("Confirme a senha"),
        strip=False,
        required=False,
        widget=forms.PasswordInput,
    )

    class Meta:
        model = Profissional
        fields = (
            "nome",
            "email",
            "telefone",
            "especialidade",
            "modalidade",
            "formacao",
            "apresentacao",
            "is_active",
        )
        labels = {
            "nome": _("Nome"),
            "email": _("E-mail"),
            "telefone": _("Telefone"),
            "especialidade": _("Especialidade"),
            "modalidade": _("Modalidade de atendimento"),
            "formacao": _("Formação"),
            "apresentacao": _("Apresentação"),
            "is_active": _("Profissional ativo"),
        }

    def clean(self):
        cleaned_data = super().clean()
        senha = cleaned_data.get("senha")
        confirmar_senha = cleaned_data.get("confirmar_senha")

        if not self.instance.pk and not senha:
            self.add_error("senha", _("Informe uma senha para o profissional."))
        if senha and senha != confirmar_senha:
            self.add_error("confirmar_senha", _("As senhas não coincidem."))
        if senha:
            try:
                validate_password(senha, user=self.instance)
            except ValidationError as error:
                self.add_error("senha", error)
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["senha"].help_text = _(
                "Deixe em branco para manter a senha atual."
            )
        else:
            self.fields["senha"].required = True
            self.fields["confirmar_senha"].required = True

    def save(self, commit=True):
        profissional = super().save(commit=False)
        senha = self.cleaned_data.get("senha")
        if senha:
            profissional.set_password(senha)
        if commit:
            profissional.save()
            self.save_m2m()
        return profissional


class ServicoForm(forms.ModelForm):
    class Meta:
        model = Servico
        fields = ("profissional", "nome", "tipo", "duracao_minutos")
        labels = {
            "profissional": _("Profissional"),
            "nome": _("Nome do serviço"),
            "tipo": _("Tipo de serviço"),
            "duracao_minutos": _("Duração (minutos)"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["profissional"].queryset = Profissional.objects.order_by("nome")


class SalaForm(forms.ModelForm):
    class Meta:
        model = Sala
        fields = ("nome", "capacidade")
        labels = {"nome": _("Nome da sala"), "capacidade": _("Capacidade")}


class RecursoForm(forms.ModelForm):
    class Meta:
        model = Recurso
        fields = ("nome", "exclusivo")
        labels = {
            "nome": _("Nome do equipamento"),
            "exclusivo": _("Uso exclusivo"),
        }


class AdministracaoView(AdministradorRequiredMixin, TemplateView):
    template_name = "admin/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoje = timezone.localdate()
        agendamentos_ativos_hoje = (
            Agendamento.objects.filter(data_hora_inicio__date=hoje)
            .exclude(status=Agendamento.Status.CANCELADO)
            .select_related("cliente", "profissional", "servico", "sala")
            .prefetch_related("recursos")
        )
        context.update(
            {
                "hoje": hoje,
                "profissionais": Profissional.objects.order_by("nome"),
                "servicos": Servico.objects.select_related("profissional"),
                "salas": Sala.objects.prefetch_related(
                    Prefetch(
                        "agendamentos",
                        queryset=agendamentos_ativos_hoje,
                    )
                ),
                "recursos": Recurso.objects.prefetch_related(
                    Prefetch(
                        "agendamentos",
                        queryset=agendamentos_ativos_hoje,
                    )
                ),
                "usuarios": Usuario.objects.select_related("perfil"),
                "agendamentos_hoje": (
                    Agendamento.objects.filter(data_hora_inicio__date=hoje)
                    .select_related("cliente", "profissional", "servico", "sala")
                    .order_by("data_hora_inicio")
                ),
                "total_profissionais": Profissional.objects.count(),
                "total_servicos": Servico.objects.count(),
                "total_salas": Sala.objects.count(),
                "total_recursos": Recurso.objects.count(),
                "papeis": (
                    (
                        Perfil.Papel.CLIENTE.label,
                        _("Agenda e dados pessoais próprios"),
                    ),
                    (
                        Perfil.Papel.PROFISSIONAL.label,
                        _("Perfil profissional, disponibilidade e agenda própria"),
                    ),
                    (
                        Perfil.Papel.RECEPCIONISTA.label,
                        _("Operações de agenda permitidas, sem gestão administrativa"),
                    ),
                    (
                        Perfil.Papel.ADMINISTRADOR.label,
                        _("Usuários, profissionais, serviços, espaços e recursos"),
                    ),
                ),
            }
        )
        return context


class AdministracaoFormMixin(AdministradorRequiredMixin):
    template_name = "admin/manage_form.html"
    success_url = reverse_lazy("administracao")
    titulo = ""
    mensagem_sucesso = _("Alterações salvas com sucesso.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = self.titulo
        return context

    def form_valid(self, form):
        messages.success(self.request, self.mensagem_sucesso)
        return super().form_valid(form)


class AdministracaoCreateView(AdministracaoFormMixin, CreateView):
    pass


class AdministracaoUpdateView(AdministracaoFormMixin, UpdateView):
    pass


class ProfissionalCreateView(AdministracaoCreateView):
    model = Profissional
    form_class = ProfissionalForm
    titulo = _("Cadastrar profissional")
    mensagem_sucesso = _("Profissional cadastrado com sucesso.")


class ProfissionalUpdateView(AdministracaoUpdateView):
    model = Profissional
    form_class = ProfissionalForm
    titulo = _("Editar profissional")
    mensagem_sucesso = _("Profissional atualizado com sucesso.")


class ServicoCreateView(AdministracaoCreateView):
    model = Servico
    form_class = ServicoForm
    titulo = _("Cadastrar serviço")
    mensagem_sucesso = _("Serviço cadastrado com sucesso.")


class ServicoUpdateView(AdministracaoUpdateView):
    model = Servico
    form_class = ServicoForm
    titulo = _("Editar serviço")
    mensagem_sucesso = _("Serviço atualizado com sucesso.")


class SalaCreateView(AdministracaoCreateView):
    model = Sala
    form_class = SalaForm
    titulo = _("Cadastrar sala")
    mensagem_sucesso = _("Sala cadastrada com sucesso.")


class SalaUpdateView(AdministracaoUpdateView):
    model = Sala
    form_class = SalaForm
    titulo = _("Editar sala")
    mensagem_sucesso = _("Sala atualizada com sucesso.")


class RecursoCreateView(AdministracaoCreateView):
    model = Recurso
    form_class = RecursoForm
    titulo = _("Cadastrar recurso")
    mensagem_sucesso = _("Recurso cadastrado com sucesso.")


class RecursoUpdateView(AdministracaoUpdateView):
    model = Recurso
    form_class = RecursoForm
    titulo = _("Editar recurso")
    mensagem_sucesso = _("Recurso atualizado com sucesso.")
