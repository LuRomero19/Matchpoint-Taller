from django.db import migrations


def resumir_notificaciones(apps, schema_editor):
    Notificacion = apps.get_model("comunicaciones", "Notificacion")
    EnvioEmail = apps.get_model("comunicaciones", "EnvioEmail")
    base = schema_editor.connection.alias
    mensajes = {
        "invitacion": "Te invitaron a participar en una reserva.",
        "reserva_anulada": "Se anuló una reserva en la que participabas.",
        "clase_anulada": "Se anuló una de tus clases.",
        "cancha_cambiada": "Tu clase cambió de cancha.",
        "contratacion": "Se registró tu contratación.",
        "contratacion_anulada": "Se anuló tu contratación.",
        "movimiento": "Se registró un movimiento en tu reserva o contratación.",
        "recordatorio_clase": "Recordá tu próxima clase.",
        "recordatorio_reserva": "Recordá tu próxima reserva.",
        "solicitud_correo": "Se solicitó cambiar el correo de tu cuenta.",
        "contrasena_cambiada": "Se cambió la contraseña de tu cuenta.",
    }
    claves = Notificacion.objects.using(base).values("clave")
    envios = EnvioEmail.objects.using(base).filter(clave__in=claves).only("clave", "tipo", "datos")
    for envio in envios.iterator(chunk_size=200):
        contenido = envio.datos.get("mensaje", {})
        parrafos = contenido.get("parrafos", [])
        mensaje = mensajes.get(envio.tipo) or next(iter(parrafos), "")
        if envio.tipo == "estado_cuenta":
            mensaje = mensaje.split(". ", 1)[0].rstrip(".") + "."
        if envio.tipo == "recordatorio_reserva" and any(p.startswith("Todavía no respondiste") for p in parrafos):
            mensaje = "Tenés una invitación pendiente de respuesta."
        if envio.tipo == "generacion_clases":
            mensaje = f"Tenés {len(contenido.get('apartados', []))} clases programadas."
        if mensaje:
            mensaje = mensaje if len(mensaje) <= 500 else mensaje[:499].rstrip() + "…"
            Notificacion.objects.using(base).filter(clave=envio.clave).exclude(mensaje=mensaje).update(mensaje=mensaje)


class Migration(migrations.Migration):
    dependencies = [("comunicaciones", "0003_configuracionnotificaciones")]

    operations = [migrations.RunPython(resumir_notificaciones, migrations.RunPython.noop)]
