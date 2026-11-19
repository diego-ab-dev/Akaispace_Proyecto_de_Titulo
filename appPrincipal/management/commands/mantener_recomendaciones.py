"""Comando: mantención diaria de recomendaciones."""
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
