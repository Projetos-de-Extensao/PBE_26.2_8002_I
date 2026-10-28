from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from agendamento.models import Perfil, Usuario


class UsuarioCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("email", "nome")


class UsuarioChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Usuario
        fields = "__all__"


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    add_form = UsuarioCreationForm
    form = UsuarioChangeForm
    list_display = ("email", "nome", "papel", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("email", "nome")
    ordering = ("email",)
    readonly_fields = ("papel",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Dados pessoais", {"fields": ("nome", "first_name", "last_name")}),
        (
            "Permissões",
            {
                "fields": (
                    "papel",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Datas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "nome", "password1", "password2"),
            },
        ),
    )
    filter_horizontal = ("groups", "user_permissions")

    @admin.display(description="Papel", ordering="perfil__papel")
    def papel(self, usuario):
        return usuario.perfil.get_papel_display()


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("usuario", "papel")
    list_editable = ("papel",)
    list_filter = ("papel",)
    search_fields = ("usuario__email", "usuario__nome")
    autocomplete_fields = ("usuario",)

    def has_delete_permission(self, request, obj=None):
        return False
