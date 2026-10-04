import calendar
import json
import logging
import re
from datetime import datetime, date
from urllib.parse import urlencode

from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Avg, Q, Sum
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.timezone import now
from django.views.decorators.http import require_http_methods

from appPrincipal import forms
from appPrincipal.decorators import admin_required, login_required_json
from .forms import ProductoForm, SolicitudDevolucionForm, OpinionForm, normalizar_rut, regiones_ciudades
from .seguridad import MENSAJE_LOGIN_INVALIDO
from .models import Producto, ItemCarritoProducto, Usuario, Carrito, Venta, ProductoVenta, Opinion, Favorito, Reclamo, Devolucion, Boleta, Envio

logger = logging.getLogger(__name__)

# Vistas para administracion

# dashboard principal administracion
@admin_required
def admin_dashboard(request):
    ultimas_ventas = Venta.objects.prefetch_related('producto_venta__producto').order_by('-fecha')[:4]
    ventas_info = [
        {
            "usuario": venta.usuario.nombre,
            "productos": [
                f"{pv.producto.nombre} (x{pv.cantidad})" for pv in venta.producto_venta.all()
            ],
            "fecha": venta.fecha,
        }
        for venta in ultimas_ventas
    ]
    ultimos_reclamos = Reclamo.objects.select_related('usuario').order_by('-fecha')[:4]
    reclamos_info = [
        {
            "usuario": reclamo.usuario.nombre,
            "asunto": reclamo.asunto,
            "fecha": reclamo.fecha,
        }
        for reclamo in ultimos_reclamos
    ]
    
    productos_bajo_stock = Producto.objects.filter(stock__lt=5).order_by('stock')[:4]
    productos_info = [
        {
            "nombre": producto.nombre,
            "stock": producto.stock,
        }
        for producto in productos_bajo_stock
    ]

    anio_actual = datetime.now().year
    datos_grafico = []

    for mes in range(1, 13):
        ultimo_dia = calendar.monthrange(anio_actual, mes)[1]
        
        fecha_inicio = f"{anio_actual}-{mes:02d}-01"
        fecha_fin = f"{anio_actual}-{mes:02d}-{ultimo_dia}"

        total_mes = Venta.objects.filter(
            fecha__range=[fecha_inicio + " 00:00:00", fecha_fin + " 23:59:59"]
        ).aggregate(Sum('total'))['total__sum'] or 0
        
        datos_grafico.append(total_mes)


    context = {
        "ventas_info": ventas_info,
        "reclamos_info": reclamos_info,
        "productos_info": productos_info,
        "datos_grafico": datos_grafico,
    }
    return render(request, 'admin_panel/dashboard.html', context)


@admin_required
def get_dashboard_counts(request):
    envios_pendientes = Envio.objects.filter(estado="En Preparación").count()
    ventas = Venta.objects.count()
    reclamos = Reclamo.objects.count()
    devoluciones = Devolucion.objects.count()

    return JsonResponse({
        "envios_pendientes": envios_pendientes,
        "ventas": ventas,
        "reclamos": reclamos,
        "devoluciones": devoluciones,
    })
# fin 

# Usuarios en administracion
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
# fin


# Productos en adminstracion
@admin_required
def admin_productos(request):
    query = request.GET.get('q', '')
    categoria = request.GET.get('categoria', '')
    genero = request.GET.get('genero', '')
    ordenar = request.GET.get('ordenar', 'recientes')

    productos_list = Producto.objects.filter(is_deleted=False)

    if query:
        productos_list = productos_list.filter(
            Q(nombre__icontains=query) | Q(codigo_de_barra__icontains=query)
        )

    if categoria:
        productos_list = productos_list.filter(categoria=categoria)

    if genero:
        productos_list = productos_list.filter(genero=genero)

    if ordenar == 'recientes':
        productos_list = productos_list.order_by('-id')
    elif ordenar == 'antiguos':
        productos_list = productos_list.order_by('id')
    elif ordenar == 'menor_precio':
        productos_list = productos_list.order_by('precio')
    elif ordenar == 'mayor_precio':
        productos_list = productos_list.order_by('-precio')

    categorias = []
    for grupo in Producto.CATEGORIAS:
        for cat in grupo[1]:
            categorias.append(cat)
    generos = Producto.GENEROS

    paginator = Paginator(productos_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    mensaje = ""
    if (query or categoria or genero) and page_obj.paginator.count == 0:
        mensaje = "No se encontraron resultados para tu búsqueda."

    return render(request, 'admin_panel/productos.html', {
        'productos': page_obj.object_list,
        'page_obj': page_obj,
        'actual_url': request.path, 
        'query': query,
        'categoria': categoria,
        'genero': genero,
        'ordenar': ordenar,
        'categorias': categorias,
        'generos': generos,
        'mensaje': mensaje
    })

@admin_required
def agregar_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        
        if form.is_valid():
            form.save()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            
            return redirect('admin_productos')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = ProductoForm()
    
    return render(request, 'admin_panel/agregar_producto.html', {'form': form})

@admin_required
def eliminar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    producto.is_deleted = True
    producto.save()
    return redirect('admin_productos')


@admin_required
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        
        if form.is_valid():
            form.save()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            
            return redirect('admin_productos')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)            
    else:
        form = ProductoForm(instance=producto) 
    return render(request, 'admin_panel/editar_producto.html', {'form': form, 'producto': producto})


@admin_required
def detalle_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    return render(request, 'admin_panel/detalle_producto.html', {'producto': producto})
# fin


# devoluciones en administracion
@admin_required
def admin_devoluciones(request):
    query = request.GET.get('q', '')
    estado = request.GET.get('estado', '')
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')

    errores = []
    hoy = date.today()

    devoluciones = Devolucion.objects.select_related('usuario', 'producto').all().order_by('-fecha_solicitud')

    if query:
        devoluciones = devoluciones.filter(
            Q(usuario__nombre__icontains=query) |
            Q(producto__nombre__icontains=query) |
            Q(id__icontains=query)
        )

    if estado:
        devoluciones = devoluciones.filter(estado=estado)

    fecha_inicio_obj = parse_date(fecha_inicio) if fecha_inicio else None
    fecha_fin_obj = parse_date(fecha_fin) if fecha_fin else None

    if fecha_inicio_obj and fecha_inicio_obj > hoy:
        errores.append("La fecha de inicio no puede ser futura.")
        fecha_inicio_obj = None

    if fecha_fin_obj and fecha_fin_obj > hoy:
        errores.append("La fecha fin no puede ser futura.")
        fecha_fin_obj = None

    if fecha_inicio_obj and fecha_fin_obj and fecha_inicio_obj > fecha_fin_obj:
        errores.append("La fecha de inicio no puede ser mayor que la fecha fin.")
        fecha_inicio_obj = None
        fecha_fin_obj = None

    if fecha_inicio_obj:
        devoluciones = devoluciones.filter(fecha_solicitud__gte=fecha_inicio_obj)

    if fecha_fin_obj:
        devoluciones = devoluciones.filter(fecha_solicitud__lte=fecha_fin_obj)

    paginator = Paginator(devoluciones, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_panel/devoluciones.html', {
        'devoluciones': page_obj,
        'page_obj': page_obj,
        'errores': errores,
        'hoy': hoy,
    })


@admin_required
def responder_devolucion(request, devolucion_id):
    devolucion = get_object_or_404(Devolucion, id=devolucion_id)
    
    monto_a_reembolsar = 0
    try:
        item_venta = ProductoVenta.objects.get(
            venta=devolucion.venta, 
            producto=devolucion.producto
        )
        monto_a_reembolsar = item_venta.precio_unitario * devolucion.cantidad
    except ProductoVenta.DoesNotExist:
        monto_a_reembolsar = 0


    if request.method == 'POST':
        accion = request.POST.get('accion') 
        respuesta = request.POST.get('respuesta')
        
        if accion == 'aceptar':
            try:
                item_venta = ProductoVenta.objects.get(
                    venta=devolucion.venta, 
                    producto=devolucion.producto
                )
                
                producto = devolucion.producto
                producto.stock += devolucion.cantidad
                producto.save()
                
                devolucion.estado = 'Aprobada'

            except ProductoVenta.DoesNotExist:
                devolucion.estado = 'Aprobada'

        elif accion == 'rechazar':
            devolucion.estado = 'Rechazada'
            
        devolucion.respuesta_admin = respuesta
        devolucion.fecha_resolucion = now()
        devolucion.save()
        
        return redirect('admin_devoluciones')

    return render(request, 'admin_panel/responder_devolucion.html', {
        'devolucion': devolucion,
        'monto_a_reembolsar': monto_a_reembolsar 
    })

@admin_required
def detalle_devolucion(request, devolucion_id):
    devolucion = get_object_or_404(Devolucion, id=devolucion_id)
    return render(request, 'admin_panel/detalle_devolucion.html', {
        'devolucion': devolucion
    })
#fin


# reclamos en administracion
@admin_required
def admin_reclamos(request):
    query = request.GET.get('q', '')
    estado = request.GET.get('estado', '')
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')

    errores = []
    hoy = date.today()

    reclamos = Reclamo.objects.select_related('usuario').order_by('-fecha')

    if query:
        reclamos = reclamos.filter(
            Q(usuario__nombre__icontains=query) |
            Q(asunto__icontains=query) |
            Q(id__icontains=query)
        )

    if estado:
        reclamos = reclamos.filter(estado=estado)

    fecha_inicio_obj = parse_date(fecha_inicio) if fecha_inicio else None
    fecha_fin_obj = parse_date(fecha_fin) if fecha_fin else None

    if fecha_inicio_obj and fecha_inicio_obj > hoy:
        errores.append("La fecha de inicio no puede ser futura.")
        fecha_inicio_obj = None

    if fecha_fin_obj and fecha_fin_obj > hoy:
        errores.append("La fecha fin no puede ser futura.")
        fecha_fin_obj = None

    if fecha_inicio_obj and fecha_fin_obj and fecha_inicio_obj > fecha_fin_obj:
        errores.append("La fecha de inicio no puede ser mayor que la fecha fin.")
        fecha_inicio_obj = None
        fecha_fin_obj = None

    if fecha_inicio_obj:
        reclamos = reclamos.filter(fecha__gte=fecha_inicio_obj)

    if fecha_fin_obj:
        reclamos = reclamos.filter(fecha__lte=fecha_fin_obj)

    paginator = Paginator(reclamos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_panel/reclamos.html', {
        'reclamos': page_obj,
        'page_obj': page_obj,
        'estado_seleccionado': estado,
        'errores': errores,
    })


@admin_required
def responder_reclamo(request, reclamo_id):
    reclamo = get_object_or_404(Reclamo, id=reclamo_id)
    if request.method == 'POST':
        respuesta = request.POST.get('respuesta')
        reclamo.respuesta = respuesta
        reclamo.estado = 'Respondido'
        reclamo.fecha_respuesta = timezone.now()
        reclamo.save()
        return redirect('admin_reclamos')
    return render(request, 'admin_panel/responder_reclamo.html', {'reclamo': reclamo})


@admin_required
def detalle_reclamo(request, reclamo_id):
    reclamo = get_object_or_404(Reclamo, id=reclamo_id)
    
    context = {
        'reclamo': reclamo
    }
    return render(request, 'admin_panel/detalle_reclamo.html', context)
# fin


# ventas en administracion
@admin_required
def admin_ventas(request):
    query = request.GET.get('q', '')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    ordenar = request.GET.get('ordenar')

    ventas_list = Venta.objects.select_related(
        'usuario'
    ).prefetch_related(
        'producto_venta__producto'
    ).all()

    if query:
        ventas_list = ventas_list.filter(
            Q(usuario__nombre__icontains=query) | Q(id__icontains=query)
        )


    hoy = date.today()
    errores = []

    fecha_inicio_obj = parse_date(fecha_inicio) if fecha_inicio else None
    fecha_fin_obj = parse_date(fecha_fin) if fecha_fin else None

    if fecha_inicio_obj and fecha_inicio_obj > hoy:
        errores.append("La fecha de inicio no puede ser futura.")
        fecha_inicio_obj = None

    if fecha_fin_obj and fecha_fin_obj > hoy:
        errores.append("La fecha de fin no puede ser futura.")
        fecha_fin_obj = None

    if fecha_inicio_obj and fecha_fin_obj and fecha_inicio_obj > fecha_fin_obj:
        errores.append("La fecha de inicio no puede ser mayor que la fecha fin.")
        fecha_inicio_obj = None
        fecha_fin_obj = None

    if fecha_inicio_obj:
        ventas_list = ventas_list.filter(fecha__gte=fecha_inicio_obj)

    if fecha_fin_obj:
        ventas_list = ventas_list.filter(fecha__lte=fecha_fin_obj)

    if ordenar == "antiguas":
        ventas_list = ventas_list.order_by("fecha")
    else:
        ventas_list = ventas_list.order_by("-fecha")

    paginator = Paginator(ventas_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_panel/ventas.html', {
        'ventas': page_obj.object_list,
        'page_obj': page_obj,
        'hoy': hoy,
        'errores': errores,   
    })


@admin_required
def admin_cambiar_estado_venta(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in dict(Venta.ESTADO_CHOICES):
            venta.estado = nuevo_estado
            venta.save()
        else:
            return redirect(f"{reverse('admin_ventas')}?msg=estado_invalido")


@admin_required
def detalle_venta(request, venta_id):
    venta = get_object_or_404(Venta.objects.prefetch_related('producto_venta__producto'), id=venta_id)
    return render(request, 'admin_panel/detalle_venta.html', {'venta': venta})

@admin_required
def modificar_venta(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    envio = getattr(venta, 'datos_envio', None)

    error = None
    estado_post = None
    tracking_post = None
    transportista_post = None 

    if request.method == 'POST':
        estado_post = request.POST.get('estado')
        tracking_post = request.POST.get('numero_seguimiento', '').strip()
        transportista_post = request.POST.get('transportista') 

        estados_con_tracking = ["Enviado", "En Tránsito", "En Reparto"]

        if estado_post in estados_con_tracking and not tracking_post:
            error = "Debe ingresar un número de seguimiento para este estado."

        if not error and tracking_post:
            if not re.match(r'^[A-Za-z0-9]{5,20}$', tracking_post):
                error = "Número de seguimiento inválido. Solo letras y números (5–20 caracteres)."
            elif Envio.objects.filter(numero_seguimiento=tracking_post).exclude(id=envio.id if envio else None).exists():
                error = f"Error: El número '{tracking_post}' ya fue asignado a otro pedido anteriormente."
        
        if error:
            return render(request, 'admin_panel/modificar_venta.html', {
                'venta': venta,
                'envio': envio,
                'error': error,
                'estado_post': estado_post,
                'tracking_post': tracking_post,
                'transportista_post': transportista_post, 
            })

        if envio:
            envio.numero_seguimiento = tracking_post
            # 2. Guardamos el transportista
            if transportista_post: 
                envio.transportista = transportista_post
            
            envio.guardar_estado(estado_post)
        else:
            venta.estado = estado_post

        venta.save()
        return redirect('detalle_venta', venta_id=venta.id)

    return render(request, 'admin_panel/modificar_venta.html', {
        'venta': venta,
        'envio': envio,
        'error': error,
    })


@admin_required
def anular_venta(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    envio = venta.datos_envio

    envio.estado = "Anulada"
    envio.save()

    for item in venta.producto_venta.all():
        producto = item.producto
        producto.stock += item.cantidad
        producto.save()

    return redirect(f"{reverse('detalle_venta', args=[venta_id])}?msg=anulada")
#fin


# vistas del cliente

# vistas relacionadas a home y menu
def home(request):
    return render(request, 'home.html')

def productos_menu(request):
    query = request.GET.get('buscar')
    orden = request.GET.get('orden') 

    if query:
        productos = Producto.objects.filter(
            nombre__icontains=query,
            stock__gt=0,
            is_deleted=False
        )
    else:
        productos = Producto.objects.filter(
            stock__gt=0,
            is_deleted=False
        )

    if orden == 'precio_asc':
        productos = productos.order_by('precio')
    elif orden == 'precio_desc':
        productos = productos.order_by('-precio')
    else:
        productos = productos.order_by('-id')

    favoritos_ids = []
    if request.user.is_authenticated:
        favoritos_ids = Favorito.objects.filter(usuario=request.user).values_list('producto_id', flat=True)

    paginator = Paginator(productos, 16)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    fc25 = Producto.objects.filter(nombre="Fc 25", is_deleted=False).first()
    silent = Producto.objects.filter(nombre="Silent Hill 2", is_deleted=False).first()
    cod6 = Producto.objects.filter(nombre="Call of Duty: Black Ops 6", is_deleted=False).first()

    ps5 = Producto.objects.filter(nombre="Play Station 5", is_deleted=False).first()
    mando = Producto.objects.filter(nombre="Control Sony Dualsense Chroma Pearl Ps5", is_deleted=False).first()
    funko = Producto.objects.filter(nombre="Funko Pop John Wick", is_deleted=False).first()

    template_name = 'resultado_busqueda.html' if query else 'productosmenu.html'
    
    return render(request, template_name, {
        'page_obj': page_obj,
        'productos': page_obj.object_list,
        'fc25': fc25,
        'silent': silent,
        'cod6': cod6,
        'ps5': ps5,
        'mando': mando,
        'funko': funko,
        'favoritos_ids': favoritos_ids,
        'query': query, 
        'orden_actual': orden, 
    })


def producto_detalle(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    rango_cantidad = range(1, producto.stock + 1)

    opiniones_list = producto.opiniones.all().order_by('-fecha_creacion')

    paginator = Paginator(opiniones_list, 5) 
    page_number = request.GET.get('page')
    opiniones = paginator.get_page(page_number)

    promedio_puntuacion = opiniones_list.aggregate(avg=Avg('puntuacion'))['avg'] or 0
    promedio_puntuacion = round(promedio_puntuacion, 1)

    full_stars = int(promedio_puntuacion)
    half_star = (promedio_puntuacion - full_stars) >= 0.5
    full_stars_range = range(full_stars)
    empty_stars_range = range(5 - full_stars - (1 if half_star else 0))

    total_opiniones = opiniones_list.count()
    ratings_data = []
    
    for score in range(5, 0, -1):
        count = opiniones_list.filter(puntuacion=score).count()
        percent = (count / total_opiniones * 100) if total_opiniones > 0 else 0
        ratings_data.append({
            "score": score,
            "count": count,
            "percent": round(percent, 1)
        })

    productos_relacionados = Producto.objects.filter(
        categoria=producto.categoria, 
        stock__gt=0,                 
        is_deleted=False           
    ).exclude(id=producto.id).order_by('?')[:4]

    es_favorito = False
    if request.user.is_authenticated:
        es_favorito = Favorito.objects.filter(usuario=request.user, producto=producto).exists()
    
    cod6 = Producto.objects.filter(nombre="Call of Duty: Black Ops 6", is_deleted=False).first()
    ps5 = Producto.objects.filter(nombre="Play Station 5", is_deleted=False).first()
    mando = Producto.objects.filter(nombre="Control Sony Dualsense Chroma Pearl Ps5", is_deleted=False).first()
    funko = Producto.objects.filter(nombre="Funko Pop John Wick", is_deleted=False).first()

    return render(request, "producto_detalle.html", {
        "producto": producto,
        "rango_cantidad": rango_cantidad,
        "opiniones": opiniones, 
        "promedio_puntuacion": promedio_puntuacion,
        "full_stars_range": full_stars_range, 
        "half_star": half_star,
        "empty_stars_range": empty_stars_range,
        "ratings": ratings_data, 
        "total_opiniones": total_opiniones,
        "es_favorito": es_favorito,
        "productos_relacionados": productos_relacionados,
        'cod6': cod6,
        'ps5': ps5,
        'mando': mando,
        'funko': funko,
    })

    
def productos_por_categoria(request, categoria):
    productos = Producto.objects.filter(
        categoria=categoria,
        is_deleted=False,
        stock__gt=0
    )

    orden = request.GET.get('orden')
    
    if orden == 'precio_asc':
        productos = productos.order_by('precio')
    elif orden == 'precio_desc':
        productos = productos.order_by('-precio')
    else:
        productos = productos.order_by('-id')

    favoritos_ids = []
    if request.user.is_authenticated:
        favoritos_ids = Favorito.objects.filter(
            usuario=request.user
        ).values_list('producto_id', flat=True)

    paginator = Paginator(productos, 16)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    nombre_categoria = dict(Producto.CATEGORIAS).get(categoria, categoria)

    cod6 = Producto.objects.filter(nombre="Call of Duty: Black Ops 6", is_deleted=False).first()
    ps5 = Producto.objects.filter(nombre="Play Station 5", is_deleted=False).first()
    mando = Producto.objects.filter(nombre="Control Sony Dualsense Chroma Pearl Ps5", is_deleted=False).first()
    funko = Producto.objects.filter(nombre="Funko Pop John Wick", is_deleted=False).first()

    context = {
        'categoria': nombre_categoria,
        'categoria_cod': categoria,  
        'favoritos_ids': favoritos_ids,
        'page_obj': page_obj,
        'productos': page_obj.object_list,
        'orden_actual': orden,
        'cod6': cod6,
        'ps5': ps5,
        'mando': mando,
        'funko': funko,
    }
    return render(request, 'productos_por_categoria.html', context)
# fin de vistas relacionadas a home y menu


# Vistas relacionadas a los inicios y registros
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
# Fin de Vistas relacionadas a los inicios y registros


# vistas sobre el perfil del usuario
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
def ver_compras(request):
    usuario = request.user
    orden = request.GET.get('orden', 'reciente')

    if orden == 'antiguo':
        orden_query = 'fecha'
    else:
        orden_query = '-fecha'

    compras_list = Venta.objects.filter(usuario=usuario).prefetch_related(
        'producto_venta__producto'
    ).order_by(orden_query)

    paginator = Paginator(compras_list, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    for compra in page_obj:
        for producto_venta in compra.producto_venta.all():
            producto = producto_venta.producto
            producto_venta.opinion_enviada = producto.opiniones.filter(usuario=usuario).exists()

    return render(request, 'ver_compras.html', {
        'usuario': usuario,
        'page_obj': page_obj,
        'orden': orden, 
    })


@login_required
def ver_detalle_compra(request, compra_id):
    compra = get_object_or_404(Venta, id=compra_id, usuario=request.user)

    total_cantidad = sum(item.cantidad for item in compra.producto_venta.all())

    devoluciones = Devolucion.objects.filter(venta=compra)
    devoluciones_existentes = {d.producto.id: True for d in devoluciones}

    return render(request, 'detalle_compra.html', {
        'compra': compra,
        'total_cantidad': total_cantidad,
        'devoluciones_existentes': devoluciones_existentes,   
    })


@login_required
def marcar_recibido(request, compra_id):
    compra = get_object_or_404(Venta, id=compra_id, usuario=request.user)

    envio = compra.datos_envio
    base_url = reverse('ver_detalle', kwargs={'compra_id': compra_id})

    if envio.estado not in ["Enviado", "En Tránsito", "En Reparto"]:
        qs = urlencode({'notif': "Aún no puedes marcar como recibido.", 'type': 'error'})
        return redirect(f"{base_url}?{qs}")

    envio.estado = "Entregado"
    envio.fecha_entrega = now()
    envio.save()

    qs = urlencode({'notif': "Pedido marcado como recibido.", 'type': 'success'})
    return redirect(f"{base_url}?{qs}")




@login_required
def enviar_opinion(request, producto_id):
    usuario_actual = request.user
    producto = get_object_or_404(Producto, id=producto_id)

    ya_opino = Opinion.objects.filter(usuario=usuario_actual, producto=producto).exists()

    if ya_opino:
        return render(request, 'ya_opinaste.html', {'producto': producto})

    if request.method == 'POST':
        form = OpinionForm(request.POST)
        if form.is_valid():
            try:
                nueva_opinion = form.save(commit=False)
                nueva_opinion.usuario = usuario_actual
                nueva_opinion.producto = producto
                nueva_opinion.save()
                return redirect('/perfil?notif=Opinión+ingresada+con+éxito&type=success')
            except Exception:
                logger.exception("Error al guardar la opinión del usuario %s", usuario_actual.id)
    else:
        form = OpinionForm()

    return render(request, 'enviar_opinion.html', {
        'form': form,
        'producto': producto
    })

@login_required
def lista_opiniones(request):
    usuario = request.user
    opiniones = Opinion.objects.filter(usuario=usuario).order_by('-fecha_creacion')

    paginator = Paginator(opiniones, 5) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'lista_opiniones.html', {'opiniones': opiniones, 'page_obj': page_obj})




@login_required
def crear_reclamo(request, compra_id):
    usuario = request.user
    compra = get_object_or_404(Venta, id=compra_id, usuario=usuario)

    if request.method == 'POST':
        asunto = request.POST.get('asunto', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()

        MAX_LENGTH_ASUNTO = 50

        if not asunto or not descripcion:
            return render(request, 'crear_reclamo.html', {
                'compra': compra,
                'error': "Todos los campos son obligatorios."
            })
        
        if len(asunto) > MAX_LENGTH_ASUNTO:
            return render(request, 'crear_reclamo.html', {
                'compra': compra,
                'error': f"El Asunto no puede exceder los {MAX_LENGTH_ASUNTO} caracteres."
            })
        
        else:
            Reclamo.objects.create(
                usuario=usuario,
                venta=compra,
                asunto=asunto,
                descripcion=descripcion
            )
            return redirect('/perfil?notif=Reclamo+enviado+con+éxito&type=success')

    return render(request, 'crear_reclamo.html', {
        'compra': compra
    })


@login_required
def lista_reclamos(request):
    usuario = request.user
    todos_reclamos = Reclamo.objects.filter(usuario=usuario).order_by('-id')

    paginator = Paginator(todos_reclamos, 5) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'lista_reclamos.html', {
        'todos_reclamos': todos_reclamos,
        'page_obj': page_obj,
    })

@login_required
def ver_detalle_reclamo(request, reclamo_id):
    usuario = request.user
    
    reclamo = get_object_or_404(Reclamo, id=reclamo_id, usuario=usuario)
    
    return render(request, 'detalle_reclamo.html', {
        'reclamo': reclamo
    })



@login_required
def crear_devolucion(request, compra_id, producto_id):
    usuario = request.user
    compra = get_object_or_404(Venta, id=compra_id, usuario=usuario)
    producto = get_object_or_404(Producto, id=producto_id)

    item = compra.producto_venta.get(producto=producto)
    cantidad_comprada = item.cantidad

    form = SolicitudDevolucionForm()

    if request.method == 'POST':
        form = SolicitudDevolucionForm(request.POST, request.FILES)

        if form.is_valid():
            motivo = form.cleaned_data['descripcion']
            cantidad = form.cleaned_data['cantidad']
            img1 = form.cleaned_data['imagen1']
            img2 = form.cleaned_data['imagen2']
            img3 = form.cleaned_data['imagen3']

            Devolucion.objects.create(
                usuario=usuario,
                venta=compra,
                producto=producto,
                cantidad=cantidad,
                motivo=motivo,
                imagen1=img1,
                imagen2=img2,
                imagen3=img3,
                estado='Pendiente'
            )
            return redirect('/perfil?notif=Solicitud+de+devolución+enviada+con+éxito&type=success')
        
        else:
            pass 

    return render(request, 'crear_devolucion.html', {
        'compra': compra,
        'producto': producto,
        'cantidad_comprada': cantidad_comprada,
        'form': form 
    })

@login_required
def listar_devoluciones(request):
    usuario = request.user
    todos_devoluciones = Devolucion.objects.filter(usuario=usuario).order_by('-id')

    paginator = Paginator(todos_devoluciones, 5) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)


    return render(request, 'lista_devoluciones.html', {
        'todos_devoluciones': todos_devoluciones,
        'page_obj': page_obj,
    })

@login_required
def ver_detalle_devolucion(request, devolucion_id):
    usuario = request.user
    devolucion = get_object_or_404(Devolucion, id=devolucion_id, usuario=usuario)
    
    monto_reembolso = 0
    try:
        item_venta = ProductoVenta.objects.get(
            venta=devolucion.venta, 
            producto=devolucion.producto
        )
        monto_reembolso = item_venta.precio_unitario * devolucion.cantidad
    except ProductoVenta.DoesNotExist:
        monto_reembolso = 0

    return render(request, 'detalle_devolucion.html', {
        'devolucion': devolucion,
        'monto_reembolso': monto_reembolso 
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

        if region and ciudad not in regiones_ciudades.get(region, []):
            return JsonResponse({'error': 'La ciudad no coincide con la región seleccionada.'}, status=400)

        usuario.telefono = telefono or usuario.telefono
        usuario.direccion = direccion or usuario.direccion
        usuario.region = region or usuario.region
        usuario.ciudad = ciudad or usuario.ciudad
        usuario.save()

        return JsonResponse({'success': 'Perfil actualizado correctamente.'})

    ciudades = regiones_ciudades.get(usuario.region, [])
    context = {
        'usuario': usuario,
        'regiones': regiones_ciudades.keys(),
        'ciudades': ciudades,
    }
    return render(request, 'editar_datos.html', context)

# fin de vistas sobre el perfil del usuario


# vistas relacionadas con carrito
@login_required_json
def agregar_al_carrito(request, producto_id):
    usuario = request.user
    carrito, created = Carrito.objects.get_or_create(usuario=usuario)
    producto = get_object_or_404(Producto, id=producto_id)

    cantidad = int(request.POST.get('cantidad', 1))

    item_carrito, item_created = ItemCarritoProducto.objects.get_or_create(
        carrito=carrito, producto=producto
    )

    if item_created:
        if cantidad <= producto.stock:
            item_carrito.cantidad = cantidad
            item_carrito.save()
    else:
        if item_carrito.cantidad + cantidad <= producto.stock:
            item_carrito.cantidad += cantidad
            item_carrito.save()

    carrito_total_items = sum(i.cantidad for i in carrito.items.all())

    return JsonResponse({
        'success': True,
        'message': 'Producto agregado correctamente',
        'total_items': carrito_total_items
    })


@login_required_json
def eliminar_del_carrito(request, item_id):
    if request.method == 'POST':
        try:
            item = get_object_or_404(
                ItemCarritoProducto,
                id=item_id,
                carrito__usuario=request.user
            )

            carrito = item.carrito
            item.delete()

            total_items = sum(i.cantidad for i in carrito.items.all())
            total = carrito.total_carrito()

            return JsonResponse({
                'success': True,
                'total_items': total_items,
                'total': total,
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@login_required_json
def actualizar_cantidad_carrito(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        nueva_cantidad = int(request.POST.get('cantidad', 1))

        item = get_object_or_404(ItemCarritoProducto, id=item_id, carrito__usuario=request.user)
        producto = item.producto

        if nueva_cantidad > producto.stock:
            return JsonResponse({
                'success': False,
                'error': f"Solo hay {producto.stock} unidades disponibles de {producto.nombre}."
            })

        if nueva_cantidad > 0:
            item.cantidad = nueva_cantidad
            item.save()
        else:
            item.delete()

        carrito = item.carrito
        total_items = sum(i.cantidad for i in carrito.items.all())
        total = carrito.total_carrito()

        return JsonResponse({
            'success': True,
            'total': total,
            'total_items': total_items,
        })

    return JsonResponse({'success': False})

@login_required
def ver_carrito(request):
    usuario = request.user

    carrito, creado = Carrito.objects.get_or_create(usuario=usuario)

    items = carrito.items.all()

    for item in items:
        if item.producto.is_deleted:
            item.delete()

    items = carrito.items.all()

    total = sum((item.producto.precio or 0) * item.cantidad for item in items)
    total_items = sum(item.cantidad for item in items)

    cod6 = Producto.objects.filter(nombre="Call of Duty: Black Ops 6", is_deleted=False).first()
    ps5 = Producto.objects.filter(nombre="Play Station 5", is_deleted=False).first()
    mando = Producto.objects.filter(nombre="Control Sony Dualsense Chroma Pearl Ps5", is_deleted=False).first()
    funko = Producto.objects.filter(nombre="Funko Pop John Wick", is_deleted=False).first()

    return render(request, "carrito.html", {
        "productos": items,
        "total": total,
        "total_items": total_items,
        'cod6': cod6,
        'ps5': ps5,
        'mando': mando,
        'funko': funko,
    })


@login_required_json
def guardar_datos_envio(request):
    if request.method == "POST":
        usuario = request.user

        region = request.POST.get("region")
        ciudad = request.POST.get("ciudad")
        direccion = request.POST.get("direccion")

        usuario.region = region
        usuario.ciudad = ciudad
        usuario.direccion = direccion
        usuario.save()

        return JsonResponse({
            'success': True,
            'region': region,
            'ciudad': ciudad,
            'direccion': direccion,
        })

    return JsonResponse({'success': False}, status=400)
# fin de vistas relacionadas con carrito


# vistas de los favoritos
@login_required
def lista_favoritos(request):
    usuario = request.user

    favoritos = Favorito.objects.filter(
        usuario=usuario,
        producto__is_deleted=False
    )

    Favorito.objects.filter(
        usuario=usuario,
        producto__is_deleted=True
    ).delete()

    paginator = Paginator(favoritos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    cod6 = Producto.objects.filter(nombre="Call of Duty: Black Ops 6", is_deleted=False).first()
    ps5 = Producto.objects.filter(nombre="Play Station 5", is_deleted=False).first()
    mando = Producto.objects.filter(nombre="Control Sony Dualsense Chroma Pearl Ps5", is_deleted=False).first()
    funko = Producto.objects.filter(nombre="Funko Pop John Wick", is_deleted=False).first()

    return render(request, 'favorite.html', {'wishlist_items': favoritos, 'page_obj': page_obj,
        'favoritos': page_obj.object_list,         
        'cod6': cod6,
        'ps5': ps5,
        'mando': mando,
        'funko': funko,})

@login_required_json
def agregar_favorito(request, producto_id):
    usuario = request.user
    producto = get_object_or_404(Producto, id=producto_id)
    
    favorito = Favorito.objects.filter(usuario=usuario, producto=producto).first()
    
    agregado = False

    if favorito:
        favorito.delete()
        mensaje = "Eliminado de favoritos"
        agregado = False
    else:
        Favorito.objects.create(usuario=usuario, producto=producto)
        mensaje = "¡Agregado a favoritos!"
        agregado = True

    return JsonResponse({
        'success': True,
        'message': mensaje,
        'agregado': agregado  
    })

@login_required_json
@require_http_methods(["DELETE"])
def eliminar_favorito(request, item_id):
    favorito = get_object_or_404(Favorito, id=item_id, usuario=request.user)
    favorito.delete()
    return JsonResponse({'message': 'Artículo eliminado correctamente'}, status=200)

@login_required_json
@require_http_methods(["POST"])
def eliminar_favoritos_seleccionados(request):
    try:
        data = json.loads(request.body)
        item_ids = data.get('ids', [])

        if item_ids:
            Favorito.objects.filter(id__in=item_ids, usuario=request.user).delete()
            return JsonResponse({'success': True})
        
        return JsonResponse({'success': False, 'error': 'No se seleccionaron items'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
# fin de las vistas de los favoritos


# vistas relacionadas con pago y envio
@login_required
def seleccionar_pago(request):
    usuario = request.user
    carrito = usuario.carritos.last()

    if not carrito or not carrito.items.exists():
        return redirect('ver_carrito')

    subtotal = sum(item.cantidad * item.producto.precio for item in carrito.items.all())

    costo_envio = 5990
    total = subtotal + costo_envio

    request.session['metodo_envio'] = "domicilio"
    request.session['direccion_envio'] = usuario.direccion
    request.session['costo_envio'] = costo_envio 

    total_items = sum(item.cantidad for item in carrito.items.all())

    if request.method == 'POST':
        metodo_pago = request.POST.get('metodo_pago')
        request.session['metodo_pago'] = metodo_pago

        if metodo_pago in ["tarjeta", "transferencia"]:
            return redirect('compra_exitosa')

    return render(request, 'seleccionar_pago.html', {
        'total': total,
        'subtotal': subtotal,
        'costo_envio': costo_envio,
        'total_items': total_items  
    })

@login_required
def compra_exitosa(request):
    usuario = request.user
    carrito = usuario.carritos.last()

    if not carrito or not carrito.items.exists():
        return redirect('ver_carrito')

    metodo_envio = request.session.get('metodo_envio', 'tienda')
    direccion_envio = request.session.get('direccion_envio')
    metodo_pago = request.session.get('metodo_pago', 'tarjeta')

    # todo o nada: si falta stock de algún producto no queda una venta a medias
    try:
        with transaction.atomic():
            venta = Venta.objects.create(
                carrito=carrito,
                usuario=usuario,
                metodo_envio=metodo_envio,
                direccion_envio=direccion_envio,
                metodo_pago=metodo_pago,
            )

            for item in carrito.items.all():
                ProductoVenta.objects.create(
                    venta=venta,
                    producto=item.producto,
                    cantidad=item.cantidad,
                    precio_unitario=item.producto.precio,
                )

            venta.calcular_total()
            carrito.items.all().delete()

            Envio.objects.create(
                venta=venta,
                estado='En Preparación',
                transportista="Starken"
            )
            Boleta.objects.create(
                venta=venta
            )
    except ValueError as e:
        return redirect(f"{reverse('ver_carrito')}?{urlencode({'notif': str(e), 'type': 'error'})}")

    total_cantidad = sum(item.cantidad for item in venta.producto_venta.all())

    return render(request, 'compra_exitosa.html', {
        'venta': venta,
        'metodo_pago': metodo_pago,
        'total_cantidad': total_cantidad,
    })


@login_required
def ver_boleta(request, venta_id):
    # el cliente solo ve sus boletas; el administrador puede ver todas
    ventas = Venta.objects.all() if request.user.is_staff else Venta.objects.filter(usuario=request.user)
    venta = get_object_or_404(ventas, id=venta_id)
    Boleta.objects.get_or_create(venta=venta)

    return render(request, 'boleta.html', {'venta': venta})
# fin de vistas relacionadas con pago y envio