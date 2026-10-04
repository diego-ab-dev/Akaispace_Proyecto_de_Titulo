import logging
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.shortcuts import redirect

logger = logging.getLogger(__name__)

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        if not request.user.is_staff:
            logger.warning("Acceso denegado al panel: usuario %s no es administrador.", request.user.pk)
            return redirect('home')

        return view_func(request, *args, **kwargs)
    return wrapper


# para vistas llamadas con fetch: si no hay sesión responde JSON en vez de redirigir al login
def login_required_json(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'not_logged_in'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper
