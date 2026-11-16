import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comunicaciones', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notificacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('clave', models.CharField(max_length=250, unique=True)),
                ('tipo', models.CharField(choices=[('bienvenida', 'Bienvenida'), ('verificacion', 'Verificá tu correo'), ('recuperacion', 'Recuperá tu contraseña'), ('solicitud_correo', 'Solicitud de cambio de correo'), ('confirmar_correo', 'Confirmá tu nuevo correo'), ('correo_cambiado', 'Cambiaste tu correo'), ('estado_cuenta', 'Estado de tu cuenta'), ('contrasena_cambiada', 'Cambiaste tu contraseña'), ('reserva_creada', 'Reserva confirmada'), ('invitacion', 'Invitación a una reserva'), ('retirada_invitacion', 'Invitación retirada'), ('respuesta_invitacion', 'Respuesta a tu invitación'), ('reserva_anulada', 'Reserva anulada'), ('asignacion_clase', 'Asignación a una clase'), ('generacion_clases', 'Tus clases programadas'), ('retirada_clase', 'Asignación retirada'), ('cancha_cambiada', 'Nueva cancha para tu clase'), ('no_asisto', 'Aviso de no asistencia'), ('clase_anulada', 'Clase anulada'), ('contratacion', 'Contratación registrada'), ('contratacion_anulada', 'Contratación anulada'), ('ajuste_horas', 'Ajuste de horas'), ('movimiento', 'Movimiento registrado'), ('recordatorio_clase', 'Recordatorio de clase'), ('recordatorio_reserva', 'Recordatorio de reserva'), ('continuidad', 'Encuesta de continuidad')], max_length=32)),
                ('mensaje', models.CharField(max_length=500)),
                ('ruta', models.CharField(blank=True, max_length=500)),
                ('creado_en', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('leida', models.BooleanField(default=False)),
                ('fecha_lectura', models.DateTimeField(blank=True, null=True)),
                ('destinatario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notificaciones', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'notificaciones',
                'ordering': ('-creado_en', '-pk'),
                'default_permissions': (),
                'indexes': [models.Index(fields=['destinatario', '-creado_en', '-id'], name='notificaciones_bandeja_idx'), models.Index(condition=models.Q(('leida', False)), fields=['destinatario'], name='notificaciones_no_leidas_idx')],
                'constraints': [models.CheckConstraint(condition=models.Q(models.Q(('fecha_lectura__isnull', True), ('leida', False)), models.Q(('fecha_lectura__isnull', False), ('leida', True)), _connector='OR'), name='notificacion_lectura_coherente')],
            },
        ),
    ]
