from django.core.management import call_command
from django.test import TestCase, override_settings

from .models import Producto, Usuario


def _urls_con_admin_de_django():
    # el admin de Django solo se monta con DEBUG=True y los tests corren con DEBUG=False,
    # así que los tests del admin usan esta lista de URLs (ROOT_URLCONF='appPrincipal.tests')
    from django.contrib import admin
    from django.urls import path
    from Akaispace.urls import urlpatterns as urls_del_sitio
    return [path('admin/', admin.site.urls), *urls_del_sitio]


urlpatterns = _urls_con_admin_de_django()


@override_settings(DEBUG=True)
class SeedDemoTests(TestCase):
    def test_carga_productos_y_usuarios(self):
        call_command('seed_demo', verbosity=0)
        self.assertEqual(Producto.objects.count(), 6)
        admin = Usuario.objects.get(email='admin@gmail.com')
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.check_password('Akaispace-Admin-2026'))
        self.assertFalse(Usuario.objects.get(email='user@gmail.com').is_staff)

    def test_es_idempotente(self):
        call_command('seed_demo', verbosity=0)
        call_command('seed_demo', verbosity=0)
        self.assertEqual(Usuario.objects.count(), 2)
        self.assertEqual(Producto.objects.count(), 6)


class RutTests(TestCase):
    def test_rut_valido_se_normaliza(self):
        from .forms import normalizar_rut
        self.assertEqual(normalizar_rut('12343455-2'), '12.343.455-2')
        self.assertEqual(normalizar_rut('12.343.455-2'), '12.343.455-2')
        self.assertEqual(normalizar_rut('75292177-6'), '75.292.177-6')
        self.assertEqual(normalizar_rut('1.000.005-k'), '1.000.005-K')

    def test_rut_invalido_lanza_error(self):
        from django.core.exceptions import ValidationError
        from .forms import normalizar_rut
        for rut in ['12.343.455-3', 'abc-1', '', '1-9', '123456789012-3']:
            with self.assertRaises(ValidationError, msg=rut):
                normalizar_rut(rut)


class RegisterTests(TestCase):
    datos = {
        'rut': '12343455-2', 'nombre': 'Juan Perez', 'telefono': '+56 9 12345678',
        'email': 'juan@example.com', 'contraseña': 'Akaispace-2026!', 'confirmar_contraseña': 'Akaispace-2026!', 'direccion': 'Calle 123',
        'region': 'LOS RIOS', 'ciudad': 'Valdivia',
        'acepta_privacidad': 'on', 'autoriza_datos_navegacion': 'on',
    }

    def test_registro_guarda_los_consentimientos_y_la_version_aceptada(self):  # HU-01
        from .constants import POLITICA_PRIVACIDAD_VERSION
        self.assertTrue(self.client.post('/register/', self.datos).json()['success'])
        usuario = Usuario.objects.get(email='juan@example.com')
        self.assertIsNotNone(usuario.privacidad_aceptada_en)
        self.assertIsNotNone(usuario.datos_navegacion_autorizados_en)
        self.assertEqual(usuario.privacidad_version, POLITICA_PRIVACIDAD_VERSION)

    def test_sin_aceptar_la_politica_no_se_crea_la_cuenta(self):  # HU-01
        datos = {k: v for k, v in self.datos.items() if k != 'acepta_privacidad'}
        respuesta = self.client.post('/register/', datos).json()
        self.assertFalse(respuesta['success'])
        self.assertIn('Política de Privacidad', respuesta['message'])
        self.assertFalse(Usuario.objects.exists())

    def test_autorizar_datos_de_navegacion_es_opcional(self):  # HU-01
        datos = {k: v for k, v in self.datos.items() if k != 'autoriza_datos_navegacion'}
        self.assertTrue(self.client.post('/register/', datos).json()['success'])
        usuario = Usuario.objects.get(email='juan@example.com')
        self.assertIsNotNone(usuario.privacidad_aceptada_en)
        self.assertIsNone(usuario.datos_navegacion_autorizados_en)

    def test_politica_de_privacidad_es_publica_y_esta_enlazada(self):  # HU-01
        respuesta = self.client.get('/politica-de-privacidad/')
        self.assertContains(respuesta, 'Política de Privacidad')
        registro = self.client.get('/register/')
        self.assertContains(registro, 'href="/politica-de-privacidad/"')
        self.assertContains(registro, 'Declaro ser mayor de 18 años')
        self.assertContains(self.client.get('/'), 'href="/politica-de-privacidad/"')

    def test_registro_valido_guarda_rut_normalizado(self):
        respuesta = self.client.post('/register/', self.datos)
        self.assertTrue(respuesta.json()['success'])
        self.assertEqual(Usuario.objects.get(email='juan@example.com').rut, '12.343.455-2')

    def test_registro_con_rut_invalido_es_rechazado(self):
        respuesta = self.client.post('/register/', {**self.datos, 'rut': '12343455-3'})
        self.assertFalse(respuesta.json()['success'])
        self.assertIn('RUT', respuesta.json()['message'])
        self.assertFalse(Usuario.objects.exists())

    def test_rut_duplicado_con_otro_formato_es_rechazado(self):
        self.client.post('/register/', self.datos)
        respuesta = self.client.post('/register/', {**self.datos, 'email': 'otro@example.com', 'rut': '12.343.455-2'})
        self.assertEqual(respuesta.json()['message'], 'El RUT ya está registrado.')


def crear_cliente(email='cliente@example.com', password='Akaispace-2026!', **extra):
    datos = {'nombre': 'Cliente Prueba', **extra}
    return Usuario.objects.create_user(email=email, password=password, **datos)


class LoginTests(TestCase):
    def setUp(self):
        self.usuario = crear_cliente()

    def login(self, email, password='Akaispace-2026!'):
        return self.client.post('/login/', {'email': email, 'contraseña': password})

    def test_login_no_distingue_mayusculas_en_email(self):  # 13
        respuesta = self.login('CLIENTE@Example.com')
        self.assertRedirects(respuesta, '/', fetch_redirect_response=False)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.usuario.pk)

    def test_mismo_mensaje_si_el_correo_no_existe_o_la_clave_es_incorrecta(self):  # 14
        clave_mala = self.login('cliente@example.com', 'incorrecta')
        correo_inexistente = self.login('nadie@example.com')
        self.assertEqual(clave_mala.context['errors'], correo_inexistente.context['errors'])

    def test_login_cambia_la_llave_de_sesion(self):  # 14
        self.client.get('/login/')
        self.client.session.save()
        llave_antes = self.client.session.session_key
        self.login('cliente@example.com')
        self.assertNotEqual(self.client.session.session_key, llave_antes)

    def test_bloqueo_tras_5_intentos_fallidos(self):  # 14
        for _ in range(5):
            self.login('cliente@example.com', 'incorrecta')
        respuesta = self.login('cliente@example.com')  # aunque ahora la clave sea correcta
        self.assertEqual(respuesta.status_code, 429)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_usuario_eliminado_no_puede_iniciar_sesion(self):
        self.usuario.delete()
        self.login('cliente@example.com')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_next_redirige_a_la_pagina_pedida_y_rechaza_sitios_externos(self):
        respuesta = self.client.post('/login/?next=/compras/', {'email': 'cliente@example.com', 'contraseña': 'Akaispace-2026!'})
        self.assertRedirects(respuesta, '/compras/', fetch_redirect_response=False)
        self.client.logout()
        respuesta = self.client.post('/login/?next=https://malicioso.com/', {'email': 'cliente@example.com', 'contraseña': 'Akaispace-2026!'})
        self.assertRedirects(respuesta, '/', fetch_redirect_response=False)


class ContraseñaTests(TestCase):  # 15
    def test_registro_rechaza_contraseña_debil(self):
        datos = {**RegisterTests.datos, 'contraseña': '12345', 'confirmar_contraseña': '12345'}
        respuesta = self.client.post('/register/', datos)
        self.assertFalse(respuesta.json()['success'])
        self.assertFalse(Usuario.objects.exists())

    def test_contraseña_sin_letra_o_sin_numero_es_rechazada(self):  # RNF-01
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        for clave in ['Akaispace-Tienda!', 'Valdivia-Gamer-Store']:  # largas y no comunes, pero sin número
            datos = {**RegisterTests.datos, 'contraseña': clave, 'confirmar_contraseña': clave}
            respuesta = self.client.post('/register/', datos).json()
            self.assertFalse(respuesta['success'], clave)
            self.assertIn('una letra y un número', respuesta['message'])
        with self.assertRaises(ValidationError):
            validate_password('2026-2027-2028!')  # sin letras
        self.assertFalse(Usuario.objects.exists())
        validate_password('Akaispace-2026!')  # con letra y número: no lanza error

    def test_las_reglas_se_muestran_antes_de_escribir_la_contraseña(self):  # RNF-01
        self.assertContains(self.client.get('/register/'), 'al menos una letra y un número')

    def test_registro_rechaza_confirmacion_distinta(self):
        datos = {**RegisterTests.datos, 'confirmar_contraseña': 'Otra-Clave-2026!'}
        self.assertEqual(self.client.post('/register/', datos).json()['message'], 'Las contraseñas no coinciden.')

    def test_cambiar_contraseña_valida_reglas_y_mantiene_la_sesion(self):
        usuario = crear_cliente()
        self.client.force_login(usuario)
        datos = {'contraseña_actual': 'Akaispace-2026!', 'nueva_contraseña': 'abc', 'confirmar_contraseña': 'abc'}
        self.client.post('/cambiar/', datos)
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password('Akaispace-2026!'))

        datos = {'contraseña_actual': 'Akaispace-2026!', 'nueva_contraseña': 'Nueva-Clave-2026!', 'confirmar_contraseña': 'Nueva-Clave-2026!'}
        self.client.post('/cambiar/', datos)
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password('Nueva-Clave-2026!'))
        self.assertEqual(self.client.get('/perfil/').status_code, 200)


class AccesoTests(TestCase):  # 1 y 20
    def setUp(self):
        from .models import Venta
        self.dueño = crear_cliente('dueno@example.com')
        self.otro = crear_cliente('otro@example.com')
        self.venta = Venta.objects.create(usuario=self.dueño, metodo_envio='tienda')

    def test_paginas_privadas_piden_login(self):
        for url in ['/perfil/', '/compras/', '/ver_carrito/', '/favorites/', '/seleccionar-pago/', f'/boleta/{self.venta.id}/']:
            respuesta = self.client.get(url)
            self.assertRedirects(respuesta, f'/login/?next={url}', fetch_redirect_response=False, msg_prefix=url)

    def test_endpoints_ajax_responden_json_sin_sesion(self):
        respuesta = self.client.post('/agregar_favorito/1/')
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()['error'], 'not_logged_in')

    def test_no_se_puede_ver_la_compra_ni_la_boleta_de_otro_usuario(self):
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(f'/compra/{self.venta.id}/detalle/').status_code, 404)
        self.assertEqual(self.client.get(f'/boleta/{self.venta.id}/').status_code, 404)

    def test_el_dueño_si_ve_su_compra(self):
        self.client.force_login(self.dueño)
        self.assertEqual(self.client.get(f'/boleta/{self.venta.id}/').status_code, 200)

    def test_cliente_no_entra_al_panel_admin(self):
        self.client.force_login(self.otro)
        self.assertRedirects(self.client.get('/admin-panel/'), '/', fetch_redirect_response=False)

    def test_admin_entra_al_panel(self):
        self.client.force_login(crear_cliente('jefe@example.com', is_staff=True))
        self.assertEqual(self.client.get('/admin-panel/').status_code, 200)


class CompraTests(TestCase):  # 1: el flujo de compra usa request.user, sin ids en la URL
    def setUp(self):
        self.producto = Producto.objects.create(
            codigo_de_barra='111', nombre='Juego', precio=10000, stock=3, categoria='Videojuegos PS5',
            imagen_principal='productos/silent.png'
        )
        self.cliente = crear_cliente()
        self.client.force_login(self.cliente)

    def test_compra_completa_descuenta_stock_y_genera_boleta(self):
        from .models import Venta
        self.client.post(f'/agregar/{self.producto.id}/', {'cantidad': 2})
        self.assertEqual(self.client.get('/seleccionar-pago/?envio=tienda').status_code, 200)
        respuesta = self.client.post('/seleccionar-pago/', {'metodo_pago': 'tarjeta'})
        self.assertRedirects(respuesta, '/compra-exitosa/', fetch_redirect_response=False)
        self.assertEqual(self.client.get('/compra-exitosa/').status_code, 200)

        venta = Venta.objects.get(usuario=self.cliente)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 1)
        self.assertTrue(hasattr(venta, 'boleta'))
        self.assertEqual(self.client.get(f'/boleta/{venta.id}/').status_code, 200)

    def test_sin_stock_no_queda_venta_a_medias(self):
        from .models import ItemCarritoProducto, Carrito, Venta
        carrito = Carrito.objects.create(usuario=self.cliente)
        ItemCarritoProducto.objects.create(carrito=carrito, producto=self.producto, cantidad=5)
        elegir_entrega(self.client)
        respuesta = self.client.get('/compra-exitosa/')
        self.assertTrue(respuesta.url.startswith('/ver_carrito/'))
        self.assertFalse(Venta.objects.exists())
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 3)

    def test_no_se_puede_modificar_el_carrito_de_otro(self):
        from .models import ItemCarritoProducto, Carrito
        otro = crear_cliente('otro@example.com')
        item = ItemCarritoProducto.objects.create(carrito=Carrito.objects.create(usuario=otro), producto=self.producto)
        self.assertEqual(self.client.post('/actualizar-cantidad/', {'item_id': item.id, 'cantidad': 2}).status_code, 404)
        self.assertFalse(self.client.post(f'/eliminar/{item.id}/').json()['success'])
        self.assertTrue(ItemCarritoProducto.objects.filter(id=item.id).exists())


class ModeloTests(TestCase):  # 17, 25, 26 y 28
    def setUp(self):
        from .models import Venta, ProductoVenta
        self.producto = Producto.objects.create(
            codigo_de_barra='222', nombre='Consola', precio=1000, stock=5, categoria='Ps5 Consolas',
            imagen_principal='productos/silent.png'
        )
        self.cliente = crear_cliente()
        self.venta = Venta.objects.create(usuario=self.cliente, metodo_envio='tienda')
        ProductoVenta.objects.create(venta=self.venta, producto=self.producto, cantidad=2, precio_unitario=1000)

    def test_objects_oculta_eliminados_y_todos_los_incluye(self):  # 28
        self.producto.delete()
        self.assertFalse(Producto.objects.filter(id=self.producto.id).exists())
        self.assertTrue(Producto.todos.filter(id=self.producto.id).exists())
        self.assertIsNotNone(Producto.todos.get(id=self.producto.id).deleted_at)

    def test_delete_masivo_tambien_es_logico(self):  # 28
        Producto.objects.filter(id=self.producto.id).delete()
        producto = Producto.todos.get(id=self.producto.id)
        self.assertTrue(producto.is_deleted)
        self.assertIsNotNone(producto.deleted_at)

    def test_historial_conserva_el_producto_eliminado(self):  # 17 y 28
        self.producto.delete()
        linea = self.venta.producto_venta.get()
        self.assertEqual(linea.producto.nombre, 'Consola')

    def test_no_se_puede_borrar_de_verdad_un_producto_o_usuario_con_ventas(self):  # 17
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.producto.hard_delete()
        with self.assertRaises(ProtectedError):
            self.cliente.hard_delete()

    def test_un_solo_carrito_por_usuario_e_items_unicos(self):  # 26
        from django.db import IntegrityError, transaction
        from .models import Carrito, ItemCarritoProducto, Favorito
        carrito = Carrito.objects.create(usuario=self.cliente)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Carrito.objects.create(usuario=self.cliente)
        ItemCarritoProducto.objects.create(carrito=carrito, producto=self.producto)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ItemCarritoProducto.objects.create(carrito=carrito, producto=self.producto)
        Favorito.objects.create(usuario=self.cliente, producto=self.producto)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Favorito.objects.create(usuario=self.cliente, producto=self.producto)

    def test_varios_usuarios_sin_rut(self):  # 26
        crear_cliente('a@example.com')
        crear_cliente('b@example.com')
        self.assertEqual(Usuario.objects.filter(rut__isnull=True).count(), 3)

    def test_estado_se_modifica_en_envio_y_anular_dos_veces_no_duplica_stock(self):  # 25
        from .models import Envio
        Envio.objects.create(venta=self.venta)
        self.client.force_login(crear_cliente('jefe@example.com', is_staff=True))
        self.client.post(f'/admin-panel/ventas/modificar/{self.venta.id}/', {'estado': 'Entregado'})
        self.assertEqual(Envio.objects.get(venta=self.venta).estado, 'Entregado')

        self.client.post(f'/ventas/anular/{self.venta.id}/')
        self.client.post(f'/ventas/anular/{self.venta.id}/')
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 7)  # 5 + 2 devueltos una sola vez

    @override_settings(ROOT_URLCONF='appPrincipal.tests')
    def test_admin_de_django_elimina_productos_de_forma_logica(self):
        self.client.force_login(Usuario.objects.create_superuser(email='root@example.com', password='x', nombre='Root'))
        self.client.post(f'/admin/appPrincipal/producto/{self.producto.id}/delete/', {'post': 'yes'})
        self.assertTrue(Producto.todos.get(id=self.producto.id).is_deleted)


class AdminDjangoTests(TestCase):
    def test_sin_debug_el_admin_de_django_no_existe(self):
        self.client.force_login(Usuario.objects.create_superuser(email='root@example.com', password='x', nombre='Root'))
        self.assertEqual(self.client.get('/admin/').status_code, 404)

    @override_settings(ROOT_URLCONF='appPrincipal.tests')
    def test_listados_del_admin_cargan(self):
        self.client.force_login(Usuario.objects.create_superuser(email='root@example.com', password='x', nombre='Root'))
        for modelo in ['usuario', 'producto', 'venta', 'reclamo', 'opinion']:
            respuesta = self.client.get(f'/admin/appPrincipal/{modelo}/')
            self.assertEqual(respuesta.status_code, 200, modelo)


class PanelFiltrosTests(TestCase):  # filtro de fechas compartido por ventas, reclamos y devoluciones
    def setUp(self):
        from django.utils import timezone
        from .models import Venta
        self.hoy = timezone.localdate()
        self.venta = Venta.objects.create(usuario=crear_cliente(), metodo_envio='tienda')
        self.client.force_login(crear_cliente('jefe@example.com', is_staff=True))

    def test_fecha_fin_incluye_las_ventas_de_ese_mismo_dia(self):
        respuesta = self.client.get('/admin-panel/ventas/', {'fecha_inicio': self.hoy, 'fecha_fin': self.hoy})
        self.assertEqual(list(respuesta.context['ventas']), [self.venta])

    def test_fecha_futura_no_se_aplica_y_se_informa(self):
        from datetime import timedelta
        respuesta = self.client.get('/admin-panel/reclamos/', {'fecha_fin': self.hoy + timedelta(days=1)})
        self.assertEqual(respuesta.context['errores'], ["La fecha de fin no puede ser futura."])

    def test_fecha_imposible_se_ignora(self):
        respuesta = self.client.get('/admin-panel/devoluciones/', {'fecha_inicio': '2026-02-31'})
        self.assertEqual(respuesta.status_code, 200)


class PlantillasTests(TestCase):  # 21: plantilla base y navbar compartido
    def test_todas_las_paginas_heredan_de_una_plantilla_base(self):
        from pathlib import Path
        from django.conf import settings
        carpeta = Path(settings.BASE_DIR) / 'templates'
        bases = {'base.html'}
        for ruta in carpeta.rglob('*.html'):
            nombre = ruta.relative_to(carpeta).as_posix()
            if nombre in bases or 'partials/' in nombre:
                continue
            self.assertIn('{% extends ', ruta.read_text(encoding='utf-8'), nombre)

    def test_promos_del_navbar_vienen_de_la_portada(self):
        from .models import Destacado
        producto = Producto.objects.create(
            codigo_de_barra='333', nombre='Consola X', precio=1, stock=1, categoria='Ps5 Consolas',
            imagen_principal='productos/silent.png'
        )
        Destacado.objects.create(seccion='menu_consolas', titulo='Consola X', producto=producto, etiqueta='¡TOP!')
        respuesta = self.client.get('/menu/')
        self.assertContains(respuesta, f'href="/producto/{producto.id}/"')
        self.assertContains(respuesta, '¡TOP!')

    def test_la_portada_se_consulta_solo_al_usarse_y_una_vez(self):
        from .context_processors import Portada
        portada = Portada()
        with self.assertNumQueries(0):
            self.assertIsInstance(portada, Portada)
        with self.assertNumQueries(1):
            portada.carrusel
            portada.menu_consolas
            portada.lanzamientos
        with self.assertRaises(AttributeError):
            portada.no_existe


def elegir_entrega(client, metodo='tienda'):
    """Deja elegida la opción de entrega en la sesión, como al pasar del carrito al pago (HU-08)."""
    session = client.session
    session['metodo_envio'] = metodo
    session.save()


def crear_producto(nombre='Juego', stock=5, **extra):
    datos = {'codigo_de_barra': nombre[:20], 'precio': 10000, 'categoria': 'Videojuegos PS5',
             'imagen_principal': 'productos/silent.png', **extra}
    return Producto.objects.create(nombre=nombre, stock=stock, **datos)


def crear_venta(cliente, producto, cantidad=2, estado='Entregado'):
    from .models import Envio, ProductoVenta, Venta
    venta = Venta.objects.create(usuario=cliente, metodo_envio='tienda')
    ProductoVenta.objects.create(venta=venta, producto=producto, cantidad=cantidad, precio_unitario=producto.precio)
    Envio.objects.create(venta=venta, estado=estado)
    return venta


class CarritoTests(TestCase): 
    def setUp(self):
        self.producto = crear_producto(stock=3)
        self.client.force_login(crear_cliente())

    def agregar(self, cantidad, producto=None):
        return self.client.post(f'/agregar/{(producto or self.producto).id}/', {'cantidad': cantidad})

    def items(self):
        from .models import ItemCarritoProducto
        return list(ItemCarritoProducto.objects.values_list('cantidad', flat=True))

    def test_cantidad_invalida_o_negativa_se_rechaza(self):
        for cantidad in ['abc', '-2', '0', '']:
            self.assertEqual(self.agregar(cantidad).status_code, 400, cantidad)
        self.assertEqual(self.items(), [])

    def test_pasarse_del_stock_no_responde_exito_ni_agrega(self):
        self.assertTrue(self.agregar(2).json()['success'])
        respuesta = self.agregar(2).json()  
        self.assertFalse(respuesta['success'])
        self.assertIn('1 unidad', respuesta['error'])
        self.assertEqual(self.items(), [2])

    def test_sin_stock_no_se_crea_el_item(self):
        self.assertFalse(self.agregar(5).json()['success'])
        self.assertEqual(self.items(), [])

    def test_no_se_pueden_agregar_productos_eliminados(self):
        self.producto.delete()
        self.assertEqual(self.agregar(1).status_code, 404)
        self.assertEqual(self.client.get(f'/producto/{self.producto.id}/').status_code, 404)

    def test_agregar_por_get_no_esta_permitido(self):
        self.assertEqual(self.client.get(f'/agregar/{self.producto.id}/').status_code, 405)

    def test_actualizar_cantidad_con_texto_no_se_cae(self):
        from .models import ItemCarritoProducto
        self.agregar(1)
        item = ItemCarritoProducto.objects.get()
        self.assertEqual(self.client.post('/actualizar-cantidad/', {'item_id': item.id, 'cantidad': 'x'}).status_code, 400)
        self.assertEqual(self.client.post('/actualizar-cantidad/', {'item_id': 'x', 'cantidad': 1}).status_code, 400)

    def test_actualizar_sobre_el_stock_no_cambia_la_cantidad(self):
        from .models import ItemCarritoProducto
        self.agregar(1)
        item = ItemCarritoProducto.objects.get()
        respuesta = self.client.post('/actualizar-cantidad/', {'item_id': item.id, 'cantidad': 500}).json()
        self.assertFalse(respuesta['success'])
        self.assertEqual(self.items(), [1])

    def test_no_se_llega_al_pago_con_mas_cantidad_que_stock(self):
        self.agregar(3)
        self.producto.stock = 1
        self.producto.save()
        respuesta = self.client.get('/seleccionar-pago/')
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.url.startswith('/ver_carrito/?notif='))


class CheckoutTests(TestCase): 
    def setUp(self):
        from .models import Carrito, ItemCarritoProducto
        self.cliente = crear_cliente()
        self.client.force_login(self.cliente)
        self.con_stock = crear_producto('Con stock', stock=5)
        self.eliminado = crear_producto('Eliminado', stock=5)
        carrito = Carrito.objects.create(usuario=self.cliente)
        ItemCarritoProducto.objects.create(carrito=carrito, producto=self.con_stock, cantidad=2)
        ItemCarritoProducto.objects.create(carrito=carrito, producto=self.eliminado, cantidad=1)
        elegir_entrega(self.client)

    def test_producto_eliminado_en_el_carrito_no_deja_venta_ni_descuenta_stock(self):
        from .models import Venta
        self.eliminado.delete()
        respuesta = self.client.get('/compra-exitosa/')
        self.assertTrue(respuesta.url.startswith('/ver_carrito/'))
        self.assertFalse(Venta.objects.exists())
        self.con_stock.refresh_from_db()
        self.assertEqual(self.con_stock.stock, 5)

    def test_calcular_total_ya_no_toca_el_stock(self):
        from .models import Venta
        self.assertEqual(self.client.get('/compra-exitosa/').status_code, 200)
        venta = Venta.objects.get()
        venta.calcular_total()  
        self.con_stock.refresh_from_db()
        self.assertEqual(self.con_stock.stock, 3)
        self.assertEqual(venta.total, 30000)


class DevolucionesTests(TestCase):  
    def setUp(self):
        self.producto = crear_producto(stock=5)
        self.cliente = crear_cliente()
        self.venta = crear_venta(self.cliente, self.producto, cantidad=2)
        self.url = f'/devolucion/crear/{self.venta.id}/{self.producto.id}/'
        self.client.force_login(self.cliente)

    def pedir(self, cantidad):
        return self.client.post(self.url, {'cantidad': cantidad, 'descripcion': 'Llegó roto'})

    def responder_como_admin(self, devolucion, accion):
        jefe = Usuario.objects.filter(email='jefe@example.com').first() or crear_cliente('jefe@example.com', is_staff=True)
        self.client.force_login(jefe)
        url = f'/admin-panel/devoluciones/responder/{devolucion.id}/'
        return self.client.post(url, {'accion': accion, 'respuesta': 'ok'})

    def test_no_se_puede_devolver_mas_de_lo_comprado_ni_cantidades_negativas(self):
        from .models import Devolucion
        for cantidad in [3, 0, -5, 'abc']:
            self.pedir(cantidad)
        self.assertFalse(Devolucion.objects.exists())

    def test_lo_ya_solicitado_descuenta_de_lo_que_se_puede_devolver(self):
        from .models import Devolucion
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.pedir(1)
        self.pedir(2)  
        self.pedir(1)
        self.assertEqual(list(Devolucion.objects.values_list('cantidad', flat=True)), [1, 1])
        self.assertEqual(self.client.get(self.url).status_code, 302)  

    def test_solo_se_puede_devolver_una_compra_entregada(self):
        from .models import Devolucion, Envio
        Envio.objects.filter(venta=self.venta).update(estado='Enviado')
        self.pedir(1)
        self.assertFalse(Devolucion.objects.exists())

    def test_aprobar_dos_veces_repone_el_stock_una_sola_vez(self):
        from .models import Devolucion
        self.pedir(2)
        devolucion = Devolucion.objects.get()
        self.responder_como_admin(devolucion, 'aceptar')
        self.responder_como_admin(devolucion, 'aceptar')
        self.responder_como_admin(devolucion, 'rechazar')
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 7)
        self.assertEqual(Devolucion.objects.get().estado, 'Aprobada')

    def test_anular_una_venta_con_devolucion_aprobada_no_repone_dos_veces(self):
        from .models import Devolucion
        self.pedir(1)
        self.responder_como_admin(Devolucion.objects.get(), 'aceptar')
        self.client.post(f'/ventas/anular/{self.venta.id}/')
        self.client.post(f'/ventas/anular/{self.venta.id}/')
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 7) 

    def test_detalle_de_compra_con_devolucion_sin_producto_no_se_cae(self):  
        from .models import Devolucion
        Devolucion.objects.create(usuario=self.cliente, venta=self.venta, producto=None, motivo='x')
        self.assertEqual(self.client.get(f'/compra/{self.venta.id}/detalle/').status_code, 200)


class AccionesPorPostTests(TestCase): 
    def setUp(self):
        self.producto = crear_producto()
        self.cliente = crear_cliente()
        self.venta = crear_venta(self.cliente, self.producto, estado='Enviado')
        self.jefe = crear_cliente('jefe@example.com', is_staff=True)

    def test_acciones_del_panel_no_se_ejecutan_con_un_link(self):
        from .models import Envio
        self.client.force_login(self.jefe)
        for url in [f'/admin-panel/usuarios/eliminar/{self.cliente.id}/',
                    f'/admin-panel/productos/eliminar/{self.producto.id}/',
                    f'/ventas/anular/{self.venta.id}/']:
            self.assertEqual(self.client.get(url).status_code, 405, url)
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.is_active)
        self.assertTrue(Producto.objects.filter(id=self.producto.id).exists())
        self.assertEqual(Envio.objects.get().estado, 'Enviado')

    def test_acciones_del_panel_funcionan_por_post(self):
        self.client.force_login(self.jefe)
        self.client.post(f'/admin-panel/productos/eliminar/{self.producto.id}/')
        self.assertFalse(Producto.objects.filter(id=self.producto.id).exists())

    def test_marcar_recibido_solo_por_post(self):
        from .models import Envio
        self.client.force_login(self.cliente)
        url = f'/marcar-recibido/{self.venta.id}/'
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.assertEqual(Envio.objects.get().estado, 'Entregado')


class OpinionesTests(TestCase):  
    def setUp(self):
        self.producto = crear_producto()
        self.cliente = crear_cliente()
        self.client.force_login(self.cliente)
        self.url = f'/opinion/enviar/{self.producto.id}/'

    def opinar(self):
        return self.client.post(self.url, {'puntuacion': 5, 'comentario': 'Excelente'})

    def test_no_se_puede_opinar_sin_haber_comprado(self):
        from .models import Opinion
        self.opinar()
        self.assertFalse(Opinion.objects.exists())

    def test_no_se_puede_opinar_si_el_pedido_no_ha_llegado(self):
        from .models import Opinion
        crear_venta(self.cliente, self.producto, estado='Enviado')
        self.opinar()
        self.assertFalse(Opinion.objects.exists())

    def test_se_puede_opinar_un_producto_recibido(self):
        from .models import Opinion
        crear_venta(self.cliente, self.producto)
        self.opinar()
        self.assertTrue(Opinion.objects.filter(usuario=self.cliente, producto=self.producto).exists())


class RegionesTests(TestCase):  
    def test_cada_region_del_select_tiene_sus_ciudades(self):
        from .constants import REGIONES, REGIONES_CIUDADES
        self.assertEqual([codigo for codigo, _ in REGIONES], list(REGIONES_CIUDADES))

    def test_el_carrito_recibe_las_regiones_desde_constants(self):
        self.client.force_login(crear_cliente())
        self.assertContains(self.client.get('/ver_carrito/'), 'id="regiones-ciudades"')

    def test_datos_de_envio_se_validan(self):
        cliente = crear_cliente(region='LOS RIOS', ciudad='Valdivia', direccion='Picarte 1')
        self.client.force_login(cliente)
        malos = [
            {'region': 'LOS RIOS', 'ciudad': 'Santiago', 'direccion': 'Calle 1'}, 
            {'region': 'INVENTADA', 'ciudad': 'Valdivia', 'direccion': 'Calle 1'},
            {'region': 'LOS RIOS', 'ciudad': 'Valdivia', 'direccion': ''},
            {'region': 'LOS RIOS', 'ciudad': 'Valdivia', 'direccion': 'x' * 101},
        ]
        for datos in malos:
            self.assertEqual(self.client.post('/guardar_datos_envio/', datos).status_code, 400, datos)
        cliente.refresh_from_db()
        self.assertEqual((cliente.ciudad, cliente.direccion), ('Valdivia', 'Picarte 1'))

        self.client.post('/guardar_datos_envio/', {'region': 'LOS LAGOS', 'ciudad': 'Osorno', 'direccion': 'Calle 2'})
        cliente.refresh_from_db()
        self.assertEqual((cliente.region, cliente.ciudad), ('LOS LAGOS', 'Osorno'))


class DashboardTests(TestCase): 
    def test_grafico_suma_por_mes_sin_ventas_anuladas_en_una_consulta(self):
        from datetime import datetime
        from django.utils import timezone
        from .models import Venta
        from .views.panel.dashboard import ventas_por_mes
        producto = crear_producto()
        cliente = crear_cliente()
        anio = timezone.localdate().year
        marzo = crear_venta(cliente, producto)
        anulada = crear_venta(cliente, producto, estado='Anulada')
        abril = crear_venta(cliente, producto)
        Venta.objects.filter(id__in=[marzo.id, anulada.id]).update(
            fecha=timezone.make_aware(datetime(anio, 3, 10, 12)), total=1000)
        Venta.objects.filter(id=abril.id).update(fecha=timezone.make_aware(datetime(anio, 4, 1, 0, 30)), total=500)

        with self.assertNumQueries(1):
            totales = ventas_por_mes(anio)
        self.assertEqual(totales[2], 1000)
        self.assertEqual(totales[3], 500)
        self.assertEqual(sum(totales), 1500)


class ErroresInternosTests(TestCase): 
    def test_crear_usuario_no_muestra_el_detalle_del_error(self):
        from unittest import mock
        self.client.force_login(crear_cliente('jefe@example.com', is_staff=True))
        datos = {'nombre': 'Nuevo', 'email': 'nuevo@example.com', 'contraseña': 'Akaispace-2026!',
                 'confirmar_contraseña': 'Akaispace-2026!', 'rut': '12343455-2', 'region': 'LOS RIOS', 'ciudad': 'Valdivia'}
        with mock.patch('appPrincipal.views.panel.usuarios.Usuario.objects.create_user',
                        side_effect=RuntimeError('detalle interno secreto')), \
                self.assertLogs('appPrincipal', level='ERROR'):
            respuesta = self.client.post('/admin-panel/usuarios/crear/', datos)
        self.assertEqual(respuesta.status_code, 500)
        self.assertNotIn('secreto', respuesta.json()['message'])

    def test_eliminar_favoritos_con_datos_invalidos_responde_400(self):
        self.client.force_login(crear_cliente())
        for cuerpo in ['no es json', '{"ids": ["abc"]}', '[1, 2]']:
            respuesta = self.client.post('/eliminar_favoritos_seleccionados/', cuerpo, content_type='application/json')
            self.assertEqual(respuesta.status_code, 400, cuerpo)
            self.assertEqual(respuesta.json()['error'], 'Solicitud inválida.')

    def test_eliminar_favoritos_acepta_ids_como_texto(self):
        from .models import Favorito
        cliente = crear_cliente()
        favorito = Favorito.objects.create(usuario=cliente, producto=crear_producto())
        self.client.force_login(cliente)
        self.client.post('/eliminar_favoritos_seleccionados/', {'ids': [str(favorito.id)]}, content_type='application/json')
        self.assertFalse(Favorito.objects.exists())


class PortadaSitioTests(TestCase): 
    def setUp(self):
        from .models import Destacado
        Destacado.objects.all().delete() 
        self.producto = crear_producto('Juego Nuevo')

    def crear(self, **datos):
        from .models import Destacado
        return Destacado.objects.create(**datos)

    def test_carrusel_muestra_solo_los_activos_en_orden(self):
        self.crear(seccion='carrusel', titulo='Segundo', producto=self.producto, orden=2)
        self.crear(seccion='carrusel', titulo='Primero', producto=self.producto, orden=1)
        self.crear(seccion='carrusel', titulo='Oculto', producto=self.producto, orden=0, activo=False)
        html = self.client.get('/menu/').content.decode()
        self.assertNotIn('Oculto', html)
        self.assertLess(html.index('Primero'), html.index('Segundo'))
        self.assertIn(f'href="/producto/{self.producto.id}/"', html)

    def test_slide_con_producto_eliminado_no_lleva_al_producto(self):
        self.crear(seccion='carrusel', titulo='Ya no está', producto=self.producto)
        self.producto.delete()
        respuesta = self.client.get('/menu/')
        self.assertContains(respuesta, 'Ya no está')
        self.assertContains(respuesta, 'Producto no disponible')

    def test_lanzamientos_del_home_con_video_de_youtube(self):
        self.crear(seccion='lanzamientos', titulo='Juego 2027', texto='Muy esperado',
                   video_url='https://youtu.be/wFGEMfyAQtI')
        respuesta = self.client.get('/')
        self.assertContains(respuesta, 'Nuevos Lanzamientos')
        self.assertContains(respuesta, 'https://www.youtube.com/embed/wFGEMfyAQtI')

    def test_lanzamientos_alternan_el_lado_del_video(self):
        for i in range(2):
            self.crear(seccion='lanzamientos', titulo=f'Juego {i}', video_url='https://youtu.be/wFGEMfyAQtI', orden=i)
        self.assertContains(self.client.get('/'), 'order-md-2', count=1) 

    def test_sin_lanzamientos_la_seccion_no_aparece(self):
        self.assertNotContains(self.client.get('/'), 'Nuevos Lanzamientos')

    def test_promo_de_menu_muestra_el_primero_activo(self):
        self.crear(seccion='menu_figuras', titulo='Figura B', producto=self.producto, orden=2)
        self.crear(seccion='menu_figuras', titulo='Figura A', producto=self.producto, orden=1)
        html = self.client.get('/menu/').content.decode()
        self.assertIn('Figura A', html)
        self.assertNotIn('Figura B', html)

    def test_links_de_youtube_aceptados(self):
        from .models import youtube_embed_url
        esperado = 'https://www.youtube.com/embed/wFGEMfyAQtI'
        for url in ['https://www.youtube.com/watch?v=wFGEMfyAQtI', 'https://youtu.be/wFGEMfyAQtI?si=abc',
                    'https://www.youtube.com/embed/wFGEMfyAQtI', 'https://www.youtube.com/watch?t=5&v=wFGEMfyAQtI']:
            self.assertEqual(youtube_embed_url(url), esperado, url)
        self.assertEqual(youtube_embed_url('https://vimeo.com/123'), '')


class PortadaPanelTests(TestCase):  
    def setUp(self):
        self.producto = crear_producto('Juego Nuevo')
        self.client.force_login(crear_cliente('jefe@example.com', is_staff=True))

    def datos(self, **cambios):
        return {'seccion': 'carrusel', 'producto': self.producto.id, 'titulo': 'Slide nuevo',
                'texto': 'Texto', 'etiqueta': '', 'video_url': '', 'orden': 1, 'activo': 'on', **cambios}

    def test_listado_y_formulario_cargan(self):
        self.assertContains(self.client.get('/admin-panel/portada/'), 'Carrusel del menú')
        self.assertEqual(self.client.get('/admin-panel/portada/nuevo/?seccion=lanzamientos').status_code, 200)

    def test_crear_editar_ocultar_y_eliminar(self):
        from .models import Destacado
        self.assertRedirects(self.client.post('/admin-panel/portada/nuevo/', self.datos()), '/admin-panel/portada/')
        destacado = Destacado.objects.get(titulo='Slide nuevo')

        self.client.post(f'/admin-panel/portada/{destacado.id}/editar/', self.datos(titulo='Slide editado'))
        destacado.refresh_from_db()
        self.assertEqual(destacado.titulo, 'Slide editado')

        self.client.post(f'/admin-panel/portada/{destacado.id}/estado/')
        destacado.refresh_from_db()
        self.assertFalse(destacado.activo)

        self.assertEqual(self.client.get(f'/admin-panel/portada/{destacado.id}/eliminar/').status_code, 405)
        self.client.post(f'/admin-panel/portada/{destacado.id}/eliminar/')
        self.assertFalse(Destacado.objects.filter(id=destacado.id).exists())

    def test_carrusel_y_menus_necesitan_producto(self):
        for seccion in ['carrusel', 'menu_consolas']:
            respuesta = self.client.post('/admin-panel/portada/nuevo/', self.datos(seccion=seccion, producto=''))
            self.assertFormError(respuesta.context['form'], 'producto', 'Elige el producto al que lleva este destacado.')

    def test_lanzamiento_sin_producto_con_video_es_valido_y_link_invalido_no(self):
        from .models import Destacado
        self.client.post('/admin-panel/portada/nuevo/', self.datos(
            seccion='lanzamientos', producto='', titulo='Lanzamiento', video_url='https://youtu.be/wFGEMfyAQtI'))
        self.assertTrue(Destacado.objects.filter(titulo='Lanzamiento').exists())

        respuesta = self.client.post('/admin-panel/portada/nuevo/', self.datos(
            seccion='lanzamientos', producto='', video_url='https://vimeo.com/123'))
        self.assertIn('video_url', respuesta.context['form'].errors)

    def test_selector_muestra_el_nombre_del_producto(self):
        respuesta = self.client.get('/admin-panel/portada/nuevo/')
        self.assertContains(respuesta, 'Juego Nuevo · ')
        self.assertNotContains(respuesta, 'Producto object')

    def test_no_se_pasa_el_maximo_de_visibles(self):
        from .models import Destacado
        Destacado.objects.filter(seccion='lanzamientos').delete()
        maximo = Destacado.MAXIMO_VISIBLES['lanzamientos']
        for i in range(maximo):
            Destacado.objects.create(seccion='lanzamientos', titulo=f'L{i}', producto=self.producto)
        lleno = self.datos(seccion='lanzamientos', titulo='Uno más')

        respuesta = self.client.post('/admin-panel/portada/nuevo/', lleno)
        self.assertIn('activo', respuesta.context['form'].errors)
        lleno.pop('activo')
        self.client.post('/admin-panel/portada/nuevo/', lleno)
        oculto = Destacado.objects.get(titulo='Uno más', activo=False)
        self.client.post(f'/admin-panel/portada/{oculto.id}/estado/')
        oculto.refresh_from_db()
        self.assertFalse(oculto.activo)
        visible = Destacado.objects.get(titulo='L0')
        respuesta = self.client.post(f'/admin-panel/portada/{visible.id}/editar/',
                                     self.datos(seccion='lanzamientos', titulo='L0 editado'))
        self.assertRedirects(respuesta, '/admin-panel/portada/')

    def test_cliente_no_puede_editar_la_portada(self):
        self.client.force_login(crear_cliente())
        self.assertRedirects(self.client.get('/admin-panel/portada/'), '/', fetch_redirect_response=False)


class PortadaInicialTests(TestCase):  
    def test_migracion_crea_el_contenido_que_estaba_en_las_plantillas(self):
        from .models import Destacado
        self.assertEqual(Destacado.objects.filter(seccion='carrusel').count(), 3)
        self.assertEqual(Destacado.objects.filter(seccion='lanzamientos').count(), 2)
        self.assertEqual(Destacado.objects.filter(seccion__startswith='menu_').count(), 4)

    def test_cargar_enlaza_los_productos_y_no_duplica(self):
        from . import portada_inicial
        from .models import Destacado
        ps5 = crear_producto('Play Station 5')
        portada_inicial.cargar(Destacado, Producto)
        portada_inicial.cargar(Destacado, Producto)
        self.assertEqual(Destacado.objects.count(), 9)
        self.assertEqual(Destacado.objects.get(seccion='menu_consolas').producto, ps5)


class EnviosTests(TestCase):  
    def setUp(self):
        from .models import Carrito
        self.producto = crear_producto(stock=10) 
        self.carrito = Carrito.objects.create(usuario=crear_cliente())

    def cliente_en(self, ciudad, region='LOS RIOS', direccion='Picarte 123'):
        cliente = self.carrito.usuario
        cliente.ciudad, cliente.region, cliente.direccion = ciudad, region, direccion
        cliente.save()
        self.client.force_login(cliente)
        return cliente

    def comprar(self, metodo, cantidad=1):
        from .models import ItemCarritoProducto, Venta
        ItemCarritoProducto.objects.create(carrito=self.carrito, producto=self.producto, cantidad=cantidad)
        respuesta = self.client.get(f'/seleccionar-pago/?envio={metodo}')
        if respuesta.status_code != 200:
            return respuesta, None
        self.client.get('/compra-exitosa/')
        return respuesta, Venta.objects.get()

    def test_costos_de_cada_opcion(self):
        from .envios import costo_envio
        self.assertEqual(costo_envio('tienda', 10000), 0)
        self.assertEqual(costo_envio('delivery', 24989), 2000)
        self.assertEqual(costo_envio('delivery', 24990), 0)
        self.assertEqual(costo_envio('bluexpress', 50000), 4500)
        self.assertEqual(costo_envio('por_pagar', 10000), 0)

    def test_delivery_en_valdivia_cobra_2000_bajo_el_minimo(self):
        self.cliente_en('Valdivia')
        _, venta = self.comprar('delivery', cantidad=2)
        self.assertEqual((venta.subtotal, venta.envio, venta.total), (20000, 2000, 22000))
        self.assertEqual(venta.datos_envio.transportista, 'Delivery Akaispace')
        self.assertEqual(venta.direccion_envio, 'Picarte 123, Valdivia, Región de Los Ríos')

    def test_delivery_gratis_desde_24990(self):
        self.cliente_en('Valdivia')
        _, venta = self.comprar('delivery', cantidad=3)
        self.assertEqual((venta.envio, venta.total), (0, 30000))

    def test_delivery_solo_para_valdivia(self):
        from .models import Venta
        self.cliente_en('Osorno', region='LOS LAGOS')
        respuesta, _ = self.comprar('delivery')
        self.assertTrue(respuesta.url.startswith('/ver_carrito/?notif='))
        self.assertFalse(Venta.objects.exists())

    def test_envio_a_region_no_se_ofrece_en_valdivia(self):
        self.cliente_en('Valdivia')
        respuesta, _ = self.comprar('bluexpress')
        self.assertTrue(respuesta.url.startswith('/ver_carrito/?notif='))

    def test_bluexpress_fuera_de_valdivia(self):
        self.cliente_en('Osorno', region='LOS LAGOS')
        _, venta = self.comprar('bluexpress')
        self.assertEqual((venta.envio, venta.total), (4500, 14500))
        self.assertTrue(venta.lleva_seguimiento)

    def test_envio_por_pagar_no_se_cobra(self):
        self.cliente_en('Osorno', region='LOS LAGOS')
        _, venta = self.comprar('por_pagar')
        self.assertEqual((venta.envio, venta.total), (0, 10000))
        self.assertTrue(venta.envio_por_pagar)
        self.assertContains(self.client.get(f'/compra/{venta.id}/detalle/'), 'Por pagar al recibir')

    def test_retiro_en_tienda_es_gratis_y_no_pide_direccion(self):
        self.cliente_en('', region='', direccion='')
        _, venta = self.comprar('tienda')
        self.assertEqual(venta.envio, 0)
        self.assertTrue(venta.direccion_envio.startswith('Retiro en tienda: Galería Caupolicán 544'))
        self.assertEqual(venta.estados_envio, ['En Preparación', 'Listo para retiro', 'Entregado'])

    def test_despacho_sin_direccion_no_avanza(self):
        self.cliente_en('Osorno', region='LOS LAGOS', direccion='')
        respuesta, _ = self.comprar('bluexpress')
        self.assertTrue(respuesta.url.startswith('/ver_carrito/?notif='))

    def test_sin_elegir_entrega_vuelve_al_carrito(self):
        from .models import ItemCarritoProducto
        self.cliente_en('Valdivia')
        ItemCarritoProducto.objects.create(carrito=self.carrito, producto=self.producto)
        self.assertTrue(self.client.get('/seleccionar-pago/').url.startswith('/ver_carrito/?notif='))
        self.assertTrue(self.client.get('/compra-exitosa/').url.startswith('/ver_carrito/?notif='))

    def test_cambiar_de_ciudad_despues_de_elegir_invalida_la_entrega(self):
        from .models import ItemCarritoProducto, Venta
        cliente = self.cliente_en('Valdivia')
        ItemCarritoProducto.objects.create(carrito=self.carrito, producto=self.producto)
        self.client.get('/seleccionar-pago/?envio=delivery')
        cliente.ciudad, cliente.region = 'Osorno', 'LOS LAGOS'
        cliente.save()
        self.assertTrue(self.client.get('/compra-exitosa/').url.startswith('/ver_carrito/?notif='))
        self.assertFalse(Venta.objects.exists())

    def test_el_carrito_muestra_las_opciones(self):
        from .models import ItemCarritoProducto
        self.cliente_en('Valdivia')
        ItemCarritoProducto.objects.create(carrito=self.carrito, producto=self.producto)
        respuesta = self.client.get('/ver_carrito/')
        self.assertContains(respuesta, 'Delivery Express en Valdivia')
        self.assertContains(respuesta, 'Retiro en tienda')
        self.assertNotContains(respuesta, '5990')

    def test_venta_antigua_a_domicilio_conserva_su_envio(self):
        from .models import Venta
        venta = Venta.objects.create(usuario=self.carrito.usuario, metodo_envio='domicilio', envio=5990)
        venta.calcular_total()
        self.assertEqual(venta.envio, 5990)


class EnviosPanelTests(TestCase): 
    def setUp(self):
        self.client.force_login(crear_cliente('jefe@example.com', is_staff=True))

    def venta_con(self, metodo):
        venta = crear_venta(crear_cliente(), crear_producto(), estado='En Preparación')
        venta.metodo_envio = metodo
        venta.save()
        return venta

    def test_retiro_en_tienda_no_pasa_por_enviado(self):
        venta = self.venta_con('tienda')
        url = f'/admin-panel/ventas/modificar/{venta.id}/'
        self.assertContains(self.client.post(url, {'estado': 'Enviado'}), 'Estado no válido.')
        self.assertRedirects(self.client.post(url, {'estado': 'Entregado'}),
                             f'/admin-panel/ventas/detalle/{venta.id}/', fetch_redirect_response=False)
        venta.datos_envio.refresh_from_db()
        self.assertEqual(venta.datos_envio.estado, 'Entregado')

    def test_delivery_en_reparto_sin_numero_de_seguimiento(self):
        venta = self.venta_con('delivery')
        self.client.post(f'/admin-panel/ventas/modificar/{venta.id}/', {'estado': 'En Reparto'})
        venta.datos_envio.refresh_from_db()
        self.assertEqual(venta.datos_envio.estado, 'En Reparto')

    def test_encomienda_exige_transportista_valido(self):
        venta = self.venta_con('bluexpress')
        url = f'/admin-panel/ventas/modificar/{venta.id}/'
        respuesta = self.client.post(url, {'estado': 'Enviado', 'transportista': 'Otro', 'numero_seguimiento': 'ABC12345'})
        self.assertContains(respuesta, 'Selecciona un transportista válido.')
        self.client.post(url, {'estado': 'Enviado', 'transportista': 'Bluexpress', 'numero_seguimiento': 'ABC12345'})
        venta.datos_envio.refresh_from_db()
        self.assertEqual((venta.datos_envio.estado, venta.datos_envio.transportista), ('Enviado', 'Bluexpress'))

    def test_no_se_anula_desde_modificar(self):
        venta = self.venta_con('bluexpress')
        respuesta = self.client.post(f'/admin-panel/ventas/modificar/{venta.id}/', {'estado': 'Anulada'})
        self.assertContains(respuesta, 'Estado no válido.')


class ListoParaRetiroTests(TestCase):
    def setUp(self):
        self.cliente = crear_cliente()
        self.admin = crear_cliente('jefe@example.com', is_staff=True)
        self.venta = crear_venta(self.cliente, crear_producto(), estado='En Preparación')
        self.venta.metodo_envio = 'tienda'
        self.venta.save()
        self.envio = self.venta.datos_envio

    def cambiar_estado(self, estado, venta=None):
        venta = venta or self.venta
        self.client.force_login(self.admin)
        return self.client.post(f'/admin-panel/ventas/modificar/{venta.id}/', {'estado': estado})

    def detalle_cliente(self):
        self.client.force_login(self.cliente)
        return self.client.get(f'/compra/{self.venta.id}/detalle/')

    def test_en_preparacion_avisa_que_se_le_notificara(self):
        self.assertContains(self.detalle_cliente(), 'Cuando esté listo para retiro lo verás aquí')

    def test_listo_para_retiro_marca_fecha_y_muestra_donde_retirar(self):
        self.cambiar_estado('Listo para retiro')
        self.envio.refresh_from_db()
        self.assertEqual(self.envio.estado, 'Listo para retiro')
        self.assertIsNotNone(self.envio.fecha_listo_retiro)
        respuesta = self.detalle_cliente()
        self.assertContains(respuesta, 'Tu pedido está listo para retiro')
        self.assertContains(respuesta, 'Galería Caupolicán 544, Local 26')
        self.assertContains(respuesta, f'#{self.venta.id}')

    def test_al_entregarlo_se_muestra_como_retirado(self):
        self.cambiar_estado('Listo para retiro')
        self.cambiar_estado('Entregado')
        self.client.force_login(self.cliente)
        self.assertContains(self.client.get('/compras/'), 'Retirado')
        self.assertNotContains(self.detalle_cliente(), 'Tu pedido está listo para retiro')

    def test_el_cliente_no_puede_marcarlo_como_recibido(self):
        self.cambiar_estado('Listo para retiro')
        self.client.force_login(self.cliente)
        self.client.post(f'/marcar-recibido/{self.venta.id}/')
        self.envio.refresh_from_db()
        self.assertEqual(self.envio.estado, 'Listo para retiro')
        self.assertNotContains(self.detalle_cliente(), 'Marcar como recibido')

    def test_guardar_el_mismo_estado_no_cambia_la_fecha(self):
        self.envio.guardar_estado('Listo para retiro')
        primera = self.envio.fecha_listo_retiro
        self.envio.guardar_estado('Listo para retiro')
        self.assertEqual(self.envio.fecha_listo_retiro, primera)

    def test_delivery_no_puede_quedar_listo_para_retiro(self):
        venta = crear_venta(crear_cliente('otro@example.com'), crear_producto('Otro'), estado='En Preparación')
        venta.metodo_envio = 'delivery'
        venta.save()
        self.assertContains(self.cambiar_estado('Listo para retiro', venta), 'Estado no válido.')

    def test_panel_filtra_y_cuenta_los_pedidos_por_retirar(self):
        otra = crear_venta(crear_cliente('otro@example.com'), crear_producto('Otro'), estado='En Preparación')
        self.cambiar_estado('Listo para retiro')
        respuesta = self.client.get('/admin-panel/ventas/?estado=Listo+para+retiro')
        self.assertEqual([v.id for v in respuesta.context['ventas']], [self.venta.id])
        self.assertNotIn(otra.id, [v.id for v in respuesta.context['ventas']])
        self.assertEqual(self.client.get('/api/dashboard-counts/').json()['por_retirar'], 1)

    def test_filtro_por_tipo_de_entrega(self):
        crear_venta(crear_cliente('otro@example.com'), crear_producto('Otro')) 
        self.client.force_login(self.admin)
        respuesta = self.client.get('/admin-panel/ventas/?entrega=delivery')
        self.assertEqual(list(respuesta.context['ventas']), [])
