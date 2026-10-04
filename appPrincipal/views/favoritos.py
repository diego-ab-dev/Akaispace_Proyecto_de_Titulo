"""Lista de favoritos."""
import json

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from appPrincipal.decorators import login_required_json
from appPrincipal.models import Favorito, Producto


@login_required
def lista_favoritos(request):
    usuario = request.user

    favoritos = Favorito.objects.filter(
        usuario=usuario,
        producto__is_deleted=False
    )

    Favorito.objects.filter(
        usuario=usuario,
        producto__is_deleted=True
    ).delete()

    paginator = Paginator(favoritos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'favorite.html', {
        'wishlist_items': favoritos,
        'page_obj': page_obj,
        'favoritos': page_obj.object_list,
    })

@login_required_json
def agregar_favorito(request, producto_id):
    usuario = request.user
    producto = get_object_or_404(Producto, id=producto_id)
    
    favorito = Favorito.objects.filter(usuario=usuario, producto=producto).first()
    
    agregado = False

    if favorito:
        favorito.delete()
        mensaje = "Eliminado de favoritos"
        agregado = False
    else:
        Favorito.objects.create(usuario=usuario, producto=producto)
        mensaje = "¡Agregado a favoritos!"
        agregado = True

    return JsonResponse({
        'success': True,
        'message': mensaje,
        'agregado': agregado  
    })

@login_required_json
@require_http_methods(["DELETE"])
def eliminar_favorito(request, item_id):
    favorito = get_object_or_404(Favorito, id=item_id, usuario=request.user)
    favorito.delete()
    return JsonResponse({'message': 'Artículo eliminado correctamente'}, status=200)

@login_required_json
@require_http_methods(["POST"])
def eliminar_favoritos_seleccionados(request):
    try:
        data = json.loads(request.body)
        item_ids = data.get('ids', [])

        if item_ids:
            Favorito.objects.filter(id__in=item_ids, usuario=request.user).delete()
            return JsonResponse({'success': True})
        
        return JsonResponse({'success': False, 'error': 'No se seleccionaron items'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
