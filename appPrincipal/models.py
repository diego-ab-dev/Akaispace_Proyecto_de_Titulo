import re

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.timezone import now


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
# Usa el sistema de autenticación de Django. Inicia sesión con el email (no hay username).
# is_staff indica si es administrador del panel. Hereda de AbstractUser: password,
# is_active, is_staff, is_superuser, last_login, date_joined, grupos y permisos.
class Usuario(AbstractUser):
    username = None
    first_name = None
    last_name = None

    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    rut = models.CharField(max_length=12, unique=True, null=True, blank=True)
    telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    direccion = models.CharField(max_length=120, blank=True, verbose_name="Dirección")
    region = models.CharField(max_length=100, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre']

    objects = UsuarioManager()

    def save(self, *args, **kwargs):
        # el email se guarda en minúsculas para que el login no distinga mayúsculas
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    # eliminación lógica: el usuario ya no puede iniciar sesión, pero se conservan sus compras
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

# borrado lógico de productos
class ProductoQuerySet(models.QuerySet):
    def delete(self):
        # Producto.objects.filter(...).delete() también es lógico (incluye la acción masiva de /admin/)
        return self.update(is_deleted=True, deleted_at=now())

    def hard_delete(self):
        return super().delete()


class ProductoManager(models.Manager.from_queryset(ProductoQuerySet)):
    # Producto.objects solo devuelve productos no eliminados
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


# clase Producto
class Producto(models.Model):
    CATEGORIAS = [
        ('VIDEOJUEGOS', [
            ('Videojuegos PS3', 'PlayStation 3'),
            ('Videojuegos PS4', 'PlayStation 4'),
            ('Videojuegos PS5', 'PlayStation 5'),
            ('Videojuegos XBOX 360', 'Xbox 360'),
            ('Videojuegos XBOX ONE', 'Xbox One'),
            ('Videojuegos XBOX SERIES', 'Xbox Series'),
            ('Videojuegos Nintendo 3DS', 'Nintendo 3DS'),
            ('Videojuegos WII', 'Nintendo Wii'),
            ('Videojuegos WII U', 'Nintendo Wii U'),
            ('Videojuegos Nintendo SWITCH', 'Nintendo Switch'),
            ('Videojuegos para PC', 'PC'),
        ]),
        ('CONSOLAS', [
            ('Ps4 Consolas', 'Consola PlayStation 4'),
            ('Ps5 Consolas', 'Consola PlayStation 5'),
            ('Xbox One Consolas', 'Consola Xbox One'),
            ('Xbox Series Consolas', 'Consola Xbox Series'),
            ('Wii U Consolas', 'Consola Wii U'),
            ('Switch Consolas', 'Consola Switch'),
        ]),
        ('ACCESORIOS', [
            ('Accesorios Psp', 'PSP'),
            ('Accesorios Ps Vita', 'PlayStation Vita'),
            ('Accesorios PS1', 'PlayStation 1'),
            ('Accesorios PS2', 'PlayStation 2'),
            ('Accesorios PS3', 'PlayStation 3'),
            ('Accesorios PS4', 'PlayStation 4'),
            ('Accesorios PS5', 'PlayStation 5'),
            ('Accesorios XBOX 360', 'Xbox 360'),
            ('Accesorios XBOX ONE', 'Xbox One'),
            ('Accesorios XBOX SERIES', 'Xbox Series'),
            ('Accesorios Nintendo 3DS', 'Nintendo 3DS'),
            ('Accesorios WII U', 'Wii U'),
            ('Accesorios Nintendo SWITCH', 'Switch'),
        ]),
        ('FIGURAS', [
            ('Figuras Funko', 'Funko Pop'),
            ('Figuras Amiibo', 'Amiibo'),
        ]),
    ]

    GENEROS = [
        ('ACCION', 'Acción'),
        ('AVENTURA', 'Aventura'),
        ('RPG', 'RPG'),
        ('DEPORTES', 'Deportes'),
        ('CARRERAS', 'Carreras'),
        ('ESTRATEGIA', 'Estrategia'),
        ('SIMULACION', 'Simulación'),
        ('PUZZLE', 'Puzzle'),
        ('TERROR', 'Terror'),
        ('CONSOLAS', 'Consolas'),
        ('FIGURAS', 'Figuras'),
        ('ACCESORIOS', 'Accesorios'),
        ('OTRO', 'Otro'),
    ]
    codigo_de_barra = models.CharField(max_length=20, verbose_name="Código de Barra")
    nombre = models.CharField(max_length=100)
    precio = models.PositiveIntegerField(default=0)  
    stock = models.PositiveIntegerField(default=0)  
    descripcion = models.TextField(blank=True, null=True, default='', verbose_name="Descripción")
    imagen_principal = models.ImageField(upload_to='productos/', verbose_name="Imagen Principal", default='') 
    imagen_2 = models.ImageField(upload_to='productos/', blank=True, null=True, verbose_name="Imagen Opcional 2")
    imagen_3 = models.ImageField(upload_to='productos/', blank=True, null=True, verbose_name="Imagen Opcional 3")
    imagen_4 = models.ImageField(upload_to='productos/', blank=True, null=True, verbose_name="Imagen Opcional 4")
    imagen_5 = models.ImageField(upload_to='productos/', blank=True, null=True, verbose_name="Imagen Opcional 5")
    imagen_6 = models.ImageField(upload_to='productos/', blank=True, null=True, verbose_name="Imagen Opcional 6")
    categoria = models.CharField(max_length=40, choices=CATEGORIAS, verbose_name="Categoría") 
    genero = models.CharField(max_length=20, choices=GENEROS, verbose_name="Género", default='OTRO')
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # objects: solo productos activos. todos: incluye los eliminados (historial, admin).
    # Al acceder a un producto desde una relación (ej: producto_venta.producto) Django
    # usa un manager sin filtro, así que el historial sigue mostrando productos eliminados.
    objects = ProductoManager()
    todos = ProductoQuerySet.as_manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.deleted_at = now()
        self.save()

    def hard_delete(self):
        super().delete()

    def imagenes(self):
        return [img for img in [
            self.imagen_principal, self.imagen_2, self.imagen_3, 
            self.imagen_4, self.imagen_5, self.imagen_6] if img]

    def promedio_puntuacion(self):
        opiniones = self.opiniones.all()
        if not opiniones:
            return 0
        return round(sum(opinion.puntuacion for opinion in opiniones) / len(opiniones), 1)

# clase Carrito
class Carrito(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='carrito')

    def total_carrito(self):
        return sum(
            (item.producto.precio or 0) * max(item.cantidad, 0) for item in self.items.all()
        )

# clase de ItemCarritoProducto
class ItemCarritoProducto(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['carrito', 'producto'], name='item_carrito_unico'),
        ]

# clase Venta
# El estado de la venta (preparación, enviado, entregado, anulada...) vive en Envio.estado.
class Venta(models.Model):
    ENVIO_CHOICES = [
        ('domicilio', 'Envío a domicilio'),
        ('tienda', 'Retiro en tienda'),
    ]
    # PROTECT: un usuario con compras no se puede borrar de verdad (solo borrado lógico)
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='ventas')
    envio = models.PositiveIntegerField(default=0)
    subtotal = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    metodo_pago = models.CharField(max_length=30, null=True, blank=True) 
    fecha = models.DateTimeField(auto_now_add=True)
    metodo_envio = models.CharField(max_length=10, choices=ENVIO_CHOICES, default='')
    direccion_envio = models.TextField(blank=True, null=True)

    def calcular_total(self):
        self.subtotal = sum(
            producto_venta.total_producto for producto_venta in self.producto_venta.all()
        )
        self.envio = 5990 if self.metodo_envio == 'domicilio' else 0
        self.total = self.subtotal + self.envio
        self.save()

# clase ProductoVenta
class ProductoVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='producto_venta')
    # PROTECT: un producto vendido no se puede borrar de verdad (solo borrado lógico)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.PositiveIntegerField() 

    @property
    def total_producto(self):
        return self.cantidad * self.precio_unitario
    
    def __str__(self):
        return f"{self.producto.nombre} (Cantidad: {self.cantidad})"

# clase Opinion
class Opinion(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="opiniones")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="opiniones")
    comentario = models.TextField(verbose_name="Comentario")
    puntuacion = models.PositiveIntegerField(
        verbose_name="Puntuación",
        default=1,
        choices=[(i, str(i)) for i in range(1, 6)] 
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")

    class Meta:
        unique_together = ('usuario', 'producto')  
        verbose_name = "Opinión"
        verbose_name_plural = "Opiniones"

    def __str__(self):
        return f"{self.usuario.nombre} - {self.producto.nombre} ({self.puntuacion} estrellas)"

# clase Reclamo
class Reclamo(models.Model):
    ESTADO_CHOICES = [
        ('Abierto', 'Abierto'),
        ('Respondido', 'Respondido'),
    ]
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='reclamos')
    venta = models.ForeignKey(Venta, on_delete=models.PROTECT, null=True, blank=True, related_name='reclamos')
    estado = models.CharField(max_length=20,choices=ESTADO_CHOICES, default='Abierto')
    asunto = models.CharField(max_length=255, default='No especificado')
    fecha = models.DateTimeField(default=now)
    descripcion = models.TextField(default='', verbose_name="Descripción")
    respuesta = models.TextField(blank=True, null=True, verbose_name="Respuesta del administrador")
    fecha_respuesta = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de respuesta")

    def __str__(self):
        return f"Reclamo {self.id} - {self.asunto}"

# clase Devolucion
class Devolucion(models.Model):
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Aprobada', 'Aprobada'),
        ('Rechazada', 'Rechazada'),
    ]
    venta = models.ForeignKey(Venta, on_delete=models.PROTECT, related_name='devoluciones', null=True, blank=True)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, null=True, blank=True)
    cantidad = models.PositiveIntegerField(default=1)
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    motivo = models.TextField(verbose_name="Motivo de la devolución")
    imagen1 = models.ImageField(upload_to='devoluciones/', blank=True, null=True)
    imagen2 = models.ImageField(upload_to='devoluciones/', blank=True, null=True)
    imagen3 = models.ImageField(upload_to='devoluciones/', blank=True, null=True)

    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Pendiente')
    respuesta_admin = models.TextField(blank=True, null=True, verbose_name="Respuesta del administrador")
    fecha_resolucion = models.DateTimeField(null=True, blank=True)

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

# clase Envio
class Envio(models.Model):
    ESTADO_CHOICES = [
        ('En Preparación', 'En Preparación'),
        ('Enviado', 'Enviado'),
        ('En Tránsito', 'En Tránsito'),
        ("En Reparto", "En Reparto"),
        ('Entregado', 'Entregado'),
        ("Anulada", "Anulada"),
    ]
    
    venta = models.OneToOneField(Venta, on_delete=models.CASCADE, related_name='datos_envio')
    numero_seguimiento = models.CharField(max_length=50, blank=True, null=True)
    fecha_preparacion = models.DateTimeField(null=True, blank=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    fecha_transito = models.DateTimeField(null=True, blank=True)
    fecha_reparto = models.DateTimeField(null=True, blank=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='En Preparación')
    transportista = models.CharField(max_length=50, default='Starken')

    def __str__(self):
        return f"Envío #{self.id} para Venta {self.venta.id}"
    
    def guardar_estado(self, nuevo_estado):
        self.estado = nuevo_estado
        
        if nuevo_estado == "En Preparación":
            self.fecha_preparacion = now()
        elif nuevo_estado == "Enviado":
            self.fecha_envio = now()
        elif nuevo_estado == "En Tránsito":
            self.fecha_transito = now()
        elif nuevo_estado == "En Reparto":
            self.fecha_reparto = now()
        elif nuevo_estado == "Entregado":
            self.fecha_entrega = now()

        self.save()

    def registrar_envio(self, tracking):
        self.numero_seguimiento = tracking
        self.estado = 'Enviado'
        self.fecha_envio = now()
        self.save()
        
    def actualizar_estado(self, nuevo_estado):
        self.estado = nuevo_estado
        self.save()

# clase Boleta
class Boleta(models.Model):
    venta = models.OneToOneField(Venta, on_delete=models.CASCADE, related_name='boleta')
    fecha_emision = models.DateTimeField(auto_now_add=True)
    archivo_pdf = models.FileField(upload_to='boletas/', null=True, blank=True)
    
    def __str__(self):
        return f"Boleta #{self.id} - Venta {self.venta.id}"

# clase Favorito
class Favorito(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'producto'], name='favorito_unico'),
        ]

    def __str__(self):
        return f"{self.usuario} - {self.producto}"

# clase Destacado
# Contenido de portada que el administrador edita desde su panel (HU-09): carrusel del menú,
# nuevos lanzamientos del home y la tarjeta promocional de cada menú del navbar.
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
    # en las secciones del navbar se muestra solo uno (el primero activo según el orden)
    SECCIONES_DE_UNO = ['menu_videojuegos', 'menu_consolas', 'menu_accesorios', 'menu_figuras']

    seccion = models.CharField(max_length=20, choices=SECCIONES, verbose_name="Sección")
    # SET_NULL: si el producto se borra de verdad, el destacado queda sin link en vez de desaparecer
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True)
    titulo = models.CharField(max_length=80, verbose_name="Título")
    texto = models.TextField(blank=True, max_length=400)
    imagen = models.ImageField(upload_to='destacados/', blank=True, null=True,
                               help_text="Opcional: si no se sube, se usa la imagen del producto.")
    etiqueta = models.CharField(max_length=20, blank=True, help_text="Texto corto sobre la imagen, ej: ¡NUEVO!")
    video_url = models.URLField(blank=True, verbose_name="Video de YouTube",
                                help_text="Solo para nuevos lanzamientos. Ej: https://www.youtube.com/watch?v=...")
    orden = models.PositiveIntegerField(default=0, help_text="Los números menores se muestran primero.")
    activo = models.BooleanField(default=True, help_text="Si se desactiva, deja de mostrarse en el sitio.")

    class Meta:
        ordering = ['seccion', 'orden', 'id']

    def __str__(self):
        return f"{self.get_seccion_display()}: {self.titulo}"

    @property
    def imagen_url(self):
        if self.imagen:
            return self.imagen.url
        if self.producto and self.producto.imagen_principal:
            return self.producto.imagen_principal.url
        return ''

    @property
    def producto_disponible(self):
        """El producto enlazado, solo si sigue a la venta (si no, no se muestra el botón)."""
        if self.producto and not self.producto.is_deleted:
            return self.producto
        return None

    @property
    def video_embed_url(self):
        """URL para incrustar el video (acepta links youtube.com/watch?v=, youtu.be/ y /embed/)."""
        return youtube_embed_url(self.video_url)


def youtube_embed_url(url):
    m = re.search(r'(?:youtube\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})', url or '')
    return f"https://www.youtube.com/embed/{m.group(1)}" if m else ''
