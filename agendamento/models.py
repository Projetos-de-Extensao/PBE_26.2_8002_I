from datetime import date, datetime, time, timedelta

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone


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
    telefone = models.CharField(max_length=20, blank=True)
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
    class Modalidade(models.TextChoices):
        PRESENCIAL = "presencial", "Presencial"
        ONLINE = "online", "Online"
        HIBRIDO = "hibrido", "Híbrido"

    especialidade = models.CharField(max_length=150)
    modalidade = models.CharField(
        max_length=20,
        choices=Modalidade.choices,
        default=Modalidade.PRESENCIAL,
    )
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

    def clean(self):
        super().clean()
        if self.hora_inicio and self.hora_fim and self.hora_fim <= self.hora_inicio:
            raise ValidationError(
                {"hora_fim": "O horário final deve ser posterior ao inicial."}
            )

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

    def clean(self):
        super().clean()
        if self.inicio and self.fim and self.fim <= self.inicio:
            raise ValidationError(
                {"fim": "O horário final deve ser posterior ao inicial."}
            )

    def agendamentos_afetados(self):
        """Atendimentos ativos do profissional que se sobrepõem ao bloqueio (RN13)."""
        return (
            Agendamento.objects.filter(
                profissional_id=self.profissional_id,
                data_hora_inicio__lt=self.fim,
                data_hora_fim__gt=self.inicio,
            )
            .exclude(status=Agendamento.Status.CANCELADO)
            .select_related("cliente", "servico")
            .order_by("data_hora_inicio")
        )


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


DIAS_SEMANA = [
    (0, "Segunda-feira"),
    (1, "Terça-feira"),
    (2, "Quarta-feira"),
    (3, "Quinta-feira"),
    (4, "Sexta-feira"),
    (5, "Sábado"),
    (6, "Domingo"),
]


class Recorrencia(models.Model):
    """Série semanal de agendamentos (UC6, RF16).

    RN11: cada ocorrência é validada individualmente pelas mesmas regras de um
    agendamento avulso. RN12: ocorrências em conflito não sobrescrevem reservas
    existentes; são descartadas.

    Os vínculos são opcionais no banco para que a migration funcione em bases
    que já tenham recorrências antigas; ``clean()`` exige todos eles.
    """

    PADRAO_SEMANAL = "Semanal"
    MAXIMO_DIAS = 366

    padrao = models.CharField(max_length=100, default=PADRAO_SEMANAL)
    data_termino = models.DateField()
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="recorrencias",
        null=True,
        blank=True,
    )
    profissional = models.ForeignKey(
        Profissional,
        on_delete=models.PROTECT,
        related_name="recorrencias",
        null=True,
        blank=True,
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
    recursos = models.ManyToManyField(
        Recurso,
        blank=True,
        related_name="recorrencias",
    )
    dias_semana = models.JSONField(default=list, blank=True)
    data_inicio = models.DateField(null=True, blank=True)
    hora_inicio = models.TimeField(null=True, blank=True)

    class Meta:
        verbose_name = "recorrencia"
        verbose_name_plural = "recorrencias"
        ordering = ("data_termino",)

    def __str__(self):
        dias = self.get_dias_semana_display()
        if dias and self.hora_inicio:
            return (
                f"{self.padrao} ({dias}, {self.hora_inicio:%H:%M}) "
                f"ate {self.data_termino}"
            )
        return f"{self.padrao} ate {self.data_termino}"

    def get_dias_semana_display(self):
        nomes = dict(DIAS_SEMANA)
        return ", ".join(nomes.get(int(dia), str(dia)) for dia in self.dias_semana or [])

    def _normalizar_dias_semana(self):
        dias = self.dias_semana
        if isinstance(dias, str):
            dias = [parte.strip() for parte in dias.split(",") if parte.strip()]
        try:
            self.dias_semana = sorted({int(dia) for dia in dias or []})
        except (TypeError, ValueError):
            raise ValidationError({"dias_semana": "Dias da semana inválidos."})

    def clean(self):
        super().clean()
        self._normalizar_dias_semana()
        erros = {}
        obrigatorios = {
            "cliente": self.cliente_id,
            "profissional": self.profissional_id,
            "servico": self.servico_id,
            "data_inicio": self.data_inicio,
            "hora_inicio": self.hora_inicio,
            "data_termino": self.data_termino,
        }
        for campo, valor in obrigatorios.items():
            if valor is None:
                erros[campo] = "Este campo é obrigatório."
        if not self.dias_semana:
            erros["dias_semana"] = "Selecione ao menos um dia da semana para a recorrência."
        elif any(dia not in range(7) for dia in self.dias_semana):
            erros["dias_semana"] = "Dia da semana inválido."
        if erros:
            raise ValidationError(erros)

        if self.data_termino < self.data_inicio:
            raise ValidationError(
                {"data_termino": "A data final deve ser posterior ou igual à data inicial."}
            )
        if (self.data_termino - self.data_inicio).days > self.MAXIMO_DIAS:
            raise ValidationError(
                {"data_termino": "A série pode durar no máximo um ano."}
            )
        if not self.datas_do_periodo():
            raise ValidationError(
                {
                    "data_termino": (
                        "O período informado não contempla nenhum dos dias "
                        "da semana selecionados."
                    )
                }
            )

    def datas_do_periodo(self):
        """Datas entre o início e o término que caem nos dias escolhidos."""
        if not self.data_inicio or not self.data_termino or not self.dias_semana:
            return []
        dias = {int(dia) for dia in self.dias_semana}
        datas = []
        atual = self.data_inicio
        while atual <= self.data_termino:
            if atual.weekday() in dias:
                datas.append(atual)
            atual += timedelta(days=1)
        return datas

    def avaliar_ocorrencias(self, recursos=None):
        """Monta e valida cada ocorrência da série, sem salvar (RN11).

        Devolve ``(validas, conflitos)``: ``validas`` é uma lista de
        agendamentos prontos para salvar e ``conflitos`` uma lista de pares
        ``(agendamento, motivo)``.
        """
        if recursos is None:
            recursos = list(self.recursos.all()) if self.pk is not None else []
        agora = timezone.now()
        validas, conflitos = [], []
        for data in self.datas_do_periodo():
            inicio = timezone.make_aware(datetime.combine(data, self.hora_inicio))
            agendamento = Agendamento(
                cliente_id=self.cliente_id,
                profissional_id=self.profissional_id,
                servico=self.servico,
                sala_id=self.sala_id,
                recorrencia=self if self.pk is not None else None,
                data_hora_inicio=inicio,
                data_hora_fim=self.servico.calcular_horario_fim(inicio),
            )
            if inicio <= agora:
                motivos = ["Este horário já passou."]
            else:
                motivos = agendamento.motivos_conflito(recursos=recursos)
            if motivos:
                conflitos.append((agendamento, " ".join(motivos)))
            else:
                validas.append(agendamento)
        return validas, conflitos

    def gerar_ocorrencias(self, recursos=None, salvar=True):
        """Gera os agendamentos da série (RF16).

        Ocorrências em conflito são descartadas sem tocar nas reservas
        existentes (RN12). Ao salvar, exige ao menos uma ocorrência válida.
        Devolve ``(validas, conflitos)``.
        """
        if recursos is None:
            recursos = list(self.recursos.all()) if self.pk is not None else []
        validas, conflitos = self.avaliar_ocorrencias(recursos=recursos)
        if not salvar:
            return validas, conflitos
        if not validas:
            raise ValidationError(
                "Nenhuma sessão pôde ser agendada: todas as datas do período "
                "apresentaram conflito."
            )
        if self.pk is None:
            raise ValueError("Salve a recorrência antes de gerar as ocorrências.")
        with transaction.atomic():
            for agendamento in validas:
                agendamento.recorrencia = self
                agendamento.save()
                agendamento.recursos.set(recursos)
        return validas, conflitos

    def cancelar(self):
        """Cancela as sessões futuras e ativas da série (UC8, RN10).

        Sessões passadas, concluídas ou já canceladas não são alteradas.
        Devolve a quantidade de sessões canceladas.
        """
        return (
            self.agendamentos.filter(
                status__in=(
                    Agendamento.Status.AGENDADO,
                    Agendamento.Status.CONFIRMADO,
                ),
                data_hora_inicio__gt=timezone.now(),
            ).update(status=Agendamento.Status.CANCELADO)
        )


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

    # Mensagens exibidas ao cliente quando o horário não pode ser reservado (RF26).
    MSG_FORA_DISPONIBILIDADE = "Horário fora da disponibilidade cadastrada pelo profissional."
    MSG_BLOQUEADO = "Horário bloqueado pelo profissional."
    MSG_PROFISSIONAL_OCUPADO = "O profissional já possui um agendamento neste horário."
    MSG_CLIENTE_OCUPADO = "O cliente já possui um agendamento neste horário."
    MSG_SALA_OCUPADA = "A sala {sala} já está reservada neste horário."
    MSG_RECURSO_OCUPADO = "O equipamento {recurso} já está reservado neste horário."

    def _periodo_informado(self):
        return (
            self.data_hora_inicio is not None
            and self.data_hora_fim is not None
            and self.data_hora_fim > self.data_hora_inicio
        )

    def _ativos_no_periodo(self):
        """Atendimentos não cancelados que se sobrepõem a este intervalo."""
        return (
            Agendamento.objects.exclude(status=self.Status.CANCELADO)
            .exclude(pk=self.pk)
            .filter(
                data_hora_inicio__lt=self.data_hora_fim,
                data_hora_fim__gt=self.data_hora_inicio,
            )
        )

    def _dentro_da_disponibilidade(self):
        """RN05: o intervalo inteiro cabe numa faixa do profissional no dia."""
        inicio = timezone.localtime(self.data_hora_inicio)
        fim = timezone.localtime(self.data_hora_fim)
        if fim.date() != inicio.date():
            return False
        return Disponibilidade.objects.filter(
            profissional_id=self.profissional_id,
            dia_semana=inicio.weekday(),
            hora_inicio__lte=inicio.time(),
            hora_fim__gte=fim.time(),
        ).exists()

    def motivos_conflito(self, recursos=None):
        """Lista os motivos que impedem reservar este horário.

        Regras verificadas: RN05 (disponibilidade), RN13 (bloqueio), RN01
        (profissional), RN02 (cliente), RN03 (sala) e RN04 (equipamentos de uso
        exclusivo). ``recursos`` permite validar os equipamentos escolhidos
        antes de o agendamento ser salvo; sem ele, usa os já vinculados.
        Lista vazia significa que o horário está livre.
        """
        if not self._periodo_informado() or self.status == self.Status.CANCELADO:
            return []

        motivos = []
        if self.profissional_id is not None:
            if not self._dentro_da_disponibilidade():
                motivos.append(self.MSG_FORA_DISPONIBILIDADE)
            if Bloqueio.objects.filter(
                profissional_id=self.profissional_id,
                inicio__lt=self.data_hora_fim,
                fim__gt=self.data_hora_inicio,
            ).exists():
                motivos.append(self.MSG_BLOQUEADO)

        ativos = self._ativos_no_periodo()
        if (
            self.profissional_id is not None
            and ativos.filter(profissional_id=self.profissional_id).exists()
        ):
            motivos.append(self.MSG_PROFISSIONAL_OCUPADO)
        if (
            self.cliente_id is not None
            and ativos.filter(cliente_id=self.cliente_id).exists()
        ):
            motivos.append(self.MSG_CLIENTE_OCUPADO)
        if self.sala_id is not None and ativos.filter(sala_id=self.sala_id).exists():
            motivos.append(self.MSG_SALA_OCUPADA.format(sala=self.sala))

        if recursos is None:
            recursos = list(self.recursos.all()) if self.pk is not None else []
        exclusivos = [recurso.pk for recurso in recursos if recurso.exclusivo]
        if exclusivos:
            ocupados = Recurso.objects.filter(
                pk__in=exclusivos,
                agendamentos__in=ativos,
            ).distinct()
            for recurso in ocupados:
                motivos.append(self.MSG_RECURSO_OCUPADO.format(recurso=recurso))
        return motivos

    def clean(self):
        super().clean()
        if (
            self.data_hora_fim is None
            and self.data_hora_inicio is not None
            and self.servico_id is not None
        ):
            # RN07: término = início + duração do serviço.
            self.data_hora_fim = self.servico.calcular_horario_fim(
                self.data_hora_inicio
            )
        if self.data_hora_inicio is None or self.data_hora_fim is None:
            return
        if self.data_hora_fim <= self.data_hora_inicio:
            raise ValidationError(
                {"data_hora_fim": "O horário final deve ser posterior ao inicial."}
            )
        if self.status == self.Status.CONCLUIDO:
            return
        motivos = self.motivos_conflito()
        if motivos:
            raise ValidationError(motivos)

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
        return bool(self.motivos_conflito())


def horarios_livres(
    profissional,
    data: date,
    duracao_minutos=30,
    passo_minutos=None,
    ignorar=None,
):
    """Inícios livres para ``profissional`` em ``data`` (RF09, UC4).

    Considera as faixas de disponibilidade do dia (RN05) e descarta horários
    que se sobrepõem a bloqueios (RN13) ou a atendimentos ativos (RN01).
    ``passo_minutos`` define o intervalo entre os horários sugeridos; por
    padrão é a própria duração do serviço. ``ignorar`` é um agendamento que
    não conta como ocupado (usado no reagendamento, para que o horário atual
    apareça livre). Devolve datetimes com fuso.
    """
    faixas = list(
        Disponibilidade.objects.filter(
            profissional=profissional,
            dia_semana=data.weekday(),
        ).order_by("hora_inicio")
    )
    if not faixas:
        return []

    duracao = timedelta(minutes=duracao_minutos)
    passo = timedelta(minutes=passo_minutos or duracao_minutos)
    inicio_do_dia = timezone.make_aware(datetime.combine(data, time.min))
    fim_do_dia = inicio_do_dia + timedelta(days=1)
    ocupados = [
        (bloqueio.inicio, bloqueio.fim)
        for bloqueio in Bloqueio.objects.filter(
            profissional=profissional,
            inicio__lt=fim_do_dia,
            fim__gt=inicio_do_dia,
        )
    ]
    ocupados += [
        (agendamento.data_hora_inicio, agendamento.data_hora_fim)
        for agendamento in Agendamento.objects.filter(
            profissional=profissional,
            data_hora_inicio__lt=fim_do_dia,
            data_hora_fim__gt=inicio_do_dia,
        )
        .exclude(status=Agendamento.Status.CANCELADO)
        .exclude(pk=getattr(ignorar, "pk", ignorar))
        .only("data_hora_inicio", "data_hora_fim")
    ]

    livres = []
    for faixa in faixas:
        cursor = timezone.make_aware(datetime.combine(data, faixa.hora_inicio))
        fim_faixa = timezone.make_aware(datetime.combine(data, faixa.hora_fim))
        while cursor + duracao <= fim_faixa:
            fim_slot = cursor + duracao
            if not any(
                cursor < fim_ocupado and fim_slot > inicio_ocupado
                for inicio_ocupado, fim_ocupado in ocupados
            ):
                livres.append(cursor)
            cursor += passo
    return livres
