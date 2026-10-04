"""Historial de compras del cliente."""
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.timezone import now
from django.views.decorators.http import require_POST

from appPrincipal.models import Devolucion, Venta


@login_required
def ver_compras(request):
    usuario = request.user
    orden = request.GET.get('orden', 'reciente')

    if orden == 'antiguo':
        orden_query = 'fecha'
    else:
        orden_query = '-fecha'

    compras_list = Venta.objects.filter(usuario=usuario).prefetch_related(
        'producto_venta__producto'
    ).order_by(orden_query)

    paginator = Paginator(compras_list, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    for compra in page_obj:
        for producto_venta in compra.producto_venta.all():
            producto = producto_venta.producto
            producto_venta.opinion_enviada = producto.opiniones.filter(usuario=usuario).exists()

    return render(request, 'ver_compras.html', {
        'usuario': usuario,
        'page_obj': page_obj,
        'orden': orden, 
    })


@login_required
def ver_detalle_compra(request, compra_id):
    compra = get_object_or_404(Venta, id=compra_id, usuario=request.user)

    total_cantidad = sum(item.cantidad for item in compra.producto_venta.all())

    # producto_id puede ser null (el modelo lo permite): esas devoluciones no marcan ningún producto
    devoluciones_existentes = {
        producto_id: True
        for producto_id in Devolucion.objects.filter(venta=compra, producto__isnull=False).values_list('producto_id', flat=True)
    }

    return render(request, 'detalle_compra.html', {
        'compra': compra,
        'total_cantidad': total_cantidad,
        'devoluciones_existentes': devoluciones_existentes,   
    })


@login_required
@require_POST
def marcar_recibido(request, compra_id):
    compra = get_object_or_404(Venta, id=compra_id, usuario=request.user)

    envio = getattr(compra, 'datos_envio', None)
    base_url = reverse('ver_detalle', kwargs={'compra_id': compra_id})

    if envio is None or envio.estado not in ["Enviado", "En Tránsito", "En Reparto"]:
        qs = urlencode({'notif': "Aún no puedes marcar como recibido.", 'type': 'error'})
        return redirect(f"{base_url}?{qs}")

    envio.estado = "Entregado"
    envio.fecha_entrega = now()
    envio.save()

    qs = urlencode({'notif': "Pedido marcado como recibido.", 'type': 'success'})
    return redirect(f"{base_url}?{qs}")
