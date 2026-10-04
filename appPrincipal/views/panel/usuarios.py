"""Panel de administración: usuarios."""
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from appPrincipal.decorators import admin_required
from appPrincipal.forms import normalizar_rut, regiones_ciudades
from appPrincipal.models import Usuario


@admin_required
def admin_usuarios(request):
    usuarios_list = Usuario.objects.filter(is_deleted=False).order_by('-id')

    paginator = Paginator(usuarios_list, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_panel/usuarios.html', {
        'page_obj': page_obj,
        'usuarios': page_obj.object_list,
    })

@admin_required
@require_POST
def eliminar_usuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)
    if usuario != request.user:
        # eliminación lógica: queda inactivo y ya no puede iniciar sesión
        usuario.delete()
    return redirect('admin_usuarios')


@admin_required
def buscar_usuarios(request):
    query = request.GET.get('q', '').strip()
    filtro = request.GET.get('filtro', 'nombre')
    es_admin = request.GET.get('es_admin', '')

    usuarios_list = Usuario.objects.filter(is_deleted=False)

    if query:
        if filtro == "nombre":
            usuarios_list = usuarios_list.filter(nombre__icontains=query)
        elif filtro == "rut":
            usuarios_list = usuarios_list.filter(rut__icontains=query)

    if es_admin == "True":
        usuarios_list = usuarios_list.filter(is_staff=True)
    elif es_admin == "False":
        usuarios_list = usuarios_list.filter(is_staff=False)

    paginator = Paginator(usuarios_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_panel/usuarios.html', {
        'page_obj': page_obj,
        'usuarios': page_obj.object_list,
    })


@admin_required
def crear_usuario(request):
    if request.method == 'GET':
        return render(request, 'admin_panel/crear_usuario.html', {
            'regiones_ciudades': regiones_ciudades,
        })

    if request.method == 'POST':
        try:
            data = request.POST
            nombre = data.get('nombre')
            email = data.get('email', '').strip().lower()
            contraseña = data.get('contraseña')
            confirmar_contraseña = data.get('confirmar_contraseña')
            telefono = data.get('telefono') 
            direccion = data.get('direccion')
            rut = data.get('rut')
            region = data.get('region')
            ciudad = data.get('ciudad')

            es_administrador = data.get('es_administrador') == 'on'

            if contraseña != confirmar_contraseña:
                return JsonResponse({'success': False, 'message': 'Las contraseñas no coinciden.'})

            try:
                rut = normalizar_rut(rut)
            except ValidationError as e:
                return JsonResponse({'success': False, 'message': e.messages[0]})

            try:
                validate_password(contraseña, user=Usuario(email=email, nombre=nombre))
            except ValidationError as e:
                return JsonResponse({'success': False, 'message': ' '.join(e.messages)})

            ciudades_validas = regiones_ciudades.get(region, [])
            if ciudad not in ciudades_validas:
                return JsonResponse({'success': False, 'message': 'La ciudad no es válida para la región seleccionada.'})

            if Usuario.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'message': 'El correo electrónico ya está registrado.'})

            if Usuario.objects.filter(rut=rut).exists():
                return JsonResponse({'success': False, 'message': 'El RUT ya está registrado.'})

            Usuario.objects.create_user(
                email=email,
                password=contraseña,
                nombre=nombre,
                is_staff=es_administrador,
                telefono=telefono,
                direccion=direccion,
                rut=rut,
                region=region,
                ciudad=ciudad
            )
            
            return JsonResponse({'success': True, 'message': 'Usuario creado exitosamente.'})

        except IntegrityError as e:
            error_msg = 'Error de base de datos.'
            if 'email' in str(e):
                error_msg = 'El email ya existe.'
            elif 'rut' in str(e):
                error_msg = 'El RUT ya existe.'
            return JsonResponse({'success': False, 'message': error_msg})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error del servidor: {str(e)}'})


@admin_required
def detalle_usuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)
    return render(request, 'admin_panel/detalle_usuario.html', {'usuario': usuario})
