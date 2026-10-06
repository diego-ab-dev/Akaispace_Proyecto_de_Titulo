"""Panel de administración: devoluciones."""
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.timezone import now

from appPrincipal.decorators import admin_required
from appPrincipal.models import Devolucion, Producto, ProductoVenta
from appPrincipal.views.panel.filtros import filtrar_por_fechas


@admin_required
def admin_devoluciones(request):
    query = request.GET.get('q', '')
    estado = request.GET.get('estado', '')
    devoluciones = Devolucion.objects.select_related('usuario', 'producto').all().order_by('-fecha_solicitud')

    if query:
        devoluciones = devoluciones.filter(
            Q(usuario__nombre__icontains=query) |
            Q(producto__nombre__icontains=query) |
            Q(id__icontains=query)
        )

    if estado:
        devoluciones = devoluciones.filter(estado=estado)

    devoluciones, errores = filtrar_por_fechas(request, devoluciones, 'fecha_solicitud')

    paginator = Paginator(devoluciones, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_panel/devoluciones.html', {
        'devoluciones': page_obj,
        'page_obj': page_obj,
        'errores': errores,
        'hoy': timezone.localdate(),
    })


@admin_required
def responder_devolucion(request, devolucion_id):
    devolucion = get_object_or_404(Devolucion, id=devolucion_id)

    if devolucion.estado != 'Pendiente':
        return redirect('detalle_devolucion', devolucion_id=devolucion.id)

    item_venta = ProductoVenta.objects.filter(venta=devolucion.venta, producto=devolucion.producto).first()
    monto_a_reembolsar = item_venta.precio_unitario * devolucion.cantidad if item_venta else 0

    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion not in ('aceptar', 'rechazar'):
            return redirect('responder_devolucion', devolucion_id=devolucion.id)

        with transaction.atomic():
            devolucion = Devolucion.objects.select_for_update().get(id=devolucion.id)
            if devolucion.estado != 'Pendiente':
                return redirect('detalle_devolucion', devolucion_id=devolucion.id)

            if accion == 'aceptar':
                envio = getattr(devolucion.venta, 'datos_envio', None)
                venta_anulada = envio is not None and envio.estado == 'Anulada'
                if devolucion.producto_id and not venta_anulada:
                    Producto.todos.filter(id=devolucion.producto_id).update(stock=F('stock') + devolucion.cantidad)
                devolucion.estado = 'Aprobada'
            else:
                devolucion.estado = 'Rechazada'

            devolucion.respuesta_admin = request.POST.get('respuesta')
            devolucion.fecha_resolucion = now()
            devolucion.save()

        return redirect('admin_devoluciones')

    return render(request, 'admin_panel/responder_devolucion.html', {
        'devolucion': devolucion,
        'monto_a_reembolsar': monto_a_reembolsar
    })


@admin_required
def detalle_devolucion(request, devolucion_id):
    devolucion = get_object_or_404(Devolucion, id=devolucion_id)
    return render(request, 'admin_panel/detalle_devolucion.html', {
        'devolucion': devolucion
    })
