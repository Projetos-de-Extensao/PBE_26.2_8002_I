from datetime import datetime, time, timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, FormView, ListView

from agendamento.models import (
    Agendamento,
    Bloqueio,
    Cliente,
    Disponibilidade,
    Perfil,
    Profissional,
    Recepcionista,
    Servico,
    Usuario,
)


def _acesso_negado(request):
    return render(request, "agendamento/acesso_negado.html", status=403)


def _cliente_para_usuario(usuario):
    cliente = Cliente.objects.filter(pk=usuario.pk).first()
    if cliente is not None:
        return cliente

    cliente = Cliente(
        usuario_ptr=usuario,
        password=usuario.password,
        last_login=usuario.last_login,
        is_superuser=usuario.is_superuser,
        first_name=usuario.first_name,
        last_name=usuario.last_name,
        is_staff=usuario.is_staff,
        is_active=usuario.is_active,
        date_joined=usuario.date_joined,
        email=usuario.email,
        nome=usuario.nome,
    )
    cliente.save()
    return cliente


def _proximos_horarios(profissional, servico, quantidade=5):
    agora = timezone.localtime()
    hoje = timezone.localdate()
    ultimo_dia = hoje + timedelta(days=30)
    disponibilidades = list(
        profissional.disponibilidades.all()
    )
    agendamentos = list(
        Agendamento.objects.filter(
            profissional=profissional,
            data_hora_inicio__lt=timezone.make_aware(
                datetime.combine(ultimo_dia + timedelta(days=1), time.min)
            ),
            data_hora_fim__gt=agora,
        )
        .exclude(status=Agendamento.Status.CANCELADO)
        .only("data_hora_inicio", "data_hora_fim")
    )
    bloqueios = list(
        Bloqueio.objects.filter(
            profissional=profissional,
            inicio__lt=timezone.make_aware(
                datetime.combine(ultimo_dia + timedelta(days=1), time.min)
            ),
            fim__gt=agora,
        ).only("inicio", "fim")
    )
    duracao = timedelta(minutes=servico.duracao_minutos)
    horarios = []

    for dias_a_frente in range(31):
        data = hoje + timedelta(days=dias_a_frente)
        for disponibilidade in disponibilidades:
            if disponibilidade.dia_semana != data.weekday():
                continue

            inicio = timezone.make_aware(
                datetime.combine(data, disponibilidade.hora_inicio)
            )
            fim_disponivel = timezone.make_aware(
                datetime.combine(data, disponibilidade.hora_fim)
            )
            while inicio + duracao <= fim_disponivel and len(horarios) < quantidade:
                fim = inicio + duracao
                ocupado = any(
                    agendamento.data_hora_inicio < fim
                    and agendamento.data_hora_fim > inicio
                    for agendamento in agendamentos
                ) or any(
                    bloqueio.inicio < fim and bloqueio.fim > inicio
                    for bloqueio in bloqueios
                )
                if inicio >= agora and not ocupado:
                    horarios.append(inicio)
                inicio += timedelta(minutes=30)

            if len(horarios) >= quantidade:
                break
        if len(horarios) >= quantidade:
            break

    return horarios


def _horario_disponivel(profissional, servico, inicio):
    agora = timezone.now()
    fim = inicio + timedelta(minutes=servico.duracao_minutos)
    dentro_da_disponibilidade = profissional.disponibilidades.filter(
        dia_semana=inicio.weekday(),
        hora_inicio__lte=inicio.time(),
        hora_fim__gte=fim.time(),
    ).exists()
    if inicio < agora or not dentro_da_disponibilidade:
        return False

    agendado = (
        Agendamento.objects.filter(
            profissional=profissional,
            data_hora_inicio__lt=fim,
            data_hora_fim__gt=inicio,
        )
        .exclude(status=Agendamento.Status.CANCELADO)
        .exists()
    )
    bloqueado = Bloqueio.objects.filter(
        profissional=profissional,
        inicio__lt=fim,
        fim__gt=inicio,
    ).exists()
    return not agendado and not bloqueado


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
    nome = forms.CharField(label=_("Nome completo"), max_length=150)
    email = forms.EmailField(
        label=_("E-mail"),
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    papel = forms.ChoiceField(
        label=_("Tipo de usuário"),
        choices=(
            (Perfil.Papel.CLIENTE, _("Cliente")),
            (Perfil.Papel.PROFISSIONAL, _("Profissional")),
            (Perfil.Papel.RECEPCIONISTA, _("Recepcionista")),
        ),
        initial=Perfil.Papel.CLIENTE,
    )
    especialidade = forms.CharField(
        label=_("Especialidade"),
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "organization-title"}),
    )
    modalidade = forms.ChoiceField(
        label=_("Modalidade de atendimento"),
        choices=Profissional.Modalidade.choices,
        required=False,
        initial=Profissional.Modalidade.PRESENCIAL,
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
        if (
            cleaned_data.get("papel") == Perfil.Papel.PROFISSIONAL
            and not cleaned_data.get("especialidade", "").strip()
        ):
            self.add_error(
                "especialidade",
                _("Informe sua especialidade profissional."),
            )
        if (
            cleaned_data.get("papel") == Perfil.Papel.PROFISSIONAL
            and not cleaned_data.get("modalidade")
        ):
            self.add_error(
                "modalidade",
                _("Informe a modalidade de atendimento."),
            )
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
        papel = self.cleaned_data["papel"]
        tipo_usuario = {
            Perfil.Papel.CLIENTE: Cliente,
            Perfil.Papel.PROFISSIONAL: Profissional,
            Perfil.Papel.RECEPCIONISTA: Recepcionista,
        }[papel]
        extra_fields = {}
        if papel == Perfil.Papel.PROFISSIONAL:
            extra_fields["especialidade"] = self.cleaned_data[
                "especialidade"
            ].strip()
            extra_fields["modalidade"] = self.cleaned_data["modalidade"]
        return tipo_usuario.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["senha"],
            nome=self.cleaned_data["nome"],
            papel=papel,
            **extra_fields,
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


class ProfissionalListView(ListView):
    model = Profissional
    context_object_name = "profissionais"
    template_name = "agendamento/profissional_list.html"

    def get_queryset(self):
        queryset = Profissional.objects.filter(is_active=True).prefetch_related(
            "servicos"
        )
        especialidade = self.request.GET.get("especialidade", "").strip()
        servico = self.request.GET.get("servico", "").strip()
        modalidade = self.request.GET.get("modalidade", "").strip()

        if especialidade:
            queryset = queryset.filter(especialidade__iexact=especialidade)
        if servico:
            queryset = queryset.filter(
                servicos__nome__iexact=servico
            ).distinct()
        if modalidade:
            queryset = queryset.filter(modalidade=modalidade)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profissionais_ativos = Profissional.objects.filter(is_active=True)
        context["especialidades"] = (
            profissionais_ativos.order_by("especialidade")
            .values_list("especialidade", flat=True)
            .distinct()
        )
        context["servicos_disponiveis"] = (
            Servico.objects.filter(profissional__is_active=True)
            .order_by("nome")
            .values_list("nome", flat=True)
            .distinct()
        )
        context["modalidades"] = Profissional.Modalidade.choices
        context["filtros"] = {
            "especialidade": self.request.GET.get("especialidade", "").strip(),
            "servico": self.request.GET.get("servico", "").strip(),
            "modalidade": self.request.GET.get("modalidade", "").strip(),
        }
        return context


class ProfissionalDetailView(DetailView):
    model = Profissional
    context_object_name = "profissional"
    template_name = "agendamento/profissional_detail.html"
    queryset = Profissional.objects.filter(is_active=True).prefetch_related(
        "servicos",
        "disponibilidades",
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        servicos = context["profissional"].servicos.all()
        for servico in servicos:
            servico.proximos_horarios = _proximos_horarios(
                context["profissional"],
                servico,
            )
        context["servicos"] = servicos
        return context


class AgendamentoForm(forms.Form):
    horario = forms.ChoiceField(
        label=_("Próximo horário disponível"),
        choices=(),
        error_messages={
            "invalid_choice": _(
                "Este horário não está mais disponível. Atualize e escolha outro."
            ),
        },
        widget=forms.Select(attrs={"autocomplete": "off"}),
    )

    def __init__(self, *args, horarios, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["horario"].choices = [
            (
                horario.isoformat(),
                timezone.localtime(horario).strftime("%d/%m/%Y às %H:%M"),
            )
            for horario in horarios
        ]


class NovoAgendamentoView(LoginRequiredMixin, FormView):
    form_class = AgendamentoForm
    template_name = "agendamento/novo_agendamento.html"
    success_url = reverse_lazy("profissionais")

    def dispatch(self, request, *args, **kwargs):
        self.servico = get_object_or_404(
            Servico.objects.select_related("profissional"),
            pk=kwargs["servico_id"],
            profissional__is_active=True,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_horarios(self):
        return _proximos_horarios(self.servico.profissional, self.servico)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["horarios"] = self.get_horarios()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["servico"] = self.servico
        context["profissional"] = self.servico.profissional
        return context

    def form_valid(self, form):
        inicio = datetime.fromisoformat(form.cleaned_data["horario"])
        if not Perfil.objects.filter(
            usuario_id=self.request.user.pk,
            papel=Perfil.Papel.CLIENTE,
        ).exists():
            return _acesso_negado(self.request)
        cliente = _cliente_para_usuario(self.request.user)

        with transaction.atomic():
            profissional = Profissional.objects.select_for_update().get(
                pk=self.servico.profissional_id
            )
            servico = Servico.objects.get(
                pk=self.servico.pk,
                profissional=profissional,
            )
            if not _horario_disponivel(profissional, servico, inicio):
                form.add_error(
                    "horario",
                    _("Este horário não está mais disponível. Escolha outro."),
                )
                return self.form_invalid(form)

            agendamento = Agendamento(
                cliente=cliente,
                profissional=profissional,
                servico=servico,
                data_hora_inicio=inicio,
                data_hora_fim=inicio
                + timedelta(minutes=servico.duracao_minutos),
            )
            if agendamento.verificar_conflito():
                form.add_error(
                    "horario",
                    _("Este horário não está mais disponível. Escolha outro."),
                )
                return self.form_invalid(form)
            agendamento.save()

        messages.success(self.request, _("Agendamento confirmado com sucesso."))
        return super().form_valid(form)


class ClienteRoleRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not Perfil.objects.filter(
            usuario_id=request.user.pk,
            papel=Perfil.Papel.CLIENTE,
        ).exists():
            return _acesso_negado(request)
        self.cliente = _cliente_para_usuario(request.user)
        return super().dispatch(request, *args, **kwargs)


class AgendaClienteView(ClienteRoleRequiredMixin, ListView):
    model = Agendamento
    context_object_name = "agendamentos"
    template_name = "agendamento/minha_agenda.html"

    def get_queryset(self):
        return (
            Agendamento.objects.filter(cliente=self.cliente)
            .select_related("servico", "profissional", "sala")
            .order_by("data_hora_inicio")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["now"] = timezone.now()
        return context


class CancelarAgendamentoView(ClienteRoleRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        agendamento = get_object_or_404(
            Agendamento,
            pk=kwargs["pk"],
            cliente=self.cliente,
        )
        if (
            agendamento.status
            in (Agendamento.Status.CANCELADO, Agendamento.Status.CONCLUIDO)
            or agendamento.data_hora_inicio <= timezone.now()
        ):
            messages.error(
                request,
                _("Este agendamento não pode mais ser cancelado."),
            )
        else:
            agendamento.status = Agendamento.Status.CANCELADO
            agendamento.save(update_fields=["status"])
            messages.success(request, _("Agendamento cancelado."))
        return HttpResponseRedirect(reverse("minha_agenda"))
