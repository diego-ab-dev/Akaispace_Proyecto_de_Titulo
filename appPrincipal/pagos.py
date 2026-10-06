"""Flujo de pago con Webpay Plus (HU-05) y creación de la venta al confirmarse (HU-06).

1. iniciar_pago: copia el carrito en un PagoWebpay pendiente y abre la transacción en Transbank.
   Todavía no se toca el stock.
2. El cliente paga en Webpay y Transbank lo devuelve a webpay_retorno con un token.
3. confirmar_pago: confirma con Transbank y, solo si el pago fue aprobado, crea la venta
   (descuenta el stock y emite la boleta). Si el stock se agotó mientras pagaba, reversa el cargo.
"""
import logging
import secrets

from django.db import transaction

from appPrincipal import envios, webpay
from appPrincipal.models import (Boleta, Envio, ItemCarritoProducto, PagoWebpay, Producto,
                                 ProductoVenta, Venta)

logger = logging.getLogger(__name__)


def crear_venta(usuario, items, metodo_envio, direccion_envio, metodo_pago):
    """Registra la venta: descuenta el stock, crea el envío y emite la boleta.

    items: [{'producto_id', 'cantidad', 'precio_unitario'}]. Es todo o nada: si un producto
    ya no está a la venta o no alcanza el stock, lanza ValueError y no se guarda nada.
    Las filas de los productos quedan bloqueadas hasta terminar, así dos compras al mismo
    tiempo no pueden vender la misma última unidad.
    """
    if not items:
        raise ValueError("Tu carrito está vacío.")
    with transaction.atomic():
        # se bloquean en orden de id para que dos compras simultáneas no se esperen mutuamente
        bloqueados = Producto.todos.select_for_update().filter(
            id__in=[item['producto_id'] for item in items]
        ).order_by('id')
        productos = {producto.id: producto for producto in bloqueados}

        for item in items:
            producto = productos.get(item['producto_id'])
            if producto is None or producto.is_deleted:
                raise ValueError(f"{producto.nombre if producto else 'Un producto'} ya no está disponible.")
            if item['cantidad'] > producto.stock:
                raise ValueError(f"Stock insuficiente para el producto {producto.nombre}")

        venta = Venta.objects.create(
            usuario=usuario,
            metodo_envio=metodo_envio,
            direccion_envio=direccion_envio,
            metodo_pago=metodo_pago,
        )
        for item in items:
            producto = productos[item['producto_id']]
            ProductoVenta.objects.create(
                venta=venta, producto=producto, cantidad=item['cantidad'], precio_unitario=item['precio_unitario'],
            )
            producto.stock -= item['cantidad']
            producto.save(update_fields=['stock'])

        venta.calcular_total()
        Envio.objects.create(
            venta=venta, estado='En Preparación',
            transportista=envios.OPCIONES_ENVIO[metodo_envio]['transportista'],
        )
        Boleta.objects.create(venta=venta)
    return venta


def _nueva_orden_compra():
    # Transbank acepta hasta 26 caracteres; el sufijo al azar evita repetir órdenes entre ambientes
    return f"AKA{secrets.token_hex(6).upper()}"


def iniciar_pago(usuario, carrito, metodo_envio, url_retorno):
    """Crea el PagoWebpay pendiente y la transacción en Transbank.

    Devuelve (pago, url_webpay). Lanza webpay.ErrorWebpay si Transbank no responde
    (el pago queda registrado con estado de error).
    """
    items = [
        {'producto_id': item.producto_id, 'cantidad': item.cantidad, 'precio_unitario': item.producto.precio}
        for item in carrito.items.select_related('producto')
    ]
    subtotal = sum(item['cantidad'] * item['precio_unitario'] for item in items)
    pago = PagoWebpay.objects.create(
        usuario=usuario,
        orden_compra=_nueva_orden_compra(),
        monto=subtotal + envios.costo_envio(metodo_envio, subtotal),
        items=items,
        metodo_envio=metodo_envio,
        direccion_envio=envios.direccion_de_entrega(metodo_envio, usuario),
    )
    try:
        respuesta = webpay.crear(pago.orden_compra, f"usuario-{usuario.pk}", pago.monto, url_retorno)
    except webpay.ErrorWebpay:
        pago.estado = PagoWebpay.ERROR
        pago.detalle = "No se pudo iniciar el pago con Transbank."
        pago.save(update_fields=['estado', 'detalle', 'actualizado'])
        raise
    pago.token = respuesta['token']
    pago.save(update_fields=['token', 'actualizado'])
    return pago, respuesta['url']


def _sacar_del_carrito(pago):
    """Quita del carrito lo que se compró (si el cliente agregó otras cosas mientras pagaba, quedan)."""
    for item in pago.items:
        en_carrito = ItemCarritoProducto.objects.filter(
            carrito__usuario=pago.usuario, producto_id=item['producto_id']
        ).first()
        if en_carrito is None:
            continue
        if en_carrito.cantidad > item['cantidad']:
            en_carrito.cantidad -= item['cantidad']
            en_carrito.save(update_fields=['cantidad'])
        else:
            en_carrito.delete()


def _reembolsar(pago, motivo):
    try:
        webpay.reembolsar(pago.token, pago.monto)
        pago.estado = PagoWebpay.REEMBOLSADO
        pago.detalle = motivo
    except webpay.ErrorWebpay:
        # el cliente pagó y no se pudo devolver: queda en error para revisarlo a mano
        logger.error("No se pudo reembolsar el pago %s (%s)", pago.orden_compra, motivo)
        pago.estado = PagoWebpay.ERROR
        pago.detalle = f"{motivo} No se pudo reversar el cargo automáticamente."


def confirmar_pago(token):
    """Procesa el regreso desde Webpay con token_ws. Devuelve el PagoWebpay, o None si no existe.

    Es seguro llamarlo dos veces con el mismo token (el cliente recarga la página o vuelve
    atrás): la fila queda bloqueada mientras se procesa y un pago ya resuelto no se repite.
    """
    with transaction.atomic():
        pago = PagoWebpay.objects.select_for_update().filter(token=token).first()
        if pago is None or pago.estado != PagoWebpay.PENDIENTE:
            return pago

        try:
            respuesta = webpay.confirmar(token)
        except webpay.ErrorWebpay:
            pago.estado = PagoWebpay.ERROR
            pago.detalle = "No pudimos confirmar el pago con Transbank."
            pago.save()
            return pago

        pago.guardar_respuesta(respuesta)
        if not webpay.fue_aprobado(respuesta):
            pago.estado = PagoWebpay.RECHAZADO
            pago.detalle = "Transbank rechazó el pago."
            pago.save()
            return pago

        # nunca debería pasar, pero si lo aprobado no calza con lo que se cobró no se entrega la compra
        if int(respuesta.get('amount') or 0) != pago.monto or respuesta.get('buy_order') != pago.orden_compra:
            logger.error("Pago %s: Transbank aprobó datos distintos a los enviados: %s", pago.orden_compra, respuesta)
            _reembolsar(pago, "Los datos del pago no coinciden con la compra.")
            pago.save()
            return pago

        try:
            venta = crear_venta(pago.usuario, pago.items, pago.metodo_envio, pago.direccion_envio,
                                pago.metodo_pago_texto)
        except ValueError as error:
            # se agotó el stock (o se dejó de vender un producto) mientras el cliente estaba en Webpay
            _reembolsar(pago, f"{error}. Reversamos el cargo completo.")
            pago.save()
            return pago

        pago.venta = venta
        pago.estado = PagoWebpay.APROBADO
        pago.detalle = ''
        pago.save()
        _sacar_del_carrito(pago)
    logger.info("Pago %s aprobado: venta %s", pago.orden_compra, pago.venta_id)
    return pago


def anular_pago(pago, motivo):
    """El cliente canceló en Webpay o se le acabó el tiempo: no hubo cargo."""
    with transaction.atomic():
        pago = PagoWebpay.objects.select_for_update().get(pk=pago.pk)
        if pago.estado == PagoWebpay.PENDIENTE:
            pago.estado = PagoWebpay.ANULADO
            pago.detalle = motivo
            pago.save(update_fields=['estado', 'detalle', 'actualizado'])
    return pago
