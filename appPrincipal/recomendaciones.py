"""Recomendaciones de productos con filtrado basado en contenido (HU-07).

Cada producto se representa como un documento de etiquetas ("cat_videojuegos plat_ps5 fam_playstation
gen_rpg") y se compara con TF-IDF y similitud del coseno. El prototipo y la justificación de cada decisión
están en notebooks/hu07_similitud_productos.ipynb.

- calcular_similitudes(): guarda en SimilitudProducto los 10 productos más similares a cada producto.
- recomendar(): elige qué mostrar según el consentimiento y el historial del cliente (arranque en frío):
  personalizadas si autorizó sus datos de navegación y tiene historial; si no, los similares al producto
  de la ficha, o los más vendidos en la página principal.

Los empates (muy frecuentes, porque hay pocos atributos) se resuelven por unidades vendidas y después
por id, para que el resultado sea siempre el mismo.

Las similitudes se recalculan solas cuando se crea o elimina un producto o cambia su categoría, plataforma
o género (señales al final de este archivo). Un cambio de precio o de stock no las afecta.
"""
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field

import numpy as np
from django.db import transaction
from django.db.models import Sum
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils.text import slugify
from django.utils.timezone import now
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from appPrincipal.models import Carrito, InteraccionProducto, Producto, ProductoVenta, SimilitudProducto

TOP_SIMILARES = 10
CANTIDAD_RECOMENDACIONES = 4
# peso de cada interacción en el perfil del cliente
PESOS = {InteraccionProducto.VISTA: 1, InteraccionProducto.CARRITO: 2}
PESO_COMPRA = 3

PERSONALIZADAS = 'personalizadas'
SIMILARES = 'similares'
MAS_VENDIDOS = 'mas_vendidos'


@dataclass
class Recomendaciones:
    tipo: str = MAS_VENDIDOS
    productos: list = field(default_factory=list)


def etiqueta(prefijo, valor):
    return f"{prefijo}_{slugify(valor).replace('-', '_')}"


def documento(producto):
    """Ej.: "cat_videojuegos plat_ps5 fam_playstation gen_rpg". Los atributos vacíos no generan etiqueta."""
    etiquetas = [etiqueta('cat', producto.categoria.nombre)]
    if producto.plataforma_id:
        etiquetas += [etiqueta('plat', producto.plataforma.codigo), etiqueta('fam', producto.plataforma.familia)]
    if producto.genero_id:
        etiquetas.append(etiqueta('gen', producto.genero.nombre))
    return ' '.join(etiquetas)


def _catalogo():
    """Productos vigentes (sin los eliminados) y su matriz TF-IDF, en el mismo orden."""
    productos = list(Producto.objects.select_related('categoria', 'plataforma', 'genero').order_by('id'))
    if not productos:
        return productos, None
    # cada palabra es una etiqueta; tf siempre vale 1, así que el peso lo pone el IDF
    vectorizador = TfidfVectorizer(token_pattern=r'\S+', lowercase=False)
    return productos, vectorizador.fit_transform([documento(producto) for producto in productos])


def unidades_vendidas():
    """{producto_id: unidades vendidas} en las ventas no anuladas, de todos los canales."""
    return dict(
        ProductoVenta.objects.filter(venta__anulada_en__isnull=True)
        .values('producto').annotate(unidades=Sum('cantidad')).values_list('producto', 'unidades')
    )


def _ordenar(puntajes, productos, vendidos):
    """Índices con puntaje > 0, del mayor al menor puntaje; los empates, por unidades vendidas y luego id.
    El puntaje se redondea a 4 decimales (los que guarda SimilitudProducto) para que un empate lo sea."""
    indices = [i for i in range(len(productos)) if round(puntajes[i], 4) > 0]
    return sorted(indices, key=lambda i: (-round(puntajes[i], 4), -vendidos.get(productos[i].id, 0),
                                          productos[i].id))


def calcular_similitudes():
    """Recalcula el top 10 de similares de todo el catálogo y reemplaza el cálculo anterior.
    Los pares sin ninguna etiqueta en común (puntaje 0) no se guardan. Devuelve cuántas filas guardó."""
    productos, matriz = _catalogo()
    filas = []
    if len(productos) > 1:
        similitud = cosine_similarity(matriz)
        np.fill_diagonal(similitud, 0)  # un producto no es similar a sí mismo
        vendidos = unidades_vendidas()
        fecha = now()
        for i, producto in enumerate(productos):
            for j in _ordenar(similitud[i], productos, vendidos)[:TOP_SIMILARES]:
                filas.append(SimilitudProducto(
                    producto=producto, producto_similar=productos[j],
                    puntaje=f'{min(similitud[i, j], 1):.4f}', fecha_calculo=fecha,
                ))
    with transaction.atomic():
        SimilitudProducto.objects.all().delete()
        SimilitudProducto.objects.bulk_create(filas)
    return len(filas)


def autorizo_datos_navegacion(usuario):
    return usuario.is_authenticated and usuario.datos_navegacion_autorizados_en is not None


def _historial(usuario):
    """{producto_id: peso} con las vistas, lo agregado al carrito y lo comprado, y el conjunto de comprados."""
    pesos = {}
    for producto_id, tipo in usuario.interacciones.values_list('producto_id', 'tipo'):
        pesos[producto_id] = pesos.get(producto_id, 0) + PESOS[tipo]
    comprados = set(
        ProductoVenta.objects.filter(venta__usuario=usuario, venta__anulada_en__isnull=True)
        .values_list('producto_id', flat=True)
    )
    for producto_id in comprados:
        pesos[producto_id] = pesos.get(producto_id, 0) + PESO_COMPRA
    return pesos, comprados


def _en_carrito(usuario):
    carrito = Carrito.objects.filter(usuario=usuario).first()
    return set(carrito.items.values_list('producto_id', flat=True)) if carrito else set()


def _personalizadas(usuario, excluidos, vendidos, cantidad):
    """Promedio ponderado de los vectores de los productos del historial, comparado con todo el catálogo."""
    pesos, comprados = _historial(usuario)
    productos, matriz = _catalogo()
    indice = {producto.id: i for i, producto in enumerate(productos)}
    pesos = {indice[producto_id]: peso for producto_id, peso in pesos.items() if producto_id in indice}
    if not pesos:
        return []
    vector_pesos = np.zeros(len(productos))
    for i, peso in pesos.items():
        vector_pesos[i] = peso
    perfil = np.asarray(matriz.T @ vector_pesos / vector_pesos.sum()).reshape(1, -1)
    puntajes = cosine_similarity(perfil, matriz).ravel()
    excluidos = excluidos | comprados
    candidatos = [productos[i] for i in _ordenar(puntajes, productos, vendidos)
                  if productos[i].id not in excluidos and productos[i].stock > 0]
    return candidatos[:cantidad]


def _similares(producto, excluidos, vendidos, cantidad):
    similares = (SimilitudProducto.objects.filter(producto=producto, producto_similar__is_deleted=False,
                                                  producto_similar__stock__gt=0)
                 .exclude(producto_similar__in=excluidos).select_related('producto_similar'))
    similares = sorted(similares, key=lambda s: (-s.puntaje, -vendidos.get(s.producto_similar_id, 0),
                                                 s.producto_similar_id))
    return [similar.producto_similar for similar in similares[:cantidad]]


def _mas_vendidos(excluidos, vendidos, cantidad):
    productos = Producto.objects.filter(stock__gt=0).exclude(id__in=excluidos)
    return sorted(productos, key=lambda p: (-vendidos.get(p.id, 0), p.id))[:cantidad]


def recomendar(usuario, producto=None, cantidad=CANTIDAD_RECOMENDACIONES):
    """Recomendaciones para la ficha de `producto`, o para la página principal si `producto` es None.
    Nunca incluye el producto de la ficha ni productos sin stock. Con consentimiento, tampoco lo que el
    cliente ya compró o tiene en el carrito."""
    vendidos = unidades_vendidas()
    excluidos = {producto.id} if producto else set()
    if autorizo_datos_navegacion(usuario):
        excluidos |= _en_carrito(usuario)
        personalizadas = _personalizadas(usuario, excluidos, vendidos, cantidad)
        if personalizadas:
            return Recomendaciones(PERSONALIZADAS, personalizadas)
        excluidos |= _historial(usuario)[1]
    if producto:
        return Recomendaciones(SIMILARES, _similares(producto, excluidos, vendidos, cantidad))
    return Recomendaciones(MAS_VENDIDOS, _mas_vendidos(excluidos, vendidos, cantidad))


# --- recálculo automático al modificar el catálogo ---

ATRIBUTOS_SIMILITUD = ['categoria_id', 'plataforma_id', 'genero_id', 'is_deleted']
_pausa = threading.local()


@contextmanager
def sin_recalculo_automatico():
    """Para cargas masivas (seed_catalogo): no recalcula por cada producto; quien lo usa recalcula al final."""
    _pausa.activa = True
    try:
        yield
    finally:
        _pausa.activa = False


def _cambia_la_similitud(producto, update_fields):
    if update_fields is not None:
        campos = {campo.removesuffix('_id') for campo in update_fields}
        if not campos & {atributo.removesuffix('_id') for atributo in ATRIBUTOS_SIMILITUD}:
            return False  # ej. la venta que descuenta stock
    anterior = Producto.todos.filter(pk=producto.pk).values(*ATRIBUTOS_SIMILITUD).first() if producto.pk else None
    return anterior is None or any(anterior[atributo] != getattr(producto, atributo)
                                   for atributo in ATRIBUTOS_SIMILITUD)


@receiver(pre_save, sender=Producto)
def _marcar_recalculo(sender, instance, update_fields=None, raw=False, **kwargs):
    instance._recalcular_similitudes = (not raw and not getattr(_pausa, 'activa', False)
                                        and _cambia_la_similitud(instance, update_fields))


@receiver(post_save, sender=Producto)
@receiver(post_delete, sender=Producto)
def _recalcular(sender, instance, signal, **kwargs):
    if signal is post_delete or getattr(instance, '_recalcular_similitudes', False):
        # después del commit, una vez que el cambio quedó guardado
        transaction.on_commit(calcular_similitudes)
