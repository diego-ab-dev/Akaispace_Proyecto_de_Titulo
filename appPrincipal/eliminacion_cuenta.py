"""Eliminación de la cuenta."""
import logging
from datetime import timedelta

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from axes.models import AccessAttempt, AccessFailureLog, AccessLog
from django.db import transaction
from django.utils.timezone import now

from appPrincipal import correos
from appPrincipal.models import (Carrito, Devolucion, Favorito, Opinion, PagoWebpay, Reclamo, Usuario, Venta)
from appPrincipal.recomendaciones import cambiar_consentimiento_navegacion

logger = logging.getLogger(__name__)

PAGO_EN_CURSO = timedelta(hours=1)
ENVIO_TERMINADO = ['Entregado', 'Anulada']


class CuentaNoEliminable(Exception):
    def __init__(self, motivos):
        self.motivos = motivos
        super().__init__(' '.join(motivos))


def motivos_para_no_eliminar(usuario):
    if usuario.is_staff:
        return ['Las cuentas de administrador no se eliminan desde aquí.']

    motivos = []
    compras_sin_entregar = (Venta.objects.filter(usuario=usuario, canal=Venta.CANAL_WEB, anulada_en__isnull=True)
                            .exclude(datos_envio__estado__in=ENVIO_TERMINADO))
    if compras_sin_entregar.exists():
        motivos.append('Tienes una compra que aún no se entrega o retira.')
    if PagoWebpay.objects.filter(usuario=usuario, estado=PagoWebpay.PENDIENTE,
                                 creado__gte=now() - PAGO_EN_CURSO).exists():
        motivos.append('Tienes un pago con Webpay en curso.')
    devoluciones = Devolucion.objects.filter(usuario=usuario)
    if (devoluciones.filter(estado__in=['Pendiente', 'Aprobada']).exists()
            or devoluciones.filter(estado='Recibida', monto_reembolso__isnull=True,
                                   venta__pago_webpay__isnull=False).exists()):
        motivos.append('Tienes una devolución o un reembolso en curso.')
    if Reclamo.objects.filter(usuario=usuario, estado='Abierto').exists():
        motivos.append('Tienes un reclamo que aún no se responde.')
    return motivos


def eliminar_cuenta(usuario, por_administrador=False):
    with transaction.atomic():
        usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
        if usuario.is_deleted:
            return usuario
        motivos = motivos_para_no_eliminar(usuario)
        if motivos:
            raise CuentaNoEliminable(motivos)

        nombre, email = usuario.nombre, usuario.email

        cambiar_consentimiento_navegacion(usuario, autoriza=False)
        Opinion.objects.filter(usuario=usuario).delete()
        Favorito.objects.filter(usuario=usuario).delete()
        Carrito.objects.filter(usuario=usuario).delete()
        Venta.objects.filter(usuario=usuario).update(direccion_envio=None)
        PagoWebpay.objects.filter(usuario=usuario).update(direccion_envio='')

        EmailAddress.objects.filter(user=usuario).delete()
        SocialAccount.objects.filter(user=usuario).delete()

        usuario.anonimizar()

        AccessAttempt.objects.filter(username=email).delete()
        AccessLog.objects.filter(username=email).update(username=usuario.email)
        AccessFailureLog.objects.filter(username=email).update(username=usuario.email)

        correos.enviar_cuenta_eliminada(nombre, email, por_administrador)

    logger.info("Cuenta eliminada y anonimizada: usuario %s (por_administrador=%s)", usuario.pk, por_administrador)
    return usuario
