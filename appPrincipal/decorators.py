import logging

from django.shortcuts import redirect
from appPrincipal.models import Usuario

logger = logging.getLogger(__name__)

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            logger.debug("Sesión no encontrada, redirigiendo al login.")
            return redirect('login')

        usuario = Usuario.objects.filter(id=usuario_id, es_administrador=True).first()
        if not usuario:
            logger.warning("Acceso denegado al panel: usuario %s no es administrador.", usuario_id)
            return redirect('login')

        return view_func(request, *args, **kwargs)
    return wrapper
