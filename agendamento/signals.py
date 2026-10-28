from django.db.models.signals import post_save
from django.dispatch import receiver

from agendamento.models import (
    Administrador,
    Cliente,
    Perfil,
    Profissional,
    Recepcionista,
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
