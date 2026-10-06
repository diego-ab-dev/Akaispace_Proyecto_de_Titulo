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
from appPrincipal import views

urlpatterns = [
    # URLS CLIENTE
     
    # home
    path('', views.home, name="home"),
    # menu
    path('menu/', views.productos_menu, name='productos_menu'),
    path('producto/<int:producto_id>/', views.producto_detalle, name='producto_detalle'),
    path('productos/<str:categoria>/', views.productos_por_categoria, name='productos_por_categoria'),
    # login y register
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),
    path('obtener_ciudades/', views.obtener_ciudades, name='obtener_ciudades'),
    # legal
    path('politica-de-privacidad/', views.politica_privacidad, name='politica_privacidad'),
    # perfil cliente
    path('perfil/', views.perfil, name='perfil'),
    path('editar/', views.editar_perfil, name='editar'),
    path('cambiar/', views.cambiar_contraseña, name='cambiar'),
    # compras de cliente
    path('compras/', views.ver_compras, name='ver_compras'),
    path('compra/<int:compra_id>/detalle/', views.ver_detalle_compra, name='ver_detalle'),
    path('marcar-recibido/<int:compra_id>/', views.marcar_recibido, name='marcar_recibido'),
    # opinion
    path('opinion/enviar/<int:producto_id>/', views.enviar_opinion, name='enviar_opinion'),
    path('perfil/opiniones/',views.lista_opiniones, name='lista_opiniones'),
    # reclamo
    path('crear_reclamo/<int:compra_id>/', views.crear_reclamo, name='crear_reclamo'),
    path('reclamos/', views.lista_reclamos, name='lista_reclamos'),
    path('reclamos/<int:reclamo_id>/detalle/', views.ver_detalle_reclamo, name='ver_detalle_reclamo'),
    # devolucion
    path('devolucion/crear/<int:compra_id>/<int:producto_id>/', views.crear_devolucion, name='crear_devolucion'),
    path('perfil/devoluciones/',views.listar_devoluciones, name='lista_devoluciones'),
    path('devoluciones/<int:devolucion_id>/detalle/', views.ver_detalle_devolucion, name='ver_detalle_devolucion'),
    # carrito
    path('ver_carrito/', views.ver_carrito, name='ver_carrito'),
    path('agregar/<int:producto_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('eliminar/<int:item_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('actualizar-cantidad/', views.actualizar_cantidad_carrito, name='actualizar_cantidad_carrito'),
    path('guardar_datos_envio/', views.guardar_datos_envio, name='guardar_datos_envio'),
    # favoritos
    path('favorites/', views.lista_favoritos, name='lista_favorito'),
    path('agregar_favorito/<int:producto_id>/', views.agregar_favorito, name='agregar_favorito'),
    path('remove_favorito/<int:item_id>/', views.eliminar_favorito, name='eliminar_favorito'),
    path('eliminar_favoritos_seleccionados/', views.eliminar_favoritos_seleccionados, name='eliminar_favoritos_seleccionados'),
    # pago - compra
    path('seleccionar-pago/', views.seleccionar_pago, name='seleccionar_pago'),
    path('pago/webpay/retorno/', views.webpay_retorno, name='webpay_retorno'),
    path('pago/<int:pago_id>/resultado/', views.resultado_pago, name='resultado_pago'),
    path('boleta/<int:venta_id>/', views.ver_boleta, name='ver_boleta'),


    # URLS ADMIN

    # principal
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('api/dashboard-counts/', views.get_dashboard_counts, name='get_dashboard_counts'),
    # usuarios
    path('admin-panel/usuarios/', views.admin_usuarios, name='admin_usuarios'),
    path('admin-panel/usuarios/buscar/', views.buscar_usuarios, name='buscar_usuarios'),
    path('admin-panel/usuarios/eliminar/<int:usuario_id>/',views.eliminar_usuario, name='eliminar_usuario'),
    path('admin-panel/usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('admin-panel/usuarios/detalle/<int:usuario_id>/', views.detalle_usuario, name='detalle_usuario'),
    # productos
    path('admin-panel/productos/', views.admin_productos, name='admin_productos'),
    path('admin-panel/productos/agregar/', views.agregar_producto, name='agregar_producto'),
    path('admin-panel/productos/eliminar/<int:producto_id>/', views.eliminar_producto, name='eliminar_producto'),
    path('admin-panel/productos/editar/<int:producto_id>/', views.editar_producto, name='editar_producto'),
    path('admin-panel/productos/detalle/<int:producto_id>/', views.detalle_producto, name='detalle_producto'),
    # ventas
    path('admin-panel/ventas/', views.admin_ventas, name='admin_ventas'),
    path('admin-panel/ventas/detalle/<int:venta_id>/', views.detalle_venta, name='detalle_venta'),
    path('admin-panel/ventas/modificar/<int:venta_id>/', views.modificar_venta, name='modificar_venta'),
    path('ventas/anular/<int:venta_id>/', views.anular_venta, name='anular_venta'),
    # reclamo
    path('admin-panel/reclamos/', views.admin_reclamos, name='admin_reclamos'),
    path('admin-panel/reclamos/responder/<int:reclamo_id>/', views.responder_reclamo, name='responder_reclamo'),
    path('administracion/reclamos/detalle/<int:reclamo_id>/', views.detalle_reclamo, name='detalle_reclamo'),
    # devolucion
    path('admin-panel/devoluciones/', views.admin_devoluciones, name='admin_devoluciones'),
    path('admin-panel/devoluciones/responder/<int:devolucion_id>/', views.responder_devolucion, name='responder_devolucion'),
    path('devolucion/detalle/<int:devolucion_id>/', views.detalle_devolucion, name='detalle_devolucion'),
    # portada (carrusel, nuevos lanzamientos y promos del navbar)
    path('admin-panel/portada/', views.admin_portada, name='admin_portada'),
    path('admin-panel/portada/nuevo/', views.crear_destacado, name='crear_destacado'),
    path('admin-panel/portada/<int:destacado_id>/editar/', views.editar_destacado, name='editar_destacado'),
    path('admin-panel/portada/<int:destacado_id>/estado/', views.cambiar_estado_destacado, name='cambiar_estado_destacado'),
    path('admin-panel/portada/<int:destacado_id>/eliminar/', views.eliminar_destacado, name='eliminar_destacado'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# El panel de administración de la tienda es el propio (/admin-panel/). El admin de Django
# queda solo en desarrollo, como herramienta para revisar datos; en producción no existe.
if settings.DEBUG:
    urlpatterns.append(path('admin/', admin.site.urls))
