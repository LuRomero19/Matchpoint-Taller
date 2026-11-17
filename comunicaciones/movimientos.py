from django.urls import reverse

from .mensajes import dato_importe
from .models import EnvioEmail
from .servicios import encolar_aviso


def avisar_ajuste_importe(ajuste, origen, tipo):
    usuario = origen.organizador if tipo == "reserva" else origen.usuario
    ruta = "reservas:reserva_detalle" if tipo == "reserva" else f"membresias:mi_{tipo}_contratado"
    return encolar_aviso(
        clave=f"ajuste_importe:{ajuste.pk}", tipo=EnvioEmail.Tipo.AJUSTE_IMPORTE, destinatario=usuario.email,
        datos={"vigencia": {"usuario_id": usuario.pk}, "mensaje": {
            "parrafos": ["Se ajustó el importe acordado de tu operación. El ajuste no registra un cobro ni una devolución."],
            "datos": [{"etiqueta": "Operación", "valor": f"{tipo.capitalize()} #{origen.pk}"},
                      dato_importe("Importe anterior", ajuste.importe_anterior), dato_importe("Nuevo importe acordado", ajuste.importe_nuevo),
                      {"etiqueta": "Motivo", "valor": ajuste.motivo}],
            "acciones": [{"texto": "Ver mi operación", "ruta": reverse(ruta, args=[origen.pk])}],
        }},
    )


def avisar_movimiento(movimiento, origen, tipo):
    if origen is None or movimiento.clase not in ("ingreso", "egreso"):
        return
    usuario = origen.organizador if tipo == "reserva" else origen.usuario
    ruta = "reservas:reserva_detalle" if tipo == "reserva" else f"membresias:mi_{tipo}_contratado"
    encolar_aviso(clave=f"movimiento:{movimiento.pk}", tipo="movimiento", destinatario=usuario.email,
                  datos={"vigencia": {"usuario_id": usuario.pk}, "mensaje": {
                      "parrafos": ["Se registró un movimiento de dinero vinculado a tu reserva o contratación."],
                      "datos": [{"etiqueta": "Operación vinculada", "valor": f"{tipo.capitalize()} #{origen.pk}"}, {"etiqueta": "Tipo", "valor": movimiento.get_clase_display()}, dato_importe("Importe", movimiento.monto),
                                {"etiqueta": "Medio", "valor": movimiento.get_medio_pago_display()},
                                {"etiqueta": "Concepto", "valor": movimiento.concepto}],
                      "acciones": [{"texto": "Ver mi operación", "ruta": reverse(ruta, args=[origen.pk])}],
                  }})
