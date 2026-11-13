"""Panel de administración: usuarios."""
import logging

from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from appPrincipal.decorators import admin_required
from appPrincipal.constants import REGIONES
from appPrincipal.forms import DIRECCION_MAXIMA, NOMBRE_MAXIMO, CrearUsuarioAdminForm, errores_para_json
from appPrincipal.models import Usuario

logger = logging.getLogger(__name__)


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
    if request.method != 'POST':
        return render(request, 'admin_panel/crear_usuario.html', {
            'regiones': REGIONES,
            'nombre_maximo': NOMBRE_MAXIMO,
            'direccion_maxima': DIRECCION_MAXIMA,
        })

    form = CrearUsuarioAdminForm(request.POST)
    if not form.is_valid():
        return JsonResponse(errores_para_json(form), status=400)

    datos = form.cleaned_data
    try:
        Usuario.objects.create_user(
            email=datos['email'],
            password=datos['contraseña'],
            nombre=datos['nombre'],
            is_staff=datos['es_administrador'],
            telefono=datos['telefono'],
            direccion=datos['direccion'],
            rut=datos['rut'],
            region=datos['region'],
            ciudad=datos['ciudad'],
        )
    except IntegrityError as e:
        campo = 'email' if 'email' in str(e) else 'rut' if 'rut' in str(e) else None
        mensaje = {'email': 'El correo ya está registrado.', 'rut': 'El RUT ya está registrado.'}.get(
            campo, 'No se pudo crear el usuario. Inténtalo de nuevo.')
        return JsonResponse({'success': False, 'message': mensaje, 'errors': {campo or '__all__': [mensaje]}},
                            status=400)
    except Exception:
        logger.exception("Error al crear un usuario desde el panel")
        return JsonResponse({'success': False, 'message': 'Ocurrió un error inesperado. Inténtalo de nuevo.'}, status=500)

    logger.info("Usuario creado desde el panel por %s (admin=%s)", request.user.pk, datos['es_administrador'])
    return JsonResponse({'success': True, 'message': 'Usuario creado exitosamente.', 'redirect': reverse('admin_usuarios')})


@admin_required
def detalle_usuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)
    return render(request, 'admin_panel/detalle_usuario.html', {'usuario': usuario})
