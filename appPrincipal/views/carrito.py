"""Carrito de compras."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from appPrincipal.decorators import login_required_json
from appPrincipal.models import Carrito, ItemCarritoProducto, Producto


@login_required_json
def agregar_al_carrito(request, producto_id):
    usuario = request.user
    carrito, created = Carrito.objects.get_or_create(usuario=usuario)
    producto = get_object_or_404(Producto, id=producto_id)

    cantidad = int(request.POST.get('cantidad', 1))

    item_carrito, item_created = ItemCarritoProducto.objects.get_or_create(
        carrito=carrito, producto=producto
    )

    if item_created:
        if cantidad <= producto.stock:
            item_carrito.cantidad = cantidad
            item_carrito.save()
    else:
        if item_carrito.cantidad + cantidad <= producto.stock:
            item_carrito.cantidad += cantidad
            item_carrito.save()

    carrito_total_items = sum(i.cantidad for i in carrito.items.all())

    return JsonResponse({
        'success': True,
        'message': 'Producto agregado correctamente',
        'total_items': carrito_total_items
    })


@login_required_json
def eliminar_del_carrito(request, item_id):
    if request.method == 'POST':
        try:
            item = get_object_or_404(
                ItemCarritoProducto,
                id=item_id,
                carrito__usuario=request.user
            )

            carrito = item.carrito
            item.delete()

            total_items = sum(i.cantidad for i in carrito.items.all())
            total = carrito.total_carrito()

            return JsonResponse({
                'success': True,
                'total_items': total_items,
                'total': total,
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@login_required_json
def actualizar_cantidad_carrito(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        nueva_cantidad = int(request.POST.get('cantidad', 1))

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

    return render(request, "carrito.html", {
        "productos": items,
        "total": total,
        "total_items": total_items,
    })


@login_required_json
def guardar_datos_envio(request):
    if request.method == "POST":
        usuario = request.user

        region = request.POST.get("region")
        ciudad = request.POST.get("ciudad")
        direccion = request.POST.get("direccion")

        usuario.region = region
        usuario.ciudad = ciudad
        usuario.direccion = direccion
        usuario.save()

        return JsonResponse({
            'success': True,
            'region': region,
            'ciudad': ciudad,
            'direccion': direccion,
        })

    return JsonResponse({'success': False}, status=400)
