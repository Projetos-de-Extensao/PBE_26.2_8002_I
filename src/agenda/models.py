from datetime import date, datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction


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

    RF10, RF13, RF14, RF15, RF16. RN01 (conflito do profissional), RN02 (conflito
    do cliente), RN03 (sala), RN04 (recurso exclusivo), RN05
    (disponibilidade), RN13 (bloqueio); agendamentos cancelados não bloqueiam
    horários.
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
    recorrencia = models.ForeignKey(
        "Recorrencia",
        on_delete=models.CASCADE,
        related_name="agendamentos",
        null=True,
        blank=True,
    )
    data = models.DateField("data")
    hora_inicio = models.TimeField("hora de início")
    hora_fim = models.TimeField("hora de término", blank=True)
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

    @property
    def eh_recorrente(self):
        return self.recorrencia_id is not None

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

    def _calcular_hora_fim(self):
        """Hora de término = início + duração do serviço (RN07)."""
        if self.servico_id is None or self.hora_inicio is None:
            return None
        inicio = datetime.combine(date.min, self.hora_inicio)
        return (inicio + timedelta(minutes=self.servico.duracao_minutos)).time()

    def clean(self):
        super().clean()
        if self.hora_fim is None:
            self.hora_fim = self._calcular_hora_fim()
        if self.hora_inicio is None or self.data is None:
            return
        if self.hora_fim is None:
            raise ValidationError(
                {"hora_fim": "Informe a hora de término ou escolha um serviço."}
            )
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
        if self.sala_id and conflitantes.filter(sala_id=self.sala_id).exists():
            raise ValidationError({"sala": "A sala já está reservada neste horário."})
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


class Recorrencia(models.Model):
    """Padrão de repetição de agendamentos (RF16).

    RN11: cada ocorrência é validada individualmente contra as regras RN01 a RN06.
    RN12: ocorrência de recorrência em conflito não pode sobrescrever reserva
    existente; ela é descartada.
    """

    PADROES = [
        ("SEMANAL", "Semanal"),
    ]

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recorrencias",
    )
    profissional = models.ForeignKey(
        Profissional,
        on_delete=models.CASCADE,
        related_name="recorrencias",
    )
    servico = models.ForeignKey(
        Servico,
        on_delete=models.PROTECT,
        related_name="recorrencias",
        null=True,
        blank=True,
    )
    sala = models.ForeignKey(
        Sala,
        on_delete=models.PROTECT,
        related_name="recorrencias",
        null=True,
        blank=True,
    )
    recurso = models.ForeignKey(
        Recurso,
        on_delete=models.PROTECT,
        related_name="recorrencias",
        null=True,
        blank=True,
    )
    padrao = models.CharField(
        "padrão", max_length=20, choices=PADROES, default="SEMANAL"
    )
    dias_semana = models.JSONField("dias da semana", default=list)
    data_inicio = models.DateField("data de início")
    data_fim = models.DateField("data de término")
    hora_inicio = models.TimeField("hora de início")
    hora_fim = models.TimeField("hora de término", blank=True)
    observacao = models.TextField("observação", blank=True)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "recorrência"
        verbose_name_plural = "recorrências"
        ordering = ["-criado_em"]

    def __str__(self):
        dias = self.get_dias_semana_display() or "sem dias"
        return f"{self.cliente} - {self.profissional} ({dias}, {self.hora_inicio})"

    @property
    def data_termino(self):
        return self.data_fim

    @data_termino.setter
    def data_termino(self, valor):
        self.data_fim = valor

    def get_dias_semana_display(self):
        mapa = dict(DIAS_SEMANA)
        return ", ".join(mapa.get(int(d), str(d)) for d in (self.dias_semana or []))

    def _calcular_hora_fim(self):
        if self.servico_id is None or self.hora_inicio is None:
            return None
        inicio = datetime.combine(date.min, self.hora_inicio)
        return (inicio + timedelta(minutes=self.servico.duracao_minutos)).time()

    def clean(self):
        super().clean()
        if isinstance(self.dias_semana, str):
            if self.dias_semana.strip():
                self.dias_semana = [
                    int(d.strip())
                    for d in self.dias_semana.split(",")
                    if d.strip().isdigit()
                ]
            else:
                self.dias_semana = []
        elif isinstance(self.dias_semana, (list, tuple, set)):
            self.dias_semana = sorted(list({int(d) for d in self.dias_semana}))
        elif self.dias_semana is None:
            self.dias_semana = []

        if not self.dias_semana:
            raise ValidationError(
                {"dias_semana": "Selecione ao menos um dia da semana para a recorrência."}
            )

        for dia in self.dias_semana:
            if dia not in range(7):
                raise ValidationError(
                    {"dias_semana": f"Dia da semana inválido: {dia}."}
                )

        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError(
                {"data_fim": "A data final deve ser posterior ou igual à data inicial."}
            )

        if self.data_inicio and self.data_fim and not self.datas_do_periodo():
            raise ValidationError(
                {
                    "data_fim": (
                        "O período informado não contempla nenhum dos dias da "
                        "semana selecionados."
                    )
                }
            )

        if self.hora_fim is None:
            self.hora_fim = self._calcular_hora_fim()

        if self.hora_inicio and self.hora_fim and self.hora_fim <= self.hora_inicio:
            raise ValidationError(
                {"hora_fim": "O horário final deve ser posterior ao inicial."}
            )

    def datas_do_periodo(self):
        """Datas entre data_inicio e data_fim que coincidem com dias_semana."""
        if not self.data_inicio or not self.data_fim or not self.dias_semana:
            return []
        dias_alvo = set(self.dias_semana)
        datas = []
        atual = self.data_inicio
        while atual <= self.data_fim:
            if atual.weekday() in dias_alvo:
                datas.append(atual)
            atual += timedelta(days=1)
        return datas

    def avaliar_ocorrencias(self):
        """Avalia individualmente cada ocorrência do período contra RN01 a RN06 e RN13.

        Retorna (validos, conflitos):
        - validos: lista de Agendamento válidos (não salvos ainda).
        - conflitos: lista de tuplas (Agendamento, mensagem_erro).
        """
        validos = []
        conflitos = []
        hora_fim = self.hora_fim or self._calcular_hora_fim()
        for d in self.datas_do_periodo():
            ag = Agendamento(
                cliente=self.cliente,
                profissional=self.profissional,
                servico=self.servico,
                sala=self.sala,
                recurso=self.recurso,
                data=d,
                hora_inicio=self.hora_inicio,
                hora_fim=hora_fim,
                observacao=self.observacao,
                recorrencia=self,
            )
            try:
                ag.clean()
            except ValidationError as erro:
                msg = (
                    " ".join(erro.messages)
                    if hasattr(erro, "messages")
                    else str(erro)
                )
                conflitos.append((ag, msg))
            else:
                validos.append(ag)
        return validos, conflitos

    def gerar_ocorrencias(self, salvar=True, descartar_conflitos=True):
        """Gera e opcionalmente persiste os agendamentos da série (RF16).

        RN11: cada ocorrência é validada individualmente.
        RN12: ocorrências em conflito são descartadas.
        """
        validos, conflitos = self.avaliar_ocorrencias()
        self.ultimos_conflitos = conflitos

        if not validos and conflitos and salvar:
            raise ValidationError(
                "Nenhuma ocorrência pôde ser gerada devido a conflitos de horário em todas as datas."
            )

        if salvar:
            if self.pk is None:
                super().save()
            for ag in validos:
                ag.recorrencia = self
                ag.save()

        return validos

    gerarOcorrencias = gerar_ocorrencias

    def save(self, *args, **kwargs):
        gerar = kwargs.pop("gerar_agendamentos", True)
        is_novo = self.pk is None
        self.clean()
        if is_novo and gerar:
            with transaction.atomic():
                super().save(*args, **kwargs)
                self.gerar_ocorrencias(salvar=True)
        else:
            super().save(*args, **kwargs)

    def cancelar(self):
        """Cancela todos os agendamentos ativos desta série (RN10)."""
        return self.agendamentos.exclude(status="CANCELADO").update(
            status="CANCELADO"
        )


def horarios_livres(profissional, data, duracao_minutos=30):
    """Horários em que `profissional` pode receber um novo agendamento em `data`.

    `duracao_minutos` é a duração do serviço a agendar. Descarta horários fora
    da disponibilidade cadastrada e horários já ocupados por bloqueios ou
    agendamentos ativos (RF09).
    """
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
