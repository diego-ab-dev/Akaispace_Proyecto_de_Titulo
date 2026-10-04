import shutil
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from appPrincipal import portada_inicial
from appPrincipal.models import Destacado, Producto, Usuario

FIXTURES_DIR = Path(__file__).resolve().parents[2] / 'fixtures'

# Cuentas de prueba para desarrollo. Nunca usar en producción.
USUARIOS_DEMO = [
    {
        'email': 'admin@gmail.com',
        'password': 'Akaispace-Admin-2026',
        'nombre': 'Admin',
        'rut': '12.343.455-2',
        'telefono': '+56 9 45533453',
        'direccion': 'Picarte 233',
        'region': 'LOS RIOS',
        'ciudad': 'Valdivia',
        'is_staff': True,
        'is_superuser': True,
    },
    {
        'email': 'user@gmail.com',
        'password': 'Akaispace-Cliente-2026',
        'nombre': 'Usuario',
        'rut': '75.292.177-6',
        'telefono': '+56 9 45645354',
        'direccion': 'Gabriela Mistral 345',
        'region': 'VALPARAISO',
        'ciudad': 'Viña del Mar',
    },
]


class Command(BaseCommand):
    help = 'Carga productos de ejemplo (con sus imágenes) y usuarios de prueba. Solo para desarrollo (DEBUG=True).'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('seed_demo solo se puede ejecutar con DEBUG=True.')
        verbose = options['verbosity'] > 0

        # productos de ejemplo
        call_command('loaddata', 'productos_demo', verbosity=0)
        origen = FIXTURES_DIR / 'demo_media'
        destino = Path(settings.MEDIA_ROOT)
        for archivo in origen.rglob('*'):
            if archivo.is_file():
                ruta_destino = destino / archivo.relative_to(origen)
                ruta_destino.parent.mkdir(parents=True, exist_ok=True)
                if not ruta_destino.exists():
                    shutil.copy2(archivo, ruta_destino)
        if verbose:
            self.stdout.write('Productos de ejemplo cargados.')

        # carrusel, lanzamientos y promos del navbar enlazados a los productos de ejemplo
        portada_inicial.cargar(Destacado, Producto)
        if verbose:
            self.stdout.write('Portada de ejemplo lista.')

        # usuarios de prueba
        for datos in USUARIOS_DEMO:
            datos = dict(datos)
            email = datos.pop('email')
            password = datos.pop('password')
            usuario = Usuario.objects.filter(email=email).first()
            if usuario is None:
                Usuario.objects.create_user(email=email, password=password, **datos)
                estado = 'creado'
            else:
                # restablece la contraseña de prueba por si cambió
                usuario.set_password(password)
                usuario.save()
                estado = 'ya existía, contraseña restablecida'
            if verbose:
                self.stdout.write(f'Usuario {email}: {estado}.')

        if verbose:
            self.stdout.write(self.style.SUCCESS('Datos de prueba listos.'))
