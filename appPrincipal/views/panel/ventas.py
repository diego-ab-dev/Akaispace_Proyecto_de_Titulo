"""Panel de administración: ventas y estado de los envíos."""
import re

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from appPrincipal.decorators import admin_required
from appPrincipal.envios import TRANSPORTISTAS_ENCOMIENDA
from appPrincipal.models import Envio, Producto, Venta
from appPrincipal.views.panel.filtros import filtrar_por_fechas


@admin_required
def admin_ventas(request):
    query = request.GET.get('q', '')
    ordenar = request.GET.get('ordenar')

    ventas_list = Venta.objects.select_related(
        'usuario'
    ).prefetch_related(
        'producto_venta__producto'
    ).all()

    if query:
        ventas_list = ventas_list.filter(
            Q(usuario__nombre__icontains=query) | Q(id__icontains=query)
        )

    ventas_list, errores = filtrar_por_fechas(request, ventas_list, 'fecha')

    estado = request.GET.get('estado', '')
    if estado in dict(Envio.ESTADO_CHOICES):
        ventas_list = ventas_list.filter(datos_envio__estado=estado)
    entrega = request.GET.get('entrega', '')
    if entrega in dict(Venta.ENVIO_CHOICES):
        ventas_list = ventas_list.filter(metodo_envio=entrega)

    if ordenar == "antiguas":
        ventas_list = ventas_list.order_by("fecha")
    else:
        ventas_list = ventas_list.order_by("-fecha")

    paginator = Paginator(ventas_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_panel/ventas.html', {
        'ventas': page_obj.object_list,
        'page_obj': page_obj,
        'hoy': timezone.localdate(),
        'errores': errores,
        'estados': Envio.ESTADO_CHOICES,
        'entregas': Venta.ENVIO_CHOICES,
    })


@admin_required
def detalle_venta(request, venta_id):
    venta = get_object_or_404(Venta.objects.prefetch_related('producto_venta__producto'), id=venta_id)
    return render(request, 'admin_panel/detalle_venta.html', {'venta': venta})

@admin_required
def modificar_venta(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    envio = getattr(venta, 'datos_envio', None)

    error = None
    estado_post = None
    tracking_post = None
    transportista_post = None 

    if request.method == 'POST':
        estado_post = request.POST.get('estado')
        tracking_post = request.POST.get('numero_seguimiento', '').strip()
        transportista_post = request.POST.get('transportista') 

        estados_con_tracking = ["Enviado", "En Tránsito", "En Reparto"]

        if estado_post not in venta.estados_envio:
            error = "Estado no válido."
        elif not venta.lleva_seguimiento:
            tracking_post = ''
            transportista_post = None
        elif transportista_post not in TRANSPORTISTAS_ENCOMIENDA:
            error = "Selecciona un transportista válido."
        elif estado_post in estados_con_tracking and not tracking_post:
            error = "Debe ingresar un número de seguimiento para este estado."

        if not error and tracking_post:
            if not re.match(r'^[A-Za-z0-9]{5,20}$', tracking_post):
                error = "Número de seguimiento inválido. Solo letras y números (5–20 caracteres)."
            elif Envio.objects.filter(numero_seguimiento=tracking_post).exclude(id=envio.id if envio else None).exists():
                error = f"Error: El número '{tracking_post}' ya fue asignado a otro pedido anteriormente."
        
        if error:
            return render(request, 'admin_panel/modificar_venta.html', {
                'venta': venta,
                'envio': envio,
                'error': error,
                'estado_post': estado_post,
                'tracking_post': tracking_post,
                'transportista_post': transportista_post,
                'transportistas': TRANSPORTISTAS_ENCOMIENDA,
            })

        if envio is None:
            envio = Envio.objects.create(venta=venta)
        envio.numero_seguimiento = tracking_post
        if transportista_post:
            envio.transportista = transportista_post
        envio.guardar_estado(estado_post)

        return redirect('detalle_venta', venta_id=venta.id)

    return render(request, 'admin_panel/modificar_venta.html', {
        'venta': venta,
        'envio': envio,
        'error': error,
        'transportistas': TRANSPORTISTAS_ENCOMIENDA,
    })


@admin_required
@require_POST
def anular_venta(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)

    with transaction.atomic():
        envio, _ = Envio.objects.get_or_create(venta=venta)
        envio = Envio.objects.select_for_update().get(id=envio.id)
        if envio.estado != "Anulada":
            envio.estado = "Anulada"
            envio.save()

            devuelto = dict(
                venta.devoluciones.filter(estado='Aprobada', producto__isnull=False)
                .values_list('producto_id').annotate(total=Sum('cantidad'))
            )
            for item in venta.producto_venta.all():
                reponer = item.cantidad - devuelto.get(item.producto_id, 0)
                if reponer > 0:
                    Producto.todos.filter(id=item.producto_id).update(stock=F('stock') + reponer)

    return redirect(f"{reverse('detalle_venta', args=[venta_id])}?msg=anulada")
