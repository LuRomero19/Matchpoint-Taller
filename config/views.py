from datetime import timedelta

from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from membresias.continuidad import ventana_continuidad
from membresias.models import MembresiaUsuario, PlanUsuario
from reservas.models import Evento
from usuarios.models import Rol, Usuario

from .inicio_portal import contexto_inicio_portal


@login_required
@never_cache
def inicio(request):
    administrador = request.user.tiene_rol(Rol.ADMINISTRADOR)
    contexto = {"puede_reservar": request.user.puede_reservar}
    if administrador:
        ahora = timezone.localtime()
        limite = ahora + timedelta(hours=1)
        proxima_hora = (
            (Q(turno__fecha__gt=ahora.date()) | Q(turno__fecha=ahora.date(), turno__hora_inicio__gte=ahora.time()))
            & (Q(turno__fecha__lt=limite.date()) | Q(turno__fecha=limite.date(), turno__hora_inicio__lt=limite.time()))
            & Q(estado=Evento.Estado.PROGRAMADO)
        )
        actividad = Evento.objects.filter(
            tipo__in=(Evento.Tipo.CLASE, Evento.Tipo.RESERVA),
            turno__fecha__range=(ahora.date(), limite.date()),
        ).exclude(estado=Evento.Estado.ANULADO).aggregate(
            hoy=Count("pk", filter=Q(turno__fecha=ahora.date())),
            clases=Count("pk", filter=proxima_hora & Q(tipo=Evento.Tipo.CLASE)),
            reservas=Count("pk", filter=proxima_hora & Q(tipo=Evento.Tipo.RESERVA)),
        )
        mes_actual = ahora.date().replace(day=1)
        apertura, cierre = ventana_continuidad(mes_actual)
        encuestas_abiertas = ahora >= apertura
        fecha_limite = cierre if encuestas_abiertas else apertura
        if ahora < apertura:
            _, cierre_anterior = ventana_continuidad(mes_actual - timedelta(days=1))
            if ahora < cierre_anterior:
                encuestas_abiertas = True
                fecha_limite = cierre_anterior
        dias_encuestas = (fecha_limite.date() - ahora.date()).days
        usuarios = Usuario.objects.aggregate(
            total=Count("pk"), nuevos_hoy=Count("pk", filter=Q(date_joined__date=ahora.date())),
        )
        contexto.update({
            "hoy": ahora.date(), "actividad": actividad, "mes_actual": mes_actual,
            "alumnos_con_plan": PlanUsuario.objects.filter(
                mes_cubierto=mes_actual, estado=PlanUsuario.Estado.ACTIVO,
            ).values("usuario_id").distinct().count(),
            "socios": MembresiaUsuario.objects.filter(
                mes_cubierto=mes_actual, estado=MembresiaUsuario.Estado.ACTIVO,
            ).values("usuario_id").distinct().count(),
            "encuestas": {"dias": dias_encuestas, "abiertas": encuestas_abiertas},
            "usuarios": usuarios,
        })
    else:
        contexto.update(contexto_inicio_portal(request.user))
    return render(request, "inicio_administracion.html" if administrador else "inicio_portal.html", contexto)
