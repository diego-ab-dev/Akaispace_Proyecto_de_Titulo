"""Checkout: selección de pago, confirmación de la compra y boleta."""
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from appPrincipal import envios
from appPrincipal.models import Boleta, Carrito, Envio, Producto, ProductoVenta, Venta


def _volver_al_carrito(mensaje):
    return redirect(f"{reverse('ver_carrito')}?{urlencode({'notif': mensaje, 'type': 'error'})}")


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
        Envio.objects.create(
            venta=venta, estado='En Preparación',
            transportista=envios.OPCIONES_ENVIO[metodo_envio]['transportista'],
        )
        Boleta.objects.create(venta=venta)
    return venta


@login_required
def seleccionar_pago(request):
    usuario = request.user
    carrito = Carrito.objects.filter(usuario=usuario).first()

    if not carrito or not carrito.items.exists():
        return redirect('ver_carrito')

    # la opción de entrega se elige en el carrito y llega como ?envio=; queda en la sesión
    # para el POST del pago y para compra_exitosa (que la vuelve a validar)
    if 'envio' in request.GET:
        request.session['metodo_envio'] = request.GET['envio']
    metodo_envio = request.session.get('metodo_envio')
    error_envio = envios.validar_eleccion(metodo_envio, usuario)
    if error_envio:
        return _volver_al_carrito(error_envio)

    # se revisa antes de mostrar el pago (el stock pudo bajar desde que se agregó al carrito);
    # al confirmar la compra se vuelve a revisar con las filas bloqueadas
    for item in carrito.items.select_related('producto'):
        if item.producto.is_deleted or item.cantidad > item.producto.stock:
            mensaje = (f"Solo hay {item.producto.stock} unidad(es) disponibles de {item.producto.nombre}. "
                       "Ajusta la cantidad para continuar.")
            if item.producto.is_deleted:
                mensaje = f"{item.producto.nombre} ya no está disponible."
            return _volver_al_carrito(mensaje)

    subtotal = sum(item.cantidad * item.producto.precio for item in carrito.items.all())
    costo_envio = envios.costo_envio(metodo_envio, subtotal)
    total = subtotal + costo_envio

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
        'total_items': total_items,
        'metodo_envio': metodo_envio,
        'opcion_envio': envios.OPCIONES_ENVIO[metodo_envio],
        'direccion_entrega': envios.direccion_de_entrega(metodo_envio, usuario),
    })

@login_required
def compra_exitosa(request):
    usuario = request.user
    carrito = Carrito.objects.filter(usuario=usuario).first()

    if not carrito or not carrito.items.exists():
        return redirect('ver_carrito')

    # se vuelve a validar: la dirección del cliente pudo cambiar después de elegir la entrega
    metodo_envio = request.session.get('metodo_envio')
    error_envio = envios.validar_eleccion(metodo_envio, usuario)
    if error_envio:
        return _volver_al_carrito(error_envio)
    direccion_envio = envios.direccion_de_entrega(metodo_envio, usuario)
    metodo_pago = request.session.get('metodo_pago', 'tarjeta')

    try:
        venta = crear_venta_desde_carrito(carrito, metodo_envio, direccion_envio, metodo_pago)
    except ValueError as e:
        return _volver_al_carrito(str(e))
    request.session.pop('metodo_envio', None)

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
