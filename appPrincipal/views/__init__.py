"""Vistas de Akaispace, separadas por funcionalidad.

Las del cliente están en este paquete y las del panel de administración en views/panel/.
Todas se reexportan aquí para que urls.py pueda usarlas como views.<nombre>.
"""
from .carrito import (
    actualizar_cantidad_carrito, agregar_al_carrito, eliminar_del_carrito, guardar_datos_envio, ver_carrito,
)
from .catalogo import home, producto_detalle, productos_menu, productos_por_categoria
from .compras import marcar_recibido, ver_compras, ver_detalle_compra
from .cuentas import login, logout, obtener_ciudades, register
from .devoluciones import crear_devolucion, listar_devoluciones, ver_detalle_devolucion
from .favoritos import agregar_favorito, eliminar_favorito, eliminar_favoritos_seleccionados, lista_favoritos
from .opiniones import enviar_opinion, lista_opiniones
from .pago import compra_exitosa, seleccionar_pago, ver_boleta
from .perfil import cambiar_contraseña, editar_perfil, perfil
from .reclamos import crear_reclamo, lista_reclamos, ver_detalle_reclamo
from .panel import (
    admin_dashboard, get_dashboard_counts,
    admin_devoluciones, detalle_devolucion, responder_devolucion,
    admin_productos, agregar_producto, detalle_producto, editar_producto, eliminar_producto,
    admin_reclamos, detalle_reclamo, responder_reclamo,
    admin_usuarios, buscar_usuarios, crear_usuario, detalle_usuario, eliminar_usuario,
    admin_ventas, anular_venta, detalle_venta, modificar_venta,
    admin_portada, cambiar_estado_destacado, crear_destacado, editar_destacado, eliminar_destacado,
)
