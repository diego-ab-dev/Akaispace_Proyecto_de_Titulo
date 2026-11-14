from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.password_validation import validate_password
from django.core import validators
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from .constants import REGIONES, REGIONES_CIUDADES
from .models import (Categoria, ConfiguracionSitio, Destacado, Devolucion, ImagenDevolucion, ImagenProducto,
                     MovimientoCaja, Opinion, Producto, Usuario, youtube_embed_url)
import os
import unicodedata


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


# ---------- validaciones compartidas por los formularios de cuentas ----------
# Los mismos límites se repiten en los atributos de los <input> (maxlength, pattern) para avisar
# antes de enviar, pero la validación que vale es siempre la del servidor.

NOMBRE_MAXIMO = 100            # igual que Usuario.nombre
DIRECCION_MAXIMA = 100
SIGNOS_PERMITIDOS_EN_NOMBRE = " '’-."


def limpiar_nombre(valor):
    """Nombre de una persona. Acepta cualquier letra de Unicode (tildes, ñ, ü, ç, etc.), espacios,
    apóstrofos, guiones y puntos (O'Higgins, Pérez-Cotapos, Mª José), como recomienda la W3C para
    nombres de personas; rechaza números y otros símbolos. Normaliza a NFC y quita espacios repetidos."""
    nombre = ' '.join(unicodedata.normalize('NFC', valor or '').split())
    if not nombre:
        raise ValidationError('Ingresa tu nombre.', code='required')
    for caracter in nombre:
        if caracter not in SIGNOS_PERMITIDOS_EN_NOMBRE and not unicodedata.category(caracter).startswith(('L', 'M')):
            raise ValidationError(
                'El nombre solo puede tener letras (con o sin tilde), espacios, guiones y apóstrofos.',
                code='nombre_caracteres')
    if sum(caracter.isalpha() for caracter in nombre) < 2:
        raise ValidationError('El nombre debe tener al menos 2 letras.', code='nombre_corto')
    if len(nombre) > NOMBRE_MAXIMO:
        raise ValidationError(f'El nombre puede tener hasta {NOMBRE_MAXIMO} caracteres.', code='max_length')
    return nombre


def normalizar_telefono(valor):
    """Celular chileno: 8 dígitos después del +56 9. Acepta '12345678', '912345678' o '+56 9 1234 5678'
    y lo guarda siempre como '+56 9 12345678'."""
    digitos = ''.join(caracter for caracter in (valor or '') if caracter.isdigit())
    if len(digitos) == 11 and digitos.startswith('569'):
        digitos = digitos[3:]
    elif len(digitos) == 9 and digitos.startswith('9'):
        digitos = digitos[1:]
    if len(digitos) != 8:
        raise ValidationError('El teléfono debe tener 8 dígitos después del +56 9.', code='telefono_invalido')
    return f'+56 9 {digitos}'


def limpiar_direccion(valor):
    direccion = ' '.join((valor or '').split())
    if not direccion:
        raise ValidationError('Ingresa tu dirección.', code='required')
    if len(direccion) > DIRECCION_MAXIMA:
        raise ValidationError(f'La dirección puede tener hasta {DIRECCION_MAXIMA} caracteres.', code='max_length')
    if not any(caracter.isalpha() for caracter in direccion):
        raise ValidationError('Escribe la calle y el número (por ejemplo: Picarte 344).', code='direccion_invalida')
    return direccion


def validar_region_y_ciudad(form, requerido=True):
    """Valida que la ciudad pertenezca a la región. Con requerido=False ambos pueden quedar vacíos,
    pero si se llena uno hay que llenar el otro."""
    region = form.cleaned_data.get('region') or ''
    ciudad = form.cleaned_data.get('ciudad') or ''
    if 'region' in form.errors:
        return
    if not region and not ciudad and not requerido:
        return
    if not region:
        form.add_error('region', 'Selecciona tu región.')
    elif not ciudad:
        form.add_error('ciudad', 'Selecciona tu ciudad.')
    elif ciudad not in REGIONES_CIUDADES.get(region, []):
        form.add_error('ciudad', 'Selecciona una ciudad de la región elegida.')


def errores_para_json(form):
    """{'campo': [mensajes]} en el orden de los campos del formulario, más el primer mensaje
    (para respuestas JSON de formularios que se envían con fetch)."""
    errores = {}
    for nombre in [*form.fields, '__all__']:
        if nombre in form.errors:
            errores[nombre] = list(form.errors[nombre])
    for nombre, mensajes in form.errors.items():
        errores.setdefault(nombre, list(mensajes))
    primero = next(iter(errores.values()))[0] if errores else 'Revisa los datos del formulario.'
    return {'success': False, 'message': primero, 'errors': errores}


def _correo_o_rut_en_uso(campo, valor, mensajes):
    usuario = Usuario.objects.filter(**{campo: valor}).only('is_deleted').first()
    if usuario:
        raise ValidationError(mensajes['eliminado'] if usuario.is_deleted else mensajes['registrado'],
                              code='duplicado')


class DatosCuentaForm(forms.Form):
    """Datos personales de una cuenta nueva (registro del cliente y creación desde el panel)."""
    telefono_requerido = True
    direccion_requerida = True
    ubicacion_requerida = True

    rut = forms.CharField(max_length=12, error_messages={'required': 'Ingresa tu RUT.'})
    nombre = forms.CharField(max_length=NOMBRE_MAXIMO, strip=False,
                             error_messages={'required': 'Ingresa tu nombre.',
                                             'max_length': f'El nombre puede tener hasta {NOMBRE_MAXIMO} caracteres.'})
    email = forms.EmailField(max_length=254, error_messages={
        'required': 'Ingresa tu correo electrónico.',
        'invalid': 'Escribe un correo válido (por ejemplo: nombre@correo.cl).',
        'max_length': 'El correo puede tener hasta 254 caracteres.',
    })
    telefono = forms.CharField(max_length=20, required=False)
    region = forms.ChoiceField(choices=REGIONES, required=False,
                               error_messages={'invalid_choice': 'Selecciona una región de la lista.'})
    ciudad = forms.CharField(max_length=100, required=False)
    direccion = forms.CharField(max_length=200, required=False, strip=False)

    def clean_rut(self):
        rut = normalizar_rut(self.cleaned_data['rut'])
        _correo_o_rut_en_uso('rut', rut, {
            'registrado': 'El RUT ya está registrado.',
            'eliminado': 'Este RUT pertenece a un usuario eliminado. No puede volver a usarse.',
        })
        return rut

    def clean_nombre(self):
        return limpiar_nombre(self.cleaned_data['nombre'])

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        _correo_o_rut_en_uso('email', email, {
            'registrado': 'El correo ya está registrado.',
            'eliminado': 'Este correo ya fue utilizado previamente (usuario eliminado). '
                         'No puede volver a registrarse con el mismo correo.',
        })
        return email

    def clean_telefono(self):
        telefono = self.cleaned_data['telefono']
        if not telefono.strip():
            if self.telefono_requerido:
                raise ValidationError('Ingresa tu teléfono.', code='required')
            return ''
        return normalizar_telefono(telefono)

    def clean_direccion(self):
        direccion = self.cleaned_data['direccion']
        if not direccion.strip() and not self.direccion_requerida:
            return ''
        return limpiar_direccion(direccion)

    def clean(self):
        cleaned_data = super().clean()
        validar_region_y_ciudad(self, requerido=self.ubicacion_requerida)
        return cleaned_data


class ContraseñaNuevaMixin(forms.Form):
    """Contraseña + confirmación, validadas con AUTH_PASSWORD_VALIDATORS (RNF-01)."""
    contraseña = forms.CharField(strip=False, error_messages={'required': 'Ingresa una contraseña.'})
    confirmar_contraseña = forms.CharField(strip=False, error_messages={'required': 'Repite tu contraseña.'})

    def validar_contraseña_nueva(self, usuario):
        contraseña = self.cleaned_data.get('contraseña')
        confirmacion = self.cleaned_data.get('confirmar_contraseña')
        if not contraseña:
            return
        try:
            validate_password(contraseña, user=usuario)
        except ValidationError as e:
            self.add_error('contraseña', e)
        if confirmacion and contraseña != confirmacion:
            self.add_error('confirmar_contraseña', 'Las contraseñas no coinciden.')

    def clean(self):
        cleaned_data = super().clean()
        # el validador de similitud compara con el nombre y el correo que se están registrando
        self.validar_contraseña_nueva(Usuario(email=cleaned_data.get('email') or '',
                                              nombre=cleaned_data.get('nombre') or ''))
        return cleaned_data


# formulario de registro del cliente (HU-01)
class UsuarioCustomForm(DatosCuentaForm, ContraseñaNuevaMixin):
    field_order = ['rut', 'nombre', 'email', 'telefono', 'region', 'ciudad', 'direccion',
                   'contraseña', 'confirmar_contraseña', 'declaracion_edad', 'acepta_privacidad',
                   'autoriza_datos_navegacion']

    # HU-01: declaración de edad obligatoria al registrarse
    declaracion_edad = forms.ChoiceField(
        choices=Usuario.DECLARACIONES_EDAD, widget=forms.RadioSelect,
        error_messages={'required': 'Debes declarar tu edad para crear tu cuenta.',
                        'invalid_choice': 'Debes declarar tu edad para crear tu cuenta.'},
    )
    acepta_privacidad = forms.BooleanField(error_messages={
        'required': 'Debes aceptar los Términos y Condiciones y la Política de Privacidad para crear tu cuenta.',
    })
    autoriza_datos_navegacion = forms.BooleanField(required=False)


# formulario para crear un usuario desde el panel: teléfono y dirección son opcionales
# (una cuenta de administrador no los necesita; el cliente puede completarlos en su perfil)
class CrearUsuarioAdminForm(DatosCuentaForm, ContraseñaNuevaMixin):
    telefono_requerido = False
    direccion_requerida = False
    ubicacion_requerida = False
    field_order = ['rut', 'nombre', 'email', 'telefono', 'region', 'ciudad', 'direccion',
                   'contraseña', 'confirmar_contraseña', 'es_administrador']

    es_administrador = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # el administrador llena los datos de otra persona: mensajes sin "tu"
        for campo, mensaje in [('rut', 'Ingresa el RUT.'), ('nombre', 'Ingresa el nombre.'),
                               ('email', 'Ingresa el correo electrónico.'), ('contraseña', 'Ingresa una contraseña.'),
                               ('confirmar_contraseña', 'Repite la contraseña.')]:
            self.fields[campo].error_messages['required'] = mensaje


# datos de contacto y despacho que el cliente edita en su perfil
class EditarPerfilForm(forms.Form):
    telefono = forms.CharField(max_length=20, error_messages={'required': 'Ingresa tu teléfono.'})
    region = forms.ChoiceField(choices=REGIONES, error_messages={
        'required': 'Selecciona tu región.', 'invalid_choice': 'Selecciona una región de la lista.'})
    ciudad = forms.CharField(max_length=100, error_messages={'required': 'Selecciona tu ciudad.'})
    direccion = forms.CharField(max_length=200, strip=False, error_messages={'required': 'Ingresa tu dirección.'})

    def clean_telefono(self):
        return normalizar_telefono(self.cleaned_data['telefono'])

    def clean_direccion(self):
        return limpiar_direccion(self.cleaned_data['direccion'])

    def clean(self):
        cleaned_data = super().clean()
        if 'ciudad' not in self.errors:
            validar_region_y_ciudad(self)
        return cleaned_data


class CambiarContraseñaForm(forms.Form):
    contraseña_actual = forms.CharField(strip=False, error_messages={'required': 'Ingresa tu contraseña actual.'})
    nueva_contraseña = forms.CharField(strip=False, error_messages={'required': 'Ingresa la nueva contraseña.'})
    confirmar_contraseña = forms.CharField(strip=False, error_messages={'required': 'Repite la nueva contraseña.'})

    def __init__(self, *args, usuario, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)

    def clean_contraseña_actual(self):
        contraseña = self.cleaned_data['contraseña_actual']
        if not self.usuario.check_password(contraseña):
            raise ValidationError('La contraseña actual no es correcta.', code='contraseña_incorrecta')
        return contraseña

    def clean(self):
        cleaned_data = super().clean()
        nueva = cleaned_data.get('nueva_contraseña')
        confirmacion = cleaned_data.get('confirmar_contraseña')
        if nueva:
            try:
                validate_password(nueva, user=self.usuario)
            except ValidationError as e:
                self.add_error('nueva_contraseña', e)
            if confirmacion and nueva != confirmacion:
                self.add_error('confirmar_contraseña', 'Las contraseñas nuevas no coinciden.')
            if cleaned_data.get('contraseña_actual') and nueva == cleaned_data['contraseña_actual']:
                self.add_error('nueva_contraseña', 'La nueva contraseña debe ser distinta de la actual.')
        return cleaned_data


class ReclamoForm(forms.Form):
    ASUNTO_MAXIMO = 50
    DESCRIPCION_MAXIMA = 2000

    asunto = forms.CharField(max_length=ASUNTO_MAXIMO, error_messages={
        'required': 'Escribe el asunto del reclamo.',
        'max_length': f'El asunto puede tener hasta {ASUNTO_MAXIMO} caracteres.',
    })
    descripcion = forms.CharField(max_length=DESCRIPCION_MAXIMA, error_messages={
        'required': 'Describe qué pasó con tu compra.',
        'max_length': f'La descripción puede tener hasta {DESCRIPCION_MAXIMA} caracteres.',
    })

# form para recuperar contraseña (HU-11): a diferencia del de Django, también incluye las cuentas
# creadas solo con Google (sin contraseña utilizable), para que puedan definir una
class RecuperarContraseñaForm(PasswordResetForm):
    def get_users(self, email):
        usuarios = Usuario._default_manager.filter(email__iexact=email, is_active=True, is_deleted=False)
        return (u for u in usuarios if _mismo_correo(email, u.email))

# compara correos sin distinguir mayúsculas ni formas unicode equivalentes (NFKC + casefold),
# igual que hace Django internamente, sin depender de su función privada
def _mismo_correo(correo1, correo2):
    return unicodedata.normalize('NFKC', correo1).casefold() == unicodedata.normalize('NFKC', correo2).casefold()

# form para opiniones
class OpinionForm(forms.ModelForm):
    COMENTARIO_MAXIMO = 1000

    class Meta:
        model = Opinion
        fields = ['puntuacion', 'comentario']
        error_messages = {
            'puntuacion': {'required': 'Elige una puntuación de 1 a 5 estrellas.',
                           'invalid_choice': 'Elige una puntuación de 1 a 5 estrellas.',
                           'invalid': 'Elige una puntuación de 1 a 5 estrellas.'},
            'comentario': {'required': 'Escribe un comentario sobre el producto.'},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comentario'].max_length = self.COMENTARIO_MAXIMO
        self.fields['comentario'].validators.append(validators.MaxLengthValidator(
            self.COMENTARIO_MAXIMO, message=f'El comentario puede tener hasta {self.COMENTARIO_MAXIMO} caracteres.'))

# form para devoluciones
class SolicitudDevolucionForm(forms.Form):
    DESCRIPCION_MAXIMA = 1000

    cantidad = forms.IntegerField(min_value=1, error_messages={
        'required': 'Indica cuántas unidades quieres devolver.',
        'invalid': 'Indica cuántas unidades quieres devolver.',
        'min_value': 'Debes devolver al menos 1 unidad.',
    })
    descripcion = forms.CharField(widget=forms.Textarea, max_length=DESCRIPCION_MAXIMA, error_messages={
        'required': 'Cuéntanos el motivo de la devolución.',
        'max_length': f'El motivo puede tener hasta {DESCRIPCION_MAXIMA} caracteres.',
    })

    def __init__(self, *args, cantidad_maxima, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cantidad'].validators.append(validators.MaxValueValidator(
            cantidad_maxima, message=f"Solo puedes devolver hasta {cantidad_maxima} unidad(es)."
        ))


# fotos de evidencia de la devolución: hasta 3, todas opcionales
# ---------- fotos que se suben (devoluciones, productos y portada) ----------
# Se acepta solo lo que el navegador muestra como foto. El formato real se revisa abriendo el archivo
# con Pillow (forms.ImageField), no por el nombre ni por el tipo que declara el navegador, que se pueden
# falsear; un .txt renombrado a .jpg no pasa.
FORMATOS_IMAGEN = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp', 'GIF': '.gif'}
EXTENSIONES_IMAGEN = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
IMAGEN_MAXIMA_MB = 8
MENSAJE_FORMATO_IMAGEN = 'Solo se aceptan fotos JPG, PNG, WEBP o GIF.'
ACCEPT_IMAGEN = 'image/jpeg,image/png,image/webp,image/gif,.jpg,.jpeg,.png,.webp,.gif'
# atributos del <input type="file">: filtran el explorador de archivos y static/js/formularios.js
# avisa apenas se elige un archivo que no sirve (la validación que vale es validar_imagen)
ATRIBUTOS_IMAGEN = {'accept': ACCEPT_IMAGEN, 'data-validacion': 'imagen', 'data-max-mb': str(IMAGEN_MAXIMA_MB)}
ERRORES_IMAGEN = {'invalid_image': f'El archivo no es una foto válida. {MENSAJE_FORMATO_IMAGEN}',
                  'invalid_extension': MENSAJE_FORMATO_IMAGEN}


def validar_imagen(imagen):
    """Valida una foto recién subida: formato real, extensión y peso. Deja la extensión del archivo
    igual a su formato real (un PNG llamado foto.jpg se guarda como foto.png)."""
    if not isinstance(imagen, UploadedFile):
        return imagen  # foto que ya estaba guardada (edición sin cambiarla)
    formato = getattr(getattr(imagen, 'image', None), 'format', None)
    nombre, extension = os.path.splitext(imagen.name)
    if formato not in FORMATOS_IMAGEN or extension.lower() not in EXTENSIONES_IMAGEN:
        raise ValidationError(MENSAJE_FORMATO_IMAGEN, code='formato_imagen')
    if imagen.size > IMAGEN_MAXIMA_MB * 1024 * 1024:
        raise ValidationError(
            f'La foto pesa {imagen.size / 1024 / 1024:.1f} MB; el máximo es {IMAGEN_MAXIMA_MB} MB.',
            code='imagen_pesada')
    imagen.name = (nombre or 'imagen') + FORMATOS_IMAGEN[formato]
    return imagen


# fotos de evidencia de la devolución: hasta 3, todas opcionales
class ImagenDevolucionForm(forms.ModelForm):
    class Meta:
        model = ImagenDevolucion
        fields = ['imagen']
        error_messages = {'imagen': ERRORES_IMAGEN}

    def clean_imagen(self):
        return validar_imagen(self.cleaned_data.get('imagen'))


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
    # Oferta: al rebajar el precio, el precio de antes queda guardado y la tienda lo muestra tachado con el %.
    # Si el cambio fue para corregir un error, el admin desmarca la casilla y no se anuncia rebaja.
    mostrar_oferta = forms.BooleanField(
        required=False, label='Mostrar como oferta',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
    )

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
        # precio "normal" contra el que se compara la rebaja: el anterior si ya está en oferta, si no el actual.
        # Se guarda aquí porque al validar el formulario la instancia ya toma el precio nuevo.
        self.precio_normal = None
        if self.instance and self.instance.pk:
            self.fields['codigo_de_barra'].disabled = True
            en_oferta = bool(self.instance.precio_anterior and self.instance.precio_anterior > self.instance.precio)
            self.precio_normal = self.instance.precio_anterior if en_oferta else self.instance.precio
            self.fields['mostrar_oferta'].initial = en_oferta

    def save(self, commit=True):
        producto = super().save(commit=False)
        hay_rebaja = self.precio_normal is not None and producto.precio < self.precio_normal
        producto.precio_anterior = self.precio_normal if hay_rebaja and self.cleaned_data.get('mostrar_oferta') else None
        if commit:
            producto.save()
            self.save_m2m()
        return producto

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
        widgets = {'imagen': forms.FileInput(attrs={'class': 'form-control', **ATRIBUTOS_IMAGEN})}
        error_messages = {'imagen': ERRORES_IMAGEN}

    def clean_imagen(self):
        return validar_imagen(self.cleaned_data.get('imagen'))


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
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control', **ATRIBUTOS_IMAGEN}),
            'etiqueta': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '20'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.youtube.com/watch?v=...'}),
            'orden': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        error_messages = {'imagen': ERRORES_IMAGEN}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = Producto.objects.select_related('categoria', 'plataforma').order_by('nombre')
        self.fields['producto'].empty_label = 'Sin producto'
        self.fields['imagen'].help_text += f' JPG, PNG, WEBP o GIF, de hasta {IMAGEN_MAXIMA_MB} MB.'
        self.fields['producto'].label_from_instance = lambda p: (
            f"{p.nombre} · {p.categoria_texto} · Cód. {p.codigo_de_barra or 'sin código'}"
        )

    def clean_imagen(self):
        return validar_imagen(self.cleaned_data.get('imagen'))

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
