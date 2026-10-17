"""Las imágenes pasan de columnas repetidas (imagen_principal a imagen_6 en Producto, imagen1 a imagen3 en
Devolucion) a las tablas ImagenProducto e ImagenDevolucion. Los archivos no se mueven: se copia su ruta.
"""
import django.db.models.deletion
from django.db import migrations, models

CAMPOS_PRODUCTO = ['imagen_principal', 'imagen_2', 'imagen_3', 'imagen_4', 'imagen_5', 'imagen_6']
CAMPOS_DEVOLUCION = ['imagen1', 'imagen2', 'imagen3']


def copiar_imagenes(apps, schema_editor):
    Producto = apps.get_model('appPrincipal', 'Producto')
    ImagenProducto = apps.get_model('appPrincipal', 'ImagenProducto')
    for producto in Producto.objects.all():
        rutas = [getattr(producto, campo).name for campo in CAMPOS_PRODUCTO if getattr(producto, campo)]
        ImagenProducto.objects.bulk_create([
            ImagenProducto(producto=producto, imagen=ruta, es_principal=True if orden == 1 else None, orden=orden)
            for orden, ruta in enumerate(rutas, 1)
        ])

    Devolucion = apps.get_model('appPrincipal', 'Devolucion')
    ImagenDevolucion = apps.get_model('appPrincipal', 'ImagenDevolucion')
    for devolucion in Devolucion.objects.all():
        ImagenDevolucion.objects.bulk_create([
            ImagenDevolucion(devolucion=devolucion, imagen=getattr(devolucion, campo).name)
            for campo in CAMPOS_DEVOLUCION if getattr(devolucion, campo)
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('appPrincipal', '0011_catalogo_normalizado'),
    ]

    operations = [
        migrations.CreateModel(
            name='ImagenProducto',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('imagen', models.ImageField(upload_to='productos/')),
                ('es_principal', models.BooleanField(default=None, null=True)),
                ('orden', models.PositiveSmallIntegerField(default=1)),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                               related_name='imagenes_producto', to='appPrincipal.producto')),
            ],
            options={'ordering': ['-es_principal', 'orden', 'id']},
        ),
        migrations.AddConstraint(
            model_name='imagenproducto',
            constraint=models.UniqueConstraint(fields=('producto', 'es_principal'),
                                               name='una_imagen_principal_por_producto'),
        ),
        migrations.CreateModel(
            name='ImagenDevolucion',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('imagen', models.ImageField(upload_to='devoluciones/')),
                ('devolucion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                 related_name='imagenes', to='appPrincipal.devolucion')),
            ],
            options={'ordering': ['id']},
        ),
        migrations.RunPython(copiar_imagenes, migrations.RunPython.noop),
    ] + [
        migrations.RemoveField(model_name='producto', name=campo) for campo in CAMPOS_PRODUCTO
    ] + [
        migrations.RemoveField(model_name='devolucion', name=campo) for campo in CAMPOS_DEVOLUCION
    ]
