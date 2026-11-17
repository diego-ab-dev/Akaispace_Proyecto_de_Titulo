"""Opiniones (reseñas) de productos."""
import logging
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from appPrincipal.forms import OpinionForm
from appPrincipal.decorators import solo_clientes
from appPrincipal.models import Opinion, Producto, ProductoVenta

logger = logging.getLogger(__name__)

# qué ve un cliente en la sección de opiniones de la ficha (estado_para_opinar)
OPINAR = 'opinar'          # lo recibió o retiró y aún no opina: se le invita a opinar
YA_OPINO = 'ya_opino'      # ya dejó su opinión
EN_CAMINO = 'en_camino'    # lo compró pero todavía no le llega: podrá opinar al recibirlo

# un retiro en tienda ya entregado también queda como 'Entregado' (se muestra como "Retirado")
ENVIO_RECIBIDO = 'Entregado'
ENVIO_ANULADO = 'Anulada'


def compras_del_producto(usuario, producto):
    return ProductoVenta.objects.filter(venta__usuario=usuario, producto=producto)


def lo_recibio(usuario, producto):
    """Regla para opinar: el cliente compró el producto y ya lo recibió o retiró."""
    return compras_del_producto(usuario, producto).filter(venta__datos_envio__estado=ENVIO_RECIBIDO).exists()


def estado_para_opinar(usuario, producto):
    """OPINAR, YA_OPINO, EN_CAMINO o None si no corresponde mostrarle nada (sin sesión, admin o no lo compró)."""
    if not usuario.is_authenticated or usuario.is_staff:
        return None
    if Opinion.objects.filter(usuario=usuario, producto=producto).exists():
        return YA_OPINO
    if lo_recibio(usuario, producto):
        return OPINAR
    en_camino = (compras_del_producto(usuario, producto)
                 .filter(venta__anulada_en__isnull=True, venta__datos_envio__isnull=False)
                 .exclude(venta__datos_envio__estado__in=[ENVIO_RECIBIDO, ENVIO_ANULADO]))
    return EN_CAMINO if en_camino.exists() else None


def _volver_con_aviso(request, url_por_defecto, mensaje, tipo):
    """Redirige a ?next= (si es de este sitio) o a url_por_defecto, mostrando el aviso."""
    siguiente = request.GET.get('next')
    if not (siguiente and url_has_allowed_host_and_scheme(
            siguiente, allowed_hosts={request.get_host()}, require_https=request.is_secure())):
        siguiente = url_por_defecto
    # el aviso va antes del #ancla (p. ej. #seccion-opiniones), si no el navegador lo ignora
    ruta, almohadilla, ancla = siguiente.partition('#')
    separador = '&' if '?' in ruta else '?'
    return redirect(f"{ruta}{separador}{urlencode({'notif': mensaje, 'type': tipo})}{almohadilla}{ancla}")


@login_required
@solo_clientes
def enviar_opinion(request, producto_id):
    usuario_actual = request.user
    producto = get_object_or_404(Producto, id=producto_id)

    # se llega desde Mis compras o desde la ficha del producto (?next=): al terminar se vuelve allá
    if not lo_recibio(usuario_actual, producto):
        return _volver_con_aviso(request, reverse('perfil'),
                                 'Solo puedes opinar sobre productos que compraste y recibiste.', 'error')

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
                return _volver_con_aviso(request, reverse('perfil'), 'Opinión ingresada con éxito', 'success')
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
