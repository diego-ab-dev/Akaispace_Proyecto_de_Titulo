import logging
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.shortcuts import redirect, render

logger = logging.getLogger(__name__)

MENSAJE_SOLO_CLIENTES = ("Estás en una cuenta de administrador. Las ventas del local se registran "
                         "desde el panel, en «Registrar venta».")

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


def login_required_json(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'not_logged_in'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


# El admin puede recorrer la tienda, pero no compra ni opina como cliente: así sus pruebas no
# descuentan stock ni ensucian los KPI. Van después de login_required / login_required_json.
def solo_clientes(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_staff:
            return render(request, 'solo_clientes.html', status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def solo_clientes_json(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_staff:
            return JsonResponse({'success': False, 'error': MENSAJE_SOLO_CLIENTES}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper
