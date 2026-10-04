"""Home, menú de productos, ficha de producto y categorías."""
from django.core.paginator import Paginator
from django.db.models import Avg
from django.shortcuts import get_object_or_404, render

from appPrincipal.models import Favorito, Producto


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
    }
    return render(request, 'productos_por_categoria.html', context)
