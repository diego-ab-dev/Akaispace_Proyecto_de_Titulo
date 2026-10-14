from django.utils.functional import SimpleLazyObject

from appPrincipal.constants import MENU_NAVBAR
from appPrincipal.models import ConfiguracionSitio, Destacado


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
            activos = Destacado.objects.filter(activo=True).select_related('producto')
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


def armar_menu_navbar(categorias_ocultas, portada):
    """Los menús del navbar sin las categorías ocultas; un grupo o menú sin categorías no se muestra."""
    menus = []
    for menu in MENU_NAVBAR:
        grupos = []
        for nombre, categorias in menu['grupos']:
            visibles = [(codigo, etiqueta) for codigo, etiqueta in categorias if codigo not in categorias_ocultas]
            if visibles:
                grupos.append({'nombre': nombre, 'categorias': visibles})
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
        'menu_navbar': SimpleLazyObject(lambda: armar_menu_navbar(configuracion.categorias_ocultas, portada)),
    }
