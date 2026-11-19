"""Registro de ventas y pago con Webpay Plus."""
import logging
import secrets

from django.db import transaction

from appPrincipal import correos, envios, webpay
from appPrincipal.models import (Carrito, Comprobante, DetallePagoWebpay, Envio, ItemCarritoProducto, PagoWebpay,
                                 Producto, ProductoVenta, Venta)

logger = logging.getLogger(__name__)

MEDIOS_PAGO_PRESENCIALES = [Venta.PAGO_TARJETA, Venta.PAGO_EFECTIVO, Venta.PAGO_TRANSFERENCIA]
CANALES_PRESENCIALES = [Venta.CANAL_TIENDA, Venta.CANAL_WHATSAPP]


def _registrar_venta(items, **datos_venta):
    bloqueados = Producto.todos.select_for_update().filter(
        id__in=[item['producto_id'] for item in items]
    ).order_by('id')
    productos = {producto.id: producto for producto in bloqueados}

    for item in items:
        producto = productos.get(item['producto_id'])
        if producto is None or producto.is_deleted:
            raise ValueError(f"{producto.nombre if producto else 'Un producto'} ya no está disponible.")
        if item['cantidad'] < 1:
            raise ValueError(f"La cantidad de {producto.nombre} debe ser al menos 1.")
        if item['cantidad'] > producto.stock:
            raise ValueError(f"Stock insuficiente para el producto {producto.nombre} (disponible: {producto.stock})")

    venta = Venta.objects.create(**datos_venta)
    for item in items:
        producto = productos[item['producto_id']]
        ProductoVenta.objects.create(
            venta=venta, producto=producto, cantidad=item['cantidad'],
            precio_unitario=item.get('precio_unitario', producto.precio), costo_unitario=producto.costo,
        )
        producto.stock -= item['cantidad']
        producto.save(update_fields=['stock'])

    venta.calcular_total()
    return venta


def crear_venta(usuario, items, metodo_envio, direccion_envio, metodo_pago):
    if not items:
        raise ValueError("Tu carrito está vacío.")
    with transaction.atomic():
        venta = _registrar_venta(
            items, usuario=usuario, metodo_envio=metodo_envio, direccion_envio=direccion_envio,
            metodo_pago=metodo_pago,
        )
        Envio.objects.create(
            venta=venta, estado='En Preparación',
            transportista=envios.OPCIONES_ENVIO[metodo_envio]['transportista'],
        )
        Comprobante.objects.create(venta=venta)
    return venta


def crear_venta_presencial(items, canal, metodo_pago):
    if canal not in CANALES_PRESENCIALES:
        raise ValueError("Selecciona si la venta fue en la tienda física o por WhatsApp.")
    if metodo_pago not in MEDIOS_PAGO_PRESENCIALES:
        raise ValueError("Selecciona el medio de pago.")
    if not items:
        raise ValueError("Agrega al menos un producto a la venta.")
    with transaction.atomic():
        venta = _registrar_venta(items, canal=canal, metodo_pago=metodo_pago)
        Comprobante.objects.create(venta=venta)
    return venta


def validar_datos_comprador(usuario):
    faltan = [dato for dato, valor in [('tu RUT', usuario.rut), ('tu teléfono', usuario.telefono)] if not valor]
    if faltan:
        return f"Completa {' y '.join(faltan)} en «Tus datos» para continuar con la compra."
    return None


def _nueva_orden_compra():
    return f"AKA{secrets.token_hex(6).upper()}"

def iniciar_pago(usuario, carrito, metodo_envio, url_retorno):
    items = list(carrito.items.select_related('producto'))
    subtotal = sum(item.cantidad * item.producto.precio for item in items)
    with transaction.atomic():
        pago = PagoWebpay.objects.create(
            usuario=usuario,
            carrito=carrito,
            orden_compra=_nueva_orden_compra(),
            monto=subtotal + envios.costo_envio(metodo_envio, subtotal),
            metodo_envio=metodo_envio,
            direccion_envio=envios.direccion_de_entrega(metodo_envio, usuario),
        )
        DetallePagoWebpay.objects.bulk_create([
            DetallePagoWebpay(pago=pago, producto_id=item.producto_id, cantidad=item.cantidad,
                              precio_unitario=item.producto.precio)
            for item in items
        ])
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


def items_del_pago(pago):
    return [
        {'producto_id': detalle.producto_id, 'cantidad': detalle.cantidad, 'precio_unitario': detalle.precio_unitario}
        for detalle in pago.detalles.all()
    ]


def _sacar_del_carrito(pago):
    for detalle in pago.detalles.all():
        en_carrito = ItemCarritoProducto.objects.filter(
            carrito__usuario=pago.usuario, carrito__vigente=True, producto_id=detalle.producto_id
        ).first()
        if en_carrito is None:
            continue
        if en_carrito.cantidad > detalle.cantidad:
            en_carrito.cantidad -= detalle.cantidad
            en_carrito.save(update_fields=['cantidad'])
        else:
            en_carrito.delete()


def _cerrar_carrito(pago):
    _sacar_del_carrito(pago)
    carrito = pago.carrito
    if carrito is None or not carrito.vigente:
        return
    carrito.cerrar()
    if carrito.items.exists():
        carrito.items.update(carrito=Carrito.objects.create(usuario=pago.usuario))


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
            venta = crear_venta(pago.usuario, items_del_pago(pago), pago.metodo_envio, pago.direccion_envio,
                                Venta.PAGO_WEBPAY)
        except ValueError as error:
            _reembolsar(pago, f"{error}. Reversamos el cargo completo.")
            pago.save()
            return pago

        pago.venta = venta
        pago.estado = PagoWebpay.APROBADO
        pago.detalle = ''
        pago.save()
        _cerrar_carrito(pago)
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
