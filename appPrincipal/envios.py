"""Opciones de entrega del checkout: precios, dónde se ofrecen y estados de cada una.
"""
from appPrincipal.constants import REGIONES, RESPONSABLE_DATOS

CIUDAD_TIENDA = 'Valdivia'
DIRECCION_TIENDA = RESPONSABLE_DATOS['domicilio']
HORARIO_TIENDA = 'Lunes a sábado de 10:00 a 19:30'

ESTADOS_RETIRO = ['En Preparación', 'Listo para retiro', 'Entregado']
ESTADOS_DELIVERY = ['En Preparación', 'En Reparto', 'Entregado']
ESTADOS_ENCOMIENDA = ['En Preparación', 'Enviado', 'En Tránsito', 'En Reparto', 'Entregado']

OPCIONES_ENVIO = {
    'tienda': {
        'nombre': 'Retiro en tienda',
        'resumen': 'Galería Caupolicán 544, Local 26',
        'descripcion': f'Retira en Galería Caupolicán 544, Local 26, Valdivia. {HORARIO_TIENDA}. '
                       'Te avisaremos cuando tu pedido esté listo para retiro.',
        'precio': 0,
        'gratis_desde': None,
        'disponible_en': 'todas',
        'transportista': 'Retiro en tienda',
        'estados': ESTADOS_RETIRO,
    },
    'delivery': {
        'nombre': 'Delivery Express en Valdivia',
        'resumen': 'Mismo día o en 24 h hábiles · Gratis desde $24.990',
        'descripcion': 'Despacho a domicilio exclusivo para Valdivia. Se entrega el mismo día o en un '
                       'plazo máximo de 24 horas hábiles una vez confirmado el pago. ¡Gratis desde $24.990!',
        'precio': 2000,
        'gratis_desde': 24990,
        'disponible_en': 'valdivia',
        'transportista': 'Delivery Akaispace',
        'estados': ESTADOS_DELIVERY,
    },
    'bluexpress': {
        'nombre': 'Envío a región por Bluexpress',
        'resumen': 'Entrega en 1 día hábil',
        'descripcion': 'Entrega en 1 día hábil por encomienda. Nos comunicaremos contigo para confirmar tus datos.',
        'precio': 4500,
        'gratis_desde': None,
        'disponible_en': 'regiones',
        'transportista': 'Bluexpress',
        'estados': ESTADOS_ENCOMIENDA,
    },
    'por_pagar': {
        'nombre': 'Envío por pagar',
        'resumen': 'Encomienda a tu elección · pagas al recibir',
        'descripcion': 'Pagas el envío al recibir. Nos comunicaremos contigo para confirmar tus datos '
                       'y la encomienda que prefieres.',
        'precio': None,
        'gratis_desde': None,
        'disponible_en': 'regiones',
        'transportista': 'Por definir',
        'estados': ESTADOS_ENCOMIENDA,
    },
}

# transportistas
TRANSPORTISTAS_ENCOMIENDA = ['Bluexpress', 'Starken', 'Chilexpress', 'Correos de Chile']


def disponible_para(clave, ciudad):
    opcion = OPCIONES_ENVIO.get(clave)
    if opcion is None:
        return False
    if opcion['disponible_en'] == 'valdivia':
        return ciudad == CIUDAD_TIENDA
    if opcion['disponible_en'] == 'regiones':
        return bool(ciudad) and ciudad != CIUDAD_TIENDA
    return True


def costo_envio(clave, subtotal):
    opcion = OPCIONES_ENVIO[clave]
    if opcion['precio'] is None:
        return 0
    if opcion['gratis_desde'] is not None and subtotal >= opcion['gratis_desde']:
        return 0
    return opcion['precio']


def requiere_direccion(clave):
    return clave != 'tienda'


def estados_para(metodo_envio):
    opcion = OPCIONES_ENVIO.get(metodo_envio)
    return opcion['estados'] if opcion else ESTADOS_ENCOMIENDA


def lleva_seguimiento(metodo_envio):
    return estados_para(metodo_envio) is ESTADOS_ENCOMIENDA


def direccion_de_entrega(clave, usuario):
    if not requiere_direccion(clave):
        return f"Retiro en tienda: {DIRECCION_TIENDA}"
    region = dict(REGIONES).get(usuario.region, usuario.region)
    return ", ".join(parte for parte in [usuario.direccion, usuario.ciudad, region] if parte)


def validar_eleccion(clave, usuario):
    if clave not in OPCIONES_ENVIO:
        return "Elige cómo quieres recibir tu compra."
    if requiere_direccion(clave) and not (usuario.direccion and usuario.ciudad and usuario.region):
        return "Completa tu dirección de entrega para usar esta opción."
    if not disponible_para(clave, usuario.ciudad):
        if OPCIONES_ENVIO[clave]['disponible_en'] == 'valdivia':
            return "El Delivery Express es solo para direcciones en Valdivia."
        return "Esa opción de envío es para direcciones fuera de Valdivia."
    return None


def opciones_para_plantilla():
    return [
        {'clave': clave, **{k: v for k, v in opcion.items() if k != 'estados'}}
        for clave, opcion in OPCIONES_ENVIO.items()
    ]
