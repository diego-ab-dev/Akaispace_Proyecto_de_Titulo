"""Solicitudes de devolución del cliente."""
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from appPrincipal.forms import SolicitudDevolucionForm
from appPrincipal.models import Devolucion, Producto, ProductoVenta, Venta


@login_required
def crear_devolucion(request, compra_id, producto_id):
    usuario = request.user
    compra = get_object_or_404(Venta, id=compra_id, usuario=usuario)
    # Producto.todos: se puede devolver un producto aunque ya no esté en el catálogo
    producto = get_object_or_404(Producto.todos, id=producto_id)

    item = get_object_or_404(compra.producto_venta, producto=producto)
    cantidad_comprada = item.cantidad

    form = SolicitudDevolucionForm()

    if request.method == 'POST':
        form = SolicitudDevolucionForm(request.POST, request.FILES)

        if form.is_valid():
            motivo = form.cleaned_data['descripcion']
            cantidad = form.cleaned_data['cantidad']
            img1 = form.cleaned_data['imagen1']
            img2 = form.cleaned_data['imagen2']
            img3 = form.cleaned_data['imagen3']

            Devolucion.objects.create(
                usuario=usuario,
                venta=compra,
                producto=producto,
                cantidad=cantidad,
                motivo=motivo,
                imagen1=img1,
                imagen2=img2,
                imagen3=img3,
                estado='Pendiente'
            )
            return redirect('/perfil?notif=Solicitud+de+devolución+enviada+con+éxito&type=success')
        
        else:
            pass 

    return render(request, 'crear_devolucion.html', {
        'compra': compra,
        'producto': producto,
        'cantidad_comprada': cantidad_comprada,
        'form': form 
    })

@login_required
def listar_devoluciones(request):
    usuario = request.user
    todos_devoluciones = Devolucion.objects.filter(usuario=usuario).order_by('-id')

    paginator = Paginator(todos_devoluciones, 5) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)


    return render(request, 'lista_devoluciones.html', {
        'todos_devoluciones': todos_devoluciones,
        'page_obj': page_obj,
    })

@login_required
def ver_detalle_devolucion(request, devolucion_id):
    usuario = request.user
    devolucion = get_object_or_404(Devolucion, id=devolucion_id, usuario=usuario)
    
    monto_reembolso = 0
    try:
        item_venta = ProductoVenta.objects.get(
            venta=devolucion.venta, 
            producto=devolucion.producto
        )
        monto_reembolso = item_venta.precio_unitario * devolucion.cantidad
    except ProductoVenta.DoesNotExist:
        monto_reembolso = 0

    return render(request, 'detalle_devolucion.html', {
        'devolucion': devolucion,
        'monto_reembolso': monto_reembolso 
    })
