from uuid import UUID

from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction

from auditoria.contexto import contexto_auditoria
from common.bloqueos import bloquear_usuarios
from common.validaciones import validar_motivo
from comunicaciones.movimientos import avisar_ajuste_importe

from .finanzas import resumen_financiero
from .ingresos import ORIGENES, consultar_origen
from .models import AjusteImporte
from .servicios import exigir_acceso_caja


def _situacion_revision(resumen):
    return {campo: format(resumen[campo], ".2f") for campo in ("importe_acordado", "ingresos", "devoluciones", "neto_recibido")}


def leer_revision_importe(actor, token, tipo, origen_id):
    exigir_acceso_caja(actor)
    try:
        datos = signing.loads(token, salt="caja.ajuste_importe", max_age=900)
        if datos["actor"] != actor.pk or datos["tipo"] != tipo or datos["origen"] != origen_id:
            raise signing.BadSignature
        return datos
    except (signing.BadSignature, KeyError, TypeError):
        raise ValidationError("La revisión del importe venció o no es válida. Revisá nuevamente.") from None


def _bloquear_origen(actor, tipo, origen_id):
    actor = exigir_acceso_caja(actor)
    origen = consultar_origen(tipo, origen_id)
    titular_id = origen.organizador_id if tipo == "reserva" else origen.usuario_id
    bloquear_usuarios({actor.pk, titular_id})
    actor = exigir_acceso_caja(actor)
    origen = consultar_origen(tipo, origen_id, bloquear=True)
    return actor, origen


@transaction.atomic
def preparar_ajuste_importe(actor, tipo, origen_id, *, importe_nuevo, motivo, operacion_id):
    actor, origen = _bloquear_origen(actor, tipo, origen_id)
    resumen = resumen_financiero(tipo, origen)
    if resumen["operacion_anulada"]:
        raise ValidationError("Una operación anulada no admite ajustes de importe.")
    if resumen["maximo_ingreso"] <= 0:
        raise ValidationError("El importe acordado ya está cubierto. No admite ajustes de importe.")
    if isinstance(importe_nuevo, (float, bool)):
        raise ValidationError("Ingresá un importe no negativo con hasta dos decimales.")
    importe = AjusteImporte._meta.get_field("importe_nuevo").clean(importe_nuevo, None)
    motivo = motivo.strip() if isinstance(motivo, str) else ""
    validar_motivo(motivo)
    try:
        operacion = str(UUID(str(operacion_id)))
    except (ValueError, TypeError, AttributeError):
        raise ValidationError("El identificador del ajuste no es válido.") from None
    if importe == resumen["importe_acordado"]:
        raise ValidationError("El nuevo importe debe ser distinto del importe acordado.")
    datos = {
        "actor": actor.pk, "tipo": tipo, "origen": origen_id, "operacion_id": operacion,
        "importe_nuevo": format(importe, ".2f"), "motivo": motivo, "situacion": _situacion_revision(resumen),
    }
    return {
        "origen": origen, "finanzas": resumen, "importe_nuevo": importe, "motivo": motivo,
        "confirmacion": signing.dumps(datos, salt="caja.ajuste_importe", compress=True),
    }


@transaction.atomic
def confirmar_ajuste_importe(actor, tipo, origen_id, token):
    datos = leer_revision_importe(actor, token, tipo, origen_id)
    actor, origen = _bloquear_origen(actor, tipo, origen_id)
    campos = {
        ORIGENES[tipo][1]: origen_id, "registrado_por_id": actor.pk,
        "importe_nuevo": AjusteImporte._meta.get_field("importe_nuevo").clean(datos["importe_nuevo"], None),
        "importe_anterior": AjusteImporte._meta.get_field("importe_anterior").clean(datos["situacion"]["importe_acordado"], None),
        "motivo": datos["motivo"],
    }
    anterior = AjusteImporte.objects.filter(operacion_id=datos["operacion_id"]).first()
    if anterior:
        if any(getattr(anterior, campo) != valor for campo, valor in campos.items()):
            raise ValidationError("El identificador del ajuste ya se usó con otros datos.")
        return anterior
    resumen = resumen_financiero(tipo, origen)
    if resumen["maximo_ingreso"] <= 0:
        raise ValidationError("El importe acordado ya está cubierto o la operación está anulada. No admite ajustes de importe.")
    if resumen["operacion_anulada"] or _situacion_revision(resumen) != datos["situacion"]:
        raise ValidationError("La operación o sus importes cambiaron. Revisá nuevamente el ajuste.")
    ajuste = AjusteImporte(operacion_id=datos["operacion_id"], **campos)
    ajuste.full_clean()
    with contexto_auditoria(actor):
        ajuste.save()
        avisar_ajuste_importe(ajuste, origen, tipo)
    return ajuste
