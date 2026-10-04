"""Panel de administración: dashboard principal."""
import calendar
from datetime import datetime

from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render

from appPrincipal.decorators import admin_required
from appPrincipal.models import Devolucion, Envio, Producto, Reclamo, Venta


@admin_required
def admin_dashboard(request):
    ultimas_ventas = Venta.objects.prefetch_related('producto_venta__producto').order_by('-fecha')[:4]
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

    anio_actual = datetime.now().year
    datos_grafico = []

    for mes in range(1, 13):
        ultimo_dia = calendar.monthrange(anio_actual, mes)[1]
        
        fecha_inicio = f"{anio_actual}-{mes:02d}-01"
        fecha_fin = f"{anio_actual}-{mes:02d}-{ultimo_dia}"

        total_mes = Venta.objects.filter(
            fecha__range=[fecha_inicio + " 00:00:00", fecha_fin + " 23:59:59"]
        ).aggregate(Sum('total'))['total__sum'] or 0
        
        datos_grafico.append(total_mes)


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
