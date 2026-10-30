"""Panel de administración: compras de mercadería a proveedores (HU-10, reporte de compras).
Al marcar una compra como recibida se suma al stock y el costo de cada producto pasa a ser el de esa compra."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from appPrincipal.decorators import admin_required
from appPrincipal.forms import normalizar_rut
from appPrincipal.models import Compra, DetalleCompra, Producto, Proveedor
from appPrincipal.views.panel.ventas import _producto_para_venta, _productos_para_venta


@admin_required
def admin_compras(request):
    compras = Compra.objects.select_related('proveedor')
    texto = request.GET.get('q', '').strip()
    if texto:
        compras = compras.filter(Q(proveedor__nombre__icontains=texto) | Q(numero_documento__icontains=texto))
    estado = request.GET.get('estado', '')
    if estado in dict(Compra.ESTADOS):
        compras = compras.filter(estado=estado)
    page_obj = Paginator(compras, 15).get_page(request.GET.get('page'))
    return render(request, 'admin_panel/compras.html', {
        'compras': page_obj.object_list,
        'page_obj': page_obj,
        'estados': Compra.ESTADOS,
        'pendientes': Compra.objects.filter(estado=Compra.PENDIENTE).count(),
    })


def _numero(valor, minimo, mensaje):
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        raise ValueError(mensaje)
    if numero < minimo:
        raise ValueError(mensaje)
    return numero


def _lineas_del_formulario(datos):
    """Une las filas del formulario por producto: {producto_id: (cantidad, costo_unitario)}."""
    lineas = {}
    for producto_id, cantidad, costo in zip(datos.getlist('producto'), datos.getlist('cantidad'),
                                            datos.getlist('costo_unitario')):
        producto_id = _numero(producto_id, 1, "Hay un producto no válido.")
        cantidad = _numero(cantidad, 1, "La cantidad de cada producto debe ser un número entero de al menos 1.")
        costo = _numero(costo, 1, "Ingresa el costo unitario de cada producto (con IVA, mayor que cero).")
        cantidad_previa = lineas.get(producto_id, (0, costo))[0]
        lineas[producto_id] = (cantidad_previa + cantidad, costo)
    if not lineas:
        raise ValueError("Agrega al menos un producto.")
    return lineas


def _proveedor(datos):
    nombre = datos.get('proveedor', '').strip()
    if not nombre:
        raise ValueError("Indica el proveedor.")
    rut = datos.get('rut', '').strip()
    if rut:
        try:
            rut = normalizar_rut(rut)
        except ValidationError as e:
            raise ValueError(f"Proveedor: {e.messages[0]}")
        proveedor = Proveedor.objects.filter(rut=rut).first()
        if proveedor:
            return proveedor
    proveedor = Proveedor.objects.filter(nombre__iexact=nombre).first()
    if proveedor is None:
        return Proveedor.objects.create(nombre=nombre[:100], rut=rut or None)
    if rut and not proveedor.rut:
        proveedor.rut = rut
        proveedor.save(update_fields=['rut'])
    return proveedor


def crear_compra(datos):
    """Registra la compra con su detalle. Si `recibida` viene marcado, suma al stock de inmediato."""
    try:
        fecha = parse_date(datos.get('fecha') or '') or timezone.localdate()
    except ValueError:
        raise ValueError("La fecha no es válida.")
    if fecha > timezone.localdate():
        raise ValueError("La fecha de la compra no puede ser futura.")
    lineas = _lineas_del_formulario(datos)
    productos = Producto.objects.in_bulk(list(lineas))
    if len(productos) != len(lineas):
        raise ValueError("Uno de los productos ya no existe en el catálogo.")

    with transaction.atomic():
        compra = Compra.objects.create(
            proveedor=_proveedor(datos), fecha=fecha, numero_documento=datos.get('numero_documento', '').strip()[:30],
        )
        DetalleCompra.objects.bulk_create([
            DetalleCompra(compra=compra, producto=productos[producto_id], cantidad=cantidad, costo_unitario=costo)
            for producto_id, (cantidad, costo) in lineas.items()
        ])
        compra.calcular_total()
        if datos.get('recibida'):
            compra.marcar_recibida()
    return compra


def _filas_ingresadas(datos):
    """Si la compra no se pudo registrar, vuelve a mostrar los productos que se habían agregado."""
    filas = [(int(producto_id), cantidad, costo) for producto_id, cantidad, costo
             in zip(datos.getlist('producto'), datos.getlist('cantidad'), datos.getlist('costo_unitario'))
             if producto_id.isdigit()]
    productos = _productos_para_venta().in_bulk([producto_id for producto_id, _, _ in filas])
    return [
        {**_producto_para_venta(productos[producto_id]), 'cantidad': cantidad, 'costo': costo}
        for producto_id, cantidad, costo in filas if producto_id in productos
    ]


@admin_required
def registrar_compra(request):
    error = None
    if request.method == 'POST':
        try:
            compra = crear_compra(request.POST)
        except ValueError as e:
            error = str(e)
        else:
            messages.success(request, "Compra registrada." if compra.estado == Compra.PENDIENTE
                             else "Compra registrada y sumada al stock.")
            return redirect('detalle_compra', compra_id=compra.id)

    return render(request, 'admin_panel/registrar_compra.html', {
        'error': error,
        'datos': request.POST if error else {'recibida': 'on', 'fecha': timezone.localdate().isoformat()},
        'hoy': timezone.localdate(),
        'proveedores': Proveedor.objects.all(),
        'items_ingresados': _filas_ingresadas(request.POST) if error else [],
    })


@admin_required
def detalle_compra(request, compra_id):
    compra = get_object_or_404(Compra.objects.select_related('proveedor'), id=compra_id)
    return render(request, 'admin_panel/detalle_compra.html', {
        'compra': compra,
        'detalles': compra.detalles.select_related('producto', 'producto__categoria'),
    })


@admin_required
@require_POST
def recibir_compra(request, compra_id):
    compra = get_object_or_404(Compra, id=compra_id)
    if compra.marcar_recibida():
        messages.success(request, "Compra recibida: las unidades ya se sumaron al stock.")
    return redirect('detalle_compra', compra_id=compra.id)


@admin_required
@require_POST
def eliminar_compra(request, compra_id):
    compra = get_object_or_404(Compra, id=compra_id)
    if compra.estado != Compra.PENDIENTE:
        messages.error(request, "Una compra recibida no se puede eliminar: su mercadería ya está en el stock.")
        return redirect('detalle_compra', compra_id=compra.id)
    compra.delete()
    messages.success(request, "Compra eliminada.")
    return redirect('admin_compras')
