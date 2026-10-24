"""Recalcula las similitudes entre productos (HU-07). Se ejecuta solo al modificar el catálogo; este comando
sirve para la carga inicial o para forzarlo a mano."""
from django.core.management.base import BaseCommand

from appPrincipal.recomendaciones import calcular_similitudes


class Command(BaseCommand):
    help = 'Recalcula los 10 productos más similares a cada producto (TF-IDF y similitud del coseno, HU-07).'

    def handle(self, *args, **options):
        filas = calcular_similitudes()
        if options['verbosity'] > 0:
            self.stdout.write(self.style.SUCCESS(f'Similitudes calculadas: {filas} pares guardados.'))
