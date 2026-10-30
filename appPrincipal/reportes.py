"""Cálculos de los reportes y del tablero de KPI del panel (HU-10).

Montos en pesos chilenos. Los precios y costos se guardan con IVA incluido (monto bruto); el neto se obtiene
dividiendo por 1,19. Se consideran las ventas de todos los canales (web, tienda física y WhatsApp), sin las
anuladas. Un detalle de venta sin costo_unitario (el producto no tenía costo registrado al venderse) no se
puede usar para calcular ganancia, así que se excluye y el reporte informa qué productos quedaron fuera.

Las fórmulas y metas de los KPI son las de la Tabla 13 del informe (formulación SMART).
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from dateutil.relativedelta import relativedelta
from django.db.models import Count, F, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date

from appPrincipal.models import (Carrito, Compra, MovimientoCaja, Producto, ProductoVenta, Venta)
from appPrincipal.recomendaciones import cobertura_atributos, tasa_de_clics

IVA = 19
MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
MESES_LARGOS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre',
                'octubre', 'noviembre', 'diciembre']
DIAS_POR_DIA = 62  # hasta este largo, los gráficos agrupan por día; sobre él, por mes


def neto(bruto):
    """Monto sin IVA, redondeado al peso."""
    return round((bruto or 0) * 100 / (100 + IVA))


def bruto_y_neto(bruto):
    bruto = bruto or 0
    return {'bruto': bruto, 'neto': neto(bruto), 'iva': bruto - neto(bruto)}


def porcentaje(parte, total):
    return round(parte * 100 / total, 1) if total else None


def variacion(actual, anterior):
    """Variación porcentual frente al periodo anterior; None si el anterior es 0."""
    return round((actual - anterior) * 100 / anterior, 1) if anterior else None


def _inicio_del_dia(dia):
    return timezone.make_aware(datetime.combine(dia, time.min))


# --- periodo de los reportes ---

PERIODOS = [
    ('hoy', 'Hoy'),
    ('7d', 'Últimos 7 días'),
    ('30d', 'Últimos 30 días'),
    ('mes', 'Este mes'),
    ('mes_anterior', 'Mes anterior'),
    ('anio', 'Este año'),
]


@dataclass(frozen=True)
class Periodo:
    desde: date
    hasta: date  # incluido
    clave: str = 'personalizado'

    @property
    def inicio(self):
        return _inicio_del_dia(self.desde)

    @property
    def fin(self):
        """Primer instante después del periodo (límite exclusivo)."""
        return _inicio_del_dia(self.hasta + timedelta(days=1))

    @property
    def dias(self):
        return (self.hasta - self.desde).days + 1

    @property
    def por_dia(self):
        return self.dias <= DIAS_POR_DIA

    @property
    def nombre(self):
        """Ej.: "30 oct 2026", "1 al 30 oct 2026", "1 sep al 30 oct 2026"."""
        desde, hasta = self.desde, self.hasta
        mes = lambda dia: MESES[dia.month - 1].lower()
        if desde == hasta:
            return f"{desde.day} {mes(desde)} {desde.year}"
        if desde.year != hasta.year:
            return f"{desde.day} {mes(desde)} {desde.year} al {hasta.day} {mes(hasta)} {hasta.year}"
        if desde.month != hasta.month:
            return f"{desde.day} {mes(desde)} al {hasta.day} {mes(hasta)} {hasta.year}"
        return f"{desde.day} al {hasta.day} {mes(hasta)} {hasta.year}"

    def anterior(self):
        """Periodo con el que se compara: el mismo tramo del mes o año anterior, o los días inmediatamente previos."""
        if self.clave in ('mes', 'mes_anterior'):
            desde = self.desde - relativedelta(months=1)
            hasta = self.hasta - relativedelta(months=1)
            if self.clave == 'mes_anterior':
                hasta = desde + relativedelta(months=1, days=-1)
            return Periodo(desde, hasta)
        if self.clave == 'anio':
            return Periodo(self.desde - relativedelta(years=1), self.hasta - relativedelta(years=1))
        return Periodo(self.desde - timedelta(days=self.dias), self.desde - timedelta(days=1))


def periodo_predefinido(clave, hoy=None):
    hoy = hoy or timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    rangos = {
        'hoy': (hoy, hoy),
        '7d': (hoy - timedelta(days=6), hoy),
        '30d': (hoy - timedelta(days=29), hoy),
        'mes': (inicio_mes, hoy),
        'mes_anterior': (inicio_mes - relativedelta(months=1), inicio_mes - timedelta(days=1)),
        'anio': (hoy.replace(month=1, day=1), hoy),
    }
    desde, hasta = rangos[clave]
    return Periodo(desde, hasta, clave)


def _leer_fecha(valor):
    try:
        return parse_date(valor) if valor else None
    except ValueError:
        return None


def periodo_desde_request(datos):
    """Lee el periodo de los parámetros GET: `periodo` (una clave de PERIODOS) o `desde` y `hasta`.
    Devuelve (periodo, errores). Si las fechas no sirven, se usa "Este mes" y se informa por qué."""
    hoy = timezone.localdate()
    clave = datos.get('periodo', '')
    if clave in dict(PERIODOS):
        return periodo_predefinido(clave, hoy), []

    desde, hasta = _leer_fecha(datos.get('desde')), _leer_fecha(datos.get('hasta'))
    if not desde and not hasta:
        return periodo_predefinido('mes', hoy), []

    errores = []
    if desde and desde > hoy or hasta and hasta > hoy:
        errores.append("Las fechas no pueden ser futuras.")
    elif desde and hasta and desde > hasta:
        errores.append("La fecha de inicio no puede ser posterior a la fecha de término.")
    if errores:
        return periodo_predefinido('mes', hoy), errores
    return Periodo(desde or hasta, hasta or hoy), []


# --- ventas ---

def ventas_vigentes():
    """Ventas confirmadas de todos los canales, sin las anuladas."""
    return Venta.objects.filter(anulada_en__isnull=True).exclude(datos_envio__estado='Anulada')


def ventas_del_periodo(periodo):
    return ventas_vigentes().filter(fecha__gte=periodo.inicio, fecha__lt=periodo.fin)


def totales_ventas(periodo):
    datos = ventas_del_periodo(periodo).aggregate(total=Sum('total'), envio=Sum('envio'), cantidad=Count('id'))
    total, cantidad = datos['total'] or 0, datos['cantidad']
    return {
        **bruto_y_neto(total),
        'envio': datos['envio'] or 0,
        'cantidad': cantidad,
        'ticket_promedio': round(total / cantidad) if cantidad else 0,
    }


def _desglose(ventas, campo, opciones):
    """Monto y número de ventas por cada opción de `campo`, incluidas las que no tienen ventas."""
    filas = {fila[campo]: fila for fila in ventas.values(campo).annotate(total=Sum('total'), cantidad=Count('id'))}
    total = sum(fila['total'] for fila in filas.values())
    if '' in filas:  # ventas antiguas sin el dato registrado
        opciones = [*opciones, ('', 'Sin registrar')]
    resultado = []
    for clave, nombre in opciones:
        fila = filas.get(clave, {'total': 0, 'cantidad': 0})
        resultado.append({'clave': clave, 'nombre': nombre, 'cantidad': fila['cantidad'], 'total': fila['total'],
                          'neto': neto(fila['total']), 'porcentaje': porcentaje(fila['total'], total) or 0})
    return resultado


def ventas_por_canal(periodo):
    return _desglose(ventas_del_periodo(periodo), 'canal', Venta.CANALES)


def ventas_por_medio_de_pago(periodo):
    return _desglose(ventas_del_periodo(periodo), 'metodo_pago', Venta.METODOS_PAGO)


def _etiqueta_mes(dia):
    return f"{MESES[dia.month - 1]} {dia:%y}"


def serie_ventas(periodo):
    """Montos vendidos por canal, por día (periodos cortos) o por mes, para el gráfico de ventas."""
    if periodo.por_dia:
        tramos = [periodo.desde + timedelta(days=i) for i in range(periodo.dias)]
        etiquetas = [f"{dia:%d/%m}" for dia in tramos]
        tramo_de = lambda dia: dia
    else:
        tramos, mes = [], periodo.desde.replace(day=1)
        while mes <= periodo.hasta:
            tramos.append(mes)
            mes += relativedelta(months=1)
        etiquetas = [_etiqueta_mes(mes) for mes in tramos]
        tramo_de = lambda dia: dia.replace(day=1)

    posicion = {tramo: i for i, tramo in enumerate(tramos)}
    series = {canal: [0] * len(tramos) for canal, _ in Venta.CANALES}
    for fecha, canal, total in ventas_del_periodo(periodo).values_list('fecha', 'canal', 'total'):
        series[canal][posicion[tramo_de(timezone.localtime(fecha).date())]] += total
    totales = [sum(valores) for valores in zip(*series.values())]
    return {
        'por_dia': periodo.por_dia,
        'etiquetas': etiquetas,
        'series': [{'clave': canal, 'nombre': nombre, 'datos': series[canal]} for canal, nombre in Venta.CANALES],
        'totales': totales,
        'filas': [{'etiqueta': etiqueta, 'valores': [series[canal][i] for canal, _ in Venta.CANALES],
                   'total': totales[i]} for i, etiqueta in enumerate(etiquetas)],
    }


def ultimos_12_meses(hoy=None):
    hoy = hoy or timezone.localdate()
    return Periodo(hoy.replace(day=1) - relativedelta(months=11), hoy)


# --- ganancia ---

def _detalles_vendidos(periodo):
    return ProductoVenta.objects.filter(venta__in=ventas_del_periodo(periodo))


def ganancia(periodo):
    """Ganancia de los productos vendidos (sin el envío), en bruto y en neto, y el margen sobre la venta neta."""
    detalles = _detalles_vendidos(periodo)
    con_costo = detalles.filter(costo_unitario__isnull=False).aggregate(
        ventas=Sum(F('cantidad') * F('precio_unitario')),
        costos=Sum(F('cantidad') * F('costo_unitario')),
    )
    ventas, costos = con_costo['ventas'] or 0, con_costo['costos'] or 0
    ventas_netas, costos_netos = neto(ventas), neto(costos)
    sin_costo = detalles.filter(costo_unitario__isnull=True)
    return {
        'ventas': bruto_y_neto(ventas),
        'costos': bruto_y_neto(costos),
        'ganancia': {'bruto': ventas - costos, 'neto': ventas_netas - costos_netos},
        'margen': porcentaje(ventas_netas - costos_netos, ventas_netas),
        'detalles_sin_costo': sin_costo.count(),
        'productos_sin_costo': list(
            sin_costo.values_list('producto__nombre', flat=True).distinct().order_by('producto__nombre')
        ),
    }


def ganancia_por_categoria(periodo):
    filas = (
        _detalles_vendidos(periodo).filter(costo_unitario__isnull=False)
        .values(categoria=F('producto__categoria__nombre'))
        .annotate(ventas=Sum(F('cantidad') * F('precio_unitario')), costos=Sum(F('cantidad') * F('costo_unitario')),
                  unidades=Sum('cantidad'))
    )
    resultado = []
    for fila in filas:
        ventas_netas, costos_netos = neto(fila['ventas']), neto(fila['costos'])
        resultado.append({
            'categoria': fila['categoria'], 'unidades': fila['unidades'],
            'ventas_netas': ventas_netas, 'costos_netos': costos_netos, 'ganancia_neta': ventas_netas - costos_netos,
            'margen': porcentaje(ventas_netas - costos_netos, ventas_netas),
        })
    return sorted(resultado, key=lambda fila: -fila['ganancia_neta'])


# --- productos ---

def mas_vendidos(periodo, limite=10):
    filas = (
        _detalles_vendidos(periodo)
        .values('producto_id', nombre=F('producto__nombre'), categoria=F('producto__categoria__nombre'))
        .annotate(unidades=Sum('cantidad'), total=Sum(F('cantidad') * F('precio_unitario')))
        .order_by('-unidades', '-total', 'nombre')[:limite]
    )
    return [{**fila, 'neto': neto(fila['total'])} for fila in filas]


def stock_critico():
    """Productos vigentes con stock igual o menor a su stock crítico, los agotados primero."""
    return (Producto.objects.filter(stock__lte=F('stock_critico')).select_related('categoria', 'plataforma')
            .order_by('stock', 'nombre'))


# --- caja, retiros y compras ---

def caja(periodo):
    """Dinero recibido por medio de pago y movimientos de la caja de la tienda física. El efectivo de la caja
    del periodo = ventas en efectivo + ingresos de dinero − retiros."""
    movimientos = MovimientoCaja.objects.filter(fecha__gte=periodo.inicio, fecha__lt=periodo.fin)
    sumas = movimientos.aggregate(
        ingresos=Sum('monto', filter=Q(tipo=MovimientoCaja.INGRESO)),
        retiros=Sum('monto', filter=Q(tipo=MovimientoCaja.RETIRO)),
    )
    medios = ventas_por_medio_de_pago(periodo)
    efectivo = next(medio['total'] for medio in medios if medio['clave'] == Venta.PAGO_EFECTIVO)
    ingresos, retiros = sumas['ingresos'] or 0, sumas['retiros'] or 0
    return {
        'medios': medios,
        'ventas_efectivo': efectivo,
        'ingresos': ingresos,
        'retiros': retiros,
        'saldo_efectivo': efectivo + ingresos - retiros,
        'movimientos': movimientos.order_by('-fecha'),
    }


def compras(periodo):
    del_periodo = Compra.objects.filter(fecha__gte=periodo.desde, fecha__lte=periodo.hasta)
    total = del_periodo.aggregate(total=Sum('total'))['total'] or 0
    return {
        **bruto_y_neto(total),
        'cantidad': del_periodo.count(),
        'pendientes': del_periodo.filter(estado=Compra.PENDIENTE).count(),
        'por_proveedor': list(
            del_periodo.values(nombre=F('proveedor__nombre')).annotate(total=Sum('total'), cantidad=Count('id'))
            .order_by('-total')
        ),
        'compras': del_periodo.select_related('proveedor'),
    }


# --- KPI (Tabla 13 del informe) ---

META_KPI01 = 16
META_KPI03 = 20
META_KPI04 = 30
META_KPI10 = 100


def mes_de(dia):
    """Periodo del mes calendario de `dia`, completo (aunque no haya terminado)."""
    inicio = dia.replace(day=1)
    return Periodo(inicio, inicio + relativedelta(months=1, days=-1), 'mes')


def nombre_mes(periodo):
    return f"{MESES_LARGOS[periodo.desde.month - 1]} {periodo.desde.year}"


def kpi01(mes, linea_base):
    """Ventas web adicionales del mes: ventas web confirmadas del mes − ventas web del último mes en la plataforma
    anterior. Sin línea base solo se informan las ventas web."""
    ventas_web = ventas_del_periodo(mes).filter(canal=Venta.CANAL_WEB).count()
    adicionales = None if linea_base is None else ventas_web - linea_base
    return {'ventas_web': ventas_web, 'linea_base': linea_base, 'valor': adicionales, 'meta': META_KPI01,
            'cumple': None if adicionales is None else adicionales >= META_KPI01}


def kpi03(hasta):
    """Tasa de recompra: clientes con dos o más compras / clientes con al menos una compra en los 6 meses que
    terminan en `hasta` (ventana móvil). Solo cuentan las ventas asociadas a un cliente con cuenta."""
    ventana = Periodo(hasta - relativedelta(months=6) + timedelta(days=1), hasta)
    compras_por_cliente = (ventas_del_periodo(ventana).filter(usuario__isnull=False)
                           .values('usuario').annotate(compras=Count('id')).values_list('compras', flat=True))
    clientes = len(compras_por_cliente)
    recurrentes = sum(1 for compras_cliente in compras_por_cliente if compras_cliente >= 2)
    tasa = porcentaje(recurrentes, clientes)
    return {'clientes': clientes, 'recurrentes': recurrentes, 'valor': tasa, 'meta': META_KPI03,
            'cumple': None if tasa is None else tasa >= META_KPI03, 'ventana': ventana}


def kpi04(mes):
    """Conversión del carrito: carritos con pago confirmado / carritos con al menos un producto, de los carritos
    creados en el mes. Al pagarse, lo comprado sale del carrito, así que un carrito pagado cuenta como carrito con
    productos aunque hoy esté vacío."""
    carritos = Carrito.todos.filter(creado_en__gte=mes.inicio, creado_en__lt=mes.fin)
    pagados = carritos.filter(convertido_en__isnull=False).count()
    sin_pagar_con_productos = carritos.filter(convertido_en__isnull=True, items__isnull=False).distinct().count()
    con_productos = pagados + sin_pagar_con_productos
    tasa = porcentaje(pagados, con_productos)
    return {'pagados': pagados, 'con_productos': con_productos, 'valor': tasa, 'meta': META_KPI04,
            'cumple': None if tasa is None else tasa >= META_KPI04}


def kpi05(mes):
    """Tasa de clics en productos recomendados del mes (solo clientes que autorizaron sus datos de navegación).
    Su meta se fija sobre la línea base de los dos primeros meses de operación."""
    datos = tasa_de_clics(desde=mes.inicio, hasta=mes.fin)
    return {**datos, 'valor': datos['tasa'], 'meta': None, 'cumple': None}


def kpi10():
    completos, total = cobertura_atributos()
    valor = porcentaje(completos, total)
    return {'completos': completos, 'total': total, 'valor': valor, 'meta': META_KPI10,
            'cumple': None if valor is None else completos == total}


def tablero_kpi(linea_base_kpi01, hoy=None):
    """Los cinco KPI que se calculan con datos de la plataforma, para el mes en curso."""
    hoy = hoy or timezone.localdate()
    mes = mes_de(hoy)
    return {
        'mes': mes,
        'kpi01': kpi01(mes, linea_base_kpi01),
        'kpi03': kpi03(hoy),
        'kpi04': kpi04(mes),
        'kpi05': kpi05(mes),
        'kpi10': kpi10(),
    }


def historial_kpi(linea_base_kpi01, meses=6, hoy=None):
    """Valor mensual de KPI-01, KPI-03, KPI-04 y KPI-05 en los últimos `meses` meses (revisión mensual).
    KPI-03 se mide al cierre de cada mes (o hoy, en el mes en curso)."""
    hoy = hoy or timezone.localdate()
    filas = []
    for atras in range(meses):
        mes = mes_de(hoy.replace(day=1) - relativedelta(months=atras))
        filas.append({
            'mes': mes,
            'nombre': nombre_mes(mes),
            'en_curso': atras == 0,
            'kpi01': kpi01(mes, linea_base_kpi01),
            'kpi03': kpi03(min(mes.hasta, hoy)),
            'kpi04': kpi04(mes),
            'kpi05': kpi05(mes),
        })
    return filas
