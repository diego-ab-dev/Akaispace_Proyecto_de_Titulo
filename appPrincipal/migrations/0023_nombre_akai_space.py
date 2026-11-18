"""La tienda se llama "Akai Space" (separado): renombra el transportista de los delivery ya registrados."""
from django.db import migrations


def separar_nombre(apps, schema_editor):
    Envio = apps.get_model('appPrincipal', 'Envio')
    Envio.objects.filter(transportista='Delivery Akaispace').update(transportista='Delivery Akai Space')


def juntar_nombre(apps, schema_editor):
    Envio = apps.get_model('appPrincipal', 'Envio')
    Envio.objects.filter(transportista='Delivery Akai Space').update(transportista='Delivery Akaispace')


class Migration(migrations.Migration):

    dependencies = [
        ('appPrincipal', '0022_barra_de_anuncio'),
    ]

    operations = [
        migrations.RunPython(separar_nombre, juntar_nombre),
    ]
