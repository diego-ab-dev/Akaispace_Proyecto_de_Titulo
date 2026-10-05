"""Panel de administración: portada del sitio (carrusel, nuevos lanzamientos y promos del navbar)."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from appPrincipal.decorators import admin_required
from appPrincipal.forms import DestacadoForm, mensaje_maximo_visibles
from appPrincipal.models import Destacado


@admin_required
def admin_portada(request):
    destacados = Destacado.objects.select_related('producto')
    secciones = []
    for codigo, nombre in Destacado.SECCIONES:
        de_la_seccion = [d for d in destacados if d.seccion == codigo]
        secciones.append({
            'codigo': codigo,
            'nombre': nombre,
            'de_uno': codigo in Destacado.SECCIONES_DE_UNO,
            'destacados': de_la_seccion,
            'visibles': sum(d.activo for d in de_la_seccion),
            'maximo': Destacado.MAXIMO_VISIBLES.get(codigo),
        })
    return render(request, 'admin_panel/portada.html', {'secciones': secciones})


@admin_required
def crear_destacado(request):
    if request.method == 'POST':
        form = DestacadoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('admin_portada')
    else:
        # desde el botón "Agregar" de cada sección la sección viene elegida
        form = DestacadoForm(initial={'seccion': request.GET.get('seccion')})
    return render(request, 'admin_panel/portada_form.html', {'form': form})


@admin_required
def editar_destacado(request, destacado_id):
    destacado = get_object_or_404(Destacado, id=destacado_id)
    if request.method == 'POST':
        form = DestacadoForm(request.POST, request.FILES, instance=destacado)
        if form.is_valid():
            form.save()
            return redirect('admin_portada')
    else:
        form = DestacadoForm(instance=destacado)
    return render(request, 'admin_panel/portada_form.html', {'form': form, 'destacado': destacado})


@admin_required
@require_POST
def cambiar_estado_destacado(request, destacado_id):
    destacado = get_object_or_404(Destacado, id=destacado_id)
    if not destacado.activo and destacado.supera_maximo_visibles():
        messages.error(request, mensaje_maximo_visibles(destacado.seccion))
        return redirect('admin_portada')
    destacado.activo = not destacado.activo
    destacado.save(update_fields=['activo'])
    return redirect('admin_portada')


@admin_required
@require_POST
def eliminar_destacado(request, destacado_id):
    get_object_or_404(Destacado, id=destacado_id).delete()
    return redirect('admin_portada')
