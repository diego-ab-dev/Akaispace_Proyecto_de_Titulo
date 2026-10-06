from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core import validators
from django.core.exceptions import ValidationError
from .constants import REGIONES, REGIONES_CIUDADES
from .models import Destacado, Opinion, Producto, Usuario, youtube_embed_url
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


    acepta_privacidad = forms.BooleanField(error_messages={
        'required': 'Debes declarar tu edad y aceptar los Términos y Condiciones y la Política de Privacidad para crear tu cuenta.',
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
    
    mensaje_error = {'invalid_image': 'Archivo no válido. Solo imágenes (JPG, PNG).'}

    imagen1 = forms.ImageField(required=False, error_messages=mensaje_error)
    imagen2 = forms.ImageField(required=False, error_messages=mensaje_error)
    imagen3 = forms.ImageField(required=False, error_messages=mensaje_error)

    def __init__(self, *args, cantidad_maxima, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cantidad'].validators.append(validators.MaxValueValidator(
            cantidad_maxima, message=f"Solo puedes devolver hasta {cantidad_maxima} unidad(es)."
        ))

    def clean(self):
        cleaned_data = super().clean()
        campos_imagen = ['imagen1', 'imagen2', 'imagen3']
        extensiones_validas = ['.jpg', '.jpeg', '.png', '.webp']

        for campo in campos_imagen:
            imagen = cleaned_data.get(campo)
            
            if imagen:
                ext = os.path.splitext(imagen.name)[1].lower()
                if ext not in extensiones_validas:
                    self.add_error(campo, "Formato no permitido.")

        return cleaned_data
        




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
            'codigo_de_barra', 'nombre', 'precio', 'stock', 'descripcion', 
            'imagen_principal', 'imagen_2', 'imagen_3', 'imagen_4', 'imagen_5', 'imagen_6',
            'categoria', 'genero'
        ]

        widgets = {
            'codigo_de_barra': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 780123456'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '60', 'placeholder': 'Nombre del producto'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'genero': forms.Select(attrs={'class': 'form-select'}),
            'imagen_principal': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'imagen_2': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'imagen_3': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'imagen_4': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'imagen_5': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'imagen_6': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
        labels = {
            'imagen_principal': 'Imagen 1 - Principal',
            'imagen_2': 'Imagen 2 - (Opcional)',
            'imagen_3': 'Imagen 3 - (Opcional)',
            'imagen_4': 'Imagen 4 - (Opcional)',
            'imagen_5': 'Imagen 5 - (Opcional)',
            'imagen_6': 'Imagen 6 - (Opcional)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['codigo_de_barra'].disabled = True


            for field_name in ['imagen_principal', 'imagen_2', 'imagen_3', 'imagen_4', 'imagen_5', 'imagen_6']:
                self.fields[field_name].widget.attrs.update({'class': 'form-control'})

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if len(nombre) > 60:
            raise forms.ValidationError("El nombre es demasiado largo (máximo 60 caracteres).")
        return nombre

    # valida codigo de barra
    def clean_codigo_de_barra(self):
        codigo = self.cleaned_data.get('codigo_de_barra')

        if self.instance and self.instance.pk:
            return codigo
        
        if Producto.objects.filter(codigo_de_barra=codigo).exists():
            raise forms.ValidationError(
                "Ya existe un producto activo con este código de barras."
            )

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

    def clean(self):
        cleaned_data = super().clean()
        
        campos_imagen = ['imagen_principal', 'imagen_2', 'imagen_3', 'imagen_4', 'imagen_5', 'imagen_6']
        
        extensiones_validas = ['.jpg', '.jpeg', '.png', '.webp', '.gif']

        for campo in campos_imagen:
            imagen = cleaned_data.get(campo)
            
            if imagen and hasattr(imagen, 'content_type'):
                
                if not imagen.content_type.startswith('image/'):
                    self.add_error(campo, "El archivo subido no es una imagen válida.")
                    continue 
                
                ext = os.path.splitext(imagen.name)[1].lower()
                if ext not in extensiones_validas:
                    self.add_error(campo, f"Formato no permitido ({ext}). Solo se aceptan: {', '.join(extensiones_validas)}")

        return cleaned_data
 



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
        self.fields['producto'].queryset = Producto.objects.order_by('nombre')
        self.fields['producto'].empty_label = 'Sin producto'
        self.fields['producto'].label_from_instance = lambda p: (
            f"{p.nombre} · {p.get_categoria_display()} · Cód. {p.codigo_de_barra}"
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
