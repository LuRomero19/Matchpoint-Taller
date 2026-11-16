from django import forms
from django.core import signing

from .models import ConfiguracionNotificaciones


class ConfiguracionNotificacionesForm(forms.ModelForm):
    version = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = ConfiguracionNotificaciones
        fields = (
            "anticipacion_clases_minutos", "anticipacion_reservas_minutos", "dia_apertura_continuidad",
            "dia_recordatorio_continuidad", "dia_cierre_continuidad", "hora_continuidad",
        )
        help_texts = {
            "anticipacion_clases_minutos": "Entre 1 y 1440 minutos (un día).",
            "anticipacion_reservas_minutos": "Entre 1 y 1440 minutos (un día).",
            "dia_apertura_continuidad": "Del 1 al 27, para dejar un recordatorio posterior incluso en febrero.",
            "dia_recordatorio_continuidad": "Posterior a la apertura. Si el día no existe, se usa el último del mes.",
            "dia_cierre_continuidad": "Inclusive, en el mes siguiente. Debe ser anterior al día de apertura para no superponer campañas.",
            "hora_continuidad": "Horario de Salta, para apertura y ambos recordatorios.",
        }
        widgets = {"hora_continuidad": forms.TimeInput(format="%H:%M", attrs={"type": "time", "step": "60"})}

    def __init__(self, *args, campo, **kwargs):
        super().__init__(*args, **kwargs)
        if campo not in self._meta.fields:
            raise ValueError("La regla de notificación no es válida.")
        self.campo = campo
        self.valor_vigente = self.instance._meta.get_field(campo).value_to_string(self.instance)
        self.firma = signing.Signer(salt="comunicaciones.regla_notificacion")
        for nombre in tuple(self.fields):
            if nombre not in (campo, "version"):
                del self.fields[nombre]
        self.fields["version"].initial = self.firma.sign_object({"campo": campo, "valor": self.valor_vigente})
        if campo == "hora_continuidad":
            self.fields[campo].input_formats = ["%H:%M"]
        self.fields[campo].widget.attrs["class"] = "form-control"

    def clean(self):
        datos = super().clean()
        apertura = datos.get("dia_apertura_continuidad", self.instance.dia_apertura_continuidad)
        recordatorio = datos.get("dia_recordatorio_continuidad", self.instance.dia_recordatorio_continuidad)
        cierre = datos.get("dia_cierre_continuidad", self.instance.dia_cierre_continuidad)
        if apertura and recordatorio and recordatorio <= apertura:
            self.add_error(self.campo, "El recordatorio debe ser posterior a la apertura.")
        if apertura and cierre and cierre >= apertura:
            self.add_error(self.campo, "El cierre debe ser anterior al día de apertura de la siguiente campaña.")
        if datos.get("version"):
            try:
                version = self.firma.unsign_object(datos["version"])
            except signing.BadSignature:
                raise forms.ValidationError("Volvé a abrir la edición de esta regla.") from None
            if version != {"campo": self.campo, "valor": self.valor_vigente}:
                raise forms.ValidationError("La regla cambió. Volvé a abrir su edición para consultar el valor vigente.")
        return datos
