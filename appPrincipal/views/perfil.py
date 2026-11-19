"""Perfil del cliente."""
from urllib.parse import urlencode

from django.contrib.auth import logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from django.db import IntegrityError

from appPrincipal import correos
from appPrincipal.constants import REGIONES, REGIONES_CIUDADES, RESPONSABLE_DATOS
from appPrincipal.eliminacion_cuenta import CuentaNoEliminable, eliminar_cuenta as eliminar_y_anonimizar
from appPrincipal.eliminacion_cuenta import motivos_para_no_eliminar
from appPrincipal.forms import (DIRECCION_MAXIMA, NOMBRE_MAXIMO, CambiarContraseñaForm, EditarPerfilForm,
                                EliminarCuentaForm)
from appPrincipal.models import Devolucion, Opinion, Reclamo, Venta
from appPrincipal.recomendaciones import cambiar_consentimiento_navegacion


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
@require_POST
def datos_navegacion(request):
    autoriza = request.POST.get('autoriza') == 'on'
    cambiar_consentimiento_navegacion(request.user, autoriza)
    mensaje = ('Activaste las recomendaciones personalizadas.' if autoriza else
               'Desactivaste las recomendaciones personalizadas y eliminamos tu historial de navegación.')
    return redirect(f"{reverse('perfil')}?{urlencode({'notif': mensaje, 'type': 'success'})}")


@login_required
def cambiar_contraseña(request):
    usuario = request.user
    form = CambiarContraseñaForm(usuario=usuario)
    if request.method == 'POST':
        form = CambiarContraseñaForm(request.POST, usuario=usuario)
        if form.is_valid():
            usuario.set_password(form.cleaned_data['nueva_contraseña'])
            usuario.save()
            update_session_auth_hash(request, usuario)
            correos.enviar_contraseña_actualizada(usuario, correos.CAMBIADA)
            aviso = urlencode({'notif': 'Contraseña actualizada correctamente.', 'type': 'success'})
            return redirect(f"{reverse('perfil')}?{aviso}")

    return render(request, 'cambiar_contrausu.html', {
        'form': form,
        'sin_contraseña': not usuario.has_usable_password(),
    })


@login_required
def editar_perfil(request):
    usuario = request.user
    if request.method == 'POST':
        form = EditarPerfilForm(request.POST, usuario=usuario)
        if form.is_valid():
            campos = ['nombre', 'telefono', 'direccion', 'region', 'ciudad']
            if not usuario.rut and form.cleaned_data['rut']:
                campos.append('rut')
            for campo in campos:
                setattr(usuario, campo, form.cleaned_data[campo])
            try:
                usuario.save(update_fields=campos)
            except IntegrityError:
                form.add_error('rut', 'El RUT ya está registrado en otra cuenta.')
            else:
                aviso = urlencode({'notif': 'Tus datos se actualizaron correctamente.', 'type': 'success'})
                return redirect(f"{reverse('perfil')}?{aviso}")
    else:
        form = EditarPerfilForm(usuario=usuario, initial={
            'nombre': usuario.nombre, 'rut': usuario.rut or '',
            'telefono': usuario.telefono[-8:] if usuario.telefono else '',
            'direccion': usuario.direccion, 'region': usuario.region, 'ciudad': usuario.ciudad,
        })

    region = form['region'].value() or ''
    return render(request, 'editar_datos.html', {
        'form': form,
        'regiones': REGIONES,
        'ciudades': REGIONES_CIUDADES.get(region, []),
        'direccion_maxima': DIRECCION_MAXIMA,
        'nombre_maximo': NOMBRE_MAXIMO,
        'rut_guardado': usuario.rut,
        'correo_tienda': RESPONSABLE_DATOS['correo_privacidad'],
    })


@login_required
def eliminar_cuenta(request):
    usuario = request.user
    motivos = motivos_para_no_eliminar(usuario)
    form = EliminarCuentaForm(usuario=usuario)
    if request.method == 'POST' and not motivos:
        form = EliminarCuentaForm(request.POST, usuario=usuario)
        if form.is_valid():
            try:
                eliminar_y_anonimizar(usuario)
            except CuentaNoEliminable as error:
                motivos = error.motivos
            else:
                auth_logout(request)
                return redirect('cuenta_eliminada')

    return render(request, 'eliminar_cuenta.html', {
        'form': form,
        'motivos': motivos,
        'con_contraseña': form.con_contraseña,
        'correo_tienda': RESPONSABLE_DATOS['correo_privacidad'],
    })


def cuenta_eliminada(request):
    return render(request, 'cuenta_eliminada.html')
