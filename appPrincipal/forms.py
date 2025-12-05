from django import forms
from django.core import validators
from django.core.exceptions import ValidationError
from .models import Usuario, Producto, Opinion


regiones_ciudades = {
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


# formulario usuario
class UsuarioCustomForm(forms.Form):

    # validacion de rut de usuario
    def validar_rut(rut):
        rut = rut.upper().replace(".", "").replace("-", "")
        cuerpo = rut[:-1]
        verificador = rut[-1]

        suma = 0
        multiplicador = 2
        for caracter in reversed(cuerpo):
            suma += int(caracter) * multiplicador
            multiplicador = 9 if multiplicador == 7 else multiplicador + 1

        resto = suma % 11
        dv = 11 - resto
        if dv == 10:
            dv = 'K'
        elif dv == 11:
            dv = '0'

        return str(dv) == verificador

    rut = forms.CharField(validators=[validar_rut]) 
        
    nombre = forms.CharField(
        validators=[
            validators.MinLengthValidator(5),
            validators.MaxLengthValidator(20)
        ]
    )
    telefono = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'number'}))
    nombre.widget.attrs['class'] = 'form-control'
    email = forms.CharField()
    contraseña = forms.CharField()
    direccion = forms.CharField()

    regiones = [
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
        ('MAGALLANES', 'Región de Magallanes y de la Antártica Chilena')
    ]
    
    region = forms.ChoiceField(choices=regiones, widget=forms.Select(attrs={'id': 'id_region', 'class': 'form-control'}))
    ciudad = forms.ChoiceField(choices=[], widget=forms.Select(attrs={'id': 'id_ciudad', 'class': 'form-control'}))

    def clean_ciudad(self):
        ciudad = self.cleaned_data.get('ciudad')
        region = self.cleaned_data.get('region')  
        if ciudad not in regiones_ciudades.get(region, []):
            raise forms.ValidationError(f'La ciudad {ciudad} no es válida para la región seleccionada.')
        return ciudad

# form para recuperar contraseña
class PasswordResetForm(forms.Form):
    email = forms.EmailField(label="Correo Electrónico", max_length=254, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Ingresa tu correo electrónico',
    }))

# form para opiniones
class OpinionForm(forms.ModelForm):
    class Meta:
        model = Opinion
        fields = ['puntuacion', 'comentario']
        


# administracion

# form de usuario en admin
class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nombre', 'email', 'rut', 'telefono', 'direccion', 'region', 'ciudad']

# form de producto en admin
class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'codigo_de_barra', 'nombre', 'precio', 'stock', 'descripcion', 
            'imagen_principal', 'imagen_2', 'imagen_3', 'imagen_4', 'imagen_5', 'imagen_6',
            'categoria', 'genero'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # desabilita el editar el codigo de barra
        if self.instance and self.instance.pk:
            self.fields['codigo_de_barra'].disabled = True

    # valida codigo de barra
    def clean_codigo_de_barra(self):
        codigo = self.cleaned_data.get('codigo_de_barra')

        if self.instance and self.instance.pk:
            return codigo
        
        productos = Producto.objects.filter(codigo_de_barra=codigo)

        if productos.filter(is_deleted=False).exists():
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



