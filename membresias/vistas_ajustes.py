from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .ajustes import admite_ajustes, confirmar_ajuste, leer_revision_ajuste, preparar_ajuste
from .forms import AjusteHorasForm
from .models import MembresiaUsuario
from .servicios import exigir_administracion_membresias


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def ajustar_horas(request, pk):
    actor = exigir_administracion_membresias(request.user)
    contratacion = get_object_or_404(MembresiaUsuario.objects.select_related("usuario", "membresia"), pk=pk)
    destino = reverse("membresias:contratacion_membresia_detalle", args=[pk])
    if not admite_ajustes(contratacion):
        messages.error(request, "Sólo se ajustan contrataciones Activas del mes vigente o de un período futuro.")
        return redirect(destino)
    paso = request.POST.get("paso") if request.method == "POST" else None
    datos = request.POST if request.method == "POST" else None
    error_revision = None
    if paso in ("editar", "confirmar"):
        try:
            firmado = leer_revision_ajuste(actor, request.POST.get("confirmacion"), contratacion_id=pk)
            datos = firmado["datos"]
            if paso == "confirmar":
                confirmar_ajuste(actor, request.POST.get("confirmacion"), contratacion_id=pk)
                messages.success(request, "El ajuste de horas fue registrado.")
                return redirect(destino)
        except ValidationError as error:
            error_revision = error
    formulario = AjusteHorasForm(datos)
    if error_revision:
        formulario.is_valid()
        formulario.add_error(None, error_revision)
    revision = None
    if paso == "revisar" and formulario.is_valid():
        try:
            revision = preparar_ajuste(actor, pk, **formulario.cleaned_data)
        except ValidationError as error:
            formulario.add_error(None, error)
    return render(request, "membresias/ajuste_horas_formulario.html", {
        "titulo": "Ajustar horas",
        "contratacion": contratacion, "formulario": formulario,
        "revision": revision, "url_cancelar": destino,
    })
