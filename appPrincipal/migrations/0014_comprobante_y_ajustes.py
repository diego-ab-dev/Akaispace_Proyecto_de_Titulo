"""Boleta pasa a llamarse Comprobante (la plataforma emite un comprobante NO tributario) y ajustes de
datos que requieren pasos intermedios: costos en 0 a NULL, códigos de barra vacíos a NULL antes de
hacerlos únicos, RUT vacíos a NULL, y venta y producto obligatorios en Devolucion.
"""
import django.db.models.deletion
from django.db import migrations, models


def costos_en_cero_a_null(apps, schema_editor):
    # 0 era el valor por defecto de la migración 0010: significa costo no registrado
    apps.get_model('appPrincipal', 'Producto').objects.filter(costo=0).update(costo=None)


def vacios_a_null(apps, schema_editor):
    apps.get_model('appPrincipal', 'Producto').objects.filter(codigo_de_barra='').update(codigo_de_barra=None)
    apps.get_model('appPrincipal', 'Usuario').objects.filter(rut='').update(rut=None)
    apps.get_model('appPrincipal', 'Proveedor').objects.filter(rut='').update(rut=None)


def revisar_devoluciones(apps, schema_editor):
    Devolucion = apps.get_model('appPrincipal', 'Devolucion')
    incompletas = Devolucion.objects.filter(models.Q(venta__isnull=True) | models.Q(producto__isnull=True))
    if incompletas.exists():
        raise RuntimeError(
            "Hay devoluciones sin venta o sin producto (ids: %s). Corrígelas antes de migrar."
            % list(incompletas.values_list('id', flat=True))
        )


class Migration(migrations.Migration):

    dependencies = [
        ('appPrincipal', '0013_claves_primarias_compuestas'),
    ]

    operations = [
        migrations.RenameModel(old_name='Boleta', new_name='Comprobante'),
        migrations.AlterField(
            model_name='comprobante', name='venta',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='comprobante',
                                       to='appPrincipal.venta'),
        ),
        migrations.AlterField(
            model_name='comprobante', name='archivo_pdf',
            field=models.FileField(blank=True, null=True, upload_to='comprobantes/'),
        ),

        migrations.AlterField(
            model_name='producto', name='costo',
            field=models.PositiveIntegerField(blank=True, null=True,
                                              help_text='Costo unitario con IVA, para calcular la ganancia.'),
        ),
        migrations.RunPython(costos_en_cero_a_null, migrations.RunPython.noop),

        migrations.AlterField(
            model_name='producto', name='codigo_de_barra',
            field=models.CharField(blank=True, db_index=True, max_length=20, null=True, verbose_name='Código de Barra'),
        ),
        migrations.RunPython(vacios_a_null, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='producto', name='codigo_de_barra',
            field=models.CharField(blank=True, max_length=20, null=True, unique=True, verbose_name='Código de Barra'),
        ),

        migrations.RunPython(revisar_devoluciones, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='devolucion', name='venta',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='devoluciones',
                                    to='appPrincipal.venta'),
        ),
        migrations.AlterField(
            model_name='devolucion', name='producto',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='appPrincipal.producto'),
        ),
    ]
