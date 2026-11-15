# Guía de instalación y ejecución

Ejecutar desde la carpeta del proyecto, con Docker iniciado. Los servicios se manejan todos juntos.

## Primera ejecución

1. Construir e iniciar todo:

   ```powershell
   docker compose up --build -d
   ```

   Las migraciones y la carga completa de demostración se ejecutan automáticamente: dos sedes, cuatro canchas, un administrador, 90 usuarios adicionales, ocho planes, dos membresías, contrataciones, clases, asistencias, reservas, bloqueos y pagos. La primera carga puede demorar varios minutos. Los usuarios de ejemplo tienen el correo verificado y pueden usarse directamente. Los reinicios conservan los datos sin duplicarlos.

2. Crear el administrador:

   ```powershell
   docker compose exec web python manage.py crear_administrador
   ```

3. Abrir <http://localhost:8000/>.

## Actualizar conservando los datos

```powershell
docker compose down
git pull
docker compose up --build -d
```

Las migraciones se aplican automáticamente. Los datos existentes se conservan.

## Detener todo

```powershell
docker compose stop
```

Para volver a iniciar:

```powershell
docker compose start
```

## Correos de prueba con Mailpit

Docker Compose habilita la simulación por defecto con `EMAILS_SIMULACION=1`. Todos los correos llegan a la bandeja local en <http://localhost:8025/>, independientemente del destinatario: nadie los recibe en su casilla real. Podés consultar el HTML, el texto y abrir los enlaces.

## Consultar registros

```powershell
docker compose logs --tail=50
```
