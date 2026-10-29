from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import AgendamentoForm, BloqueioForm, DisponibilidadeForm
from .models import Agendamento, Bloqueio, Disponibilidade, Profissional


@login_required
def painel_profissional(request):
    """Agenda do profissional logado por dia, com acesso rápido ao bloqueio de horário (RF18)."""
    profissional = get_object_or_404(Profissional, usuario=request.user)

    dia_str = request.GET.get("dia")
    dia = date.fromisoformat(dia_str) if dia_str else date.today()

    agendamentos = (
        Agendamento.objects.filter(profissional=profissional, data=dia)
        .exclude(status="CANCELADO")
        .order_by("hora_inicio")
    )

    context = {
        "profissional": profissional,
        "dia": dia,
        "dia_anterior": dia - timedelta(days=1),
        "dia_seguinte": dia + timedelta(days=1),
        "agendamentos": agendamentos,
        "bloqueio_form": BloqueioForm(initial={"data": dia}),
    }
    return render(request, "agenda/painel_profissional.html", context)


@login_required
def disponibilidade_bloqueio(request):
    """Tela onde o profissional cadastra faixas de disponibilidade e bloqueios (RF07, RF20)."""
    profissional = get_object_or_404(Profissional, usuario=request.user)

    disponibilidade_form = DisponibilidadeForm()
    if request.method == "POST" and "salvar_disponibilidade" in request.POST:
        disponibilidade_form = DisponibilidadeForm(request.POST)
        if disponibilidade_form.is_valid():
            faixa = disponibilidade_form.save(commit=False)
            faixa.profissional = profissional
            try:
                faixa.save()
                return redirect("agenda:disponibilidade_bloqueio")
            except ValidationError as erro:
                disponibilidade_form.add_error(None, erro)

    return render(
        request,
        "agenda/disponibilidade_bloqueio.html",
        _contexto_disponibilidade_bloqueio(profissional, disponibilidade_form, BloqueioForm()),
    )


def _contexto_disponibilidade_bloqueio(profissional, disponibilidade_form, bloqueio_form):
    return {
        "profissional": profissional,
        "disponibilidade_form": disponibilidade_form,
        "bloqueio_form": bloqueio_form,
        "faixas": Disponibilidade.objects.filter(profissional=profissional),
        "bloqueios": Bloqueio.objects.filter(profissional=profissional),
    }


@login_required
def remover_disponibilidade(request, pk):
    profissional = get_object_or_404(Profissional, usuario=request.user)
    faixa = get_object_or_404(Disponibilidade, pk=pk, profissional=profissional)
    if request.method == "POST":
        faixa.delete()
    return redirect("agenda:disponibilidade_bloqueio")


@login_required
def remover_bloqueio(request, pk):
    profissional = get_object_or_404(Profissional, usuario=request.user)
    bloqueio = get_object_or_404(Bloqueio, pk=pk, profissional=profissional)
    if request.method == "POST":
        bloqueio.delete()
    return redirect("agenda:disponibilidade_bloqueio")


@login_required
def criar_bloqueio(request):
    """Cria um bloqueio a partir do modal do painel ou da tela de disponibilidade.

    Se houver atendimentos ativos no período, pede confirmação antes de
    aplicar o bloqueio (RN13).
    """
    profissional = get_object_or_404(Profissional, usuario=request.user)
    destino = request.POST.get("origem") or reverse("agenda:disponibilidade_bloqueio")

    if request.method != "POST":
        return redirect(destino)

    form = BloqueioForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "agenda/disponibilidade_bloqueio.html",
            _contexto_disponibilidade_bloqueio(profissional, DisponibilidadeForm(), form),
        )

    bloqueio = form.save(commit=False)
    bloqueio.profissional = profissional

    try:
        bloqueio.clean()
    except ValidationError as erro:
        form.add_error(None, erro)
        return render(
            request,
            "agenda/disponibilidade_bloqueio.html",
            _contexto_disponibilidade_bloqueio(profissional, DisponibilidadeForm(), form),
        )

    afetados = bloqueio.agendamentos_afetados()
    if afetados.exists() and request.POST.get("confirmar") != "1":
        return render(
            request,
            "agenda/confirmar_bloqueio.html",
            {"form": form, "afetados": afetados, "profissional": profissional, "destino": destino},
        )

    bloqueio.save()
    return redirect(destino)


@login_required
def novo_agendamento(request):
    """Tela de criação de agendamento (RF10)."""
    if request.method == "POST":
        form = AgendamentoForm(request.POST)
        if form.is_valid():
            agendamento = form.save(commit=False)
            agendamento.cliente = request.user
            try:
                agendamento.save()
            except ValidationError as erro:
                for mensagem in erro.messages:
                    form.add_error(None, mensagem)
            else:
                messages.success(request, "Agendamento criado com sucesso.")
                return redirect("agenda:novo_agendamento")
    else:
        form = AgendamentoForm()

    return render(request, "agenda/novo_agendamento.html", {"form": form})
