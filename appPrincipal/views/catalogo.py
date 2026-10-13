"""Home, menú de productos, ficha de producto y categorías."""
import re

from django.core.paginator import Paginator
from django.db.models import Avg
from django.shortcuts import get_object_or_404, render

from appPrincipal.models import Favorito, Producto

PLATAFORMAS = {
    codigo: (nombre, categorias)
    for _, opciones in Producto.PLATAFORMAS
    for codigo, nombre, categorias in opciones
}


def _leer_precio(valor):
    """Acepta "15000", "15.000" o "$15.000". Devuelve (precio, es_valido)."""
    valor = valor.replace('$', '').replace('.', '').strip()
    if not valor:
        return None, True
    if not re.fullmatch(r'\d{1,9}', valor):
        return None, False
    return int(valor), True


def filtrar_catalogo(request, productos, con_plataforma=True):
    """Aplica los filtros de género, plataforma y rango de precio que vienen en la URL."""
    genero = request.GET.get('genero', '')
    plataforma = request.GET.get('plataforma', '') if con_plataforma else ''
    texto_min = request.GET.get('precio_min', '').strip()
    texto_max = request.GET.get('precio_max', '').strip()
    errores = []

    if genero not in dict(Producto.GENEROS):
        genero = ''
    if plataforma not in PLATAFORMAS:
        plataforma = ''

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
        productos = productos.filter(categoria__in=PLATAFORMAS[plataforma][1])
    if precio_min is not None:
        productos = productos.filter(precio__gte=precio_min)
    if precio_max is not None:
        productos = productos.filter(precio__lte=precio_max)

    # etiquetas de los filtros aplicados, cada una con el enlace para quitarla
    aplicados = []
    if genero:
        aplicados.append((f"Género: {dict(Producto.GENEROS)[genero]}", ['genero']))
    if plataforma:
        aplicados.append((f"Plataforma: {PLATAFORMAS[plataforma][0]}", ['plataforma']))
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
        'genero': genero,
        'plataforma': plataforma,
        'precio_min': texto_min,
        'precio_max': texto_max,
        'generos': Producto.GENEROS,
        'plataformas': Producto.PLATAFORMAS,
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
    producto = get_object_or_404(Producto, id=producto_id)
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

    productos_relacionados = Producto.objects.filter(
        categoria=producto.categoria, 
        stock__gt=0,
    ).exclude(id=producto.id).order_by('?')[:4]

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

    
def productos_por_categoria(request, categoria):
    productos = Producto.objects.filter(
        categoria=categoria,
        stock__gt=0
    )
    # la categoría ya define la plataforma, así que aquí no se muestra ese filtro
    productos, filtros = filtrar_catalogo(request, productos, con_plataforma=False)

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

    nombre_categoria = dict(Producto.CATEGORIAS).get(categoria, categoria)

    context = {
        'categoria': nombre_categoria,
        'categoria_cod': categoria,  
        'favoritos_ids': favoritos_ids,
        'page_obj': page_obj,
        'productos': page_obj.object_list,
        'orden_actual': orden,
        'filtros': filtros,
    }
    return render(request, 'productos_por_categoria.html', context)
