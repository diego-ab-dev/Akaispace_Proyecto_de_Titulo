"""Cálculos de los reportes del panel (HU-10). Por ahora, la ganancia de las ventas.

Montos en pesos chilenos con IVA incluido. Un detalle de venta sin costo_unitario (NULL: el producto no
tenía costo registrado al venderse) no se puede usar para calcular ganancia, así que se excluye y el
reporte informa cuántos detalles y qué productos quedaron fuera.
"""
from django.db.models import F, Sum

from appPrincipal.models import ProductoVenta


def ganancia(ventas):
    """`ventas`: queryset de Venta (por ejemplo, filtrado por fecha). Las anuladas no se consideran."""
    detalles = ProductoVenta.objects.filter(venta__in=ventas.filter(anulada_en__isnull=True))
    con_costo = detalles.filter(costo_unitario__isnull=False).aggregate(
        ventas=Sum(F('cantidad') * F('precio_unitario')),
        costos=Sum(F('cantidad') * F('costo_unitario')),
    )
    sin_costo = detalles.filter(costo_unitario__isnull=True)
    total_ventas = con_costo['ventas'] or 0
    total_costos = con_costo['costos'] or 0
    return {
        'ventas': total_ventas,
        'costos': total_costos,
        'ganancia': total_ventas - total_costos,
        'detalles_sin_costo': sin_costo.count(),
        'productos_sin_costo': list(
            sin_costo.values_list('producto__nombre', flat=True).distinct().order_by('producto__nombre')
        ),
    }
