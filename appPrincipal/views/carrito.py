"""Carrito de compras."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from appPrincipal import envios
from appPrincipal.constants import REGIONES_CIUDADES
from appPrincipal.decorators import login_required_json
from appPrincipal.models import Carrito, ItemCarritoProducto, Producto


def _leer_entero(valor):
    """Valor enviado por el cliente como entero, o None si no es un número."""
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


@login_required_json
@require_POST
def agregar_al_carrito(request, producto_id):
    # Producto.objects no incluye los productos eliminados: no se pueden agregar
    producto = get_object_or_404(Producto, id=producto_id)
    cantidad = _leer_entero(request.POST.get('cantidad', 1))

    if cantidad is None or cantidad < 1:
        return JsonResponse({'success': False, 'error': 'La cantidad no es válida.'}, status=400)

    carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
    item = carrito.items.filter(producto=producto).first()
    en_carrito = item.cantidad if item else 0

    if en_carrito + cantidad > producto.stock:
        disponibles = max(producto.stock - en_carrito, 0)
        mensaje = (f"Solo puedes agregar {disponibles} unidad(es) más de {producto.nombre}."
                   if disponibles else f"No hay más stock disponible de {producto.nombre}.")
        return JsonResponse({'success': False, 'error': mensaje})

    if item:
        item.cantidad += cantidad
        item.save()
    else:
        ItemCarritoProducto.objects.create(carrito=carrito, producto=producto, cantidad=cantidad)

    return JsonResponse({
        'success': True,
        'message': 'Producto agregado correctamente',
        'total_items': sum(i.cantidad for i in carrito.items.all()),
    })


@login_required_json
@require_POST
def eliminar_del_carrito(request, item_id):
    item = ItemCarritoProducto.objects.filter(id=item_id, carrito__usuario=request.user).first()
    if item is None:
        return JsonResponse({'success': False, 'error': 'El producto ya no está en tu carrito.'}, status=404)

    carrito = item.carrito
    item.delete()

    return JsonResponse({
        'success': True,
        'total_items': sum(i.cantidad for i in carrito.items.all()),
        'total': carrito.total_carrito(),
    })


@login_required_json
def actualizar_cantidad_carrito(request):
    if request.method == 'POST':
        item_id = _leer_entero(request.POST.get('item_id'))
        nueva_cantidad = _leer_entero(request.POST.get('cantidad', 1))
        if item_id is None or nueva_cantidad is None:
            return JsonResponse({'success': False, 'error': 'La cantidad no es válida.'}, status=400)

        item = get_object_or_404(ItemCarritoProducto, id=item_id, carrito__usuario=request.user)
        producto = item.producto

        if nueva_cantidad > producto.stock:
            return JsonResponse({
                'success': False,
                'error': f"Solo hay {producto.stock} unidades disponibles de {producto.nombre}."
            })

        if nueva_cantidad > 0:
            item.cantidad = nueva_cantidad
            item.save()
        else:
            item.delete()

        carrito = item.carrito
        total_items = sum(i.cantidad for i in carrito.items.all())
        total = carrito.total_carrito()

        return JsonResponse({
            'success': True,
            'total': total,
            'total_items': total_items,
        })

    return JsonResponse({'success': False})

@login_required
def ver_carrito(request):
    usuario = request.user

    carrito, creado = Carrito.objects.get_or_create(usuario=usuario)

    items = carrito.items.all()

    for item in items:
        if item.producto.is_deleted:
            item.delete()

    items = carrito.items.all()

    total = sum((item.producto.precio or 0) * item.cantidad for item in items)
    total_items = sum(item.cantidad for item in items)

    # la opción de entrega elegida antes (si volvió desde el pago) queda marcada
    envio_elegido = request.session.get('metodo_envio')
    if not envios.disponible_para(envio_elegido, usuario.ciudad):
        envio_elegido = None

    return render(request, "carrito.html", {
        "productos": items,
        "total": total,
        "total_items": total_items,
        "regiones_ciudades": REGIONES_CIUDADES,
        "opciones_envio": envios.opciones_para_plantilla(),
        "envio_elegido": envio_elegido,
        "ciudad_tienda": envios.CIUDAD_TIENDA,
    })


@login_required_json
@require_POST
def guardar_datos_envio(request):
    region = request.POST.get("region", "")
    ciudad = request.POST.get("ciudad", "")
    direccion = request.POST.get("direccion", "").strip()

    if ciudad not in REGIONES_CIUDADES.get(region, []):
        return JsonResponse({'success': False, 'error': 'La ciudad no corresponde a la región seleccionada.'}, status=400)
    if not direccion or len(direccion) > 100:
        return JsonResponse({'success': False, 'error': 'Ingresa una dirección de hasta 100 caracteres.'}, status=400)

    usuario = request.user
    usuario.region = region
    usuario.ciudad = ciudad
    usuario.direccion = direccion
    usuario.save(update_fields=['region', 'ciudad', 'direccion'])

    return JsonResponse({
        'success': True,
        'region': region,
        'ciudad': ciudad,
        'direccion': direccion,
    })
