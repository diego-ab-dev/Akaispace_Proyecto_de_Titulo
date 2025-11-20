from django import template

register = template.Library()

@register.filter
def formato_chileno(valor):
    """
    Formatea un número al estilo chileno:
    - Punto para los miles
    - Coma para los decimales (si corresponde)
    """
    if not isinstance(valor, (int, float)):
        return valor  
    return f"{valor:,.0f}".replace(",", ".")


@register.filter
def multiply(value, arg):
    return value * arg


@register.filter(name='add_class')
def add_class(value, css_class):
    return value.as_widget(attrs={"class": css_class})

