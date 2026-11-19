"""Recomendaciones de productos."""
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import timedelta

import numpy as np
from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils.text import slugify
from django.utils.timezone import now
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from appPrincipal.models import (Carrito, InteraccionProducto, Producto, ProductoVenta, Recomendacion,
                                 SimilitudProducto)

TOP_SIMILARES = 10
CANTIDAD_RECOMENDACIONES = 4
PESOS = {InteraccionProducto.VISTA: 1, InteraccionProducto.CARRITO: 2}
PESO_COMPRA = 3
VENTANA_VISTAS = timedelta(minutes=30)
VISTOS_RECIENTES = timedelta(days=7)
PESO_PRODUCTO_ACTUAL = 0.6
CONSERVACION_NAVEGACION = timedelta(days=730)

PERSONALIZADAS = 'personalizadas'
SIMILARES = 'similares'
MAS_VENDIDOS = 'mas_vendidos'
COMPLEMENTOS = 'complementos'
TITULOS = {
    PERSONALIZADAS: 'Recomendado para ti',
    SIMILARES: 'Productos similares',
    MAS_VENDIDOS: 'Lo más vendido',
    COMPLEMENTOS: 'Complementa tu compra',
}


@dataclass
class Recomendaciones:
    tipo: str = MAS_VENDIDOS
    productos: list = field(default_factory=list)

    @property
    def titulo(self):
        return TITULOS[self.tipo]


def etiqueta(prefijo, valor):
    return f"{prefijo}_{slugify(valor).replace('-', '_')}"


def documento(producto):
    etiquetas = [etiqueta('cat', producto.categoria.nombre)]
    if producto.plataforma_id:
        etiquetas += [etiqueta('plat', producto.plataforma.codigo), etiqueta('fam', producto.plataforma.familia)]
    if producto.genero_id:
        etiquetas.append(etiqueta('gen', producto.genero.nombre))
    return ' '.join(etiquetas)


def _catalogo():
    productos = list(Producto.objects.select_related('categoria', 'plataforma', 'genero').order_by('id'))
    if not productos:
        return productos, None
    vectorizador = TfidfVectorizer(token_pattern=r'\S+', lowercase=False)  # nosec B106
    return productos, vectorizador.fit_transform([documento(producto) for producto in productos])


def unidades_vendidas():
    return dict(
        ProductoVenta.objects.filter(venta__anulada_en__isnull=True)
        .values('producto').annotate(unidades=Sum('cantidad')).values_list('producto', 'unidades')
    )


def _ordenar(puntajes, productos, vendidos):
    indices = [i for i in range(len(productos)) if round(puntajes[i], 4) > 0]
    return sorted(indices, key=lambda i: (-round(puntajes[i], 4), -vendidos.get(productos[i].id, 0),
                                          productos[i].id))


def calcular_similitudes():
    productos, matriz = _catalogo()
    filas = []
    if len(productos) > 1:
        similitud = cosine_similarity(matriz)
        np.fill_diagonal(similitud, 0)
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


def cobertura_atributos():
    productos = Producto.objects.all()
    incompletos = productos.filter(Q(categoria__requiere_plataforma=True, plataforma__isnull=True)
                                   | Q(categoria__requiere_genero=True, genero__isnull=True)).count()
    total = productos.count()
    return total - incompletos, total


def autorizo_datos_navegacion(usuario):
    return usuario.is_authenticated and usuario.datos_navegacion_autorizados_en is not None


def _eliminar_navegacion(usuario):
    InteraccionProducto.objects.filter(usuario=usuario).delete()
    Recomendacion.objects.filter(usuario=usuario).delete()


def eliminar_navegacion_antigua():
    limite = now() - CONSERVACION_NAVEGACION
    interacciones, _ = InteraccionProducto.objects.filter(fecha__lt=limite).delete()
    recomendaciones, _ = Recomendacion.objects.filter(mostrada_en__lt=limite).delete()
    return interacciones, recomendaciones


def cambiar_consentimiento_navegacion(usuario, autoriza):
    with transaction.atomic():
        if autoriza:
            if usuario.datos_navegacion_autorizados_en is None:
                usuario.datos_navegacion_autorizados_en = now()
        else:
            usuario.datos_navegacion_autorizados_en = None
            _eliminar_navegacion(usuario)
        usuario.save(update_fields=['datos_navegacion_autorizados_en'])


def registrar_interaccion(usuario, producto, tipo):
    if not autorizo_datos_navegacion(usuario):
        return False
    if tipo == InteraccionProducto.VISTA and usuario.interacciones.filter(
            producto=producto, tipo=tipo, fecha__gte=now() - VENTANA_VISTAS).exists():
        return False
    InteraccionProducto.objects.create(usuario=usuario, producto=producto, tipo=tipo)
    return True


def _historial(usuario):
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


def _vistos_recientes(usuario):
    return set(usuario.interacciones.filter(tipo=InteraccionProducto.VISTA, fecha__gte=now() - VISTOS_RECIENTES)
               .values_list('producto_id', flat=True))


def _personalizadas(usuario, excluidos, vendidos, cantidad, producto=None):
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
    if producto is not None and producto.id in indice:
        actual = matriz[indice[producto.id]].toarray()
        perfil = (1 - PESO_PRODUCTO_ACTUAL) * perfil + PESO_PRODUCTO_ACTUAL * actual
    puntajes = cosine_similarity(perfil, matriz).ravel()
    excluidos = excluidos | comprados | _vistos_recientes(usuario)
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
    vendidos = unidades_vendidas()
    excluidos = {producto.id} if producto else set()
    if autorizo_datos_navegacion(usuario):
        excluidos |= _en_carrito(usuario)
        personalizadas = _personalizadas(usuario, excluidos, vendidos, cantidad, producto)
        if personalizadas:
            return Recomendaciones(PERSONALIZADAS, personalizadas)
        excluidos |= _historial(usuario)[1]
    if producto:
        return Recomendaciones(SIMILARES, _similares(producto, excluidos, vendidos, cantidad))
    return Recomendaciones(MAS_VENDIDOS, _mas_vendidos(excluidos, vendidos, cantidad))


def _complementos(en_carrito, excluidos, vendidos):
    pares = {(p.categoria_id, p.plataforma.familia) for p in en_carrito if p.plataforma_id}
    if not pares:
        return []
    plataformas = {p.plataforma_id for p in en_carrito if p.plataforma_id}
    candidatos = (Producto.objects.filter(stock__gt=0, plataforma__familia__in={familia for _, familia in pares})
                  .exclude(id__in=excluidos).select_related('plataforma'))
    complementos = [c for c in candidatos if (c.categoria_id, c.plataforma.familia) not in pares]
    return sorted(complementos, key=lambda c: (c.plataforma_id not in plataformas, -vendidos.get(c.id, 0), c.id))


def _similares_a_varios(productos, excluidos, vendidos):
    mejores = {}
    for similar in (SimilitudProducto.objects.filter(producto__in=productos, producto_similar__is_deleted=False,
                                                     producto_similar__stock__gt=0)
                    .exclude(producto_similar__in=excluidos).select_related('producto_similar')):
        actual = mejores.get(similar.producto_similar_id)
        if actual is None or similar.puntaje > actual.puntaje:
            mejores[similar.producto_similar_id] = similar
    ordenados = sorted(mejores.values(), key=lambda s: (-s.puntaje, -vendidos.get(s.producto_similar_id, 0),
                                                         s.producto_similar_id))
    return [similar.producto_similar for similar in ordenados]


def recomendar_para_carrito(usuario, cantidad=CANTIDAD_RECOMENDACIONES):
    vendidos = unidades_vendidas()
    carrito = Carrito.objects.filter(usuario=usuario).first()
    en_carrito = [item.producto for item in carrito.items.select_related('producto__plataforma')] if carrito else []
    excluidos = {producto.id for producto in en_carrito}
    if autorizo_datos_navegacion(usuario):
        excluidos |= _historial(usuario)[1]
    if not en_carrito:
        return Recomendaciones(MAS_VENDIDOS, _mas_vendidos(excluidos, vendidos, cantidad))

    elegidos = []
    for producto in (_complementos(en_carrito, excluidos, vendidos)
                     + _similares_a_varios(en_carrito, excluidos, vendidos)
                     + _mas_vendidos(excluidos, vendidos, cantidad)):
        if producto.id not in {p.id for p in elegidos}:
            elegidos.append(producto)
        if len(elegidos) == cantidad:
            break
    return Recomendaciones(COMPLEMENTOS, elegidos)


# KPI-05: recomendaciones mostradas y clics

def registrar_mostradas(usuario, productos, ubicacion):
    if not autorizo_datos_navegacion(usuario):
        return []
    return [Recomendacion.objects.create(usuario=usuario, producto=producto, ubicacion=ubicacion, posicion=posicion)
            for posicion, producto in enumerate(productos, start=1)]


def marcar_clic(usuario, recomendacion_id):
    if not usuario.is_authenticated:
        return None
    recomendacion = Recomendacion.objects.filter(id=recomendacion_id, usuario=usuario).first()
    if recomendacion is None:
        return None
    if recomendacion.clic_en is None:
        recomendacion.clic_en = now()
        recomendacion.save(update_fields=['clic_en'])
    return recomendacion.producto


def tasa_de_clics(desde=None, hasta=None):
    recomendaciones = Recomendacion.objects.filter(usuario__is_staff=False)
    if desde is not None:
        recomendaciones = recomendaciones.filter(mostrada_en__gte=desde)
    if hasta is not None:
        recomendaciones = recomendaciones.filter(mostrada_en__lt=hasta)
    mostradas = recomendaciones.count()
    clics = recomendaciones.filter(clic_en__isnull=False).count()
    return {'mostradas': mostradas, 'clics': clics, 'tasa': round(clics / mostradas * 100, 1) if mostradas else None}


# Recálculo automático al modificar el catálogo

ATRIBUTOS_SIMILITUD = ['categoria_id', 'plataforma_id', 'genero_id', 'is_deleted']
_pausa = threading.local()


@contextmanager
def sin_recalculo_automatico():
    _pausa.activa = True
    try:
        yield
    finally:
        _pausa.activa = False


def _cambia_la_similitud(producto, update_fields):
    if update_fields is not None:
        campos = {campo.removesuffix('_id') for campo in update_fields}
        if not campos & {atributo.removesuffix('_id') for atributo in ATRIBUTOS_SIMILITUD}:
            return False
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
        transaction.on_commit(calcular_similitudes)

