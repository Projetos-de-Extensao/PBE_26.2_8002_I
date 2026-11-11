"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib.auth.views import LogoutView
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.urls import path, reverse_lazy

from agendamento.agenda_profissional import (
    CriarBloqueioView,
    DisponibilidadeBloqueioView,
    RemoverBloqueioView,
    RemoverDisponibilidadeView,
)
from agendamento.administracao import (
    AdministracaoView,
    ProfissionalCreateView,
    ProfissionalUpdateView,
    RecursoCreateView,
    RecursoUpdateView,
    SalaCreateView,
    SalaUpdateView,
    ServicoCreateView,
    ServicoUpdateView,
)
from agendamento.views import (
    AgendaClienteView,
    RecepcaoAgendaView,
    RecepcaoAgendarView,
    CadastroView,
    InicioView,
    LoginView,
    NovoAgendamentoView,
    PerfilEdicaoView,
    PreviaRecorrenciaView,
    ProfissionalDetailView,
    ProfissionalListView,
    CancelarAgendamentoView,
    HorariosReagendamentoView,
    ReagendarAgendamentoView,
)
from agendamento.admin_site import admin_site

urlpatterns = [
    path("admin/", admin_site.urls),
    path("administracao/", AdministracaoView.as_view(), name="administracao"),
    path(
        "administracao/profissionais/novo/",
        ProfissionalCreateView.as_view(),
        name="administracao_profissional_novo",
    ),
    path(
        "administracao/profissionais/<int:pk>/editar/",
        ProfissionalUpdateView.as_view(),
        name="administracao_profissional_editar",
    ),
    path(
        "administracao/servicos/novo/",
        ServicoCreateView.as_view(),
        name="administracao_servico_novo",
    ),
    path(
        "administracao/servicos/<int:pk>/editar/",
        ServicoUpdateView.as_view(),
        name="administracao_servico_editar",
    ),
    path(
        "administracao/salas/nova/",
        SalaCreateView.as_view(),
        name="administracao_sala_nova",
    ),
    path(
        "administracao/salas/<int:pk>/editar/",
        SalaUpdateView.as_view(),
        name="administracao_sala_editar",
    ),
    path(
        "administracao/recursos/novo/",
        RecursoCreateView.as_view(),
        name="administracao_recurso_novo",
    ),
    path(
        "administracao/recursos/<int:pk>/editar/",
        RecursoUpdateView.as_view(),
        name="administracao_recurso_editar",
    ),
    path("", LoginView.as_view(), name="login"),
    path("inicio/", InicioView.as_view(), name="inicio"),
    path("cadastrar/", CadastroView.as_view(), name="cadastro"),
    path("perfil/", PerfilEdicaoView.as_view(), name="perfil"),
    path(
        "profissionais/",
        ProfissionalListView.as_view(),
        name="profissionais",
    ),
    path(
        "profissionais/<int:pk>/",
        ProfissionalDetailView.as_view(),
        name="profissional_detail",
    ),
    path(
        "agendar/<int:servico_id>/",
        NovoAgendamentoView.as_view(),
        name="novo_agendamento",
    ),
    path(
        "agendar/<int:servico_id>/previa-recorrencia/",
        PreviaRecorrenciaView.as_view(),
        name="previa_recorrencia",
    ),
    path(
        "profissional/disponibilidade/",
        DisponibilidadeBloqueioView.as_view(),
        name="disponibilidade_bloqueio",
    ),
    path(
        "profissional/disponibilidade/<int:pk>/remover/",
        RemoverDisponibilidadeView.as_view(),
        name="remover_disponibilidade",
    ),
    path(
        "profissional/bloqueios/novo/",
        CriarBloqueioView.as_view(),
        name="criar_bloqueio",
    ),
    path(
        "profissional/bloqueios/<int:pk>/remover/",
        RemoverBloqueioView.as_view(),
        name="remover_bloqueio",
    ),
    path(
        "recepcao/agenda/",
        RecepcaoAgendaView.as_view(),
        name="recepcao_agenda",
    ),
    path(
        "recepcao/agendar/<int:servico_id>/",
        RecepcaoAgendarView.as_view(),
        name="recepcao_agendar",
    ),
    path(
        "minha-agenda/",
        AgendaClienteView.as_view(),
        name="minha_agenda",
    ),
    path(
        "minha-agenda/<int:pk>/cancelar/",
        CancelarAgendamentoView.as_view(),
        name="cancelar_agendamento",
    ),
    path(
        "agendamentos/<int:pk>/horarios/",
        HorariosReagendamentoView.as_view(),
        name="horarios_reagendamento",
    ),
    path(
        "agendamentos/<int:pk>/reagendar/",
        ReagendarAgendamentoView.as_view(),
        name="reagendar_agendamento",
    ),
    path(
        "senha/redefinir/",
        PasswordResetView.as_view(
            template_name="agendamento/registration/password_reset_form.html",
            email_template_name="agendamento/registration/password_reset_email.txt",
            subject_template_name="agendamento/registration/password_reset_subject.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "senha/redefinir/enviado/",
        PasswordResetDoneView.as_view(
            template_name="agendamento/registration/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "senha/redefinir/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(
            template_name="agendamento/registration/password_reset_confirm.html",
            success_url=reverse_lazy("password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "senha/redefinir/concluido/",
        PasswordResetCompleteView.as_view(
            template_name="agendamento/registration/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
    path("sair/", LogoutView.as_view(next_page="login"), name="logout"),
]
