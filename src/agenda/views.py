from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from .forms import AgendamentoForm


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
