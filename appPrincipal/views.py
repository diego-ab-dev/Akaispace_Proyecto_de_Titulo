from django.shortcuts import render, get_object_or_404, redirect
from .models import Producto ,ItemCarritoProducto, Usuario, Carrito, Venta, ProductoVenta ,Opinion, Favorito, Reclamo
from appPrincipal import forms
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db.models import Avg
from django.db import IntegrityError
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings
import json
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.contrib.messages import get_messages
from .forms import UsuarioForm, ProductoForm
from appPrincipal.decorators import admin_required
from django.db.models import Q
from django.utils.dateparse import parse_date
from django.contrib import messages
from .forms import OpinionForm

# Create your views here.

# Vistas para administracion
regiones_ciudades = {
    'ARICA Y PARINACOTA': ['Arica', 'Putre'],
    'TARAPACA': ['Iquique', 'Alto Hospicio'],
    'ANTOFAGASTA': ['Antofagasta', 'Calama', 'Tocopilla'],
    'ATACAMA': ['Copiapó', 'Vallenar', 'Chañaral'],
    'COQUIMBO': ['La Serena', 'Coquimbo', 'Ovalle'],
    'VALPARAISO': ['Valparaíso', 'Viña del Mar', 'Quillota', 'San Antonio'],
    'METROPOLITANA': ['Santiago', 'Puente Alto', 'Maipú', 'La Florida'],
    'OHIGGINS': ['Rancagua', 'San Fernando', 'Pichilemu'],
    'MAULE': ['Talca', 'Curicó', 'Linares'],
    'ÑUBLE': ['Chillán', 'San Carlos'],
    'BIOBIO': ['Concepción', 'Los Ángeles', 'Coronel'],
    'ARAUCANIA': ['Temuco', 'Villarrica', 'Angol'],
    'LOS RIOS': ['Valdivia', 'La Unión'],
    'LOS LAGOS': ['Puerto Montt', 'Osorno', 'Castro'],
    'AYSEN': ['Coyhaique', 'Puerto Aysén'],
    'MAGALLANES': ['Punta Arenas', 'Puerto Natales'],
}

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

    context = {
        "ventas_info": ventas_info,
        "reclamos_info": reclamos_info,
        "productos_info": productos_info,
    }
    return render(request, 'admin_panel/dashboard.html', context)


@admin_required
def get_dashboard_counts(request):
    usuarios = Usuario.objects.count()
    ventas = Venta.objects.count()
    reclamos = Reclamo.objects.count()
    opiniones = Opinion.objects.count()

    return JsonResponse({
        "usuarios": usuarios,
        "ventas": ventas,
        "reclamos": reclamos,
        "opiniones": opiniones,
    })
# fin 

# Usuarios en administracion
@admin_required
def admin_usuarios(request):
    usuarios = Usuario.objects.all()
    return render(request, 'admin_panel/usuarios.html', {'usuarios': usuarios})

@admin_required
def editar_usuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            print("Usuario actualizado:", form.cleaned_data)
            return redirect('admin_usuarios')  
        else:
            print("Errores en el formulario:", form.errors)
    else:
        form = UsuarioForm(instance=usuario)
    
    return render(request, 'admin_panel/editar_usuario.html', {
        'form': form,
        'usuario': usuario,
        'regiones_ciudades': regiones_ciudades,
    })

@admin_required
def eliminar_usuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)
    usuario.delete()
    return redirect('admin_usuarios')

@admin_required
def buscar_usuarios(request):
    query = request.GET.get('q', '').strip()
    filtro = request.GET.get('filtro', 'nombre') 
    es_administrador = request.GET.get('es_administrador', '')
    usuarios = Usuario.objects.all()
    if query:
        if filtro == "nombre":
            usuarios = usuarios.filter(nombre__icontains=query)
        elif filtro == "rut":
            usuarios = usuarios.filter(rut__icontains=query)
    if es_administrador:
        usuarios = usuarios.filter(es_administrador=(es_administrador == "True"))
    if not usuarios.exists():
        mensaje = "No se encontraron resultados."
    else:
        mensaje = ""
    return render(request, 'admin_panel/usuarios.html', {'usuarios': usuarios, 'mensaje': mensaje})


@admin_required
def crear_usuario(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email = request.POST.get('email').strip().lower()
        contraseña = request.POST.get('contraseña')
        confirmar_contraseña = request.POST.get('confirmar_contraseña')
        telefono = request.POST.get('telefono')
        direccion = request.POST.get('direccion')
        rut = request.POST.get('rut')
        region = request.POST.get('region')
        ciudad = request.POST.get('ciudad')
        es_administrador = request.POST.get('es_administrador') == 'on'

        if contraseña != confirmar_contraseña:
            return render(request, 'admin_panel/crear_usuario.html', {
                'error': 'Las contraseñas no coinciden.',
                'regiones_ciudades_json': json.dumps(regiones_ciudades),
            })

        ciudades_validas = regiones_ciudades.get(region, [])
        if ciudad not in ciudades_validas:
            return render(request, 'admin_panel/crear_usuario.html', {
                'error': f'La ciudad "{ciudad}" no es válida para la región "{region}".',
                'regiones_ciudades_json': json.dumps(regiones_ciudades),
            })

        try:
            Usuario.objects.create(
                nombre=nombre,
                email=email,
                contraseña=make_password(contraseña),
                es_administrador=es_administrador,
                telefono=telefono,
                direccion=direccion,
                rut=rut,
                region=region,
                ciudad=ciudad
            )
            return redirect('admin_usuarios')
        except IntegrityError as e:
            error = 'Ocurrió un error al crear el usuario.'
            if 'email' in str(e):
                error = 'El email ya está registrado.'
            elif 'rut' in str(e):
                error = 'El RUT ya está registrado.'
            return render(request, 'admin_panel/crear_usuario.html', {
                'error': error,
                'regiones_ciudades_json': json.dumps(regiones_ciudades),
            })
        
    return render(request, 'admin_panel/crear_usuario.html', {
    'regiones_ciudades': regiones_ciudades,
    })
# fin


# Productos en adminstracion
@admin_required
def admin_productos(request):
    productos = Producto.objects.all()
    return render(request, 'admin_panel/productos.html', {'productos': productos})

@admin_required
def agregar_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('admin_productos')
    else:
        form = ProductoForm()
    return render(request, 'admin_panel/agregar_producto.html', {'form': form})

@admin_required
def eliminar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    producto.delete()
    return redirect('admin_productos')

@admin_required
def buscar_productos(request):
    query = request.GET.get('q', '').strip()
    categoria = request.GET.get('categoria', '')
    genero = request.GET.get('genero', '')
    ordenar = request.GET.get('ordenar', 'recientes')

    productos = Producto.objects.all()

    if query:
        productos = productos.filter(
            Q(nombre__icontains=query) | Q(codigo_de_barra__icontains=query)
        )

    if categoria:
        productos = productos.filter(categoria=categoria)

    if genero:
        productos = productos.filter(genero=genero)

    if ordenar == 'recientes':
        productos = productos.order_by('-id')
    elif ordenar == 'antiguos':
        productos = productos.order_by('id')
    elif ordenar == 'menor_precio':
        productos = productos.order_by('precio')
    elif ordenar == 'mayor_precio':
        productos = productos.order_by('-precio')

    if not productos.exists():
        mensaje = "No se encontraron resultados para tu búsqueda."
    else:
        mensaje = ""

    categorias = []
    for grupo in Producto.CATEGORIAS:
        for categoria in grupo[1]:  
            categorias.append(categoria)
    generos = Producto.GENEROS

    return render(request, 'admin_panel/productos.html', {
        'productos': productos,
        'mensaje': mensaje,
        'query': query,
        'categoria': categoria,
        'genero': genero,
        'ordenar': ordenar,
        'categorias': categorias,
        'generos': generos,
    })


@admin_required
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('admin_productos')
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'admin_panel/editar_producto.html', {'form': form})
# fin


# opiniones en administracion
@admin_required
def admin_opiniones(request):
    opiniones = Opinion.objects.select_related('usuario', 'producto').all()
    return render(request, 'admin_panel/opiniones.html', {'opiniones': opiniones})
#fin


# reclamos en administracion
@admin_required
def admin_reclamos(request):
    reclamos = Reclamo.objects.select_related('usuario').all()
    return render(request, 'admin_panel/reclamos.html', {'reclamos': reclamos})

@admin_required
def responder_reclamo(request, reclamo_id):
    reclamo = get_object_or_404(Reclamo, id=reclamo_id)
    if request.method == 'POST':
        respuesta = request.POST.get('respuesta')
        reclamo.respuesta = respuesta
        reclamo.estado = 'Respondido'
        reclamo.save()
        return redirect('admin_reclamos')
    return render(request, 'admin_panel/responder_reclamo.html', {'reclamo': reclamo})
# fin


# ventas en administracion
@admin_required
def admin_ventas(request):
    query = request.GET.get('q', '')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    ventas = Venta.objects.select_related('usuario').prefetch_related('producto_venta__producto').all()

    if query:
        ventas = ventas.filter(
            Q(usuario__nombre__icontains=query) | Q(id__icontains=query)
        )
    
    if fecha_inicio and fecha_fin:
        ventas = ventas.filter(
            fecha__range=[parse_date(fecha_inicio), parse_date(fecha_fin)]
        )

    return render(request, 'admin_panel/ventas.html', {'ventas': ventas})

@admin_required
def admin_cambiar_estado_venta(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in dict(Venta.ESTADO_CHOICES):
            venta.estado = nuevo_estado
            venta.save()
        else:
            messages.error(request, "Estado no válido.")
    return redirect('admin_ventas')
#fin
# Fin vistas para administracion


# vistas relacionadas a home y menu
def home(request):
    usuario_id = request.session.get('usuario_id')
    usuario = None
    if usuario_id:
        try:
            usuario = Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            pass
    return render(request, 'home.html', {'usuario': usuario})

def productos_menu(request):
    query = request.GET.get('buscar')
    if query:
        productos = Producto.objects.filter(nombre__icontains=query, stock__gt=0)
        return render(request, 'resultado_busqueda.html', {'productos': productos, 'query': query})
    else:
        productos = Producto.objects.filter(stock__gt=0) 
        productos_recientes = Producto.objects.filter(stock__gt=0).order_by('-id')[:10]
        return render(request, 'productosmenu.html', {
            'productos': productos,
            'productos_recientes': productos_recientes,
        })
    
def producto_detalle(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    rango_cantidad = range(1, producto.stock + 1)

    promedio_puntuacion = producto.opiniones.aggregate(Avg('puntuacion'))['puntuacion__avg']
    promedio_puntuacion = round(promedio_puntuacion, 1) if promedio_puntuacion else 0

    opiniones = producto.opiniones.all()
    opiniones_list = [
        {
            "usuario": opinion.usuario.nombre,
            "comentario": opinion.comentario,
            "fecha": opinion.fecha_creacion,
            "estrellas_llenas": range(opinion.puntuacion),  
            "estrellas_vacias": range(5 - opinion.puntuacion),  
        }
        for opinion in opiniones
    ]

    return render(
        request,
        'producto_detalle.html',
        {
            'producto': producto,
            'rango_cantidad': rango_cantidad,
            'promedio_puntuacion': promedio_puntuacion,
            'opiniones_list': opiniones_list,  
        },
    )
    
def vista_carrusel(request):
    productos = Producto.objects.all()
    cod6 = Producto.objects.filter(nombre="Call of Duty: Black Ops 6").first() 
    fc25 = Producto.objects.filter(nombre="Fc 25").first()
    silent = Producto.objects.filter(nombre="Silent Hill 2").first()    
    return render(request, 'productosmenu.html', {'productos': productos, 'cod6': cod6, 'fc25': fc25, 'silent':silent})

def productos_por_categoria(request, categoria):
    productos = Producto.objects.filter(categoria=categoria)
    
    genero = request.GET.get('genero')
    if genero:
        productos = productos.filter(genero=genero)
    
    precio_min = request.GET.get('precio_min')
    precio_max = request.GET.get('precio_max')
    if precio_min and precio_max:
        productos = productos.filter(precio__gte=precio_min, precio__lte=precio_max)
    
    orden_precio = request.GET.get('orden_precio')
    if orden_precio == 'asc':
        productos = productos.order_by('precio')
    elif orden_precio == 'desc':
        productos = productos.order_by('-precio')
    
    context = {
        'categoria': dict(Producto.CATEGORIAS).get(categoria, categoria),
        'productos': productos,
        'generos': Producto.GENEROS,
    }
    return render(request, 'productos_por_categoria.html', context)
# fin de vistas relacionadas a home y menu


# Vistas relacionadas a los inicios y registros
def login(request):
    errors = {}  
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        contraseña = request.POST.get('contraseña', '').strip()

        if not email:
            errors['email'] = "Por favor, ingresa tu correo electrónico."
        if not contraseña:
            errors['contraseña'] = "Por favor, ingresa tu contraseña."

        if not errors:
            try:
                usuario = Usuario.objects.get(email=email)
                if check_password(contraseña, usuario.contraseña):
                    request.session['usuario_id'] = usuario.id
                    print(f"Usuario {usuario.id} - Admin: {usuario.es_administrador}")  
                    if usuario.es_administrador:
                        return redirect('admin_dashboard') 
                    else:
                        return redirect('home') 
                else:
                    errors['contraseña'] = "Contraseña incorrecta."
            except Usuario.DoesNotExist:
                errors['email'] = "Correo electrónico no registrado."

    return render(request, 'login.html', {'errors': errors})


def register(request):
    form = forms.UsuarioCustomForm()
    if request.method == 'POST':
        form = forms.UsuarioCustomForm(request.POST)
        region_seleccionada = request.POST.get('region')
        ciudades = regiones_ciudades.get(region_seleccionada, [])
        form.fields['ciudad'].choices = [(ciudad, ciudad) for ciudad in ciudades]

        if form.is_valid():
            try:
                registro = Usuario(
                    rut=form.cleaned_data['rut'],
                    nombre=form.cleaned_data['nombre'],
                    telefono=form.cleaned_data['telefono'],
                    email=form.cleaned_data['email'],
                    contraseña=make_password(form.cleaned_data['contraseña']),
                    direccion=form.cleaned_data['direccion'],
                    ciudad=form.cleaned_data['ciudad'],
                    region=form.cleaned_data['region'],
                )
                registro.save()
                return JsonResponse({'success': True, 'message': 'Usuario registrado exitosamente.'})
            except IntegrityError as e:
                if 'email' in str(e):
                    return JsonResponse({'success': False, 'message': 'El correo ya está registrado.'})
                elif 'rut' in str(e):
                    return JsonResponse({'success': False, 'message': 'El RUT ya está registrado.'})
        else:
            print(form.errors)
    data = {'form': form, 'regiones_ciudades': regiones_ciudades}
    return render(request, 'register.html', data)

def logout(request):
    request.session.flush()  
    return redirect('login')

def password_reset_request(request):
    if request.method == 'POST':
        form = forms.PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                usuario = Usuario.objects.get(email=email)
                token = get_random_string(length=32)
                usuario.contraseña = make_password(token)
                usuario.save()
                send_mail(
                    subject="Recuperación de contraseña - SD Games",
                    message=f"Tu nueva contraseña temporal es: {token}",
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[email],
                    fail_silently=False,
                )
                return redirect('login')
            except Usuario.DoesNotExist:
                form.add_error('email', "El correo no está registrado.")
    else:
        form = forms.PasswordResetForm()
    return render(request, 'password_reset.html', {'form': form, 'mensaje_exito': "Se ha enviado una nueva contraseña a tu correo electrónico."})

def obtener_ciudades(request):
    region = request.GET.get('region')
    ciudades = regiones_ciudades.get(region, [])
    return JsonResponse({'ciudades': ciudades})
# Fin de Vistas relacionadas a los inicios y registros


# vistas sobre el perfil del usuario
def perfil(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')
    
    usuario = get_object_or_404(Usuario, id=usuario_id)
    compras = Venta.objects.filter(usuario=usuario).order_by('-fecha')[:3]
    opiniones = Opinion.objects.filter(usuario=usuario).order_by('-fecha_creacion')[:2]
    reclamos_recientes = Reclamo.objects.filter(usuario=usuario).order_by('-fecha')[:2]
    
    return render(request, 'perfil_usuario.html', {
        'usuario': usuario,
        'compras': compras,
        'opiniones': opiniones,
        'reclamos_recientes': reclamos_recientes,
    })

def lista_opiniones(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    usuario = get_object_or_404(Usuario, id=usuario_id)
    opiniones = Opinion.objects.filter(usuario=usuario).order_by('-fecha_creacion')

    return render(request, 'lista_opiniones.html', {'opiniones': opiniones})

def ver_compras(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')
    
    usuario = get_object_or_404(Usuario, id=usuario_id)
    compras = Venta.objects.filter(usuario=usuario).prefetch_related(
        'producto_venta__producto'
    ).order_by('-fecha')

    for compra in compras:
        for producto_venta in compra.producto_venta.all():
            producto = producto_venta.producto
            producto_venta.opinion_enviada = producto.opiniones.filter(usuario=usuario).exists()

    return render(request, 'ver_compras.html', {'usuario': usuario, 'compras': compras})


def enviar_opinion(request, producto_id):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login') 

    usuario = get_object_or_404(Usuario, id=usuario_id)
    producto = get_object_or_404(Producto, id=producto_id)
    
    producto_comprado = ProductoVenta.objects.filter(
        venta__usuario=usuario,
        producto=producto
    ).exists()

    if not producto_comprado:
        return redirect('ver_compras')  

    if request.method == 'POST':
        form = OpinionForm(request.POST)
        if form.is_valid():
            opinion = form.save(commit=False)
            opinion.usuario = usuario  
            opinion.producto = producto
            opinion.save()
            return redirect('ver_compras')  
    else:
        form = OpinionForm()

    return render(request, 'enviar_opinion.html', {
        'producto': producto,
        'form': form,
    })


def crear_reclamo(request, compra_id):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    usuario = get_object_or_404(Usuario, id=usuario_id)
    compra = get_object_or_404(Venta, id=compra_id, usuario=usuario)

    if request.method == 'POST':
        asunto = request.POST.get('asunto', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()

        if not asunto or not descripcion:
            return render(request, 'crear_reclamo.html', {'compra': compra, 'error': "Todos los campos son obligatorios."})
        else:
            Reclamo.objects.create(usuario=usuario, asunto=asunto, descripcion=descripcion)
            return redirect('ver_compras')


    return render(request, 'crear_reclamo.html', {
        'compra': compra
    })

def lista_reclamos(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    usuario = get_object_or_404(Usuario, id=usuario_id)
    todos_reclamos = Reclamo.objects.filter(usuario=usuario).order_by('-id')

    return render(request, 'lista_reclamos.html', {
        'todos_reclamos': todos_reclamos,
    })

def cambiar_contraseña(request):
    errores = []
    if request.method == 'POST':
        contraseña_actual = request.POST.get('contraseña_actual')
        nueva_contraseña = request.POST.get('nueva_contraseña')
        confirmar_contraseña = request.POST.get('confirmar_contraseña')
        usuario_id = request.session.get('usuario_id')

        if usuario_id:
            try:
                usuario = Usuario.objects.get(id=usuario_id)
                if not check_password(contraseña_actual, usuario.contraseña):
                    errores.append("La contraseña actual no es correcta.")
                elif nueva_contraseña != confirmar_contraseña:
                    errores.append("Las contraseñas no coinciden. Inténtelo nuevamente.")
                else:
                    usuario.contraseña = make_password(nueva_contraseña)
                    usuario.save()
                    return redirect('perfil')
            except Usuario.DoesNotExist:
                errores.append("Usuario no encontrado. Inténtelo más tarde.")
        else:
            errores.append("Debes iniciar sesión para cambiar tu contraseña.")

    storage = get_messages(request)
    mensajes = [{'tipo': message.tags, 'texto': message.message} for message in storage]

    contexto = {
        'mensajes_json': json.dumps(mensajes),
        'errores': errores,
    }

    return render(request, 'cambiar_contrausu.html', contexto)

@csrf_exempt
def editar_perfil(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return JsonResponse({'error': "Debes iniciar sesión para acceder a la edición de perfil."}, status=403)

    usuario = get_object_or_404(Usuario, id=usuario_id)

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

regiones_ciudades = {
    'ARICA Y PARINACOTA': ['Arica', 'Putre'],
    'TARAPACA': ['Iquique', 'Alto Hospicio'],
    'ANTOFAGASTA': ['Antofagasta', 'Calama', 'Tocopilla'],
    'ATACAMA': ['Copiapó', 'Vallenar', 'Chañaral'],
    'COQUIMBO': ['La Serena', 'Coquimbo', 'Ovalle'],
    'VALPARAISO': ['Valparaíso', 'Viña del Mar', 'Quillota', 'San Antonio'],
    'METROPOLITANA': ['Santiago', 'Puente Alto', 'Maipú', 'La Florida'],
    'OHIGGINS': ['Rancagua', 'San Fernando', 'Pichilemu'],
    'MAULE': ['Talca', 'Curicó', 'Linares'],
    'ÑUBLE': ['Chillán', 'San Carlos'],
    'BIOBIO': ['Concepción', 'Los Ángeles', 'Coronel'],
    'ARAUCANIA': ['Temuco', 'Villarrica', 'Angol'],
    'LOS RIOS': ['Valdivia', 'La Unión'],
    'LOS LAGOS': ['Puerto Montt', 'Osorno', 'Castro'],
    'AYSEN': ['Coyhaique', 'Puerto Aysén'],
    'MAGALLANES': ['Punta Arenas', 'Puerto Natales'],
}
# fin de vistas sobre el perfil del usuario


# vistas relacionadas con carrito:
def usuario_compro_producto(usuario, producto):
    return ItemCarritoProducto.objects.filter(
        carrito__venta__isnull=False,  
        carrito__usuario=usuario,
        producto=producto
    ).exists()

def agregar_al_carrito(request, producto_id):
    usuario_id = request.session.get('usuario_id')
    
    if not usuario_id:
        return redirect('login') 

    usuario = get_object_or_404(Usuario, id=usuario_id)
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

    return redirect('ver_carrito')

def eliminar_del_carrito(request, item_id):
    if request.method == 'POST':
        try:
            item = get_object_or_404(ItemCarritoProducto, id=item_id)
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

def actualizar_cantidad_carrito(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        nueva_cantidad = int(request.POST.get('cantidad', 1))

        item = get_object_or_404(ItemCarritoProducto, id=item_id)
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

def ver_carrito(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    usuario = get_object_or_404(Usuario, id=usuario_id)
    carrito, created = Carrito.objects.get_or_create(usuario=usuario)

    total_items = sum(item.cantidad for item in carrito.items.all())

    return render(request, 'carrito.html', {
        'carrito': carrito,
        'productos': carrito.items.all(),
        'total': carrito.total_carrito(),
        'total_items': total_items,  
    })

def carrito(request):
    return render(request, 'carrito.html')

# fin de vistas relacionadas con carrito:


# vistas de los favoritos
def lista_favoritos(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    usuario = get_object_or_404(Usuario, id=usuario_id)

    wishlist_items = Favorito.objects.filter(usuario=usuario)
    return render(request, 'favorite.html', {'wishlist_items': wishlist_items})

def agregar_favorito(request, producto_id):
    usuario_id = request.session.get('usuario_id')

    if not usuario_id:
        return redirect('login') 

    usuario = get_object_or_404(Usuario, id=usuario_id)
    producto = get_object_or_404(Producto, id=producto_id)
    favorito, created = Favorito.objects.get_or_create(usuario=usuario, producto=producto)

    return redirect('lista_favorito')

@require_http_methods(["DELETE"])
def eliminar_favorito(request, item_id):
    favorito = get_object_or_404(Favorito, id=item_id)
    favorito.delete()
    return JsonResponse({'message': 'Artículo eliminado correctamente'}, status=200)
# fin de las vistas de los favoritos


# vistas relacionadas con pago y envio
def seleccionar_envio(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)
    carrito = usuario.carritos.last() 

    if not carrito or not carrito.items.exists():
        return redirect('carrito_vacio') 

    if request.method == 'POST':
        metodo_envio = request.POST.get('metodo_envio', 'tienda')
        direccion_envio = usuario.direccion if metodo_envio == 'domicilio' else None
        request.session['metodo_envio'] = metodo_envio
        request.session['direccion_envio'] = direccion_envio

        return redirect('seleccionar_pago', usuario_id=usuario_id)

    return render(request, 'seleccionar_envio.html', {'usuario': usuario, 'carrito': carrito})

def seleccionar_pago(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)
    carrito = usuario.carritos.last()

    if not carrito or not carrito.items.exists():
        return redirect('ver_carrito')

    subtotal = sum(item.cantidad * item.producto.precio for item in carrito.items.all())

    metodo_envio = request.session.get('metodo_envio', 'tienda')
    costo_envio = 0
    if metodo_envio == 'domicilio':
        costo_envio = 5000

    total = subtotal + costo_envio

    if request.method == 'POST':
        metodo_pago = request.POST.get('metodo_pago')

        if metodo_pago in ["tarjeta", "transferencia"]:
            return redirect('compra_exitosa', usuario_id=usuario_id)
        
        return redirect('seleccionar_pago', usuario_id=usuario_id)

    return render(request, 'seleccionar_pago.html', {
        'usuario': usuario,
        'total': total,
    })


def compra_exitosa(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)
    carrito = usuario.carritos.last()

    if not carrito or not carrito.items.exists():
        return redirect('ver_carrito')

    metodo_envio = request.session.get('metodo_envio', 'tienda')
    direccion_envio = request.session.get('direccion_envio')  
    metodo_pago = request.session.get('metodo_pago', 'tarjeta')

    venta = Venta.objects.create(
        carrito=carrito,
        usuario=usuario,
        metodo_envio=metodo_envio,
        direccion_envio=direccion_envio, 
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

    return render(request, 'compra_exitosa.html', {
        'venta': venta,
        'metodo_pago': metodo_pago,
    })
# fin de vistas relacionadas con pago y envio