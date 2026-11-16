from datetime import datetime, timedelta

from django.utils import timezone

from .models import ConfiguracionNotificaciones


def obtener_configuracion():
    return ConfiguracionNotificaciones.objects.get(pk=1)


def dentro_del_plazo_recordatorio(actividad, configuracion=None):
    configuracion = configuracion or obtener_configuracion()
    minutos = (configuracion.anticipacion_clases_minutos if actividad.evento.tipo == "clase"
               else configuracion.anticipacion_reservas_minutos)
    turno = actividad.evento.turno
    inicio = timezone.make_aware(datetime.combine(turno.fecha, turno.hora_inicio))
    ahora = timezone.now()
    return ahora < inicio <= ahora + timedelta(minutes=minutos)
