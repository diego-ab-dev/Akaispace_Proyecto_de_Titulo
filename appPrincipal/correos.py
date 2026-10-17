"""Correos que envía la tienda.

- Confirmación de compra: se envía al aprobarse el pago con Webpay.
- Resolución de devolución: se envía cuando el administrador aprueba o rechaza una solicitud.
- Recuperación de contraseña: la envía Django (PasswordResetView).
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from appPrincipal import envios
from appPrincipal.constants import CONDICIONES_COMPRA, POLITICA_RETRACTO, RESPONSABLE_DATOS

logger = logging.getLogger(__name__)


def _enviar(asunto, plantilla, contexto, destinatario):
    texto = render_to_string(f'correos/{plantilla}.txt', contexto)
    html = render_to_string(f'correos/{plantilla}.html', contexto)
    mensaje = EmailMultiAlternatives(asunto, texto, to=[destinatario])
    mensaje.attach_alternative(html, 'text/html')
    try:
        mensaje.send()
    except Exception:
        logger.exception("No se pudo enviar el correo '%s' a %s", asunto, destinatario)
        return False
    return True


def enviar_confirmacion_compra(venta):
    contexto = {
        'venta': venta,
        'items': venta.producto_venta.select_related('producto'),
        'pago': getattr(venta, 'pago_webpay', None),
        'opcion_envio': envios.OPCIONES_ENVIO.get(venta.metodo_envio),
        'url_comprobante': settings.SITIO_URL + reverse('ver_comprobante', args=[venta.id]),
        'url_compra': settings.SITIO_URL + reverse('ver_detalle', args=[venta.id]),
        'condiciones': CONDICIONES_COMPRA,
        'retracto': POLITICA_RETRACTO,
        'tienda': RESPONSABLE_DATOS,
    }
    enviado = _enviar(f"Confirmación de tu compra Nº {venta.id} - Akaispace", 'confirmacion_compra',
                      contexto, venta.usuario.email)
    if enviado:
        logger.info("Correo de confirmación enviado: venta %s", venta.id)
    return enviado


def enviar_resolucion_devolucion(devolucion):
    item = devolucion.venta.producto_venta.filter(producto=devolucion.producto).first()
    contexto = {
        'devolucion': devolucion,
        'aprobada': devolucion.estado == 'Aprobada',
        'monto_reembolso': item.precio_unitario * devolucion.cantidad if item else 0,
        'url_devolucion': settings.SITIO_URL + reverse('ver_detalle_devolucion', args=[devolucion.id]),
        'tienda': RESPONSABLE_DATOS,
    }
    resultado = 'aprobada' if contexto['aprobada'] else 'rechazada'
    enviado = _enviar(f"Tu solicitud de devolución Nº {devolucion.id} fue {resultado} - Akaispace",
                      'resolucion_devolucion', contexto, devolucion.usuario.email)
    if enviado:
        logger.info("Correo de resolución de devolución enviado: devolución %s", devolucion.id)
    return enviado
