from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("membresias", "0015_seguimiento_recordatorios"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="ajustehorasmembresia",
            name="ajuste_horas_reversion_distinta",
        ),
        migrations.RemoveField(
            model_name="ajustehorasmembresia",
            name="reversion_de",
        ),
        migrations.RunSQL(
            sql="""
                CREATE OR REPLACE FUNCTION proteger_ajustes_horas() RETURNS trigger
                LANGUAGE plpgsql AS $$
                BEGIN
                    RAISE EXCEPTION 'Los ajustes de horas no se editan ni se borran. Registrá otro ajuste.';
                END;
                $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
