"""Páginas legales del sitio."""
from django.shortcuts import render

from appPrincipal.constants import (
    CONDICIONES_COMPRA, POLITICA_PRIVACIDAD_FECHA, POLITICA_PRIVACIDAD_VERSION, POLITICA_RETRACTO,
    RESPONSABLE_DATOS, TERMINOS_FECHA, TERMINOS_VERSION,
)
from appPrincipal.envios import HORARIO_TIENDA, OPCIONES_ENVIO, TRANSPORTISTAS_ENCOMIENDA


def politica_privacidad(request):
    return render(request, 'politica_privacidad.html', {
        'responsable': RESPONSABLE_DATOS,
        'version': POLITICA_PRIVACIDAD_VERSION,
        'fecha_actualizacion': POLITICA_PRIVACIDAD_FECHA,
        'transportistas': TRANSPORTISTAS_ENCOMIENDA,
    })


def terminos_condiciones(request):
    return render(request, 'terminos_condiciones.html', {
        'responsable': RESPONSABLE_DATOS,
        'version': TERMINOS_VERSION,
        'fecha_actualizacion': TERMINOS_FECHA,
        'opciones_envio': OPCIONES_ENVIO.values(),
        'horario_tienda': HORARIO_TIENDA,
        'transportistas_por_pagar': [t for t in TRANSPORTISTAS_ENCOMIENDA if t != 'Bluexpress'],
        'garantia': CONDICIONES_COMPRA[:2],
        'retracto': POLITICA_RETRACTO,
    })
