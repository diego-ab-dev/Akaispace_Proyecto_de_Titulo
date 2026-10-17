"""Catálogo normalizado: categoría, plataforma y género pasan a ser tablas propias.

Antes, Producto.categoria era un texto que mezclaba categoría y plataforma ("Videojuegos PS5",
"Ps5 Consolas") y Producto.genero incluía valores que no son géneros (CONSOLAS, FIGURAS,
ACCESORIOS, OTRO). Los datos fijos de abajo son copia de Producto.CATEGORIAS, GENEROS y
PLATAFORMAS tal como estaban en models.py antes de este cambio.
"""
import django.db.models.deletion
from django.db import migrations, models

# (nombre, requiere_plataforma, requiere_genero)
CATEGORIAS = [
    ('Videojuegos', True, True),
    ('Consolas', True, False),
    ('Accesorios', True, False),
    ('Funko Pop', False, False),
    ('Amiibo', False, False),
]

# (código, nombre, familia, categorías antiguas que la componían)
PLATAFORMAS = [
    ('ps5', 'PlayStation 5', 'playstation', ['Videojuegos PS5', 'Ps5 Consolas', 'Accesorios PS5']),
    ('ps4', 'PlayStation 4', 'playstation', ['Videojuegos PS4', 'Ps4 Consolas', 'Accesorios PS4']),
    ('ps3', 'PlayStation 3', 'playstation', ['Videojuegos PS3', 'Accesorios PS3']),
    ('ps2', 'PlayStation 2', 'playstation', ['Accesorios PS2']),
    ('ps1', 'PlayStation 1', 'playstation', ['Accesorios PS1']),
    ('psvita', 'PlayStation Vita', 'playstation', ['Accesorios Ps Vita']),
    ('psp', 'PSP', 'playstation', ['Accesorios Psp']),
    ('xboxseries', 'Xbox Series', 'xbox', ['Videojuegos XBOX SERIES', 'Xbox Series Consolas', 'Accesorios XBOX SERIES']),
    ('xboxone', 'Xbox One', 'xbox', ['Videojuegos XBOX ONE', 'Xbox One Consolas', 'Accesorios XBOX ONE']),
    ('xbox360', 'Xbox 360', 'xbox', ['Videojuegos XBOX 360', 'Accesorios XBOX 360']),
    ('switch', 'Nintendo Switch', 'nintendo', ['Videojuegos Nintendo SWITCH', 'Switch Consolas', 'Accesorios Nintendo SWITCH']),
    ('wiiu', 'Nintendo Wii U', 'nintendo', ['Videojuegos WII U', 'Wii U Consolas', 'Accesorios WII U']),
    ('wii', 'Nintendo Wii', 'nintendo', ['Videojuegos WII']),
    ('3ds', 'Nintendo 3DS', 'nintendo', ['Videojuegos Nintendo 3DS', 'Accesorios Nintendo 3DS']),
    ('pc', 'PC', 'pc', ['Videojuegos para PC']),
]

# código antiguo -> nombre del género. CONSOLAS, FIGURAS, ACCESORIOS y OTRO no son géneros: quedan en NULL.
GENEROS = [
    ('ACCION', 'Acción'),
    ('AVENTURA', 'Aventura'),
    ('RPG', 'RPG'),
    ('DEPORTES', 'Deportes'),
    ('CARRERAS', 'Carreras'),
    ('ESTRATEGIA', 'Estrategia'),
    ('SIMULACION', 'Simulación'),
    ('PUZZLE', 'Puzzle'),
    ('TERROR', 'Terror'),
]

FIGURAS = {'Figuras Funko': 'Funko Pop', 'Figuras Amiibo': 'Amiibo'}


def categoria_antigua(texto):
    """'Videojuegos PS5' -> ('Videojuegos', 'ps5'); 'Figuras Funko' -> ('Funko Pop', None)."""
    if texto in FIGURAS:
        return FIGURAS[texto], None
    for codigo, _, _, antiguas in PLATAFORMAS:
        if texto in antiguas:
            if texto.startswith('Videojuegos'):
                return 'Videojuegos', codigo
            if texto.startswith('Accesorios'):
                return 'Accesorios', codigo
            return 'Consolas', codigo
    raise ValueError(f"Categoría desconocida: {texto!r}")


def cargar_catalogo(apps, schema_editor):
    Categoria = apps.get_model('appPrincipal', 'Categoria')
    Plataforma = apps.get_model('appPrincipal', 'Plataforma')
    Genero = apps.get_model('appPrincipal', 'Genero')
    for nombre, requiere_plataforma, requiere_genero in CATEGORIAS:
        Categoria.objects.create(nombre=nombre, requiere_plataforma=requiere_plataforma,
                                 requiere_genero=requiere_genero)
    for codigo, nombre, familia, _ in PLATAFORMAS:
        Plataforma.objects.create(codigo=codigo, nombre=nombre, familia=familia)
    for _, nombre in GENEROS:
        Genero.objects.create(nombre=nombre)


def migrar_productos(apps, schema_editor):
    Producto = apps.get_model('appPrincipal', 'Producto')
    categorias = {c.nombre: c for c in apps.get_model('appPrincipal', 'Categoria').objects.all()}
    plataformas = {p.codigo: p for p in apps.get_model('appPrincipal', 'Plataforma').objects.all()}
    generos = {g.nombre: g for g in apps.get_model('appPrincipal', 'Genero').objects.all()}
    nombre_genero = dict(GENEROS)
    for producto in Producto.objects.all():
        categoria, plataforma = categoria_antigua(producto.categoria)
        producto.categoria_ref = categorias[categoria]
        producto.plataforma = plataformas[plataforma] if plataforma else None
        producto.genero_ref = generos.get(nombre_genero.get(producto.genero))
        producto.save(update_fields=['categoria_ref', 'plataforma', 'genero_ref'])


def migrar_categorias_ocultas(apps, schema_editor):
    """Una categoría nueva queda oculta si estaban ocultas todas sus entradas antiguas del navbar."""
    ConfiguracionSitio = apps.get_model('appPrincipal', 'ConfiguracionSitio')
    Categoria = apps.get_model('appPrincipal', 'Categoria')
    configuracion = ConfiguracionSitio.objects.filter(pk=1).first()
    ocultas = set(configuracion.categorias_ocultas or []) if configuracion else set()
    if not ocultas:
        return
    antiguas_por_categoria = {}
    for _, _, _, antiguas in PLATAFORMAS:
        for texto in antiguas:
            antiguas_por_categoria.setdefault(categoria_antigua(texto)[0], set()).add(texto)
    for texto, nombre in FIGURAS.items():
        antiguas_por_categoria.setdefault(nombre, set()).add(texto)
    for nombre, antiguas in antiguas_por_categoria.items():
        if antiguas <= ocultas:
            Categoria.objects.filter(nombre=nombre).update(visible_en_menu=False)


class Migration(migrations.Migration):

    dependencies = [
        ('appPrincipal', '0010_modelo_datos_hu_y_kpi'),
    ]

    operations = [
        migrations.CreateModel(
            name='Categoria',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('nombre', models.CharField(max_length=40, unique=True)),
                ('visible_en_menu', models.BooleanField(default=True)),
                ('requiere_plataforma', models.BooleanField(default=False)),
                ('requiere_genero', models.BooleanField(default=False)),
            ],
            options={'ordering': ['id']},
        ),
        migrations.CreateModel(
            name='Plataforma',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('codigo', models.SlugField(max_length=20, unique=True)),
                ('nombre', models.CharField(max_length=40, unique=True)),
                ('familia', models.CharField(max_length=12)),
            ],
            options={'ordering': ['id']},
        ),
        migrations.CreateModel(
            name='Genero',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('nombre', models.CharField(max_length=40, unique=True)),
            ],
            options={'ordering': ['id']},
        ),
        migrations.RunPython(cargar_catalogo, migrations.RunPython.noop),
        migrations.AddField(
            model_name='producto',
            name='categoria_ref',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name='+', to='appPrincipal.categoria'),
        ),
        migrations.AddField(
            model_name='producto',
            name='plataforma',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name='productos', to='appPrincipal.plataforma'),
        ),
        migrations.AddField(
            model_name='producto',
            name='genero_ref',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name='+', to='appPrincipal.genero'),
        ),
        migrations.RunPython(migrar_productos, migrations.RunPython.noop),
        migrations.RemoveField(model_name='producto', name='categoria'),
        migrations.RemoveField(model_name='producto', name='genero'),
        migrations.RenameField(model_name='producto', old_name='categoria_ref', new_name='categoria'),
        migrations.RenameField(model_name='producto', old_name='genero_ref', new_name='genero'),
        migrations.AlterField(
            model_name='producto',
            name='categoria',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='productos',
                                    to='appPrincipal.categoria', verbose_name='Categoría'),
        ),
        migrations.AlterField(
            model_name='producto',
            name='genero',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name='productos', to='appPrincipal.genero', verbose_name='Género'),
        ),
        migrations.RunPython(migrar_categorias_ocultas, migrations.RunPython.noop),
        migrations.RemoveField(model_name='configuracionsitio', name='categorias_ocultas'),
    ]
