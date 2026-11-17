from decimal import Decimal

from django.db.models import Q, Sum

from caja.models import MovimientoFondo
from clases.models import Asistencia, Clase, ClaseAlumno
from membresias.models import MembresiaUsuario, PlanUsuario
from reservas.models import Reserva
from usuarios.models import Usuario


CERO = Decimal("0.00")
SITUACIONES = {"cubierto": "Cubierto", "faltante": "Falta cobrar", "excedente": "Excedente por resolver", "anulada": "Anulada"}


def cobros_por_origen(campo, identificadores):
    movimientos = MovimientoFondo.objects.using("reportes").filter(estado="vigente", **{f"{campo}__in": identificadores})
    return {fila[campo]: fila for fila in movimientos.values(campo).annotate(
        cobros=Sum("monto", filter=Q(clase="ingreso"), default=CERO),
        devoluciones=Sum("monto", filter=Q(clase="egreso", categoria_egreso="devoluciones"), default=CERO),
    )}


def contrataciones(datos):
    filas = []
    producto = datos.get("producto", "")
    for tipo, modelo, campo in (("plan", PlanUsuario, "plan_usuario_id"), ("membresia", MembresiaUsuario, "membresia_usuario_id")):
        if datos.get("tipo") and datos["tipo"] != tipo:
            continue
        if producto and not producto.startswith(tipo + ":"):
            continue
        consulta = modelo.objects.using("reportes").filter(fecha_alta__range=(datos["desde"], datos["hasta"]))
        if datos.get("usuario"):
            consulta = consulta.filter(usuario=datos["usuario"])
        if producto:
            consulta = consulta.filter(**{f"{tipo}_id": int(producto.split(":")[1])})
        contratos = list(consulta.select_related("usuario", tipo).prefetch_related("ajustes_importe").order_by("usuario__last_name", "usuario__first_name", "mes_cubierto", "pk"))
        movimientos = cobros_por_origen(campo, [c.pk for c in contratos])
        for contrato in contratos:
            fondos = movimientos.get(contrato.pk, {"cobros": CERO, "devoluciones": CERO})
            neto = fondos["cobros"] - fondos["devoluciones"]
            diferencia = neto - contrato.importe_acordado
            situacion = "anulada" if contrato.estado == "anulado" else "faltante" if diferencia < 0 else "excedente" if diferencia > 0 else "cubierto"
            if datos.get("situacion") and datos["situacion"] != situacion:
                continue
            filas.append({
                "titular": str(contrato.usuario), "producto": contrato.producto.nombre,
                "mes": contrato.mes_cubierto, "estado": contrato.get_estado_display(),
                "importe": contrato.importe_acordado, "cobros": fondos["cobros"],
                "devoluciones": fondos["devoluciones"], "neto": neto,
                "diferencia": None if situacion == "anulada" else abs(diferencia),
                "situacion": SITUACIONES[situacion], "_situacion": situacion,
                "_orden": (contrato.usuario.last_name, contrato.usuario.first_name, contrato.usuario_id, contrato.mes_cubierto, tipo, contrato.pk),
            })
    filas.sort(key=lambda fila: fila["_orden"])
    totales = {campo: sum((f[campo] for f in filas), CERO) for campo in ("cobros", "devoluciones", "neto")}
    totales["importe"] = sum((f["importe"] for f in filas if f["_situacion"] != "anulada"), CERO)
    faltante = sum((f["diferencia"] for f in filas if f["_situacion"] == "faltante"), CERO)
    excedente = sum((f["diferencia"] for f in filas if f["_situacion"] == "excedente"), CERO)
    return {"filas": filas, "totales": totales, "indicadores": [
        ("Contrataciones", len(filas), "entero"), ("Diferencia por cubrir", faltante, "dinero"),
        ("Excedente por resolver", excedente, "dinero"),
    ]}


def asistencia(datos):
    clases = Clase.objects.using("reportes").filter(evento__estado="finalizado", evento__turno__fecha__range=(datos["desde"], datos["hasta"]))
    if datos.get("sede"):
        clases = clases.filter(evento__turno__cancha__sede=datos["sede"])
    if datos.get("profesor"):
        clases = clases.filter(profesores__profesor=datos["profesor"])
    fechas = dict(clases.values_list("pk", "evento__turno__fecha"))
    asignaciones = ClaseAlumno.objects.using("reportes").filter(clase_id__in=fechas)
    marcas = Asistencia.objects.using("reportes").filter(clase_id__in=fechas)
    contratos = PlanUsuario.objects.using("reportes").exclude(estado="anulado").filter(
        mes_cubierto__range=(datos["desde"].replace(day=1), datos["hasta"].replace(day=1)),
    ).select_related("plan")
    if datos.get("usuario"):
        asignaciones = asignaciones.filter(usuario=datos["usuario"])
        marcas = marcas.filter(usuario=datos["usuario"])
        contratos = contratos.filter(usuario=datos["usuario"])
    planes = {(c.usuario_id, c.mes_cubierto): c.plan for c in contratos}
    asignados = set(asignaciones.values_list("clase_id", "usuario_id"))
    estados = {(a["clase_id"], a["usuario_id"]): a["estado"] for a in marcas.values("clase_id", "usuario_id", "estado")}
    grupos = {}

    def agregar_grupo(usuario_id, mes):
        clave = (usuario_id, mes)
        if clave not in grupos:
            plan = planes.get(clave)
            if datos.get("plan") and (plan is None or plan.pk != datos["plan"].pk):
                return None
            grupos[clave] = {"mes": mes, "plan": plan.nombre if plan else "Sin plan", "asignadas": 0,
                             "presente": 0, "ausente": 0, "sin_registrar": 0, "_usuario_id": usuario_id, "_clases": set()}
        return grupos.get(clave)

    # Sin sede ni profesor, se incluyen también contratados sin actividad en el período.
    if not datos.get("sede") and not datos.get("profesor"):
        for usuario_id, mes in planes:
            agregar_grupo(usuario_id, mes)
    for clase_id, usuario_id in sorted(asignados | set(estados)):
        grupo = agregar_grupo(usuario_id, fechas[clase_id].replace(day=1))
        if grupo is None:
            continue
        grupo["asignadas"] += int((clase_id, usuario_id) in asignados)
        grupo[estados.get((clase_id, usuario_id), "sin_registrar")] += 1
        grupo["_clases"].add(clase_id)
    usuarios = Usuario.objects.using("reportes").in_bulk({g["_usuario_id"] for g in grupos.values()})
    filas = list(grupos.values())
    for grupo in filas:
        usuario = usuarios[grupo["_usuario_id"]]
        grupo["alumno"] = str(usuario)
        registradas = grupo["presente"] + grupo["ausente"]
        grupo["porcentaje"] = Decimal(100) * grupo["presente"] / registradas if registradas else None
    filas.sort(key=lambda f: (usuarios[f["_usuario_id"]].last_name, usuarios[f["_usuario_id"]].first_name, f["_usuario_id"], f["mes"]))
    totales = {campo: sum(f[campo] for f in filas) for campo in ("asignadas", "presente", "ausente", "sin_registrar")}
    registradas = totales["presente"] + totales["ausente"]
    totales["porcentaje"] = Decimal(100) * totales["presente"] / registradas if registradas else None
    clases_incluidas = set().union(*(f["_clases"] for f in filas))
    return {"filas": filas, "totales": totales, "indicadores": [
        ("Alumnos distintos", len(usuarios), "entero"), ("Clases con participación", len(clases_incluidas), "entero"),
        ("Asistencia global", totales["porcentaje"], "porcentaje"),
    ]}


def reservas(datos):
    consulta = Reserva.objects.using("reportes").filter(evento__turno__fecha__range=(datos["desde"], datos["hasta"]))
    if datos.get("sede"):
        consulta = consulta.filter(evento__turno__cancha__sede=datos["sede"])
    if datos.get("cancha"):
        consulta = consulta.filter(evento__turno__cancha=datos["cancha"])
    if datos.get("modalidad"):
        consulta = consulta.filter(membresia_usuario__isnull=datos["modalidad"] == "normal")
    if datos.get("estado"):
        consulta = consulta.filter(evento__estado=datos["estado"])
    operaciones = list(consulta.select_related("evento__turno__cancha__sede").prefetch_related("invitados", "ajustes_importe").order_by("pk"))
    movimientos = cobros_por_origen("reserva_id", [r.pk for r in operaciones])
    grupos = {}
    for reserva in operaciones:
        cancha = reserva.evento.turno.cancha
        if cancha.pk not in grupos:
            grupos[cancha.pk] = {"sede": cancha.sede.nombre, "cancha": cancha.nombre,
                                "programado": 0, "finalizado": 0, "anulado": 0,
                                "importe": CERO, "cobros": CERO, "devoluciones": CERO, "neto": CERO}
        fila = grupos[cancha.pk]
        fila[reserva.evento.estado] += 1
        if reserva.evento.estado != "anulado":
            fila["importe"] += reserva.importe_acordado
        fondos = movimientos.get(reserva.pk, {"cobros": CERO, "devoluciones": CERO})
        fila["cobros"] += fondos["cobros"]
        fila["devoluciones"] += fondos["devoluciones"]
        fila["neto"] = fila["cobros"] - fila["devoluciones"]
    filas = sorted(grupos.values(), key=lambda f: (f["sede"], f["cancha"]))
    totales = {campo: sum((f[campo] for f in filas), CERO if campo in ("importe", "cobros", "devoluciones", "neto") else 0)
               for campo in ("programado", "finalizado", "anulado", "importe", "cobros", "devoluciones", "neto")}
    return {"filas": filas, "totales": totales, "indicadores": [
        ("Reservas", len(operaciones), "entero"), ("Canchas con reservas", len(filas), "entero"),
        ("Neto recibido", totales["neto"], "dinero"),
    ]}
