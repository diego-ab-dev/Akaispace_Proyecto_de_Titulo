"""Panel de administración: devoluciones."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.timezone import now
from django.views.decorators.http import require_POST

from appPrincipal import correos, reembolsos
from appPrincipal.decorators import admin_required
from appPrincipal.models import Devolucion, ProductoVenta
from appPrincipal.templatetags.custom_filters import formato_chileno
from appPrincipal.views.panel.filtros import filtrar_por_fechas

LARGO_MAXIMO_RESPUESTA = 1000


@admin_required
def admin_devoluciones(request):
    query = request.GET.get('q', '')
    estado = request.GET.get('estado', '')
    devoluciones = Devolucion.objects.select_related('usuario', 'producto').all().order_by('-fecha_solicitud')

    if query:
        devoluciones = devoluciones.filter(
            Q(usuario__nombre__icontains=query) |
            Q(producto__nombre__icontains=query) |
            Q(id__icontains=query)
        )

    if estado:
        devoluciones = devoluciones.filter(estado=estado)

    devoluciones, errores = filtrar_por_fechas(request, devoluciones, 'fecha_solicitud')

    paginator = Paginator(devoluciones, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_panel/devoluciones.html', {
        'devoluciones': page_obj,
        'page_obj': page_obj,
        'errores': errores,
        'hoy': timezone.localdate(),
    })


@admin_required
def responder_devolucion(request, devolucion_id):
    devolucion = get_object_or_404(Devolucion, id=devolucion_id)

    if devolucion.estado != 'Pendiente':
        return redirect('detalle_devolucion', devolucion_id=devolucion.id)

    item_venta = ProductoVenta.objects.filter(venta=devolucion.venta, producto=devolucion.producto).first()
    monto_a_reembolsar = item_venta.precio_unitario * devolucion.cantidad if item_venta else 0

    error = None
    accion = None
    respuesta = ''

    if request.method == 'POST':
        accion = request.POST.get('accion')
        respuesta = request.POST.get('respuesta', '').strip()

        if accion not in ('aceptar', 'rechazar'):
            error = "Elige si apruebas o rechazas la devolución."
        elif not respuesta:
            error = "Escribe una respuesta para el cliente: se le enviará por correo."
        elif len(respuesta) > LARGO_MAXIMO_RESPUESTA:
            error = f"La respuesta no puede superar los {LARGO_MAXIMO_RESPUESTA} caracteres."

    if request.method == 'POST' and not error:
        with transaction.atomic():
            devolucion = Devolucion.objects.select_for_update().get(id=devolucion.id)
            if devolucion.estado != 'Pendiente':
                return redirect('detalle_devolucion', devolucion_id=devolucion.id)

            # aprobar solo avisa al cliente cómo entregar o enviar el producto: el stock y el reembolso
            # se procesan cuando el administrador registra la recepción
            devolucion.estado = 'Aprobada' if accion == 'aceptar' else 'Rechazada'
            devolucion.respuesta_admin = respuesta
            devolucion.fecha_resolucion = now()
            devolucion.save()

            # el aviso al cliente sale solo si la resolución quedó guardada
            transaction.on_commit(lambda: correos.enviar_resolucion_devolucion(devolucion))

        if devolucion.estado == 'Aprobada':
            messages.success(request, f"Devolución Nº {devolucion.id} aprobada. Cuando recibas e inspecciones el "
                                      "producto, usa \"Registrar recepción\" para reponer el stock y reembolsar.")
        return redirect('admin_devoluciones')

    return render(request, 'admin_panel/responder_devolucion.html', {
        'devolucion': devolucion,
        'monto_a_reembolsar': monto_a_reembolsar,
        'error': error,
        'accion': accion,
        'respuesta': respuesta,
        'largo_maximo_respuesta': LARGO_MAXIMO_RESPUESTA,
    })


@admin_required
def detalle_devolucion(request, devolucion_id):
    devolucion = get_object_or_404(Devolucion, id=devolucion_id)
    return render(request, 'admin_panel/detalle_devolucion.html', {
        'devolucion': devolucion,
        'estado_reembolso': reembolsos.estado_reembolso(devolucion),
        'reembolso_pendiente': reembolsos.reembolso_pendiente(devolucion),
    })


def _mensaje_recepcion(request, devolucion, reembolso):
    inicio = f"Recepción de la devolución Nº {devolucion.id} registrada y stock repuesto."
    if reembolso is None:
        messages.success(request, inicio)
    elif reembolso.realizado and reembolso.guardado:
        messages.success(request, f"{inicio} Se reembolsaron ${formato_chileno(reembolso.monto)} en Webpay.")
    elif reembolso.realizado:
        messages.error(request, f"{inicio} Transbank reembolsó ${formato_chileno(reembolso.monto)}, pero no se pudo "
                                "guardar el registro. No lo reembolses de nuevo en Transbank: anótalo con "
                                "\"Registrar reembolso manual\".")
    else:
        messages.error(request, f"{inicio} El reembolso de ${formato_chileno(reembolso.monto)} NO se hizo en Webpay. "
                                f"{reembolso.motivo} Hazlo a mano en el portal de Transbank y anótalo con "
                                "\"Registrar reembolso manual\".")


@admin_required
@require_POST
def registrar_recepcion_devolucion(request, devolucion_id):
    """Aprobada -> Recibida, después de recibir e inspeccionar el producto."""
    get_object_or_404(Devolucion, id=devolucion_id)
    try:
        devolucion, reembolso = reembolsos.registrar_recepcion(devolucion_id)
    except reembolsos.OperacionNoPermitida as error:
        messages.error(request, str(error))
    else:
        correos.enviar_recepcion_devolucion(devolucion, reembolso)
        _mensaje_recepcion(request, devolucion, reembolso)
    return redirect('detalle_devolucion', devolucion_id=devolucion_id)


@admin_required
@require_POST
def registrar_reembolso_manual(request, devolucion_id):
    """Anota un reembolso que el administrador hizo a mano en el portal de Transbank."""
    get_object_or_404(Devolucion, id=devolucion_id)
    try:
        devolucion = reembolsos.registrar_reembolso_manual(devolucion_id, request.POST.get('monto', ''))
    except (reembolsos.OperacionNoPermitida, ValueError) as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Reembolso manual de ${formato_chileno(devolucion.monto_reembolso)} registrado.")
    return redirect('detalle_devolucion', devolucion_id=devolucion_id)
