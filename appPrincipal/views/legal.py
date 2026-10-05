"""Páginas legales del sitio."""
from django.shortcuts import render

from appPrincipal.constants import POLITICA_PRIVACIDAD_FECHA, POLITICA_PRIVACIDAD_VERSION, RESPONSABLE_DATOS


def politica_privacidad(request):
    return render(request, 'politica_privacidad.html', {
        'responsable': RESPONSABLE_DATOS,
        'version': POLITICA_PRIVACIDAD_VERSION,
        'fecha_actualizacion': POLITICA_PRIVACIDAD_FECHA,
    })
