from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core import validators
from django.core.exceptions import ValidationError
from .constants import REGIONES, REGIONES_CIUDADES
from .models import (Categoria, ConfiguracionSitio, Destacado, Devolucion, ImagenDevolucion, ImagenProducto,
                     MovimientoCaja, Opinion, Producto, Usuario, youtube_embed_url)
import os


# validacion de rut
def calcular_dv(cuerpo):
    suma = 0
    multiplicador = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1

    dv = 11 - (suma % 11)
    if dv == 11:
        return '0'
    if dv == 10:
        return 'K'
    return str(dv)


def normalizar_rut(rut):
    limpio = (rut or '').strip().upper().replace('.', '').replace('-', '')
    cuerpo, dv = limpio[:-1], limpio[-1:]

    if not cuerpo.isdigit() or len(cuerpo) < 7 or len(cuerpo) > 8 or dv not in '0123456789K':
        raise ValidationError('El RUT no tiene un formato válido.')
    if calcular_dv(cuerpo) != dv:
        raise ValidationError('El RUT no es válido (dígito verificador incorrecto).')

    return f"{int(cuerpo):,}".replace(',', '.') + '-' + dv


# formulario usuario
class UsuarioCustomForm(forms.Form):

    rut = forms.CharField()

    def clean_rut(self):
        return normalizar_rut(self.cleaned_data['rut'])
        
    nombre = forms.CharField(
        max_length=50, 
        validators=[
            validators.MinLengthValidator(5),
            validators.MaxLengthValidator(50)
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'id': 'floatingInputUsername',
            'maxlength': '50', 
            'placeholder': 'myusername'
        })
    )
    telefono = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'number'}))

    email = forms.EmailField(
        max_length=254, 
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 
            'id': 'floatingInputEmail',
            'maxlength': '254', 
            'placeholder': 'name@example.com'
        })
    )

    contraseña = forms.CharField()
    confirmar_contraseña = forms.CharField()

    direccion = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'floatingInputAdress', 
            'maxlength': '100', 
            'placeholder': 'Picarte 344'
        })
    )

    region = forms.ChoiceField(choices=REGIONES, widget=forms.Select(attrs={'id': 'id_region', 'class': 'form-control'}))
    ciudad = forms.ChoiceField(choices=[], widget=forms.Select(attrs={'id': 'id_ciudad', 'class': 'form-control'}))


    # HU-01: declaración de edad obligatoria al registrarse
    declaracion_edad = forms.ChoiceField(
        choices=Usuario.DECLARACIONES_EDAD, widget=forms.RadioSelect,
        error_messages={'required': 'Debes declarar tu edad para crear tu cuenta.'},
    )
    acepta_privacidad = forms.BooleanField(error_messages={
        'required': 'Debes aceptar los Términos y Condiciones y la Política de Privacidad para crear tu cuenta.',
    })
    autoriza_datos_navegacion = forms.BooleanField(required=False)

    def clean_ciudad(self):
        ciudad = self.cleaned_data.get('ciudad')
        region = self.cleaned_data.get('region')
        if ciudad not in REGIONES_CIUDADES.get(region, []):
            raise forms.ValidationError(f'La ciudad {ciudad} no es válida para la región seleccionada.')
        return ciudad

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean(self):
        cleaned_data = super().clean()
        contraseña = cleaned_data.get('contraseña')
        if not contraseña:
            return cleaned_data

        if contraseña != cleaned_data.get('confirmar_contraseña'):
            self.add_error('confirmar_contraseña', 'Las contraseñas no coinciden.')
            return cleaned_data

        usuario = Usuario(email=cleaned_data.get('email', ''), nombre=cleaned_data.get('nombre', ''))
        try:
            validate_password(contraseña, user=usuario)
        except ValidationError as e:
            self.add_error('contraseña', e)
        return cleaned_data

# form para opiniones
class OpinionForm(forms.ModelForm):
    class Meta:
        model = Opinion
        fields = ['puntuacion', 'comentario']

# form para devoluciones
class SolicitudDevolucionForm(forms.Form):
    cantidad = forms.IntegerField(min_value=1)
    descripcion = forms.CharField(widget=forms.Textarea, required=True)

    def __init__(self, *args, cantidad_maxima, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cantidad'].validators.append(validators.MaxValueValidator(
            cantidad_maxima, message=f"Solo puedes devolver hasta {cantidad_maxima} unidad(es)."
        ))


# fotos de evidencia de la devolución: hasta 3, todas opcionales
class ImagenDevolucionForm(forms.ModelForm):
    class Meta:
        model = ImagenDevolucion
        fields = ['imagen']
        error_messages = {'imagen': {'invalid_image': 'Archivo no válido. Solo imágenes (JPG, PNG).'}}

    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if imagen and os.path.splitext(imagen.name)[1].lower() not in ['.jpg', '.jpeg', '.png', '.webp']:
            raise forms.ValidationError("Formato no permitido.")
        return imagen


ImagenDevolucionFormSet = forms.inlineformset_factory(
    Devolucion, ImagenDevolucion, form=ImagenDevolucionForm,
    extra=Devolucion.MAXIMO_IMAGENES, max_num=Devolucion.MAXIMO_IMAGENES, validate_max=True, can_delete=False,
)




# administracion

# form de usuario en admin
class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nombre', 'email', 'rut', 'telefono', 'direccion', 'region', 'ciudad']
        
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '50'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '100'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'rut': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'maxlength': '254'}),
            'region': forms.Select(attrs={'class': 'form-select'}),
            'ciudad': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if len(nombre) > 50:
            raise forms.ValidationError("El nombre no puede exceder los 50 caracteres.")
        return nombre

    def clean_direccion(self):
        direccion = self.cleaned_data.get('direccion')
        if len(direccion) > 100:
            raise forms.ValidationError("La dirección no puede exceder los 100 caracteres.")
        return direccion

# form de producto en admin
class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'codigo_de_barra', 'nombre', 'precio', 'costo', 'stock', 'stock_critico', 'descripcion',
            'categoria', 'plataforma', 'genero',
        ]

        widgets = {
            'codigo_de_barra': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 780123456'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '60', 'placeholder': 'Nombre del producto'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control'}),
            'costo': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Opcional'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_critico': forms.NumberInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'plataforma': forms.Select(attrs={'class': 'form-select'}),
            'genero': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'costo': 'Costo unitario con IVA',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['plataforma'].empty_label = 'Sin plataforma'
        self.fields['genero'].empty_label = 'Sin género'
        if self.instance and self.instance.pk:
            self.fields['codigo_de_barra'].disabled = True

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if len(nombre) > 60:
            raise forms.ValidationError("El nombre es demasiado largo (máximo 60 caracteres).")
        return nombre

    # valida codigo de barra: es único también entre los productos eliminados
    def clean_codigo_de_barra(self):
        codigo = (self.cleaned_data.get('codigo_de_barra') or '').strip() or None

        if self.instance and self.instance.pk:
            return self.instance.codigo_de_barra

        existente = Producto.todos.filter(codigo_de_barra=codigo).first() if codigo else None
        if existente and existente.is_deleted:
            raise forms.ValidationError("Este código de barras pertenece a un producto eliminado.")
        if existente:
            raise forms.ValidationError("Ya existe un producto activo con este código de barras.")

        return codigo

    # valida límite de stock
    def clean_stock(self):
        stock = self.cleaned_data.get('stock')

        if stock is None:
            return stock

        if stock < 0:
            raise forms.ValidationError("El stock no puede ser negativo.")

        if stock > 999:
            raise forms.ValidationError("El stock máximo permitido es 999 unidades.")

        return stock


# imágenes del producto: hasta 6; una se marca como principal con el radio "principal" del formulario
class ImagenProductoForm(forms.ModelForm):
    class Meta:
        model = ImagenProducto
        fields = ['imagen']
        widgets = {'imagen': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})}

    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if imagen and hasattr(imagen, 'content_type'):
            if not imagen.content_type.startswith('image/'):
                raise forms.ValidationError("El archivo subido no es una imagen válida.")
            extensiones_validas = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
            ext = os.path.splitext(imagen.name)[1].lower()
            if ext not in extensiones_validas:
                raise forms.ValidationError(
                    f"Formato no permitido ({ext}). Solo se aceptan: {', '.join(extensiones_validas)}")
        return imagen


class BaseImagenProductoFormSet(forms.BaseInlineFormSet):
    def imagenes_conservadas(self):
        """[(posición en el formulario, ImagenProducto)] de los espacios que quedan con imagen."""
        conservadas = []
        for posicion, form in enumerate(self.forms):
            if form.cleaned_data.get('DELETE') or not form.instance.imagen:
                continue
            conservadas.append((posicion, form.instance))
        return conservadas

    def clean(self):
        super().clean()
        if not any(self.errors) and not self.imagenes_conservadas():
            raise forms.ValidationError("Sube al menos una imagen del producto.")

    def guardar(self, principal):
        """Guarda las imágenes en el orden de los espacios del formulario. `principal` es la posición
        elegida como imagen principal; si esa posición quedó vacía, la principal es la primera."""
        producto = self.instance
        conservadas = self.imagenes_conservadas()
        posiciones = [posicion for posicion, _ in conservadas]
        elegida = principal if principal in posiciones else posiciones[0]
        # se quita la marca de principal antes de asignarla, para no chocar con la restricción única
        producto.imagenes_producto.update(es_principal=None)
        for form in self.forms:
            if form.cleaned_data.get('DELETE') and form.instance.pk:
                form.instance.delete()
        for orden, (posicion, imagen) in enumerate(conservadas, 1):
            imagen.producto = producto
            imagen.orden = orden
            imagen.es_principal = True if posicion == elegida else None
            imagen.save()


ImagenProductoFormSet = forms.inlineformset_factory(
    Producto, ImagenProducto, form=ImagenProductoForm, formset=BaseImagenProductoFormSet,
    extra=Producto.MAXIMO_IMAGENES, max_num=Producto.MAXIMO_IMAGENES, validate_max=True, can_delete=True,
)


# form de la portada (carrusel, nuevos lanzamientos y promos del navbar) en el panel
class DestacadoForm(forms.ModelForm):
    class Meta:
        model = Destacado
        fields = ['seccion', 'producto', 'titulo', 'texto', 'imagen', 'etiqueta', 'video_url', 'orden', 'activo']
        widgets = {
            'seccion': forms.Select(attrs={'class': 'form-select'}),
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '80'}),
            'texto': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'maxlength': '400'}),
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'etiqueta': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '20'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.youtube.com/watch?v=...'}),
            'orden': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = Producto.objects.select_related('categoria', 'plataforma').order_by('nombre')
        self.fields['producto'].empty_label = 'Sin producto'
        self.fields['producto'].label_from_instance = lambda p: (
            f"{p.nombre} · {p.categoria_texto} · Cód. {p.codigo_de_barra or 'sin código'}"
        )

    def clean_video_url(self):
        video_url = self.cleaned_data.get('video_url', '')
        if video_url and not youtube_embed_url(video_url):
            raise forms.ValidationError('Pega el link de un video de YouTube (por ejemplo https://www.youtube.com/watch?v=...).')
        return video_url

    def clean(self):
        cleaned_data = super().clean()
        seccion = cleaned_data.get('seccion')
        producto = cleaned_data.get('producto')
        imagen = cleaned_data.get('imagen')
        if seccion == Destacado.SECCION_LANZAMIENTOS:
            if not cleaned_data.get('video_url') and not imagen and not producto:
                self.add_error('video_url', 'Agrega un video, una imagen o un producto para este lanzamiento.')
        elif seccion and not producto:
            self.add_error('producto', 'Elige el producto al que lleva este destacado.')

        if seccion and cleaned_data.get('activo'):
            self.instance.seccion = seccion
            if self.instance.supera_maximo_visibles():
                self.add_error('activo', mensaje_maximo_visibles(seccion))
        return cleaned_data


def mensaje_maximo_visibles(seccion):
    nombre = dict(Destacado.SECCIONES)[seccion]
    maximo = Destacado.MAXIMO_VISIBLES[seccion]
    return (f'"{nombre}" ya tiene {maximo} elementos visibles (el máximo). '
            'Oculta o elimina alguno, o guarda este como oculto.')


class ConfiguracionSitioForm(forms.ModelForm):
    # en el panel se marcan las categorías que SÍ se ven en el navbar (Categoria.visible_en_menu)
    categorias_visibles = forms.ModelMultipleChoiceField(
        queryset=Categoria.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = ConfiguracionSitio
        fields = ['productos_relacionados', 'mostrar_opiniones', 'mostrar_etiquetas', 'mostrar_stock',
                  'mostrar_recomendaciones', 'kpi01_linea_base']
        widgets = {
            'kpi01_linea_base': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1}),
            'productos_relacionados': forms.RadioSelect,
            'mostrar_opiniones': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'mostrar_etiquetas': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'mostrar_stock': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'mostrar_recomendaciones': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial['categorias_visibles'] = list(
                Categoria.objects.filter(visible_en_menu=True).values_list('id', flat=True))

    def save(self, commit=True):
        configuracion = super().save(commit)
        # lista de ids y no queryset: MySQL no permite un UPDATE con subconsulta sobre la misma tabla
        visibles = [categoria.id for categoria in self.cleaned_data['categorias_visibles']]
        Categoria.objects.filter(id__in=visibles).update(visible_en_menu=True)
        Categoria.objects.exclude(id__in=visibles).update(visible_en_menu=False)
        return configuracion


# HU-10: retiro o ingreso de dinero en la caja de la tienda física
class MovimientoCajaForm(forms.ModelForm):
    tipo = forms.ChoiceField(choices=[(MovimientoCaja.RETIRO, 'Retiro'), (MovimientoCaja.INGRESO, 'Ingreso')],
                             initial=MovimientoCaja.RETIRO, widget=forms.RadioSelect,
                             error_messages={'required': 'Indica si es un retiro o un ingreso.'})

    class Meta:
        model = MovimientoCaja
        fields = ['tipo', 'monto', 'motivo']
        widgets = {
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'step': 1, 'inputmode': 'numeric'}),
            'motivo': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 255,
                                             'placeholder': 'Ej.: pago a proveedor, sencillo para la caja'}),
        }
        error_messages = {
            'monto': {'required': 'Ingresa el monto.'},
            'motivo': {'required': 'Indica el motivo del movimiento.'},
        }

    def clean_monto(self):
        monto = self.cleaned_data['monto']
        if monto < 1:
            raise ValidationError("El monto debe ser mayor que cero.")
        return monto
