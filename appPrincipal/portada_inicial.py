"""Contenido inicial de la portada
"""
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage

CONTENIDO_INICIAL = [
    {
        'seccion': 'carrusel', 'orden': 1, 'titulo': 'Call of Duty: Black Ops 6',
        'texto': 'Prepárate para la adrenalina de Call of Duty: Black Ops 6. Vive una experiencia de combate '
                 'que no querrás dejar. ¡Consíguelo ahora!',
        'imagen_static': 'cod6.png', 'producto': 'Call of Duty: Black Ops 6',
    },
    {
        'seccion': 'carrusel', 'orden': 2, 'titulo': 'FC25',
        'texto': '¡Vive la emoción del fútbol como nunca antes con FC25! Llévate el juego que todos quieren '
                 'y domina la cancha desde casa.',
        'imagen_static': 'fc25.png', 'producto': 'Fc 25',
    },
    {
        'seccion': 'carrusel', 'orden': 3, 'titulo': 'Silent Hill 2',
        'texto': 'Sumérgete en el terror psicológico de Silent Hill 2. Atrévete a enfrentar tus miedos y '
                 'descubre los oscuros secretos que te esperan.',
        'imagen_static': 'silent.png', 'producto': 'Silent Hill 2',
    },
    {
        'seccion': 'lanzamientos', 'orden': 1, 'titulo': 'Battlefield 6',
        'texto': 'Battlefield 6 es un videojuego de disparos en primera persona de 2025 desarrollado por '
                 'Battlefield Studios y publicado por Electronic Arts. Siendo la decimoctava entrega de la '
                 'serie Battlefield, el juego se lanzó para PlayStation 5, Windows y Xbox Series X/S el 10 de '
                 'octubre de 2025.',
        'video_url': 'https://www.youtube.com/watch?v=wFGEMfyAQtI',
    },
    {
        'seccion': 'lanzamientos', 'orden': 2, 'titulo': 'EA Sports FC 26',
        'texto': 'EA Sports FC 26 es un videojuego de fútbol desarrollado por EA Vancouver y EA Romania y '
                 'publicado por Electronic Arts. Su lanzamiento mundial fue el 26 de septiembre de 2025 para '
                 'Microsoft Windows, PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch, '
                 'Nintendo Switch 2 y Amazon Luna.',
        'video_url': 'https://www.youtube.com/watch?v=TSi0iJYSQ24',
    },
    {
        'seccion': 'menu_videojuegos', 'orden': 1, 'titulo': 'Call of Duty: Black Ops 6', 'etiqueta': '¡NUEVO!',
        'imagen_static': 'cod6.png', 'producto': 'Call of Duty: Black Ops 6',
    },
    {
        'seccion': 'menu_consolas', 'orden': 1, 'titulo': 'Play Station 5', 'etiqueta': '¡TOP VENTAS!',
        'producto': 'Play Station 5',
    },
    {
        'seccion': 'menu_accesorios', 'orden': 1, 'titulo': 'DualSense Chroma Pearl', 'etiqueta': 'EXCLUSIVO',
        'producto': 'Control Sony Dualsense Chroma Pearl Ps5',
    },
    {
        'seccion': 'menu_figuras', 'orden': 1, 'titulo': 'Funko Pop John Wick', 'etiqueta': 'COLECCIÓN',
        'producto': 'Funko Pop John Wick',
    },
]


def _copiar_imagen_static(nombre):
    destino = f'destacados/{nombre}'
    if not default_storage.exists(destino):
        origen = Path(settings.BASE_DIR) / 'static' / 'images' / nombre
        with open(origen, 'rb') as archivo:
            destino = default_storage.save(destino, File(archivo))
    return destino


def cargar(Destacado, Producto):
    if not Destacado.objects.exists():
        for datos in CONTENIDO_INICIAL:
            imagen = _copiar_imagen_static(datos['imagen_static']) if datos.get('imagen_static') else None
            Destacado.objects.create(
                seccion=datos['seccion'], orden=datos['orden'], titulo=datos['titulo'],
                texto=datos.get('texto', ''), etiqueta=datos.get('etiqueta', ''),
                video_url=datos.get('video_url', ''), imagen=imagen,
            )

    for datos in CONTENIDO_INICIAL:
        if not datos.get('producto'):
            continue
        producto = Producto.objects.filter(nombre=datos['producto']).first()
        if producto:
            Destacado.objects.filter(
                seccion=datos['seccion'], titulo=datos['titulo'], producto__isnull=True
            ).update(producto=producto)
