from django.contrib import admin

from .models import Agendamento, Bloqueio, Disponibilidade, Profissional, Recurso, Sala


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ("nome", "capacidade")
    search_fields = ("nome",)


@admin.register(Recurso)
class RecursoAdmin(admin.ModelAdmin):
    list_display = ("nome", "exclusivo")
    list_filter = ("exclusivo",)
    search_fields = ("nome",)


@admin.register(Profissional)
class ProfissionalAdmin(admin.ModelAdmin):
    list_display = ("usuario", "especialidade", "modalidade", "ativo")
    list_filter = ("especialidade", "modalidade", "ativo")
    search_fields = ("usuario__username", "usuario__first_name", "registro_profissional")


@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ("cliente", "profissional", "servico", "data", "hora_inicio", "status")
    list_filter = ("status", "data")
    search_fields = ("cliente__username", "profissional__usuario__username", "servico")


@admin.register(Disponibilidade)
class DisponibilidadeAdmin(admin.ModelAdmin):
    list_display = ("profissional", "dia_semana", "hora_inicio", "hora_fim")
    list_filter = ("dia_semana",)
    search_fields = ("profissional__usuario__username",)


@admin.register(Bloqueio)
class BloqueioAdmin(admin.ModelAdmin):
    list_display = ("profissional", "data", "hora_inicio", "hora_fim", "motivo")
    list_filter = ("data",)
    search_fields = ("profissional__usuario__username", "motivo")
