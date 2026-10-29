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


DIAS_SEMANA = [
    (0, "Segunda-feira"),
    (1, "Terça-feira"),
    (2, "Quarta-feira"),
    (3, "Quinta-feira"),
    (4, "Sexta-feira"),
    (5, "Sábado"),
    (6, "Domingo"),
]


class Disponibilidade(models.Model):
    """Faixa de horário em que o profissional pode ser agendado.

    RF07, RF09. RN05: só horários compatíveis com alguma faixa cadastrada
    para o dia da semana correspondente podem ser selecionados.
    """

    profissional = models.ForeignKey(
        Profissional, on_delete=models.CASCADE, related_name="disponibilidades"
    )
    dia_semana = models.PositiveSmallIntegerField("dia da semana", choices=DIAS_SEMANA)
    hora_inicio = models.TimeField("hora de início")
    hora_fim = models.TimeField("hora de término")

    class Meta:
        verbose_name = "disponibilidade"
        verbose_name_plural = "disponibilidades"
        ordering = ["profissional", "dia_semana", "hora_inicio"]

    def __str__(self):
        return (
            f"{self.profissional} - {self.get_dia_semana_display()} "
            f"{self.hora_inicio}-{self.hora_fim}"
        )

    def clean(self):
        super().clean()
        if self.hora_inicio and self.hora_fim and self.hora_fim <= self.hora_inicio:
            raise ValidationError(
                {"hora_fim": "O horário final deve ser posterior ao inicial."}
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class Bloqueio(models.Model):
    """Período em que o profissional fica indisponível (férias, almoço, curso...).

    RF20. RN13: um bloqueio torna o intervalo indisponível para novos
    agendamentos; se houver atendimento confirmado no período, o profissional
    deve ser alertado antes da aplicação (ver `agendamentos_afetados`).
    """

    profissional = models.ForeignKey(
        Profissional, on_delete=models.CASCADE, related_name="bloqueios"
    )
    data = models.DateField("data")
    hora_inicio = models.TimeField("hora de início")
    hora_fim = models.TimeField("hora de término")
    motivo = models.CharField("motivo", max_length=200, blank=True)

    class Meta:
        verbose_name = "bloqueio"
        verbose_name_plural = "bloqueios"
        ordering = ["data", "hora_inicio"]

    def __str__(self):
        return f"{self.profissional} - {self.data} {self.hora_inicio}-{self.hora_fim}"

    def clean(self):
        super().clean()
        if self.hora_inicio and self.hora_fim and self.hora_fim <= self.hora_inicio:
            raise ValidationError(
                {"hora_fim": "O horário final deve ser posterior ao inicial."}
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def agendamentos_afetados(self):
        """Agendamentos ativos do profissional que se sobrepõem a este bloqueio (RN13)."""
        return Agendamento.objects.filter(
            profissional=self.profissional,
            data=self.data,
            hora_inicio__lt=self.hora_fim,
            hora_fim__gt=self.hora_inicio,
        ).exclude(status="CANCELADO")


class Agendamento(models.Model):
    """Reserva de um atendimento entre um cliente e um profissional.

    RF10, RF13, RF14, RF15. RN01 (conflito do profissional), RN02 (conflito
    do cliente), RN05 (disponibilidade), RN13 (bloqueio); agendamentos
    cancelados não bloqueiam horários.
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
    servico = models.CharField("serviço", max_length=100)
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

    def _fora_da_disponibilidade(self):
        """True se o horário não estiver contido em nenhuma faixa cadastrada
        pelo profissional para o dia da semana da data do agendamento (RN05)."""
        faixas = Disponibilidade.objects.filter(
            profissional_id=self.profissional_id, dia_semana=self.data.weekday()
        )
        return not faixas.filter(
            hora_inicio__lte=self.hora_inicio, hora_fim__gte=self.hora_fim
        ).exists()

    def _bloqueado(self):
        """True se o horário se sobrepuser a um bloqueio do profissional (RN13)."""
        return Bloqueio.objects.filter(
            profissional_id=self.profissional_id,
            data=self.data,
            hora_inicio__lt=self.hora_fim,
            hora_fim__gt=self.hora_inicio,
        ).exists()

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
        if self.profissional_id and self._fora_da_disponibilidade():
            raise ValidationError(
                "Horário fora da disponibilidade cadastrada pelo profissional."
            )
        if self.profissional_id and self._bloqueado():
            raise ValidationError("Horário bloqueado pelo profissional.")
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

    def save(self, *args, **kwargs):
        # Garante as validações críticas no back-end, fora de formulários.
        self.clean()
        super().save(*args, **kwargs)


def horarios_livres(profissional, data, duracao_minutos=30):
    """Horários em que `profissional` pode receber um novo agendamento em `data`.

    `duracao_minutos` é a duração do serviço a agendar. Descarta horários fora
    da disponibilidade cadastrada e horários já ocupados por bloqueios ou
    agendamentos ativos (RF09).
    """
    from datetime import datetime, timedelta

    duracao = timedelta(minutes=duracao_minutos)
    faixas = Disponibilidade.objects.filter(
        profissional=profissional, dia_semana=data.weekday()
    ).order_by("hora_inicio")

    ocupados = [
        (bloqueio.hora_inicio, bloqueio.hora_fim)
        for bloqueio in Bloqueio.objects.filter(profissional=profissional, data=data)
    ]
    ocupados += [
        (agendamento.hora_inicio, agendamento.hora_fim)
        for agendamento in Agendamento.objects.filter(
            profissional=profissional, data=data
        ).exclude(status="CANCELADO")
    ]

    livres = []
    for faixa in faixas:
        cursor = datetime.combine(data, faixa.hora_inicio)
        fim_faixa = datetime.combine(data, faixa.hora_fim)
        while cursor + duracao <= fim_faixa:
            inicio_slot = cursor.time()
            fim_slot = (cursor + duracao).time()
            ocupado = any(
                inicio_slot < fim_ocupado and fim_slot > inicio_ocupado
                for inicio_ocupado, fim_ocupado in ocupados
            )
            if not ocupado:
                livres.append(inicio_slot)
            cursor += duracao

    return livres
