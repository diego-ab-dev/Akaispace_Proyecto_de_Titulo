"""Panel de administración: reportes de gestión y tablero de KPI (HU-10). Los cálculos están en appPrincipal/reportes.py."""
from urllib.parse import urlencode

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from appPrincipal import reportes
from appPrincipal.decorators import admin_required
from appPrincipal.forms import MovimientoCajaForm
from appPrincipal.models import ConfiguracionSitio

VISTAS = [
    ('ventas', 'Ventas'),
    ('ganancia', 'Ganancia'),
    ('productos', 'Productos'),
    ('caja', 'Caja y retiros'),
    ('compras', 'Compras'),
    ('indicadores', 'Indicadores'),
]


def _datos_ventas(periodo):
    anterior = periodo.anterior()
    totales, totales_anterior = reportes.totales_ventas(periodo), reportes.totales_ventas(anterior)
    return {
        'totales': totales,
        'anterior': anterior,
        'variacion': {
            'bruto': reportes.variacion(totales['bruto'], totales_anterior['bruto']),
            'cantidad': reportes.variacion(totales['cantidad'], totales_anterior['cantidad']),
            'ticket_promedio': reportes.variacion(totales['ticket_promedio'], totales_anterior['ticket_promedio']),
        },
        'por_canal': reportes.ventas_por_canal(periodo),
        'por_medio': reportes.ventas_por_medio_de_pago(periodo),
        'serie': reportes.serie_ventas(periodo),
    }


def _datos_ganancia(periodo):
    return {'ganancia': reportes.ganancia(periodo), 'por_categoria': reportes.ganancia_por_categoria(periodo)}


def _datos_productos(periodo):
    criticos = reportes.stock_critico()
    return {
        'mas_vendidos': reportes.mas_vendidos(periodo),
        'stock_critico': criticos,
        'agotados': sum(1 for producto in criticos if producto.stock == 0),
    }


def _datos_caja(periodo):
    return {'caja': reportes.caja(periodo), 'form_caja': MovimientoCajaForm()}


def _datos_compras(periodo):
    return {'compras': reportes.compras(periodo)}


def _datos_indicadores(periodo):
    linea_base = ConfiguracionSitio.actual().kpi01_linea_base
    return {'tablero': reportes.tablero_kpi(linea_base), 'historial': reportes.historial_kpi(linea_base)}


DATOS = {
    'ventas': _datos_ventas,
    'ganancia': _datos_ganancia,
    'productos': _datos_productos,
    'caja': _datos_caja,
    'compras': _datos_compras,
    'indicadores': _datos_indicadores,
}


@admin_required
def admin_reportes(request):
    vista = request.GET.get('vista')
    if vista not in DATOS:
        vista = 'ventas'
    periodo, errores = reportes.periodo_desde_request(request.GET)
    if periodo.clave in dict(reportes.PERIODOS):
        consulta_periodo = urlencode({'periodo': periodo.clave})
    else:
        consulta_periodo = urlencode({'desde': periodo.desde.isoformat(), 'hasta': periodo.hasta.isoformat()})
    return render(request, 'admin_panel/reportes.html', {
        'consulta_periodo': consulta_periodo,
        'vista': vista,
        'vistas': VISTAS,
        'periodo': periodo,
        'periodos': reportes.PERIODOS,
        'errores': errores,
        'usa_periodo': vista != 'indicadores',
        **DATOS[vista](periodo),
    })


@admin_required
@require_POST
def registrar_movimiento_caja(request):
    form = MovimientoCajaForm(request.POST)
    if form.is_valid():
        movimiento = form.save()
        messages.success(request, f"{movimiento.get_tipo_display()} registrado.")
    else:
        errores = [error for lista in form.errors.values() for error in lista]
        messages.error(request, "No se registró el movimiento: " + " ".join(errores))
    return redirect(f"{reverse('admin_reportes')}?vista=caja&periodo=hoy")
