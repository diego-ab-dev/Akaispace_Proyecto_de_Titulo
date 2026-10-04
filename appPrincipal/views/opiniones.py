"""Opiniones (reseñas) de productos."""
import logging
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from appPrincipal.forms import OpinionForm
from appPrincipal.models import Opinion, Producto, ProductoVenta

logger = logging.getLogger(__name__)


@login_required
def enviar_opinion(request, producto_id):
    usuario_actual = request.user
    producto = get_object_or_404(Producto, id=producto_id)

    # HU-04: solo se puede opinar sobre un producto comprado y ya recibido
    lo_recibio = ProductoVenta.objects.filter(
        venta__usuario=usuario_actual, producto=producto, venta__datos_envio__estado='Entregado'
    ).exists()
    if not lo_recibio:
        aviso = urlencode({'notif': 'Solo puedes opinar sobre productos que compraste y recibiste.', 'type': 'error'})
        return redirect(f"{reverse('perfil')}?{aviso}")

    ya_opino = Opinion.objects.filter(usuario=usuario_actual, producto=producto).exists()

    if ya_opino:
        return render(request, 'ya_opinaste.html', {'producto': producto})

    if request.method == 'POST':
        form = OpinionForm(request.POST)
        if form.is_valid():
            try:
                nueva_opinion = form.save(commit=False)
                nueva_opinion.usuario = usuario_actual
                nueva_opinion.producto = producto
                nueva_opinion.save()
                return redirect('/perfil?notif=Opinión+ingresada+con+éxito&type=success')
            except Exception:
                logger.exception("Error al guardar la opinión del usuario %s", usuario_actual.id)
    else:
        form = OpinionForm()

    return render(request, 'enviar_opinion.html', {
        'form': form,
        'producto': producto
    })

@login_required
def lista_opiniones(request):
    usuario = request.user
    opiniones = Opinion.objects.filter(usuario=usuario).order_by('-fecha_creacion')

    paginator = Paginator(opiniones, 5) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'lista_opiniones.html', {'opiniones': opiniones, 'page_obj': page_obj})
