from django.urls import path

from . import views


app_name = "reportes"
urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("<slug:tipo>/", views.detalle, name="detalle"),
    path("<slug:tipo>/pdf/", views.detalle, {"exportar": True}, name="pdf"),
]
