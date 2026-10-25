"""Tarea diaria de las recomendaciones (HU-07): borra la navegación con más de 24 meses (plazo de la política de
privacidad) y recalcula las similitudes, para que el desempate por unidades vendidas use las ventas del día.
Se programa una vez al día (por ejemplo, con cron en el servidor)."""
from django.core.management.base import BaseCommand

from appPrincipal.recomendaciones import calcular_similitudes, eliminar_navegacion_antigua


class Command(BaseCommand):
    help = 'Borra la navegación con más de 24 meses y recalcula las similitudes (tarea diaria, HU-07).'

    def handle(self, *args, **options):
        interacciones, recomendaciones = eliminar_navegacion_antigua()
        similitudes = calcular_similitudes()
        if options['verbosity'] > 0:
            self.stdout.write(self.style.SUCCESS(
                f'Navegación antigua eliminada: {interacciones} interacciones y {recomendaciones} recomendaciones. '
                f'Similitudes recalculadas: {similitudes} pares.'
            ))
