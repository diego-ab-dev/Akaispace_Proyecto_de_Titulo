from appPrincipal.models import Destacado


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


def portada_context(request):
    return {'portada': Portada()}
