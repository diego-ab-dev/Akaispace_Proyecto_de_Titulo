"""Conexión con Webpay Plus de Transbank (HU-05).

Envuelve el SDK oficial (transbank-sdk) para que el resto del proyecto no dependa de él:
cualquier falla, ya sea de Transbank o de red, sale como ErrorWebpay.
El ambiente y las credenciales se configuran en settings (WEBPAY_*, ver .env.example).
"""
import logging

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from transbank.common.integration_api_keys import IntegrationApiKeys
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_type import IntegrationType
from transbank.common.options import WebpayOptions
from transbank.error.transbank_error import TransbankError
from transbank.webpay.webpay_plus.transaction import Transaction

logger = logging.getLogger(__name__)


class ErrorWebpay(Exception):
    """Transbank respondió con error o no se pudo conectar."""


def es_integracion():
    return settings.WEBPAY_AMBIENTE != 'produccion'


def _transaccion():
    if es_integracion():
        opciones = WebpayOptions(IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY,
                                 IntegrationType.TEST, timeout=settings.WEBPAY_TIMEOUT)
    else:
        if not (settings.WEBPAY_CODIGO_COMERCIO and settings.WEBPAY_API_KEY):
            raise ImproperlyConfigured(
                "WEBPAY_AMBIENTE=produccion requiere WEBPAY_CODIGO_COMERCIO y WEBPAY_API_KEY."
            )
        opciones = WebpayOptions(settings.WEBPAY_CODIGO_COMERCIO, settings.WEBPAY_API_KEY,
                                 IntegrationType.LIVE, timeout=settings.WEBPAY_TIMEOUT)
    return Transaction(opciones)


def _llamar(accion, *args):
    try:
        return getattr(_transaccion(), accion)(*args)
    except (TransbankError, requests.RequestException) as error:
        detalle = getattr(error, 'message', None) or str(error)
        logger.warning("Webpay %s falló: %s", accion, detalle)
        raise ErrorWebpay(detalle) from error


def crear(orden_compra, id_sesion, monto, url_retorno):
    """Inicia la transacción. Devuelve {'token': ..., 'url': ...} para enviar al cliente a Webpay."""
    return _llamar('create', orden_compra, id_sesion, monto, url_retorno)


def confirmar(token):
    """Confirma (commit) la transacción cuando el cliente vuelve de Webpay.

    Si el commit falla, por ejemplo porque se cortó la conexión justo después de que
    Transbank lo procesara, se consulta el estado para no perder un pago que sí se hizo.
    """
    try:
        return _llamar('commit', token)
    except ErrorWebpay:
        estado = _llamar('status', token)
        if estado.get('status') == 'AUTHORIZED':
            return estado
        raise


def reembolsar(token, monto):
    """Reversa o anula el cargo completo (se usa si se agotó el stock mientras el cliente pagaba)."""
    return _llamar('refund', token, monto)


def fue_aprobado(respuesta):
    return respuesta.get('status') == 'AUTHORIZED' and respuesta.get('response_code') == 0
