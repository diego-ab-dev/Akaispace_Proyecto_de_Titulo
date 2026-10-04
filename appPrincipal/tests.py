from django.contrib.auth.hashers import check_password
from django.core.management import call_command
from django.test import TestCase, override_settings

from .models import Producto, Usuario


@override_settings(DEBUG=True)
class SeedDemoTests(TestCase):
    def test_carga_productos_y_usuarios(self):
        call_command('seed_demo', verbosity=0)
        self.assertEqual(Producto.objects.count(), 6)
        admin = Usuario.objects.get(email='admin@gmail.com')
        self.assertTrue(admin.es_administrador)
        self.assertTrue(check_password('12345', admin.contraseña))
        self.assertFalse(Usuario.objects.get(email='user@gmail.com').es_administrador)

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
        'email': 'juan@example.com', 'contraseña': 'clave-segura-123', 'direccion': 'Calle 123',
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
