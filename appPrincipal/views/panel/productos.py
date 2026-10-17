"""Panel de administración: productos."""
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from appPrincipal.decorators import admin_required
from appPrincipal.forms import ImagenProductoFormSet, ProductoForm
from appPrincipal.models import Categoria, Genero, Producto


@admin_required
def admin_productos(request):
    query = request.GET.get('q', '')
    categoria = request.GET.get('categoria', '')
    genero = request.GET.get('genero', '')
    ordenar = request.GET.get('ordenar', 'recientes')

    productos_list = Producto.objects.select_related('categoria', 'plataforma', 'genero').prefetch_related(
        'imagenes_producto')

    if query:
        productos_list = productos_list.filter(
            Q(nombre__icontains=query) | Q(codigo_de_barra__icontains=query)
        )

    if categoria.isdigit():
        productos_list = productos_list.filter(categoria_id=categoria)

    if genero.isdigit():
        productos_list = productos_list.filter(genero_id=genero)

    if ordenar == 'recientes':
        productos_list = productos_list.order_by('-id')
    elif ordenar == 'antiguos':
        productos_list = productos_list.order_by('id')
    elif ordenar == 'menor_precio':
        productos_list = productos_list.order_by('precio')
    elif ordenar == 'mayor_precio':
        productos_list = productos_list.order_by('-precio')

    categorias = Categoria.objects.all()
    generos = Genero.objects.all()

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

def _errores_json(form, formset):
    """Errores del producto y de sus imágenes, con el name del campo como clave (lo usa el JS de la plantilla)."""
    errores = dict(form.errors)
    for form_imagen in formset.forms:
        for campo, mensajes in form_imagen.errors.items():
            errores[form_imagen.add_prefix(campo)] = mensajes
    if formset.non_form_errors():
        errores[f'{formset.prefix}-TOTAL_FORMS'] = formset.non_form_errors()
    return errores


def _guardar_producto(request, producto, plantilla, contexto):
    """Crea o edita un producto junto con sus imágenes (formset de hasta 6)."""
    es_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        formset = ImagenProductoFormSet(request.POST, request.FILES, instance=form.instance, prefix='imagenes')
        if form.is_valid() and formset.is_valid():
            principal = request.POST.get('principal', '0')
            with transaction.atomic():
                producto = form.save()
                formset.instance = producto
                formset.guardar(int(principal) if principal.isdigit() else 0)
            if es_ajax:
                return JsonResponse({'success': True})
            return redirect('admin_productos')
        if es_ajax:
            return JsonResponse({'success': False, 'errors': _errores_json(form, formset)}, status=400)
    else:
        form = ProductoForm(instance=producto)
        formset = ImagenProductoFormSet(instance=form.instance, prefix='imagenes')
    return render(request, plantilla, {**contexto, 'form': form, 'formset': formset})


@admin_required
def agregar_producto(request):
    return _guardar_producto(request, None, 'admin_panel/agregar_producto.html', {})

@admin_required
@require_POST
def eliminar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    producto.delete() 
    return redirect('admin_productos')


@admin_required
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    return _guardar_producto(request, producto, 'admin_panel/editar_producto.html', {'producto': producto})


@admin_required
def detalle_producto(request, producto_id):
    producto = get_object_or_404(
        Producto.objects.select_related('categoria', 'plataforma', 'genero').prefetch_related('imagenes_producto'),
        id=producto_id,
    )
    return render(request, 'admin_panel/detalle_producto.html', {'producto': producto})
