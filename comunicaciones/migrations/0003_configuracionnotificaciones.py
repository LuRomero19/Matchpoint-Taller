import datetime
import django.core.validators
from django.db import migrations, models


def cargar_configuracion(apps, schema_editor):
    apps.get_model('comunicaciones', 'ConfiguracionNotificaciones').objects.using(schema_editor.connection.alias).create(pk=1)


class Migration(migrations.Migration):

    dependencies = [
        ('comunicaciones', '0002_notificacion'),
        ('auditoria', '0007_acciones_contrasena'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfiguracionNotificaciones',
            fields=[
                ('id', models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ('anticipacion_clases_minutos', models.PositiveSmallIntegerField(default=60, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(1440)], verbose_name='Anticipación de clases (minutos)')),
                ('anticipacion_reservas_minutos', models.PositiveSmallIntegerField(default=60, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(1440)], verbose_name='Anticipación de reservas (minutos)')),
                ('dia_apertura_continuidad', models.PositiveSmallIntegerField(default=25, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(27)], verbose_name='Día de apertura de continuidad')),
                ('dia_recordatorio_continuidad', models.PositiveSmallIntegerField(choices=[(0, 'Último día del mes'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (11, '11'), (12, '12'), (13, '13'), (14, '14'), (15, '15'), (16, '16'), (17, '17'), (18, '18'), (19, '19'), (20, '20'), (21, '21'), (22, '22'), (23, '23'), (24, '24'), (25, '25'), (26, '26'), (27, '27'), (28, '28'), (29, '29'), (30, '30'), (31, '31')], default=0, verbose_name='Día de recordatorio de continuidad')),
                ('dia_cierre_continuidad', models.PositiveSmallIntegerField(default=5, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(26)], verbose_name='Último día de respuesta del mes siguiente')),
                ('hora_continuidad', models.TimeField(default=datetime.time(9, 0), verbose_name='Hora de avisos de continuidad')),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'configuracion_notificaciones',
                'default_permissions': (),
                'constraints': [models.CheckConstraint(condition=models.Q(('pk', 1)), name='notificaciones_config_unica'), models.CheckConstraint(condition=models.Q(('anticipacion_clases_minutos__range', (1, 1440)), ('anticipacion_reservas_minutos__range', (1, 1440))), name='notificaciones_anticipacion'), models.CheckConstraint(condition=models.Q(('dia_apertura_continuidad__range', (1, 27)), ('dia_cierre_continuidad__range', (1, 26)), ('dia_cierre_continuidad__lt', models.F('dia_apertura_continuidad')), ('dia_recordatorio_continuidad__range', (0, 31)), models.Q(('dia_recordatorio_continuidad', 0), ('dia_recordatorio_continuidad__gt', models.F('dia_apertura_continuidad')), _connector='OR')), name='notificaciones_campana_valida'), models.CheckConstraint(condition=models.Q(('hora_continuidad__second', 0)), name='notificaciones_hora_minutos')],
            },
        ),
        migrations.RunPython(cargar_configuracion, migrations.RunPython.noop),
        migrations.RunSQL(
            "CREATE TRIGGER auditar_configuracion_notificaciones AFTER UPDATE OR DELETE "
            "ON configuracion_notificaciones FOR EACH ROW EXECUTE FUNCTION registrar_auditoria('id')",
            reverse_sql="DROP TRIGGER auditar_configuracion_notificaciones ON configuracion_notificaciones",
        ),
    ]
