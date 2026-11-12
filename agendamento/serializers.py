from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from agendamento.models import (
    Administrador,
    Agendamento,
    Bloqueio,
    Cliente,
    Disponibilidade,
    Papel,
    Perfil,
    Permissao,
    Profissional,
    Recepcionista,
    Recorrencia,
    Recurso,
    Sala,
    Servico,
    Usuario,
)


class RegrasDoModeloMixin:
    """Roda o ``clean()`` do model antes de salvar.

    Assim a API respeita as mesmas regras de negócio das telas (RN01 a RN13)
    e devolve 400 com a mensagem, em vez de gravar dado inválido ou dar 500.
    """

    def validate(self, attrs):
        attrs = super().validate(attrs)
        modelo = self.Meta.model
        muitos_para_muitos = {campo.name for campo in modelo._meta.many_to_many}
        simples = {
            nome: valor
            for nome, valor in attrs.items()
            if nome not in muitos_para_muitos and nome != "password"
        }
        if self.instance is None:
            instancia = modelo(**simples)
        else:
            instancia = self.instance
            for nome, valor in simples.items():
                setattr(instancia, nome, valor)
        try:
            instancia.clean()
            self.validar_instancia(instancia, attrs)
        except DjangoValidationError as erro:
            raise serializers.ValidationError(serializers.as_serializer_error(erro))
        # clean() pode normalizar valores (ex.: dias_semana "1, 3" -> [1, 3]).
        for nome in simples:
            attrs[nome] = getattr(instancia, nome)
        return attrs

    def validar_instancia(self, instancia, attrs):
        """Regras extras de cada serializer; lança ValidationError do Django."""


class PermissaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permissao
        fields = ["id", "nome", "descricao"]


class PapelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Papel
        fields = ["id", "nome", "permissoes"]


class UsuarioSerializer(RegrasDoModeloMixin, serializers.ModelSerializer):
    """Campos comuns a todos os usuários. A senha só é aceita na escrita."""

    password = serializers.CharField(
        label="Senha",
        write_only=True,
        required=False,
        style={"input_type": "password"},
        help_text="Obrigatória ao criar. Ao editar, deixe vazio para manter a atual.",
    )
    papel = serializers.CharField(source="perfil.papel", read_only=True)

    class Meta:
        model = Usuario
        fields = ["id", "email", "nome", "telefone", "is_active", "papel", "password"]

    def validate_password(self, valor):
        if not valor:
            return valor
        try:
            validate_password(valor, self.instance)
        except DjangoValidationError as erro:
            raise serializers.ValidationError(list(erro.messages))
        return valor

    def validar_instancia(self, instancia, attrs):
        if self.instance is None and not attrs.get("password"):
            raise DjangoValidationError({"password": "Informe a senha do usuário."})

    def create(self, validated_data):
        senha = validated_data.pop("password")
        usuario = self.Meta.model(**validated_data)
        usuario.set_password(senha)
        usuario.save()
        return usuario

    def update(self, instance, validated_data):
        senha = validated_data.pop("password", None)
        instance = super().update(instance, validated_data)
        if senha:
            instance.set_password(senha)
            instance.save(update_fields=["password"])
        return instance


class ClienteSerializer(UsuarioSerializer):
    class Meta(UsuarioSerializer.Meta):
        model = Cliente


class ProfissionalSerializer(UsuarioSerializer):
    class Meta(UsuarioSerializer.Meta):
        model = Profissional
        fields = UsuarioSerializer.Meta.fields + [
            "especialidade",
            "modalidade",
            "formacao",
            "apresentacao",
        ]


class RecepcionistaSerializer(UsuarioSerializer):
    class Meta(UsuarioSerializer.Meta):
        model = Recepcionista


class AdministradorSerializer(UsuarioSerializer):
    class Meta(UsuarioSerializer.Meta):
        model = Administrador

    def create(self, validated_data):
        # O painel administrativo exige is_staff junto com o papel de administrador.
        validated_data["is_staff"] = True
        return super().create(validated_data)


class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = ["id", "usuario", "papel"]


class ServicoSerializer(RegrasDoModeloMixin, serializers.ModelSerializer):
    class Meta:
        model = Servico
        fields = ["id", "profissional", "nome", "tipo", "duracao_minutos"]


class DisponibilidadeSerializer(RegrasDoModeloMixin, serializers.ModelSerializer):
    dia_semana_nome = serializers.CharField(
        source="get_dia_semana_display", read_only=True
    )

    class Meta:
        model = Disponibilidade
        fields = [
            "id",
            "profissional",
            "dia_semana",
            "dia_semana_nome",
            "hora_inicio",
            "hora_fim",
        ]


class BloqueioSerializer(RegrasDoModeloMixin, serializers.ModelSerializer):
    agendamentos_afetados = serializers.SerializerMethodField(
        help_text="Atendimentos ativos que caem dentro do bloqueio (RN13)."
    )

    class Meta:
        model = Bloqueio
        fields = [
            "id",
            "profissional",
            "inicio",
            "fim",
            "motivo",
            "agendamentos_afetados",
        ]

    def get_agendamentos_afetados(self, bloqueio) -> list[int]:
        return [agendamento.pk for agendamento in bloqueio.agendamentos_afetados()]


class SalaSerializer(RegrasDoModeloMixin, serializers.ModelSerializer):
    class Meta:
        model = Sala
        fields = ["id", "nome", "capacidade"]


class RecursoSerializer(RegrasDoModeloMixin, serializers.ModelSerializer):
    class Meta:
        model = Recurso
        fields = ["id", "nome", "exclusivo"]


class RecorrenciaSerializer(RegrasDoModeloMixin, serializers.ModelSerializer):
    class Meta:
        model = Recorrencia
        fields = [
            "id",
            "padrao",
            "cliente",
            "profissional",
            "servico",
            "sala",
            "recursos",
            "dias_semana",
            "data_inicio",
            "hora_inicio",
            "data_termino",
            "agendamentos",
        ]
        read_only_fields = ["agendamentos"]


class AgendamentoSerializer(RegrasDoModeloMixin, serializers.ModelSerializer):
    class Meta:
        model = Agendamento
        fields = [
            "id",
            "cliente",
            "profissional",
            "servico",
            "recepcionista",
            "sala",
            "recursos",
            "recorrencia",
            "data_hora_inicio",
            "data_hora_fim",
            "status",
        ]
        extra_kwargs = {
            "data_hora_fim": {
                "required": False,
                "help_text": "Se ficar vazio, é calculado pela duração do serviço (RN07).",
            }
        }

    def validate(self, attrs):
        servico = attrs.get("servico", getattr(self.instance, "servico", None))
        profissional = attrs.get(
            "profissional", getattr(self.instance, "profissional", None)
        )
        if servico and profissional and servico.profissional_id != profissional.pk:
            raise serializers.ValidationError(
                {"servico": "Este serviço não é oferecido pelo profissional escolhido."}
            )
        return super().validate(attrs)

    def validar_instancia(self, agendamento, attrs):
        if "recursos" in attrs:
            motivos = agendamento.conflitos_de_recursos(recursos=attrs["recursos"])
            if motivos:
                raise DjangoValidationError({"recursos": motivos})
        # clean() calcula o término quando ele não foi enviado (RN07).
        attrs["data_hora_fim"] = agendamento.data_hora_fim
