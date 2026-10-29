from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

from agendamento.admin_site import admin_site
from agendamento.models import Perfil, Profissional, Sala, Servico, Usuario


class UsuarioCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("email", "nome")


class UsuarioChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Usuario
        fields = "__all__"


@admin.register(Usuario, site=admin_site)
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


@admin.register(Perfil, site=admin_site)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("usuario", "papel")
    list_editable = ("papel",)
    list_filter = ("papel",)
    search_fields = ("usuario__email", "usuario__nome")
    autocomplete_fields = ("usuario",)

    def has_delete_permission(self, request, obj=None):
        return False


class ProfissionalCreationForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput,
    )
    password2 = forms.CharField(
        label="Confirme a senha",
        widget=forms.PasswordInput,
    )

    class Meta:
        model = Profissional
        fields = (
            "email",
            "nome",
            "especialidade",
            "modalidade",
            "formacao",
            "apresentacao",
        )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "As senhas não coincidem.")
        if password1:
            try:
                validate_password(password1, user=self.instance)
            except ValidationError as error:
                self.add_error("password1", error)
        return cleaned_data


class ProfissionalChangeForm(forms.ModelForm):
    class Meta:
        model = Profissional
        fields = (
            "email",
            "nome",
            "especialidade",
            "modalidade",
            "formacao",
            "apresentacao",
            "is_active",
        )


@admin.register(Profissional, site=admin_site)
class ProfissionalAdmin(admin.ModelAdmin):
    form = ProfissionalChangeForm
    add_form = ProfissionalCreationForm
    list_display = ("nome", "email", "especialidade", "modalidade", "is_active")
    list_filter = ("is_active", "especialidade", "modalidade")
    search_fields = ("nome", "email", "especialidade")

    def get_form(self, request, obj=None, **kwargs):
        kwargs["form"] = self.add_form if obj is None else self.form
        return super().get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.set_password(form.cleaned_data["password1"])
        super().save_model(request, obj, form, change)


@admin.register(Servico, site=admin_site)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "profissional", "duracao_minutos")
    list_filter = ("tipo",)
    search_fields = ("nome", "tipo", "profissional__nome")
    autocomplete_fields = ("profissional",)


@admin.register(Sala, site=admin_site)
class SalaAdmin(admin.ModelAdmin):
    list_display = ("nome", "capacidade")
    search_fields = ("nome",)
