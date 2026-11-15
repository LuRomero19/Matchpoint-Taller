from . import consultas
from .forms import AsistenciaForm, ContratacionesForm, ReservasForm


REPORTES = {
    "contrataciones": {
        "titulo": "Situación de cobro de contrataciones",
        "descripcion": "Consultá los cobros de planes y membresías, sus devoluciones y las diferencias por cubrir o revisar.",
        "procesos": "Contrataciones de planes y membresías + caja",
        "formulario": ContratacionesForm, "consulta": consultas.contrataciones,
        "notas": (
            "El rango selecciona la fecha efectiva de alta. Los cobros y devoluciones son los vigentes a la fecha de consulta, cualquiera sea su fecha de registro.",
            "El total del importe acordado excluye contrataciones anuladas. Las diferencias por cubrir no constituyen por sí solas una deuda exigible; los excedentes requieren revisión administrativa.",
        ),
        "columnas": (
            ("titular", "Titular", "texto", 1.35), ("producto", "Producto", "texto", 1.45),
            ("mes", "Mes cubierto", "mes", 0.65), ("estado", "Estado", "texto", 0.7),
            ("importe", "Importe acordado", "dinero", 1), ("cobros", "Cobros", "dinero", 1),
            ("devoluciones", "Devoluciones", "dinero", 1), ("neto", "Neto recibido", "dinero", 1),
            ("diferencia", "Diferencia", "dinero", 0.95), ("situacion", "Situación", "texto", 1.15),
        ),
    },
    "asistencia": {
        "titulo": "Participación en clases y contratación de planes",
        "descripcion": "Relacioná la participación y la asistencia de cada alumno con el plan contratado para ese mes.",
        "procesos": "Contrataciones de planes + clases y asistencias",
        "formulario": AsistenciaForm, "consulta": consultas.asistencia,
        "notas": (
            "El rango selecciona fechas de clases finalizadas. El plan corresponde al titular y mes, incluyendo contratos vencidos y excluyendo anulados; no existe un vínculo directo entre clase y contratación.",
            "Incluye asignados sin carga y asistencias de personas no asignadas. El porcentaje es presentes / (presentes + ausentes); Sin registrar queda fuera. La tasa global se calcula sobre todas las marcas, sin promediar porcentajes de filas.",
            "Sin filtro de sede o profesor, incluye contratados sin actividad. Con esos filtros muestra sólo personas con participación en ese alcance. Una fila corresponde a una persona y mes.",
        ),
        "columnas": (
            ("alumno", "Alumno o participante", "texto", 1.6), ("mes", "Mes", "mes", 0.7),
            ("plan", "Plan contratado", "texto", 1.7), ("asignadas", "Clases asignadas", "entero", 1),
            ("presente", "Presentes", "entero", 0.8), ("ausente", "Ausentes", "entero", 0.8),
            ("sin_registrar", "Sin registrar", "entero", 0.9), ("porcentaje", "Asistencia", "porcentaje", 0.9),
        ),
    },
    "reservas": {
        "titulo": "Reservas y resultado financiero por cancha",
        "descripcion": "Consultá la actividad de reservas por cancha junto con sus cobros, devoluciones y neto recibido.",
        "procesos": "Reservas normales y con membresía + caja",
        "formulario": ReservasForm, "consulta": consultas.reservas,
        "notas": (
            "El rango selecciona la fecha del turno. Los cobros y devoluciones son los vigentes a la fecha de consulta, cualquiera sea su fecha de registro. No incluye el precio de las suscripciones de membresía.",
            "El importe acordado excluye reservas anuladas; sus cobros y devoluciones permanecen incluidos. Finalizada significa que terminó el horario y no acredita realización efectiva. El neto recibido no representa rentabilidad.",
        ),
        "columnas": (
            ("sede", "Sede", "texto", 1.5), ("cancha", "Cancha", "texto", 0.9),
            ("programado", "Programadas", "entero", 0.9), ("finalizado", "Finalizadas", "entero", 0.9),
            ("anulado", "Anuladas", "entero", 0.8), ("importe", "Importe acordado", "dinero", 1.1),
            ("cobros", "Cobros", "dinero", 1.1), ("devoluciones", "Devoluciones", "dinero", 1.1),
            ("neto", "Neto recibido", "dinero", 1.1),
        ),
    },
}
