from appPrincipal.models import Producto


def usuario_context(request):
    # los templates usan {{ usuario }}: es el usuario autenticado, o None si no inició sesión
    usuario = request.user if request.user.is_authenticated else None
    return {'usuario': usuario}


class ProductosDestacados:
    """Productos que se promocionan en el navbar y en el carrusel del menú.

    Se usa en las plantillas como {{ destacados.ps5 }}. Cada producto se consulta
    solo la primera vez que una plantilla lo pide, así las páginas que no muestran
    el navbar (por ejemplo el panel de administración) no hacen consultas extra.
    """
    NOMBRES = {
        'cod6': "Call of Duty: Black Ops 6",
        'fc25': "Fc 25",
        'silent': "Silent Hill 2",
        'ps5': "Play Station 5",
        'mando': "Control Sony Dualsense Chroma Pearl Ps5",
        'funko': "Funko Pop John Wick",
    }

    def __init__(self):
        self._cache = {}

    def __getattr__(self, clave):
        if clave not in self.NOMBRES:
            raise AttributeError(clave)
        if clave not in self._cache:
            self._cache[clave] = Producto.objects.filter(nombre=self.NOMBRES[clave]).first()
        return self._cache[clave]


def destacados_context(request):
    return {'destacados': ProductosDestacados()}
