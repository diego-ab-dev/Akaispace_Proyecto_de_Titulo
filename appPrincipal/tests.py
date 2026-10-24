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


@override_settings(MEDIA_ROOT=__import__('tempfile').mkdtemp())
class SeedCatalogoTests(TestCase):  # HU-07: catálogo de prueba con atributos completos (KPI-10)
    def csv(self, *filas):
        import tempfile
        encabezado = 'codigo_de_barra,nombre,categoria,plataforma,genero,precio,costo,stock,stock_critico,descripcion\n'
        archivo = tempfile.NamedTemporaryFile('w', suffix='.csv', encoding='utf-8', delete=False)
        archivo.write(encabezado + ''.join(fila + '\n' for fila in filas))
        archivo.close()
        return archivo.name

    def test_carga_el_catalogo_completo_con_imagen_generica(self):
        import csv
        from .management.commands.seed_catalogo import FIXTURES_DIR
        with open(FIXTURES_DIR / 'catalogo.csv', encoding='utf-8') as archivo:
            total = sum(1 for _ in csv.DictReader(archivo))
        call_command('seed_catalogo', verbosity=0)
        self.assertEqual(Producto.objects.count(), total)
        self.assertGreaterEqual(total, 100)
        # KPI-10: cada producto tiene los atributos que exige su categoría
        for producto in Producto.objects.select_related('categoria'):
            if producto.categoria.requiere_plataforma:
                self.assertIsNotNone(producto.plataforma_id, producto.nombre)
            if producto.categoria.requiere_genero:
                self.assertIsNotNone(producto.genero_id, producto.nombre)
        elden = Producto.objects.get(codigo_de_barra='2000000000015')
        self.assertEqual(elden.imagen_principal.name, 'productos/generico_videojuegos.png')
        from django.core.files.storage import default_storage
        self.assertTrue(default_storage.exists('productos/generico_funko_pop.png'))

    def test_es_idempotente_y_no_toca_precio_ni_stock(self):
        from .models import ImagenProducto
        archivo = self.csv('2000000000015,Elden Ring,Videojuegos,ps5,RPG,39990,25000,10,5,RPG')
        call_command('seed_catalogo', archivo=archivo, verbosity=0)
        Producto.objects.filter(codigo_de_barra='2000000000015').update(stock=3, precio=35990)
        archivo = self.csv('2000000000015,Elden Ring GOTY,Videojuegos,ps5,Acción,39990,25000,10,5,RPG')
        call_command('seed_catalogo', archivo=archivo, verbosity=0)
        producto = Producto.objects.get(codigo_de_barra='2000000000015')
        self.assertEqual((producto.nombre, producto.genero.nombre), ('Elden Ring GOTY', 'Acción'))
        self.assertEqual((producto.stock, producto.precio), (3, 35990))
        self.assertEqual(Producto.objects.count(), 1)
        self.assertEqual(ImagenProducto.objects.filter(producto=producto).count(), 1)

    def test_respeta_productos_eliminados_e_imagenes_propias(self):
        from .models import ImagenProducto
        archivo = self.csv('2000000000015,Elden Ring,Videojuegos,ps5,RPG,39990,,10,5,',
                           '2000000000022,Tekken 8,Videojuegos,ps5,Acción,44990,,10,5,')
        call_command('seed_catalogo', archivo=archivo, verbosity=0)
        Producto.objects.get(codigo_de_barra='2000000000015').delete()
        tekken = Producto.objects.get(codigo_de_barra='2000000000022')
        tekken.imagenes_producto.all().delete()
        ImagenProducto.objects.create(producto=tekken, imagen='productos/tekken.png', es_principal=True)
        call_command('seed_catalogo', archivo=archivo, verbosity=0)
        self.assertFalse(Producto.objects.filter(codigo_de_barra='2000000000015').exists())
        self.assertEqual([i.imagen.name for i in tekken.imagenes_producto.all()], ['productos/tekken.png'])

    def test_una_fila_con_error_no_carga_nada(self):
        from django.core.management.base import CommandError
        archivo = self.csv('2000000000015,Elden Ring,Videojuegos,ps5,RPG,39990,,10,5,',
                           '2000000000022,Juego sin plataforma,Videojuegos,,RPG,19990,,10,5,',
                           '2000000000039,Otro,Videojuegos,ps9,RPG,19990,,10,5,')
        with self.assertRaises(CommandError) as contexto:
            call_command('seed_catalogo', archivo=archivo, verbosity=0)
        self.assertIn('Fila 3', str(contexto.exception))
        self.assertIn("plataforma 'ps9'", str(contexto.exception))
        self.assertFalse(Producto.objects.exists())


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
        'region': 'LOS RIOS', 'ciudad': 'Valdivia', 'declaracion_edad': 'mayor_18',
        'acepta_privacidad': 'on', 'autoriza_datos_navegacion': 'on',
    }

    def test_registro_guarda_los_consentimientos_y_la_version_aceptada(self):  # HU-01
        from .constants import POLITICA_PRIVACIDAD_VERSION
        self.assertTrue(self.client.post('/register/', self.datos).json()['success'])
        usuario = Usuario.objects.get(email='juan@example.com')
        self.assertEqual(usuario.declaracion_edad, Usuario.MAYOR_18)
        self.assertIsNotNone(usuario.privacidad_aceptada_en)
        self.assertIsNotNone(usuario.datos_navegacion_autorizados_en)
        self.assertEqual(usuario.privacidad_version, POLITICA_PRIVACIDAD_VERSION)

    def test_sin_aceptar_la_politica_no_se_crea_la_cuenta(self):  # HU-01
        datos = {k: v for k, v in self.datos.items() if k != 'acepta_privacidad'}
        respuesta = self.client.post('/register/', datos).json()
        self.assertFalse(respuesta['success'])
        self.assertIn('Política de Privacidad', respuesta['message'])
        self.assertFalse(Usuario.objects.exists())

    def test_la_declaracion_de_edad_es_obligatoria(self):  # HU-01
        for valor in [None, 'menor_sin_permiso']:
            datos = {k: v for k, v in self.datos.items() if k != 'declaracion_edad'}
            if valor:
                datos['declaracion_edad'] = valor
            respuesta = self.client.post('/register/', datos).json()
            self.assertFalse(respuesta['success'], valor)
        self.assertFalse(Usuario.objects.exists())
        datos = {**self.datos, 'declaracion_edad': 'autorizacion_tutor'}
        self.assertTrue(self.client.post('/register/', datos).json()['success'])
        self.assertEqual(Usuario.objects.get().declaracion_edad, Usuario.AUTORIZACION_TUTOR)

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
        self.assertContains(registro, 'Mayor de 18 años')
        self.assertContains(registro, 'Menor de 18 años con autorización de su padre, madre o tutor')
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
        for url in ['/perfil/', '/compras/', '/ver_carrito/', '/favorites/', '/seleccionar-pago/', f'/comprobante/{self.venta.id}/']:
            respuesta = self.client.get(url)
            self.assertRedirects(respuesta, f'/login/?next={url}', fetch_redirect_response=False, msg_prefix=url)

    def test_endpoints_ajax_responden_json_sin_sesion(self):
        respuesta = self.client.post('/agregar_favorito/1/')
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()['error'], 'not_logged_in')

    def test_no_se_puede_ver_la_compra_ni_el_comprobante_de_otro_usuario(self):
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(f'/compra/{self.venta.id}/detalle/').status_code, 404)
        self.assertEqual(self.client.get(f'/comprobante/{self.venta.id}/').status_code, 404)

    def test_el_dueño_si_ve_su_compra(self):
        self.client.force_login(self.dueño)
        self.assertEqual(self.client.get(f'/comprobante/{self.venta.id}/').status_code, 200)

    def test_cliente_no_entra_al_panel_admin(self):
        self.client.force_login(self.otro)
        self.assertRedirects(self.client.get('/admin-panel/'), '/', fetch_redirect_response=False)

    def test_admin_entra_al_panel(self):
        self.client.force_login(crear_cliente('jefe@example.com', is_staff=True))
        self.assertEqual(self.client.get('/admin-panel/').status_code, 200)


class CompraTests(TestCase):  # 1: el flujo de compra usa request.user, sin ids en la URL
    def setUp(self):
        self.producto = crear_producto('Juego', stock=3, codigo_de_barra='111')
        self.cliente = crear_cliente()
        self.client.force_login(self.cliente)

    def test_compra_completa_descuenta_stock_y_genera_comprobante(self):
        from .models import Venta
        self.client.post(f'/agregar/{self.producto.id}/', {'cantidad': 2})
        self.assertEqual(self.client.get('/seleccionar-pago/?envio=tienda').status_code, 200)
        _, pago = pagar(self.client)

        venta = Venta.objects.get(usuario=self.cliente)
        self.assertEqual(pago.venta, venta)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 1)
        self.assertTrue(hasattr(venta, 'comprobante'))
        self.assertEqual(self.client.get(f'/comprobante/{venta.id}/').status_code, 200)

    def test_sin_stock_no_queda_venta_a_medias(self):
        from .models import ItemCarritoProducto, Carrito, Venta
        carrito = Carrito.objects.create(usuario=self.cliente)
        ItemCarritoProducto.objects.create(carrito=carrito, producto=self.producto, cantidad=5)
        respuesta, pago = iniciar_pago(self.client, 'tienda')
        self.assertTrue(respuesta.url.startswith('/ver_carrito/'))
        self.assertIsNone(pago)
        self.assertFalse(Venta.objects.exists())
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 3)

    def test_no_se_puede_modificar_el_carrito_de_otro(self):
        from .models import ItemCarritoProducto, Carrito
        otro = crear_cliente('otro@example.com')
        item = ItemCarritoProducto.objects.create(carrito=Carrito.objects.create(usuario=otro), producto=self.producto)
        self.assertEqual(self.client.post('/actualizar-cantidad/', {'producto_id': item.producto_id, 'cantidad': 2}).status_code, 404)
        self.assertFalse(self.client.post(f'/eliminar/{item.producto_id}/').json()['success'])
        self.assertTrue(ItemCarritoProducto.objects.filter(pk=item.pk).exists())


class ModeloTests(TestCase):  # 17, 25, 26 y 28
    def setUp(self):
        from .models import Venta, ProductoVenta
        self.producto = crear_producto('Consola', stock=5, categoria='Consolas', codigo_de_barra='222', precio=1000)
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
        self.venta.refresh_from_db()
        self.assertTrue(self.venta.anulada)

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
        bases = {'base.html', 'correos/base.html'}  # los correos tienen su propia base
        for ruta in carpeta.rglob('*.html'):
            nombre = ruta.relative_to(carpeta).as_posix()
            if nombre in bases or 'partials/' in nombre:
                continue
            self.assertIn('{% extends ', ruta.read_text(encoding='utf-8'), nombre)

    def test_promos_del_navbar_vienen_de_la_portada(self):
        from .models import Destacado
        producto = crear_producto('Consola X', stock=1, categoria='Consolas', codigo_de_barra='333', precio=1)
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


URL_WEBPAY_PRUEBA = 'https://webpay3gint.transbank.cl/webpayserver/initTransaction'


def respuesta_webpay(pago, aprobado=True, **cambios):
    """Respuesta de commit como la que entrega Transbank (los tests no se conectan a Transbank)."""
    return {
        'vci': 'TSY', 'amount': pago.monto, 'status': 'AUTHORIZED' if aprobado else 'FAILED',
        'buy_order': pago.orden_compra, 'session_id': f'usuario-{pago.usuario_id}',
        'card_detail': {'card_number': '6623'}, 'accounting_date': '1006',
        'transaction_date': '2026-10-06T13:45:10.123Z', 'authorization_code': '1213' if aprobado else '000000',
        'payment_type_code': 'VD', 'response_code': 0 if aprobado else -1, 'installments_number': 0,
        **cambios,
    }


def iniciar_pago(client, envio=None):
    """Hace clic en "Pagar con Webpay". Devuelve (respuesta, PagoWebpay o None)."""
    import secrets
    from unittest import mock
    from .models import PagoWebpay
    token = secrets.token_hex(32)
    url = '/seleccionar-pago/' + (f'?envio={envio}' if envio else '')
    with mock.patch('appPrincipal.webpay.crear', return_value={'token': token, 'url': URL_WEBPAY_PRUEBA}):
        respuesta = client.post(url)
    return respuesta, PagoWebpay.objects.filter(token=token).first()


def volver_de_webpay(client, pago, aprobado=True, **cambios):
    """Transbank devuelve al cliente con token_ws (por GET) y el sitio confirma el pago."""
    from unittest import mock
    with mock.patch('appPrincipal.webpay.confirmar', return_value=respuesta_webpay(pago, aprobado, **cambios)):
        return client.get('/pago/webpay/retorno/', {'token_ws': pago.token})


def pagar(client, envio=None, aprobado=True):
    """Compra completa con Webpay simulado. Devuelve (respuesta al iniciar, PagoWebpay o None)."""
    respuesta, pago = iniciar_pago(client, envio)
    if pago is None:
        return respuesta, None
    volver_de_webpay(client, pago, aprobado)
    pago.refresh_from_db()
    return respuesta, pago


def elegir_entrega(client, metodo='tienda'):
    """Deja elegida la opción de entrega en la sesión, como al pasar del carrito al pago (HU-08)."""
    session = client.session
    session['metodo_envio'] = metodo
    session.save()


def crear_producto(nombre='Juego', stock=5, categoria='Videojuegos', plataforma='ps5', genero=None,
                   imagen='productos/silent.png', **extra):
    """categoria y genero van por nombre (ej. 'Videojuegos', 'Deportes'); plataforma por código (ej. 'ps5')."""
    from .models import Categoria, Genero, ImagenProducto, Plataforma
    datos = {'codigo_de_barra': nombre[:20], 'precio': 10000, **extra}
    producto = Producto.objects.create(
        nombre=nombre, stock=stock, categoria=Categoria.objects.get(nombre=categoria),
        plataforma=Plataforma.objects.get(codigo=plataforma) if plataforma else None,
        genero=Genero.objects.get(nombre=genero) if genero else None, **datos,
    )
    if imagen:
        ImagenProducto.objects.create(producto=producto, imagen=imagen, es_principal=True)
    return producto


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
        self.assertEqual(self.client.post('/actualizar-cantidad/', {'producto_id': item.producto_id, 'cantidad': 'x'}).status_code, 400)
        self.assertEqual(self.client.post('/actualizar-cantidad/', {'item_id': 'x', 'cantidad': 1}).status_code, 400)

    def test_actualizar_sobre_el_stock_no_cambia_la_cantidad(self):
        from .models import ItemCarritoProducto
        self.agregar(1)
        item = ItemCarritoProducto.objects.get()
        respuesta = self.client.post('/actualizar-cantidad/', {'producto_id': item.producto_id, 'cantidad': 500}).json()
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
        respuesta, _ = iniciar_pago(self.client)
        self.assertTrue(respuesta.url.startswith('/ver_carrito/'))
        self.assertFalse(Venta.objects.exists())
        self.con_stock.refresh_from_db()
        self.assertEqual(self.con_stock.stock, 5)

    def test_calcular_total_ya_no_toca_el_stock(self):
        from .models import Venta
        pagar(self.client)
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

    def pedir(self, cantidad, **fotos):
        datos = {'cantidad': cantidad, 'descripcion': 'Llegó roto',
                 'imagenes-TOTAL_FORMS': '3', 'imagenes-INITIAL_FORMS': '0', **fotos}
        return self.client.post(self.url, datos)

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

    def test_la_devolucion_exige_venta_y_producto(self):
        from django.db import IntegrityError, transaction
        from .models import Devolucion
        for faltante in [{'venta': None}, {'producto': None}]:
            datos = {'usuario': self.cliente, 'venta': self.venta, 'producto': self.producto, 'motivo': 'x', **faltante}
            with self.assertRaises(IntegrityError), transaction.atomic():
                Devolucion.objects.create(**datos)

    def test_las_fotos_de_evidencia_quedan_en_imagen_devolucion(self):
        import shutil, tempfile
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import Devolucion
        gif = (b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,'
               b'\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        with self.settings(MEDIA_ROOT=media):
            self.pedir(1, **{'imagenes-0-imagen': SimpleUploadedFile('foto1.png', gif, 'image/png'),
                             'imagenes-2-imagen': SimpleUploadedFile('foto3.png', gif, 'image/png')})
            devolucion = Devolucion.objects.get()
            self.assertEqual(devolucion.imagenes.count(), 2)
            self.assertContains(self.client.get(f'/devoluciones/{devolucion.id}/detalle/'), 'Evidencia 2')

    def test_foto_con_formato_no_permitido_no_crea_la_devolucion(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import Devolucion
        self.pedir(1, **{'imagenes-0-imagen': SimpleUploadedFile('foto.txt', b'hola', 'text/plain')})
        self.assertFalse(Devolucion.objects.exists())


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
        self.client.post('/eliminar_favoritos_seleccionados/', {'ids': [str(favorito.producto_id)]}, content_type='application/json')
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
        self.assertContains(respuesta, 'https://www.youtube-nocookie.com/embed/wFGEMfyAQtI')

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
        esperado = 'https://www.youtube-nocookie.com/embed/wFGEMfyAQtI'
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
        from .models import ItemCarritoProducto
        ItemCarritoProducto.objects.create(carrito=self.carrito, producto=self.producto, cantidad=cantidad)
        respuesta, pago = pagar(self.client, metodo)
        return respuesta, pago.venta if pago else None

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
        self.assertTrue(iniciar_pago(self.client)[0].url.startswith('/ver_carrito/?notif='))

    def test_cambiar_de_ciudad_despues_de_elegir_invalida_la_entrega(self):
        from .models import ItemCarritoProducto, Venta
        cliente = self.cliente_en('Valdivia')
        ItemCarritoProducto.objects.create(carrito=self.carrito, producto=self.producto)
        self.client.get('/seleccionar-pago/?envio=delivery')
        cliente.ciudad, cliente.region = 'Osorno', 'LOS LAGOS'
        cliente.save()
        respuesta, pago = iniciar_pago(self.client)
        self.assertTrue(respuesta.url.startswith('/ver_carrito/?notif='))
        self.assertIsNone(pago)
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


class WebpayTests(TestCase):  # HU-05 y HU-06: pago con Webpay Plus (Transbank simulado con mock)
    def setUp(self):
        from .models import Carrito, ItemCarritoProducto
        self.cliente = crear_cliente()
        self.client.force_login(self.cliente)
        self.producto = crear_producto(stock=5)  # $10.000 c/u
        self.carrito = Carrito.objects.create(usuario=self.cliente)
        self.item = ItemCarritoProducto.objects.create(carrito=self.carrito, producto=self.producto, cantidad=2)
        elegir_entrega(self.client)

    def stock(self):
        self.producto.refresh_from_db()
        return self.producto.stock

    def test_pagina_de_pago_no_pide_datos_de_tarjeta(self):
        respuesta = self.client.get('/seleccionar-pago/')
        self.assertContains(respuesta, 'Pagar con Webpay')
        self.assertNotContains(respuesta, 'numero_tarjeta')
        self.assertNotContains(respuesta, 'Transferencia')
        self.assertNotContains(respuesta, 'cvv')

    def test_iniciar_crea_pago_pendiente_y_envia_a_webpay_sin_tocar_stock(self):
        from .models import PagoWebpay, Venta
        respuesta, pago = iniciar_pago(self.client)
        self.assertContains(respuesta, URL_WEBPAY_PRUEBA)
        self.assertContains(respuesta, f'name="token_ws" value="{pago.token}"')
        self.assertEqual(pago.estado, PagoWebpay.PENDIENTE)
        self.assertEqual(pago.monto, 20000)
        self.assertEqual(list(pago.detalles.values('producto_id', 'cantidad', 'precio_unitario')),
                         [{'producto_id': self.producto.id, 'cantidad': 2, 'precio_unitario': 10000}])
        self.assertEqual(self.stock(), 5)
        self.assertFalse(Venta.objects.exists())

    def test_iniciar_envia_a_transbank_monto_orden_y_url_de_retorno(self):
        from unittest import mock
        with mock.patch('appPrincipal.webpay.crear', return_value={'token': 'a' * 64, 'url': URL_WEBPAY_PRUEBA}) as crear:
            self.client.post('/seleccionar-pago/')
        orden, sesion, monto, url_retorno = crear.call_args.args
        self.assertTrue(orden.startswith('AKA') and len(orden) <= 26)
        self.assertEqual(monto, 20000)
        self.assertEqual(url_retorno, 'http://testserver/pago/webpay/retorno/')

    def test_pago_aprobado_crea_venta_descuenta_stock_y_vacia_carrito(self):
        from .models import PagoWebpay
        _, pago = iniciar_pago(self.client)
        respuesta = volver_de_webpay(self.client, pago)
        self.assertRedirects(respuesta, f'/pago/{pago.id}/resultado/', fetch_redirect_response=False)
        pago.refresh_from_db()
        self.assertEqual(pago.estado, PagoWebpay.APROBADO)
        venta = pago.venta
        self.assertEqual((venta.total, venta.metodo_pago, venta.metodo_pago_texto), (20000, 'webpay', 'Webpay - Débito'))
        self.assertTrue(hasattr(venta, 'comprobante'))
        self.assertEqual(self.stock(), 3)
        self.assertFalse(self.carrito.items.exists())
        self.assertEqual((pago.codigo_autorizacion, pago.tarjeta_ultimos_digitos), ('1213', '6623'))

    def test_pago_aprobado_deja_el_carrito_en_el_historial(self):  # KPI-04
        from .models import Carrito
        _, pago = pagar(self.client)
        self.carrito.refresh_from_db()
        self.assertEqual(pago.carrito, self.carrito)
        self.assertIsNone(self.carrito.vigente)
        self.assertIsNotNone(self.carrito.convertido_en)
        self.assertFalse(Carrito.objects.filter(usuario=self.cliente).exists())
        self.assertEqual(Carrito.todos.filter(usuario=self.cliente).count(), 1)

    def test_comprobante_muestra_los_datos_de_transbank(self):
        _, pago = pagar(self.client)
        respuesta = self.client.get(f'/pago/{pago.id}/resultado/')
        self.assertContains(respuesta, '¡Compra Exitosa!')
        for dato in [pago.orden_compra, '1213', '**** 6623', 'Débito', '$20.000']:
            self.assertContains(respuesta, dato)

    def test_pago_rechazado_no_crea_venta_ni_toca_stock_ni_carrito(self):
        from .models import PagoWebpay, Venta
        _, pago = pagar(self.client, aprobado=False)
        self.assertEqual(pago.estado, PagoWebpay.RECHAZADO)
        self.assertFalse(Venta.objects.exists())
        self.assertEqual(self.stock(), 5)
        self.assertTrue(self.carrito.items.exists())
        self.assertContains(self.client.get(f'/pago/{pago.id}/resultado/'), 'Pago rechazado')

    def test_cliente_cancela_en_webpay(self):
        from .models import PagoWebpay, Venta
        _, pago = iniciar_pago(self.client)
        # al anular, Transbank devuelve TBK_TOKEN (y no token_ws), por POST
        respuesta = self.client.post('/pago/webpay/retorno/', {
            'TBK_TOKEN': pago.token, 'TBK_ORDEN_COMPRA': pago.orden_compra, 'TBK_ID_SESION': 'x',
        })
        self.assertRedirects(respuesta, f'/pago/{pago.id}/resultado/', fetch_redirect_response=False)
        pago.refresh_from_db()
        self.assertEqual(pago.estado, PagoWebpay.ANULADO)
        self.assertFalse(Venta.objects.exists())
        self.assertContains(self.client.get(f'/pago/{pago.id}/resultado/'), 'Pago cancelado')

    def test_error_en_el_formulario_y_volver_no_confirma(self):
        # si hubo un error en Webpay y el cliente volvió, llegan token_ws y TBK_TOKEN: no se confirma
        from unittest import mock
        from .models import PagoWebpay
        _, pago = iniciar_pago(self.client)
        with mock.patch('appPrincipal.webpay.confirmar') as confirmar:
            self.client.post('/pago/webpay/retorno/', {'token_ws': pago.token, 'TBK_TOKEN': pago.token})
        confirmar.assert_not_called()
        pago.refresh_from_db()
        self.assertEqual(pago.estado, PagoWebpay.ANULADO)

    def test_se_acaba_el_tiempo_en_webpay(self):
        from .models import PagoWebpay
        _, pago = iniciar_pago(self.client)
        self.client.post('/pago/webpay/retorno/', {'TBK_ORDEN_COMPRA': pago.orden_compra, 'TBK_ID_SESION': 'x'})
        pago.refresh_from_db()
        self.assertEqual(pago.estado, PagoWebpay.ANULADO)
        self.assertIn('tiempo', pago.detalle)

    def test_volver_dos_veces_no_duplica_la_venta(self):
        from unittest import mock
        from .models import Venta
        _, pago = iniciar_pago(self.client)
        volver_de_webpay(self.client, pago)
        with mock.patch('appPrincipal.webpay.confirmar') as confirmar:
            respuesta = self.client.get('/pago/webpay/retorno/', {'token_ws': pago.token})
        confirmar.assert_not_called()
        self.assertRedirects(respuesta, f'/pago/{pago.id}/resultado/', fetch_redirect_response=False)
        self.assertEqual(Venta.objects.count(), 1)
        self.assertEqual(self.stock(), 3)

    def test_retorno_por_post_sin_sesion_confirma_igual(self):
        # si Transbank vuelve por POST el navegador no manda la cookie de sesión
        from django.test import Client
        from .models import PagoWebpay
        _, pago = iniciar_pago(self.client)
        anonimo = Client(enforce_csrf_checks=True)
        from unittest import mock
        with mock.patch('appPrincipal.webpay.confirmar', return_value=respuesta_webpay(pago)):
            respuesta = anonimo.post('/pago/webpay/retorno/', {'token_ws': pago.token})
        self.assertEqual(respuesta.status_code, 302)
        pago.refresh_from_db()
        self.assertEqual(pago.estado, PagoWebpay.APROBADO)

    def test_sin_stock_al_volver_se_reembolsa(self):
        # otro cliente compró la última unidad mientras este estaba en Webpay
        from unittest import mock
        from .models import PagoWebpay, Venta
        _, pago = iniciar_pago(self.client)
        self.producto.stock = 1
        self.producto.save()
        with mock.patch('appPrincipal.webpay.reembolsar', return_value={'type': 'REVERSED'}) as reembolsar:
            volver_de_webpay(self.client, pago)
        reembolsar.assert_called_once_with(pago.token, 20000)
        pago.refresh_from_db()
        self.assertEqual(pago.estado, PagoWebpay.REEMBOLSADO)
        self.assertFalse(Venta.objects.exists())
        self.assertEqual(self.stock(), 1)
        self.assertContains(self.client.get(f'/pago/{pago.id}/resultado/'), 'Reversamos el cargo completo')

    def test_si_el_reembolso_falla_queda_en_error_para_revisar(self):
        from unittest import mock
        from .models import PagoWebpay
        from .webpay import ErrorWebpay
        _, pago = iniciar_pago(self.client)
        self.producto.stock = 0
        self.producto.save()
        with mock.patch('appPrincipal.webpay.reembolsar', side_effect=ErrorWebpay('caído')):
            volver_de_webpay(self.client, pago)
        pago.refresh_from_db()
        self.assertEqual(pago.estado, PagoWebpay.ERROR)
        self.assertIn('No se pudo reversar', pago.detalle)

    def test_monto_distinto_al_cobrado_no_entrega_la_compra(self):
        from unittest import mock
        from .models import PagoWebpay, Venta
        _, pago = iniciar_pago(self.client)
        with mock.patch('appPrincipal.webpay.reembolsar', return_value={}):
            volver_de_webpay(self.client, pago, amount=1)
        pago.refresh_from_db()
        self.assertEqual(pago.estado, PagoWebpay.REEMBOLSADO)
        self.assertFalse(Venta.objects.exists())

    def test_se_cobra_el_precio_del_momento_de_pagar(self):
        _, pago = iniciar_pago(self.client)
        self.producto.precio = 99990  # el admin cambió el precio mientras el cliente pagaba
        self.producto.save()
        volver_de_webpay(self.client, pago)
        pago.refresh_from_db()
        self.assertEqual(pago.venta.total, 20000)

    def test_lo_agregado_al_carrito_mientras_pagaba_se_conserva(self):
        from .models import Carrito, ItemCarritoProducto
        _, pago = iniciar_pago(self.client)
        otro = crear_producto('Otro')
        ItemCarritoProducto.objects.create(carrito=self.carrito, producto=otro)
        self.item.cantidad = 3
        self.item.save()
        volver_de_webpay(self.client, pago)
        vigente = Carrito.objects.get(usuario=self.cliente)
        self.assertNotEqual(vigente, self.carrito)
        quedan = {i.producto_id: i.cantidad for i in vigente.items.all()}
        self.assertEqual(quedan, {otro.id: 1, self.producto.id: 1})

    def test_transbank_caido_al_iniciar(self):
        from unittest import mock
        from .models import PagoWebpay
        from .webpay import ErrorWebpay
        with mock.patch('appPrincipal.webpay.crear', side_effect=ErrorWebpay('timeout')):
            respuesta = self.client.post('/seleccionar-pago/')
        self.assertContains(respuesta, 'No pudimos conectarnos con Webpay')
        self.assertEqual(PagoWebpay.objects.get().estado, PagoWebpay.ERROR)

    def test_no_se_puede_ver_el_resultado_de_otro_cliente(self):
        _, pago = pagar(self.client)
        self.client.force_login(crear_cliente('otro@example.com'))
        self.assertEqual(self.client.get(f'/pago/{pago.id}/resultado/').status_code, 404)

    def test_token_desconocido_vuelve_al_carrito(self):
        respuesta = self.client.get('/pago/webpay/retorno/', {'token_ws': 'no-existe'})
        self.assertTrue(respuesta.url.startswith('/ver_carrito/?notif='))


class WebpayConexionTests(TestCase):  # appPrincipal/webpay.py
    def test_si_el_commit_falla_pero_transbank_lo_autorizo_no_se_pierde(self):
        from unittest import mock
        from . import webpay
        autorizado = {'status': 'AUTHORIZED', 'response_code': 0}
        with mock.patch.object(webpay, '_llamar', side_effect=[webpay.ErrorWebpay('corte'), autorizado]):
            self.assertEqual(webpay.confirmar('t'), autorizado)

    def test_si_el_commit_falla_y_no_esta_autorizado_es_error(self):
        from unittest import mock
        from . import webpay
        with mock.patch.object(webpay, '_llamar', side_effect=[webpay.ErrorWebpay('corte'), {'status': 'FAILED'}]):
            with self.assertRaises(webpay.ErrorWebpay):
                webpay.confirmar('t')

    def test_errores_de_red_salen_como_error_webpay(self):
        import requests
        from unittest import mock
        from . import webpay
        with mock.patch('transbank.webpay.webpay_plus.transaction.RequestService.post',
                        side_effect=requests.ConnectionError('sin red')):
            with self.assertRaises(webpay.ErrorWebpay):
                webpay.crear('AKA1', 's', 1000, 'http://testserver/')

    @override_settings(WEBPAY_AMBIENTE='produccion', WEBPAY_CODIGO_COMERCIO='', WEBPAY_API_KEY='')
    def test_produccion_sin_credenciales_no_arranca(self):
        from django.core.exceptions import ImproperlyConfigured
        from . import webpay
        with self.assertRaises(ImproperlyConfigured):
            webpay.crear('AKA1', 's', 1000, 'http://testserver/')


class CorreoCompraTests(TestCase):  # HU-06: correo de confirmación al aprobarse el pago
    def setUp(self):
        from .models import Carrito, ItemCarritoProducto
        self.cliente = crear_cliente()
        self.client.force_login(self.cliente)
        self.producto = crear_producto(stock=5)  # $10.000 c/u
        carrito = Carrito.objects.create(usuario=self.cliente)
        ItemCarritoProducto.objects.create(carrito=carrito, producto=self.producto, cantidad=2)
        elegir_entrega(self.client)

    def test_pago_aprobado_envia_el_detalle_las_condiciones_y_el_retracto(self):
        from django.core import mail
        _, pago = pagar(self.client)
        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertEqual(correo.to, ['cliente@example.com'])
        self.assertIn(f'Nº {pago.venta.id}', correo.subject)
        html = correo.alternatives[0][0]
        datos = ['Juego', '$20.000', 'Retiro en tienda', pago.orden_compra, '**** 6623',
                 'Garantía legal', '10 días corridos', f'http://localhost:8000/comprobante/{pago.venta.id}/']
        for texto in [correo.body, html]:  # versión de texto y HTML
            for dato in datos:
                self.assertIn(dato, texto)

    def test_pago_rechazado_no_envia_correo(self):
        from django.core import mail
        pagar(self.client, aprobado=False)
        self.assertEqual(mail.outbox, [])

    def test_volver_dos_veces_no_repite_el_correo(self):
        from django.core import mail
        _, pago = pagar(self.client)
        volver_de_webpay(self.client, pago)
        self.assertEqual(len(mail.outbox), 1)

    def test_si_el_correo_falla_la_compra_igual_queda_aprobada(self):
        import smtplib
        from unittest import mock
        from .models import PagoWebpay
        with mock.patch('django.core.mail.EmailMultiAlternatives.send', side_effect=smtplib.SMTPException('caído')), \
                self.assertLogs('appPrincipal.correos', level='ERROR'):
            respuesta, pago = pagar(self.client)
        self.assertEqual(pago.estado, PagoWebpay.APROBADO)
        self.assertEqual(self.producto.__class__.objects.get(pk=self.producto.pk).stock, 3)


class RecuperarContraseñaTests(TestCase):  # HU-11
    def setUp(self):
        self.usuario = crear_cliente()

    def pedir_enlace(self, email='cliente@example.com'):
        return self.client.post('/recuperar-contrasena/', {'email': email})

    def enlace_del_correo(self):
        import re
        from django.core import mail
        return re.search(r'http://testserver(/recuperar-contrasena/\S+/\S+/)', mail.outbox[-1].body).group(1)

    def test_el_login_enlaza_a_recuperar_contraseña(self):
        self.assertContains(self.client.get('/login/'), 'href="/recuperar-contrasena/"')

    def test_envia_un_enlace_al_correo_registrado(self):
        from django.core import mail
        respuesta = self.pedir_enlace('CLIENTE@example.com')
        self.assertRedirects(respuesta, '/recuperar-contrasena/enviado/')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['cliente@example.com'])
        self.assertIn('1 hora', mail.outbox[0].body)

    def test_correo_no_registrado_muestra_lo_mismo_y_no_envia_nada(self):
        from django.core import mail
        respuesta = self.pedir_enlace('nadie@example.com')
        self.assertRedirects(respuesta, '/recuperar-contrasena/enviado/')
        self.assertEqual(mail.outbox, [])

    def test_usuario_eliminado_no_recibe_enlace(self):
        from django.core import mail
        self.usuario.delete()
        self.pedir_enlace()
        self.assertEqual(mail.outbox, [])

    def test_el_enlace_permite_crear_una_nueva_contraseña(self):
        self.pedir_enlace()
        formulario = self.client.get(self.enlace_del_correo(), follow=True)
        self.assertContains(formulario, 'Crea tu nueva contraseña')
        respuesta = self.client.post(formulario.redirect_chain[-1][0],
                                     {'new_password1': 'NuevaClave-2027', 'new_password2': 'NuevaClave-2027'})
        self.assertRedirects(respuesta, '/recuperar-contrasena/listo/')
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password('NuevaClave-2027'))

    def test_el_enlace_solo_sirve_una_vez(self):
        self.pedir_enlace()
        enlace = self.enlace_del_correo()
        formulario = self.client.get(enlace, follow=True)
        self.client.post(formulario.redirect_chain[-1][0],
                         {'new_password1': 'NuevaClave-2027', 'new_password2': 'NuevaClave-2027'})
        self.assertContains(self.client.get(enlace, follow=True), 'El enlace ya no es válido')

    def test_el_enlace_vence_en_una_hora(self):
        from datetime import timedelta
        from unittest import mock
        from django.contrib.auth.tokens import PasswordResetTokenGenerator
        self.pedir_enlace()
        enlace = self.enlace_del_correo()
        mas_tarde = PasswordResetTokenGenerator()._now() + timedelta(hours=1, minutes=1)
        with mock.patch.object(PasswordResetTokenGenerator, '_now', return_value=mas_tarde):
            self.assertContains(self.client.get(enlace, follow=True), 'El enlace ya no es válido')

    def test_la_nueva_contraseña_cumple_las_reglas(self):  # RNF-01
        self.pedir_enlace()
        formulario = self.client.get(self.enlace_del_correo(), follow=True)
        respuesta = self.client.post(formulario.redirect_chain[-1][0],
                                     {'new_password1': 'abcdefgh', 'new_password2': 'abcdefgh'})
        self.assertEqual(respuesta.status_code, 200)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password('Akaispace-2026!'))

    def test_desbloquea_el_login_tras_intentos_fallidos(self):
        for _ in range(5):
            self.client.post('/login/', {'email': 'cliente@example.com', 'contraseña': 'incorrecta'})
        self.pedir_enlace()
        formulario = self.client.get(self.enlace_del_correo(), follow=True)
        self.client.post(formulario.redirect_chain[-1][0],
                         {'new_password1': 'NuevaClave-2027', 'new_password2': 'NuevaClave-2027'})
        respuesta = self.client.post('/login/', {'email': 'cliente@example.com', 'contraseña': 'NuevaClave-2027'})
        self.assertRedirects(respuesta, '/', fetch_redirect_response=False)


class FiltrosCatalogoTests(TestCase):  # HU-17: buscar y filtrar por género, plataforma y precio
    def setUp(self):
        from .models import Categoria, Genero
        crear_producto('Zelda Switch', plataforma='switch', genero='Aventura', precio=45000)
        crear_producto('FIFA PS5', plataforma='ps5', genero='Deportes', precio=50000)
        crear_producto('Control PS5', categoria='Accesorios', plataforma='ps5', precio=60000)
        crear_producto('Gran Turismo PS4', plataforma='ps4', genero='Carreras', precio=15000)
        self.deportes = str(Genero.objects.get(nombre='Deportes').id)
        self.videojuegos = Categoria.objects.get(nombre='Videojuegos')

    def nombres(self, respuesta):
        return {p.nombre for p in respuesta.context['productos']}

    def test_filtra_por_genero(self):
        respuesta = self.client.get('/menu/', {'genero': self.deportes})
        self.assertEqual(self.nombres(respuesta), {'FIFA PS5'})
        self.assertContains(respuesta, 'Género: Deportes')

    def test_filtra_por_plataforma_juntando_juegos_consolas_y_accesorios(self):
        respuesta = self.client.get('/menu/', {'plataforma': 'ps5'})
        self.assertEqual(self.nombres(respuesta), {'FIFA PS5', 'Control PS5'})

    def test_filtra_por_rango_de_precio_con_formato_chileno(self):
        respuesta = self.client.get('/menu/', {'precio_min': '20.000', 'precio_max': '$50.000'})
        self.assertEqual(self.nombres(respuesta), {'Zelda Switch', 'FIFA PS5'})
        self.assertContains(respuesta, 'Precio: $20.000 a $50.000')

    def test_combina_busqueda_y_filtros(self):
        respuesta = self.client.get('/menu/', {'buscar': 'PS5', 'precio_max': '55000'})
        self.assertTemplateUsed(respuesta, 'resultado_busqueda.html')
        self.assertEqual(self.nombres(respuesta), {'FIFA PS5'})

    def test_filtros_en_categoria_y_plataforma_sin_selector_de_plataforma(self):
        url = f'/productos/{self.videojuegos.id}/ps5/'
        respuesta = self.client.get(url, {'genero': self.deportes, 'plataforma': 'switch'})
        self.assertEqual(self.nombres(respuesta), {'FIFA PS5'})
        self.assertNotContains(respuesta, 'name="plataforma"')
        self.assertContains(respuesta, 'Videojuegos PlayStation 5')

    def test_categoria_sin_plataforma_en_la_url_muestra_el_selector(self):
        respuesta = self.client.get(f'/productos/{self.videojuegos.id}/', {'plataforma': 'ps4'})
        self.assertEqual(self.nombres(respuesta), {'Gran Turismo PS4'})
        self.assertContains(respuesta, 'name="plataforma"')

    def test_categoria_o_plataforma_inexistente_da_404(self):
        self.assertEqual(self.client.get('/productos/9999/').status_code, 404)
        self.assertEqual(self.client.get(f'/productos/{self.videojuegos.id}/gameboy/').status_code, 404)

    def test_precio_minimo_mayor_al_maximo_avisa_y_no_filtra(self):
        respuesta = self.client.get('/menu/', {'precio_min': '50000', 'precio_max': '10000'})
        self.assertContains(respuesta, 'El precio mínimo no puede ser mayor que el máximo.')
        self.assertEqual(len(self.nombres(respuesta)), 4)

    def test_precio_invalido_avisa_y_no_filtra(self):
        respuesta = self.client.get('/menu/', {'precio_min': 'abc'})
        self.assertContains(respuesta, 'El precio debe ser un número entero')
        self.assertEqual(len(self.nombres(respuesta)), 4)

    def test_valores_desconocidos_se_ignoran(self):
        respuesta = self.client.get('/menu/', {'genero': '9999', 'plataforma': 'gameboy'})
        self.assertEqual(len(self.nombres(respuesta)), 4)
        self.assertFalse(respuesta.context['filtros']['activos'])

    def test_el_orden_se_combina_con_los_filtros(self):
        respuesta = self.client.get('/menu/', {'plataforma': 'ps5', 'orden': 'precio_asc'})
        self.assertEqual([p.nombre for p in respuesta.context['productos']], ['FIFA PS5', 'Control PS5'])

    def test_quitar_un_filtro_conserva_los_demas(self):
        respuesta = self.client.get('/menu/', {'genero': self.deportes, 'plataforma': 'ps5', 'page': '1'})
        enlaces = {f['texto']: f['url'] for f in respuesta.context['filtros']['aplicados']}
        self.assertEqual(enlaces['Género: Deportes'], 'plataforma=ps5')
        self.assertEqual(respuesta.context['filtros']['url_limpiar'], '')

    def test_el_navbar_solo_usa_categorias_y_plataformas_existentes(self):
        from .constants import MENU_NAVBAR
        from .models import Categoria, Plataforma
        categorias = set(Categoria.objects.values_list('nombre', flat=True))
        plataformas = set(Plataforma.objects.values_list('codigo', flat=True))
        for menu in MENU_NAVBAR:
            for _, entradas in menu['grupos']:
                for categoria, plataforma, _ in entradas:
                    self.assertIn(categoria, categorias)
                    if plataforma:
                        self.assertIn(plataforma, plataformas)


class CarritoEliminarVariosTests(TestCase):  # HU-11: eliminar algunos o todos los productos del carrito
    def setUp(self):
        from .models import Carrito, ItemCarritoProducto
        self.cliente = crear_cliente()
        self.client.force_login(self.cliente)
        carrito = Carrito.objects.create(usuario=self.cliente)
        self.items = [
            ItemCarritoProducto.objects.create(carrito=carrito, producto=crear_producto(f'Juego {i}'), cantidad=i)
            for i in (1, 2, 3)
        ]

    def ids_en_carrito(self):
        from .models import ItemCarritoProducto
        return set(ItemCarritoProducto.objects.filter(carrito__usuario=self.cliente).values_list('producto_id', flat=True))

    def test_elimina_solo_los_seleccionados_y_devuelve_el_resumen(self):
        uno, dos, tres = self.items
        respuesta = self.client.post('/carrito/eliminar-seleccionados/', {'ids': [uno.producto_id, tres.producto_id]}).json()
        self.assertTrue(respuesta['success'])
        self.assertEqual(set(respuesta['eliminados']), {uno.producto_id, tres.producto_id})
        self.assertEqual(respuesta['total_items'], 2)
        self.assertEqual(respuesta['total'], 20000)
        self.assertEqual(self.ids_en_carrito(), {dos.producto_id})

    def test_vaciar_elimina_todo(self):
        respuesta = self.client.post('/carrito/vaciar/').json()
        self.assertTrue(respuesta['success'])
        self.assertEqual(respuesta['total_items'], 0)
        self.assertEqual(respuesta['total'], 0)
        self.assertEqual(self.ids_en_carrito(), set())

    def test_no_se_pueden_borrar_items_de_otro_cliente(self):
        from .models import Carrito, ItemCarritoProducto
        otro = crear_cliente('otro@example.com')
        carrito_ajeno = Carrito.objects.create(usuario=otro)
        ajeno = ItemCarritoProducto.objects.create(carrito=carrito_ajeno, producto=crear_producto('Ajeno'))
        compartido = ItemCarritoProducto.objects.create(carrito=carrito_ajeno, producto=self.items[0].producto)
        respuesta = self.client.post('/carrito/eliminar-seleccionados/', {'ids': [ajeno.producto_id]})
        self.assertEqual(respuesta.status_code, 404)
        self.assertTrue(ItemCarritoProducto.objects.filter(pk=ajeno.pk).exists())
        # mezclado con uno propio: se borra solo el propio, aunque el otro cliente tenga el mismo producto
        respuesta = self.client.post('/carrito/eliminar-seleccionados/',
                                     {'ids': [ajeno.producto_id, self.items[0].producto_id]}).json()
        self.assertEqual(respuesta['eliminados'], [self.items[0].producto_id])
        self.assertTrue(ItemCarritoProducto.objects.filter(pk=ajeno.pk).exists())
        self.assertTrue(ItemCarritoProducto.objects.filter(pk=compartido.pk).exists())
        # y vaciar el carrito propio no toca el ajeno
        self.client.post('/carrito/vaciar/')
        self.assertTrue(ItemCarritoProducto.objects.filter(pk=ajeno.pk).exists())

    def test_seleccion_vacia_o_invalida_se_rechaza(self):
        for datos in [{}, {'ids': ['abc']}, {'ids': [self.items[0].producto_id, 'x']}]:
            respuesta = self.client.post('/carrito/eliminar-seleccionados/', datos)
            self.assertEqual(respuesta.status_code, 400, datos)
        self.assertEqual(len(self.ids_en_carrito()), 3)

    def test_solo_por_post_y_con_sesion(self):
        self.assertEqual(self.client.get('/carrito/vaciar/').status_code, 405)
        self.assertEqual(self.client.get('/carrito/eliminar-seleccionados/').status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.post('/carrito/vaciar/').status_code, 401)
        self.assertEqual(len(self.ids_en_carrito()), 3)

    def test_el_carrito_muestra_la_seleccion_y_los_botones(self):
        respuesta = self.client.get('/ver_carrito/')
        self.assertContains(respuesta, 'class="form-check-input check-carrito check-item"', count=3)
        self.assertContains(respuesta, 'Vaciar carrito')
        self.assertContains(respuesta, 'Eliminar seleccionados')


class DevolucionCorreoTests(TestCase):  # HU-21: se notifica al cliente la resolución de su devolución
    def setUp(self):
        from .models import Devolucion
        self.producto = crear_producto(stock=5)
        self.cliente = crear_cliente()
        venta = crear_venta(self.cliente, self.producto, cantidad=2)
        self.devolucion = Devolucion.objects.create(usuario=self.cliente, venta=venta, producto=self.producto,
                                                    cantidad=1, motivo='Llegó roto')
        self.client.force_login(crear_cliente('jefe@example.com', is_staff=True))
        self.url = f'/admin-panel/devoluciones/responder/{self.devolucion.id}/'

    def responder(self, accion='aceptar', respuesta='Puedes traerlo a la tienda.'):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(self.url, {'accion': accion, 'respuesta': respuesta})

    def test_aprobar_envia_correo_al_cliente_con_la_respuesta(self):
        from django.core import mail
        self.responder()
        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertEqual(correo.to, ['cliente@example.com'])
        self.assertIn(f'Nº {self.devolucion.id} fue aprobada', correo.subject)
        html = correo.alternatives[0][0]
        for texto in [correo.body, html]:
            for dato in ['Puedes traerlo a la tienda.', 'Juego', '$10.000',
                         f'http://localhost:8000/devoluciones/{self.devolucion.id}/detalle/']:
                self.assertIn(dato, texto)

    def test_rechazar_envia_correo_de_rechazo_sin_monto(self):
        from django.core import mail
        self.responder('rechazar', 'El producto tiene daño por mal uso.')
        correo = mail.outbox[0]
        self.assertIn('fue rechazada', correo.subject)
        self.assertIn('SOLICITUD RECHAZADA', correo.body)
        self.assertNotIn('Monto a reembolsar', correo.body)

    def test_respuesta_vacia_o_accion_invalida_no_resuelve_ni_envia(self):
        from django.core import mail
        casos = [('aceptar', '   ', 'Escribe una respuesta'), ('borrar', 'ok', 'Elige si apruebas'),
                 ('aceptar', 'x' * 1001, 'no puede superar')]
        for accion, respuesta, error in casos:
            self.assertContains(self.responder(accion, respuesta), error)
        self.devolucion.refresh_from_db()
        self.assertEqual(self.devolucion.estado, 'Pendiente')
        self.assertEqual(mail.outbox, [])

    def test_el_formulario_conserva_lo_escrito_si_hay_error(self):
        respuesta = self.responder('', 'Texto a medio escribir')
        self.assertContains(respuesta, 'Texto a medio escribir</textarea>')

    def test_una_devolucion_ya_resuelta_no_reenvia_el_correo(self):
        from django.core import mail
        self.responder()
        self.responder('rechazar')
        self.assertEqual(len(mail.outbox), 1)

    def test_si_el_correo_falla_la_resolucion_igual_queda_guardada(self):
        from unittest import mock
        with mock.patch('django.core.mail.EmailMultiAlternatives.send', side_effect=OSError('SMTP caído')):
            respuesta = self.responder()
        self.assertRedirects(respuesta, '/admin-panel/devoluciones/', fetch_redirect_response=False)
        self.devolucion.refresh_from_db()
        self.assertEqual(self.devolucion.estado, 'Aprobada')


class ConfiguracionSitioTests(TestCase):  # HU-09: habilitar o deshabilitar funcionalidades de visualización
    def setUp(self):
        self.ps5 = crear_producto('Juego PS5', stock=2)
        self.otro_ps5 = crear_producto('Otro PS5')
        self.switch = crear_producto('Juego Switch', plataforma='switch')

    def configurar(self, **opciones):
        from .models import ConfiguracionSitio
        configuracion = ConfiguracionSitio.actual()
        for campo, valor in opciones.items():
            setattr(configuracion, campo, valor)
        configuracion.save()

    def ficha(self):
        return self.client.get(f'/producto/{self.ps5.id}/')

    def ocultar(self, *nombres):
        from .models import Categoria
        Categoria.objects.filter(nombre__in=nombres).update(visible_en_menu=False)

    def test_por_defecto_el_navbar_muestra_todas_las_categorias(self):
        from .constants import MENU_NAVBAR
        from .context_processors import url_categoria
        from .models import Categoria
        ids = dict(Categoria.objects.values_list('nombre', 'id'))
        html = self.client.get('/menu/').content.decode()
        for menu in MENU_NAVBAR:
            for _, entradas in menu['grupos']:
                for categoria, plataforma, _ in entradas:
                    self.assertIn(f'href="{url_categoria(ids[categoria], plataforma)}"', html, (categoria, plataforma))
        for menu in ['Videojuegos', 'Consolas', 'Accesorios', 'Figuras']:
            self.assertIn(f'<a href="#">{menu}</a>', html)

    def test_una_categoria_oculta_sale_del_navbar_pero_su_pagina_sigue(self):
        from .models import Categoria
        self.ocultar('Videojuegos')
        url = f'/productos/{Categoria.objects.get(nombre="Videojuegos").id}/ps5/'
        respuesta = self.client.get('/menu/')
        self.assertNotContains(respuesta, f'href="{url}"')
        self.assertNotContains(respuesta, '<a href="#">Videojuegos</a>')
        self.assertContains(self.client.get(url), 'Juego PS5')

    def test_si_se_ocultan_todas_las_de_un_menu_el_menu_desaparece(self):
        self.ocultar('Funko Pop')
        self.assertContains(self.client.get('/menu/'), '<a href="#">Figuras</a>')
        self.ocultar('Amiibo')
        respuesta = self.client.get('/menu/')
        self.assertNotContains(respuesta, '<a href="#">Figuras</a>')
        self.assertContains(respuesta, '<a href="#">Consolas</a>')

    def test_relacionados_de_la_misma_categoria_por_defecto(self):
        relacionados = list(self.ficha().context['productos_relacionados'])
        self.assertEqual(relacionados, [self.otro_ps5])

    def test_relacionados_aleatorios_incluyen_otras_categorias(self):
        self.configurar(productos_relacionados='aleatorios')
        relacionados = set(self.ficha().context['productos_relacionados'])
        self.assertEqual(relacionados, {self.otro_ps5, self.switch})

    def test_relacionados_se_pueden_desactivar(self):
        self.configurar(productos_relacionados='ninguno')
        self.assertNotContains(self.ficha(), 'También te podría interesar')

    def test_ocultar_opiniones_y_stock_en_la_ficha(self):
        self.assertContains(self.ficha(), 'Opiniones del Producto')
        self.assertContains(self.ficha(), '<strong>Stock:</strong>')
        self.configurar(mostrar_opiniones=False, mostrar_stock=False)
        respuesta = self.ficha()
        self.assertNotContains(respuesta, 'Opiniones del Producto')
        self.assertNotContains(respuesta, '<strong>Stock:</strong>')

    def test_ocultar_etiquetas_del_catalogo(self):
        self.assertContains(self.client.get('/menu/'), '¡Últimos!')
        self.configurar(mostrar_etiquetas=False)
        for url in ['/menu/', '/menu/?buscar=Juego', f'/productos/{self.ps5.categoria_id}/ps5/']:
            self.assertNotContains(self.client.get(url), 'badge-overlay', msg_prefix=url)

    def test_hay_un_solo_registro_de_configuracion(self):
        from .models import ConfiguracionSitio
        ConfiguracionSitio.actual()
        ConfiguracionSitio().save()
        self.assertEqual(ConfiguracionSitio.objects.count(), 1)


class ConfiguracionPanelTests(TestCase):  # HU-09: pantalla del panel
    url = '/admin-panel/configuracion/'

    def setUp(self):
        self.client.force_login(crear_cliente('jefe@example.com', is_staff=True))

    def categorias(self):
        from .models import Categoria
        return dict(Categoria.objects.values_list('nombre', 'id'))

    def datos(self, **cambios):
        datos = {'productos_relacionados': 'categoria', 'mostrar_opiniones': 'on', 'mostrar_etiquetas': 'on',
                 'mostrar_stock': 'on', 'categorias_visibles': list(self.categorias().values())}
        datos.update(cambios)
        return {clave: valor for clave, valor in datos.items() if valor is not None}

    def visibles(self):
        from .models import Categoria
        return set(Categoria.objects.filter(visible_en_menu=True).values_list('nombre', flat=True))

    def test_guarda_las_opciones(self):
        from .models import ConfiguracionSitio
        visibles = [id_ for nombre, id_ in self.categorias().items() if nombre != 'Accesorios']
        respuesta = self.client.post(self.url, self.datos(productos_relacionados='ninguno', mostrar_stock=None,
                                                          categorias_visibles=visibles), follow=True)
        self.assertContains(respuesta, 'Configuración guardada')
        configuracion = ConfiguracionSitio.actual()
        self.assertEqual(configuracion.productos_relacionados, 'ninguno')
        self.assertFalse(configuracion.mostrar_stock)
        self.assertTrue(configuracion.mostrar_opiniones)
        self.assertEqual(self.visibles(), {'Videojuegos', 'Consolas', 'Funko Pop', 'Amiibo'})

    def test_el_formulario_muestra_lo_guardado(self):
        from .models import Categoria
        Categoria.objects.filter(nombre='Amiibo').update(visible_en_menu=False)
        ids = self.categorias()
        html = self.client.get(self.url).content.decode()
        self.assertIn(f'value="{ids["Funko Pop"]}"\n                                   data-menu="categorias" checked', html)
        self.assertNotIn(f'value="{ids["Amiibo"]}"\n                                   data-menu="categorias" checked', html)

    def test_valores_invalidos_no_se_guardan(self):
        from .models import ConfiguracionSitio
        for cambio in [{'productos_relacionados': 'todos'}, {'categorias_visibles': ['9999']}]:
            respuesta = self.client.post(self.url, self.datos(**cambio))
            self.assertContains(respuesta, 'No se pudo guardar', msg_prefix=str(cambio))
        configuracion = ConfiguracionSitio.actual()
        self.assertEqual(configuracion.productos_relacionados, 'categoria')
        self.assertEqual(len(self.visibles()), 5)

    def test_solo_el_administrador_puede_entrar(self):
        from .models import ConfiguracionSitio
        self.client.force_login(crear_cliente())
        self.assertNotEqual(self.client.get(self.url).status_code, 200)
        self.client.post(self.url, self.datos(productos_relacionados='ninguno'))
        self.assertEqual(ConfiguracionSitio.actual().productos_relacionados, 'categoria')


GIF_1X1 = (b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,'
           b'\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')


class ModeloDeDatosTests(TestCase):  # restricciones del modelo de datos definitivo (3FN, claves compuestas)
    def setUp(self):
        self.cliente = crear_cliente()
        self.producto = crear_producto('Juego', genero='Acción')

    def test_un_producto_no_se_repite_en_la_misma_venta(self):
        from django.db import IntegrityError, transaction
        from .models import ProductoVenta, Venta
        venta = Venta.objects.create(usuario=self.cliente)
        ProductoVenta.objects.create(venta=venta, producto=self.producto, cantidad=1, precio_unitario=10000)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductoVenta.objects.create(venta=venta, producto=self.producto, cantidad=1, precio_unitario=10000)
        self.assertEqual(venta.producto_venta.get().pk, (venta.id, self.producto.id))

    def test_tablas_de_detalle_con_clave_primaria_compuesta(self):
        from .models import (DetalleCompra, DetallePagoWebpay, Favorito, ItemCarritoProducto, ProductoVenta,
                             SimilitudProducto)
        esperadas = {
            ProductoVenta: ['venta', 'producto'], ItemCarritoProducto: ['carrito', 'producto'],
            DetalleCompra: ['compra', 'producto'], Favorito: ['usuario', 'producto'],
            DetallePagoWebpay: ['pago', 'producto'], SimilitudProducto: ['producto', 'producto_similar'],
        }
        for modelo, campos in esperadas.items():
            self.assertEqual([campo.name for campo in modelo._meta.pk_fields], campos, modelo.__name__)
            self.assertFalse(any(campo.name == 'id' for campo in modelo._meta.fields), modelo.__name__)

    def test_la_categoria_exige_plataforma_y_genero_cuando_corresponde(self):
        from django.core.exceptions import ValidationError
        from .models import Categoria, Producto
        juego = Producto(nombre='Sin datos', categoria=Categoria.objects.get(nombre='Videojuegos'))
        with self.assertRaises(ValidationError) as error:
            juego.clean()
        self.assertEqual(set(error.exception.message_dict), {'plataforma', 'genero'})
        consola = Producto(nombre='Consola', categoria=Categoria.objects.get(nombre='Consolas'))
        with self.assertRaises(ValidationError) as error:
            consola.clean()
        self.assertEqual(set(error.exception.message_dict), {'plataforma'})
        Producto(nombre='Funko', categoria=Categoria.objects.get(nombre='Funko Pop')).clean()

    def test_codigo_de_barra_vacio_queda_nulo_y_es_unico(self):
        from django.db import IntegrityError, transaction
        a = crear_producto('A', codigo_de_barra='')
        b = crear_producto('B', codigo_de_barra='')
        self.assertIsNone(a.codigo_de_barra)
        self.assertIsNone(b.codigo_de_barra)
        with self.assertRaises(IntegrityError), transaction.atomic():
            crear_producto('C', codigo_de_barra=self.producto.codigo_de_barra)

    def test_rut_vacio_queda_nulo(self):
        otro = crear_cliente('otro@example.com', rut='')
        self.assertIsNone(otro.rut)
        crear_cliente('tercero@example.com', rut='')

    def test_la_puntuacion_de_la_opinion_va_de_1_a_5(self):
        from django.db import IntegrityError, transaction
        from .models import Opinion
        for puntuacion in [0, 6]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Opinion.objects.create(usuario=self.cliente, producto=self.producto, comentario='x', puntuacion=puntuacion)
        Opinion.objects.create(usuario=self.cliente, producto=self.producto, comentario='x', puntuacion=5)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Opinion.objects.create(usuario=self.cliente, producto=self.producto, comentario='y', puntuacion=4)

    def test_similitud_entre_0_y_1_y_entre_productos_distintos(self):
        from decimal import Decimal
        from django.db import IntegrityError, transaction
        from django.utils.timezone import now
        from .models import SimilitudProducto
        otro = crear_producto('Otro')
        SimilitudProducto.objects.create(producto=self.producto, producto_similar=otro, puntaje=Decimal('0.8123'),
                                         fecha_calculo=now())
        tercero = crear_producto('Tercero')
        for similar, puntaje in [(tercero, Decimal('1.5')), (self.producto, Decimal('0.5'))]:  # fuera de rango; consigo mismo
            with self.assertRaises(IntegrityError), transaction.atomic():
                SimilitudProducto.objects.create(producto=self.producto, producto_similar=similar, puntaje=puntaje,
                                                 fecha_calculo=now())
        self.assertEqual(self.producto.similitudes.get().producto_similar, otro)

    def test_una_sola_imagen_principal_por_producto(self):
        from django.db import IntegrityError, transaction
        from .models import ImagenProducto
        ImagenProducto.objects.create(producto=self.producto, imagen='productos/b.png', orden=2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ImagenProducto.objects.create(producto=self.producto, imagen='productos/c.png', es_principal=True)
        self.assertEqual(self.producto.imagen_principal.name, 'productos/silent.png')
        self.assertEqual([i.name for i in self.producto.imagenes()], ['productos/silent.png', 'productos/b.png'])

    def test_sin_imagen_principal_marcada_se_usa_la_primera(self):
        from .models import ImagenProducto
        producto = crear_producto('Sin principal', imagen=None)
        self.assertIsNone(producto.imagen_principal)
        ImagenProducto.objects.create(producto=producto, imagen='productos/x.png', orden=1)
        self.assertEqual(producto.imagen_principal.name, 'productos/x.png')

    def test_el_detalle_copia_el_costo_y_la_ganancia_excluye_los_sin_costo(self):  # HU-10
        from .models import ProductoVenta, Venta
        from .reportes import ganancia
        self.producto.costo = 6000
        self.producto.save()
        sin_costo = crear_producto('Sin costo')
        venta = Venta.objects.create(usuario=self.cliente)
        ProductoVenta.objects.create(venta=venta, producto=self.producto, cantidad=2, precio_unitario=10000)
        ProductoVenta.objects.create(venta=venta, producto=sin_costo, cantidad=1, precio_unitario=10000)
        self.assertEqual(venta.producto_venta.get(producto=self.producto).costo_unitario, 6000)
        self.assertIsNone(venta.producto_venta.get(producto=sin_costo).costo_unitario)
        reporte = ganancia(Venta.objects.all())
        self.assertEqual((reporte['ventas'], reporte['costos'], reporte['ganancia']), (20000, 12000, 8000))
        self.assertEqual((reporte['detalles_sin_costo'], reporte['productos_sin_costo']), (1, ['Sin costo']))

    def test_la_compra_suma_stock_solo_al_marcarse_recibida(self):  # HU-10
        from .models import Compra, DetalleCompra, Proveedor
        compra = Compra.objects.create(proveedor=Proveedor.objects.create(nombre='Distribuidora'))
        DetalleCompra.objects.create(compra=compra, producto=self.producto, cantidad=4, costo_unitario=5000)
        self.producto.refresh_from_db()
        self.assertEqual((compra.estado, self.producto.stock), (Compra.PENDIENTE, 5))
        self.assertTrue(compra.marcar_recibida())
        self.assertFalse(compra.marcar_recibida())
        self.producto.refresh_from_db()
        compra.refresh_from_db()
        self.assertEqual((compra.estado, self.producto.stock), (Compra.RECIBIDA, 9))
        self.assertIsNotNone(compra.fecha_recepcion)

    def test_el_comprobante_no_es_tributario(self):
        from .models import Comprobante, Venta
        venta = Venta.objects.create(usuario=self.cliente)
        self.client.force_login(self.cliente)
        respuesta = self.client.get(f'/comprobante/{venta.id}/')
        self.assertContains(respuesta, f'Comprobante de compra Nº {venta.id}')
        self.assertContains(respuesta, 'Documento no tributario')
        self.assertNotContains(respuesta, 'Timbre Electrónico SII')
        self.assertTrue(Comprobante.objects.filter(venta=venta).exists())
        self.assertEqual(venta.comprobante.archivo_pdf.field.upload_to, 'comprobantes/')

    def test_tablas_en_minuscula_sin_prefijo_y_columnas_comentadas(self):
        from django.apps import apps
        for modelo in apps.get_app_config('appPrincipal').get_models():
            self.assertEqual(modelo._meta.db_table, modelo._meta.db_table.lower(), modelo.__name__)
            self.assertFalse(modelo._meta.db_table.startswith('appPrincipal'), modelo.__name__)
            self.assertTrue(modelo._meta.db_table_comment, modelo.__name__)
            for campo in modelo._meta.local_concrete_fields:
                self.assertTrue(campo.db_comment, f'{modelo.__name__}.{campo.name}')


@override_settings(MEDIA_ROOT=__import__('tempfile').mkdtemp())
class ImagenesProductoPanelTests(TestCase):  # HU-09: formulario de producto con hasta 6 imágenes
    def setUp(self):
        from .models import Categoria, Genero, Plataforma
        self.client.force_login(crear_cliente('jefe@example.com', is_staff=True))
        self.base = {
            'codigo_de_barra': '7800001', 'nombre': 'Juego Nuevo', 'precio': '20000', 'stock': '5', 'stock_critico': '2',
            'descripcion': '', 'categoria': Categoria.objects.get(nombre='Videojuegos').id,
            'plataforma': Plataforma.objects.get(codigo='ps5').id, 'genero': Genero.objects.get(nombre='RPG').id,
            'imagenes-TOTAL_FORMS': '6', 'imagenes-INITIAL_FORMS': '0',
        }

    def foto(self, nombre):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile(nombre, GIF_1X1, 'image/gif')

    def test_crea_el_producto_con_sus_imagenes_y_la_principal_elegida(self):
        from .models import Producto
        datos = {**self.base, 'imagenes-0-imagen': self.foto('a.gif'), 'imagenes-2-imagen': self.foto('b.gif'),
                 'principal': '2'}
        respuesta = self.client.post('/admin-panel/productos/agregar/', datos, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertTrue(respuesta.json()['success'], respuesta.content)
        producto = Producto.objects.get(nombre='Juego Nuevo')
        imagenes = list(producto.imagenes_producto.order_by('orden'))
        self.assertEqual([(i.orden, i.es_principal) for i in imagenes], [(1, None), (2, True)])
        self.assertTrue(producto.imagen_principal.name.endswith('b.gif'))

    def test_exige_al_menos_una_imagen_y_plataforma_en_videojuegos(self):
        from .models import Producto
        respuesta = self.client.post('/admin-panel/productos/agregar/', {**self.base, 'plataforma': ''},
                                     HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        errores = respuesta.json()['errors']
        self.assertIn('plataforma', errores)
        respuesta = self.client.post('/admin-panel/productos/agregar/', self.base, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertIn('imagenes-TOTAL_FORMS', respuesta.json()['errors'])
        self.assertFalse(Producto.objects.filter(nombre='Juego Nuevo').exists())

    def test_editar_cambia_la_principal_y_quita_imagenes(self):
        from .models import ImagenProducto
        producto = crear_producto('Editable', genero='RPG')
        segunda = ImagenProducto.objects.create(producto=producto, imagen='productos/otra.png', orden=2)
        primera = producto.imagenes_producto.get(es_principal=True)
        datos = {**self.base, 'codigo_de_barra': producto.codigo_de_barra, 'imagenes-TOTAL_FORMS': '6',
                 'imagenes-INITIAL_FORMS': '2', 'imagenes-0-id': primera.id, 'imagenes-0-producto': producto.id,
                 'imagenes-1-id': segunda.id, 'imagenes-1-producto': producto.id, 'principal': '1'}
        respuesta = self.client.post(f'/admin-panel/productos/editar/{producto.id}/', datos,
                                     HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertTrue(respuesta.json()['success'], respuesta.content)
        self.assertEqual(producto.imagen_principal.name, 'productos/otra.png')
        datos.update({'imagenes-1-DELETE': 'on', 'principal': '0'})
        self.client.post(f'/admin-panel/productos/editar/{producto.id}/', datos, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual([(i.imagen.name, i.es_principal) for i in producto.imagenes_producto.all()],
                         [('productos/silent.png', True)])

    def test_no_admite_mas_de_6_imagenes(self):
        datos = {**self.base, 'imagenes-TOTAL_FORMS': '7'}
        datos.update({f'imagenes-{i}-imagen': self.foto(f'{i}.gif') for i in range(7)})
        respuesta = self.client.post('/admin-panel/productos/agregar/', datos, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertFalse(respuesta.json()['success'])


class LoginGoogleTests(TestCase):  # HU-02: django-allauth
    def test_el_boton_de_google_solo_aparece_con_credenciales(self):
        # sin credenciales a propósito: el .env de cada computador puede tenerlas configuradas
        with self.settings(GOOGLE_CLIENT_ID='', GOOGLE_CLIENT_SECRET=''):
            self.assertNotContains(self.client.get('/login/'), 'Continuar con Google')
        with self.settings(GOOGLE_CLIENT_ID='id-de-prueba', GOOGLE_CLIENT_SECRET='secreto-de-prueba'):
            respuesta = self.client.get('/login/')
        self.assertContains(respuesta, 'Continuar con Google')
        self.assertContains(respuesta, 'action="/accounts/google/login/')

    def test_el_registro_de_allauth_esta_cerrado(self):
        self.client.post('/accounts/signup/', {'email': 'x@example.com', 'password1': 'Akaispace-2026!',
                                               'password2': 'Akaispace-2026!'})
        self.assertFalse(Usuario.objects.exists())

    def test_la_cuenta_de_google_toma_el_nombre_del_perfil(self):
        from unittest import mock
        from .cuentas_google import AdaptadorCuentaGoogle
        sociallogin = mock.Mock()
        sociallogin.account.extra_data = {'name': 'Ana Pérez'}
        sociallogin.user = Usuario(email='ana@gmail.com')
        with mock.patch('allauth.socialaccount.adapter.DefaultSocialAccountAdapter.populate_user',
                        return_value=sociallogin.user):
            usuario = AdaptadorCuentaGoogle().populate_user(None, sociallogin, {'email': 'ana@gmail.com'})
        self.assertEqual(usuario.nombre, 'Ana Pérez')

    def test_el_boton_de_google_tambien_aparece_en_el_registro(self):
        with self.settings(GOOGLE_CLIENT_ID='', GOOGLE_CLIENT_SECRET=''):
            self.assertNotContains(self.client.get('/register/'), 'Registrarse con Google')
        with self.settings(GOOGLE_CLIENT_ID='id-de-prueba', GOOGLE_CLIENT_SECRET='secreto-de-prueba'):
            respuesta = self.client.get('/register/')
        self.assertContains(respuesta, 'Registrarse con Google')
        self.assertContains(respuesta, 'action="/accounts/google/login/')

    def _registro_google(self, datos):
        from allauth.account.models import EmailAddress
        from allauth.socialaccount.models import SocialAccount, SocialLogin
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.test import RequestFactory
        from .cuentas_google import RegistroGoogleForm
        sociallogin = SocialLogin(
            user=Usuario(email='ana@gmail.com', nombre='Ana Pérez'),
            account=SocialAccount(provider='google', uid='123'),
            email_addresses=[EmailAddress(email='ana@gmail.com', verified=True, primary=True)],
        )
        form = RegistroGoogleForm(data=datos, sociallogin=sociallogin)
        if not form.is_valid():
            return form, None
        request = RequestFactory().post('/accounts/3rdparty/signup/')
        SessionMiddleware(lambda r: None).process_request(request)
        return form, form.save(request)

    def test_la_cuenta_nueva_de_google_guarda_los_consentimientos(self):
        form, usuario = self._registro_google({'declaracion_edad': Usuario.MAYOR_18, 'acepta_privacidad': 'on',
                                               'email': 'otro@example.com'})
        usuario.refresh_from_db()
        self.assertEqual(usuario.email, 'ana@gmail.com')  # el correo verificado por Google no se cambia
        self.assertEqual(usuario.nombre, 'Ana Pérez')
        self.assertEqual(usuario.declaracion_edad, Usuario.MAYOR_18)
        self.assertIsNotNone(usuario.privacidad_aceptada_en)
        self.assertIsNone(usuario.datos_navegacion_autorizados_en)
        self.assertFalse(usuario.has_usable_password())

    def test_la_cuenta_de_google_exige_aceptar_la_politica(self):
        form, usuario = self._registro_google({'declaracion_edad': Usuario.MAYOR_18})
        self.assertIsNone(usuario)
        self.assertIn('acepta_privacidad', form.errors)
        self.assertFalse(Usuario.objects.exists())


class VentaPresencialTests(TestCase):  # HU-12: ventas de la tienda física y WhatsApp registradas en el panel
    def setUp(self):
        self.juego = crear_producto('Juego', stock=5, codigo_de_barra='7801234567890', precio=20000, costo=12000)
        self.control = crear_producto('Control', stock=2, categoria='Accesorios', plataforma=None,
                                      codigo_de_barra='7809999999999', precio=5000)
        self.client.force_login(crear_cliente('jefe@example.com', is_staff=True))

    def registrar(self, filas, canal='tienda', metodo_pago='efectivo'):
        return self.client.post('/admin-panel/ventas/registrar/', {
            'producto': [producto.id for producto, _ in filas],
            'cantidad': [cantidad for _, cantidad in filas],
            'canal': canal, 'metodo_pago': metodo_pago,
        })

    def test_registrar_descuenta_stock_y_queda_como_venta_presencial(self):
        from .models import Comprobante, Envio, Venta
        respuesta = self.registrar([(self.juego, 2), (self.control, 1)], canal='whatsapp', metodo_pago='transferencia')

        venta = Venta.objects.get()
        self.assertRedirects(respuesta, f'/admin-panel/ventas/detalle/{venta.id}/?msg=registrada',
                             fetch_redirect_response=False)
        self.assertEqual((venta.canal, venta.metodo_pago, venta.usuario), ('whatsapp', 'transferencia', None))
        self.assertEqual((venta.subtotal, venta.envio, venta.total), (45000, 0, 45000))
        self.assertEqual(venta.producto_venta.get(producto=self.juego).costo_unitario, 12000)
        self.juego.refresh_from_db()
        self.control.refresh_from_db()
        self.assertEqual((self.juego.stock, self.control.stock), (3, 1))
        self.assertFalse(Envio.objects.exists())
        self.assertTrue(Comprobante.objects.filter(venta=venta).exists())

    def test_sin_stock_suficiente_no_se_registra_nada(self):
        from .models import Venta
        respuesta = self.registrar([(self.juego, 1), (self.control, 3)])

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('Stock insuficiente para el producto Control (disponible: 2)', respuesta.context['error'])
        self.assertFalse(Venta.objects.exists())
        self.juego.refresh_from_db()
        self.assertEqual(self.juego.stock, 5)
        # los productos agregados se vuelven a mostrar para corregir la cantidad
        self.assertEqual([(fila['id'], fila['cantidad']) for fila in respuesta.context['items_ingresados']],
                         [(self.juego.id, '1'), (self.control.id, '3')])

    def test_el_mismo_producto_en_dos_filas_se_suma(self):
        from .models import Venta
        self.registrar([(self.juego, 2), (self.juego, 1)], metodo_pago='tarjeta')
        detalle = Venta.objects.get().producto_venta.get()
        self.assertEqual(detalle.cantidad, 3)
        self.juego.refresh_from_db()
        self.assertEqual(self.juego.stock, 2)

    def test_datos_invalidos_se_rechazan(self):
        from .models import Venta
        casos = [
            ([(self.juego, 1)], 'tienda', 'webpay'),  # Webpay es solo de la tienda en línea
            ([(self.juego, 1)], 'tienda', ''),
            ([(self.juego, 1)], 'web', 'efectivo'),
            ([(self.juego, 0)], 'tienda', 'efectivo'),
            ([(self.juego, 'dos')], 'tienda', 'efectivo'),
            ([], 'tienda', 'efectivo'),
        ]
        for filas, canal, metodo_pago in casos:
            respuesta = self.registrar(filas, canal, metodo_pago)
            self.assertEqual(respuesta.status_code, 200, (filas, canal, metodo_pago))
            self.assertTrue(respuesta.context['error'])
        self.assertFalse(Venta.objects.exists())

    def test_producto_eliminado_no_se_puede_vender(self):
        from .models import Venta
        self.juego.delete()
        respuesta = self.registrar([(self.juego, 1)])
        self.assertIn('ya no está disponible', respuesta.context['error'])
        self.assertFalse(Venta.objects.exists())

    def test_buscar_por_codigo_de_barras_exacto_o_por_nombre(self):
        exacto = self.client.get('/admin-panel/ventas/buscar-productos/', {'q': '7801234567890'}).json()
        self.assertEqual([p['id'] for p in exacto['productos']], [self.juego.id])
        self.assertEqual(exacto['productos'][0]['stock'], 5)

        por_nombre = self.client.get('/admin-panel/ventas/buscar-productos/', {'q': 'contr'}).json()
        self.assertEqual([p['nombre'] for p in por_nombre['productos']], ['Control'])

        por_parte_del_codigo = self.client.get('/admin-panel/ventas/buscar-productos/', {'q': '780'}).json()
        self.assertEqual(len(por_parte_del_codigo['productos']), 2)

        self.juego.delete()
        eliminado = self.client.get('/admin-panel/ventas/buscar-productos/', {'q': '7801234567890'}).json()
        self.assertEqual(eliminado['productos'], [])

    def test_un_cliente_no_puede_registrar_ni_buscar(self):
        from .models import Venta
        self.client.force_login(crear_cliente())
        self.assertRedirects(self.registrar([(self.juego, 1)]), '/', fetch_redirect_response=False)
        self.assertRedirects(self.client.get('/admin-panel/ventas/buscar-productos/', {'q': 'Juego'}), '/',
                             fetch_redirect_response=False)
        self.assertFalse(Venta.objects.exists())

    def test_formulario_listado_detalle_y_comprobante(self):
        from .models import Venta
        self.assertEqual(self.client.get('/admin-panel/ventas/registrar/').status_code, 200)
        self.registrar([(self.juego, 1)])
        venta = Venta.objects.get()

        listado = self.client.get('/admin-panel/ventas/', {'canal': 'tienda'})
        self.assertEqual(list(listado.context['ventas']), [venta])
        self.assertEqual(list(self.client.get('/admin-panel/ventas/', {'canal': 'web'}).context['ventas']), [])

        detalle = self.client.get(f'/admin-panel/ventas/detalle/{venta.id}/')
        self.assertContains(detalle, 'Tienda física')
        self.assertContains(detalle, 'Efectivo')
        self.assertNotContains(detalle, f'/admin-panel/ventas/modificar/{venta.id}/')
        self.assertContains(self.client.get(f'/comprobante/{venta.id}/'), 'Tienda física')
        # no tiene envío que modificar
        self.assertRedirects(self.client.get(f'/admin-panel/ventas/modificar/{venta.id}/'),
                             f'/admin-panel/ventas/detalle/{venta.id}/', fetch_redirect_response=False)

    def test_anular_repone_el_stock_una_vez_y_sale_del_grafico(self):
        from django.utils import timezone
        from .models import Envio, Venta
        from .views.panel.dashboard import ventas_por_mes
        self.registrar([(self.juego, 2)])
        venta = Venta.objects.get()
        self.assertEqual(sum(ventas_por_mes(timezone.localdate().year)), 40000)

        self.client.post(f'/ventas/anular/{venta.id}/')
        self.client.post(f'/ventas/anular/{venta.id}/')

        venta.refresh_from_db()
        self.juego.refresh_from_db()
        self.assertTrue(venta.anulada)
        self.assertEqual(self.juego.stock, 5)
        self.assertFalse(Envio.objects.exists())
        self.assertEqual(sum(ventas_por_mes(timezone.localdate().year)), 0)
        self.assertContains(self.client.get(f'/admin-panel/ventas/detalle/{venta.id}/'), 'Venta Anulada')


class RecomendacionesTests(TestCase):  # HU-07: similitud TF-IDF + coseno y arranque en frío
    def setUp(self):
        self.elden = crear_producto('Elden Ring', genero='RPG')
        self.demons = crear_producto("Demon's Souls", genero='RPG')
        self.bloodborne = crear_producto('Bloodborne', plataforma='ps4', genero='RPG')
        self.pokemon = crear_producto('Pokémon Escarlata', plataforma='switch', genero='RPG')
        self.gow = crear_producto('God of War', genero='Acción')
        self.consola = crear_producto('Consola PS5', categoria='Consolas')
        self.funko = crear_producto('Funko Kratos', categoria='Funko Pop', plataforma=None)

    def similares(self, producto):
        from .models import SimilitudProducto
        return list(SimilitudProducto.objects.filter(producto=producto).order_by('-puntaje', 'producto_similar_id')
                    .values_list('producto_similar__nombre', 'puntaje'))

    def autorizar(self, cliente):
        from django.utils import timezone
        cliente.datos_navegacion_autorizados_en = timezone.now()
        cliente.save()
        return cliente

    def interaccion(self, cliente, producto, tipo='vista'):
        from .models import InteraccionProducto
        InteraccionProducto.objects.create(usuario=cliente, producto=producto, tipo=tipo)

    def test_documento_de_etiquetas(self):
        from .recomendaciones import documento
        self.assertEqual(documento(self.elden), 'cat_videojuegos plat_ps5 fam_playstation gen_rpg')
        self.assertEqual(documento(self.consola), 'cat_consolas plat_ps5 fam_playstation')
        self.assertEqual(documento(self.funko), 'cat_funko_pop')

    def test_calcula_similares_con_la_familia_de_plataforma(self):
        from .recomendaciones import calcular_similitudes
        calcular_similitudes()
        similares = self.similares(self.elden)
        self.assertEqual(similares[0][0], "Demon's Souls")
        self.assertEqual(similares[0][1], 1)
        # el RPG de PS4 (misma familia) queda antes que el de Switch
        nombres = [nombre for nombre, _ in similares]
        self.assertLess(nombres.index('Bloodborne'), nombres.index('Pokémon Escarlata'))
        # sin etiquetas en común (puntaje 0) no se guarda, ni el producto consigo mismo
        self.assertNotIn('Funko Kratos', nombres)
        self.assertNotIn('Elden Ring', nombres)
        self.assertTrue(all(0 < puntaje <= 1 for _, puntaje in similares))

    def test_recalcular_reemplaza_y_excluye_eliminados(self):
        from .models import SimilitudProducto
        from .recomendaciones import calcular_similitudes
        calcular_similitudes()
        self.demons.delete()
        calcular_similitudes()
        self.assertNotIn("Demon's Souls", [nombre for nombre, _ in self.similares(self.elden)])
        self.assertFalse(SimilitudProducto.objects.filter(producto=self.demons).exists())

    def test_guarda_como_maximo_10_similares(self):
        from .recomendaciones import TOP_SIMILARES, calcular_similitudes
        for numero in range(12):
            crear_producto(f'RPG {numero}', genero='RPG')
        calcular_similitudes()
        self.assertEqual(len(self.similares(self.elden)), TOP_SIMILARES)

    def test_desempata_por_unidades_vendidas_y_luego_id(self):
        from .recomendaciones import calcular_similitudes
        juegos = [crear_producto(f'RPG {numero}', genero='RPG') for numero in range(10)]
        crear_venta(crear_cliente(), juegos[-1], cantidad=3)
        calcular_similitudes()
        nombres = [nombre for nombre, _ in self.similares(self.elden)]
        # 11 empatados con 1.0 para 10 puestos: entra el más vendido y queda fuera el de id más alto
        self.assertIn('RPG 9', nombres)
        self.assertNotIn('RPG 8', nombres)

    def test_anonimo_en_la_ficha_ve_similares_con_stock(self):
        from django.contrib.auth.models import AnonymousUser
        from .recomendaciones import SIMILARES, calcular_similitudes, recomendar
        self.demons.stock = 0
        self.demons.save()
        calcular_similitudes()
        recomendaciones = recomendar(AnonymousUser(), self.elden)
        self.assertEqual(recomendaciones.tipo, SIMILARES)
        self.assertEqual(recomendaciones.productos[0], self.bloodborne)
        self.assertNotIn(self.demons, recomendaciones.productos)
        self.assertNotIn(self.elden, recomendaciones.productos)

    def test_anonimo_en_la_portada_ve_los_mas_vendidos(self):
        from django.contrib.auth.models import AnonymousUser
        from .recomendaciones import MAS_VENDIDOS, recomendar
        cliente = crear_cliente()
        crear_venta(cliente, self.funko, cantidad=5)
        crear_venta(cliente, self.consola, cantidad=2)
        recomendaciones = recomendar(AnonymousUser())
        self.assertEqual(recomendaciones.tipo, MAS_VENDIDOS)
        self.assertEqual(recomendaciones.productos[:2], [self.funko, self.consola])

    def test_las_ventas_anuladas_no_cuentan_como_vendidas(self):
        from django.utils import timezone
        from .recomendaciones import unidades_vendidas
        venta = crear_venta(crear_cliente(), self.funko, cantidad=5)
        venta.anulada_en = timezone.now()
        venta.save()
        self.assertNotIn(self.funko.id, unidades_vendidas())

    def test_cliente_que_autorizo_recibe_personalizadas_sin_lo_comprado_ni_el_carrito(self):
        from .models import Carrito, ItemCarritoProducto
        from .recomendaciones import PERSONALIZADAS, recomendar
        otro_switch = crear_producto('Xenoblade', plataforma='switch', genero='RPG')
        cliente = self.autorizar(crear_cliente())
        self.interaccion(cliente, self.pokemon)
        self.interaccion(cliente, otro_switch, 'carrito')
        crear_venta(cliente, self.pokemon)
        carrito = Carrito.objects.create(usuario=cliente)
        ItemCarritoProducto.objects.create(carrito=carrito, producto=otro_switch)
        recomendaciones = recomendar(cliente)
        self.assertEqual(recomendaciones.tipo, PERSONALIZADAS)
        self.assertNotIn(self.pokemon, recomendaciones.productos)
        self.assertNotIn(otro_switch, recomendaciones.productos)
        # sin más juegos de Switch, lo más cercano a un RPG de Switch son los otros RPG
        self.assertIn(recomendaciones.productos[0], [self.elden, self.demons, self.bloodborne])

    def test_sin_consentimiento_no_se_usa_su_historial(self):
        from .recomendaciones import SIMILARES, calcular_similitudes, recomendar
        cliente = crear_cliente()
        self.interaccion(cliente, self.funko)
        calcular_similitudes()
        recomendaciones = recomendar(cliente, self.elden)
        self.assertEqual(recomendaciones.tipo, SIMILARES)

    def test_autorizo_pero_sin_historial_usa_el_arranque_en_frio(self):
        from .recomendaciones import MAS_VENDIDOS, SIMILARES, calcular_similitudes, recomendar
        cliente = self.autorizar(crear_cliente())
        calcular_similitudes()
        self.assertEqual(recomendar(cliente, self.elden).tipo, SIMILARES)
        self.assertEqual(recomendar(cliente).tipo, MAS_VENDIDOS)
