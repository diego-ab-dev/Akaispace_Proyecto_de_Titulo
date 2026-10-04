"""Panel de administración: reclamos."""
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from appPrincipal.decorators import admin_required
from appPrincipal.models import Reclamo
from appPrincipal.views.panel.filtros import filtrar_por_fechas


@admin_required
def admin_reclamos(request):
    query = request.GET.get('q', '')
    estado = request.GET.get('estado', '')
    reclamos = Reclamo.objects.select_related('usuario').order_by('-fecha')

    if query:
        reclamos = reclamos.filter(
            Q(usuario__nombre__icontains=query) |
            Q(asunto__icontains=query) |
            Q(id__icontains=query)
        )

    if estado:
        reclamos = reclamos.filter(estado=estado)

    reclamos, errores = filtrar_por_fechas(request, reclamos, 'fecha')

    paginator = Paginator(reclamos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_panel/reclamos.html', {
        'reclamos': page_obj,
        'page_obj': page_obj,
        'estado_seleccionado': estado,
        'errores': errores,
    })


@admin_required
def responder_reclamo(request, reclamo_id):
    reclamo = get_object_or_404(Reclamo, id=reclamo_id)
    if request.method == 'POST':
        respuesta = request.POST.get('respuesta')
        reclamo.respuesta = respuesta
        reclamo.estado = 'Respondido'
        reclamo.fecha_respuesta = timezone.now()
        reclamo.save()
        return redirect('admin_reclamos')
    return render(request, 'admin_panel/responder_reclamo.html', {'reclamo': reclamo})


@admin_required
def detalle_reclamo(request, reclamo_id):
    reclamo = get_object_or_404(Reclamo, id=reclamo_id)
    
    context = {
        'reclamo': reclamo
    }
    return render(request, 'admin_panel/detalle_reclamo.html', context)
