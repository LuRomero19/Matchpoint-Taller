from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .ajustes import confirmar_ajuste_importe, leer_revision_importe, preparar_ajuste_importe
from .finanzas import resumen_financiero
from .forms import AjusteImporteForm
from .ingresos import ORIGENES, consultar_origen, url_del_origen
from .servicios import exigir_acceso_caja


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def ajustar_importe(request, tipo, origen_id):
    actor = exigir_acceso_caja(request.user)
    if tipo not in ORIGENES:
        raise Http404
    try:
        origen = consultar_origen(tipo, origen_id)
    except ValidationError:
        raise Http404 from None
    destino = url_del_origen(tipo, origen_id)
    paso = request.POST.get("paso") if request.method == "POST" else None
    datos = request.POST if request.method == "POST" else None
    error_revision = None
    if paso in ("editar", "confirmar"):
        try:
            firmado = leer_revision_importe(actor, request.POST.get("confirmacion"), tipo, origen_id)
            datos = firmado
            if paso == "confirmar":
                confirmar_ajuste_importe(actor, tipo, origen_id, request.POST.get("confirmacion"))
                messages.success(request, "El importe acordado fue ajustado.")
                return redirect(destino)
        except ValidationError as error:
            error_revision = error
    origen.refresh_from_db()
    finanzas = resumen_financiero(tipo, origen)
    if finanzas["operacion_anulada"]:
        messages.error(request, "Una operación anulada no admite ajustes de importe.")
        return redirect(destino)
    if finanzas["maximo_ingreso"] <= 0:
        messages.error(request, "El importe acordado ya está cubierto. No admite ajustes de importe.")
        return redirect(destino)
    formulario = AjusteImporteForm(datos)
    if error_revision:
        formulario.is_valid()
        formulario.add_error(None, error_revision)
    revision = None
    if paso == "revisar" and formulario.is_valid():
        try:
            revision = preparar_ajuste_importe(actor, tipo, origen_id, **formulario.cleaned_data)
        except ValidationError as error:
            formulario.add_error(None, error)
    return render(request, "caja/ajuste_importe_formulario.html", {
        "origen": origen, "finanzas": finanzas, "formulario": formulario,
        "revision": revision, "url_cancelar": destino,
    })
