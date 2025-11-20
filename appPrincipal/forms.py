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

class UsuarioCustomForm(forms.Form):


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

class PasswordResetForm(forms.Form):
    email = forms.EmailField(label="Correo Electrónico", max_length=254, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Ingresa tu correo electrónico',
    }))


class OpinionForm(forms.ModelForm):
    class Meta:
        model = Opinion
        fields = ['puntuacion', 'comentario']
        widgets = {
            'puntuacion': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'comentario': forms.Textarea(attrs={'rows': 4}),
        }


# administracion

class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nombre', 'email', 'rut', 'telefono', 'direccion', 'region', 'ciudad']

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'codigo_de_barra', 'nombre', 'precio', 'stock', 'descripcion', 
            'imagen_principal', 'imagen_2', 'imagen_3', 'imagen_4', 'imagen_5', 'imagen_6',
            'categoria', 'genero'
        ]
