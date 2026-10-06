"""Checkout: pago con Webpay Plus (HU-05), resultado del pago y boleta.

La lógica del pago está en appPrincipal/pagos.py; aquí solo están las páginas.
"""
import logging
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from appPrincipal import envios, pagos, webpay
from appPrincipal.models import Boleta, Carrito, PagoWebpay, Venta

logger = logging.getLogger(__name__)


def _volver_al_carrito(mensaje):
    return redirect(f"{reverse('ver_carrito')}?{urlencode({'notif': mensaje, 'type': 'error'})}")


@login_required
def seleccionar_pago(request):
    usuario = request.user
    carrito = Carrito.objects.filter(usuario=usuario).first()

    if not carrito or not carrito.items.exists():
        return redirect('ver_carrito')

    # la opción de entrega se elige en el carrito y llega como ?envio=; queda en la sesión
    # para el POST que inicia el pago (que la vuelve a validar)
    if 'envio' in request.GET:
        request.session['metodo_envio'] = request.GET['envio']
    metodo_envio = request.session.get('metodo_envio')
    error_envio = envios.validar_eleccion(metodo_envio, usuario)
    if error_envio:
        return _volver_al_carrito(error_envio)

    # se revisa antes de pagar (el stock pudo bajar desde que se agregó al carrito);
    # al confirmar el pago se vuelve a revisar con las filas bloqueadas
    for item in carrito.items.select_related('producto'):
        if item.producto.is_deleted or item.cantidad > item.producto.stock:
            mensaje = (f"Solo hay {item.producto.stock} unidad(es) disponibles de {item.producto.nombre}. "
                       "Ajusta la cantidad para continuar.")
            if item.producto.is_deleted:
                mensaje = f"{item.producto.nombre} ya no está disponible."
            return _volver_al_carrito(mensaje)

    subtotal = sum(item.cantidad * item.producto.precio for item in carrito.items.all())
    costo_envio = envios.costo_envio(metodo_envio, subtotal)
    total = subtotal + costo_envio
    error = None

    if request.method == 'POST':
        if total <= 0:
            error = "El total de la compra debe ser mayor a $0 para pagar con Webpay."
        else:
            url_retorno = request.build_absolute_uri(reverse('webpay_retorno'))
            try:
                pago, url_webpay = pagos.iniciar_pago(usuario, carrito, metodo_envio, url_retorno)
            except webpay.ErrorWebpay:
                error = "No pudimos conectarnos con Webpay. Inténtalo nuevamente en unos minutos."
            else:
                # Webpay se abre enviando el token por POST a la url que entregó Transbank
                return render(request, 'webpay_redirigir.html', {'url': url_webpay, 'token': pago.token})

    return render(request, 'seleccionar_pago.html', {
        'total': total,
        'subtotal': subtotal,
        'costo_envio': costo_envio,
        'total_items': sum(item.cantidad for item in carrito.items.all()),
        'metodo_envio': metodo_envio,
        'opcion_envio': envios.OPCIONES_ENVIO[metodo_envio],
        'direccion_entrega': envios.direccion_de_entrega(metodo_envio, usuario),
        'error': error,
        'webpay_integracion': webpay.es_integracion(),
    })


# Transbank devuelve al cliente aquí (por GET o POST, según la versión de su API).
# No pide sesión ni CSRF: si vuelve por POST desde el sitio de Transbank el navegador no
# envía la cookie de sesión. El token es secreto y el pago se valida directo con Transbank;
# después se redirige a resultado_pago, que sí exige que el cliente sea el dueño.
@csrf_exempt
@require_http_methods(['GET', 'POST'])
def webpay_retorno(request):
    datos = request.POST if request.method == 'POST' else request.GET
    token = datos.get('token_ws')
    token_anulado = datos.get('TBK_TOKEN')
    orden_compra = datos.get('TBK_ORDEN_COMPRA')

    pago = None
    if token_anulado:
        # canceló en el formulario de Webpay (o hubo un error ahí y volvió al comercio)
        pago = PagoWebpay.objects.filter(token=token_anulado).first()
        if pago:
            pago = pagos.anular_pago(pago, "Cancelaste el pago en Webpay.")
    elif token:
        pago = pagos.confirmar_pago(token)
    elif orden_compra:
        # se acabó el tiempo para pagar en el formulario de Webpay
        pago = PagoWebpay.objects.filter(orden_compra=orden_compra).first()
        if pago:
            pago = pagos.anular_pago(pago, "Se acabó el tiempo para completar el pago.")

    if pago is None:
        logger.warning("Retorno de Webpay sin un pago conocido: %s", dict(datos))
        return _volver_al_carrito("No encontramos el pago. Si se realizó un cargo, contáctanos.")
    return redirect('resultado_pago', pago_id=pago.id)


@login_required
def resultado_pago(request, pago_id):
    pago = get_object_or_404(PagoWebpay, id=pago_id, usuario=request.user)

    if pago.estado == PagoWebpay.APROBADO:
        request.session.pop('metodo_envio', None)
        venta = pago.venta
        return render(request, 'compra_exitosa.html', {
            'venta': venta,
            'pago': pago,
            'total_cantidad': sum(item.cantidad for item in venta.producto_venta.all()),
        })

    return render(request, 'pago_fallido.html', {'pago': pago})


@login_required
def ver_boleta(request, venta_id):
    # el cliente solo ve sus boletas; el administrador puede ver todas
    ventas = Venta.objects.all() if request.user.is_staff else Venta.objects.filter(usuario=request.user)
    venta = get_object_or_404(ventas, id=venta_id)
    Boleta.objects.get_or_create(venta=venta)

    return render(request, 'boleta.html', {'venta': venta})
