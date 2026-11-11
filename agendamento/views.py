from datetime import date, datetime, time, timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from agendamento.models import (
    Agendamento,
    Cliente,
    DIAS_SEMANA,
    Perfil,
    Profissional,
    Recepcionista,
    Recorrencia,
    Recurso,
    Sala,
    Servico,
    Usuario,
    horarios_livres,
)


def _acesso_negado(request):
    return render(request, "agendamento/acesso_negado.html", status=403)


def _url_tela_inicial(usuario):
    if usuario.perfil.papel == Perfil.Papel.ADMINISTRADOR:
        return reverse("administracao")
    return reverse("inicio")


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
    """Próximos inícios livres do profissional para o serviço (RF09).

    Usa ``horarios_livres`` dia a dia, com passo de 30 minutos, descartando
    horários que já passaram.
    """
    agora = timezone.now()
    hoje = timezone.localdate()
    horarios = []
    for dias_a_frente in range(31):
        data = hoje + timedelta(days=dias_a_frente)
        for inicio in horarios_livres(
            profissional,
            data,
            duracao_minutos=servico.duracao_minutos,
            passo_minutos=30,
        ):
            if inicio >= agora:
                horarios.append(inicio)
                if len(horarios) >= quantidade:
                    return horarios
    return horarios


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

    def get_success_url(self):
        return _url_tela_inicial(self.request.user)


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


class InicioView(LoginRequiredMixin, TemplateView):
    template_name = "agendamento/inicio.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.request.user
        perfil = usuario.perfil
        agora = timezone.now()
        context.update(
            {
                "papel": perfil.get_papel_display(),
                "eh_cliente": perfil.papel == Perfil.Papel.CLIENTE,
                "eh_profissional": perfil.papel == Perfil.Papel.PROFISSIONAL,
                "eh_recepcionista": perfil.papel == Perfil.Papel.RECEPCIONISTA,
            }
        )

        if perfil.papel in (
            Perfil.Papel.CLIENTE,
            Perfil.Papel.PROFISSIONAL,
        ):
            campo = (
                "cliente_id"
                if perfil.papel == Perfil.Papel.CLIENTE
                else "profissional_id"
            )
            context["agendamentos"] = (
                Agendamento.objects.filter(**{campo: usuario.pk})
                .filter(data_hora_inicio__gte=agora)
                .exclude(status=Agendamento.Status.CANCELADO)
                .select_related("cliente", "profissional", "servico", "sala")
                .order_by("data_hora_inicio")[:10]
            )
        elif perfil.papel == Perfil.Papel.RECEPCIONISTA:
            hoje = timezone.localdate()
            context["agendamentos"] = (
                Agendamento.objects.filter(data_hora_inicio__date=hoje)
                .exclude(status=Agendamento.Status.CANCELADO)
                .select_related("cliente", "profissional", "servico", "sala")
                .order_by("data_hora_inicio")
            )
            context["hoje"] = hoje

        return context


class UsuarioPerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ("nome", "telefone")


class ProfissionalPerfilForm(forms.ModelForm):
    class Meta:
        model = Profissional
        fields = ("nome", "telefone", "especialidade", "apresentacao")
        labels = {"apresentacao": _("Apresentação")}


class PerfilEdicaoView(LoginRequiredMixin, View):
    template_name = "agendamento/perfil_edicao.html"

    def get_form(self, request, data=None):
        if request.user.perfil.papel == Perfil.Papel.PROFISSIONAL:
            profissional = get_object_or_404(Profissional, pk=request.user.pk)
            return ProfissionalPerfilForm(data=data, instance=profissional)
        return UsuarioPerfilForm(data=data, instance=request.user)

    def render_form(self, request, form):
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "eh_profissional": (
                    request.user.perfil.papel == Perfil.Papel.PROFISSIONAL
                ),
            },
        )

    def get(self, request, *args, **kwargs):
        return self.render_form(request, self.get_form(request))

    def post(self, request, *args, **kwargs):
        form = self.get_form(request, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Perfil atualizado com sucesso."))
            return HttpResponseRedirect(_url_tela_inicial(request.user))
        return self.render_form(request, form)


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
    sala = forms.ModelChoiceField(
        label=_("Local"),
        queryset=Sala.objects.all(),
        required=False,
        empty_label=_("Não preciso de sala"),
    )
    recursos = forms.ModelMultipleChoiceField(
        label=_("Equipamentos"),
        queryset=Recurso.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text=_("Marque apenas se o atendimento precisar de algum equipamento."),
    )
    repetir_semanal = forms.BooleanField(
        label=_("Repetir semanalmente"),
        required=False,
    )
    dias_semana = forms.TypedMultipleChoiceField(
        label=_("Dias da semana"),
        choices=DIAS_SEMANA,
        coerce=int,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text=_("Se nenhum dia for marcado, repete no mesmo dia da semana do primeiro horário."),
    )
    data_termino = forms.DateField(
        label=_("Repetir até"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
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
        if not Sala.objects.exists():
            del self.fields["sala"]
        if not Recurso.objects.exists():
            del self.fields["recursos"]

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("repetir_semanal") and not cleaned_data.get("data_termino"):
            self.add_error(
                "data_termino",
                _("Informe até quando o agendamento deve se repetir."),
            )
        return cleaned_data

    def montar_recorrencia(self, cliente, servico):
        """Recorrência descrita pelo formulário (ainda não salva)."""
        inicio = timezone.localtime(
            datetime.fromisoformat(self.cleaned_data["horario"])
        )
        return Recorrencia(
            padrao=Recorrencia.PADRAO_SEMANAL,
            cliente=cliente,
            profissional=servico.profissional,
            servico=servico,
            sala=self.cleaned_data.get("sala"),
            dias_semana=self.cleaned_data.get("dias_semana") or [inicio.weekday()],
            data_inicio=inicio.date(),
            data_termino=self.cleaned_data["data_termino"],
            hora_inicio=inicio.time(),
        )


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


class NovoAgendamentoView(ClienteRoleRequiredMixin, FormView):
    """Agendamento de um serviço (UC5, RF10).

    Quando o horário não pode ser reservado, a tela informa o motivo e sugere
    outros horários livres (RF26), preferindo o mesmo dia.
    """

    form_class = AgendamentoForm
    template_name = "agendamento/novo_agendamento.html"
    success_url = reverse_lazy("profissionais")
    quantidade_horarios = 12
    quantidade_sugestoes = 6

    def dispatch(self, request, *args, **kwargs):
        self.servico = get_object_or_404(
            Servico.objects.select_related("profissional"),
            pk=kwargs["servico_id"],
            profissional__is_active=True,
        )
        self.conflito = []
        self.sugestoes = []
        return super().dispatch(request, *args, **kwargs)

    def get_horarios(self):
        if not hasattr(self, "_horarios"):
            self._horarios = _proximos_horarios(
                self.servico.profissional,
                self.servico,
                quantidade=self.quantidade_horarios,
            )
        return self._horarios

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["horarios"] = self.get_horarios()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["servico"] = self.servico
        context["profissional"] = self.servico.profissional
        context["conflito"] = self.conflito
        context["sugestoes"] = self.sugestoes
        return context

    def _novo_agendamento(self, cliente, inicio, sala):
        return Agendamento(
            cliente=cliente,
            profissional=self.servico.profissional,
            servico=self.servico,
            sala=sala,
            data_hora_inicio=inicio,
            data_hora_fim=self.servico.calcular_horario_fim(inicio),
        )

    def _sugestoes(self, cliente, inicio, sala, recursos):
        """Outros horários da lista que passam em todas as regras, começando
        pelos do mesmo dia do horário recusado."""
        dia = timezone.localtime(inicio).date()
        candidatos = sorted(
            (h for h in self.get_horarios() if h != inicio),
            key=lambda h: (timezone.localtime(h).date() != dia, h),
        )
        sugestoes = []
        for candidato in candidatos:
            agendamento = self._novo_agendamento(cliente, candidato, sala)
            if not agendamento.motivos_conflito(recursos=recursos):
                sugestoes.append(candidato)
                if len(sugestoes) >= self.quantidade_sugestoes:
                    break
        return sugestoes

    def form_valid(self, form):
        inicio = datetime.fromisoformat(form.cleaned_data["horario"])
        sala = form.cleaned_data.get("sala")
        recursos = list(form.cleaned_data.get("recursos") or [])
        cliente = self.cliente
        if form.cleaned_data.get("repetir_semanal"):
            return self._criar_recorrencia(form, cliente, recursos)

        with transaction.atomic():
            Profissional.objects.select_for_update().get(
                pk=self.servico.profissional_id
            )
            agendamento = self._novo_agendamento(cliente, inicio, sala)
            if inicio < timezone.now():
                motivos = [_("Este horário já passou.")]
            else:
                motivos = agendamento.motivos_conflito(recursos=recursos)
            if motivos:
                form.add_error(
                    "horario",
                    _("Este horário não está mais disponível. Escolha outro."),
                )
                self.conflito = motivos
                self.sugestoes = self._sugestoes(cliente, inicio, sala, recursos)
                return self.form_invalid(form)
            agendamento.save()
            agendamento.recursos.set(recursos)

        messages.success(self.request, _("Agendamento confirmado com sucesso."))
        return super().form_valid(form)

    def _criar_recorrencia(self, form, cliente, recursos):
        """Cria a série semanal (UC6): cada sessão é validada isoladamente
        (RN11) e as que têm conflito são descartadas (RN12)."""
        recorrencia = form.montar_recorrencia(cliente, self.servico)
        try:
            recorrencia.clean()
        except ValidationError as erro:
            for campo, mensagens in erro.message_dict.items():
                destino = campo if campo in form.fields else None
                for mensagem in mensagens:
                    form.add_error(destino, mensagem)
            return self.form_invalid(form)

        with transaction.atomic():
            Profissional.objects.select_for_update().get(
                pk=self.servico.profissional_id
            )
            validas, conflitos = recorrencia.avaliar_ocorrencias(recursos=recursos)
            if not validas:
                self.conflito = [
                    _("Todas as sessões do período apresentaram conflito: %(motivo)s")
                    % {"motivo": conflitos[0][1] if conflitos else ""}
                ]
                return self.form_invalid(form)
            recorrencia.save()
            recorrencia.recursos.set(recursos)
            validas, conflitos = recorrencia.gerar_ocorrencias(recursos=recursos)

        if conflitos:
            datas = ", ".join(
                timezone.localtime(agendamento.data_hora_inicio).strftime("%d/%m/%Y")
                for agendamento, _motivo in conflitos
            )
            messages.warning(
                self.request,
                _(
                    "Série criada com %(validas)s sessão(ões). %(conflitos)s "
                    "sessão(ões) com conflito foram descartadas (%(datas)s)."
                )
                % {"validas": len(validas), "conflitos": len(conflitos), "datas": datas},
            )
        else:
            messages.success(
                self.request,
                _("Série criada com sucesso: %(validas)s sessões agendadas.")
                % {"validas": len(validas)},
            )
        return HttpResponseRedirect(reverse("minha_agenda"))


class PreviaRecorrenciaView(NovoAgendamentoView):
    """JSON com cada data da série e se ela está livre ou em conflito (RF16).

    Usa o mesmo formulário e as mesmas regras da criação, sem salvar nada.
    """

    http_method_names = ["post"]

    def form_invalid(self, form):
        mensagens = [
            str(mensagem)
            for erros in form.errors.values()
            for mensagem in erros
        ]
        return JsonResponse(
            {"valido": False, "erro": " ".join(mensagens)},
            status=400,
        )

    def form_valid(self, form):
        if not Perfil.objects.filter(
            usuario_id=self.request.user.pk,
            papel=Perfil.Papel.CLIENTE,
        ).exists():
            return JsonResponse(
                {"valido": False, "erro": str(_("Apenas clientes podem agendar."))},
                status=403,
            )
        if not form.cleaned_data.get("data_termino"):
            return JsonResponse(
                {"valido": False, "erro": str(_("Informe até quando o agendamento deve se repetir."))},
                status=400,
            )
        cliente = _cliente_para_usuario(self.request.user)
        recorrencia = form.montar_recorrencia(cliente, self.servico)
        try:
            recorrencia.clean()
        except ValidationError as erro:
            return JsonResponse(
                {"valido": False, "erro": " ".join(erro.messages)},
                status=400,
            )

        recursos = list(form.cleaned_data.get("recursos") or [])
        validas, conflitos = recorrencia.avaliar_ocorrencias(recursos=recursos)
        motivos = {
            timezone.localtime(agendamento.data_hora_inicio).date(): motivo
            for agendamento, motivo in conflitos
        }
        nomes = dict(DIAS_SEMANA)
        sessoes = []
        for agendamento in sorted(
            validas + [agendamento for agendamento, _motivo in conflitos],
            key=lambda item: item.data_hora_inicio,
        ):
            inicio = timezone.localtime(agendamento.data_hora_inicio)
            fim = timezone.localtime(agendamento.data_hora_fim)
            conflito = inicio.date() in motivos
            sessoes.append(
                {
                    "data": inicio.date().isoformat(),
                    "data_formatada": f"{inicio:%d/%m/%Y} ({nomes[inicio.weekday()]})",
                    "horario": f"{inicio:%H:%M} - {fim:%H:%M}",
                    "conflito": conflito,
                    "status": "Conflito" if conflito else "Disponível",
                    "motivo": motivos.get(inicio.date(), ""),
                }
            )
        return JsonResponse(
            {
                "valido": True,
                "total": len(sessoes),
                "total_validas": len(validas),
                "total_conflitos": len(conflitos),
                "sessoes": sessoes,
            }
        )


class AgendaClienteView(ClienteRoleRequiredMixin, ListView):
    """Agenda do cliente com filtro opcional por período (UC9, RF17)."""

    model = Agendamento
    context_object_name = "agendamentos"
    template_name = "agendamento/minha_agenda.html"

    def _data_do_filtro(self, nome):
        valor = self.request.GET.get(nome, "").strip()
        try:
            return valor, date.fromisoformat(valor) if valor else None
        except ValueError:
            return valor, None

    def get_queryset(self):
        queryset = (
            Agendamento.objects.filter(cliente=self.cliente)
            .select_related("servico", "profissional", "sala")
            .prefetch_related("recursos")
            .order_by("data_hora_inicio")
        )
        _, data_inicio = self._data_do_filtro("data_inicio")
        _, data_fim = self._data_do_filtro("data_fim")
        if data_inicio:
            queryset = queryset.filter(
                data_hora_inicio__gte=timezone.make_aware(
                    datetime.combine(data_inicio, time.min)
                )
            )
        if data_fim:
            queryset = queryset.filter(
                data_hora_inicio__lt=timezone.make_aware(
                    datetime.combine(data_fim + timedelta(days=1), time.min)
                )
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["now"] = timezone.now()
        context["data_inicio"] = self._data_do_filtro("data_inicio")[0]
        context["data_fim"] = self._data_do_filtro("data_fim")[0]
        context["filtrando"] = bool(context["data_inicio"] or context["data_fim"])
        return context


# ---------------------------------------------------------------------------
# Cancelamento e reagendamento (UC7, UC8, RF11, RF12, RN10).
# ---------------------------------------------------------------------------
def _pode_operar_agendamento(usuario, agendamento):
    """Cliente do atendimento, profissional responsável, recepção (RN14) ou
    administração podem cancelar e reagendar."""
    papel = (
        Perfil.objects.filter(usuario_id=usuario.pk)
        .values_list("papel", flat=True)
        .first()
    )
    if papel == Perfil.Papel.CLIENTE:
        return agendamento.cliente_id == usuario.pk
    if papel == Perfil.Papel.PROFISSIONAL:
        return agendamento.profissional_id == usuario.pk
    return papel in (Perfil.Papel.RECEPCIONISTA, Perfil.Papel.ADMINISTRADOR)


def _agendamento_operavel(request, pk):
    """Agendamento que o usuário pode operar; 404 para os demais, sem revelar
    que o atendimento existe."""
    agendamento = get_object_or_404(
        Agendamento.objects.select_related("servico", "profissional", "cliente"),
        pk=pk,
    )
    if not _pode_operar_agendamento(request.user, agendamento):
        raise Http404
    return agendamento


def _pode_ser_alterado(agendamento):
    """Só atendimentos futuros e ativos podem ser cancelados ou reagendados."""
    return (
        agendamento.status
        in (Agendamento.Status.AGENDADO, Agendamento.Status.CONFIRMADO)
        and agendamento.data_hora_inicio > timezone.now()
    )


def _destino_apos_operacao(request):
    destino = request.POST.get("origem")
    if destino and url_has_allowed_host_and_scheme(
        destino,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return destino
    if Perfil.objects.filter(
        usuario_id=request.user.pk, papel=Perfil.Papel.CLIENTE
    ).exists():
        return reverse("minha_agenda")
    return reverse("inicio")


class CancelarAgendamentoView(LoginRequiredMixin, View):
    """Cancela uma sessão ou, em atendimentos recorrentes, toda a série."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        agendamento = _agendamento_operavel(request, kwargs["pk"])
        destino = _destino_apos_operacao(request)
        if not _pode_ser_alterado(agendamento):
            messages.error(
                request,
                _("Este agendamento não pode mais ser cancelado."),
            )
            return HttpResponseRedirect(destino)

        if request.POST.get("escopo") == "serie" and agendamento.recorrencia_id:
            total = agendamento.recorrencia.cancelar()
            messages.success(
                request,
                _(
                    "Série cancelada: %(total)s sessão(ões) futura(s) cancelada(s). "
                    "Os horários, a sala e os equipamentos foram liberados."
                )
                % {"total": total},
            )
        else:
            agendamento.status = Agendamento.Status.CANCELADO
            agendamento.save(update_fields=["status"])
            messages.success(request, _("Agendamento cancelado."))
        return HttpResponseRedirect(destino)


class HorariosReagendamentoView(LoginRequiredMixin, View):
    """JSON com os horários livres para remarcar um atendimento numa data.

    O próprio atendimento não conta como ocupado, e só entram horários que
    passam em todas as regras de conflito com a sala e os equipamentos já
    reservados.
    """

    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        agendamento = _agendamento_operavel(request, kwargs["pk"])
        if not _pode_ser_alterado(agendamento):
            return JsonResponse(
                {"erro": _("Este agendamento não pode mais ser reagendado.")},
                status=400,
            )
        valor = request.GET.get("data", "").strip()
        if not valor:
            return JsonResponse({"erro": _("Informe a data.")}, status=400)
        try:
            data = date.fromisoformat(valor)
        except ValueError:
            return JsonResponse(
                {"erro": _("Formato de data inválido. Use AAAA-MM-DD.")},
                status=400,
            )

        agora = timezone.now()
        duracao = agendamento.servico.duracao_minutos
        recursos = list(agendamento.recursos.all())
        horarios = []
        for inicio in horarios_livres(
            agendamento.profissional,
            data,
            duracao_minutos=duracao,
            passo_minutos=30,
            ignorar=agendamento,
        ):
            if inicio <= agora:
                continue
            candidato = Agendamento(
                pk=agendamento.pk,
                cliente_id=agendamento.cliente_id,
                profissional_id=agendamento.profissional_id,
                servico_id=agendamento.servico_id,
                sala_id=agendamento.sala_id,
                data_hora_inicio=inicio,
                data_hora_fim=agendamento.servico.calcular_horario_fim(inicio),
            )
            if not candidato.motivos_conflito(recursos=recursos):
                horarios.append(timezone.localtime(inicio).strftime("%H:%M"))

        return JsonResponse(
            {"horarios": horarios, "data": valor, "duracao_minutos": duracao}
        )


class ReagendarAgendamentoView(LoginRequiredMixin, View):
    """Remarca um atendimento (UC7). A troca é atômica: o horário antigo só é
    liberado quando o novo passa em todas as regras."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        agendamento = _agendamento_operavel(request, kwargs["pk"])
        if not _pode_ser_alterado(agendamento):
            return JsonResponse(
                {"erro": _("Este agendamento não pode mais ser reagendado.")},
                status=400,
            )
        nova_data = request.POST.get("data", "").strip()
        nova_hora = request.POST.get("hora_inicio", "").strip()
        if not nova_data or not nova_hora:
            return JsonResponse(
                {"erro": _("Informe a nova data e o novo horário.")},
                status=400,
            )
        try:
            inicio = timezone.make_aware(
                datetime.combine(
                    date.fromisoformat(nova_data),
                    time.fromisoformat(nova_hora),
                )
            )
        except ValueError:
            return JsonResponse(
                {"erro": _("Data ou horário em formato inválido.")},
                status=400,
            )
        if inicio == agendamento.data_hora_inicio:
            return JsonResponse(
                {"erro": _("O novo horário é igual ao atual.")},
                status=400,
            )
        if inicio <= timezone.now():
            return JsonResponse(
                {"erro": _("Escolha um horário que ainda não passou.")},
                status=400,
            )

        with transaction.atomic():
            Profissional.objects.select_for_update().get(
                pk=agendamento.profissional_id
            )
            agendamento.data_hora_inicio = inicio
            agendamento.data_hora_fim = agendamento.servico.calcular_horario_fim(
                inicio
            )
            motivos = agendamento.motivos_conflito()
            if motivos:
                return JsonResponse({"erro": " ".join(motivos)}, status=400)
            agendamento.save(update_fields=["data_hora_inicio", "data_hora_fim"])

        local_inicio = timezone.localtime(agendamento.data_hora_inicio)
        local_fim = timezone.localtime(agendamento.data_hora_fim)
        messages.success(
            request,
            _("Atendimento remarcado para %(data)s às %(hora)s.")
            % {
                "data": local_inicio.strftime("%d/%m/%Y"),
                "hora": local_inicio.strftime("%H:%M"),
            },
        )
        return JsonResponse(
            {
                "ok": True,
                "data": local_inicio.strftime("%d/%m/%Y"),
                "hora_inicio": local_inicio.strftime("%H:%M"),
                "hora_fim": local_fim.strftime("%H:%M"),
            }
        )
