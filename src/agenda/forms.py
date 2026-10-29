from django import forms

from .models import Agendamento


class AgendamentoForm(forms.ModelForm):
    """Formulário da tela de novo agendamento (RF10).

    A hora de término não aparece no formulário: ela é calculada a partir da
    duração do serviço escolhido (RN07).
    """

    class Meta:
        model = Agendamento
        fields = ["servico", "profissional", "sala", "recurso", "data", "hora_inicio"]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}),
            "hora_inicio": forms.TimeInput(attrs={"type": "time"}),
        }
        labels = {
            "sala": "Local",
            "recurso": "Equipamento",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["servico"].required = True
        self.fields["sala"].empty_label = "Não precisa de sala"
        self.fields["recurso"].empty_label = "Não precisa de equipamento"
