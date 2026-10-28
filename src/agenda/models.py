from django.conf import settings
from django.core.exceptions import ValidationError
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


class Profissional(models.Model):
    """Qualquer profissional que ofereça atendimentos pela plataforma.

    A especialidade (Personal Trainer, Nutricionista, Fisioterapeuta...)
    diferencia os profissionais; não há uma classe por especialidade.
    RF04, RF07, RF20.
    """

    ESPECIALIDADES = [
        ("PERSONAL", "Personal Trainer"),
        ("NUTRICIONISTA", "Nutricionista"),
        ("FISIOTERAPEUTA", "Fisioterapeuta"),
        ("PILATES", "Professor de Pilates"),
        ("PREPARADOR", "Preparador Físico"),
        ("OUTRO", "Outro"),
    ]

    MODALIDADES = [
        ("PRESENCIAL", "Presencial"),
        ("ONLINE", "Online"),
        ("HIBRIDO", "Híbrido"),
    ]

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil_profissional",
    )
    especialidade = models.CharField(
        "especialidade", max_length=30, choices=ESPECIALIDADES
    )
    registro_profissional = models.CharField(
        "registro profissional", max_length=50, blank=True, null=True
    )
    telefone = models.CharField("telefone", max_length=20, blank=True)
    modalidade = models.CharField(
        "modalidade", max_length=20, choices=MODALIDADES, default="PRESENCIAL"
    )
    descricao = models.TextField("descrição", blank=True)
    ativo = models.BooleanField("ativo", default=True)

    class Meta:
        verbose_name = "profissional"
        verbose_name_plural = "profissionais"

    def __str__(self):
        return f"{self.usuario} - {self.get_especialidade_display()}"


class Servico(models.Model):
    """Atendimento oferecido por um profissional, com duração definida.

    RF05. RN07: a duração é o que define o horário de término do agendamento.
    """

    MODALIDADES = Profissional.MODALIDADES

    profissional = models.ForeignKey(
        Profissional,
        on_delete=models.CASCADE,
        related_name="servicos",
    )
    nome = models.CharField("nome", max_length=100)
    duracao_minutos = models.PositiveIntegerField(
        "duração (minutos)", validators=[MinValueValidator(1)]
    )
    modalidade = models.CharField(
        "modalidade", max_length=20, choices=MODALIDADES, default="PRESENCIAL"
    )
    ativo = models.BooleanField("ativo", default=True)

    class Meta:
        verbose_name = "serviço"
        verbose_name_plural = "serviços"
        ordering = ["profissional", "nome"]
        unique_together = [("profissional", "nome")]

    def __str__(self):
        return f"{self.nome} ({self.duracao_minutos} min)"


class Agendamento(models.Model):
    """Reserva de um atendimento entre um cliente e um profissional.

    RF10, RF13, RF14, RF15. RN01 (conflito do profissional), RN02 (conflito
    do cliente), RN03 (conflito de sala), RN04 (conflito de recurso
    exclusivo); agendamentos cancelados não bloqueiam horários.
    """

    STATUS = [
        ("AGENDADO", "Agendado"),
        ("CONFIRMADO", "Confirmado"),
        ("CONCLUIDO", "Concluído"),
        ("CANCELADO", "Cancelado"),
    ]

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agendamentos_cliente",
    )
    profissional = models.ForeignKey(
        Profissional,
        on_delete=models.CASCADE,
        related_name="agendamentos",
    )
    servico = models.ForeignKey(
        Servico,
        on_delete=models.PROTECT,
        related_name="agendamentos",
        null=True,
        blank=True,
    )
    sala = models.ForeignKey(
        Sala,
        on_delete=models.PROTECT,
        related_name="agendamentos",
        null=True,
        blank=True,
    )
    recurso = models.ForeignKey(
        Recurso,
        on_delete=models.PROTECT,
        related_name="agendamentos",
        null=True,
        blank=True,
    )
    data = models.DateField("data")
    hora_inicio = models.TimeField("hora de início")
    hora_fim = models.TimeField("hora de término")
    status = models.CharField(
        "status", max_length=20, choices=STATUS, default="AGENDADO"
    )
    observacao = models.TextField("observação", blank=True)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "agendamento"
        verbose_name_plural = "agendamentos"
        ordering = ["data", "hora_inicio"]

    def __str__(self):
        return f"{self.cliente} - {self.profissional} - {self.data} {self.hora_inicio}"

    def _conflitantes(self):
        """Agendamentos ativos no mesmo dia cujo horário se sobrepõe a este."""
        return (
            Agendamento.objects.exclude(pk=self.pk)
            .exclude(status="CANCELADO")
            .filter(
                data=self.data,
                hora_inicio__lt=self.hora_fim,
                hora_fim__gt=self.hora_inicio,
            )
        )

    def clean(self):
        super().clean()
        if self.hora_inicio is None or self.hora_fim is None or self.data is None:
            return
        if self.hora_fim <= self.hora_inicio:
            raise ValidationError(
                {"hora_fim": "O horário final deve ser posterior ao inicial."}
            )
        if self.status == "CANCELADO":
            return
        conflitantes = self._conflitantes()
        if self.profissional_id and conflitantes.filter(
            profissional_id=self.profissional_id
        ).exists():
            raise ValidationError(
                "O profissional já possui um agendamento neste horário."
            )
        if self.cliente_id and conflitantes.filter(
            cliente_id=self.cliente_id
        ).exists():
            raise ValidationError("O cliente já possui um agendamento neste horário.")
        if self.sala_id and conflitantes.filter(sala_id=self.sala_id).exists():
            raise ValidationError(
                {"sala": "A sala já está reservada neste horário."}
            )
        # Recurso compartilhado pode ser usado por mais de um atendimento.
        if (
            self.recurso_id
            and self.recurso.exclusivo
            and conflitantes.filter(recurso_id=self.recurso_id).exists()
        ):
            raise ValidationError(
                {"recurso": "O recurso já está reservado neste horário."}
            )

    def save(self, *args, **kwargs):
        # Garante as validações críticas no back-end, fora de formulários.
        self.clean()
        super().save(*args, **kwargs)
