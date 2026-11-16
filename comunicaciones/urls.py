from django.urls import path

from . import views

app_name = "comunicaciones"
urlpatterns = [
    path("", views.envios_lista, name="envios_lista"),
    path("configuracion/", views.configuracion_notificaciones, name="configuracion_notificaciones"),
    path("notificaciones/", views.notificaciones_lista, name="notificaciones_lista"),
    path("notificaciones/leer-todas/", views.notificaciones_leer_todas, name="notificaciones_leer_todas"),
    path("notificaciones/<int:pk>/leer/", views.notificacion_leer, name="notificacion_leer"),
]
