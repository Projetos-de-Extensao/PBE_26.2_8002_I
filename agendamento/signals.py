from django.core.exceptions import ValidationError
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from agendamento.models import (
    Administrador,
    Agendamento,
    Cliente,
    Perfil,
    Profissional,
    Recepcionista,
    Recurso,
    Usuario,
)


@receiver(post_save)
def criar_perfil_de_usuario(sender, instance, created, using, **kwargs):
    if not created or not isinstance(instance, Usuario):
        return

    papel = getattr(instance, "_papel_inicial", None)
    if papel is not None:
        papel = str(papel).strip().casefold()
        papeis_validos = {valor for valor, _ in Perfil.Papel.choices}
        papeis_validos.update(
            rotulo.casefold() for _, rotulo in Perfil.Papel.choices
        )
        if papel not in papeis_validos:
            raise ValueError(f"Papel de usuário inválido: {papel}")
        papel = next(
            valor
            for valor, rotulo in Perfil.Papel.choices
            if papel in (valor, rotulo.casefold())
        )
    elif instance.is_superuser or isinstance(instance, Administrador):
        papel = Perfil.Papel.ADMINISTRADOR
    elif isinstance(instance, Recepcionista):
        papel = Perfil.Papel.RECEPCIONISTA
    elif isinstance(instance, Profissional):
        papel = Perfil.Papel.PROFISSIONAL
    elif isinstance(instance, Cliente):
        papel = Perfil.Papel.CLIENTE
    else:
        papel = Perfil.Papel.CLIENTE

    Perfil.objects.using(using).get_or_create(
        usuario_id=instance.pk,
        defaults={"papel": papel},
    )


@receiver(m2m_changed, sender=Agendamento.recursos.through)
def validar_equipamentos_do_agendamento(sender, instance, action, pk_set, reverse, **kwargs):
    """RN04: impede vincular um equipamento exclusivo já reservado no horário.

    A verificação em ``Agendamento.clean()`` não alcança os equipamentos, que
    só podem ser ligados depois que o agendamento é salvo. Sem esta checagem,
    um atendimento criado pelo admin consegue reservar o mesmo equipamento
    exclusivo duas vezes no mesmo intervalo.
    """
    if action != "pre_add" or reverse or not pk_set:
        return
    recursos = list(Recurso.objects.filter(pk__in=pk_set))
    motivos = instance.conflitos_de_recursos(recursos=recursos)
    if motivos:
        raise ValidationError(motivos)
