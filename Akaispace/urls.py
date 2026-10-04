"""
URL configuration for Akaispace project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from appPrincipal.views import home,ver_boleta,ver_detalle_compra, ver_detalle_reclamo, login, register, productos_menu, producto_detalle, logout, productos_por_categoria, perfil, editar_perfil, obtener_ciudades, cambiar_contraseña,  agregar_al_carrito, eliminar_del_carrito, actualizar_cantidad_carrito, ver_carrito, lista_favoritos, agregar_favorito, eliminar_favorito, ver_compras, lista_opiniones, crear_reclamo, lista_reclamos, seleccionar_pago, compra_exitosa, admin_dashboard, admin_productos, admin_usuarios, editar_producto, agregar_producto, buscar_usuarios, eliminar_producto, eliminar_usuario, admin_devoluciones, admin_reclamos, responder_reclamo, detalle_reclamo , admin_ventas, crear_usuario, get_dashboard_counts, admin_cambiar_estado_venta, enviar_opinion, guardar_datos_envio, eliminar_favoritos_seleccionados, responder_devolucion, detalle_devolucion, crear_devolucion, listar_devoluciones, ver_detalle_devolucion, detalle_producto, detalle_usuario, detalle_venta, modificar_venta, marcar_recibido, anular_venta

urlpatterns = [
    # URLS CLIENTE
     
    # home
    path('admin/', admin.site.urls),
    path('', home, name="home"),
    # menu
    path('menu/', productos_menu, name='productos_menu'),
    path('producto/<int:producto_id>/', producto_detalle, name='producto_detalle'),
    path('productos/<str:categoria>/', productos_por_categoria, name='productos_por_categoria'),
    # login y register
    path('login/', login, name='login'),
    path('register/', register, name='register'),
    path('logout/', logout, name='logout'),
    path('obtener_ciudades/', obtener_ciudades, name='obtener_ciudades'),
    # perfil cliente
    path('perfil/', perfil, name='perfil'),
    path('editar/', editar_perfil, name='editar'),
    path('cambiar/', cambiar_contraseña, name='cambiar'),
    # compras de cliente
    path('compras/', ver_compras, name='ver_compras'),
    path('compra/<int:compra_id>/detalle/', ver_detalle_compra, name='ver_detalle'),
    path('marcar-recibido/<int:compra_id>/', marcar_recibido, name='marcar_recibido'),
    # opinion
    path('opinion/enviar/<int:producto_id>/', enviar_opinion, name='enviar_opinion'),
    path('perfil/opiniones/',lista_opiniones, name='lista_opiniones'),
    # reclamo
    path('crear_reclamo/<int:compra_id>/', crear_reclamo, name='crear_reclamo'),
    path('reclamos/', lista_reclamos, name='lista_reclamos'),
    path('reclamos/<int:reclamo_id>/detalle/', ver_detalle_reclamo, name='ver_detalle_reclamo'),
    # devolucion
    path('devolucion/crear/<int:compra_id>/<int:producto_id>/', crear_devolucion, name='crear_devolucion'),
    path('perfil/devoluciones/',listar_devoluciones, name='lista_devoluciones'),
    path('devoluciones/<int:devolucion_id>/detalle/', ver_detalle_devolucion, name='ver_detalle_devolucion'),
    # carrito
    path('ver_carrito/', ver_carrito, name='ver_carrito'),
    path('agregar/<int:producto_id>/', agregar_al_carrito, name='agregar_al_carrito'),
    path('eliminar/<int:item_id>/', eliminar_del_carrito, name='eliminar_del_carrito'),
    path('actualizar-cantidad/', actualizar_cantidad_carrito, name='actualizar_cantidad_carrito'),
    path('guardar_datos_envio/', guardar_datos_envio, name='guardar_datos_envio'),
    # favoritos
    path('favorites/', lista_favoritos, name='lista_favorito'),
    path('agregar_favorito/<int:producto_id>/', agregar_favorito, name='agregar_favorito'),
    path('remove_favorito/<int:item_id>/', eliminar_favorito, name='eliminar_favorito'),
    path('eliminar_favoritos_seleccionados/', eliminar_favoritos_seleccionados, name='eliminar_favoritos_seleccionados'),
    # pago - compra
    path('seleccionar-pago/', seleccionar_pago, name='seleccionar_pago'),
    path('compra-exitosa/', compra_exitosa, name='compra_exitosa'),
    path('boleta/<int:venta_id>/', ver_boleta, name='ver_boleta'),


    # URLS ADMIN

    # principal
    path('admin-panel/', admin_dashboard, name='admin_dashboard'),
    path('api/dashboard-counts/', get_dashboard_counts, name='get_dashboard_counts'),
    # usuarios
    path('admin-panel/usuarios/', admin_usuarios, name='admin_usuarios'),
    path('admin-panel/usuarios/buscar/', buscar_usuarios, name='buscar_usuarios'),
    path('admin-panel/usuarios/eliminar/<int:usuario_id>/',eliminar_usuario, name='eliminar_usuario'),
    path('admin-panel/usuarios/crear/', crear_usuario, name='crear_usuario'),
    path('admin-panel/usuarios/detalle/<int:usuario_id>/', detalle_usuario, name='detalle_usuario'),
    # productos
    path('admin-panel/productos/', admin_productos, name='admin_productos'),
    path('admin-panel/productos/agregar/', agregar_producto, name='agregar_producto'),
    path('admin-panel/productos/eliminar/<int:producto_id>/', eliminar_producto, name='eliminar_producto'),
    path('admin-panel/productos/editar/<int:producto_id>/', editar_producto, name='editar_producto'),
    path('admin-panel/productos/detalle/<int:producto_id>/', detalle_producto, name='detalle_producto'),
    # ventas
    path('admin-panel/ventas/', admin_ventas, name='admin_ventas'),
    path('ventas/cambiar-estado/<int:venta_id>/', admin_cambiar_estado_venta, name='admin_cambiar_estado_venta'),
    path('admin-panel/ventas/detalle/<int:venta_id>/', detalle_venta, name='detalle_venta'),
    path('admin-panel/ventas/modificar/<int:venta_id>/', modificar_venta, name='modificar_venta'),
    path('ventas/anular/<int:venta_id>/', anular_venta, name='anular_venta'),
    # reclamo
    path('admin-panel/reclamos/', admin_reclamos, name='admin_reclamos'),
    path('admin-panel/reclamos/responder/<int:reclamo_id>/', responder_reclamo, name='responder_reclamo'),
    path('administracion/reclamos/detalle/<int:reclamo_id>/', detalle_reclamo, name='detalle_reclamo'),
    # devolucion
    path('admin-panel/devoluciones/', admin_devoluciones, name='admin_devoluciones'),
    path('admin-panel/devoluciones/responder/<int:devolucion_id>/', responder_devolucion, name='responder_devolucion'),
    path('devolucion/detalle/<int:devolucion_id>/', detalle_devolucion, name='detalle_devolucion'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
