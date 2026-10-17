import re

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, Q
from django.utils.dateparse import parse_datetime
from django.utils.timezone import localdate, now
from django.utils.translation import gettext_lazy as _

from appPrincipal.envios import OPCIONES_ENVIO, costo_envio, estados_para, lleva_seguimiento

# Todas las tablas propias llevan nombre en minúscula y sin prefijo (db_table), y cada columna su
# comentario (db_comment), para generar el diagrama y el diccionario de datos desde MySQL.
# Los montos son enteros en pesos chilenos (CLP) con IVA incluido.


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('El correo electrónico es obligatorio.')
        usuario = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if not extra_fields['is_staff'] or not extra_fields['is_superuser']:
            raise ValueError('Un superusuario debe tener is_staff=True e is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


# clase Usuario
class Usuario(AbstractUser):
    MAYOR_18 = 'mayor_18'
    AUTORIZACION_TUTOR = 'autorizacion_tutor'
    DECLARACIONES_EDAD = [
        (MAYOR_18, 'Mayor de 18 años'),
        (AUTORIZACION_TUTOR, 'Menor de 18 años con autorización de su padre, madre o tutor'),
    ]

    username = None
    first_name = None
    last_name = None

    id = models.BigAutoField(primary_key=True, db_comment="Identificador del usuario.")
    # columnas heredadas de AbstractUser: se redeclaran igual que en Django solo para comentarlas
    password = models.CharField(_("password"), max_length=128,
                                db_comment="Hash de la contraseña generado por Django (algoritmo PBKDF2).")
    last_login = models.DateTimeField(_("last login"), blank=True, null=True,
                                      db_comment="Fecha y hora del último inicio de sesión.")
    is_superuser = models.BooleanField(
        _("superuser status"), default=False,
        help_text=_("Designates that this user has all permissions without explicitly assigning them."),
        db_comment="Indica si el usuario tiene todos los permisos del sistema.",
    )
    is_staff = models.BooleanField(
        _("staff status"), default=False,
        help_text=_("Designates whether the user can log into this admin site."),
        db_comment="Indica si el usuario es administrador de la tienda y accede al panel (HU-09, HU-10, HU-12).",
    )
    is_active = models.BooleanField(
        _("active"), default=True,
        help_text=_("Designates whether this user should be treated as active. "
                    "Unselect this instead of deleting accounts."),
        db_comment="Indica si la cuenta puede iniciar sesión. Se desactiva al eliminar la cuenta.",
    )
    date_joined = models.DateTimeField(_("date joined"), default=now,
                                       db_comment="Fecha y hora de creación de la cuenta.")

    nombre = models.CharField(max_length=100, db_comment="Nombre completo del usuario.")
    email = models.EmailField(unique=True, db_comment="Correo electrónico, en minúscula. Se usa para iniciar sesión (HU-02).")
    rut = models.CharField(max_length=12, unique=True, null=True, blank=True,
                           db_comment="RUT con puntos y guion (ej. 12.345.678-9). NULL si no se registró.")
    telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono",
                                db_comment="Teléfono de contacto.")
    direccion = models.CharField(max_length=120, blank=True, verbose_name="Dirección",
                                 db_comment="Calle y número para el despacho (HU-08).")
    region = models.CharField(max_length=100, blank=True,
                              db_comment="Región de residencia, valor de la lista REGIONES de constants.py.")
    ciudad = models.CharField(max_length=100, blank=True,
                              db_comment="Ciudad de residencia, debe pertenecer a la región.")
    is_deleted = models.BooleanField(default=False,
                                     db_comment="Borrado lógico: 1 si el usuario eliminó su cuenta.")
    deleted_at = models.DateTimeField(null=True, blank=True,
                                      db_comment="Fecha y hora del borrado lógico. NULL si la cuenta está vigente.")
    declaracion_edad = models.CharField(
        max_length=20, choices=DECLARACIONES_EDAD, blank=True, verbose_name="Declaración de edad",
        db_comment="Declaración de edad al registrarse (HU-01). Valores: mayor_18, autorizacion_tutor; "
                   "vacío en cuentas creadas antes de este campo.",
    )
    privacidad_aceptada_en = models.DateTimeField(
        null=True, blank=True, verbose_name="Aceptó la política de privacidad",
        db_comment="Fecha y hora en que aceptó la política de privacidad (HU-01).",
    )
    privacidad_version = models.CharField(max_length=20, blank=True, verbose_name="Versión de la política aceptada",
                                          db_comment="Versión de la política de privacidad aceptada (HU-01).")
    datos_navegacion_autorizados_en = models.DateTimeField(
        null=True, blank=True, verbose_name="Autorizó el uso de datos de navegación",
        db_comment="Fecha y hora en que autorizó usar su navegación para recomendaciones (HU-07). "
                   "NULL si no lo autorizó.",
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre']

    objects = UsuarioManager()

    class Meta:
        db_table = 'usuario'
        db_table_comment = "Clientes y administradores de la tienda (HU-01, HU-02, HU-11)."

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        if not self.rut:
            self.rut = None
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.is_active = False
        self.deleted_at = now()
        self.save()

    def hard_delete(self):
        super().delete()

    def get_full_name(self):
        return self.nombre

    def get_short_name(self):
        return self.nombre

    def __str__(self):
        return self.nombre


# Catálogo: categoría, plataforma y género son tablas propias (HU-07, HU-09, KPI-10).
# Se cargan con datos fijos en la migración 0011; el admin no las edita desde el panel.
class PorNombreManager(models.Manager):
    """Permite usar el nombre como clave natural en los fixtures."""
    campo_natural = 'nombre'

    def get_by_natural_key(self, valor):
        return self.get(**{self.campo_natural: valor})


class PorCodigoManager(PorNombreManager):
    campo_natural = 'codigo'


class Categoria(models.Model):
    id = models.BigAutoField(primary_key=True, db_comment="Identificador de la categoría.")
    nombre = models.CharField(max_length=40, unique=True,
                              db_comment="Nombre de la categoría (ej. Videojuegos, Consolas, Funko Pop).")
    visible_en_menu = models.BooleanField(
        default=True, verbose_name="Visible en el navbar",
        db_comment="Indica si la categoría aparece en los menús del navbar (HU-09). Sus productos se "
                   "siguen vendiendo aunque esté oculta.",
    )
    requiere_plataforma = models.BooleanField(
        default=False, db_comment="Indica si sus productos deben indicar plataforma (HU-07, KPI-10).")
    requiere_genero = models.BooleanField(
        default=False, db_comment="Indica si sus productos deben indicar género (HU-07, KPI-10).")

    objects = PorNombreManager()

    class Meta:
        db_table = 'categoria'
        db_table_comment = "Categorías del catálogo. Definen qué atributos debe tener un producto (HU-09)."
        ordering = ['id']
        verbose_name = "Categoría"

    def __str__(self):
        return self.nombre

    def natural_key(self):
        return (self.nombre,)


class Plataforma(models.Model):
    PLAYSTATION = 'playstation'
    XBOX = 'xbox'
    NINTENDO = 'nintendo'
    PC = 'pc'
    FAMILIAS = [
        (PLAYSTATION, 'PlayStation'),
        (XBOX, 'Xbox'),
        (NINTENDO, 'Nintendo'),
        (PC, 'PC'),
    ]
    id = models.BigAutoField(primary_key=True, db_comment="Identificador de la plataforma.")
    codigo = models.SlugField(max_length=20, unique=True,
                              db_comment="Código corto usado en las URL y filtros (ej. ps5, switch).")
    nombre = models.CharField(max_length=40, unique=True,
                              db_comment="Nombre de la plataforma (ej. PlayStation 5).")
    familia = models.CharField(max_length=12, choices=FAMILIAS,
                               db_comment="Fabricante o familia. Valores: playstation, xbox, nintendo, pc.")

    objects = PorCodigoManager()

    class Meta:
        db_table = 'plataforma'
        db_table_comment = "Consolas y sistemas para los que existe un producto (filtro HU-17, HU-07)."
        ordering = ['id']

    def __str__(self):
        return self.nombre

    def natural_key(self):
        return (self.codigo,)


class Genero(models.Model):
    id = models.BigAutoField(primary_key=True, db_comment="Identificador del género.")
    nombre = models.CharField(max_length=40, unique=True, db_comment="Nombre del género (ej. Acción, RPG).")

    objects = PorNombreManager()

    class Meta:
        db_table = 'genero'
        db_table_comment = "Géneros de videojuegos (filtro HU-17, HU-07)."
        ordering = ['id']
        verbose_name = "Género"

    def __str__(self):
        return self.nombre

    def natural_key(self):
        return (self.nombre,)


# borrado lógico de productos
class ProductoQuerySet(models.QuerySet):
    def delete(self):
        return self.update(is_deleted=True, deleted_at=now())

    def hard_delete(self):
        return super().delete()


class ProductoManager(models.Manager.from_queryset(ProductoQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


# clase Producto
class Producto(models.Model):
    MAXIMO_IMAGENES = 6

    id = models.BigAutoField(primary_key=True, db_comment="Identificador del producto.")
    codigo_de_barra = models.CharField(
        max_length=20, unique=True, null=True, blank=True, verbose_name="Código de Barra",
        db_comment="Código de barras (EAN) para buscar el producto en la venta presencial (HU-12). "
                   "NULL si no tiene.",
    )
    nombre = models.CharField(max_length=100, db_comment="Nombre comercial del producto.")
    precio = models.PositiveIntegerField(default=0, db_comment="Precio de venta en pesos chilenos, IVA incluido.")
    costo = models.PositiveIntegerField(
        null=True, blank=True, help_text="Costo unitario con IVA, para calcular la ganancia.",
        db_comment="Costo unitario vigente en pesos chilenos, IVA incluido. NULL si no se ha registrado; "
                   "esos productos se excluyen del reporte de ganancia (HU-10).",
    )
    stock = models.PositiveIntegerField(default=0, db_comment="Unidades disponibles. Baja con cada venta (HU-06).")
    stock_critico = models.PositiveIntegerField(
        default=5, verbose_name="Stock crítico",
        help_text="Con esta cantidad o menos, el producto aparece en el reporte de stock crítico.",
        db_comment="Con este stock o menos el producto aparece en el reporte de stock crítico (HU-10).",
    )
    descripcion = models.TextField(blank=True, null=True, default='', verbose_name="Descripción",
                                   db_comment="Descripción que se muestra en la ficha del producto.")
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='productos',
                                  verbose_name="Categoría", db_comment="Categoría del producto (FK a categoria).")
    plataforma = models.ForeignKey(
        Plataforma, on_delete=models.PROTECT, null=True, blank=True, related_name='productos',
        db_comment="Plataforma del producto (FK a plataforma). Obligatoria si la categoría la requiere; "
                   "atributo de HU-07 y KPI-10.",
    )
    genero = models.ForeignKey(
        Genero, on_delete=models.PROTECT, null=True, blank=True, related_name='productos', verbose_name="Género",
        db_comment="Género del producto (FK a genero). Obligatorio si la categoría lo requiere; "
                   "atributo de HU-07 y KPI-10.",
    )
    is_deleted = models.BooleanField(default=False,
                                     db_comment="Borrado lógico: 1 si el producto se eliminó del catálogo.")
    deleted_at = models.DateTimeField(null=True, blank=True,
                                      db_comment="Fecha y hora del borrado lógico. NULL si está vigente.")
    objects = ProductoManager()
    todos = ProductoQuerySet.as_manager()

    class Meta:
        db_table = 'producto'
        db_table_comment = "Catálogo de productos de la tienda (HU-09)."

    def __str__(self):
        return self.nombre

    def clean(self):
        categoria = self.categoria if self.categoria_id else None
        errores = {}
        if categoria and categoria.requiere_plataforma and not self.plataforma_id:
            errores['plataforma'] = f"Los productos de {categoria.nombre} deben indicar su plataforma."
        if categoria and categoria.requiere_genero and not self.genero_id:
            errores['genero'] = f"Los productos de {categoria.nombre} deben indicar su género."
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        if not self.codigo_de_barra:
            self.codigo_de_barra = None
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.deleted_at = now()
        self.save()

    def hard_delete(self):
        super().delete()

    def imagenes(self):
        """Archivos de las imágenes del producto, la principal primero.
        En los listados conviene hacer prefetch_related('imagenes_producto')."""
        return [imagen.imagen for imagen in self.imagenes_producto.all()]

    @property
    def imagen_principal(self):
        """Archivo de la imagen principal, o de la primera si ninguna está marcada; None si no tiene."""
        imagenes = self.imagenes()
        return imagenes[0] if imagenes else None

    @property
    def categoria_texto(self):
        """Ej.: "Videojuegos PlayStation 5" o "Funko Pop"."""
        if self.plataforma_id:
            return f"{self.categoria.nombre} {self.plataforma.nombre}"
        return self.categoria.nombre

    def promedio_puntuacion(self):
        opiniones = self.opiniones.all()
        if not opiniones:
            return 0
        return round(sum(opinion.puntuacion for opinion in opiniones) / len(opiniones), 1)


# clase ImagenProducto: hasta 6 imágenes por producto (límite del formulario)
class ImagenProducto(models.Model):
    id = models.BigAutoField(primary_key=True, db_comment="Identificador de la imagen.")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='imagenes_producto',
                                 db_comment="Producto al que pertenece la imagen (FK a producto).")
    imagen = models.ImageField(upload_to='productos/',
                               db_comment="Ruta del archivo dentro de media/ (carpeta productos/).")
    # True = principal; NULL = secundaria. MySQL no tiene índices únicos parciales, así que la
    # restricción única (producto, es_principal), que ignora los NULL, asegura una sola principal.
    es_principal = models.BooleanField(
        null=True, default=None,
        db_comment="1 si es la imagen principal del producto; NULL si es secundaria. "
                   "Solo puede haber una principal por producto.",
    )
    orden = models.PositiveSmallIntegerField(default=1,
                                             db_comment="Posición de la imagen en la galería de la ficha (1 a 6).")

    class Meta:
        db_table = 'imagen_producto'
        db_table_comment = "Imágenes de cada producto (HU-09)."
        ordering = ['-es_principal', 'orden', 'id']
        constraints = [
            models.UniqueConstraint(fields=['producto', 'es_principal'], name='una_imagen_principal_por_producto'),
        ]

    def __str__(self):
        return f"Imagen {self.orden} de {self.producto}"


class CarritoVigenteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(vigente=True)


# clase Carrito: cada usuario tiene un carrito vigente; al pagarse queda en el historial (KPI-04)
class Carrito(models.Model):
    id = models.BigAutoField(primary_key=True, db_comment="Identificador del carrito.")
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='carritos',
                                db_comment="Dueño del carrito (FK a usuario).")
    # True = carrito en uso; NULL = ya se pagó. La restricción única ignora los NULL,
    # así la BD permite un solo carrito vigente por usuario y muchos en el historial.
    vigente = models.BooleanField(
        null=True, default=True,
        db_comment="1 si es el carrito en uso; NULL si ya se pagó y quedó en el historial (KPI-04).",
    )
    creado_en = models.DateTimeField(default=now, db_comment="Fecha y hora de creación del carrito.")
    convertido_en = models.DateTimeField(
        null=True, blank=True, verbose_name="Pagado en",
        db_comment="Fecha y hora en que el carrito se convirtió en compra. NULL si no se ha pagado (KPI-04).",
    )

    objects = CarritoVigenteManager()
    todos = models.Manager()

    class Meta:
        db_table = 'carrito'
        db_table_comment = "Carritos de compra, vigentes y pagados, para medir la conversión (KPI-04)."
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'vigente'], name='un_carrito_vigente_por_usuario'),
        ]

    def cerrar(self):
        """Deja el carrito en el historial como convertido en compra."""
        self.vigente = None
        self.convertido_en = now()
        self.save(update_fields=['vigente', 'convertido_en'])

    def total_carrito(self):
        return sum(
            (item.producto.precio or 0) * max(item.cantidad, 0) for item in self.items.all()
        )


# clase de ItemCarritoProducto
class ItemCarritoProducto(models.Model):
    pk = models.CompositePrimaryKey('carrito_id', 'producto_id')
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items',
                                db_comment="Carrito al que pertenece el ítem (FK a carrito). Parte de la clave primaria.")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE,
                                 db_comment="Producto agregado (FK a producto). Parte de la clave primaria.")
    cantidad = models.PositiveIntegerField(default=1, db_comment="Unidades del producto en el carrito.")

    class Meta:
        db_table = 'item_carrito'
        db_table_comment = "Productos de cada carrito. Clave primaria compuesta (carrito_id, producto_id)."


# clase Venta
class Venta(models.Model):
    ENVIO_CHOICES = [
        ('tienda', 'Retiro en tienda'),
        ('delivery', 'Delivery Express en Valdivia'),
        ('bluexpress', 'Envío a región por Bluexpress'),
        ('por_pagar', 'Envío por pagar'),
        ('domicilio', 'Envío a domicilio'),
    ]
    CANAL_WEB = 'web'
    CANAL_TIENDA = 'tienda'
    CANAL_WHATSAPP = 'whatsapp'
    CANALES = [
        (CANAL_WEB, 'Tienda en línea'),
        (CANAL_TIENDA, 'Tienda física'),
        (CANAL_WHATSAPP, 'WhatsApp'),
    ]
    PAGO_WEBPAY = 'webpay'
    PAGO_TARJETA = 'tarjeta'
    PAGO_EFECTIVO = 'efectivo'
    PAGO_TRANSFERENCIA = 'transferencia'
    METODOS_PAGO = [
        (PAGO_WEBPAY, 'Webpay'),
        (PAGO_TARJETA, 'Tarjeta en terminal'),
        (PAGO_EFECTIVO, 'Efectivo'),
        (PAGO_TRANSFERENCIA, 'Transferencia'),
    ]
    id = models.BigAutoField(primary_key=True, db_comment="Identificador y número de la venta.")
    # las ventas presenciales (HU-12) pueden no tener un cliente con cuenta
    usuario = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, null=True, blank=True, related_name='ventas',
        db_comment="Cliente que compró (FK a usuario). NULL en ventas presenciales sin cuenta (HU-12).",
    )
    canal = models.CharField(
        max_length=10, choices=CANALES, default=CANAL_WEB,
        db_comment="Canal de la venta (KPI-01). Valores: web, tienda, whatsapp.",
    )
    envio = models.PositiveIntegerField(default=0,
                                        db_comment="Costo de envío cobrado, en pesos chilenos con IVA incluido (HU-08).")
    subtotal = models.PositiveIntegerField(
        default=0, db_comment="Suma de los productos al momento de la venta, en pesos chilenos con IVA incluido.")
    total = models.PositiveIntegerField(default=0,
                                        db_comment="Subtotal más envío, en pesos chilenos con IVA incluido.")
    metodo_pago = models.CharField(
        max_length=15, choices=METODOS_PAGO, blank=True, default='',
        db_comment="Medio de pago (HU-05, HU-12). Valores: webpay, tarjeta, efectivo, transferencia.",
    )
    fecha = models.DateTimeField(auto_now_add=True, db_index=True, db_comment="Fecha y hora de la venta.")
    metodo_envio = models.CharField(
        max_length=10, choices=ENVIO_CHOICES, blank=True, default='',
        db_comment="Forma de entrega (HU-08). Valores: tienda, delivery, bluexpress, por_pagar, domicilio; "
                   "vacío en ventas presenciales.",
    )
    direccion_envio = models.TextField(
        blank=True, null=True,
        db_comment="Dirección de entrega al momento de la compra (copia histórica de la del cliente).",
    )
    anulada_en = models.DateTimeField(null=True, blank=True, verbose_name="Anulada en",
                                      db_comment="Fecha y hora de anulación. NULL si la venta está vigente.")

    class Meta:
        db_table = 'venta'
        db_table_comment = "Ventas de todos los canales: web, tienda física y WhatsApp (HU-03, HU-06, HU-12, KPI-01)."

    @property
    def anulada(self):
        return self.anulada_en is not None

    @property
    def metodo_pago_texto(self):
        pago = getattr(self, 'pago_webpay', None)
        if pago is not None:
            return pago.metodo_pago_texto
        return self.get_metodo_pago_display()

    def calcular_total(self):
        self.subtotal = sum(
            producto_venta.total_producto for producto_venta in self.producto_venta.all()
        )
        if self.metodo_envio in OPCIONES_ENVIO:
            self.envio = costo_envio(self.metodo_envio, self.subtotal)
        self.total = self.subtotal + self.envio
        self.save()

    @property
    def envio_por_pagar(self):
        return self.metodo_envio == 'por_pagar'

    @property
    def es_retiro_en_tienda(self):
        return self.metodo_envio == 'tienda'

    @property
    def estados_envio(self):
        return estados_para(self.metodo_envio)

    @property
    def lleva_seguimiento(self):
        return lleva_seguimiento(self.metodo_envio)


# clase ProductoVenta: detalle de la venta, un producto una sola vez por venta
class ProductoVenta(models.Model):
    pk = models.CompositePrimaryKey('venta_id', 'producto_id')
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='producto_venta',
                              db_comment="Venta a la que pertenece el detalle (FK a venta). Parte de la clave primaria.")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT,
                                 db_comment="Producto vendido (FK a producto). Parte de la clave primaria.")
    cantidad = models.PositiveIntegerField(default=1, db_comment="Unidades vendidas.")
    precio_unitario = models.PositiveIntegerField(
        db_comment="Precio unitario cobrado, en pesos chilenos con IVA incluido (copia histórica).")
    costo_unitario = models.PositiveIntegerField(
        null=True, blank=True, help_text="Costo del producto al momento de la venta.",
        db_comment="Costo unitario del producto al vender, en pesos chilenos con IVA incluido. "
                   "NULL si el producto no tenía costo registrado (HU-10, reporte de ganancia).",
    )

    class Meta:
        db_table = 'detalle_venta'
        db_table_comment = "Productos de cada venta. Clave primaria compuesta (venta_id, producto_id)."

    def save(self, *args, **kwargs):
        if self._state.adding and self.costo_unitario is None:
            self.costo_unitario = self.producto.costo
        super().save(*args, **kwargs)

    @property
    def total_producto(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.producto.nombre} (Cantidad: {self.cantidad})"


# clase Opinion
class Opinion(models.Model):
    id = models.BigAutoField(primary_key=True, db_comment="Identificador de la opinión.")
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="opiniones",
                                db_comment="Cliente que opina (FK a usuario).")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="opiniones",
                                 db_comment="Producto comprado y recibido sobre el que opina (FK a producto, HU-04).")
    comentario = models.TextField(verbose_name="Comentario", db_comment="Texto de la reseña.")
    puntuacion = models.PositiveIntegerField(
        verbose_name="Puntuación",
        default=1,
        choices=[(i, str(i)) for i in range(1, 6)],
        db_comment="Puntuación en estrellas, de 1 a 5.",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación",
                                          db_comment="Fecha y hora de la reseña.")

    class Meta:
        db_table = 'opinion'
        db_table_comment = "Reseñas de productos comprados y recibidos (HU-04). Una por cliente y producto."
        verbose_name = "Opinión"
        verbose_name_plural = "Opiniones"
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'producto'], name='una_opinion_por_usuario_y_producto'),
            models.CheckConstraint(condition=Q(puntuacion__gte=1) & Q(puntuacion__lte=5),
                                   name='opinion_puntuacion_entre_1_y_5'),
        ]

    def __str__(self):
        return f"{self.usuario.nombre} - {self.producto.nombre} ({self.puntuacion} estrellas)"


# clase Reclamo
class Reclamo(models.Model):
    ESTADO_CHOICES = [
        ('Abierto', 'Abierto'),
        ('Respondido', 'Respondido'),
    ]
    CANALES = [
        ('web', 'Plataforma'),
        ('whatsapp', 'WhatsApp'),
        ('tienda', 'Tienda física'),
    ]
    id = models.BigAutoField(primary_key=True, db_comment="Identificador del reclamo.")
    # KPI-08: el admin registra también los reclamos recibidos por WhatsApp o en tienda,
    # que pueden venir de personas sin cuenta (se guardan su nombre y contacto)
    usuario = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, null=True, blank=True, related_name='reclamos',
        db_comment="Cliente que reclama (FK a usuario). NULL si el reclamo llegó por otro canal sin cuenta.",
    )
    canal = models.CharField(max_length=10, choices=CANALES, default='web',
                             db_comment="Canal por el que llegó el reclamo (KPI-08). Valores: web, whatsapp, tienda.")
    nombre_contacto = models.CharField(max_length=100, blank=True, verbose_name="Nombre de quien reclama",
                                       db_comment="Nombre de quien reclama cuando no tiene cuenta.")
    contacto = models.CharField(max_length=100, blank=True, verbose_name="Teléfono o correo de contacto",
                                db_comment="Teléfono o correo de quien reclama cuando no tiene cuenta.")
    venta = models.ForeignKey(Venta, on_delete=models.PROTECT, null=True, blank=True, related_name='reclamos',
                              db_comment="Venta reclamada (FK a venta). NULL si el reclamo no es sobre una venta.")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Abierto',
                              db_comment="Estado del reclamo. Valores: Abierto, Respondido.")
    asunto = models.CharField(max_length=255, default='No especificado', db_comment="Asunto del reclamo.")
    fecha = models.DateTimeField(default=now, db_comment="Fecha y hora en que se registró el reclamo.")
    descripcion = models.TextField(default='', verbose_name="Descripción", db_comment="Detalle del reclamo.")
    respuesta = models.TextField(blank=True, null=True, verbose_name="Respuesta del administrador",
                                 db_comment="Respuesta del administrador. NULL mientras está abierto.")
    fecha_respuesta = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de respuesta",
                                           db_comment="Fecha y hora de la respuesta. NULL mientras está abierto.")

    class Meta:
        db_table = 'reclamo'
        db_table_comment = "Reclamos de clientes recibidos por todos los canales (KPI-08)."

    def __str__(self):
        return f"Reclamo {self.id} - {self.asunto}"


# clase Devolucion
class Devolucion(models.Model):
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Aprobada', 'Aprobada'),
        ('Rechazada', 'Rechazada'),
    ]
    MAXIMO_IMAGENES = 3

    id = models.BigAutoField(primary_key=True, db_comment="Identificador y número de la solicitud de devolución.")
    venta = models.ForeignKey(Venta, on_delete=models.PROTECT, related_name='devoluciones',
                              db_comment="Venta en la que se compró el producto (FK a venta).")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT,
                                 db_comment="Producto que se devuelve (FK a producto).")
    cantidad = models.PositiveIntegerField(default=1, db_comment="Unidades que se devuelven.")
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT,
                                db_comment="Cliente que solicita la devolución (FK a usuario).")

    fecha_solicitud = models.DateTimeField(auto_now_add=True, db_comment="Fecha y hora de la solicitud.")
    motivo = models.TextField(verbose_name="Motivo de la devolución", db_comment="Motivo que indica el cliente.")

    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Pendiente',
                              db_comment="Estado de la solicitud. Valores: Pendiente, Aprobada, Rechazada.")
    respuesta_admin = models.TextField(blank=True, null=True, verbose_name="Respuesta del administrador",
                                       db_comment="Respuesta del administrador al cliente. NULL mientras está pendiente.")
    fecha_resolucion = models.DateTimeField(null=True, blank=True,
                                            db_comment="Fecha y hora en que se aprobó o rechazó. NULL si está pendiente.")
    monto_reembolso = models.PositiveIntegerField(
        null=True, blank=True,
        db_comment="Monto reembolsado al cliente, en pesos chilenos con IVA incluido. NULL si no se ha reembolsado.",
    )
    fecha_reembolso = models.DateTimeField(null=True, blank=True,
                                           db_comment="Fecha y hora del reembolso. NULL si no se ha reembolsado.")

    class Meta:
        db_table = 'devolucion'
        db_table_comment = "Solicitudes de devolución de productos de una venta (derecho a retracto y garantía)."

    def __str__(self):
        return f"Devolución {self.id} - {self.usuario.nombre}"

    def aprobar(self):
        self.estado = 'Aprobada'
        self.fecha_resolucion = now()
        self.save()

    def rechazar(self):
        self.estado = 'Rechazada'
        self.fecha_resolucion = now()
        self.save()


# clase ImagenDevolucion: fotos de evidencia de una devolución (hasta 3, límite del formulario)
class ImagenDevolucion(models.Model):
    id = models.BigAutoField(primary_key=True, db_comment="Identificador de la imagen.")
    devolucion = models.ForeignKey(Devolucion, on_delete=models.CASCADE, related_name='imagenes',
                                   db_comment="Devolución a la que pertenece la foto (FK a devolucion).")
    imagen = models.ImageField(upload_to='devoluciones/',
                               db_comment="Ruta del archivo dentro de media/ (carpeta devoluciones/).")

    class Meta:
        db_table = 'imagen_devolucion'
        db_table_comment = "Fotos de evidencia que el cliente adjunta a una devolución."
        ordering = ['id']

    def __str__(self):
        return f"Imagen de la devolución {self.devolucion_id}"


# clase Envio
class Envio(models.Model):
    ESTADO_CHOICES = [
        ('En Preparación', 'En Preparación'),
        ('Enviado', 'Enviado'),
        ('En Tránsito', 'En Tránsito'),
        ("En Reparto", "En Reparto"),
        ('Listo para retiro', 'Listo para retiro'),
        ('Entregado', 'Entregado'),
        ("Anulada", "Anulada"),
    ]
    CLASES_ESTADO = {
        'En Preparación': 'estado-preparacion',
        'Enviado': 'estado-enviado',
        'En Tránsito': 'estado-transito',
        'En Reparto': 'estado-reparto',
        'Listo para retiro': 'estado-listo-retiro',
        'Entregado': 'estado-entregado',
        'Anulada': 'estado-anulada',
    }
    FECHAS_ESTADO = {
        'En Preparación': 'fecha_preparacion',
        'Enviado': 'fecha_envio',
        'En Tránsito': 'fecha_transito',
        'En Reparto': 'fecha_reparto',
        'Listo para retiro': 'fecha_listo_retiro',
        'Entregado': 'fecha_entrega',
    }

    id = models.BigAutoField(primary_key=True, db_comment="Identificador del envío.")
    venta = models.OneToOneField(Venta, on_delete=models.CASCADE, related_name='datos_envio',
                                 db_comment="Venta que se entrega (FK única a venta).")
    numero_seguimiento = models.CharField(max_length=50, blank=True, null=True,
                                          db_comment="Número de seguimiento del transportista. NULL si no aplica.")
    fecha_preparacion = models.DateTimeField(null=True, blank=True,
                                             db_comment="Fecha y hora en que pasó a En Preparación.")
    fecha_envio = models.DateTimeField(null=True, blank=True, db_comment="Fecha y hora en que pasó a Enviado.")
    fecha_transito = models.DateTimeField(null=True, blank=True, db_comment="Fecha y hora en que pasó a En Tránsito.")
    fecha_reparto = models.DateTimeField(null=True, blank=True, db_comment="Fecha y hora en que pasó a En Reparto.")
    fecha_listo_retiro = models.DateTimeField(null=True, blank=True, verbose_name="Listo para retiro desde",
                                              db_comment="Fecha y hora en que quedó listo para retiro en tienda.")
    fecha_entrega = models.DateTimeField(null=True, blank=True,
                                         db_comment="Fecha y hora de entrega o retiro.")
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default='En Preparación',
        db_comment="Estado actual (HU-08). Valores: En Preparación, Enviado, En Tránsito, En Reparto, "
                   "Listo para retiro, Entregado, Anulada.",
    )
    transportista = models.CharField(max_length=50, default='Starken',
                                     db_comment="Empresa o medio que realiza la entrega.")

    class Meta:
        db_table = 'envio'
        db_table_comment = "Retiro o despacho de cada venta web y su seguimiento (HU-08)."

    def __str__(self):
        return f"Envío #{self.id} para Venta {self.venta.id}"

    def guardar_estado(self, nuevo_estado):
        if nuevo_estado != self.estado and nuevo_estado in self.FECHAS_ESTADO:
            setattr(self, self.FECHAS_ESTADO[nuevo_estado], now())
        self.estado = nuevo_estado
        self.save()

    @property
    def clase_estado(self):
        return self.CLASES_ESTADO.get(self.estado, '')

    @property
    def estado_para_mostrar(self):
        """Un retiro en tienda entregado se muestra como "Retirado"."""
        if self.estado == 'Entregado' and self.venta.es_retiro_en_tienda:
            return 'Retirado'
        return self.estado

    def registrar_envio(self, tracking):
        self.numero_seguimiento = tracking
        self.estado = 'Enviado'
        self.fecha_envio = now()
        self.save()

    def actualizar_estado(self, nuevo_estado):
        self.estado = nuevo_estado
        self.save()


# clase Comprobante: comprobante de compra NO tributario (no reemplaza la boleta del SII)
class Comprobante(models.Model):
    id = models.BigAutoField(primary_key=True, db_comment="Identificador del comprobante.")
    venta = models.OneToOneField(Venta, on_delete=models.CASCADE, related_name='comprobante',
                                 db_comment="Venta que respalda el comprobante (FK única a venta).")
    fecha_emision = models.DateTimeField(auto_now_add=True, db_comment="Fecha y hora de emisión.")
    archivo_pdf = models.FileField(upload_to='comprobantes/', null=True, blank=True,
                                   db_comment="Ruta del PDF dentro de media/ (carpeta comprobantes/). NULL si no se generó.")

    class Meta:
        db_table = 'comprobante'
        db_table_comment = "Comprobante de compra no tributario que la plataforma emite por cada venta (HU-06)."

    def __str__(self):
        return f"Comprobante #{self.id} - Venta {self.venta.id}"


# clase PagoWebpay
class PagoWebpay(models.Model):
    PENDIENTE = 'pendiente'
    APROBADO = 'aprobado'
    RECHAZADO = 'rechazado'
    ANULADO = 'anulado'
    REEMBOLSADO = 'reembolsado'
    ERROR = 'error'
    ESTADOS = [
        (PENDIENTE, 'Pendiente'),
        (APROBADO, 'Aprobado'),
        (RECHAZADO, 'Rechazado'),
        (ANULADO, 'Anulado por el cliente'),
        (REEMBOLSADO, 'Reembolsado (sin stock)'),
        (ERROR, 'Error'),
    ]
    TIPOS_PAGO = {
        'VD': 'Débito',
        'VP': 'Prepago',
        'VN': 'Crédito',
        'VC': 'Crédito en cuotas',
        'SI': '3 cuotas sin interés',
        'S2': '2 cuotas sin interés',
        'NC': 'Cuotas sin interés',
    }

    id = models.BigAutoField(primary_key=True, db_comment="Identificador del intento de pago.")
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='pagos_webpay',
                                db_comment="Cliente que paga (FK a usuario).")
    venta = models.OneToOneField(Venta, on_delete=models.PROTECT, null=True, blank=True, related_name='pago_webpay',
                                 db_comment="Venta creada al aprobarse el pago (FK única a venta). NULL si no se aprobó.")
    carrito = models.ForeignKey(Carrito, on_delete=models.SET_NULL, null=True, blank=True, related_name='pagos_webpay',
                                db_comment="Carrito que se está pagando (FK a carrito, KPI-04).")
    orden_compra = models.CharField(max_length=26, unique=True,
                                    db_comment="Orden de compra (buy_order) enviada a Transbank.")
    token = models.CharField(max_length=64, unique=True, null=True, blank=True,
                             db_comment="Token de la transacción entregado por Transbank. NULL si no se pudo iniciar.")
    monto = models.PositiveIntegerField(db_comment="Monto cobrado, en pesos chilenos con IVA incluido.")
    estado = models.CharField(
        max_length=12, choices=ESTADOS, default=PENDIENTE,
        db_comment="Estado del pago (HU-05). Valores: pendiente, aprobado, rechazado, anulado, reembolsado, error.",
    )
    detalle = models.CharField(max_length=255, blank=True, help_text="Motivo del estado, para el cliente y el panel.",
                               db_comment="Motivo del estado, para el cliente y el panel.")

    metodo_envio = models.CharField(
        max_length=10, choices=Venta.ENVIO_CHOICES,
        db_comment="Forma de entrega elegida al pagar. Valores: tienda, delivery, bluexpress, por_pagar, domicilio.",
    )
    direccion_envio = models.TextField(blank=True, db_comment="Dirección de entrega elegida al pagar.")

    codigo_autorizacion = models.CharField(max_length=10, blank=True,
                                           db_comment="Código de autorización entregado por Transbank.")
    tipo_pago = models.CharField(
        max_length=2, blank=True,
        db_comment="Tipo de pago de Transbank. Valores: VD, VP, VN, VC, SI, S2, NC.",
    )
    cuotas = models.PositiveSmallIntegerField(null=True, blank=True,
                                              db_comment="Número de cuotas. NULL si el pago no fue en cuotas.")
    tarjeta_ultimos_digitos = models.CharField(max_length=4, blank=True,
                                               db_comment="Últimos 4 dígitos de la tarjeta.")
    fecha_transaccion = models.DateTimeField(null=True, blank=True,
                                             db_comment="Fecha y hora de la transacción informada por Transbank.")
    respuesta = models.JSONField(null=True, blank=True, help_text="Respuesta completa de Transbank (auditoría).",
                                 db_comment="Respuesta completa de Transbank, guardada sin procesar solo para auditoría.")

    creado = models.DateTimeField(auto_now_add=True, db_comment="Fecha y hora en que se inició el pago.")
    actualizado = models.DateTimeField(auto_now=True, db_comment="Fecha y hora del último cambio de estado.")

    class Meta:
        db_table = 'pago_webpay'
        db_table_comment = "Intentos de pago con Webpay Plus de Transbank (HU-05)."
        ordering = ['-creado']
        verbose_name = "Pago Webpay"
        verbose_name_plural = "Pagos Webpay"

    def __str__(self):
        return f"{self.orden_compra} ({self.get_estado_display()})"

    @property
    def tipo_pago_display(self):
        return self.TIPOS_PAGO.get(self.tipo_pago, self.tipo_pago)

    @property
    def metodo_pago_texto(self):
        return f"Webpay - {self.tipo_pago_display}" if self.tipo_pago else "Webpay"

    def guardar_respuesta(self, respuesta):
        self.respuesta = respuesta
        self.codigo_autorizacion = respuesta.get('authorization_code') or ''
        self.tipo_pago = respuesta.get('payment_type_code') or ''
        self.cuotas = respuesta.get('installments_number') or None
        self.tarjeta_ultimos_digitos = ((respuesta.get('card_detail') or {}).get('card_number') or '')[-4:]
        fecha = respuesta.get('transaction_date')
        self.fecha_transaccion = parse_datetime(fecha) if fecha else None


# clase DetallePagoWebpay: productos que cubre el pago, fijados al iniciarlo (el carrito puede cambiar mientras paga)
class DetallePagoWebpay(models.Model):
    pk = models.CompositePrimaryKey('pago_id', 'producto_id')
    pago = models.ForeignKey(PagoWebpay, on_delete=models.CASCADE, related_name='detalles',
                             db_comment="Pago al que pertenece el detalle (FK a pago_webpay). Parte de la clave primaria.")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT,
                                 db_comment="Producto que se paga (FK a producto). Parte de la clave primaria.")
    cantidad = models.PositiveIntegerField(db_comment="Unidades que se pagan.")
    precio_unitario = models.PositiveIntegerField(
        db_comment="Precio unitario al iniciar el pago, en pesos chilenos con IVA incluido.")

    class Meta:
        db_table = 'detalle_pago_webpay'
        db_table_comment = "Productos de cada pago Webpay. Clave primaria compuesta (pago_id, producto_id)."


# clase Favorito
class Favorito(models.Model):
    pk = models.CompositePrimaryKey('usuario_id', 'producto_id')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE,
                                db_comment="Cliente (FK a usuario). Parte de la clave primaria.")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE,
                                 db_comment="Producto guardado como favorito (FK a producto). Parte de la clave primaria.")

    class Meta:
        db_table = 'favorito'
        db_table_comment = "Productos favoritos de cada cliente. Clave primaria compuesta (usuario_id, producto_id)."

    def __str__(self):
        return f"{self.usuario} - {self.producto}"


# clase Destacado
class Destacado(models.Model):
    SECCION_CARRUSEL = 'carrusel'
    SECCION_LANZAMIENTOS = 'lanzamientos'
    SECCIONES = [
        (SECCION_CARRUSEL, 'Carrusel del menú'),
        (SECCION_LANZAMIENTOS, 'Nuevos lanzamientos (home)'),
        ('menu_videojuegos', 'Navbar: menú Videojuegos'),
        ('menu_consolas', 'Navbar: menú Consolas'),
        ('menu_accesorios', 'Navbar: menú Accesorios'),
        ('menu_figuras', 'Navbar: menú Figuras'),
    ]
    SECCIONES_DE_UNO = ['menu_videojuegos', 'menu_consolas', 'menu_accesorios', 'menu_figuras']
    MAXIMO_VISIBLES = {SECCION_CARRUSEL: 8, SECCION_LANZAMIENTOS: 4}
    id = models.BigAutoField(primary_key=True, db_comment="Identificador del destacado.")
    seccion = models.CharField(
        max_length=20, choices=SECCIONES, verbose_name="Sección",
        db_comment="Lugar del sitio donde se muestra (HU-09). Valores: carrusel, lanzamientos, menu_videojuegos, "
                   "menu_consolas, menu_accesorios, menu_figuras.",
    )
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True,
                                 db_comment="Producto al que enlaza (FK a producto). NULL si no enlaza a uno.")
    titulo = models.CharField(max_length=80, verbose_name="Título", db_comment="Título que se muestra.")
    texto = models.TextField(blank=True, max_length=400, db_comment="Texto descriptivo, hasta 400 caracteres.")
    imagen = models.ImageField(upload_to='destacados/', blank=True, null=True,
                               help_text="Opcional: si no se sube, se usa la imagen del producto.",
                               db_comment="Ruta de la imagen propia dentro de media/. NULL para usar la del producto.")
    etiqueta = models.CharField(max_length=20, blank=True, help_text="Texto corto sobre la imagen, ej: ¡NUEVO!",
                                db_comment="Texto corto sobre la imagen (ej. ¡NUEVO!).")
    video_url = models.URLField(blank=True, verbose_name="Video de YouTube",
                                help_text="Solo para nuevos lanzamientos. Ej: https://www.youtube.com/watch?v=...",
                                db_comment="Enlace a un video de YouTube, solo para nuevos lanzamientos.")
    orden = models.PositiveIntegerField(default=0, help_text="Los números menores se muestran primero.",
                                        db_comment="Orden dentro de la sección; los menores se muestran primero.")
    activo = models.BooleanField(default=True, help_text="Si se desactiva, deja de mostrarse en el sitio.",
                                 db_comment="Indica si se muestra en el sitio (HU-09).")

    class Meta:
        db_table = 'destacado'
        db_table_comment = "Contenido de portada que edita el administrador: carrusel, lanzamientos y promociones del navbar (HU-09)."
        ordering = ['seccion', 'orden', 'id']

    def __str__(self):
        return f"{self.get_seccion_display()}: {self.titulo}"

    def supera_maximo_visibles(self):
        maximo = self.MAXIMO_VISIBLES.get(self.seccion)
        if maximo is None:
            return False
        otros = Destacado.objects.filter(seccion=self.seccion, activo=True).exclude(pk=self.pk)
        return otros.count() >= maximo

    @property
    def imagen_url(self):
        if self.imagen:
            return self.imagen.url
        if self.producto and self.producto.imagen_principal:
            return self.producto.imagen_principal.url
        return ''

    @property
    def producto_disponible(self):
        if self.producto and not self.producto.is_deleted:
            return self.producto
        return None

    @property
    def video_embed_url(self):
        return youtube_embed_url(self.video_url)


def youtube_embed_url(url):
    m = re.search(r'(?:youtube\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})', url or '')
    return f"https://www.youtube-nocookie.com/embed/{m.group(1)}" if m else ''


# clase ConfiguracionSitio: opciones de visualización de la tienda que el admin cambia desde el panel
class ConfiguracionSitio(models.Model):
    RELACIONADOS_CATEGORIA = 'categoria'
    RELACIONADOS_ALEATORIOS = 'aleatorios'
    RELACIONADOS_NINGUNO = 'ninguno'
    OPCIONES_RELACIONADOS = [
        (RELACIONADOS_CATEGORIA, 'De la misma categoría'),
        (RELACIONADOS_ALEATORIOS, 'Aleatorios de toda la tienda'),
        (RELACIONADOS_NINGUNO, 'No mostrar'),
    ]

    id = models.BigAutoField(primary_key=True, db_comment="Identificador. La tabla tiene un único registro con id 1.")
    productos_relacionados = models.CharField(
        max_length=12, choices=OPCIONES_RELACIONADOS, default=RELACIONADOS_CATEGORIA,
        verbose_name="Productos relacionados en la ficha",
        db_comment="Qué productos relacionados muestra la ficha (HU-09). Valores: categoria, aleatorios, ninguno.",
    )
    mostrar_opiniones = models.BooleanField(default=True, verbose_name="Mostrar opiniones en la ficha",
                                            db_comment="Indica si la ficha muestra las reseñas (HU-09).")
    mostrar_etiquetas = models.BooleanField(default=True, verbose_name='Mostrar etiquetas "Nuevo" y "¡Últimos!"',
                                            db_comment="Indica si se muestran las etiquetas Nuevo y Últimos (HU-09).")
    mostrar_stock = models.BooleanField(default=True, verbose_name="Mostrar el stock disponible en la ficha",
                                        db_comment="Indica si la ficha muestra el stock disponible (HU-09).")
    # HU-07: se habilita cuando el catálogo tiene sus atributos completos (KPI-10)
    mostrar_recomendaciones = models.BooleanField(
        default=False, verbose_name="Mostrar recomendaciones personalizadas",
        db_comment="Indica si se muestran recomendaciones personalizadas (HU-07). Se habilita con KPI-10 cumplido.",
    )
    actualizado = models.DateTimeField(auto_now=True, db_comment="Fecha y hora del último cambio.")

    class Meta:
        db_table = 'configuracion_sitio'
        db_table_comment = "Opciones de visualización de la tienda que el administrador activa o desactiva (HU-09)."
        verbose_name = "Configuración del sitio"
        verbose_name_plural = "Configuración del sitio"

    def __str__(self):
        return "Configuración del sitio"

    @classmethod
    def actual(cls):
        """La configuración es un único registro; si no existe se crea con los valores por defecto."""
        configuracion, _ = cls.objects.get_or_create(pk=1)
        return configuracion

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


# clase Proveedor: a quién le compra mercadería la tienda (reporte de compras, HU-10)
class Proveedor(models.Model):
    id = models.BigAutoField(primary_key=True, db_comment="Identificador del proveedor.")
    nombre = models.CharField(max_length=100, db_comment="Nombre o razón social del proveedor.")
    rut = models.CharField(max_length=12, unique=True, null=True, blank=True,
                           db_comment="RUT del proveedor con puntos y guion. NULL si no se registró.")
    telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono", db_comment="Teléfono de contacto.")
    email = models.EmailField(blank=True, db_comment="Correo de contacto.")

    class Meta:
        db_table = 'proveedor'
        db_table_comment = "Proveedores a los que la tienda compra mercadería (HU-10)."
        ordering = ['nombre']
        verbose_name_plural = "Proveedores"

    def save(self, *args, **kwargs):
        if not self.rut:
            self.rut = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


# clase Compra: ingreso de mercadería al inventario (HU-10). El stock sube al marcarla como recibida.
class Compra(models.Model):
    PENDIENTE = 'pendiente'
    RECIBIDA = 'recibida'
    ESTADOS = [
        (PENDIENTE, 'Pendiente'),
        (RECIBIDA, 'Recibida'),
    ]
    id = models.BigAutoField(primary_key=True, db_comment="Identificador de la compra.")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='compras',
                                  db_comment="Proveedor al que se compró (FK a proveedor).")
    numero_documento = models.CharField(max_length=30, blank=True, verbose_name="N.º de factura o documento",
                                        db_comment="Número de la factura o documento del proveedor.")
    fecha = models.DateField(default=localdate, db_index=True, db_comment="Fecha de la compra.")
    total = models.PositiveIntegerField(default=0, help_text="Total con IVA.",
                                        db_comment="Total de la compra, en pesos chilenos con IVA incluido.")
    estado = models.CharField(max_length=10, choices=ESTADOS, default=PENDIENTE,
                              db_comment="Estado de la compra (HU-10). Valores: pendiente, recibida.")
    fecha_recepcion = models.DateTimeField(
        null=True, blank=True,
        db_comment="Fecha y hora en que se recibió la mercadería y se sumó al stock. NULL si está pendiente.",
    )
    creado = models.DateTimeField(auto_now_add=True, db_comment="Fecha y hora en que se registró la compra.")

    class Meta:
        db_table = 'compra'
        db_table_comment = "Compras de mercadería a proveedores (HU-10, reporte de compras)."
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f"Compra #{self.id} - {self.proveedor}"

    def calcular_total(self):
        self.total = sum(detalle.total_producto for detalle in self.detalles.all())
        self.save(update_fields=['total'])

    def marcar_recibida(self):
        """Suma al stock lo comprado y deja la compra como recibida. Devuelve False si ya lo estaba."""
        with transaction.atomic():
            compra = Compra.objects.select_for_update().get(pk=self.pk)
            if compra.estado == self.RECIBIDA:
                return False
            for detalle in compra.detalles.all():
                Producto.todos.filter(pk=detalle.producto_id).update(stock=F('stock') + detalle.cantidad)
            compra.estado = self.RECIBIDA
            compra.fecha_recepcion = now()
            compra.save(update_fields=['estado', 'fecha_recepcion'])
        self.estado, self.fecha_recepcion = compra.estado, compra.fecha_recepcion
        return True


# clase DetalleCompra
class DetalleCompra(models.Model):
    pk = models.CompositePrimaryKey('compra_id', 'producto_id')
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='detalles',
                               db_comment="Compra a la que pertenece el detalle (FK a compra). Parte de la clave primaria.")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='compras',
                                 db_comment="Producto comprado (FK a producto). Parte de la clave primaria.")
    cantidad = models.PositiveIntegerField(default=1, db_comment="Unidades compradas.")
    costo_unitario = models.PositiveIntegerField(help_text="Costo unitario con IVA.",
                                                 db_comment="Costo unitario pagado, en pesos chilenos con IVA incluido.")

    class Meta:
        db_table = 'detalle_compra'
        db_table_comment = "Productos de cada compra a proveedor. Clave primaria compuesta (compra_id, producto_id)."

    @property
    def total_producto(self):
        return self.cantidad * self.costo_unitario

    def __str__(self):
        return f"{self.producto.nombre} (Cantidad: {self.cantidad})"


# clase MovimientoCaja: dinero que se saca o ingresa a la caja de la tienda física (reportes de caja y retiros, HU-10)
class MovimientoCaja(models.Model):
    RETIRO = 'retiro'
    INGRESO = 'ingreso'
    TIPOS = [
        (RETIRO, 'Retiro de dinero'),
        (INGRESO, 'Ingreso de dinero'),
    ]
    id = models.BigAutoField(primary_key=True, db_comment="Identificador del movimiento.")
    tipo = models.CharField(max_length=10, choices=TIPOS,
                            db_comment="Tipo de movimiento (HU-10). Valores: retiro, ingreso.")
    monto = models.PositiveIntegerField(db_comment="Monto del movimiento, en pesos chilenos.")
    motivo = models.CharField(max_length=255, db_comment="Motivo del movimiento.")
    fecha = models.DateTimeField(default=now, db_index=True, db_comment="Fecha y hora del movimiento.")

    class Meta:
        db_table = 'movimiento_caja'
        db_table_comment = "Retiros e ingresos de dinero de la caja de la tienda física (HU-10, reportes de caja)."
        ordering = ['-fecha']
        verbose_name = "Movimiento de caja"
        verbose_name_plural = "Movimientos de caja"

    def __str__(self):
        return f"{self.get_tipo_display()} de ${self.monto}"


# clase InteraccionProducto: navegación del cliente que alimenta las recomendaciones (HU-07).
# Solo se registra si el cliente autorizó el uso de sus datos de navegación.
class InteraccionProducto(models.Model):
    VISTA = 'vista'
    CARRITO = 'carrito'
    TIPOS = [
        (VISTA, 'Vio la ficha del producto'),
        (CARRITO, 'Agregó el producto al carrito'),
    ]
    id = models.BigAutoField(primary_key=True, db_comment="Identificador de la interacción.")
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='interacciones',
                                db_comment="Cliente que interactuó (FK a usuario).")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='interacciones',
                                 db_comment="Producto con el que interactuó (FK a producto).")
    tipo = models.CharField(max_length=10, choices=TIPOS,
                            db_comment="Tipo de interacción. Valores: vista, carrito.")
    fecha = models.DateTimeField(auto_now_add=True, db_comment="Fecha y hora de la interacción.")

    class Meta:
        db_table = 'interaccion_producto'
        db_table_comment = "Navegación de clientes que autorizaron su uso, para personalizar las recomendaciones (HU-07)."
        indexes = [models.Index(fields=['usuario', 'fecha'], name='interaccion_usuario_fecha')]
        verbose_name = "Interacción con producto"
        verbose_name_plural = "Interacciones con productos"

    def __str__(self):
        return f"{self.usuario} - {self.producto} ({self.tipo})"


# clase SimilitudProducto: resultado del filtrado basado en contenido (HU-07). Se guardan los 10 productos
# más similares a cada producto, según TF-IDF y similitud del coseno sobre categoría, plataforma y género.
class SimilitudProducto(models.Model):
    pk = models.CompositePrimaryKey('producto_id', 'producto_similar_id')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='similitudes',
                                 db_comment="Producto de referencia (FK a producto). Parte de la clave primaria.")
    producto_similar = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='+',
                                         db_comment="Producto similar al de referencia (FK a producto). Parte de la clave primaria.")
    puntaje = models.DecimalField(max_digits=5, decimal_places=4,
                                  db_comment="Similitud del coseno entre ambos productos, de 0 a 1.")
    fecha_calculo = models.DateTimeField(db_comment="Fecha y hora en que se calculó la similitud.")

    class Meta:
        db_table = 'similitud_producto'
        db_table_comment = ("Los 10 productos más similares a cada producto, calculados con TF-IDF y similitud "
                            "del coseno (HU-07). Clave primaria compuesta (producto_id, producto_similar_id).")
        constraints = [
            models.CheckConstraint(condition=Q(puntaje__gte=0) & Q(puntaje__lte=1),
                                   name='similitud_puntaje_entre_0_y_1'),
            models.CheckConstraint(condition=~Q(producto=F('producto_similar')),
                                   name='similitud_productos_distintos'),
        ]

    def __str__(self):
        return f"{self.producto_id} ~ {self.producto_similar_id} ({self.puntaje})"


# clase Recomendacion: cada producto recomendado que se le mostró a un cliente y si hizo clic (KPI-05)
class Recomendacion(models.Model):
    UBICACIONES = [
        ('home', 'Página principal'),
        ('ficha', 'Ficha de producto'),
    ]
    id = models.BigAutoField(primary_key=True, db_comment="Identificador de la recomendación mostrada.")
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='recomendaciones',
                                db_comment="Cliente al que se le mostró (FK a usuario).")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='recomendaciones',
                                 db_comment="Producto recomendado (FK a producto).")
    ubicacion = models.CharField(max_length=10, choices=UBICACIONES, verbose_name="Ubicación",
                                 db_comment="Página donde se mostró (HU-07). Valores: home, ficha.")
    posicion = models.PositiveSmallIntegerField(default=1, verbose_name="Posición",
                                                db_comment="Posición dentro de la lista de recomendaciones, desde 1.")
    mostrada_en = models.DateTimeField(auto_now_add=True, db_index=True,
                                       db_comment="Fecha y hora en que se mostró (denominador de KPI-05).")
    clic_en = models.DateTimeField(null=True, blank=True,
                                   db_comment="Fecha y hora del clic. NULL si no hizo clic (numerador de KPI-05).")

    class Meta:
        db_table = 'recomendacion'
        db_table_comment = "Recomendaciones mostradas a cada cliente y sus clics (KPI-05)."
        verbose_name = "Recomendación"
        verbose_name_plural = "Recomendaciones"

    def __str__(self):
        return f"{self.producto} para {self.usuario} ({self.get_ubicacion_display()})"
