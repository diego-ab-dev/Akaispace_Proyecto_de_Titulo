"""Flujo de pago con Webpay Plus
"""
import logging
import secrets

from django.db import transaction

from appPrincipal import correos, envios, webpay
from appPrincipal.models import (Boleta, Envio, ItemCarritoProducto, PagoWebpay, Producto,
                                 ProductoVenta, Venta)

logger = logging.getLogger(__name__)

# Registra la venta: descuenta el stock, crea el envío y emite la boleta
def crear_venta(usuario, items, metodo_envio, direccion_envio, metodo_pago):
    if not items:
        raise ValueError("Tu carrito está vacío.")
    with transaction.atomic():
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
    return f"AKA{secrets.token_hex(6).upper()}"

# Crea el PagoWebpay pendiente y la transacción en Transbank
def iniciar_pago(usuario, carrito, metodo_envio, url_retorno):
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
        logger.error("No se pudo reembolsar el pago %s (%s)", pago.orden_compra, motivo)
        pago.estado = PagoWebpay.ERROR
        pago.detalle = f"{motivo} No se pudo reversar el cargo automáticamente."


def confirmar_pago(token):
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

        if int(respuesta.get('amount') or 0) != pago.monto or respuesta.get('buy_order') != pago.orden_compra:
            logger.error("Pago %s: Transbank aprobó datos distintos a los enviados: %s", pago.orden_compra, respuesta)
            _reembolsar(pago, "Los datos del pago no coinciden con la compra.")
            pago.save()
            return pago

        try:
            venta = crear_venta(pago.usuario, pago.items, pago.metodo_envio, pago.direccion_envio,
                                pago.metodo_pago_texto)
        except ValueError as error:
            _reembolsar(pago, f"{error}. Reversamos el cargo completo.")
            pago.save()
            return pago

        pago.venta = venta
        pago.estado = PagoWebpay.APROBADO
        pago.detalle = ''
        pago.save()
        _sacar_del_carrito(pago)
    logger.info("Pago %s aprobado: venta %s", pago.orden_compra, pago.venta_id)
    correos.enviar_confirmacion_compra(pago.venta)
    return pago


def anular_pago(pago, motivo):
    with transaction.atomic():
        pago = PagoWebpay.objects.select_for_update().get(pk=pago.pk)
        if pago.estado == PagoWebpay.PENDIENTE:
            pago.estado = PagoWebpay.ANULADO
            pago.detalle = motivo
            pago.save(update_fields=['estado', 'detalle', 'actualizado'])
    return pago
