"""Eliminación de la cuenta (derecho de supresión, Ley 21.719 y política de privacidad).

El cliente la elimina desde su perfil, de inmediato y sin que intervenga el administrador; el administrador
también puede eliminar una cuenta desde el panel. En ambos casos:

1. No se permite mientras haya algo en curso que necesite contactar al cliente (motivos_para_no_eliminar):
   una compra web pagada sin entregar, un pago Webpay recién iniciado, una devolución sin terminar
   (incluido un reembolso pendiente) o un reclamo sin responder.
2. Se borra lo que solo sirve al cliente: historial de navegación y recomendaciones (HU-07), opiniones,
   favoritos, el carrito vigente y sus vínculos de inicio de sesión (correos de allauth y la cuenta de Google).
3. Se conservan, sin datos personales, las ventas, pagos, devoluciones y reclamos: el negocio debe guardarlos
   por obligación tributaria y de protección al consumidor (la Ley 21.719 permite conservar datos por una
   obligación legal). Se vacía la dirección de entrega que guardan las ventas y los pagos, que ya no se
   necesita una vez entregada la compra.
4. Usuario.anonimizar() reemplaza nombre, correo, RUT, teléfono y dirección, desactiva la cuenta y cierra la
   sesión en todos los dispositivos.
5. Se avisa por correo a la dirección original, después de confirmar los cambios.

Todo ocurre en una sola transacción: o se aplica completo o no se aplica nada.
"""
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

# Un pago Webpay iniciado hace menos de esto puede estar en curso (el formulario de Transbank expira antes);
# los más antiguos que siguen "pendientes" son pagos abandonados y no bloquean la eliminación.
PAGO_EN_CURSO = timedelta(hours=1)
ENVIO_TERMINADO = ['Entregado', 'Anulada']


class CuentaNoEliminable(Exception):
    def __init__(self, motivos):
        self.motivos = motivos
        super().__init__(' '.join(motivos))


def motivos_para_no_eliminar(usuario):
    """Lista de mensajes para el cliente; vacía si la cuenta se puede eliminar."""
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
    """Elimina y anonimiza la cuenta. Lanza CuentaNoEliminable si hay algo en curso."""
    with transaction.atomic():
        # bloquea la fila: dos solicitudes simultáneas (o una compra que termina justo ahora) no se cruzan
        usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
        if usuario.is_deleted:
            return usuario
        motivos = motivos_para_no_eliminar(usuario)
        if motivos:
            raise CuentaNoEliminable(motivos)

        nombre, email = usuario.nombre, usuario.email

        cambiar_consentimiento_navegacion(usuario, autoriza=False)  # borra navegación y recomendaciones
        Opinion.objects.filter(usuario=usuario).delete()
        Favorito.objects.filter(usuario=usuario).delete()
        Carrito.objects.filter(usuario=usuario).delete()  # solo el vigente; los pagados quedan para KPI-04
        Venta.objects.filter(usuario=usuario).update(direccion_envio=None)
        PagoWebpay.objects.filter(usuario=usuario).update(direccion_envio='')

        EmailAddress.objects.filter(user=usuario).delete()
        SocialAccount.objects.filter(user=usuario).delete()  # sus tokens se borran en cascada

        usuario.anonimizar()

        # intentos de inicio de sesión (django-axes): se borran los vigentes y el registro de seguridad
        # queda con el correo anónimo
        AccessAttempt.objects.filter(username=email).delete()
        AccessLog.objects.filter(username=email).update(username=usuario.email)
        AccessFailureLog.objects.filter(username=email).update(username=usuario.email)

        correos.enviar_cuenta_eliminada(nombre, email, por_administrador)

    logger.info("Cuenta eliminada y anonimizada: usuario %s (por_administrador=%s)", usuario.pk, por_administrador)
    return usuario
