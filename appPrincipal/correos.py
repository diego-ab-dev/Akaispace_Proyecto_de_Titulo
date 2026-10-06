"""Correos que envía la tienda.

- Confirmación de compra (HU-06): se envía al aprobarse el pago con Webpay (ver pagos.confirmar_pago).
- Recuperación de contraseña (HU-11): la envía Django (PasswordResetView); sus plantillas están en
  templates/correos/ y las URLs en Akaispace/urls.py.

La configuración del servidor de correo está en settings.py (EMAIL_*). Sin configurar, los correos
se muestran en la consola de runserver.
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
    """Envía un correo con versión HTML y de texto. Devuelve False si no se pudo enviar.

    Un error del servidor de correo nunca interrumpe lo que lo disparó (ej: un pago ya aprobado):
    se registra en el log para revisarlo.
    """
    texto = render_to_string(f'correos/{plantilla}.txt', contexto)
    html = render_to_string(f'correos/{plantilla}.html', contexto)
    mensaje = EmailMultiAlternatives(asunto, texto, to=[destinatario])
    mensaje.attach_alternative(html, 'text/html')
    try:
        mensaje.send()
    except Exception:  # SMTP caído, credenciales incorrectas, timeout, etc.
        logger.exception("No se pudo enviar el correo '%s' a %s", asunto, destinatario)
        return False
    return True


def enviar_confirmacion_compra(venta):
    """HU-06: detalle de la compra, condiciones y política de retracto al correo del cliente."""
    contexto = {
        'venta': venta,
        'items': venta.producto_venta.select_related('producto'),
        'pago': getattr(venta, 'pago_webpay', None),
        'opcion_envio': envios.OPCIONES_ENVIO.get(venta.metodo_envio),
        'url_boleta': settings.SITIO_URL + reverse('ver_boleta', args=[venta.id]),
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
