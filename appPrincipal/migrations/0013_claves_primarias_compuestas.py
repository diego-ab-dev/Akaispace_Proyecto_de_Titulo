"""Las tablas de detalle pasan a clave primaria compuesta y pierden su columna id.

Django no puede convertir una tabla existente a clave compuesta, así que para cada una se crea el
modelo nuevo (con su nombre de tabla definitivo), se copian las filas, se elimina el modelo viejo y
se renombra el nuevo. Además, la lista de productos de cada pago Webpay deja de ser un JSON
(PagoWebpay.items, un grupo repetitivo) y pasa a la tabla detalle_pago_webpay.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _copiar(origen, destino, campos):
    def copiar(apps, schema_editor):
        Origen = apps.get_model('appPrincipal', origen)
        Destino = apps.get_model('appPrincipal', destino)
        Destino.objects.bulk_create([
            Destino(**{campo: valor(fila) for campo, valor in campos.items()})
            for fila in Origen.objects.all()
        ])
    return copiar


def copiar_items_de_pagos(apps, schema_editor):
    PagoWebpay = apps.get_model('appPrincipal', 'PagoWebpay')
    DetallePagoWebpay = apps.get_model('appPrincipal', 'DetallePagoWebpay')
    Producto = apps.get_model('appPrincipal', 'Producto')
    existentes = set(Producto.objects.values_list('id', flat=True))
    detalles = []
    for pago in PagoWebpay.objects.all():
        cantidades = {}
        for item in pago.items or []:
            if item['producto_id'] not in existentes:
                continue
            cantidad, precio = cantidades.get(item['producto_id'], (0, item['precio_unitario']))
            cantidades[item['producto_id']] = (cantidad + item['cantidad'], precio)
        detalles += [
            DetallePagoWebpay(pago=pago, producto_id=producto_id, cantidad=cantidad, precio_unitario=precio)
            for producto_id, (cantidad, precio) in cantidades.items()
        ]
    DetallePagoWebpay.objects.bulk_create(detalles)


def _clave(*campos):
    return ('pk', models.CompositePrimaryKey(*campos, blank=True, editable=False, primary_key=True, serialize=False))


def _fk(modelo, on_delete=django.db.models.deletion.CASCADE):
    return models.ForeignKey(on_delete=on_delete, related_name='+', to=modelo)


class Migration(migrations.Migration):

    dependencies = [
        ('appPrincipal', '0012_imagenes'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # detalle_venta (ProductoVenta): hoy permite repetir un producto en la misma venta
        migrations.CreateModel(
            name='ProductoVentaNuevo',
            fields=[
                _clave('venta_id', 'producto_id'),
                ('venta', _fk('appPrincipal.venta')),
                ('producto', _fk('appPrincipal.producto', django.db.models.deletion.PROTECT)),
                ('cantidad', models.PositiveIntegerField(default=1)),
                ('precio_unitario', models.PositiveIntegerField()),
                ('costo_unitario', models.PositiveIntegerField(blank=True, null=True)),
            ],
            options={'db_table': 'detalle_venta'},
        ),
        migrations.RunPython(_copiar('ProductoVenta', 'ProductoVentaNuevo', {
            'venta_id': lambda f: f.venta_id,
            'producto_id': lambda f: f.producto_id,
            'cantidad': lambda f: f.cantidad,
            'precio_unitario': lambda f: f.precio_unitario,
            # 0 era el valor por defecto de la migración 0010: significa costo no registrado
            'costo_unitario': lambda f: f.costo_unitario or None,
        }), migrations.RunPython.noop),
        migrations.DeleteModel(name='ProductoVenta'),
        migrations.RenameModel(old_name='ProductoVentaNuevo', new_name='ProductoVenta'),
        migrations.AlterField(
            model_name='productoventa', name='venta',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='producto_venta',
                                    to='appPrincipal.venta'),
        ),
        migrations.AlterField(
            model_name='productoventa', name='producto',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='appPrincipal.producto'),
        ),

        # item_carrito (ItemCarritoProducto)
        migrations.CreateModel(
            name='ItemCarritoNuevo',
            fields=[
                _clave('carrito_id', 'producto_id'),
                ('carrito', _fk('appPrincipal.carrito')),
                ('producto', _fk('appPrincipal.producto')),
                ('cantidad', models.PositiveIntegerField(default=1)),
            ],
            options={'db_table': 'item_carrito'},
        ),
        migrations.RunPython(_copiar('ItemCarritoProducto', 'ItemCarritoNuevo', {
            'carrito_id': lambda f: f.carrito_id,
            'producto_id': lambda f: f.producto_id,
            'cantidad': lambda f: f.cantidad,
        }), migrations.RunPython.noop),
        migrations.DeleteModel(name='ItemCarritoProducto'),
        migrations.RenameModel(old_name='ItemCarritoNuevo', new_name='ItemCarritoProducto'),
        migrations.AlterField(
            model_name='itemcarritoproducto', name='carrito',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items',
                                    to='appPrincipal.carrito'),
        ),
        migrations.AlterField(
            model_name='itemcarritoproducto', name='producto',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='appPrincipal.producto'),
        ),

        # detalle_compra (DetalleCompra)
        migrations.CreateModel(
            name='DetalleCompraNuevo',
            fields=[
                _clave('compra_id', 'producto_id'),
                ('compra', _fk('appPrincipal.compra')),
                ('producto', _fk('appPrincipal.producto', django.db.models.deletion.PROTECT)),
                ('cantidad', models.PositiveIntegerField(default=1)),
                ('costo_unitario', models.PositiveIntegerField()),
            ],
            options={'db_table': 'detalle_compra'},
        ),
        migrations.RunPython(_copiar('DetalleCompra', 'DetalleCompraNuevo', {
            'compra_id': lambda f: f.compra_id,
            'producto_id': lambda f: f.producto_id,
            'cantidad': lambda f: f.cantidad,
            'costo_unitario': lambda f: f.costo_unitario,
        }), migrations.RunPython.noop),
        migrations.DeleteModel(name='DetalleCompra'),
        migrations.RenameModel(old_name='DetalleCompraNuevo', new_name='DetalleCompra'),
        migrations.AlterField(
            model_name='detallecompra', name='compra',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='detalles',
                                    to='appPrincipal.compra'),
        ),
        migrations.AlterField(
            model_name='detallecompra', name='producto',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='compras',
                                    to='appPrincipal.producto'),
        ),

        # favorito (Favorito)
        migrations.CreateModel(
            name='FavoritoNuevo',
            fields=[
                _clave('usuario_id', 'producto_id'),
                ('usuario', _fk(settings.AUTH_USER_MODEL)),
                ('producto', _fk('appPrincipal.producto')),
            ],
            options={'db_table': 'favorito'},
        ),
        migrations.RunPython(_copiar('Favorito', 'FavoritoNuevo', {
            'usuario_id': lambda f: f.usuario_id,
            'producto_id': lambda f: f.producto_id,
        }), migrations.RunPython.noop),
        migrations.DeleteModel(name='Favorito'),
        migrations.RenameModel(old_name='FavoritoNuevo', new_name='Favorito'),
        migrations.AlterField(
            model_name='favorito', name='usuario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='favorito', name='producto',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='appPrincipal.producto'),
        ),

        # detalle_pago_webpay: reemplaza al JSON PagoWebpay.items
        migrations.CreateModel(
            name='DetallePagoWebpay',
            fields=[
                _clave('pago_id', 'producto_id'),
                ('pago', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='detalles',
                                           to='appPrincipal.pagowebpay')),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                               to='appPrincipal.producto')),
                ('cantidad', models.PositiveIntegerField()),
                ('precio_unitario', models.PositiveIntegerField()),
            ],
            options={'db_table': 'detalle_pago_webpay'},
        ),
        migrations.RunPython(copiar_items_de_pagos, migrations.RunPython.noop),
        migrations.RemoveField(model_name='pagowebpay', name='items'),
    ]
