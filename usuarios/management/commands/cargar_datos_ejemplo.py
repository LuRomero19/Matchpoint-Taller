from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Carga las instalaciones, el administrador y el escenario completo de demostración sobre una base inicial."

    def handle(self, *args, **options):
        script = (settings.BASE_DIR / "scripts" / "datos_ejemplo.sql").read_text(encoding="utf-8")
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(script)
            call_command("cargar_demo_parcial", omitir_si_hay_datos=True, stdout=self.stdout, stderr=self.stderr)
        self.stdout.write("Carga de ejemplo procesada. Los datos existentes se conservan.")
