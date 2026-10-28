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

from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.urls import path, reverse_lazy

from agendamento.views import CadastroView, LoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", LoginView.as_view(), name="login"),
    path("cadastrar/", CadastroView.as_view(), name="cadastro"),
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
