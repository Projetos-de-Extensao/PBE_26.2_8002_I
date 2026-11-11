"""Área do profissional: disponibilidade semanal e bloqueios de horário.

Incorporado de src/agenda (UC10, UC11, RF07, RF20, RN05, RN13), adaptado aos
models deste projeto: o profissional é o próprio usuário autenticado e o
bloqueio guarda início e fim como data e hora (``inicio``/``fim``).
"""

from datetime import date, datetime, time, timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import ListView

from agendamento.models import (
    Agendamento,
    Bloqueio,
    Disponibilidade,
    Perfil,
    Profissional,
)
from agendamento.views import _acesso_negado


class ProfissionalRoleRequiredMixin(LoginRequiredMixin):
    """Libera a view apenas para usuários com papel de profissional (RN08)."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not Perfil.objects.filter(
            usuario_id=request.user.pk,
            papel=Perfil.Papel.PROFISSIONAL,
        ).exists():
            return _acesso_negado(request)
        self.profissional = Profissional.objects.filter(pk=request.user.pk).first()
        if self.profissional is None:
            return _acesso_negado(request)
        return super().dispatch(request, *args, **kwargs)


class DisponibilidadeForm(forms.ModelForm):
    class Meta:
        model = Disponibilidade
        fields = ["dia_semana", "hora_inicio", "hora_fim"]
        widgets = {
            "hora_inicio": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "hora_fim": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        }
        labels = {
            "dia_semana": _("Dia da semana"),
            "hora_inicio": _("Hora de início"),
            "hora_fim": _("Hora de término"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["dia_semana"].choices = [("", _("Escolha o dia"))] + list(
            Disponibilidade.DiaSemana.choices
        )


class BloqueioForm(forms.Form):
    """Coleta data e faixa de horário e monta o intervalo ``inicio``/``fim``."""

    data = forms.DateField(
        label=_("Data"),
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    hora_inicio = forms.TimeField(
        label=_("Hora de início"),
        widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
    )
    hora_fim = forms.TimeField(
        label=_("Hora de término"),
        widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
    )
    motivo = forms.CharField(label=_("Motivo"), max_length=255)

    def clean(self):
        cleaned_data = super().clean()
        data = cleaned_data.get("data")
        hora_inicio = cleaned_data.get("hora_inicio")
        hora_fim = cleaned_data.get("hora_fim")
        if data and hora_inicio and hora_fim:
            if hora_fim <= hora_inicio:
                self.add_error(
                    "hora_fim",
                    _("O horário final deve ser posterior ao inicial."),
                )
            else:
                cleaned_data["inicio"] = timezone.make_aware(
                    datetime.combine(data, hora_inicio)
                )
                cleaned_data["fim"] = timezone.make_aware(
                    datetime.combine(data, hora_fim)
                )
        return cleaned_data


def _contexto(profissional, disponibilidade_form, bloqueio_form):
    return {
        "profissional": profissional,
        "disponibilidade_form": disponibilidade_form,
        "bloqueio_form": bloqueio_form,
        "faixas": Disponibilidade.objects.filter(profissional=profissional),
        "bloqueios": Bloqueio.objects.filter(profissional=profissional),
    }


def _destino_seguro(request):
    destino = request.POST.get("origem")
    if destino and url_has_allowed_host_and_scheme(
        destino,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return destino
    return reverse("disponibilidade_bloqueio")


class DisponibilidadeBloqueioView(ProfissionalRoleRequiredMixin, View):
    """Tela onde o profissional cadastra faixas de disponibilidade e bloqueios."""

    template_name = "agendamento/disponibilidade_bloqueio.html"

    def get(self, request, *args, **kwargs):
        return render(
            request,
            self.template_name,
            _contexto(self.profissional, DisponibilidadeForm(), BloqueioForm()),
        )

    def post(self, request, *args, **kwargs):
        form = DisponibilidadeForm(request.POST)
        if form.is_valid():
            faixa = form.save(commit=False)
            faixa.profissional = self.profissional
            faixa.save()
            messages.success(request, _("Faixa de disponibilidade salva."))
            return HttpResponseRedirect(reverse("disponibilidade_bloqueio"))
        return render(
            request,
            self.template_name,
            _contexto(self.profissional, form, BloqueioForm()),
        )


class RemoverDisponibilidadeView(ProfissionalRoleRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        faixa = get_object_or_404(
            Disponibilidade,
            pk=kwargs["pk"],
            profissional=self.profissional,
        )
        faixa.delete()
        messages.success(request, _("Faixa de disponibilidade removida."))
        return HttpResponseRedirect(reverse("disponibilidade_bloqueio"))


class CriarBloqueioView(ProfissionalRoleRequiredMixin, View):
    """Registra um bloqueio. Se houver atendimentos ativos no período, pede
    confirmação antes de aplicar (RN13)."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        destino = _destino_seguro(request)
        form = BloqueioForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "agendamento/disponibilidade_bloqueio.html",
                _contexto(self.profissional, DisponibilidadeForm(), form),
            )

        bloqueio = Bloqueio(
            profissional=self.profissional,
            inicio=form.cleaned_data["inicio"],
            fim=form.cleaned_data["fim"],
            motivo=form.cleaned_data["motivo"],
        )
        try:
            bloqueio.full_clean()
        except ValidationError as erro:
            form.add_error(None, erro)
            return render(
                request,
                "agendamento/disponibilidade_bloqueio.html",
                _contexto(self.profissional, DisponibilidadeForm(), form),
            )

        afetados = bloqueio.agendamentos_afetados()
        if afetados.exists() and request.POST.get("confirmar") != "1":
            return render(
                request,
                "agendamento/confirmar_bloqueio.html",
                {
                    "form": form,
                    "afetados": afetados,
                    "profissional": self.profissional,
                    "destino": destino,
                },
            )

        bloqueio.save()
        messages.success(request, _("Bloqueio registrado."))
        return HttpResponseRedirect(destino)


class RemoverBloqueioView(ProfissionalRoleRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        bloqueio = get_object_or_404(
            Bloqueio,
            pk=kwargs["pk"],
            profissional=self.profissional,
        )
        bloqueio.delete()
        messages.success(request, _("Bloqueio removido."))
        return HttpResponseRedirect(reverse("disponibilidade_bloqueio"))


class PainelProfissionalView(ProfissionalRoleRequiredMixin, ListView):
    """Agenda do profissional, dia a dia (UC9, RF18, protótipo 09).

    A tela inicial mostra apenas os próximos atendimentos; aqui o profissional
    navega por data, como o protótipo previa.
    """

    model = Agendamento
    context_object_name = "agendamentos"
    template_name = "agendamento/painel_profissional.html"

    def dia(self):
        valor = self.request.GET.get("dia", "").strip()
        try:
            return date.fromisoformat(valor) if valor else timezone.localdate()
        except ValueError:
            return timezone.localdate()

    def get_queryset(self):
        dia = self.dia()
        inicio = timezone.make_aware(datetime.combine(dia, time.min))
        return (
            Agendamento.objects.filter(
                profissional=self.profissional,
                data_hora_inicio__gte=inicio,
                data_hora_inicio__lt=inicio + timedelta(days=1),
            )
            .select_related("cliente", "servico", "sala")
            .prefetch_related("recursos")
            .order_by("data_hora_inicio")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dia = self.dia()
        context.update(
            {
                "profissional": self.profissional,
                "dia": dia,
                "dia_anterior": dia - timedelta(days=1),
                "dia_seguinte": dia + timedelta(days=1),
                "hoje": timezone.localdate(),
                "bloqueios": Bloqueio.objects.filter(
                    profissional=self.profissional,
                    inicio__date=dia,
                ).order_by("inicio"),
            }
        )
        return context
