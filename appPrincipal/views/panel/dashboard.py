"""Panel de administración: resumen del negocio (HU-10). Los cálculos están en appPrincipal/reportes.py."""
from django.shortcuts import render
from django.utils import timezone

from appPrincipal import reportes
from appPrincipal.decorators import admin_required
from appPrincipal.models import ConfiguracionSitio, Devolucion, Envio, Reclamo, Venta


def _por_atender():
    return [
        {'nombre': 'Pedidos por preparar', 'cantidad': Envio.objects.filter(estado='En Preparación').count(),
         'url_nombre': 'admin_ventas', 'filtro': '?estado=En+Preparación', 'icono': 'bx-package'},
        {'nombre': 'Listos para retiro', 'cantidad': Envio.objects.filter(estado='Listo para retiro').count(),
         'url_nombre': 'admin_ventas', 'filtro': '?estado=Listo+para+retiro', 'icono': 'bx-store'},
        {'nombre': 'Reclamos abiertos', 'cantidad': Reclamo.objects.filter(estado='Abierto').count(),
         'url_nombre': 'admin_reclamos', 'filtro': '', 'icono': 'bx-message-square-error'},
        {'nombre': 'Devoluciones pendientes', 'cantidad': Devolucion.objects.filter(estado='Pendiente').count(),
         'url_nombre': 'admin_devoluciones', 'filtro': '', 'icono': 'bx-revision'},
    ]


@admin_required
def admin_dashboard(request):
    hoy = timezone.localdate()
    mes = reportes.periodo_predefinido('mes', hoy)
    anterior = mes.anterior()
    ventas, ventas_anterior = reportes.totales_ventas(mes), reportes.totales_ventas(anterior)
    ganancia, ganancia_anterior = reportes.ganancia(mes), reportes.ganancia(anterior)
    criticos = reportes.stock_critico()

    return render(request, 'admin_panel/dashboard.html', {
        'hoy': hoy,
        'mes': mes,
        'anterior': anterior,
        'ventas': ventas,
        'ganancia': ganancia,
        'variacion': {
            'bruto': reportes.variacion(ventas['bruto'], ventas_anterior['bruto']),
            'cantidad': reportes.variacion(ventas['cantidad'], ventas_anterior['cantidad']),
            'ticket_promedio': reportes.variacion(ventas['ticket_promedio'], ventas_anterior['ticket_promedio']),
            'ganancia': reportes.variacion(ganancia['ganancia']['neto'], ganancia_anterior['ganancia']['neto']),
        },
        'serie': reportes.serie_ventas(reportes.ultimos_12_meses(hoy)),
        'tablero': reportes.tablero_kpi(ConfiguracionSitio.actual().kpi01_linea_base, hoy),
        'por_atender': _por_atender(),
        'ultimas_ventas': Venta.objects.select_related('usuario').order_by('-fecha')[:6],
        'stock_critico': criticos[:6],
        'total_stock_critico': criticos.count(),
    })
