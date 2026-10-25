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

# Política de privacidad
POLITICA_PRIVACIDAD_VERSION = '1.1'
POLITICA_PRIVACIDAD_FECHA = '24 de octubre de 2026'

# Términos y condiciones
TERMINOS_VERSION = '1.0'
TERMINOS_FECHA = '6 de octubre de 2026'

# Datos del responsable del tratamiento que aparecen en la política.
# El RUT es ficticio
RESPONSABLE_DATOS = {
    'nombre_comercial': 'Akaispace',
    'razon_social': 'Carlos Fuentes Riquelme',
    'rut': '15.432.876-9',
    'domicilio': 'Galería Caupolicán 544, Local 26, Valdivia, Región de Los Ríos, Chile',
    'correo_privacidad': 'akaispacevaldivia@gmail.com',
    'telefono': '+56 9 6156 1944',
    'proveedor_hosting': 'Amazon Web Services (AWS), con servidores en São Paulo, Brasil',
}

# Condiciones y política de retracto que se envían en el correo de confirmación de compra
# Siguen la Ley 19.496 del Consumidor
CONDICIONES_COMPRA = [
    'Garantía legal de 6 meses desde que recibes el producto: si presenta una falla, puedes elegir '
    'entre su cambio, reparación o la devolución del dinero.',
    'Para usar la garantía o hacer un reclamo, ingresa a "Mis compras" en tu perfil o escríbenos al '
    f'correo {RESPONSABLE_DATOS["correo_privacidad"]}.',
    'Los precios incluyen IVA. El costo de envío es el informado al momento de pagar.',
]
POLITICA_RETRACTO = [
    'Tienes 10 días corridos desde que recibes o retiras tu pedido para retractarte de la compra, '
    'sin necesidad de dar un motivo (artículo 3 bis de la Ley 19.496).',
    'El producto debe estar sin uso y con su embalaje original, etiquetas, manuales y accesorios en buen estado.',
    'Para ejercerlo, solicita la devolución desde "Mis compras" o escríbenos indicando el número de tu pedido.',
    'Te devolveremos el monto pagado al mismo medio de pago, a la brevedad y como máximo dentro de 45 días '
    'desde que nos informas el retracto.',
]


# Menús de categorías del navbar. Cada entrada es (categoría, código de plataforma o None, etiqueta) y
# enlaza a esa categoría filtrada por la plataforma. El admin oculta una categoría completa desde el panel
# (Configuración, Categoria.visible_en_menu); oculta sigue existiendo y sus productos siguen a la venta.
# clase_flecha / clase_submenu: las usa static/js/navbar.js para abrir el menú en celulares.
MENU_NAVBAR = [
    {
        'nombre': 'Videojuegos', 'promo': 'menu_videojuegos',
        'clase_flecha': 'htmlcss-arrow', 'clase_submenu': 'htmlCss-sub-menu',
        'texto_link': 'Ver detalles', 'color_etiqueta': '', 'vacio': 'Próximamente',
        'grupos': [
            ('PlayStation', [('Videojuegos', 'ps3', 'PlayStation 3'), ('Videojuegos', 'ps4', 'PlayStation 4'),
                             ('Videojuegos', 'ps5', 'PlayStation 5')]),
            ('Microsoft', [('Videojuegos', 'xbox360', 'XBOX 360'), ('Videojuegos', 'xboxone', 'XBOX ONE'),
                           ('Videojuegos', 'xboxseries', 'XBOX SERIES')]),
            ('Nintendo', [('Videojuegos', 'switch', 'SWITCH'), ('Videojuegos', '3ds', '3DS'),
                          ('Videojuegos', 'wii', 'WII'), ('Videojuegos', 'wiiu', 'WII U')]),
            ('PC', [('Videojuegos', 'pc', 'Videojuegos PC')]),
        ],
    },
    {
        'nombre': 'Consolas', 'promo': 'menu_consolas',
        'clase_flecha': 'js-arrow', 'clase_submenu': 'js-sub-menu',
        'texto_link': 'Ver consola', 'color_etiqueta': '', 'vacio': 'Próximamente',
        'grupos': [
            ('PlayStation', [('Consolas', 'ps4', 'PlayStation 4'), ('Consolas', 'ps5', 'PlayStation 5')]),
            ('Microsoft', [('Consolas', 'xboxone', 'XBOX ONE'), ('Consolas', 'xboxseries', 'XBOX SERIES')]),
            ('Nintendo', [('Consolas', 'wiiu', 'WII U'), ('Consolas', 'switch', 'SWITCH')]),
        ],
    },
    {
        'nombre': 'Accesorios', 'promo': 'menu_accesorios',
        'clase_flecha': 'js-arrow', 'clase_submenu': 'js-sub-menu',
        'texto_link': 'Ver accesorio', 'color_etiqueta': '#8e44ad', 'vacio': 'Sin stock destacado',
        'grupos': [
            ('PlayStation', [('Accesorios', 'psp', 'PSP'), ('Accesorios', 'psvita', 'VITA'),
                             ('Accesorios', 'ps1', 'PLAY STATION 1'), ('Accesorios', 'ps2', 'PLAY STATION 2'),
                             ('Accesorios', 'ps3', 'PLAY STATION 3'), ('Accesorios', 'ps4', 'PLAY STATION 4'),
                             ('Accesorios', 'ps5', 'PLAY STATION 5')]),
            ('Microsoft', [('Accesorios', 'xbox360', 'XBOX 360'), ('Accesorios', 'xboxone', 'XBOX ONE'),
                           ('Accesorios', 'xboxseries', 'XBOX SERIES')]),
            ('Nintendo', [('Accesorios', '3ds', '3DS'), ('Accesorios', 'wiiu', 'WII U'),
                          ('Accesorios', 'switch', 'SWITCH')]),
        ],
    },
    {
        'nombre': 'Figuras', 'promo': 'menu_figuras',
        'clase_flecha': 'js-arrow', 'clase_submenu': 'js-sub-menu',
        'texto_link': 'Lo quiero', 'color_etiqueta': '#f39c12', 'vacio': 'Próximamente',
        'grupos': [
            ('Coleccionables', [('Funko Pop', None, 'FUNKO POP'), ('Amiibo', None, 'AMIIBO')]),
        ],
    },
]
