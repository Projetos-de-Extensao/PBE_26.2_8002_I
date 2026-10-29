from django import forms

from .models import DIAS_SEMANA, Agendamento, Bloqueio, Disponibilidade, Recorrencia


class DisponibilidadeForm(forms.ModelForm):
    class Meta:
        model = Disponibilidade
        fields = ["dia_semana", "hora_inicio", "hora_fim"]
        widgets = {
            "hora_inicio": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "hora_fim": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        }


class BloqueioForm(forms.ModelForm):
    class Meta:
        model = Bloqueio
        fields = ["data", "hora_inicio", "hora_fim", "motivo"]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "hora_inicio": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "hora_fim": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        }


class AgendamentoForm(forms.ModelForm):
    """Formulário da tela de novo agendamento (RF10, RF16).

    A hora de término não aparece no formulário: ela é calculada a partir da
    duração do serviço escolhido (RN07).
    Permite marcar repetição semanal para agendamento recorrente (FA2, RF16).
    """

    repetir_semanal = forms.BooleanField(
        label="Repetir agendamento semanalmente",
        required=False,
    )
    dias_semana = forms.MultipleChoiceField(
        label="Dias da semana",
        choices=DIAS_SEMANA,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    data_fim = forms.DateField(
        label="Data final da repetição",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        required=False,
    )

    class Meta:
        model = Agendamento
        fields = ["servico", "profissional", "sala", "recurso", "data", "hora_inicio"]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "hora_inicio": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        }
        labels = {"sala": "Local", "recurso": "Equipamento"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["servico"].required = True
        self.fields["sala"].empty_label = "Não precisa de sala"
        self.fields["recurso"].empty_label = "Não precisa de equipamento"

    def clean(self):
        cleaned_data = super().clean()
        repetir = cleaned_data.get("repetir_semanal")
        if repetir:
            data_inicio = cleaned_data.get("data")
            data_fim = cleaned_data.get("data_fim")
            dias_semana = cleaned_data.get("dias_semana")

            if not data_fim:
                self.add_error(
                    "data_fim", "Informe a data final para a repetição do agendamento."
                )
            elif data_inicio and data_fim < data_inicio:
                self.add_error(
                    "data_fim",
                    "A data final deve ser posterior ou igual à data inicial.",
                )

            if not dias_semana and data_inicio:
                cleaned_data["dias_semana"] = [str(data_inicio.weekday())]

        return cleaned_data


class RecorrenciaForm(forms.ModelForm):
    """Formulário para configuração direta de agendamento recorrente (RF16)."""

    dias_semana = forms.MultipleChoiceField(
        label="Dias da semana",
        choices=DIAS_SEMANA,
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )

    class Meta:
        model = Recorrencia
        fields = [
            "servico",
            "profissional",
            "sala",
            "recurso",
            "dias_semana",
            "data_inicio",
            "data_fim",
            "hora_inicio",
            "observacao",
        ]
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "data_fim": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "hora_inicio": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        }
        labels = {
            "sala": "Local",
            "recurso": "Equipamento",
            "data_inicio": "Data de início",
            "data_fim": "Data de término",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["servico"].required = True
        self.fields["sala"].empty_label = "Não precisa de sala"
        self.fields["recurso"].empty_label = "Não precisa de equipamento"
