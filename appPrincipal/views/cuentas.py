"""Inicio de sesión, registro y cierre de sesión."""
import logging

from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from appPrincipal import forms
from appPrincipal.forms import regiones_ciudades
from appPrincipal.models import Usuario
from appPrincipal.seguridad import MENSAJE_LOGIN_INVALIDO

logger = logging.getLogger(__name__)


def _redirigir_tras_login(request, usuario):
    siguiente = request.POST.get('next') or request.GET.get('next')
    if siguiente and url_has_allowed_host_and_scheme(
        siguiente, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(siguiente)
    return redirect('admin_dashboard' if usuario.is_staff else 'home')


def login(request):
    if request.user.is_authenticated:
        return _redirigir_tras_login(request, request.user)

    errors = {}
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        contraseña = request.POST.get('contraseña', '')

        if not email:
            errors['email'] = "Por favor, ingresa tu correo electrónico."
        if not contraseña:
            errors['contraseña'] = "Por favor, ingresa tu contraseña."

        if not errors:
            # authenticate rechaza usuarios inactivos (eliminados) y django-axes cuenta los intentos fallidos
            usuario = authenticate(request, username=email, password=contraseña)
            if usuario is None:
                # mismo mensaje si el correo no existe o la contraseña es incorrecta
                errors['email'] = MENSAJE_LOGIN_INVALIDO
            else:
                # auth_login cambia la llave de sesión (evita fijación de sesión)
                auth_login(request, usuario)
                logger.info("Inicio de sesión: usuario %s (admin=%s)", usuario.pk, usuario.is_staff)
                return _redirigir_tras_login(request, usuario)

    return render(request, 'login.html', {'errors': errors})


def register(request):
    form = forms.UsuarioCustomForm()
    if request.method == 'POST':
        form = forms.UsuarioCustomForm(request.POST)
        region_seleccionada = request.POST.get('region')
        ciudades = regiones_ciudades.get(region_seleccionada, [])
        form.fields['ciudad'].choices = [(ciudad, ciudad) for ciudad in ciudades]

        if form.is_valid():
            email = form.cleaned_data['email']
            rut = form.cleaned_data['rut']

            usuario_email = Usuario.objects.filter(email=email).first()
            if usuario_email:
                if usuario_email.is_deleted:
                    return JsonResponse({
                        'success': False,
                        'message': 'Este correo ya fue utilizado previamente (usuario eliminado). No puede volver a registrarse con el mismo correo.'
                    })
                return JsonResponse({
                    'success': False,
                    'message': 'El correo ya está registrado.'
                })

            usuario_rut = Usuario.objects.filter(rut=rut).first()
            if usuario_rut:
                if usuario_rut.is_deleted:
                    return JsonResponse({
                        'success': False,
                        'message': 'Este RUT pertenece a un usuario eliminado. No puede volver a usarse.'
                    })
                return JsonResponse({
                    'success': False,
                    'message': 'El RUT ya está registrado.'
                })
            try:
                Usuario.objects.create_user(
                    email=email,
                    password=form.cleaned_data['contraseña'],
                    rut=rut,
                    nombre=form.cleaned_data['nombre'],
                    telefono=form.cleaned_data['telefono'],
                    direccion=form.cleaned_data['direccion'],
                    ciudad=form.cleaned_data['ciudad'],
                    region=form.cleaned_data['region'],
                )
                return JsonResponse({'success': True, 'message': 'Usuario registrado exitosamente.'})

            except IntegrityError as e:
                if 'email' in str(e):
                    return JsonResponse({'success': False, 'message': 'El correo ya está registrado.'})
                elif 'rut' in str(e):
                    return JsonResponse({'success': False, 'message': 'El RUT ya está registrado.'})
                return JsonResponse({'success': False, 'message': 'Error inesperado.'})
        else:
            logger.debug("Registro inválido: %s", form.errors.as_json())
            primer_error = next(iter(form.errors.values()))[0]
            return JsonResponse({'success': False, 'message': primer_error})
    data = {'form': form, 'regiones_ciudades': regiones_ciudades}
    return render(request, 'register.html', data)

def logout(request):
    auth_logout(request)
    return redirect('login')

def obtener_ciudades(request):
    region = request.GET.get('region')
    ciudades = regiones_ciudades.get(region, [])
    return JsonResponse({'ciudades': ciudades})
