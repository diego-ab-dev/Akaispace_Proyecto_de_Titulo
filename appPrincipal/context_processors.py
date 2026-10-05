from appPrincipal.models import Destacado


def usuario_context(request):
    # los templates usan {{ usuario }}: es el usuario autenticado, o None si no inició sesión
    usuario = request.user if request.user.is_authenticated else None
    return {'usuario': usuario}


class Portada:
    """Contenido de portada que el admin edita en el panel (modelo Destacado).

    En las plantillas: {{ portada.carrusel }} y {{ portada.lanzamientos }} son listas, y
    {{ portada.menu_consolas }} (y los demás menús del navbar) es un solo destacado o None.
    Se consulta la base de datos solo la primera vez que una plantilla lo usa, y una sola
    vez por página, así las páginas sin navbar (como el panel) no hacen consultas extra.
    """

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
        # el panel no deja pasar el máximo, esto solo cubre datos cargados por otro lado
        return destacados[:Destacado.MAXIMO_VISIBLES.get(seccion)]


def portada_context(request):
    return {'portada': Portada()}
