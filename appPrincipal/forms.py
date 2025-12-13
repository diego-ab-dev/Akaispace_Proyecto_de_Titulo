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

    direccion = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'floatingInputAdress', 
            'maxlength': '100', 
            'placeholder': 'Picarte 344'
        })
    )

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
            'imagen_principal': forms.FileInput(attrs={'class': 'form-control'}),
            'imagen_2': forms.FileInput(attrs={'class': 'form-control'}),
            'imagen_3': forms.FileInput(attrs={'class': 'form-control'}),
            'imagen_4': forms.FileInput(attrs={'class': 'form-control'}),
            'imagen_5': forms.FileInput(attrs={'class': 'form-control'}),
            'imagen_6': forms.FileInput(attrs={'class': 'form-control'}),
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
        # desabilita el editar el codigo de barra
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



