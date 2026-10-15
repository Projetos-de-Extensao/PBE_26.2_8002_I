from django.contrib import admin

from .models import Recurso, Sala


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ("nome", "capacidade")
    search_fields = ("nome",)


@admin.register(Recurso)
class RecursoAdmin(admin.ModelAdmin):
    list_display = ("nome", "exclusivo")
    list_filter = ("exclusivo",)
    search_fields = ("nome",)
