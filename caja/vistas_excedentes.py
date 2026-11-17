from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .excedentes import leer_revision_excedente, revision_excedente
from .finanzas import resumen_financiero
from .forms import ExcedenteForm
from .ingresos import ORIGENES, consultar_origen, url_del_origen
from .models import SesionCaja
from .movimientos import registrar_movimiento
from .servicios import exigir_acceso_caja


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def ingreso_excedente(request, pk, tipo, origen_id):
    actor = exigir_acceso_caja(request.user)
    sesion = get_object_or_404(SesionCaja, pk=pk)
    if sesion.responsable_id != actor.pk:
        raise PermissionDenied
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
            firmado = leer_revision_excedente(actor, pk, tipo, origen_id, request.POST.get("confirmacion"))
            datos = firmado["datos"]
            if paso == "confirmar":
                formulario = ExcedenteForm(datos)
                if formulario.is_valid():
                    movimiento = registrar_movimiento(actor, pk, clase="ingreso", tipo_origen=tipo, origen_id=origen_id,
                                                      revision_excedente=request.POST.get("confirmacion"), **formulario.cleaned_data)
                    messages.success(request, f"El cobro {movimiento.numero} fue registrado con excedente.")
                    return redirect("caja:movimiento_detalle", pk=movimiento.pk)
        except ValidationError as error:
            error_revision = error
    origen.refresh_from_db()
    finanzas = resumen_financiero(tipo, origen)
    sesion.refresh_from_db()
    if finanzas["operacion_anulada"] or sesion.estado != "abierta":
        messages.error(request, "El origen está anulado o la sesión está cerrada. No admite nuevos cobros.")
        return redirect(destino)
    if finanzas["maximo_ingreso"] <= 0:
        messages.error(request, "El importe acordado ya está cubierto. No admite cobros con excedente.")
        return redirect(destino)
    formulario = ExcedenteForm(datos)
    if error_revision:
        formulario.is_valid()
        formulario.add_error(None, error_revision)
    revision = None
    confirmacion = None
    if paso == "revisar" and formulario.is_valid():
        try:
            confirmacion = revision_excedente(actor, pk, tipo, origen_id, formulario.cleaned_data, finanzas)
            revision = formulario.cleaned_data
        except ValidationError as error:
            formulario.add_error(None, error)
    return render(request, "caja/excedente_formulario.html", {
        "origen": origen, "sesion": sesion, "finanzas": finanzas, "formulario": formulario,
        "revision": revision, "confirmacion": confirmacion, "url_cancelar": destino,
        "medio_texto": dict(formulario.fields["medio_pago"].choices).get(revision["medio_pago"]) if revision else None,
        "excedente_resultante": finanzas["neto_recibido"] + revision["monto"] - finanzas["importe_acordado"] if revision else None,
    })
