from django import forms
from django.db.models import Q

from common.fechas import FECHA_INICIO_OPERACIONES, fecha_maxima_agenda
from instalaciones.models import Cancha, Sede
from membresias.models import Membresia, Plan
from usuarios.models import Rol, Usuario


class FechasForm(forms.Form):
    desde = forms.DateField(label="Desde", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    hasta = forms.DateField(label="Hasta", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs["class"] = "form-control"

    def clean(self):
        datos = super().clean()
        desde, hasta = datos.get("desde"), datos.get("hasta")
        if desde and hasta:
            if desde > hasta:
                raise forms.ValidationError("La fecha desde debe ser anterior o igual a hasta.")
            if desde < FECHA_INICIO_OPERACIONES or hasta > fecha_maxima_agenda():
                raise forms.ValidationError("El período debe estar dentro del calendario operativo de la agenda.")
        return datos


class ContratacionesForm(FechasForm):
    usuario = forms.ModelChoiceField(label="Titular", queryset=Usuario.objects.order_by("last_name", "first_name", "pk"), required=False, empty_label="Todos")
    tipo = forms.ChoiceField(label="Tipo", choices=(("", "Todos"), ("plan", "Plan"), ("membresia", "Membresía")), required=False)
    producto = forms.ChoiceField(label="Producto", required=False)
    situacion = forms.ChoiceField(label="Situación financiera", required=False, choices=(
        ("", "Todas"), ("cubierto", "Cubierto"), ("faltante", "Falta cobrar"),
        ("excedente", "Excedente por resolver"), ("anulada", "Anulada"),
    ))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["desde"].label = "Alta desde"
        self.fields["hasta"].label = "Alta hasta"
        self.fields["producto"].choices = [("", "Todos")] + [
            (f"{tipo}:{producto.pk}", producto.nombre)
            for tipo, modelo in (("plan", Plan), ("membresia", Membresia))
            for producto in modelo.objects.order_by("nombre", "pk")
        ]

    def clean(self):
        datos = super().clean()
        if datos.get("tipo") and datos.get("producto") and not datos["producto"].startswith(datos["tipo"] + ":"):
            self.add_error("producto", "El producto no corresponde al tipo seleccionado.")
        return datos


class AsistenciaForm(FechasForm):
    usuario = forms.ModelChoiceField(label="Alumno o participante", queryset=Usuario.objects.order_by("last_name", "first_name", "pk"), required=False, empty_label="Todos")
    plan = forms.ModelChoiceField(label="Plan", queryset=Plan.objects.order_by("nombre", "pk"), required=False, empty_label="Todos, incluye sin plan")
    profesor = forms.ModelChoiceField(label="Profesor", queryset=Usuario.objects.filter(
        Q(roles__rol__codigo=Rol.PROFESOR) | Q(clases_como_profesor__isnull=False),
    ).distinct().order_by("last_name", "first_name", "pk"), required=False, empty_label="Todos")
    sede = forms.ModelChoiceField(label="Sede", queryset=Sede.objects.order_by("nombre", "pk"), required=False, empty_label="Todas")


class ReservasForm(FechasForm):
    sede = forms.ModelChoiceField(label="Sede", queryset=Sede.objects.order_by("nombre", "pk"), required=False, empty_label="Todas")
    cancha = forms.ModelChoiceField(label="Cancha", queryset=Cancha.objects.select_related("sede").order_by("sede__nombre", "nombre", "pk"), required=False, empty_label="Todas")
    modalidad = forms.ChoiceField(label="Modalidad", required=False, choices=(("", "Todas"), ("normal", "Normal"), ("membresia", "Con membresía")))
    estado = forms.ChoiceField(label="Estado", required=False, choices=(("", "Todos"), ("programado", "Programado"), ("finalizado", "Finalizado"), ("anulado", "Anulado")))

    def clean(self):
        datos = super().clean()
        if datos.get("sede") and datos.get("cancha") and datos["cancha"].sede_id != datos["sede"].pk:
            self.add_error("cancha", "La cancha no pertenece a la sede seleccionada.")
        return datos
