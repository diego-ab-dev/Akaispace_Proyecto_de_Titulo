"""Perfil del cliente: resumen, edición de datos y cambio de contraseña."""
from urllib.parse import urlencode

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from appPrincipal.constants import REGIONES_CIUDADES
from appPrincipal.models import Devolucion, Opinion, Reclamo, Venta


@login_required
def perfil(request):
    usuario = request.user
    compras = Venta.objects.filter(usuario=usuario).order_by('-fecha')[:3]
    opiniones = Opinion.objects.filter(usuario=usuario).order_by('-fecha_creacion')[:2]
    reclamos_recientes = Reclamo.objects.filter(usuario=usuario).order_by('-fecha')[:2]
    devoluciones_recientes = Devolucion.objects.filter(usuario=usuario).order_by('-fecha_solicitud')[:2]
    
    return render(request, 'perfil_usuario.html', {
        'usuario': usuario,
        'compras': compras,
        'opiniones': opiniones,
        'reclamos_recientes': reclamos_recientes,
        'devoluciones_recientes': devoluciones_recientes,
    })


@login_required
def cambiar_contraseña(request):
    if request.method == 'POST':
        contraseña_actual = request.POST.get('contraseña_actual', '')
        nueva_contraseña = request.POST.get('nueva_contraseña', '')
        confirmar_contraseña = request.POST.get('confirmar_contraseña', '')
        usuario = request.user
        url_error = reverse('cambiar')

        if not usuario.check_password(contraseña_actual):
            return redirect(f"{url_error}?{urlencode({'notif': 'La contraseña actual no es correcta.', 'type': 'error'})}")

        if nueva_contraseña != confirmar_contraseña:
            return redirect(f"{url_error}?{urlencode({'notif': 'Las contraseñas nuevas no coinciden.', 'type': 'error'})}")

        try:
            validate_password(nueva_contraseña, user=usuario)
        except ValidationError as e:
            return redirect(f"{url_error}?{urlencode({'notif': ' '.join(e.messages), 'type': 'error'})}")

        usuario.set_password(nueva_contraseña)
        usuario.save()
        # mantiene la sesión actual abierta (y cierra las de otros dispositivos)
        update_session_auth_hash(request, usuario)

        return redirect(f"{reverse('perfil')}?{urlencode({'notif': 'Contraseña actualizada correctamente.', 'type': 'success'})}")

    return render(request, 'cambiar_contrausu.html')


@login_required
def editar_perfil(request):
    usuario = request.user

    if request.method == 'POST':
        telefono = request.POST.get('telefono')
        direccion = request.POST.get('direccion')
        region = request.POST.get('region')
        ciudad = request.POST.get('ciudad')

        if region and ciudad not in REGIONES_CIUDADES.get(region, []):
            return JsonResponse({'error': 'La ciudad no coincide con la región seleccionada.'}, status=400)

        usuario.telefono = telefono or usuario.telefono
        usuario.direccion = direccion or usuario.direccion
        usuario.region = region or usuario.region
        usuario.ciudad = ciudad or usuario.ciudad
        usuario.save()

        return JsonResponse({'success': 'Perfil actualizado correctamente.'})

    ciudades = REGIONES_CIUDADES.get(usuario.region, [])
    context = {
        'usuario': usuario,
        'regiones': REGIONES_CIUDADES.keys(),
        'ciudades': ciudades,
    }
    return render(request, 'editar_datos.html', context)

