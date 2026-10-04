"""Vistas del panel de administración propio de Akaispace (no confundir con el admin de Django)."""
from .dashboard import admin_dashboard, get_dashboard_counts
from .portada import (
    admin_portada, cambiar_estado_destacado, crear_destacado, editar_destacado, eliminar_destacado,
)
from .devoluciones import admin_devoluciones, detalle_devolucion, responder_devolucion
from .productos import admin_productos, agregar_producto, detalle_producto, editar_producto, eliminar_producto
from .reclamos import admin_reclamos, detalle_reclamo, responder_reclamo
from .usuarios import admin_usuarios, buscar_usuarios, crear_usuario, detalle_usuario, eliminar_usuario
from .ventas import admin_ventas, anular_venta, detalle_venta, modificar_venta

