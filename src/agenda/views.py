from datetime import date, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import AgendamentoForm, BloqueioForm, DisponibilidadeForm
from .models import (
    DIAS_SEMANA,
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


def _sugestoes_de_horario(dados):
    """Horários livres do profissional no mesmo dia, para oferecer ao cliente
    quando o horário escolhido der conflito (RF26)."""
    profissional = dados.get("profissional")
    data = dados.get("data")
    servico = dados.get("servico")
    if profissional is None or data is None:
        return []
    duracao = servico.duracao_minutos if servico else 30
    livres = horarios_livres(profissional, data, duracao)
    return [hora for hora in livres if hora != dados.get("hora_inicio")][:6]


def _mensagens_de_conflito(form):
    """Erros de validação que impedem a reserva do horário escolhido."""
    mensagens = list(form.non_field_errors())
    for campo in ("sala", "recurso", "data_fim", "dias_semana"):
        mensagens += list(form.errors.get(campo, []))
    return mensagens


@login_required
def novo_agendamento(request):
    """Tela de criação de agendamento (RF10, RF16).

    Quando a validação recusa o horário, a tela reabre com o motivo do
    conflito e sugestões de horários livres no mesmo dia (RF26).
    Em agendamento recorrente, valida cada ocorrência individualmente (RN11)
    e descarta ocorrências em conflito (RN12).
    """
    conflito = None
    sugestoes = []

    if request.method == "POST":
        form = AgendamentoForm(request.POST)
        if form.is_valid():
            if form.cleaned_data.get("repetir_semanal"):
                dias = [
                    int(d)
                    for d in form.cleaned_data.get("dias_semana")
                    or [form.cleaned_data["data"].weekday()]
                ]
                recorrencia = Recorrencia(
                    cliente=request.user,
                    profissional=form.cleaned_data["profissional"],
                    servico=form.cleaned_data["servico"],
                    sala=form.cleaned_data.get("sala"),
                    recurso=form.cleaned_data.get("recurso"),
                    padrao="SEMANAL",
                    dias_semana=dias,
                    data_inicio=form.cleaned_data["data"],
                    data_fim=form.cleaned_data["data_fim"],
                    hora_inicio=form.cleaned_data["hora_inicio"],
                )
                try:
                    recorrencia.clean()
                    validos, conflitos_rec = recorrencia.avaliar_ocorrencias()
                    if not validos:
                        motivo = (
                            conflitos_rec[0][1]
                            if conflitos_rec
                            else "Nenhum horário livre no período."
                        )
                        conflito = (
                            f"Todas as ocorrências no período apresentaram conflito: "
                            f"{motivo}"
                        )
                    else:
                        recorrencia.save(gerar_agendamentos=False)
                        for ag in validos:
                            ag.recorrencia = recorrencia
                            ag.save()
                        qtd_validos = len(validos)
                        qtd_conflitos = len(conflitos_rec)
                        if qtd_conflitos > 0:
                            datas_conflito = ", ".join(
                                ag.data.strftime("%d/%m/%Y")
                                for ag, _ in conflitos_rec
                            )
                            messages.warning(
                                request,
                                f"Recorrência criada com {qtd_validos} agendamento(s). "
                                f"{qtd_conflitos} ocorrência(s) com conflito foram descartadas ({datas_conflito}).",
                            )
                        else:
                            messages.success(
                                request,
                                f"Recorrência criada com sucesso: {qtd_validos} agendamentos gerados.",
                            )
                        return redirect("agenda:novo_agendamento")
                except ValidationError as erro:
                    conflito = (
                        " ".join(erro.messages)
                        if hasattr(erro, "messages")
                        else str(erro)
                    )
            else:
                agendamento = form.save(commit=False)
                agendamento.cliente = request.user
                try:
                    agendamento.save()
                except ValidationError as erro:
                    conflito = " ".join(erro.messages)
                else:
                    messages.success(request, "Agendamento criado com sucesso.")
                    return redirect("agenda:novo_agendamento")
        else:
            mensagens = _mensagens_de_conflito(form)
            conflito = " ".join(mensagens) if mensagens else None
        if conflito:
            sugestoes = _sugestoes_de_horario(getattr(form, "cleaned_data", {}))
    else:
        form = AgendamentoForm()

    return render(
        request,
        "agenda/novo_agendamento.html",
        {"form": form, "conflito": conflito, "sugestoes": sugestoes},
    )


@login_required
def previa_recorrencia(request):
    """Retorna a prévia das ocorrências de uma recorrência com identificação de conflitos (RF16)."""
    if request.method != "POST":
        return JsonResponse({"erro": "Método não permitido."}, status=405)

    servico_id = request.POST.get("servico")
    profissional_id = request.POST.get("profissional")
    data_str = request.POST.get("data")
    data_fim_str = request.POST.get("data_fim")
    hora_str = request.POST.get("hora_inicio")
    sala_id = request.POST.get("sala") or None
    recurso_id = request.POST.get("recurso") or None
    dias_semana_raw = request.POST.getlist("dias_semana")

    if not all([servico_id, profissional_id, data_str, data_fim_str, hora_str]):
        return JsonResponse(
            {
                "valido": False,
                "erro": "Preencha o serviço, profissional, horário, data inicial e data final.",
            },
            status=400,
        )

    try:
        data_inicio = date.fromisoformat(data_str)
        data_fim = date.fromisoformat(data_fim_str)
        hora_inicio = time.fromisoformat(hora_str)
    except ValueError:
        return JsonResponse(
            {"valido": False, "erro": "Formato de data ou horário inválido."},
            status=400,
        )

    if data_fim < data_inicio:
        return JsonResponse(
            {
                "valido": False,
                "erro": "A data final deve ser posterior ou igual à data inicial.",
            },
            status=400,
        )

    dias_semana = (
        [int(d) for d in dias_semana_raw if d.isdigit()]
        if dias_semana_raw
        else [data_inicio.weekday()]
    )

    servico = get_object_or_404(Servico, pk=servico_id)
    profissional = get_object_or_404(Profissional, pk=profissional_id)
    sala = get_object_or_404(Sala, pk=sala_id) if sala_id else None
    recurso = get_object_or_404(Recurso, pk=recurso_id) if recurso_id else None

    recorrencia = Recorrencia(
        cliente=request.user,
        profissional=profissional,
        servico=servico,
        sala=sala,
        recurso=recurso,
        padrao="SEMANAL",
        dias_semana=dias_semana,
        data_inicio=data_inicio,
        data_fim=data_fim,
        hora_inicio=hora_inicio,
    )

    try:
        recorrencia.clean()
    except ValidationError as erro:
        msg = " ".join(erro.messages) if hasattr(erro, "messages") else str(erro)
        return JsonResponse({"valido": False, "erro": msg}, status=400)

    validos, conflitos = recorrencia.avaliar_ocorrencias()
    mapa_conflitos = {ag.data: motivo for ag, motivo in conflitos}

    datas_todas = recorrencia.datas_do_periodo()
    hora_fim = recorrencia.hora_fim
    hora_fim_str = hora_fim.strftime("%H:%M") if hora_fim else ""
    hora_inicio_str = hora_inicio.strftime("%H:%M")

    sessoes = []
    mapa_dias = dict(DIAS_SEMANA)
    for d in datas_todas:
        nome_dia = mapa_dias.get(d.weekday(), "")
        data_formatada = f"{d.strftime('%d/%m/%Y')} ({nome_dia})"
        if d in mapa_conflitos:
            sessoes.append(
                {
                    "data": d.isoformat(),
                    "data_formatada": data_formatada,
                    "horario": f"{hora_inicio_str} - {hora_fim_str}",
                    "conflito": True,
                    "status": "Conflito",
                    "motivo": mapa_conflitos[d],
                }
            )
        else:
            sessoes.append(
                {
                    "data": d.isoformat(),
                    "data_formatada": data_formatada,
                    "horario": f"{hora_inicio_str} - {hora_fim_str}",
                    "conflito": False,
                    "status": "Disponível",
                    "motivo": "",
                }
            )

    return JsonResponse(
        {
            "valido": True,
            "total": len(datas_todas),
            "total_validas": len(validos),
            "total_conflitos": len(conflitos),
            "sessoes": sessoes,
        }
    )
