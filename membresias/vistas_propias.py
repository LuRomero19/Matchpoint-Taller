from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from usuarios.models import Usuario

from caja.consultas import contexto_financiero

from .ajustes import contexto_horas_contratacion
from .consultas import listar_contrataciones
from .models import MembresiaUsuario, PlanUsuario
from .continuidad import contexto_continuidad


MODELOS_CONTRATACIONES = {"plan": PlanUsuario, "membresia": MembresiaUsuario}


def _exigir_titular(usuario):
    if not usuario.is_authenticated:
        raise PermissionDenied
    return get_object_or_404(
        Usuario, pk=usuario.pk, is_active=True, correo_verificado_en__isnull=False, debe_cambiar_contrasena=False,
    )


def _contexto(tipo):
    url_lista = reverse("membresias:mis_contrataciones") + f"?tipo={tipo}"
    return {
        "propias": True, "tipo": tipo, "plural": "planes" if tipo == "plan" else "membresías",
        "nombre_tipo": "plan" if tipo == "plan" else "membresía",
        "titulo_lista": "Mis contrataciones", "url_lista": url_lista,
        "ruta_detalle": f"membresias:mi_{tipo}_contratado",
        "ruta_comprobante": f"membresias:mi_{tipo}_comprobante",
        "etiqueta_importe": "Importe aplicado (ARS)",
    }


@login_required
@never_cache
@require_GET
def mis_contrataciones(request):
    titular = _exigir_titular(request.user)
    tipo = request.GET.get("tipo", "plan")
    if tipo not in MODELOS_CONTRATACIONES:
        tipo = "plan"
    if not request.GET.get("tipo") and not PlanUsuario.objects.filter(usuario=titular).exists():
        if MembresiaUsuario.objects.filter(usuario=titular).exists():
            tipo = "membresia"
    modelo = MODELOS_CONTRATACIONES[tipo]
    contrataciones = modelo.objects.filter(usuario=titular).select_related("usuario", tipo)
    datos = listar_contrataciones(contrataciones, request.GET, tipo=tipo, buscar_usuario=False)
    datos["parametros"] = urlencode({
        "tipo": tipo, "q": datos["busqueda"], "estado": datos["estado_actual"], "mes": datos["mes_actual"],
    })
    return render(request, "membresias/contratacion_lista.html", {**datos, **_contexto(tipo)})


@login_required
@never_cache
@require_GET
def contratacion_propia_detalle(request, pk, tipo="plan"):
    titular = _exigir_titular(request.user)
    modelo = MODELOS_CONTRATACIONES[tipo]
    contratacion = get_object_or_404(
        modelo.objects.filter(usuario=titular).select_related("usuario", tipo), pk=pk,
    )
    return render(request, "membresias/contratacion_detalle.html", {
        **contexto_financiero(request.user, tipo, contratacion, request.GET),
        **_contexto(tipo), "contratacion": contratacion,
        **(contexto_horas_contratacion(contratacion, request.GET, administrador=False) if tipo == "membresia" else {}),
        **contexto_continuidad(contratacion, titular, tipo=tipo),
    })


@login_required
@never_cache
@require_GET
def contratacion_propia_comprobante(request, pk, tipo="plan"):
    titular = _exigir_titular(request.user)
    modelo = MODELOS_CONTRATACIONES[tipo]
    contratacion = get_object_or_404(
        modelo.objects.filter(usuario=titular).select_related("usuario", tipo), pk=pk,
    )
    return render(request, "membresias/contratacion_comprobante.html", {
        **_contexto(tipo), "contratacion": contratacion,
    })


@login_required
@never_cache
@require_GET
def uso_membresia_propia(request, pk):
    from reservas.horas import resumen_horas_del_mes
    from reservas.models import Reserva, ReservaInvitado

    titular = _exigir_titular(request.user)
    contrato = get_object_or_404(
        MembresiaUsuario.objects.select_related("membresia"), pk=pk, usuario=titular,
    )
    reservas = Reserva.objects.filter(
        organizador=titular, membresia_usuario=contrato,
    ).select_related("evento__turno__cancha__sede").order_by("evento__turno__fecha", "evento__turno__hora_inicio")
    invitaciones = ReservaInvitado.objects.filter(
        usuario=titular, membresia_usuario=contrato,
    ).select_related("reserva__evento__turno__cancha__sede").order_by(
        "reserva__evento__turno__fecha", "reserva__evento__turno__hora_inicio",
    )
    return render(request, "reservas/uso_membresia.html", {
        "titular": titular, "contrato": contrato,
        "meses": resumen_horas_del_mes(titular.pk, contrato.mes_cubierto, contrato),
        "reservas": reservas,
        "invitaciones": [{"invitacion": i, "respuesta_texto": i.get_respuesta_display()} for i in invitaciones],
    })
