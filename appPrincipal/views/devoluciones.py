"""Solicitudes de devolución del cliente."""
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from appPrincipal.forms import SolicitudDevolucionForm
from appPrincipal.models import Devolucion, Producto, ProductoVenta, Venta


def _cantidad_ya_solicitada(compra, producto):
    return Devolucion.objects.filter(venta=compra, producto=producto).exclude(
        estado='Rechazada'
    ).aggregate(total=Sum('cantidad'))['total'] or 0


@login_required
def crear_devolucion(request, compra_id, producto_id):
    usuario = request.user
    compra = get_object_or_404(Venta, id=compra_id, usuario=usuario)
    producto = get_object_or_404(Producto.todos, id=producto_id)
    item = get_object_or_404(compra.producto_venta, producto=producto)
    url_compra = reverse('ver_detalle', kwargs={'compra_id': compra.id})

    envio = getattr(compra, 'datos_envio', None)
    if envio is None or envio.estado != 'Entregado':
        aviso = urlencode({'notif': 'Solo puedes pedir la devolución de una compra ya entregada.', 'type': 'error'})
        return redirect(f"{url_compra}?{aviso}")

    disponible = item.cantidad - _cantidad_ya_solicitada(compra, producto)
    if disponible <= 0:
        aviso = urlencode({'notif': 'Ya pediste la devolución de todas las unidades de este producto.', 'type': 'error'})
        return redirect(f"{url_compra}?{aviso}")

    form = SolicitudDevolucionForm(cantidad_maxima=disponible)

    if request.method == 'POST':
        form = SolicitudDevolucionForm(request.POST, request.FILES, cantidad_maxima=disponible)

        if form.is_valid():
            with transaction.atomic():
                Venta.objects.select_for_update().get(id=compra.id)
                disponible = item.cantidad - _cantidad_ya_solicitada(compra, producto)
                if form.cleaned_data['cantidad'] > disponible:
                    aviso = urlencode({'notif': 'La cantidad supera lo que aún puedes devolver.', 'type': 'error'})
                    return redirect(f"{url_compra}?{aviso}")

                Devolucion.objects.create(
                    usuario=usuario,
                    venta=compra,
                    producto=producto,
                    cantidad=form.cleaned_data['cantidad'],
                    motivo=form.cleaned_data['descripcion'],
                    imagen1=form.cleaned_data['imagen1'],
                    imagen2=form.cleaned_data['imagen2'],
                    imagen3=form.cleaned_data['imagen3'],
                    estado='Pendiente'
                )
            return redirect('/perfil?notif=Solicitud+de+devolución+enviada+con+éxito&type=success')

    return render(request, 'crear_devolucion.html', {
        'compra': compra,
        'producto': producto,
        'cantidad_comprada': item.cantidad,
        'cantidad_disponible': disponible,
        'form': form
    })


@login_required
def listar_devoluciones(request):
    usuario = request.user
    todos_devoluciones = Devolucion.objects.filter(usuario=usuario).order_by('-id')

    paginator = Paginator(todos_devoluciones, 5) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)


    return render(request, 'lista_devoluciones.html', {
        'todos_devoluciones': todos_devoluciones,
        'page_obj': page_obj,
    })

@login_required
def ver_detalle_devolucion(request, devolucion_id):
    usuario = request.user
    devolucion = get_object_or_404(Devolucion, id=devolucion_id, usuario=usuario)
    
    monto_reembolso = 0
    try:
        item_venta = ProductoVenta.objects.get(
            venta=devolucion.venta, 
            producto=devolucion.producto
        )
        monto_reembolso = item_venta.precio_unitario * devolucion.cantidad
    except ProductoVenta.DoesNotExist:
        monto_reembolso = 0

    return render(request, 'detalle_devolucion.html', {
        'devolucion': devolucion,
        'monto_reembolso': monto_reembolso 
    })
