from django.db import migrations, models


# las ventas que ya existían se marcan como enviadas, para que el comando reenviar_confirmaciones
# no les mande un correo antiguo
def marcar_ventas_existentes(apps, schema_editor):
    Venta = apps.get_model('appPrincipal', 'Venta')
    Venta.objects.update(confirmacion_enviada=True)


class Migration(migrations.Migration):

    dependencies = [
        ('appPrincipal', '0017_devolucion_fk_detalle_venta'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='confirmacion_enviada',
            field=models.BooleanField(default=False, db_comment='Indica si se envió el correo de confirmación de compra (HU-06). Las ventas web con 0 se reenvían con el comando reenviar_confirmaciones.'),
        ),
        migrations.RunPython(marcar_ventas_existentes, migrations.RunPython.noop),
    ]
