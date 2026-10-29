from django.urls import path

from . import views

app_name = "agenda"

urlpatterns = [
    path("agendamentos/novo/", views.novo_agendamento, name="novo_agendamento"),
    path(
        "agendamentos/previa-recorrencia/",
        views.previa_recorrencia,
        name="previa_recorrencia",
    ),
    path("painel/", views.painel_profissional, name="painel_profissional"),
    path(
        "disponibilidade-bloqueio/",
        views.disponibilidade_bloqueio,
        name="disponibilidade_bloqueio",
    ),
    path(
        "disponibilidade/<int:pk>/remover/",
        views.remover_disponibilidade,
        name="remover_disponibilidade",
    ),
    path("bloqueio/novo/", views.criar_bloqueio, name="criar_bloqueio"),
    path("bloqueio/<int:pk>/remover/", views.remover_bloqueio, name="remover_bloqueio"),
]
