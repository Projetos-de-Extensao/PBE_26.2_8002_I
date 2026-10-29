from functools import update_wrapper

from django.contrib.admin import AdminSite
from django.template.response import TemplateResponse

from agendamento.models import Perfil


class AgendamentoAdminSite(AdminSite):
    site_header = "Administração de Agendamentos"
    site_title = "Administração"
    index_title = "Gerenciamento do sistema"

    def has_permission(self, request):
        return (
            request.user.is_active
            and request.user.is_staff
            and Perfil.objects.filter(
                usuario_id=request.user.pk,
                papel=Perfil.Papel.ADMINISTRADOR,
            ).exists()
        )

    def admin_view(self, view, cacheable=False):
        protected_view = super().admin_view(view, cacheable=cacheable)

        def inner(request, *args, **kwargs):
            if request.user.is_authenticated and not self.has_permission(request):
                return TemplateResponse(
                    request,
                    "admin/access_denied.html",
                    status=403,
                )
            return protected_view(request, *args, **kwargs)

        return update_wrapper(inner, view)


admin_site = AgendamentoAdminSite(name="admin")
