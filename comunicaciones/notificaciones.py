from django.core.exceptions import ValidationError
from django.urls import reverse

from usuarios.models import Usuario

from .models import EnvioEmail, Notificacion


MENSAJES_BREVES = {
    EnvioEmail.Tipo.INVITACION: "Te invitaron a participar en una reserva.",
    EnvioEmail.Tipo.RESERVA_ANULADA: "Se anuló una reserva en la que participabas.",
    EnvioEmail.Tipo.CLASE_ANULADA: "Se anuló una de tus clases.",
    EnvioEmail.Tipo.CANCHA_CAMBIADA: "Tu clase cambió de cancha.",
    EnvioEmail.Tipo.CONTRATACION: "Se registró tu contratación.",
    EnvioEmail.Tipo.CONTRATACION_ANULADA: "Se anuló tu contratación.",
    EnvioEmail.Tipo.MOVIMIENTO: "Se registró un movimiento en tu reserva o contratación.",
    EnvioEmail.Tipo.RECORDATORIO_CLASE: "Recordá tu próxima clase.",
    EnvioEmail.Tipo.RECORDATORIO_RESERVA: "Recordá tu próxima reserva.",
    EnvioEmail.Tipo.SOLICITUD_CORREO: "Se solicitó cambiar el correo de tu cuenta.",
    EnvioEmail.Tipo.CONTRASENA_CAMBIADA: "Se cambió la contraseña de tu cuenta.",
}


def registrar_notificacion(envio):
    if envio.datos.get("enlace"):
        return
    usuario = Usuario.objects.filter(
        pk=envio.datos.get("vigencia", {}).get("usuario_id"), correo_verificado_en__isnull=False,
    ).first()
    if usuario is None:
        return
    # El cambio confirmado avisa a dos direcciones, pero corresponde a una sola cuenta.
    if envio.tipo == EnvioEmail.Tipo.CORREO_CAMBIADO and envio.destinatario.casefold() != usuario.email.casefold():
        return
    contenido = envio.datos["mensaje"]
    parrafos = contenido.get("parrafos", [])
    mensaje = MENSAJES_BREVES.get(envio.tipo) or next(iter(parrafos), "") or envio.get_tipo_display()
    if envio.tipo == EnvioEmail.Tipo.ESTADO_CUENTA:
        mensaje = mensaje.split(". ", 1)[0].rstrip(".") + "."
    if envio.tipo == EnvioEmail.Tipo.RECORDATORIO_RESERVA and any(p.startswith("Todavía no respondiste") for p in parrafos):
        mensaje = "Tenés una invitación pendiente de respuesta."
    acciones = contenido.get("acciones", [])
    ruta = acciones[0]["ruta"] if acciones else ""
    if envio.tipo == EnvioEmail.Tipo.GENERACION_CLASES:
        mensaje = f"Tenés {len(contenido.get('apartados', []))} clases programadas."
        ruta = reverse("clases:actividad_clases", kwargs={"usuario_id": usuario.pk})
    elif envio.tipo == EnvioEmail.Tipo.CONTINUIDAD:
        ruta = reverse("membresias:mis_contrataciones")
    if len(mensaje) > 500:
        mensaje = mensaje[:499].rstrip() + "…"
    valores = {"destinatario_id": usuario.pk, "tipo": envio.tipo, "mensaje": mensaje, "ruta": ruta}
    candidato = Notificacion(clave=envio.clave, **valores)
    candidato.full_clean(validate_unique=False, validate_constraints=False)
    notificacion, _ = Notificacion.objects.get_or_create(
        clave=envio.clave, defaults={**valores, "creado_en": envio.creado_en},
    )
    if any(getattr(notificacion, campo) != valor for campo, valor in valores.items()):
        raise ValidationError("La clave de la notificación corresponde a otro contenido.")
