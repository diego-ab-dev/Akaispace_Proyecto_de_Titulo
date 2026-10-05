"""Datos fijos compartidos por formularios, vistas y plantillas."""

# ciudades disponibles por región (los formularios validan que la ciudad sea de la región)
REGIONES_CIUDADES = {
    'ARICA Y PARINACOTA': ['Arica', 'Putre'],
    'TARAPACA': ['Iquique', 'Alto Hospicio'],
    'ANTOFAGASTA': ['Antofagasta', 'Calama', 'Tocopilla'],
    'ATACAMA': ['Copiapó', 'Vallenar', 'Chañaral'],
    'COQUIMBO': ['La Serena', 'Coquimbo', 'Ovalle'],
    'VALPARAISO': ['Valparaíso', 'Viña del Mar', 'Quillota', 'San Antonio'],
    'METROPOLITANA': ['Santiago', 'Puente Alto', 'Maipú', 'La Florida'],
    'OHIGGINS': ['Rancagua', 'San Fernando', 'Pichilemu'],
    'MAULE': ['Talca', 'Curicó', 'Linares'],
    'ÑUBLE': ['Chillán', 'San Carlos'],
    'BIOBIO': ['Concepción', 'Los Ángeles', 'Coronel'],
    'ARAUCANIA': ['Temuco', 'Villarrica', 'Angol'],
    'LOS RIOS': ['Valdivia', 'La Unión'],
    'LOS LAGOS': ['Puerto Montt', 'Osorno', 'Castro'],
    'AYSEN': ['Coyhaique', 'Puerto Aysén'],
    'MAGALLANES': ['Punta Arenas', 'Puerto Natales'],
}

# nombre completo de cada región, para los <select>
REGIONES = [
    ('ARICA Y PARINACOTA', 'Región de Arica y Parinacota'),
    ('TARAPACA', 'Región de Tarapacá'),
    ('ANTOFAGASTA', 'Región de Antofagasta'),
    ('ATACAMA', 'Región de Atacama'),
    ('COQUIMBO', 'Región de Coquimbo'),
    ('VALPARAISO', 'Región de Valparaíso'),
    ('METROPOLITANA', 'Región Metropolitana de Santiago'),
    ('OHIGGINS', 'Región del Libertador General Bernardo O\'Higgins'),
    ('MAULE', 'Región del Maule'),
    ('ÑUBLE', 'Región de Ñuble'),
    ('BIOBIO', 'Región del Biobío'),
    ('ARAUCANIA', 'Región de La Araucanía'),
    ('LOS RIOS', 'Región de Los Ríos'),
    ('LOS LAGOS', 'Región de Los Lagos'),
    ('AYSEN', 'Región de Aysén del General Carlos Ibáñez del Campo'),
    ('MAGALLANES', 'Región de Magallanes y de la Antártica Chilena'),
]

# Política de privacidad (templates/politica_privacidad.html).
# Si cambia el contenido de la política, sube la versión y la fecha: cada usuario guarda
# la versión que aceptó al registrarse (Usuario.privacidad_version).
POLITICA_PRIVACIDAD_VERSION = '1.0'
POLITICA_PRIVACIDAD_FECHA = '5 de octubre de 2026'

# Datos del responsable del tratamiento que aparecen en la política.
# El RUT es ficticio (proyecto académico): reemplazarlo por el real antes de publicar el sitio.
RESPONSABLE_DATOS = {
    'nombre_comercial': 'Akaispace',
    'razon_social': 'Carlos Fuentes Riquelme',
    'rut': '15.432.876-9',
    'domicilio': 'Galería Caupolicán 544, Local 26, Valdivia, Región de Los Ríos, Chile',
    'correo_privacidad': 'akaispacevaldivia@gmail.com',
    'telefono': '+56 9 6156 1944',
    'proveedor_hosting': 'Amazon Web Services (AWS), con servidores en São Paulo, Brasil',
}
