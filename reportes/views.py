from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import connections, transaction
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils import formats, timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from caja.servicios import exigir_acceso_caja
from common.fechas import FECHA_INICIO_OPERACIONES

from .catalogo import REPORTES


def formatear(valor, tipo):
    if valor is None:
        return "—"
    if tipo == "dinero":
        return "$ " + formats.number_format(valor, decimal_pos=2, use_l10n=True, force_grouping=True)
    if tipo == "porcentaje":
        return formats.number_format(valor, decimal_pos=2, use_l10n=True) + " %"
    if tipo == "mes":
        return valor.strftime("%m/%Y")
    if tipo == "entero":
        return formats.number_format(valor, decimal_pos=0, use_l10n=True, force_grouping=True)
    return str(valor)


def describir_filtros(formulario):
    aplicados = []
    for nombre, valor in formulario.cleaned_data.items():
        if valor is None or valor == "":
            continue
        campo = formulario.fields[nombre]
        if nombre in ("desde", "hasta"):
            texto = valor.strftime("%d/%m/%Y")
        elif hasattr(campo, "queryset"):
            texto = str(valor)
        elif hasattr(campo, "choices"):
            texto = dict(campo.choices).get(valor, valor)
        else:
            texto = str(valor)
        aplicados.append(f"{campo.label}: {texto}")
    return aplicados


@login_required
@never_cache
@require_GET
def inicio(request):
    exigir_acceso_caja(request.user)
    return render(request, "reportes/inicio.html", {"reportes": REPORTES.items()})


@login_required
@never_cache
@require_GET
def detalle(request, tipo, exportar=False):
    actor = exigir_acceso_caja(request.user)
    if tipo not in REPORTES:
        raise Http404
    reporte = REPORTES[tipo]
    parametros = request.GET.copy()
    parametros.pop("pagina", None)
    parametros.setdefault("desde", FECHA_INICIO_OPERACIONES.isoformat())
    parametros.setdefault("hasta", timezone.localdate().isoformat())
    formulario = reporte["formulario"](parametros)
    contexto = {"reporte": reporte, "tipo": tipo, "formulario": formulario, "columnas": reporte["columnas"],
                "parametros": parametros.urlencode(), "generado_en": timezone.now()}
    if formulario.is_valid():
        # Todos los agregados de la vista o PDF corresponden a la misma instantánea.
        with transaction.atomic(using="reportes"):
            with connections["reportes"].cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            resultado = reporte["consulta"](formulario.cleaned_data)
        filas = [[formatear(fila.get(clave), formato) for clave, _, formato, _ in reporte["columnas"]]
                 for fila in resultado["filas"]]
        totales = ["Totales"] + [formatear(resultado["totales"].get(clave), formato)
                                 for clave, _, formato, _ in reporte["columnas"][1:]]
        contexto.update({
            "pagina": Paginator([
                [{"texto": texto, "numero": reporte["columnas"][i][2] in ("dinero", "entero", "porcentaje")}
                 for i, texto in enumerate(fila)] for fila in filas
            ], 25).get_page(request.GET.get("pagina")),
            "totales_tabla": totales, "filtros_aplicados": describir_filtros(formulario),
            "indicadores": [(nombre, formatear(valor, formato)) for nombre, valor, formato in resultado["indicadores"]],
        })
        if exportar:
            from .pdf import generar_pdf

            contexto["filas_pdf"] = filas
            respuesta = HttpResponse(generar_pdf(contexto, actor), content_type="application/pdf")
            respuesta["Content-Disposition"] = f'attachment; filename="reporte-{tipo}.pdf"'
            respuesta["X-Content-Type-Options"] = "nosniff"
            return respuesta
    return render(request, "reportes/detalle.html", contexto, status=400 if exportar else 200)
