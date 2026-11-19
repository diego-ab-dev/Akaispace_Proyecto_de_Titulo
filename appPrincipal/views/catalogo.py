"""Catálogo: home, menú, ficha de producto y categorías."""
import re

from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, prefetch_related_objects
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from appPrincipal.models import (Categoria, ConfiguracionSitio, Favorito, Genero, InteraccionProducto, Plataforma,
                                 Producto, ProductoVenta)
from appPrincipal.recomendaciones import (marcar_clic, recomendar, recomendar_para_carrito, registrar_interaccion,
                                          registrar_mostradas)
from appPrincipal.views.opiniones import ENVIO_RECIBIDO, estado_para_opinar


def productos_para_listado(productos):
    return productos.select_related('categoria', 'plataforma', 'genero').prefetch_related('imagenes_producto')


def plataformas_por_familia():
    grupos = {}
    for plataforma in Plataforma.objects.all():
        grupos.setdefault(plataforma.get_familia_display(), []).append(plataforma)
    return list(grupos.items())


def _leer_precio(valor):
    valor = valor.replace('$', '').replace('.', '').strip()
    if not valor:
        return None, True
    if not re.fullmatch(r'\d{1,9}', valor):
        return None, False
    return int(valor), True


def filtrar_catalogo(request, productos, con_plataforma=True):
    generos = list(Genero.objects.all())
    texto_genero = request.GET.get('genero', '')
    genero = next((g for g in generos if str(g.id) == texto_genero), None)
    codigo_plataforma = request.GET.get('plataforma', '') if con_plataforma else ''
    plataforma = Plataforma.objects.filter(codigo=codigo_plataforma).first() if codigo_plataforma else None
    texto_min = request.GET.get('precio_min', '').strip()
    texto_max = request.GET.get('precio_max', '').strip()
    errores = []

    precio_min, min_valido = _leer_precio(texto_min)
    precio_max, max_valido = _leer_precio(texto_max)
    if not (min_valido and max_valido):
        errores.append("El precio debe ser un número entero, por ejemplo 15000.")
        precio_min = precio_max = None
    elif precio_min is not None and precio_max is not None and precio_min > precio_max:
        errores.append("El precio mínimo no puede ser mayor que el máximo.")
        precio_min = precio_max = None

    if genero:
        productos = productos.filter(genero=genero)
    if plataforma:
        productos = productos.filter(plataforma=plataforma)
    if precio_min is not None:
        productos = productos.filter(precio__gte=precio_min)
    if precio_max is not None:
        productos = productos.filter(precio__lte=precio_max)

    aplicados = []
    if genero:
        aplicados.append((f"Género: {genero.nombre}", ['genero']))
    if plataforma:
        aplicados.append((f"Plataforma: {plataforma.nombre}", ['plataforma']))
    if precio_min is not None and precio_max is not None:
        aplicados.append((f"Precio: ${precio_min:,} a ${precio_max:,}".replace(',', '.'), ['precio_min', 'precio_max']))
    elif precio_min is not None:
        aplicados.append((f"Precio desde ${precio_min:,}".replace(',', '.'), ['precio_min']))
    elif precio_max is not None:
        aplicados.append((f"Precio hasta ${precio_max:,}".replace(',', '.'), ['precio_max']))

    def url_sin(*parametros):
        params = request.GET.copy()
        for parametro in ('page', *parametros):
            params.pop(parametro, None)
        return params.urlencode()

    return productos, {
        'genero': genero.id if genero else None,
        'plataforma': plataforma.codigo if plataforma else '',
        'precio_min': texto_min,
        'precio_max': texto_max,
        'generos': generos,
        'plataformas': plataformas_por_familia() if con_plataforma else [],
        'con_plataforma': con_plataforma,
        'errores': errores,
        'activos': bool(aplicados),
        'aplicados': [{'texto': texto, 'url': url_sin(*params)} for texto, params in aplicados],
        'url_limpiar': url_sin('genero', 'plataforma', 'precio_min', 'precio_max'),
    }


def recomendaciones_para(request, producto=None):
    if not ConfiguracionSitio.actual().mostrar_recomendaciones:
        return None
    return _preparar_recomendaciones(request, recomendar(request.user, producto), 'ficha' if producto else 'home')


def recomendaciones_carrito(request):
    if not ConfiguracionSitio.actual().mostrar_recomendaciones:
        return None
    return _preparar_recomendaciones(request, recomendar_para_carrito(request.user), 'carrito')


def _preparar_recomendaciones(request, recomendaciones, ubicacion):
    prefetch_related_objects(recomendaciones.productos, 'categoria', 'plataforma', 'imagenes_producto')
    mostradas = registrar_mostradas(request.user, recomendaciones.productos, ubicacion)
    for recomendado, mostrada in zip(recomendaciones.productos, mostradas):
        recomendado.url_recomendacion = reverse('clic_recomendacion', args=[mostrada.id])
        recomendado.id_recomendacion = mostrada.id
    return recomendaciones


def clic_recomendacion(request, recomendacion_id):
    producto = marcar_clic(request.user, recomendacion_id)
    if producto is None:
        raise Http404
    return redirect('producto_detalle', producto_id=producto.id)


def home(request):
    return render(request, 'home.html', {'recomendaciones': recomendaciones_para(request)})

def _pagina_de_catalogo(request, productos):
    orden = request.GET.get('orden')
    productos = productos_para_listado(productos).order_by(
        {'precio_asc': 'precio', 'precio_desc': '-precio'}.get(orden, '-id'))
    page_obj = Paginator(productos, 16).get_page(request.GET.get('page'))
    favoritos_ids = set()
    if request.user.is_authenticated:
        favoritos_ids = set(Favorito.objects.filter(usuario=request.user).values_list('producto_id', flat=True))
    return {
        'page_obj': page_obj,
        'productos': page_obj.object_list,
        'favoritos_ids': favoritos_ids,
        'orden_actual': orden,
    }


def productos_menu(request):
    query = request.GET.get('buscar')
    productos = Producto.objects.filter(stock__gt=0)
    if query:
        productos = productos.filter(nombre__icontains=query)
    productos, filtros = filtrar_catalogo(request, productos)

    template_name = 'resultado_busqueda.html' if query else 'productosmenu.html'
    return render(request, template_name, {
        **_pagina_de_catalogo(request, productos),
        'query': query,
        'filtros': filtros,
    })


def producto_detalle(request, producto_id):
    producto = get_object_or_404(
        Producto.objects.select_related('categoria', 'plataforma', 'genero').prefetch_related('imagenes_producto'),
        id=producto_id,
    )
    registrar_interaccion(request.user, producto, InteraccionProducto.VISTA)
    rango_cantidad = range(1, producto.stock + 1)

    opiniones_list = producto.opiniones.select_related('usuario').order_by('-fecha_creacion')

    paginator = Paginator(opiniones_list, 5) 
    page_number = request.GET.get('page')
    opiniones = paginator.get_page(page_number)

    autores_verificados = set(
        ProductoVenta.objects.filter(producto=producto, venta__datos_envio__estado=ENVIO_RECIBIDO,
                                     venta__usuario__in=[op.usuario_id for op in opiniones])
        .values_list('venta__usuario', flat=True)
    )
    for op in opiniones:
        op.compra_verificada = op.usuario_id in autores_verificados

    resumen = producto.opiniones.aggregate(
        avg=Avg('puntuacion'), total=Count('id'),
        **{f'estrellas_{n}': Count('id', filter=Q(puntuacion=n)) for n in range(1, 6)},
    )
    promedio_puntuacion = round(resumen['avg'] or 0, 1)

    full_stars = int(promedio_puntuacion)
    half_star = (promedio_puntuacion - full_stars) >= 0.5
    full_stars_range = range(full_stars)
    empty_stars_range = range(5 - full_stars - (1 if half_star else 0))

    total_opiniones = resumen['total']
    ratings_data = []

    for score in range(5, 0, -1):
        count = resumen[f'estrellas_{score}']
        percent = (count / total_opiniones * 100) if total_opiniones > 0 else 0
        ratings_data.append({
            "score": score,
            "count": count,
            "percent": round(percent, 1)
        })

    configuracion = ConfiguracionSitio.actual()
    productos_relacionados = Producto.objects.none()
    titulo_relacionados = 'También te podría interesar'
    recomendaciones = recomendaciones_para(request, producto)
    if recomendaciones is not None:
        productos_relacionados = recomendaciones.productos
        titulo_relacionados = recomendaciones.titulo
    elif configuracion.productos_relacionados != ConfiguracionSitio.RELACIONADOS_NINGUNO:
        productos_relacionados = Producto.objects.filter(stock__gt=0).exclude(id=producto.id)
        if configuracion.productos_relacionados == ConfiguracionSitio.RELACIONADOS_CATEGORIA:
            productos_relacionados = productos_relacionados.filter(categoria=producto.categoria,
                                                                   plataforma=producto.plataforma)
        productos_relacionados = productos_para_listado(productos_relacionados).order_by('?')[:4]

    es_favorito = False
    if request.user.is_authenticated:
        es_favorito = Favorito.objects.filter(usuario=request.user, producto=producto).exists()

    estado_opinion = estado_para_opinar(request.user, producto) if configuracion.mostrar_opiniones else None

    url_compartir = request.build_absolute_uri(reverse('producto_detalle', args=[producto.id]))
    imagen = producto.imagen_principal
    imagen_compartir = request.build_absolute_uri(imagen.url) if imagen else ''

    return render(request, "producto_detalle.html", {
        "url_compartir": url_compartir,
        "imagen_compartir": imagen_compartir,
        "producto": producto,
        "rango_cantidad": rango_cantidad,
        "opiniones": opiniones, 
        "promedio_puntuacion": promedio_puntuacion,
        "full_stars_range": full_stars_range, 
        "half_star": half_star,
        "empty_stars_range": empty_stars_range,
        "ratings": ratings_data, 
        "total_opiniones": total_opiniones,
        "es_favorito": es_favorito,
        "estado_opinion": estado_opinion,
        "productos_relacionados": productos_relacionados,
        "titulo_relacionados": titulo_relacionados,
    })

    
def productos_por_categoria(request, categoria_id, plataforma=None):
    categoria = get_object_or_404(Categoria, id=categoria_id)
    productos = Producto.objects.filter(categoria=categoria, stock__gt=0)
    nombre_categoria = categoria.nombre
    if plataforma:
        plataforma = get_object_or_404(Plataforma, codigo=plataforma)
        productos = productos.filter(plataforma=plataforma)
        nombre_categoria = f"{categoria.nombre} {plataforma.nombre}"
    con_plataforma = plataforma is None and categoria.requiere_plataforma
    productos, filtros = filtrar_catalogo(request, productos, con_plataforma=con_plataforma)
    return render(request, 'productos_por_categoria.html', {
        **_pagina_de_catalogo(request, productos),
        'categoria': nombre_categoria,
        'filtros': filtros,
    })
