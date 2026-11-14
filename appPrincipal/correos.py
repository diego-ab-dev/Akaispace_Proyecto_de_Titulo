"""Correos que envía la tienda.

- Confirmación de compra: se envía al aprobarse el pago con Webpay. Si falla, la reenvía el comando
  reenviar_confirmaciones.
- Resolución de devolución: se envía cuando el administrador aprueba (con las instrucciones para entregar o enviar
  el producto) o rechaza una solicitud.
- Recepción de devolución: se envía cuando la tienda recibe el producto, e indica si el reembolso se hizo en Webpay
  o se gestionará a mano.
- Recuperación de contraseña: la envía Django (PasswordResetView).
- Bienvenida: una sola vez, al crear la cuenta (formulario o Google).
- Contraseña actualizada: aviso de seguridad al cambiarla desde el perfil o restablecerla con el enlace de
  recuperación, con un enlace para recuperar la cuenta si el cambio no lo hizo el cliente.

Todos son correos de la cuenta o de una compra (transaccionales), no publicidad. No se avisa cada inicio de
sesión: sería un correo en cada visita.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.timezone import localtime, now

from appPrincipal import envios
from appPrincipal.constants import CONDICIONES_COMPRA, POLITICA_RETRACTO, RESPONSABLE_DATOS
from appPrincipal.models import Venta

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


def _al_confirmar(funcion, *args):
    """Envía el correo cuando la cuenta o el cambio ya quedaron guardados (si algo se deshace, no se envía).
    Si el correo falla, _enviar lo deja en el log: el cliente nunca ve un error por esto."""
    transaction.on_commit(lambda: funcion(*args))


def _enviar_bienvenida(usuario, con_google):
    contexto = {
        'usuario': usuario,
        'con_google': con_google,
        'url_tienda': settings.SITIO_URL + reverse('home'),
        'url_perfil': settings.SITIO_URL + reverse('perfil'),
        'tienda': RESPONSABLE_DATOS,
    }
    enviado = _enviar("¡Bienvenido/a a Akaispace!", 'bienvenida', contexto, usuario.email)
    if enviado:
        logger.info("Correo de bienvenida enviado: usuario %s", usuario.pk)
    return enviado


def enviar_bienvenida(usuario, con_google=False):
    _al_confirmar(_enviar_bienvenida, usuario, con_google)


RESTABLECIDA = 'restablecida'
CAMBIADA = 'cambiada'


def _enviar_contraseña_actualizada(usuario, como):
    contexto = {
        'usuario': usuario,
        'restablecida': como == RESTABLECIDA,
        'fecha': localtime(now()),
        'url_recuperar': settings.SITIO_URL + reverse('recuperar_contraseña'),
        'tienda': RESPONSABLE_DATOS,
    }
    enviado = _enviar("Se actualizó la contraseña de tu cuenta - Akaispace", 'contraseña_actualizada',
                      contexto, usuario.email)
    if enviado:
        logger.info("Aviso de contraseña actualizada enviado: usuario %s", usuario.pk)
    return enviado


def enviar_contraseña_actualizada(usuario, como=CAMBIADA):
    """`como`: CAMBIADA (desde el perfil) o RESTABLECIDA (con el enlace de recuperación)."""
    _al_confirmar(_enviar_contraseña_actualizada, usuario, como)


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
        Venta.objects.filter(pk=venta.pk).update(confirmacion_enviada=True)
        venta.confirmacion_enviada = True
        logger.info("Correo de confirmación enviado: venta %s", venta.id)
    else:
        logger.error("Confirmación de compra pendiente: venta %s, cliente %s. La reenvía reenviar_confirmaciones.",
                     venta.id, venta.usuario.email)
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


def enviar_recepcion_devolucion(devolucion, reembolso=None):
    """`reembolso`: el ResultadoReembolso de Webpay, o None si la venta no se pagó con Webpay."""
    item = devolucion.venta.producto_venta.filter(producto=devolucion.producto).first()
    contexto = {
        'devolucion': devolucion,
        'webpay': reembolso is not None,
        'reembolsado': reembolso is not None and reembolso.realizado,
        'monto': reembolso.monto if reembolso is not None else (item.precio_unitario * devolucion.cantidad if item else 0),
        'fecha_reembolso': devolucion.fecha_reembolso or now(),
        'url_devolucion': settings.SITIO_URL + reverse('ver_detalle_devolucion', args=[devolucion.id]),
        'tienda': RESPONSABLE_DATOS,
    }
    enviado = _enviar(f"Recibimos el producto de tu devolución Nº {devolucion.id} - Akaispace",
                      'recepcion_devolucion', contexto, devolucion.usuario.email)
    if enviado:
        logger.info("Correo de recepción de devolución enviado: devolución %s", devolucion.id)
    return enviado
