"""Panel de administración: opciones de visualización de la tienda (HU-09)."""
from datetime import timedelta

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.timezone import now

from appPrincipal.decorators import admin_required
from appPrincipal.forms import ConfiguracionSitioForm
from appPrincipal.models import Categoria, ConfiguracionSitio
from appPrincipal.recomendaciones import cobertura_atributos, tasa_de_clics


@admin_required
def admin_configuracion(request):
    configuracion = ConfiguracionSitio.actual()
    form = ConfiguracionSitioForm(request.POST or None, instance=configuracion)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Configuración guardada. Los cambios ya se ven en la tienda.")
        return redirect('admin_configuracion')

    completos, total = cobertura_atributos()
    return render(request, 'admin_panel/configuracion.html', {
        'form': form,
        'kpi10': {'completos': completos, 'total': total, 'cumple': completos == total},
        'kpi05': tasa_de_clics(desde=now() - timedelta(days=30)),
        'categorias': Categoria.objects.all(),
        'visibles': {int(valor) for valor in form['categorias_visibles'].value() or [] if str(valor).isdigit()},
    })
