"""Optimización de las fotos que se suben (productos, devoluciones y portada).

Una foto de celular mide ~4000 px y pesa varios MB, pero en el sitio se muestra a unos cientos de píxeles.
Las fotos pesadas o muy grandes se achican y se guardan en WebP, que a la vista no se distingue y pesa
mucho menos. Las que ya son livianas se dejan tal cual, y los GIF animados también (se perdería la animación).
Al pasar por aquí la foto queda derecha (orientación EXIF de la cámara) y sin metadatos, como la ubicación GPS.
"""
import io
import os

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image, ImageOps

LADO_MAXIMO = 1600          # productos y devoluciones
LADO_MAXIMO_PORTADA = 1920  # carrusel de la portada, que va a todo el ancho
PESO_SIN_TOCAR = 300 * 1024
CALIDAD_WEBP = 82


def necesita_optimizar(imagen, peso):
    """True si la foto pesa más de 300 KB o mide más que el lado máximo. Los GIF animados nunca."""
    if getattr(imagen, 'is_animated', False):
        return False
    return peso > PESO_SIN_TOCAR or max(imagen.size) > LADO_MAXIMO


def convertir_a_webp(imagen, lado_maximo=LADO_MAXIMO):
    """Bytes de la foto en WebP, con su lado mayor de a lo más `lado_maximo` px. Conserva la transparencia."""
    imagen = ImageOps.exif_transpose(imagen)
    transparente = imagen.mode in ('RGBA', 'LA') or (imagen.mode == 'P' and 'transparency' in imagen.info)
    imagen = imagen.convert('RGBA' if transparente else 'RGB')
    imagen.thumbnail((lado_maximo, lado_maximo), Image.LANCZOS)
    salida = io.BytesIO()
    imagen.save(salida, 'WEBP', quality=CALIDAD_WEBP, method=6)
    return salida.getvalue()


def optimizar_subida(archivo, lado_maximo=LADO_MAXIMO):
    """Recibe una foto recién subida y ya validada. Devuelve la misma si no vale la pena tocarla,
    o una nueva en WebP (mismo nombre, extensión .webp)."""
    archivo.seek(0)
    with Image.open(archivo) as imagen:
        if not necesita_optimizar(imagen, archivo.size):
            archivo.seek(0)
            return archivo
        datos = convertir_a_webp(imagen, lado_maximo)
    if len(datos) >= archivo.size:  # raro, pero si no achica, se queda la original
        archivo.seek(0)
        return archivo
    nombre = os.path.splitext(archivo.name)[0] + '.webp'
    return SimpleUploadedFile(nombre, datos, content_type='image/webp')
