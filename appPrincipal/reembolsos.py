"""Devoluciones y reembolsos."""
import logging
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.db.models import F, Sum
from django.utils.timezone import now

from appPrincipal import webpay
from appPrincipal.models import Devolucion, PagoWebpay, Producto, ProductoVenta, Venta

logger = logging.getLogger(__name__)

PLAZO_ANULACION_WEBPAY = timedelta(days=90)
TIPOS_PAGO_SIN_ANULACION_PARCIAL = {'SI', 'S2', 'NC'}

REALIZADO = 'realizado'
PENDIENTE_MANUAL = 'pendiente_manual'


class OperacionNoPermitida(Exception):
    pass


@dataclass
class ResultadoReembolso:
    realizado: bool
    monto: int
    motivo: str = ''
    guardado: bool = True


@dataclass
class _Solicitud:
    pago_id: int
    orden_compra: str
    token: str
    monto: int
    saldo: int
    motivo: str | None


def _pesos(monto):
    return f"${monto:,}".replace(',', '.')


def _pago_webpay(venta, bloquear=False):
    if venta.canal != Venta.CANAL_WEB:
        return None
    pagos = PagoWebpay.objects.filter(venta=venta, estado__in=[PagoWebpay.APROBADO, PagoWebpay.REEMBOLSADO])
    return (pagos.select_for_update() if bloquear else pagos).first()


def _monto_productos(devolucion):
    item = ProductoVenta.objects.filter(venta=devolucion.venta, producto=devolucion.producto).first()
    return item.precio_unitario * devolucion.cantidad if item else 0


def _saldo(devolucion, pago):
    ya_reembolsado = Devolucion.objects.filter(venta=devolucion.venta, monto_reembolso__isnull=False).exclude(
        pk=devolucion.pk
    ).aggregate(total=Sum('monto_reembolso'))['total'] or 0
    return pago.monto - ya_reembolsado


def _venta_anulada(venta):
    envio = getattr(venta, 'datos_envio', None)
    return venta.anulada or (envio is not None and envio.estado == 'Anulada')


def _fue_reembolsado(respuesta):
    tipo = (respuesta or {}).get('type')
    return tipo == 'REVERSED' or (tipo == 'NULLIFIED' and respuesta.get('response_code') == 0)


def _motivo_para_no_llamar(pago, monto, saldo):
    if monto <= 0:
        return "No queda saldo del pago por reembolsar en Webpay."
    if now() - (pago.fecha_transaccion or pago.venta.fecha) > PLAZO_ANULACION_WEBPAY:
        return "Pasaron más de 90 días desde la compra y Transbank ya no permite anularla."
    if monto < saldo and pago.tipo_pago in TIPOS_PAGO_SIN_ANULACION_PARCIAL:
        return "El pago fue en cuotas sin interés y Transbank no permite reembolsos parciales de esas compras."
    return None


def _preparar_solicitud(devolucion):
    pago = _pago_webpay(devolucion.venta, bloquear=True)
    if pago is None:
        return None
    saldo = _saldo(devolucion, pago)
    monto = max(min(_monto_productos(devolucion), saldo), 0)
    return _Solicitud(pago_id=pago.id, orden_compra=pago.orden_compra, token=pago.token, monto=monto, saldo=saldo,
                      motivo=_motivo_para_no_llamar(pago, monto, saldo))


def _pedir_reembolso(devolucion, solicitud):
    motivo, respuesta = solicitud.motivo, None
    if motivo is None:
        try:
            respuesta = webpay.reembolsar(solicitud.token, solicitud.monto)
        except webpay.ErrorWebpay as error:
            motivo = f"Transbank rechazó el reembolso: {error}"
        else:
            if not _fue_reembolsado(respuesta):
                motivo = f"Transbank no confirmó el reembolso (respuesta: {respuesta})."
    if motivo:
        logger.error("Reembolso pendiente, hacerlo a mano: devolución %s, orden %s, monto %s. %s",
                     devolucion.id, solicitud.orden_compra, solicitud.monto, motivo)
        return ResultadoReembolso(realizado=False, monto=solicitud.monto, motivo=motivo), None
    logger.info("Reembolso realizado en Webpay: devolución %s, orden %s, monto %s, respuesta %s",
                devolucion.id, solicitud.orden_compra, solicitud.monto, respuesta)
    return ResultadoReembolso(realizado=True, monto=solicitud.monto), respuesta


def _marcar_pago_si_quedo_en_cero(pago, monto, saldo, respuesta=None):
    if monto >= saldo or (respuesta or {}).get('balance') == 0:
        pago.estado = PagoWebpay.REEMBOLSADO
        pago.detalle = "Reembolsado por devolución."
        pago.save(update_fields=['estado', 'detalle', 'actualizado'])


def _guardar_reembolso(devolucion, solicitud, resultado, respuesta):
    fecha = now()
    try:
        with transaction.atomic():
            Devolucion.objects.filter(id=devolucion.id, monto_reembolso__isnull=True).update(
                monto_reembolso=solicitud.monto, fecha_reembolso=fecha)
            pago = PagoWebpay.objects.select_for_update().get(id=solicitud.pago_id)
            _marcar_pago_si_quedo_en_cero(pago, solicitud.monto, solicitud.saldo, respuesta)
    except Exception:
        logger.exception("Transbank reembolsó pero NO se guardó el reembolso: devolución %s, orden %s, monto %s. "
                         "Anotarlo con 'Registrar reembolso manual'.",
                         devolucion.id, solicitud.orden_compra, solicitud.monto)
        resultado.guardado = False
        return
    devolucion.monto_reembolso, devolucion.fecha_reembolso = solicitud.monto, fecha


def registrar_recepcion(devolucion_id):
    with transaction.atomic():
        devolucion = Devolucion.objects.select_for_update().get(id=devolucion_id)
        if devolucion.estado != 'Aprobada':
            raise OperacionNoPermitida("Solo se registra la recepción de una devolución aprobada.")
        if not _venta_anulada(devolucion.venta):
            Producto.todos.filter(id=devolucion.producto_id).update(stock=F('stock') + devolucion.cantidad)
        devolucion.estado = 'Recibida'
        devolucion.save(update_fields=['estado'])
        solicitud = _preparar_solicitud(devolucion)

    if solicitud is None:
        return devolucion, None
    resultado, respuesta = _pedir_reembolso(devolucion, solicitud)
    if resultado.realizado:
        _guardar_reembolso(devolucion, solicitud, resultado, respuesta)
    return devolucion, resultado


def registrar_reembolso_manual(devolucion_id, monto_texto):
    with transaction.atomic():
        devolucion = Devolucion.objects.select_for_update().get(id=devolucion_id)
        pago = _pago_webpay(devolucion.venta, bloquear=True)
        if devolucion.estado != 'Recibida' or pago is None or devolucion.monto_reembolso is not None:
            raise OperacionNoPermitida("Esta devolución no tiene un reembolso pendiente.")
        try:
            monto = int(monto_texto.strip().replace('.', '').replace('$', ''))
        except ValueError:
            raise ValueError("Ingresa el monto en pesos, solo con números.")
        saldo = _saldo(devolucion, pago)
        if monto < 1:
            raise ValueError("El monto debe ser mayor que cero.")
        if monto > saldo:
            raise ValueError(f"El monto no puede superar el saldo por reembolsar ({_pesos(saldo)}).")
        devolucion.monto_reembolso, devolucion.fecha_reembolso = monto, now()
        devolucion.save(update_fields=['monto_reembolso', 'fecha_reembolso'])
        _marcar_pago_si_quedo_en_cero(pago, monto, saldo)
    logger.info("Reembolso manual registrado: devolución %s, orden %s, monto %s",
                devolucion.id, pago.orden_compra, monto)
    return devolucion


def estado_reembolso(devolucion):
    if devolucion.monto_reembolso is not None:
        return REALIZADO
    if devolucion.estado == 'Recibida' and _pago_webpay(devolucion.venta) is not None:
        return PENDIENTE_MANUAL
    return None


def reembolso_pendiente(devolucion):
    if estado_reembolso(devolucion) != PENDIENTE_MANUAL:
        return None
    saldo = _saldo(devolucion, _pago_webpay(devolucion.venta))
    return {'monto': max(min(_monto_productos(devolucion), saldo), 0), 'saldo': saldo}
