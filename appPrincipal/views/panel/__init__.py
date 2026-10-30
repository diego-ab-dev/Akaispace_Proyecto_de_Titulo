"""Vistas del panel de administración propio de Akaispace (no confundir con el admin de Django)."""
from .configuracion import admin_configuracion
from .compras import admin_compras, detalle_compra, eliminar_compra, recibir_compra, registrar_compra
from .dashboard import admin_dashboard
from .portada import (
    admin_portada, cambiar_estado_destacado, crear_destacado, editar_destacado, eliminar_destacado,
)
from .devoluciones import admin_devoluciones, detalle_devolucion, responder_devolucion
from .productos import admin_productos, agregar_producto, detalle_producto, editar_producto, eliminar_producto
from .reportes import admin_reportes, registrar_movimiento_caja
from .reclamos import admin_reclamos, detalle_reclamo, responder_reclamo
from .usuarios import admin_usuarios, buscar_usuarios, crear_usuario, detalle_usuario, eliminar_usuario
from .ventas import (
    admin_ventas, anular_venta, buscar_productos_venta, detalle_venta, modificar_venta, registrar_venta,
)

