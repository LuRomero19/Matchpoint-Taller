from datetime import time
from uuid import uuid4

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class EnvioEmail(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_PROCESO = "en_proceso", "En proceso"
        ENVIADO = "enviado", "Enviado"
        FALLIDO = "fallido", "Fallido"
        DESCARTADO = "descartado", "Descartado"

    class Tipo(models.TextChoices):
        BIENVENIDA = "bienvenida", "Bienvenida"
        VERIFICACION = "verificacion", "Verificá tu correo"
        RECUPERACION = "recuperacion", "Recuperá tu contraseña"
        SOLICITUD_CORREO = "solicitud_correo", "Solicitud de cambio de correo"
        CONFIRMAR_CORREO = "confirmar_correo", "Confirmá tu nuevo correo"
        CORREO_CAMBIADO = "correo_cambiado", "Cambiaste tu correo"
        ESTADO_CUENTA = "estado_cuenta", "Estado de tu cuenta"
        CONTRASENA_CAMBIADA = "contrasena_cambiada", "Cambiaste tu contraseña"
        RESERVA_CREADA = "reserva_creada", "Reserva confirmada"
        INVITACION = "invitacion", "Invitación a una reserva"
        RETIRADA_INVITACION = "retirada_invitacion", "Invitación retirada"
        RESPUESTA_INVITACION = "respuesta_invitacion", "Respuesta a tu invitación"
        RESERVA_ANULADA = "reserva_anulada", "Reserva anulada"
        ASIGNACION_CLASE = "asignacion_clase", "Asignación a una clase"
        GENERACION_CLASES = "generacion_clases", "Tus clases programadas"
        RETIRADA_CLASE = "retirada_clase", "Asignación retirada"
        CANCHA_CAMBIADA = "cancha_cambiada", "Nueva cancha para tu clase"
        NO_ASISTO = "no_asisto", "Aviso de no asistencia"
        CLASE_ANULADA = "clase_anulada", "Clase anulada"
        CONTRATACION = "contratacion", "Contratación registrada"
        CONTRATACION_ANULADA = "contratacion_anulada", "Contratación anulada"
        AJUSTE_HORAS = "ajuste_horas", "Ajuste de horas"
        MOVIMIENTO = "movimiento", "Movimiento registrado"
        RECORDATORIO_CLASE = "recordatorio_clase", "Recordatorio de clase"
        RECORDATORIO_RESERVA = "recordatorio_reserva", "Recordatorio de reserva"
        CONTINUIDAD = "continuidad", "Encuesta de continuidad"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    clave = models.CharField(max_length=250, unique=True)
    tipo = models.CharField(max_length=32, choices=Tipo.choices)
    destinatario = models.EmailField()
    datos = models.JSONField()
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    creado_en = models.DateTimeField(default=timezone.now, editable=False)
    proximo_intento_en = models.DateTimeField(default=timezone.now)
    intentos = models.PositiveSmallIntegerField(default=0)
    ultimo_intento_en = models.DateTimeField(null=True, blank=True)
    enlace_emitido_en = models.DateTimeField(null=True, blank=True)
    reserva_token = models.UUIDField(null=True, blank=True, editable=False)
    reservado_hasta = models.DateTimeField(null=True, blank=True)
    aceptado_en = models.DateTimeField(null=True, blank=True)
    error_resumido = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "envios_email"
        ordering = ("-creado_en", "-pk")
        default_permissions = ()
        indexes = [
            models.Index(fields=("estado", "proximo_intento_en"), name="envios_pendientes_idx"),
            models.Index(fields=("estado", "reservado_hasta"), name="envios_reservados_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(estado__in=(
                "pendiente", "en_proceso", "enviado", "fallido", "descartado",
            )), name="envio_estado_valido"),
            models.CheckConstraint(condition=models.Q(intentos__lte=4), name="envio_intentos_validos"),
            models.CheckConstraint(condition=(
                models.Q(estado="en_proceso", reserva_token__isnull=False, reservado_hasta__isnull=False)
                | (~models.Q(estado="en_proceso") & models.Q(reserva_token__isnull=True, reservado_hasta__isnull=True))
            ), name="envio_reserva_coherente"),
            models.CheckConstraint(condition=(
                models.Q(estado="enviado", aceptado_en__isnull=False)
                | (~models.Q(estado="enviado") & models.Q(aceptado_en__isnull=True))
            ), name="envio_aceptacion_coherente"),
        ]


class Notificacion(models.Model):
    clave = models.CharField(max_length=250, unique=True)
    destinatario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificaciones")
    tipo = models.CharField(max_length=32, choices=EnvioEmail.Tipo.choices)
    mensaje = models.CharField(max_length=500)
    ruta = models.CharField(max_length=500, blank=True)
    creado_en = models.DateTimeField(default=timezone.now, editable=False)
    leida = models.BooleanField(default=False)
    fecha_lectura = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notificaciones"
        ordering = ("-creado_en", "-pk")
        default_permissions = ()
        indexes = [
            models.Index(fields=("destinatario", "-creado_en", "-id"), name="notificaciones_bandeja_idx"),
            models.Index(fields=("destinatario",), condition=models.Q(leida=False), name="notificaciones_no_leidas_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=(
                models.Q(leida=False, fecha_lectura__isnull=True)
                | models.Q(leida=True, fecha_lectura__isnull=False)
            ), name="notificacion_lectura_coherente"),
        ]


class ConfiguracionNotificaciones(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    anticipacion_clases_minutos = models.PositiveSmallIntegerField(
        "Anticipación de clases (minutos)", default=60, validators=[MinValueValidator(1), MaxValueValidator(1440)],
    )
    anticipacion_reservas_minutos = models.PositiveSmallIntegerField(
        "Anticipación de reservas (minutos)", default=60, validators=[MinValueValidator(1), MaxValueValidator(1440)],
    )
    dia_apertura_continuidad = models.PositiveSmallIntegerField(
        "Día de apertura de continuidad", default=25, validators=[MinValueValidator(1), MaxValueValidator(27)],
    )
    dia_recordatorio_continuidad = models.PositiveSmallIntegerField(
        "Día de recordatorio de continuidad", default=0,
        choices=[(0, "Último día del mes"), *[(dia, str(dia)) for dia in range(1, 32)]],
    )
    dia_cierre_continuidad = models.PositiveSmallIntegerField(
        "Último día de respuesta del mes siguiente", default=5,
        validators=[MinValueValidator(1), MaxValueValidator(26)],
    )
    hora_continuidad = models.TimeField("Hora de avisos de continuidad", default=time(9))
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "configuracion_notificaciones"
        default_permissions = ()
        constraints = [
            models.CheckConstraint(condition=models.Q(pk=1), name="notificaciones_config_unica"),
            models.CheckConstraint(condition=(
                models.Q(anticipacion_clases_minutos__range=(1, 1440))
                & models.Q(anticipacion_reservas_minutos__range=(1, 1440))
            ), name="notificaciones_anticipacion"),
            models.CheckConstraint(condition=(
                models.Q(dia_apertura_continuidad__range=(1, 27))
                & models.Q(dia_cierre_continuidad__range=(1, 26))
                & models.Q(dia_cierre_continuidad__lt=models.F("dia_apertura_continuidad"))
                & models.Q(dia_recordatorio_continuidad__range=(0, 31))
                & (models.Q(dia_recordatorio_continuidad=0)
                   | models.Q(dia_recordatorio_continuidad__gt=models.F("dia_apertura_continuidad")))
            ), name="notificaciones_campana_valida"),
            models.CheckConstraint(condition=models.Q(hora_continuidad__second=0), name="notificaciones_hora_minutos"),
        ]
