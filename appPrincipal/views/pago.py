"""Checkout: selección de pago, confirmación de la compra y boleta."""
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from appPrincipal.models import Boleta, Carrito, Envio, Producto, ProductoVenta, Venta


def crear_venta_desde_carrito(carrito, metodo_envio, direccion_envio, metodo_pago):
    """Convierte el carrito en una venta: descuenta el stock, emite la boleta y vacía el carrito.

    Es todo o nada: si un producto ya no está a la venta o no alcanza el stock, lanza
    ValueError y no se guarda nada. Las filas de los productos quedan bloqueadas hasta
    terminar, así dos compras al mismo tiempo no pueden vender la misma última unidad.
    """
    with transaction.atomic():
        items = list(carrito.items.all())
        if not items:
            raise ValueError("Tu carrito está vacío.")
        # se bloquean en orden de id para que dos compras simultáneas no se esperen mutuamente
        bloqueados = Producto.todos.select_for_update().filter(
            id__in=[item.producto_id for item in items]
        ).order_by('id')
        productos = {producto.id: producto for producto in bloqueados}

        for item in items:
            producto = productos[item.producto_id]
            if producto.is_deleted:
                raise ValueError(f"{producto.nombre} ya no está disponible.")
            if item.cantidad > producto.stock:
                raise ValueError(f"Stock insuficiente para el producto {producto.nombre}")

        venta = Venta.objects.create(
            usuario=carrito.usuario,
            metodo_envio=metodo_envio,
            direccion_envio=direccion_envio,
            metodo_pago=metodo_pago,
        )
        for item in items:
            producto = productos[item.producto_id]
            ProductoVenta.objects.create(
                venta=venta, producto=producto, cantidad=item.cantidad, precio_unitario=producto.precio,
            )
            producto.stock -= item.cantidad
            producto.save(update_fields=['stock'])

        venta.calcular_total()
        carrito.items.all().delete()
        Envio.objects.create(venta=venta, estado='En Preparación', transportista="Starken")
        Boleta.objects.create(venta=venta)
    return venta


@login_required
def seleccionar_pago(request):
    usuario = request.user
    carrito = Carrito.objects.filter(usuario=usuario).first()

    if not carrito or not carrito.items.exists():
        return redirect('ver_carrito')

    subtotal = sum(item.cantidad * item.producto.precio for item in carrito.items.all())

    costo_envio = 5990
    total = subtotal + costo_envio

    request.session['metodo_envio'] = "domicilio"
    request.session['direccion_envio'] = usuario.direccion
    request.session['costo_envio'] = costo_envio 

    total_items = sum(item.cantidad for item in carrito.items.all())

    if request.method == 'POST':
        metodo_pago = request.POST.get('metodo_pago')
        request.session['metodo_pago'] = metodo_pago

        if metodo_pago in ["tarjeta", "transferencia"]:
            return redirect('compra_exitosa')

    return render(request, 'seleccionar_pago.html', {
        'total': total,
        'subtotal': subtotal,
        'costo_envio': costo_envio,
        'total_items': total_items  
    })

@login_required
def compra_exitosa(request):
    usuario = request.user
    carrito = Carrito.objects.filter(usuario=usuario).first()

    if not carrito or not carrito.items.exists():
        return redirect('ver_carrito')

    metodo_envio = request.session.get('metodo_envio', 'tienda')
    direccion_envio = request.session.get('direccion_envio')
    metodo_pago = request.session.get('metodo_pago', 'tarjeta')

    try:
        venta = crear_venta_desde_carrito(carrito, metodo_envio, direccion_envio, metodo_pago)
    except ValueError as e:
        return redirect(f"{reverse('ver_carrito')}?{urlencode({'notif': str(e), 'type': 'error'})}")

    total_cantidad = sum(item.cantidad for item in venta.producto_venta.all())

    return render(request, 'compra_exitosa.html', {
        'venta': venta,
        'metodo_pago': metodo_pago,
        'total_cantidad': total_cantidad,
    })


@login_required
def ver_boleta(request, venta_id):
    # el cliente solo ve sus boletas; el administrador puede ver todas
    ventas = Venta.objects.all() if request.user.is_staff else Venta.objects.filter(usuario=request.user)
    venta = get_object_or_404(ventas, id=venta_id)
    Boleta.objects.get_or_create(venta=venta)

    return render(request, 'boleta.html', {'venta': venta})
