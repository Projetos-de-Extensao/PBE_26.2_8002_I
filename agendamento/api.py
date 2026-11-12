"""API REST do sistema (Django REST Framework), publicada em /api/.

Cada model tem um endpoint com listagem e criação (GET e POST em
``/api/<recurso>/``) e detalhe, edição e exclusão (GET, PUT, PATCH e DELETE em
``/api/<recurso>/<id>/``). Só administradores acessam: a API expõe dados de
todos os usuários.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import ProtectedError, RestrictedError
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

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
from agendamento.serializers import (
    AdministradorSerializer,
    AgendamentoSerializer,
    BloqueioSerializer,
    ClienteSerializer,
    DisponibilidadeSerializer,
    PapelSerializer,
    PerfilSerializer,
    PermissaoSerializer,
    ProfissionalSerializer,
    RecepcionistaSerializer,
    RecorrenciaSerializer,
    RecursoSerializer,
    SalaSerializer,
    ServicoSerializer,
    UsuarioSerializer,
)


class RegistroEmUso(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "O registro está em uso e não pode ser excluído."
    default_code = "registro_em_uso"


@extend_schema_view(
    destroy=extend_schema(
        responses={
            204: OpenApiResponse(description="Excluído."),
            409: OpenApiResponse(
                description=(
                    "O registro está em uso (ex.: tem agendamentos) e não pode "
                    "ser excluído."
                )
            ),
        }
    )
)
class ModelViewSet(viewsets.ModelViewSet):
    # Responde 409 (e não 500) ao excluir registro em uso. Sem docstring de
    # propósito: o Swagger usaria este texto em todas as operações.

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except (ProtectedError, RestrictedError) as erro:
            objetos = erro.protected_objects or erro.restricted_objects
            tipos = sorted({obj._meta.verbose_name_plural for obj in objetos})
            raise RegistroEmUso(
                "Não é possível excluir: existem registros ligados a este item "
                f"({', '.join(tipos)}). Exclua ou altere esses registros antes."
            )


class PermissaoViewSet(ModelViewSet):
    """Permissões que podem ser concedidas a um papel."""

    queryset = Permissao.objects.all()
    serializer_class = PermissaoSerializer


class PapelViewSet(ModelViewSet):
    """Papéis de acesso e as permissões que cada um concede."""

    queryset = Papel.objects.prefetch_related("permissoes")
    serializer_class = PapelSerializer


class UsuarioViewSet(ModelViewSet):
    """Todos os usuários. Para criar, use o endpoint do tipo (clientes,
    profissionais, recepcionistas ou administradores)."""

    queryset = Usuario.objects.select_related("perfil")
    serializer_class = UsuarioSerializer
    http_method_names = ["get", "put", "patch", "delete", "head", "options"]


class ClienteViewSet(ModelViewSet):
    """Clientes (alunos/pacientes). Ao criar, informe a senha; ao editar, deixe a
    senha vazia para mantê-la."""

    queryset = Cliente.objects.select_related("perfil").order_by("nome")
    serializer_class = ClienteSerializer


class ProfissionalViewSet(ModelViewSet):
    """Profissionais que oferecem serviços. Ao criar, informe a senha; ao editar,
    deixe a senha vazia para mantê-la."""

    queryset = Profissional.objects.select_related("perfil")
    serializer_class = ProfissionalSerializer


class RecepcionistaViewSet(ModelViewSet):
    """Recepcionistas, que agendam em nome dos clientes (RF25)."""

    queryset = Recepcionista.objects.select_related("perfil").order_by("nome")
    serializer_class = RecepcionistaSerializer


class AdministradorViewSet(ModelViewSet):
    """Administradores do estabelecimento. São criados com acesso ao painel /admin/."""

    queryset = Administrador.objects.select_related("perfil").order_by("nome")
    serializer_class = AdministradorSerializer


class PerfilViewSet(ModelViewSet):
    """Papel de cada usuário. O perfil é criado junto com o usuário e some
    quando ele é excluído; por isso não há DELETE aqui."""

    queryset = Perfil.objects.select_related("usuario")
    serializer_class = PerfilSerializer
    http_method_names = ["get", "post", "put", "patch", "head", "options"]


class ServicoViewSet(ModelViewSet):
    """Serviços oferecidos por cada profissional; a duração define o término do
    agendamento (RN07)."""

    queryset = Servico.objects.select_related("profissional")
    serializer_class = ServicoSerializer


class DisponibilidadeViewSet(ModelViewSet):
    """Faixas de horário em que o profissional atende, por dia da semana (RF07,
    RN05)."""

    queryset = Disponibilidade.objects.select_related("profissional")
    serializer_class = DisponibilidadeSerializer


class BloqueioViewSet(ModelViewSet):
    """Períodos em que o profissional fecha a agenda (RF20, RN13). A resposta lista
    os agendamentos afetados."""

    queryset = Bloqueio.objects.select_related("profissional")
    serializer_class = BloqueioSerializer


class SalaViewSet(ModelViewSet):
    """Salas físicas. Uma sala não pode ser reservada duas vezes no mesmo intervalo
    (RN03)."""

    queryset = Sala.objects.all()
    serializer_class = SalaSerializer


class RecursoViewSet(ModelViewSet):
    """Equipamentos. Um equipamento exclusivo não pode ser reservado duas vezes no
    mesmo intervalo (RN04)."""

    queryset = Recurso.objects.all()
    serializer_class = RecursoSerializer


class RecorrenciaViewSet(ModelViewSet):
    """Séries semanais de agendamentos (RF16). Depois de criar, use gerar-
    ocorrencias para criar as sessões."""

    queryset = Recorrencia.objects.prefetch_related("recursos", "agendamentos")
    serializer_class = RecorrenciaSerializer

    @extend_schema(
        request=None,
        responses={
            201: inline_serializer(
                "OcorrenciasGeradas",
                {
                    "agendamentos_criados": serializers.ListField(
                        child=serializers.IntegerField()
                    ),
                    "conflitos": serializers.ListField(
                        child=inline_serializer(
                            "ConflitoDeOcorrencia",
                            {
                                "data_hora_inicio": serializers.DateTimeField(),
                                "motivo": serializers.CharField(),
                            },
                        )
                    ),
                },
            ),
            400: OpenApiResponse(
                description="Todas as datas da série tiveram conflito."
            ),
        },
    )
    @action(detail=True, methods=["post"], url_path="gerar-ocorrencias")
    def gerar_ocorrencias(self, request, pk=None):
        """Cria os agendamentos da série; datas com conflito ficam de fora
        (RN11, RN12)."""
        recorrencia = self.get_object()
        try:
            validas, conflitos = recorrencia.gerar_ocorrencias()
        except DjangoValidationError as erro:
            raise serializers.ValidationError(serializers.as_serializer_error(erro))
        return Response(
            {
                "agendamentos_criados": [agendamento.pk for agendamento in validas],
                "conflitos": [
                    {"data_hora_inicio": agendamento.data_hora_inicio, "motivo": motivo}
                    for agendamento, motivo in conflitos
                ],
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=None,
        responses=inline_serializer(
            "SerieCancelada", {"sessoes_canceladas": serializers.IntegerField()}
        ),
    )
    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        """Cancela as sessões futuras e ativas da série (RN10)."""
        canceladas = self.get_object().cancelar()
        return Response({"sessoes_canceladas": canceladas})


class AgendamentoViewSet(ModelViewSet):
    """Agendamentos. A API aplica as regras de conflito (RN01 a RN05 e RN13); o
    término é calculado pelo serviço quando não é enviado."""

    queryset = Agendamento.objects.select_related(
        "cliente", "profissional", "servico", "sala"
    ).prefetch_related("recursos")
    serializer_class = AgendamentoSerializer


# A página /api/ é o Swagger (project/urls.py), não a raiz do router.
router = DefaultRouter()
router.include_root_view = False
router.register("papeis", PapelViewSet)
router.register("permissoes", PermissaoViewSet)
router.register("usuarios", UsuarioViewSet)
router.register("perfis", PerfilViewSet)
router.register("clientes", ClienteViewSet)
router.register("profissionais", ProfissionalViewSet)
router.register("recepcionistas", RecepcionistaViewSet)
router.register("administradores", AdministradorViewSet)
router.register("servicos", ServicoViewSet)
router.register("disponibilidades", DisponibilidadeViewSet)
router.register("bloqueios", BloqueioViewSet)
router.register("salas", SalaViewSet)
router.register("recursos", RecursoViewSet)
router.register("recorrencias", RecorrenciaViewSet)
router.register("agendamentos", AgendamentoViewSet)
