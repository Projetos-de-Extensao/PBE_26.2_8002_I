from django.core.validators import MinValueValidator
from django.db import models


class Sala(models.Model):
    """Espaço físico compartilhado (consultório, estúdio) usado em atendimentos.

    RF06, RF15. RN03: não pode ser reservada por dois atendimentos no mesmo
    intervalo (validação feita em Agendamento).
    """

    nome = models.CharField("nome", max_length=100, unique=True)
    capacidade = models.PositiveIntegerField(
        "capacidade", default=1, validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = "sala"
        verbose_name_plural = "salas"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Recurso(models.Model):
    """Equipamento ou item necessário a determinados serviços.

    RF06, RF15. RN04: um recurso exclusivo não pode ser reservado
    simultaneamente (validação feita em Agendamento).
    """

    nome = models.CharField("nome", max_length=100, unique=True)
    exclusivo = models.BooleanField("exclusivo", default=True)

    class Meta:
        verbose_name = "recurso"
        verbose_name_plural = "recursos"
        ordering = ["nome"]

    def __str__(self):
        return self.nome
