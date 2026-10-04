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
    }

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
        self.assertEqual(self.client.get('/seleccionar-pago/').status_code, 200)
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

        self.client.get(f'/ventas/anular/{self.venta.id}/')
        self.client.get(f'/ventas/anular/{self.venta.id}/')
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

    def test_destacados_del_navbar_vienen_del_context_processor(self):
        destacado = Producto.objects.create(
            codigo_de_barra='333', nombre='Play Station 5', precio=1, stock=1, categoria='Ps5 Consolas',
            imagen_principal='productos/silent.png'
        )
        respuesta = self.client.get('/menu/')
        self.assertContains(respuesta, f'href="/producto/{destacado.id}/"')

    def test_destacados_se_consultan_solo_al_usarse(self):
        from .context_processors import ProductosDestacados
        destacados = ProductosDestacados()
        with self.assertNumQueries(0):
            self.assertIsInstance(destacados, ProductosDestacados)
        with self.assertNumQueries(1):
            destacados.ps5
            destacados.ps5  # la segunda vez usa el caché
        with self.assertRaises(AttributeError):
            destacados.no_existe
