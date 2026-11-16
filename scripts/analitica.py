"""Lee la base del proyecto y genera cuatro gráficos para la administración.

Pandas organiza los datos, numpy calcula los valores del resumen y matplotlib
dibuja los gráficos. Los resultados se guardan como imágenes PNG y un resumen de texto.
"""

import argparse
from datetime import date, datetime, time, timedelta
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib

# Permite guardar los gráficos sin abrir ventanas, incluso dentro de Docker.
matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, PercentFormatter
import numpy as np
import pandas as pd
import psycopg


ZONA_HORARIA = ZoneInfo("America/Argentina/Salta")
COLORES = ("#22624F", "#DA9A36", "#467BA2", "#8A659C")
DIAS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")
MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def entero_positivo(valor):
    numero = int(valor)
    if numero < 1:
        raise argparse.ArgumentTypeError("El identificador debe ser mayor que cero.")
    return numero


def argumentos():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--desde", type=date.fromisoformat, required=True, help="Fecha inicial AAAA-MM-DD, incluida.")
    parser.add_argument("--hasta", type=date.fromisoformat, required=True, help="Fecha final AAAA-MM-DD, incluida.")
    parser.add_argument("--sede", type=entero_positivo, help="ID de sede para actividad y asistencia.")
    parser.add_argument("--cancha", type=entero_positivo, help="ID de cancha para actividad y asistencia.")
    parser.add_argument("--ventana-tendencia", type=entero_positivo, default=4, help="Semanas de la media móvil (4 por defecto).")
    parser.add_argument("--salida", type=Path, default=Path("output/analitica"), help="Carpeta de los cuatro PNG y resumen.txt.")
    opciones = parser.parse_args()
    if opciones.desde > opciones.hasta:
        parser.error("La fecha desde debe ser anterior o igual a hasta.")
    if opciones.hasta == date.max:
        parser.error("La fecha hasta debe ser anterior a 9999-12-31.")
    return parser, opciones


def consultar(conexion, sql, parametros=()):
    # Los datos se leen con el conector de PostgreSQL y se pasan a una tabla de pandas.
    with conexion.cursor() as cursor:
        cursor.execute(sql, parametros)
        return pd.DataFrame(cursor.fetchall(), columns=[columna.name for columna in cursor.description])


def leer_datos(conexion, opciones):
    # Finalizado indica que terminó el horario; no confirma que la actividad se realizó.
    # Los eventos programados, anulados y bloqueos quedan fuera del análisis de actividad.
    condiciones = ["t.fecha BETWEEN %s AND %s", "e.estado = 'finalizado'", "e.tipo IN ('clase', 'reserva')"]
    parametros = [opciones.desde, opciones.hasta]
    alcance = []
    if opciones.sede:
        sede = consultar(conexion, "SELECT nombre FROM sedes WHERE id = %s", (opciones.sede,))
        if sede.empty:
            raise ValueError("La sede indicada no existe.")
        condiciones.append("ca.sede_id = %s")
        parametros.append(opciones.sede)
        alcance.append(f"Sede: {sede.iloc[0]['nombre']}")
    if opciones.cancha:
        cancha = consultar(conexion, "SELECT nombre, sede_id FROM canchas WHERE id = %s", (opciones.cancha,))
        if cancha.empty:
            raise ValueError("La cancha indicada no existe.")
        if opciones.sede and cancha.iloc[0]["sede_id"] != opciones.sede:
            raise ValueError("La cancha indicada no pertenece a la sede seleccionada.")
        condiciones.append("t.cancha_id = %s")
        parametros.append(opciones.cancha)
        alcance.append(f"Cancha: {cancha.iloc[0]['nombre']}")

    # Las fechas y los filtros se envían separados de la consulta para leerlos como valores.
    eventos = consultar(conexion, f"""
        SELECT e.id AS evento_id, e.tipo, t.fecha, t.hora_inicio
        FROM eventos e JOIN turnos t ON t.id = e.turno_id
        JOIN canchas ca ON ca.id = t.cancha_id
        WHERE {' AND '.join(condiciones)}
        ORDER BY t.fecha, t.hora_inicio, e.id
    """, parametros)
    eventos["fecha"] = pd.to_datetime(eventos["fecha"])

    # Se incluye a quienes estaban asignados y a quienes tienen asistencia cargada,
    # contando una sola vez a cada persona por clase. Sin carga no significa ausente.
    asistencias = consultar(conexion, f"""
        WITH personas AS (
            SELECT clase_id, usuario_id FROM clases_alumnos
            UNION
            SELECT clase_id, usuario_id FROM asistencias
        )
        SELECT t.fecha, COALESCE(a.estado, 'sin_registrar') AS estado
        FROM clases c JOIN eventos e ON e.id = c.evento_id
        JOIN turnos t ON t.id = e.turno_id
        JOIN canchas ca ON ca.id = t.cancha_id
        JOIN personas p ON p.clase_id = c.id
        LEFT JOIN asistencias a ON a.clase_id = p.clase_id AND a.usuario_id = p.usuario_id
        WHERE {' AND '.join(condiciones)}
        ORDER BY t.fecha, c.id, p.usuario_id
    """, parametros)
    asistencias["fecha"] = pd.to_datetime(asistencias["fecha"])

    # El día final se incluye completo, desde las 00:00 hasta antes del día siguiente,
    # usando la hora de Salta para que los cobros no cambien de día por la zona horaria.
    inicio = datetime.combine(opciones.desde, time.min, ZONA_HORARIA)
    fin = datetime.combine(opciones.hasta + timedelta(days=1), time.min, ZONA_HORARIA)
    # Caja se consulta de forma global: las contrataciones de planes y membresías
    # no tienen una sede asociada. Sólo se toman cobros y devoluciones vigentes.
    fondos = consultar(conexion, """
        SELECT clase, categoria_ingreso, categoria_egreso, monto
        FROM movimientos_fondos
        WHERE estado = 'vigente' AND creado_en >= %s AND creado_en < %s
          AND (clase = 'ingreso' OR (clase = 'egreso' AND categoria_egreso = 'devoluciones'))
        ORDER BY id
    """, (inicio, fin))
    fondos["monto"] = fondos["monto"].astype(float)
    return eventos, asistencias, fondos, " · ".join(alcance) or "Todas las sedes y canchas"


def figura(titulo, opciones, alcance):
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor("#FAFAF7")
    ax.set_facecolor("#FAFAF7")
    fig.suptitle(f"Academia TM | {titulo}", x=0.08, ha="left", fontsize=17, fontweight="bold")
    fig.text(0.08, 0.89, f"{opciones.desde:%d/%m/%Y} a {opciones.hasta:%d/%m/%Y} · {alcance}", fontsize=10, wrap=True)
    ax.spines[["top", "right"]].set_visible(False)
    fig.subplots_adjust(left=0.09, right=0.95, bottom=0.23, top=0.81)
    return fig, ax


def guardar(fig, opciones, nombre, nota):
    # Cada imagen conserva el período, el alcance y una nota para poder interpretarla
    # sin tener que abrir el programa que la generó.
    fig.text(0.08, 0.055, nota, fontsize=9, color="#454545", linespacing=1.6)
    destino = opciones.salida / nombre
    fig.savefig(destino, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Generado: {destino}")


def sin_datos(ax, mensaje):
    ax.text(0.5, 0.5, mensaje, ha="center", va="center", transform=ax.transAxes, fontsize=13)
    ax.set_axis_off()


def actividad_mensual(eventos, opciones, alcance):
    """¿Cómo se distribuye la actividad mensual entre clases y reservas?"""
    fig, ax = figura("Actividad mensual por tipo", opciones, alcance)
    if eventos.empty:
        sin_datos(ax, "Sin clases ni reservas finalizadas en el período.")
    else:
        # Se cuenta cada tipo de actividad por mes. Los meses sin actividad aparecen
        # con cero para que no desaparezcan del período solicitado.
        meses = pd.period_range(opciones.desde, opciones.hasta, freq="M")
        actividad = eventos.assign(mes=eventos.fecha.dt.to_period("M")).pivot_table(
            index="mes", columns="tipo", values="evento_id", aggfunc="count", fill_value=0,
        ).reindex(index=meses, columns=["clase", "reserva"], fill_value=0)
        # Cada evento ocupa una hora, por eso la cantidad de eventos equivale a horas.
        # Las barras quedan una al lado de la otra para comparar clases y reservas.
        posiciones = np.arange(len(meses))
        for indice, (tipo, etiqueta) in enumerate((("clase", "Clases"), ("reserva", "Reservas"))):
            ax.bar(posiciones + (indice - 0.5) * 0.36, actividad[tipo], 0.36, label=etiqueta, color=COLORES[indice])
        paso = max(1, int(np.ceil(len(meses) / 12)))
        ax.set_xticks(posiciones[::paso], [f"{MESES[mes.month - 1]} {mes.year}" for mes in meses[::paso]], rotation=35, ha="right")
        ax.set_xlim(-0.8, max(0.8, len(meses) - 0.2))
        ax.set_ylabel("Horas con eventos finalizados")
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.legend()
        ax.grid(axis="y", alpha=0.2)
        ax.set_axisbelow(True)
    guardar(fig, opciones, "01_actividad_mensual.png",
            "Cada evento ocupa un turno de una hora. Se excluyen programados, anulados y bloqueos.\n"
            "Finalizado indica cierre del horario; no confirma realización ni asistencia. Los meses extremos pueden ser parciales.")


def composicion_ingresos(fondos, opciones):
    """¿Qué parte de los cobros corresponde a planes, membresías y reservas?"""
    fig, ax = figura("Composición de los ingresos cobrados", opciones, "Caja global · Sin filtro de sede o cancha")
    # Se suman los cobros por categoría. Cada sector muestra su parte del total.
    # Las devoluciones se informan aparte para que los sectores representen sólo cobros.
    ingresos = fondos.loc[fondos.clase == "ingreso"].groupby("categoria_ingreso").monto.sum()
    ingresos = ingresos.reindex(["planes", "membresias", "reservas", "otros"], fill_value=0)
    ingresos = ingresos[ingresos > 0]
    total = float(np.sum(ingresos.to_numpy()))
    devoluciones = float(np.sum(fondos.loc[fondos.clase == "egreso", "monto"].to_numpy()))
    if total == 0:
        sin_datos(ax, "Sin ingresos cobrados vigentes en el período.")
    else:
        nombres = {"planes": "Planes", "membresias": "Membresías", "reservas": "Reservas", "otros": "Otros"}
        sectores, _, _ = ax.pie(ingresos, startangle=90, colors=COLORES, autopct="%1.1f%%",
                               pctdistance=0.78, wedgeprops={"width": 0.42, "edgecolor": "white"})
        ax.text(0, 0, f"ARS {total:,.2f}\nTotal cobrado", ha="center", va="center", fontsize=12)
        ax.legend(sectores, [f"{nombres[categoria]}: ARS {monto:,.2f}" for categoria, monto in ingresos.items()],
                  loc="center left", bbox_to_anchor=(1, 0.5), frameon=False)
        ax.set_xlim(-1.7, 2.0)
    guardar(fig, opciones, "02_composicion_ingresos.png",
            f"Ingresos vigentes por fecha de cobro, en hora de Salta. No incluye aportes, saldos iniciales ni movimientos anulados.\n"
            f"Devoluciones vigentes del período (se informan aparte): ARS {devoluciones:,.2f}. No representa rentabilidad.")
    return total, devoluciones


def evolucion_asistencia(asistencias, opciones, alcance):
    """¿Cómo cambia la asistencia a clases de una semana a otra?"""
    fig, ax = figura("Evolución semanal de la asistencia", opciones, alcance)
    # Cada semana comienza el lunes y termina el domingo. Se cuentan por separado
    # presentes, ausentes y participaciones sin registrar.
    semanas = pd.period_range(opciones.desde, opciones.hasta, freq="W-SUN")
    semanal = asistencias.assign(semana=asistencias.fecha.dt.to_period("W-SUN")).groupby(
        ["semana", "estado"],
    ).size().unstack(fill_value=0).reindex(
        index=semanas, columns=["presente", "ausente", "sin_registrar"], fill_value=0,
    )
    # El porcentaje usa sólo presentes y ausentes. Una semana sin marcas queda
    # sin valor, en lugar de mostrar un 0 % que podría confundirse con inasistencia.
    registradas = semanal.presente + semanal.ausente
    porcentaje = semanal.presente.div(registradas.where(registradas > 0)).mul(100)
    if porcentaje.notna().any():
        fechas = semanas.start_time
        ax.plot(fechas, porcentaje, marker="o", color=COLORES[0], label="Asistencia registrada")
        # La línea de tendencia promedia los porcentajes de las últimas semanas
        # elegidas para suavizar las variaciones. Cada semana con datos pesa lo mismo.
        tendencia = porcentaje.rolling(opciones.ventana_tendencia, min_periods=1).mean()
        # Una semana sin registros no se representa como una medición de asistencia.
        tendencia = tendencia.where(porcentaje.notna())
        ax.plot(fechas, tendencia, linestyle="--", marker="x", color=COLORES[1], label=f"Media móvil de {opciones.ventana_tendencia} semanas")
        ax.set_xlim(mdates.date2num(fechas[0].to_pydatetime()) - 2,
                    mdates.date2num(fechas[-1].to_pydatetime()) + 2)
        ax.set_ylim(0, 105)
        ax.yaxis.set_major_formatter(PercentFormatter(100))
        ax.set_ylabel("Presentes / (presentes + ausentes)")
        ax.set_xlabel("Semana que comienza el lunes indicado")
        paso = max(1, int(np.ceil(len(semanas) / 9)))
        ax.set_xticks(fechas[::paso])
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%Y"))
        ax.tick_params(axis="x", rotation=25)
        ax.grid(alpha=0.2)
        ax.legend(loc="lower left")
    else:
        sin_datos(ax, "Sin asistencias presentes o ausentes registradas en el período.")
    sin_registrar = int(np.sum(semanal.sin_registrar.to_numpy()))
    guardar(fig, opciones, "03_evolucion_asistencia.png",
            f"Sólo clases finalizadas. Sin registrar: {sin_registrar} participaciones; se excluyen del porcentaje.\n"
            "Las semanas sin carga dejan huecos. La media móvil promedia porcentajes semanales disponibles; extremos pueden ser parciales.")
    return porcentaje, sin_registrar


def concentracion(eventos, opciones, alcance):
    """¿En qué días y horarios se concentra la actividad de las canchas?"""
    fig, ax = figura("Concentración de turnos por día y hora", opciones, alcance)
    percentil = None
    if eventos.empty:
        sin_datos(ax, "Sin clases ni reservas finalizadas en el período.")
    else:
        # Cada casilla reúne los turnos de un día de semana y una hora de inicio.
        # Se muestran los siete días y las horas de inicio permitidas, de 00 a 22.
        matriz = eventos.assign(dia=eventos.fecha.dt.dayofweek, hora=eventos.hora_inicio.map(lambda hora: hora.hour)).pivot_table(
            index="dia", columns="hora", values="evento_id", aggfunc="count", fill_value=0,
        ).reindex(index=range(7), columns=range(23), fill_value=0)
        valores = matriz.to_numpy(dtype=int)
        # El percentil 90 indica el valor por debajo o igual al cual queda aproximadamente el 90 %
        # de las casillas. También considera las casillas con cero turnos.
        percentil = float(np.percentile(valores, 90))
        # Un color más oscuro representa más turnos. Es un conteo de actividad,
        # no un porcentaje de ocupación de la capacidad disponible.
        imagen = ax.imshow(valores, cmap="YlGn", aspect="auto", vmin=0, vmax=max(1, int(np.max(valores))))
        barra = fig.colorbar(imagen, ax=ax, pad=0.02)
        barra.set_label("Turnos acumulados en el período")
        barra.locator = MaxNLocator(integer=True)
        barra.update_ticks()
        ax.set_yticks(range(7), DIAS)
        ax.set_xticks(range(23), [f"{hora:02d}" for hora in range(23)])
        ax.set_xlabel("Hora de inicio")
        for fila, columna in np.ndindex(valores.shape):
            valor = valores[fila, columna]
            if valor:
                ax.text(columna, fila, str(valor), ha="center", va="center", fontsize=8,
                        color="white" if valor > np.max(valores) * 0.55 else "#183C30")
    guardar(fig, opciones, "04_concentracion_turnos.png",
            "Clases y reservas finalizadas; se excluyen programados, anulados y bloqueos. Horas locales de Salta.\n"
            "Cuenta turnos acumulados, no porcentaje de ocupación ni realización efectiva. Cero indica que no hay eventos finalizados.")
    return percentil


def main():
    parser, opciones = argumentos()
    # Se usa la conexión configurada para el proyecto, sin escribir credenciales aquí.
    nombres_entorno = ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT")
    faltantes = [nombre for nombre in nombres_entorno if not os.environ.get(nombre)]
    if faltantes:
        parser.error(f"Faltan variables de conexión: {', '.join(faltantes)}. Podés ejecutar el script con Docker Compose.")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.titleweight": "bold"})
    try:
        with psycopg.connect(dbname=os.environ["DB_NAME"], user=os.environ["DB_USER"],
                             password=os.environ["DB_PASSWORD"], host=os.environ["DB_HOST"],
                             port=os.environ["DB_PORT"], connect_timeout=10) as conexion:
            # Las tres lecturas ven el mismo estado de la base, aunque alguien cargue
            # datos mientras se ejecuta el script. Esta conexión no permite escribir.
            conexion.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            eventos, asistencias, fondos, alcance = leer_datos(conexion, opciones)
    except ValueError as error:
        parser.error(str(error))
    except psycopg.Error:
        parser.exit(1, "No se pudieron leer los datos de PostgreSQL. Revisá la conexión y las migraciones del proyecto.\n")

    opciones.salida.mkdir(parents=True, exist_ok=True)
    actividad_mensual(eventos, opciones, alcance)
    total, devoluciones = composicion_ingresos(fondos, opciones)
    porcentaje, sin_registrar = evolucion_asistencia(asistencias, opciones, alcance)
    percentil = concentracion(eventos, opciones, alcance)
    # Este promedio da el mismo peso a cada semana con datos. No equivale al
    # porcentaje de asistencia de todas las personas juntas en el período.
    media = f"{np.mean(porcentaje.dropna().to_numpy()):.2f}%" if porcentaje.notna().any() else "Sin datos"
    resumen = (
        f"Academia TM | Analítica\nPeríodo: {opciones.desde} a {opciones.hasta} (ambos incluidos)\n"
        f"Actividad y asistencia: {alcance}\nCaja: global, sin filtro de sede o cancha\n"
        f"Zona horaria: {ZONA_HORARIA}\nVentana de tendencia: {opciones.ventana_tendencia} semanas\n\n"
        f"Horas de clases finalizadas: {int(np.sum(eventos.tipo == 'clase'))}\n"
        f"Horas de reservas finalizadas: {int(np.sum(eventos.tipo == 'reserva'))}\n"
        f"Ingresos cobrados vigentes: ARS {total:,.2f}\nDevoluciones vigentes: ARS {devoluciones:,.2f}\n"
        f"Media de porcentajes semanales de asistencia: {media}\nParticipaciones sin registrar: {sin_registrar}\n"
        f"Percentil 90 de turnos por día/hora: {percentil if percentil is not None else 'Sin datos'}\n"
        "El percentil considera las 161 celdas (7 días × 23 horas), incluidas las que tienen cero turnos.\n"
        "Finalizado indica cierre del horario y no confirma realización, asistencia ni pago.\n"
    )
    (opciones.salida / "resumen.txt").write_text(resumen, encoding="utf-8")
    print(resumen)


if __name__ == "__main__":
    main()
