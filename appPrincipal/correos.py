"""Correos que envía la tienda.

- Confirmación de compra: se envía al aprobarse el pago con Webpay. Si falla, la reenvía el comando
  reenviar_confirmaciones.
- Pedido listo para retiro: se envía la primera vez que el administrador marca un retiro en tienda como
  "Listo para retiro", con la dirección y el horario de la tienda.
- Pedido enviado: la primera vez que una encomienda pasa a "Enviado", con el transportista y el número de
  seguimiento (el panel lo exige para ese estado). Los demás estados de la encomienda no se avisan: el
  transportista ya informa el seguimiento.
- Pedido en reparto: la primera vez que un Delivery Express en Valdivia pasa a "En Reparto", con la dirección de
  entrega.
- Resolución de devolución: se envía cuando el administrador aprueba (con las instrucciones para entregar o enviar
  el producto) o rechaza una solicitud.
- Recepción de devolución: se envía cuando la tienda recibe el producto, e indica si el reembolso se hizo en Webpay
  o se gestionará a mano.
- Recuperación de contraseña: la envía Django (PasswordResetView).
- Bienvenida: una sola vez, al crear la cuenta (formulario o Google).
- Contraseña actualizada: aviso de seguridad al cambiarla desde el perfil o restablecerla con el enlace de
  recuperación, con un enlace para recuperar la cuenta si el cambio no lo hizo el cliente.
- Cuenta eliminada: confirma la eliminación y anonimización de la cuenta, y qué datos se conservan por ley.

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


def responder_a():
    """'Responder a' de todos los correos: CONTACT_EMAIL si está definido. El remitente (DEFAULT_FROM_EMAIL)
    es una dirección sin buzón del dominio verificado en SES."""
    return [settings.CONTACT_EMAIL] if settings.CONTACT_EMAIL else None


def _enviar(asunto, plantilla, contexto, destinatario):
    texto = render_to_string(f'correos/{plantilla}.txt', contexto)
    html = render_to_string(f'correos/{plantilla}.html', contexto)
    mensaje = EmailMultiAlternatives(asunto, texto, to=[destinatario], reply_to=responder_a())
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
    enviado = _enviar("¡Bienvenido/a a Akai Space!", 'bienvenida', contexto, usuario.email)
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
    enviado = _enviar("Se actualizó la contraseña de tu cuenta - Akai Space", 'contraseña_actualizada',
                      contexto, usuario.email)
    if enviado:
        logger.info("Aviso de contraseña actualizada enviado: usuario %s", usuario.pk)
    return enviado


def enviar_contraseña_actualizada(usuario, como=CAMBIADA):
    """`como`: CAMBIADA (desde el perfil) o RESTABLECIDA (con el enlace de recuperación)."""
    _al_confirmar(_enviar_contraseña_actualizada, usuario, como)


def _enviar_cuenta_eliminada(nombre, email, por_administrador):
    contexto = {
        'nombre': nombre,
        'email': email,
        'por_administrador': por_administrador,
        'fecha': localtime(now()),
        'url_privacidad': settings.SITIO_URL + reverse('politica_privacidad') + '#conservacion',
        'tienda': RESPONSABLE_DATOS,
    }
    enviado = _enviar("Tu cuenta fue eliminada - Akai Space", 'cuenta_eliminada', contexto, email)
    if enviado:
        logger.info("Aviso de cuenta eliminada enviado")  # sin el correo: la cuenta ya está anonimizada
    return enviado


def enviar_cuenta_eliminada(nombre, email, por_administrador=False):
    """Recibe el nombre y el correo originales: al enviarse, la cuenta ya está anonimizada."""
    _al_confirmar(_enviar_cuenta_eliminada, nombre, email, por_administrador)


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
    enviado = _enviar(f"Confirmación de tu compra Nº {venta.id} - Akai Space", 'confirmacion_compra',
                      contexto, venta.usuario.email)
    if enviado:
        Venta.objects.filter(pk=venta.pk).update(confirmacion_enviada=True)
        venta.confirmacion_enviada = True
        logger.info("Correo de confirmación enviado: venta %s", venta.id)
    else:
        logger.error("Confirmación de compra pendiente: venta %s, cliente %s. La reenvía reenviar_confirmaciones.",
                     venta.id, venta.usuario.email)
    return enviado


def _enviar_listo_para_retiro(venta):
    contexto = {
        'venta': venta,
        'items': venta.producto_venta.select_related('producto'),
        'direccion': envios.DIRECCION_TIENDA,
        'horario': envios.HORARIO_TIENDA,
        'url_compra': settings.SITIO_URL + reverse('ver_detalle', args=[venta.id]),
        'tienda': RESPONSABLE_DATOS,
    }
    enviado = _enviar(f"Tu pedido Nº {venta.id} está listo para retiro - Akai Space", 'listo_para_retiro',
                      contexto, venta.usuario.email)
    if enviado:
        logger.info("Aviso de pedido listo para retiro enviado: venta %s", venta.id)
    return enviado


def enviar_listo_para_retiro(venta):
    _al_confirmar(_enviar_listo_para_retiro, venta)


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
    enviado = _enviar(f"Tu solicitud de devolución Nº {devolucion.id} fue {resultado} - Akai Space",
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
    enviado = _enviar(f"Recibimos el producto de tu devolución Nº {devolucion.id} - Akai Space",
                      'recepcion_devolucion', contexto, devolucion.usuario.email)
    if enviado:
        logger.info("Correo de recepción de devolución enviado: devolución %s", devolucion.id)
    return enviado


def _enviar_pedido_enviado(venta, envio):
    contexto = {
        'venta': venta,
        'envio': envio,
        'items': venta.producto_venta.select_related('producto'),
        'url_compra': settings.SITIO_URL + reverse('ver_detalle', args=[venta.id]),
        'tienda': RESPONSABLE_DATOS,
    }
    enviado = _enviar(f"Tu pedido Nº {venta.id} fue enviado - Akai Space", 'pedido_enviado',
                      contexto, venta.usuario.email)
    if enviado:
        logger.info("Aviso de pedido enviado: venta %s", venta.id)
    return enviado


def _enviar_pedido_en_reparto(venta):
    contexto = {
        'venta': venta,
        'items': venta.producto_venta.select_related('producto'),
        'url_compra': settings.SITIO_URL + reverse('ver_detalle', args=[venta.id]),
        'tienda': RESPONSABLE_DATOS,
    }
    enviado = _enviar(f"Tu pedido Nº {venta.id} va en camino - Akai Space", 'pedido_en_reparto',
                      contexto, venta.usuario.email)
    if enviado:
        logger.info("Aviso de pedido en reparto enviado: venta %s", venta.id)
    return enviado


def avisar_estado_envio(venta, envio, estado):
    """Avisa al cliente los estados que le sirven saber. La vista lo llama solo la primera vez que el pedido
    llega a cada estado, para no repetir el correo si el administrador corrige el estado."""
    if estado == 'Listo para retiro':
        enviar_listo_para_retiro(venta)
    elif estado == 'Enviado':
        _al_confirmar(_enviar_pedido_enviado, venta, envio)
    elif estado == 'En Reparto' and venta.metodo_envio == 'delivery':
        _al_confirmar(_enviar_pedido_en_reparto, venta)
