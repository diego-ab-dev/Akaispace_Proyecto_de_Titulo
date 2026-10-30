"""Panel de administración: ventas, estado de los envíos y registro de ventas presenciales (HU-12)."""
import re

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from appPrincipal import pagos
from appPrincipal.decorators import admin_required
from appPrincipal.envios import TRANSPORTISTAS_ENCOMIENDA
from appPrincipal.models import Envio, Producto, Venta
from appPrincipal.views.panel.filtros import filtrar_por_fechas


@admin_required
def admin_ventas(request):
    query = request.GET.get('q', '')
    ordenar = request.GET.get('ordenar')

    ventas_list = Venta.objects.select_related(
        'usuario'
    ).prefetch_related(
        'producto_venta__producto'
    ).all()

    if query:
        ventas_list = ventas_list.filter(
            Q(usuario__nombre__icontains=query) | Q(id__icontains=query)
        )

    ventas_list, errores = filtrar_por_fechas(request, ventas_list, 'fecha')

    estado = request.GET.get('estado', '')
    if estado in dict(Envio.ESTADO_CHOICES):
        ventas_list = ventas_list.filter(datos_envio__estado=estado)
    entrega = request.GET.get('entrega', '')
    if entrega in dict(Venta.ENVIO_CHOICES):
        ventas_list = ventas_list.filter(metodo_envio=entrega)
    canal = request.GET.get('canal', '')
    if canal in dict(Venta.CANALES):
        ventas_list = ventas_list.filter(canal=canal)

    if ordenar == "antiguas":
        ventas_list = ventas_list.order_by("fecha")
    else:
        ventas_list = ventas_list.order_by("-fecha")

    paginator = Paginator(ventas_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_panel/ventas.html', {
        'ventas': page_obj.object_list,
        'page_obj': page_obj,
        'hoy': timezone.localdate(),
        'errores': errores,
        'estados': Envio.ESTADO_CHOICES,
        'entregas': Venta.ENVIO_CHOICES,
        'canales': Venta.CANALES,
    })


@admin_required
def detalle_venta(request, venta_id):
    venta = get_object_or_404(Venta.objects.prefetch_related('producto_venta__producto__imagenes_producto'), id=venta_id)
    return render(request, 'admin_panel/detalle_venta.html', {'venta': venta})

@admin_required
def modificar_venta(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    if venta.canal != Venta.CANAL_WEB:
        return redirect('detalle_venta', venta_id=venta.id)  # las ventas presenciales no tienen envío
    envio = getattr(venta, 'datos_envio', None)

    error = None
    estado_post = None
    tracking_post = None
    transportista_post = None 

    if request.method == 'POST':
        estado_post = request.POST.get('estado')
        tracking_post = request.POST.get('numero_seguimiento', '').strip()
        transportista_post = request.POST.get('transportista') 

        estados_con_tracking = ["Enviado", "En Tránsito", "En Reparto"]

        if estado_post not in venta.estados_envio:
            error = "Estado no válido."
        elif not venta.lleva_seguimiento:
            tracking_post = ''
            transportista_post = None
        elif transportista_post not in TRANSPORTISTAS_ENCOMIENDA:
            error = "Selecciona un transportista válido."
        elif estado_post in estados_con_tracking and not tracking_post:
            error = "Debe ingresar un número de seguimiento para este estado."

        if not error and tracking_post:
            if not re.match(r'^[A-Za-z0-9]{5,20}$', tracking_post):
                error = "Número de seguimiento inválido. Solo letras y números (5–20 caracteres)."
            elif Envio.objects.filter(numero_seguimiento=tracking_post).exclude(id=envio.id if envio else None).exists():
                error = f"Error: El número '{tracking_post}' ya fue asignado a otro pedido anteriormente."
        
        if error:
            return render(request, 'admin_panel/modificar_venta.html', {
                'venta': venta,
                'envio': envio,
                'error': error,
                'estado_post': estado_post,
                'tracking_post': tracking_post,
                'transportista_post': transportista_post,
                'transportistas': TRANSPORTISTAS_ENCOMIENDA,
            })

        if envio is None:
            envio = Envio.objects.create(venta=venta)
        envio.numero_seguimiento = tracking_post
        if transportista_post:
            envio.transportista = transportista_post
        envio.guardar_estado(estado_post)

        return redirect('detalle_venta', venta_id=venta.id)

    return render(request, 'admin_panel/modificar_venta.html', {
        'venta': venta,
        'envio': envio,
        'error': error,
        'transportistas': TRANSPORTISTAS_ENCOMIENDA,
    })


@admin_required
@require_POST
def anular_venta(request, venta_id):
    with transaction.atomic():
        venta = get_object_or_404(Venta.objects.select_for_update(), id=venta_id)
        envio = Envio.objects.filter(venta=venta).first()
        if not venta.anulada and not (envio and envio.estado == "Anulada"):
            # las ventas presenciales (HU-12) no tienen envío: basta con anulada_en
            if venta.canal == Venta.CANAL_WEB:
                envio = envio or Envio(venta=venta)
                envio.estado = "Anulada"
                envio.save()
            venta.anulada_en = timezone.now()
            venta.save(update_fields=['anulada_en'])

            devuelto = dict(
                venta.devoluciones.filter(estado='Aprobada')
                .values_list('producto_id').annotate(total=Sum('cantidad'))
            )
            for item in venta.producto_venta.all():
                reponer = item.cantidad - devuelto.get(item.producto_id, 0)
                if reponer > 0:
                    Producto.todos.filter(id=item.producto_id).update(stock=F('stock') + reponer)

    return redirect(f"{reverse('detalle_venta', args=[venta_id])}?msg=anulada")


def _producto_para_venta(producto):
    imagen = producto.imagen_principal
    return {
        'id': producto.id,
        'nombre': producto.nombre,
        'codigo': producto.codigo_de_barra or '',
        'categoria': producto.categoria_texto,
        'precio': producto.precio,
        'costo': producto.costo,
        'stock': producto.stock,
        'imagen': imagen.url if imagen else '',
    }


def _productos_para_venta():
    return Producto.objects.select_related('categoria', 'plataforma').prefetch_related('imagenes_producto')


# HU-12: el lector de código de barras escribe el código y presiona Enter, así que un código exacto
# devuelve solo ese producto; si no, se busca por nombre o por parte del código.
@admin_required
def buscar_productos_venta(request):
    texto = request.GET.get('q', '').strip()
    if not texto:
        return JsonResponse({'productos': []})
    productos = list(_productos_para_venta().filter(codigo_de_barra=texto))
    if not productos:
        productos = _productos_para_venta().filter(
            Q(nombre__icontains=texto) | Q(codigo_de_barra__icontains=texto)
        ).order_by('nombre')[:10]
    return JsonResponse({'productos': [_producto_para_venta(producto) for producto in productos]})


def _items_del_formulario(datos):
    """Une las filas del formulario por producto. Lanza ValueError si una cantidad no es válida."""
    cantidades = {}
    for producto_id, cantidad in zip(datos.getlist('producto'), datos.getlist('cantidad')):
        try:
            producto_id, cantidad = int(producto_id), int(cantidad)
        except ValueError:
            raise ValueError("Revisa las cantidades: deben ser números enteros.")
        if cantidad < 1:
            raise ValueError("La cantidad de cada producto debe ser al menos 1.")
        cantidades[producto_id] = cantidades.get(producto_id, 0) + cantidad
    return [{'producto_id': producto_id, 'cantidad': cantidad} for producto_id, cantidad in cantidades.items()]


def _filas_ingresadas(datos):
    """Si la venta no se pudo registrar, vuelve a mostrar los productos que el admin había agregado."""
    filas = [(int(producto_id), cantidad) for producto_id, cantidad
             in zip(datos.getlist('producto'), datos.getlist('cantidad')) if producto_id.isdigit()]
    productos = _productos_para_venta().in_bulk([producto_id for producto_id, _ in filas])
    return [
        {**_producto_para_venta(productos[producto_id]), 'cantidad': cantidad}
        for producto_id, cantidad in filas if producto_id in productos
    ]


@admin_required
def registrar_venta(request):
    """HU-12: venta hecha en la tienda física o por WhatsApp. Descuenta el stock y queda en los reportes."""
    canal = request.POST.get('canal', Venta.CANAL_TIENDA)
    metodo_pago = request.POST.get('metodo_pago', '')
    error = None

    if request.method == 'POST':
        try:
            venta = pagos.crear_venta_presencial(_items_del_formulario(request.POST), canal, metodo_pago)
        except ValueError as e:
            error = str(e)
        else:
            return redirect(f"{reverse('detalle_venta', args=[venta.id])}?msg=registrada")

    return render(request, 'admin_panel/registrar_venta.html', {
        'canales': [(valor, nombre) for valor, nombre in Venta.CANALES if valor in pagos.CANALES_PRESENCIALES],
        'medios_pago': [
            (valor, nombre) for valor, nombre in Venta.METODOS_PAGO if valor in pagos.MEDIOS_PAGO_PRESENCIALES
        ],
        'canal': canal,
        'metodo_pago': metodo_pago,
        'error': error,
        'items_ingresados': _filas_ingresadas(request.POST) if error else [],
    })
