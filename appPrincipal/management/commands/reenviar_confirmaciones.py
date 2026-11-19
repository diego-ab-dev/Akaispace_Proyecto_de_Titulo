"""Comando: reenviar confirmaciones de compra."""
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils.timezone import now

from appPrincipal import correos
from appPrincipal.models import PagoWebpay, Venta

logger = logging.getLogger(__name__)


def confirmaciones_pendientes():
    ahora = now()
    return Venta.objects.filter(
        pago_webpay__estado=PagoWebpay.APROBADO, confirmacion_enviada=False,
        fecha__lt=ahora - timedelta(minutes=5), fecha__gt=ahora - timedelta(days=7),
    ).select_related('usuario', 'pago_webpay')


class Command(BaseCommand):
    help = 'Reenvía las confirmaciones de compra que no se pudieron enviar (tarea cada 15 minutos, HU-06).'

    def handle(self, *args, **options):
        enviadas = fallidas = 0
        for venta in confirmaciones_pendientes():
            if not Venta.objects.filter(pk=venta.pk, confirmacion_enviada=False).update(confirmacion_enviada=True):
                continue
            try:
                enviado = correos.enviar_confirmacion_compra(venta)
            except Exception:
                logger.exception("Error al reenviar la confirmación de la venta %s", venta.id)
                enviado = False
            if enviado:
                enviadas += 1
            else:
                Venta.objects.filter(pk=venta.pk).update(confirmacion_enviada=False)
                fallidas += 1
        if options['verbosity'] > 0:
            self.stdout.write(self.style.SUCCESS(
                f'Confirmaciones reenviadas: {enviadas}. Fallidas (se reintentan en la próxima ejecución): {fallidas}.'
            ))
