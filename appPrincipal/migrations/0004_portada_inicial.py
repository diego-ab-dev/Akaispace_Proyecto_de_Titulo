from django.db import migrations


def cargar_portada(apps, schema_editor):
    from appPrincipal.portada_inicial import cargar
    cargar(apps.get_model('appPrincipal', 'Destacado'), apps.get_model('appPrincipal', 'Producto'))


class Migration(migrations.Migration):

    dependencies = [
        ('appPrincipal', '0003_destacados'),
    ]

    operations = [
        migrations.RunPython(cargar_portada, migrations.RunPython.noop),
    ]
