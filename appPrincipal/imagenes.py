"""Optimización de imágenes."""
import io
import os

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image, ImageOps

LADO_MAXIMO = 1600
LADO_MAXIMO_PORTADA = 1920
PESO_SIN_TOCAR = 300 * 1024
CALIDAD_WEBP = 82


def necesita_optimizar(imagen, peso):
    if getattr(imagen, 'is_animated', False):
        return False
    return peso > PESO_SIN_TOCAR or max(imagen.size) > LADO_MAXIMO


def convertir_a_webp(imagen, lado_maximo=LADO_MAXIMO):
    imagen = ImageOps.exif_transpose(imagen)
    transparente = imagen.mode in ('RGBA', 'LA') or (imagen.mode == 'P' and 'transparency' in imagen.info)
    imagen = imagen.convert('RGBA' if transparente else 'RGB')
    imagen.thumbnail((lado_maximo, lado_maximo), Image.LANCZOS)
    salida = io.BytesIO()
    imagen.save(salida, 'WEBP', quality=CALIDAD_WEBP, method=6)
    return salida.getvalue()


def optimizar_subida(archivo, lado_maximo=LADO_MAXIMO):
    archivo.seek(0)
    with Image.open(archivo) as imagen:
        if not necesita_optimizar(imagen, archivo.size):
            archivo.seek(0)
            return archivo
        datos = convertir_a_webp(imagen, lado_maximo)
    if len(datos) >= archivo.size:
        archivo.seek(0)
        return archivo
    nombre = os.path.splitext(archivo.name)[0] + '.webp'
    return SimpleUploadedFile(nombre, datos, content_type='image/webp')
