"""Comando: optimizar imágenes subidas."""
import os

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image, UnidentifiedImageError

from appPrincipal.imagenes import LADO_MAXIMO, LADO_MAXIMO_PORTADA, convertir_a_webp, necesita_optimizar
from appPrincipal.models import Destacado, ImagenDevolucion, ImagenProducto

CAMPOS = [(ImagenProducto, LADO_MAXIMO), (ImagenDevolucion, LADO_MAXIMO), (Destacado, LADO_MAXIMO_PORTADA)]


def kb(bytes_):
    return f'{bytes_ / 1024:,.0f} KB'.replace(',', '.')


class Command(BaseCommand):
    help = 'Pasa a WebP las fotos subidas que son pesadas o muy grandes (productos, devoluciones y portada).'

    def add_arguments(self, parser):
        parser.add_argument('--probar', action='store_true', help='Solo muestra lo que haría, sin cambiar nada.')
        parser.add_argument('--borrar-originales', action='store_true',
                            help='Borra de media/ los archivos originales después de convertirlos.')

    def handle(self, *args, probar=False, borrar_originales=False, **options):
        rutas = {}
        for modelo, lado in CAMPOS:
            for ruta in modelo.objects.exclude(imagen='').exclude(imagen__isnull=True).values_list('imagen', flat=True):
                rutas[ruta] = max(lado, rutas.get(ruta, 0))

        convertidas, antes, despues = 0, 0, 0
        for ruta, lado in sorted(rutas.items()):
            if not default_storage.exists(ruta):
                self.stdout.write(self.style.WARNING(f'No existe el archivo: {ruta}'))
                continue
            peso = default_storage.size(ruta)
            try:
                with default_storage.open(ruta, 'rb') as archivo, Image.open(archivo) as imagen:
                    if not necesita_optimizar(imagen, peso):
                        continue
                    datos = convertir_a_webp(imagen, lado)
            except (UnidentifiedImageError, OSError) as error:
                self.stdout.write(self.style.WARNING(f'No se pudo leer {ruta}: {error}'))
                continue
            if len(datos) >= peso:
                continue

            convertidas += 1
            antes += peso
            despues += len(datos)
            self.stdout.write(f'{ruta}: {kb(peso)} -> {kb(len(datos))}')
            if probar:
                continue
            nueva = default_storage.save(os.path.splitext(ruta)[0] + '.webp', ContentFile(datos))
            with transaction.atomic():
                for modelo, _ in CAMPOS:
                    modelo.objects.filter(imagen=ruta).update(imagen=nueva)
            if borrar_originales:
                default_storage.delete(ruta)

        resumen = f'{convertidas} foto(s): {kb(antes)} -> {kb(despues)}'
        if probar:
            self.stdout.write(self.style.SUCCESS(f'Prueba, sin cambios. Se optimizarían {resumen}.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Optimizadas {resumen}.'))
