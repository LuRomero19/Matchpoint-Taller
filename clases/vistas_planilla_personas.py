from collections import Counter
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from instalaciones.models import Cancha

from .forms import PersonasPlanillaForm
from .permisos import exigir_administracion_clases
from .planilla_personas import (
    ACCIONES, aplicar_cambio_personas, consultar_seleccion, personas_asignadas,
    seleccionar_horarios,
)


@login_required
@never_cache
@require_POST
def gestionar_personas(request):
    usuario = exigir_administracion_clases(request.user)
    token = request.POST.get("seleccion", "")
    try:
        if not token:
            cancha_id = request.POST.get("cancha", "")
            if not cancha_id.isdecimal() or len(cancha_id) > 18:
                raise Http404("Elegí una cancha válida.")
            cancha = get_object_or_404(Cancha, pk=int(cancha_id))
            token = seleccionar_horarios(usuario, cancha, request.POST.getlist("turno"), request.POST.get("funcion"))
        seleccion = consultar_seleccion(usuario, token)
    except ValidationError as error:
        for mensaje in error.messages:
            messages.error(request, mensaje)
        return redirect("clases:planilla")
    cancha = seleccion["cancha"]
    url_planilla = reverse("clases:planilla") + "?" + urlencode({"sede": cancha.sede_id, "cancha": cancha.pk})
    paso = request.POST.get("paso", "")
    accion = request.POST.get("accion", "")
    if accion not in ACCIONES:
        raise Http404("Elegí agregar o quitar personas.")
    formulario = PersonasPlanillaForm(
        request.POST if paso == "guardar" else None,
        funcion=seleccion["funcion"], accion=accion, turnos=seleccion["turnos"],
    )
    campo = formulario[seleccion["funcion"]]
    personas = formulario.seleccionados(seleccion["funcion"])
    disponibles = []
    if accion == "quitar":
        alcance = Counter(
            pk for turno in seleccion["turnos"] for pk in personas_asignadas(turno, seleccion["funcion"])
        )
        elegidos = {persona.pk for persona in personas}
        disponibles = [
            {"persona": persona, "cantidad": alcance[persona.pk], "elegida": persona.pk in elegidos}
            for persona in formulario.fields[seleccion["funcion"]].queryset.order_by("last_name", "first_name", "pk")
        ]
    if paso == "guardar" and formulario.is_valid():
        ids = set(formulario.cleaned_data[seleccion["funcion"]].values_list("pk", flat=True))
        try:
            resultado = aplicar_cambio_personas(usuario, token, accion, ids)
            messages.success(request, f"Asignaciones modificadas: {resultado['vinculos']}. Horarios actualizados: {resultado['horarios_modificados']}.")
            return redirect(url_planilla)
        except ValidationError as error:
            formulario.add_error(None, error)
    return render(request, "clases/planilla_personas.html", {
        **seleccion, "seleccion": token, "accion": accion, "formulario": formulario,
        "campo": campo, "personas": personas, "disponibles": disponibles,
        "url_planilla": url_planilla,
    })
