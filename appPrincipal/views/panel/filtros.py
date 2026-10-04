"""Filtros compartidos por los listados del panel de administración."""
from datetime import datetime, time, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date


def _leer_fecha(valor):
    try:
        return parse_date(valor) if valor else None
    except ValueError:  # formato correcto pero fecha imposible, ej. 2026-02-31
        return None


def _inicio_del_dia(dia):
    return timezone.make_aware(datetime.combine(dia, time.min))


def filtrar_por_fechas(request, queryset, campo):
    """Filtra el queryset por ?fecha_inicio y ?fecha_fin (AAAA-MM-DD) sobre `campo`.

    Devuelve (queryset, errores). Una fecha futura o un rango invertido no se aplica
    y queda explicado en `errores` para mostrarlo en la plantilla.
    """
    hoy = timezone.localdate()
    errores = []
    inicio = _leer_fecha(request.GET.get('fecha_inicio'))
    fin = _leer_fecha(request.GET.get('fecha_fin'))

    if inicio and inicio > hoy:
        errores.append("La fecha de inicio no puede ser futura.")
        inicio = None

    if fin and fin > hoy:
        errores.append("La fecha de fin no puede ser futura.")
        fin = None

    if inicio and fin and inicio > fin:
        errores.append("La fecha de inicio no puede ser mayor que la fecha fin.")
        inicio = fin = None

    # se compara contra el inicio del día siguiente: con campo__lte=fin quedaban fuera los
    # registros del mismo día de fin (fin se interpretaba como las 00:00 de ese día)
    if inicio:
        queryset = queryset.filter(**{f'{campo}__gte': _inicio_del_dia(inicio)})
    if fin:
        queryset = queryset.filter(**{f'{campo}__lt': _inicio_del_dia(fin + timedelta(days=1))})

    return queryset, errores
