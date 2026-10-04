"""Panel de administración: dashboard principal."""
from datetime import datetime

from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from appPrincipal.decorators import admin_required
from appPrincipal.models import Devolucion, Envio, Producto, Reclamo, Venta


def ventas_por_mes(anio):
    """Total vendido en cada mes del año (lista de 12 montos), sin contar las ventas anuladas."""
    inicio = timezone.make_aware(datetime(anio, 1, 1))
    fin = timezone.make_aware(datetime(anio + 1, 1, 1))
    ventas = Venta.objects.filter(fecha__gte=inicio, fecha__lt=fin).exclude(
        datos_envio__estado='Anulada'
    ).values_list('fecha', 'total')

    # una sola consulta y se agrupa aquí: TruncMonth en MySQL depende de que el servidor
    # tenga cargadas las tablas de zonas horarias, y si no las tiene devuelve vacío
    totales = [0] * 12
    for fecha, total in ventas:
        totales[timezone.localtime(fecha).month - 1] += total
    return totales


@admin_required
def admin_dashboard(request):
    ultimas_ventas = Venta.objects.select_related('usuario').prefetch_related('producto_venta__producto').order_by('-fecha')[:4]
    ventas_info = [
        {
            "usuario": venta.usuario.nombre,
            "productos": [
                f"{pv.producto.nombre} (x{pv.cantidad})" for pv in venta.producto_venta.all()
            ],
            "fecha": venta.fecha,
        }
        for venta in ultimas_ventas
    ]
    ultimos_reclamos = Reclamo.objects.select_related('usuario').order_by('-fecha')[:4]
    reclamos_info = [
        {
            "usuario": reclamo.usuario.nombre,
            "asunto": reclamo.asunto,
            "fecha": reclamo.fecha,
        }
        for reclamo in ultimos_reclamos
    ]
    
    productos_bajo_stock = Producto.objects.filter(stock__lt=5).order_by('stock')[:4]
    productos_info = [
        {
            "nombre": producto.nombre,
            "stock": producto.stock,
        }
        for producto in productos_bajo_stock
    ]

    datos_grafico = ventas_por_mes(timezone.localdate().year)

    context = {
        "ventas_info": ventas_info,
        "reclamos_info": reclamos_info,
        "productos_info": productos_info,
        "datos_grafico": datos_grafico,
    }
    return render(request, 'admin_panel/dashboard.html', context)


@admin_required
def get_dashboard_counts(request):
    envios_pendientes = Envio.objects.filter(estado="En Preparación").count()
    ventas = Venta.objects.count()
    reclamos = Reclamo.objects.count()
    devoluciones = Devolucion.objects.count()

    return JsonResponse({
        "envios_pendientes": envios_pendientes,
        "ventas": ventas,
        "reclamos": reclamos,
        "devoluciones": devoluciones,
    })
