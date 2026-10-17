"""Home, menú de productos, ficha de producto y categorías."""
import re

from django.core.paginator import Paginator
from django.db.models import Avg
from django.shortcuts import get_object_or_404, render

from appPrincipal.models import Categoria, ConfiguracionSitio, Favorito, Genero, Plataforma, Producto


def productos_para_listado(productos):
    """Carga de una vez lo que muestran las tarjetas: categoría, plataforma, género e imágenes."""
    return productos.select_related('categoria', 'plataforma', 'genero').prefetch_related('imagenes_producto')


def plataformas_por_familia():
    """[(familia, [plataformas])] en el orden de la tabla, para el <select> con <optgroup>."""
    grupos = {}
    for plataforma in Plataforma.objects.all():
        grupos.setdefault(plataforma.get_familia_display(), []).append(plataforma)
    return list(grupos.items())


def _leer_precio(valor):
    """Acepta "15000", "15.000" o "$15.000". Devuelve (precio, es_valido)."""
    valor = valor.replace('$', '').replace('.', '').strip()
    if not valor:
        return None, True
    if not re.fullmatch(r'\d{1,9}', valor):
        return None, False
    return int(valor), True


def filtrar_catalogo(request, productos, con_plataforma=True):
    """Aplica los filtros de género, plataforma y rango de precio que vienen en la URL.
    El género llega como su id y la plataforma como su código (ej. ps5)."""
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

    # etiquetas de los filtros aplicados, cada una con el enlace para quitarla
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


def home(request):
    return render(request, 'home.html')

def productos_menu(request):
    query = request.GET.get('buscar')
    orden = request.GET.get('orden') 

    if query:
        productos = Producto.objects.filter(
            nombre__icontains=query,
            stock__gt=0,
        )
    else:
        productos = Producto.objects.filter(
            stock__gt=0,
        )

    productos, filtros = filtrar_catalogo(request, productos)
    productos = productos_para_listado(productos)

    if orden == 'precio_asc':
        productos = productos.order_by('precio')
    elif orden == 'precio_desc':
        productos = productos.order_by('-precio')
    else:
        productos = productos.order_by('-id')

    favoritos_ids = []
    if request.user.is_authenticated:
        favoritos_ids = Favorito.objects.filter(usuario=request.user).values_list('producto_id', flat=True)

    paginator = Paginator(productos, 16)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    template_name = 'resultado_busqueda.html' if query else 'productosmenu.html'
    
    return render(request, template_name, {
        'page_obj': page_obj,
        'productos': page_obj.object_list,
        'favoritos_ids': favoritos_ids,
        'query': query,
        'orden_actual': orden,
        'filtros': filtros,
    })


def producto_detalle(request, producto_id):
    producto = get_object_or_404(
        Producto.objects.select_related('categoria', 'plataforma', 'genero').prefetch_related('imagenes_producto'),
        id=producto_id,
    )
    rango_cantidad = range(1, producto.stock + 1)

    opiniones_list = producto.opiniones.all().order_by('-fecha_creacion')

    paginator = Paginator(opiniones_list, 5) 
    page_number = request.GET.get('page')
    opiniones = paginator.get_page(page_number)

    promedio_puntuacion = opiniones_list.aggregate(avg=Avg('puntuacion'))['avg'] or 0
    promedio_puntuacion = round(promedio_puntuacion, 1)

    full_stars = int(promedio_puntuacion)
    half_star = (promedio_puntuacion - full_stars) >= 0.5
    full_stars_range = range(full_stars)
    empty_stars_range = range(5 - full_stars - (1 if half_star else 0))

    total_opiniones = opiniones_list.count()
    ratings_data = []
    
    for score in range(5, 0, -1):
        count = opiniones_list.filter(puntuacion=score).count()
        percent = (count / total_opiniones * 100) if total_opiniones > 0 else 0
        ratings_data.append({
            "score": score,
            "count": count,
            "percent": round(percent, 1)
        })

    # qué relacionados se muestran lo decide el admin en Configuración del panel
    configuracion = ConfiguracionSitio.actual()
    productos_relacionados = Producto.objects.none()
    if configuracion.productos_relacionados != ConfiguracionSitio.RELACIONADOS_NINGUNO:
        productos_relacionados = Producto.objects.filter(stock__gt=0).exclude(id=producto.id)
        if configuracion.productos_relacionados == ConfiguracionSitio.RELACIONADOS_CATEGORIA:
            productos_relacionados = productos_relacionados.filter(categoria=producto.categoria,
                                                                   plataforma=producto.plataforma)
        productos_relacionados = productos_para_listado(productos_relacionados).order_by('?')[:4]

    es_favorito = False
    if request.user.is_authenticated:
        es_favorito = Favorito.objects.filter(usuario=request.user, producto=producto).exists()

    return render(request, "producto_detalle.html", {
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
        "productos_relacionados": productos_relacionados,
    })

    
def productos_por_categoria(request, categoria_id, plataforma=None):
    categoria = get_object_or_404(Categoria, id=categoria_id)
    productos = Producto.objects.filter(categoria=categoria, stock__gt=0)
    nombre_categoria = categoria.nombre
    if plataforma:
        plataforma = get_object_or_404(Plataforma, codigo=plataforma)
        productos = productos.filter(plataforma=plataforma)
        nombre_categoria = f"{categoria.nombre} {plataforma.nombre}"
    # si la URL ya fija la plataforma, o la categoría no la usa, no se muestra ese filtro
    con_plataforma = plataforma is None and categoria.requiere_plataforma
    productos, filtros = filtrar_catalogo(request, productos, con_plataforma=con_plataforma)
    productos = productos_para_listado(productos)

    orden = request.GET.get('orden')
    
    if orden == 'precio_asc':
        productos = productos.order_by('precio')
    elif orden == 'precio_desc':
        productos = productos.order_by('-precio')
    else:
        productos = productos.order_by('-id')

    favoritos_ids = []
    if request.user.is_authenticated:
        favoritos_ids = Favorito.objects.filter(
            usuario=request.user
        ).values_list('producto_id', flat=True)

    paginator = Paginator(productos, 16)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'categoria': nombre_categoria,
        'favoritos_ids': favoritos_ids,
        'page_obj': page_obj,
        'productos': page_obj.object_list,
        'orden_actual': orden,
        'filtros': filtros,
    }
    return render(request, 'productos_por_categoria.html', context)
