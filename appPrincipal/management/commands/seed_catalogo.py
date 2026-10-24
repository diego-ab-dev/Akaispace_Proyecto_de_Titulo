"""Carga el catálogo de prueba desde fixtures/catalogo.csv (HU-07: catálogo con atributos completos, KPI-10).

- Cada fila se identifica por su código de barras: si el producto no existe se crea, y si existe se actualizan
  sus atributos (nombre, descripción, categoría, plataforma y género). El precio, el costo y el stock de un
  producto que ya existe no se tocan, para no deshacer ventas ni cambios hechos desde el panel.
- Un producto que el administrador eliminó (borrado lógico) sigue eliminado.
- Los productos sin imágenes reciben la imagen genérica de su categoría (fixtures/catalogo_media).
- Si una fila tiene un error, no se carga nada.
"""
import csv
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from appPrincipal.models import Categoria, Genero, ImagenProducto, Plataforma, Producto

FIXTURES_DIR = Path(__file__).resolve().parents[2] / 'fixtures'
COLUMNAS = ['codigo_de_barra', 'nombre', 'categoria', 'plataforma', 'genero', 'precio', 'costo', 'stock',
            'stock_critico', 'descripcion']
ATRIBUTOS_CATALOGO = ['nombre', 'descripcion', 'categoria', 'plataforma', 'genero']


def imagen_generica(categoria):
    """Ruta dentro de media/ de la imagen genérica de la categoría, copiándola si aún no está."""
    nombre = f"productos/generico_{slugify(categoria.nombre).replace('-', '_')}.png"
    if not default_storage.exists(nombre):
        origen = FIXTURES_DIR / 'catalogo_media' / nombre
        if not origen.exists():
            return None
        with origen.open('rb') as archivo:
            default_storage.save(nombre, File(archivo))
    return nombre


class Command(BaseCommand):
    help = 'Carga o actualiza el catálogo de prueba desde un CSV (por defecto appPrincipal/fixtures/catalogo.csv).'

    def add_arguments(self, parser):
        parser.add_argument('--archivo', default=str(FIXTURES_DIR / 'catalogo.csv'),
                            help='CSV con las columnas: ' + ', '.join(COLUMNAS))

    def handle(self, *args, **options):
        filas = self._leer(Path(options['archivo']))
        categorias = {c.nombre: c for c in Categoria.objects.all()}
        plataformas = {p.codigo: p for p in Plataforma.objects.all()}
        generos = {g.nombre: g for g in Genero.objects.all()}

        creados = actualizados = sin_cambios = 0
        errores = []
        with transaction.atomic():
            for numero, fila in filas:
                try:
                    datos = self._datos(fila, categorias, plataformas, generos)
                    producto = Producto.todos.filter(codigo_de_barra=datos['codigo_de_barra']).first()
                    if producto is None:
                        producto = Producto(**datos)
                        producto.full_clean()
                        producto.save()
                        creados += 1
                    else:
                        cambios = [campo for campo in ATRIBUTOS_CATALOGO
                                   if getattr(producto, campo) != datos[campo]]
                        for campo in cambios:
                            setattr(producto, campo, datos[campo])
                        if cambios:
                            producto.full_clean()
                            producto.save(update_fields=cambios)
                            actualizados += 1
                        else:
                            sin_cambios += 1
                except (KeyError, ValueError) as error:
                    errores.append(f"Fila {numero}: {error}")
                    continue
                except ValidationError as error:
                    detalle = '; '.join(m for mensajes in error.message_dict.values() for m in mensajes)
                    errores.append(f"Fila {numero} ({fila.get('nombre')}): {detalle}")
                    continue
                if not producto.imagenes_producto.exists():
                    imagen = imagen_generica(producto.categoria)
                    if imagen:
                        ImagenProducto.objects.create(producto=producto, imagen=imagen, es_principal=True)
            if errores:
                transaction.set_rollback(True)

        if errores:
            raise CommandError('No se cargó el catálogo:\n' + '\n'.join(errores))
        if options['verbosity'] > 0:
            self.stdout.write(self.style.SUCCESS(
                f'Catálogo listo: {creados} creados, {actualizados} actualizados, {sin_cambios} sin cambios.'
            ))

    def _leer(self, ruta):
        if not ruta.exists():
            raise CommandError(f'No existe el archivo {ruta}.')
        # utf-8-sig: acepta también el CSV guardado desde Excel, que agrega un BOM al inicio
        with ruta.open(encoding='utf-8-sig', newline='') as archivo:
            lector = csv.DictReader(archivo)
            faltantes = [columna for columna in COLUMNAS if columna not in (lector.fieldnames or [])]
            if faltantes:
                raise CommandError(f'Al CSV le faltan las columnas: {", ".join(faltantes)}.')
            # la fila 1 es el encabezado
            return [(numero, fila) for numero, fila in enumerate(lector, start=2)]

    def _datos(self, fila, categorias, plataformas, generos):
        fila = {columna: (fila.get(columna) or '').strip() for columna in COLUMNAS}
        if not fila['codigo_de_barra'] or not fila['nombre']:
            raise ValueError('el código de barras y el nombre son obligatorios.')
        if fila['categoria'] not in categorias:
            raise ValueError(f"la categoría '{fila['categoria']}' no existe.")
        if fila['plataforma'] and fila['plataforma'] not in plataformas:
            raise ValueError(f"la plataforma '{fila['plataforma']}' no existe (usa su código, ej. ps5).")
        if fila['genero'] and fila['genero'] not in generos:
            raise ValueError(f"el género '{fila['genero']}' no existe.")
        try:
            numeros = {campo: int(fila[campo]) if fila[campo] else None
                       for campo in ['precio', 'costo', 'stock', 'stock_critico']}
        except ValueError:
            raise ValueError('precio, costo, stock y stock crítico deben ser números enteros.')
        return {
            'codigo_de_barra': fila['codigo_de_barra'],
            'nombre': fila['nombre'],
            'descripcion': fila['descripcion'],
            'categoria': categorias[fila['categoria']],
            'plataforma': plataformas.get(fila['plataforma']),
            'genero': generos.get(fila['genero']),
            'precio': numeros['precio'] or 0,
            'costo': numeros['costo'],
            'stock': numeros['stock'] or 0,
            'stock_critico': numeros['stock_critico'] if numeros['stock_critico'] is not None else 5,
        }
