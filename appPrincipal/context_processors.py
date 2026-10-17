from django.urls import reverse
from django.utils.functional import SimpleLazyObject

from appPrincipal.constants import MENU_NAVBAR
from appPrincipal.models import Categoria, ConfiguracionSitio, Destacado


def usuario_context(request):
    usuario = request.user if request.user.is_authenticated else None
    return {'usuario': usuario}

# Contenido de portada que el admin edita en el panel (modelo Destacado).
class Portada:

    def __init__(self):
        self._por_seccion = None

    def _cargar(self):
        if self._por_seccion is None:
            self._por_seccion = {}
            activos = Destacado.objects.filter(activo=True).select_related('producto').prefetch_related(
                'producto__imagenes_producto')
            for destacado in activos:
                self._por_seccion.setdefault(destacado.seccion, []).append(destacado)
        return self._por_seccion

    def __getattr__(self, seccion):
        if seccion not in dict(Destacado.SECCIONES):
            raise AttributeError(seccion)
        destacados = self._cargar().get(seccion, [])
        if seccion in Destacado.SECCIONES_DE_UNO:
            return destacados[0] if destacados else None
        return destacados[:Destacado.MAXIMO_VISIBLES.get(seccion)]


def url_categoria(categoria_id, plataforma=None):
    if plataforma:
        return reverse('productos_por_categoria_y_plataforma', args=[categoria_id, plataforma])
    return reverse('productos_por_categoria', args=[categoria_id])


def armar_menu_navbar(portada):
    """Los menús del navbar sin las categorías ocultas (Categoria.visible_en_menu); un grupo o menú
    sin categorías visibles no se muestra."""
    visibles = dict(Categoria.objects.filter(visible_en_menu=True).values_list('nombre', 'id'))
    menus = []
    for menu in MENU_NAVBAR:
        grupos = []
        for nombre, entradas in menu['grupos']:
            enlaces = [(url_categoria(visibles[categoria], plataforma), etiqueta)
                       for categoria, plataforma, etiqueta in entradas if categoria in visibles]
            if enlaces:
                grupos.append({'nombre': nombre, 'enlaces': enlaces})
        if grupos:
            menus.append({**menu, 'grupos': grupos, 'destacado': getattr(portada, menu['promo'])})
    return menus


def portada_context(request):
    """Lo que el admin edita en el panel: la portada (Destacado), las opciones de visualización
    (ConfiguracionSitio) y, a partir de ellas, el menú del navbar. Todo se carga solo si la página lo usa."""
    portada = Portada()
    configuracion = SimpleLazyObject(ConfiguracionSitio.actual)
    return {
        'portada': portada,
        'config_sitio': configuracion,
        'menu_navbar': SimpleLazyObject(lambda: armar_menu_navbar(portada)),
    }
