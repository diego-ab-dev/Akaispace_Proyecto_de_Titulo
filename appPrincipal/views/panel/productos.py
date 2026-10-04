"""Panel de administración: productos."""
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from appPrincipal.decorators import admin_required
from appPrincipal.forms import ProductoForm
from appPrincipal.models import Producto


@admin_required
def admin_productos(request):
    query = request.GET.get('q', '')
    categoria = request.GET.get('categoria', '')
    genero = request.GET.get('genero', '')
    ordenar = request.GET.get('ordenar', 'recientes')

    productos_list = Producto.objects.all()

    if query:
        productos_list = productos_list.filter(
            Q(nombre__icontains=query) | Q(codigo_de_barra__icontains=query)
        )

    if categoria:
        productos_list = productos_list.filter(categoria=categoria)

    if genero:
        productos_list = productos_list.filter(genero=genero)

    if ordenar == 'recientes':
        productos_list = productos_list.order_by('-id')
    elif ordenar == 'antiguos':
        productos_list = productos_list.order_by('id')
    elif ordenar == 'menor_precio':
        productos_list = productos_list.order_by('precio')
    elif ordenar == 'mayor_precio':
        productos_list = productos_list.order_by('-precio')

    categorias = []
    for grupo in Producto.CATEGORIAS:
        for cat in grupo[1]:
            categorias.append(cat)
    generos = Producto.GENEROS

    paginator = Paginator(productos_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    mensaje = ""
    if (query or categoria or genero) and page_obj.paginator.count == 0:
        mensaje = "No se encontraron resultados para tu búsqueda."

    return render(request, 'admin_panel/productos.html', {
        'productos': page_obj.object_list,
        'page_obj': page_obj,
        'actual_url': request.path, 
        'query': query,
        'categoria': categoria,
        'genero': genero,
        'ordenar': ordenar,
        'categorias': categorias,
        'generos': generos,
        'mensaje': mensaje
    })

@admin_required
def agregar_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        
        if form.is_valid():
            form.save()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            
            return redirect('admin_productos')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = ProductoForm()
    
    return render(request, 'admin_panel/agregar_producto.html', {'form': form})

@admin_required
@require_POST
def eliminar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    producto.delete()  # borrado lógico: guarda también deleted_at
    return redirect('admin_productos')


@admin_required
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        
        if form.is_valid():
            form.save()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            
            return redirect('admin_productos')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)            
    else:
        form = ProductoForm(instance=producto) 
    return render(request, 'admin_panel/editar_producto.html', {'form': form, 'producto': producto})


@admin_required
def detalle_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    return render(request, 'admin_panel/detalle_producto.html', {'producto': producto})
