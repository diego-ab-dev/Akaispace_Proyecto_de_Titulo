from django import template

register = template.Library()

# Formatea un número al estilo chileno
@register.filter
def formato_chileno(valor):
    if not isinstance(valor, (int, float)):
        return valor  
    return f"{valor:,.0f}".replace(",", ".")


@register.filter
def multiply(value, arg):
    return value * arg


@register.filter(name='add_class')
def add_class(value, css_class):
    return value.as_widget(attrs={"class": css_class})

@register.filter
def range_filter(value):
    return range(1, value + 1)

@register.filter
def get_item(dictionary, key):
    try:
        return dictionary.get(key)
    except AttributeError:
        return None

@register.simple_tag(takes_context=True)
def param_replace(context, **kwargs):
    d = context['request'].GET.copy()
    for k, v in kwargs.items():
        d[k] = v
    return d.urlencode()

@register.filter
def valor_absoluto(valor):
    return abs(valor) if isinstance(valor, (int, float)) else valor


# Ofertas: el producto guarda su precio anterior cuando el admin lo rebaja (ver ProductoForm).
# El % se redondea hacia abajo para no anunciar más descuento del real; bajo 1% no se muestra oferta.
@register.filter
def descuento(producto):
    """Porcentaje de rebaja del producto (ej. 25), o 0 si no está en oferta."""
    anterior, precio = getattr(producto, 'precio_anterior', None), getattr(producto, 'precio', None)
    if not anterior or precio is None or anterior <= precio:
        return 0
    return (anterior - precio) * 100 // anterior


@register.filter
def ahorro(producto):
    """Pesos que se ahorra el cliente con la oferta, o 0."""
    return producto.precio_anterior - producto.precio if descuento(producto) else 0
