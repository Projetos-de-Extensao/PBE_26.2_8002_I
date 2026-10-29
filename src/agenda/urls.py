from django.urls import path

from . import views

app_name = "agenda"

urlpatterns = [
    path("agendamentos/novo/", views.novo_agendamento, name="novo_agendamento"),
]
