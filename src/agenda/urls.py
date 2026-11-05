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
    path(
        "agendamentos/<int:pk>/cancelar/",
        views.cancelar_agendamento,
        name="cancelar_agendamento",
    ),
    path(
        "agendamentos/<int:pk>/horarios/",
        views.horarios_reagendamento,
        name="horarios_reagendamento",
    ),
    path(
        "agendamentos/<int:pk>/reagendar/",
        views.reagendar_agendamento,
        name="reagendar_agendamento",
    ),
    path("minha-agenda/", views.agenda_cliente, name="agenda_cliente"),
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
