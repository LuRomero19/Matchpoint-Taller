from decimal import Decimal

from django.core import signing
from django.core.exceptions import ValidationError

from common.validaciones import validar_motivo


CAMPOS_EXCEDENTE = ("concepto", "monto", "medio_pago", "referencia", "verificado", "motivo_excedente", "operacion_id")


def _datos_revision(actor, sesion_id, tipo, origen_id, datos, resumen):
    campos = {campo: datos.get(campo, "") for campo in CAMPOS_EXCEDENTE}
    campos["monto"] = format(Decimal(campos["monto"]), ".2f")
    campos["operacion_id"] = str(campos["operacion_id"])
    situacion = {campo: format(resumen[campo], ".2f") for campo in ("importe_acordado", "ingresos", "devoluciones", "neto_recibido")}
    return {"actor": actor.pk, "sesion": sesion_id, "tipo": tipo, "origen": origen_id, "datos": campos, "situacion": situacion}


def revision_excedente(actor, sesion_id, tipo, origen_id, datos, resumen):
    if resumen["operacion_anulada"]:
        raise ValidationError("Una operación anulada no admite ingresos.")
    if resumen["maximo_ingreso"] <= 0:
        raise ValidationError("El importe acordado ya está cubierto. No admite cobros con excedente.")
    if datos["monto"] <= resumen["maximo_ingreso"]:
        raise ValidationError("El importe no genera un excedente. Registralo mediante el cobro habitual.")
    validar_motivo(datos["motivo_excedente"])
    return signing.dumps(_datos_revision(actor, sesion_id, tipo, origen_id, datos, resumen), salt="caja.excedente", compress=True)


def leer_revision_excedente(actor, sesion_id, tipo, origen_id, token):
    try:
        datos = signing.loads(token, salt="caja.excedente", max_age=900)
        if (datos["actor"], datos["sesion"], datos["tipo"], datos["origen"]) != (actor.pk, sesion_id, tipo, origen_id):
            raise signing.BadSignature
        return datos
    except (signing.BadSignature, KeyError, TypeError):
        raise ValidationError("La revisión del excedente venció o no es válida. Revisá nuevamente.") from None


def validar_revision_excedente(actor, sesion_id, tipo, origen_id, datos, resumen, token):
    if resumen["maximo_ingreso"] <= 0:
        raise ValidationError("El importe acordado ya está cubierto o la operación está anulada. No admite cobros con excedente.")
    firmado = leer_revision_excedente(actor, sesion_id, tipo, origen_id, token)
    if firmado != _datos_revision(actor, sesion_id, tipo, origen_id, datos, resumen):
        raise ValidationError("El cobro o la situación financiera cambió. Revisá nuevamente el excedente.")
