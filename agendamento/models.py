from datetime import datetime, timedelta

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Q


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    @transaction.atomic
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("O e-mail deve ser informado.")
        papel_inicial = extra_fields.pop("papel", None)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        user = self.model(email=self.normalize_email(email), **extra_fields)
        if papel_inicial is not None:
            user._papel_inicial = getattr(papel_inicial, "nome", papel_inicial)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.pop("papel", None)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superusuários devem ter is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusuários devem ter is_superuser=True.")

        return self.create_user(
            email,
            password,
            papel="administrador",
            **extra_fields,
        )


class Papel(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    permissoes = models.ManyToManyField(
        "Permissao",
        blank=True,
        related_name="papeis",
    )

    class Meta:
        verbose_name = "papel"
        verbose_name_plural = "papeis"
        ordering = ("nome",)

    def __str__(self):
        return self.nome


class Permissao(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True)

    class Meta:
        verbose_name = "permissao"
        verbose_name_plural = "permissoes"
        ordering = ("nome",)

    def __str__(self):
        return self.nome


class Usuario(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    nome = models.CharField(max_length=150)
    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ("nome",)

    def __str__(self):
        return self.nome


class Perfil(models.Model):
    class Papel(models.TextChoices):
        CLIENTE = "cliente", "Cliente"
        PROFISSIONAL = "profissional", "Profissional"
        RECEPCIONISTA = "recepcionista", "Recepcionista"
        ADMINISTRADOR = "administrador", "Administrador"

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name="perfil",
    )
    papel = models.CharField(
        max_length=20,
        choices=Papel.choices,
        default=Papel.CLIENTE,
    )

    class Meta:
        verbose_name = "perfil"
        verbose_name_plural = "perfis"
        ordering = ("usuario__nome",)

    def __str__(self):
        return f"{self.usuario.nome} — {self.get_papel_display()}"


class Cliente(Usuario):
    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"


class Profissional(Usuario):
    especialidade = models.CharField(max_length=150)
    formacao = models.TextField(blank=True)
    apresentacao = models.TextField(blank=True)

    class Meta:
        verbose_name = "profissional"
        verbose_name_plural = "profissionais"
        ordering = ("nome",)


class Recepcionista(Usuario):
    class Meta:
        verbose_name = "recepcionista"
        verbose_name_plural = "recepcionistas"


class Administrador(Usuario):
    class Meta:
        verbose_name = "administrador"
        verbose_name_plural = "administradores"


class Servico(models.Model):
    profissional = models.ForeignKey(
        Profissional,
        on_delete=models.PROTECT,
        related_name="servicos",
    )
    nome = models.CharField(max_length=150)
    tipo = models.CharField(max_length=100)
    duracao_minutos = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    class Meta:
        verbose_name = "servico"
        verbose_name_plural = "servicos"
        ordering = ("nome",)

    def __str__(self):
        return self.nome

    def calcular_horario_fim(self, inicio: datetime) -> datetime:
        return inicio + timedelta(minutes=self.duracao_minutos)


class Disponibilidade(models.Model):
    class DiaSemana(models.IntegerChoices):
        SEGUNDA = 0, "Segunda-feira"
        TERCA = 1, "Terca-feira"
        QUARTA = 2, "Quarta-feira"
        QUINTA = 3, "Quinta-feira"
        SEXTA = 4, "Sexta-feira"
        SABADO = 5, "Sabado"
        DOMINGO = 6, "Domingo"

    profissional = models.ForeignKey(
        Profissional,
        on_delete=models.CASCADE,
        related_name="disponibilidades",
    )
    dia_semana = models.PositiveSmallIntegerField(choices=DiaSemana.choices)
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()

    class Meta:
        verbose_name = "disponibilidade"
        verbose_name_plural = "disponibilidades"
        ordering = ("dia_semana", "hora_inicio")
        constraints = [
            models.CheckConstraint(
                condition=Q(hora_fim__gt=models.F("hora_inicio")),
                name="disponibilidade_horario_valido",
            ),
        ]

    def __str__(self):
        return f"{self.profissional}: {self.get_dia_semana_display()}"

    def esta_disponivel(self, horario: datetime) -> bool:
        return (
            horario.weekday() == self.dia_semana
            and self.hora_inicio <= horario.time() < self.hora_fim
        )


class Bloqueio(models.Model):
    profissional = models.ForeignKey(
        Profissional,
        on_delete=models.CASCADE,
        related_name="bloqueios",
    )
    inicio = models.DateTimeField()
    fim = models.DateTimeField()
    motivo = models.CharField(max_length=255)

    class Meta:
        verbose_name = "bloqueio"
        verbose_name_plural = "bloqueios"
        ordering = ("inicio",)
        constraints = [
            models.CheckConstraint(
                condition=Q(fim__gt=models.F("inicio")),
                name="bloqueio_periodo_valido",
            ),
        ]

    def __str__(self):
        return f"{self.profissional}: {self.inicio} - {self.fim}"


class Sala(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    capacidade = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    class Meta:
        verbose_name = "sala"
        verbose_name_plural = "salas"
        ordering = ("nome",)

    def __str__(self):
        return self.nome


class Recurso(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    exclusivo = models.BooleanField(default=False)

    class Meta:
        verbose_name = "recurso"
        verbose_name_plural = "recursos"
        ordering = ("nome",)

    def __str__(self):
        return self.nome


class Recorrencia(models.Model):
    padrao = models.CharField(max_length=100)
    data_termino = models.DateField()

    class Meta:
        verbose_name = "recorrencia"
        verbose_name_plural = "recorrencias"
        ordering = ("data_termino",)

    def __str__(self):
        return f"{self.padrao} ate {self.data_termino}"


class Agendamento(models.Model):
    class Status(models.TextChoices):
        AGENDADO = "agendado", "Agendado"
        CONFIRMADO = "confirmado", "Confirmado"
        CANCELADO = "cancelado", "Cancelado"
        CONCLUIDO = "concluido", "Concluido"

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="agendamentos",
    )
    profissional = models.ForeignKey(
        Profissional,
        on_delete=models.PROTECT,
        related_name="agendamentos",
    )
    servico = models.ForeignKey(
        Servico,
        on_delete=models.PROTECT,
        related_name="agendamentos",
    )
    recepcionista = models.ForeignKey(
        Recepcionista,
        on_delete=models.PROTECT,
        related_name="agendamentos_operados",
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
    recursos = models.ManyToManyField(
        Recurso,
        blank=True,
        related_name="agendamentos",
    )
    recorrencia = models.ForeignKey(
        Recorrencia,
        on_delete=models.SET_NULL,
        related_name="agendamentos",
        null=True,
        blank=True,
    )
    data_hora_inicio = models.DateTimeField()
    data_hora_fim = models.DateTimeField()
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.AGENDADO,
    )

    class Meta:
        verbose_name = "agendamento"
        verbose_name_plural = "agendamentos"
        ordering = ("data_hora_inicio",)
        indexes = [
            models.Index(fields=("profissional", "data_hora_inicio")),
            models.Index(fields=("cliente", "data_hora_inicio")),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(data_hora_fim__gt=models.F("data_hora_inicio")),
                name="agendamento_periodo_valido",
            ),
        ]

    def __str__(self):
        return f"{self.cliente} - {self.data_hora_inicio}"

    def verificar_conflito(self) -> bool:
        if (
            self.profissional_id is None
            or self.cliente_id is None
            or self.data_hora_inicio is None
            or self.data_hora_fim is None
            or self.data_hora_fim <= self.data_hora_inicio
        ):
            raise ValueError(
                "Informe cliente, profissional e um intervalo valido "
                "antes de verificar conflitos."
            )

        conflitos = (
            Agendamento.objects.exclude(
                status=self.Status.CANCELADO,
            )
            .exclude(pk=self.pk)
            .filter(
                data_hora_inicio__lt=self.data_hora_fim,
                data_hora_fim__gt=self.data_hora_inicio,
            )
        )
        alvos = Q(profissional_id=self.profissional_id) | Q(
            cliente_id=self.cliente_id,
        )

        if self.sala_id is not None:
            alvos |= Q(sala_id=self.sala_id)

        if self.pk is not None:
            recursos_exclusivos = self.recursos.filter(exclusivo=True)
            if recursos_exclusivos.exists():
                alvos |= Q(recursos__in=recursos_exclusivos)

        return conflitos.filter(alvos).distinct().exists()
