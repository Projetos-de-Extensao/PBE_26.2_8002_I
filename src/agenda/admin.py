from django.contrib import admin

from .models import (
    Agendamento,
    Bloqueio,
    Disponibilidade,
    Profissional,
    Recorrencia,
    Recurso,
    Sala,
    Servico,
)


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


@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ("nome", "profissional", "duracao_minutos", "modalidade", "ativo")
    list_filter = ("modalidade", "ativo")
    search_fields = ("nome", "profissional__usuario__username")


class AgendamentoInline(admin.TabularInline):
    model = Agendamento
    extra = 0
    fields = ("data", "hora_inicio", "hora_fim", "status", "sala", "recurso")
    readonly_fields = ("data", "hora_inicio", "hora_fim", "status", "sala", "recurso")
    can_delete = True
    show_change_link = True


@admin.register(Recorrencia)
class RecorrenciaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cliente",
        "profissional",
        "servico",
        "data_inicio",
        "data_fim",
        "hora_inicio",
        "padrao",
        "total_agendamentos",
    )
    list_filter = ("padrao", "profissional", "servico")
    search_fields = (
        "cliente__username",
        "profissional__usuario__username",
        "servico__nome",
    )
    inlines = [AgendamentoInline]

    def total_agendamentos(self, obj):
        return obj.agendamentos.count()

    total_agendamentos.short_description = "Ocorrências"


@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = (
        "cliente",
        "profissional",
        "servico",
        "data",
        "hora_inicio",
        "sala",
        "recurso",
        "recorrencia",
        "status",
    )
    list_filter = ("status", "data", "sala", "recurso", "recorrencia")
    search_fields = (
        "cliente__username",
        "profissional__usuario__username",
        "servico__nome",
    )


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
