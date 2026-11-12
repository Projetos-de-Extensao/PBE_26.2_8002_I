from rest_framework import permissions


class EhAdministrador(permissions.BasePermission):
    """Mesma regra do painel /admin/: usuário ativo, staff e com papel administrador.

    Fica fora de ``agendamento.api`` porque o settings do REST framework a
    importa antes de os ViewSets serem carregados.
    """

    message = "A API é restrita a administradores."

    def has_permission(self, request, view):
        from agendamento.admin_site import admin_site

        return bool(request.user and request.user.is_authenticated) and (
            admin_site.has_permission(request)
        )
