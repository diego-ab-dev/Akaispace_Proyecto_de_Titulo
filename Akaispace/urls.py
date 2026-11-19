"""Rutas del sitio."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from appPrincipal import views


# Comprobación de estado del balanceador. No usa la base de datos: si RDS fallara, el autoescalado
# reemplazaría instancias sanas una y otra vez.
def health(request):
    return HttpResponse('ok')


urlpatterns = [
    path('health/', health),
    # Cliente
     
    # Home
    path('', views.home, name="home"),
    # Menú
    path('menu/', views.productos_menu, name='productos_menu'),
    path('producto/<int:producto_id>/', views.producto_detalle, name='producto_detalle'),
    path('recomendacion/<int:recomendacion_id>/', views.clic_recomendacion, name='clic_recomendacion'),
    path('productos/<int:categoria_id>/', views.productos_por_categoria, name='productos_por_categoria'),
    path('productos/<int:categoria_id>/<slug:plataforma>/', views.productos_por_categoria,
         name='productos_por_categoria_y_plataforma'),
    # Login y registro
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),
    # Inicio de sesión con Google
    path('accounts/', include('allauth.urls')),
    path('obtener_ciudades/', views.obtener_ciudades, name='obtener_ciudades'),
    # Recuperar contraseña
    path('recuperar-contrasena/', views.recuperar_contraseña, name='recuperar_contraseña'),
    path('recuperar-contrasena/enviado/', views.recuperar_contraseña_enviado, name='recuperar_contraseña_enviado'),
    path('recuperar-contrasena/listo/', views.restablecer_contraseña_listo, name='restablecer_contraseña_listo'),
    path('recuperar-contrasena/<uidb64>/<token>/', views.restablecer_contraseña, name='restablecer_contraseña'),
    # Legal
    path('politica-de-privacidad/', views.politica_privacidad, name='politica_privacidad'),
    path('terminos-y-condiciones/', views.terminos_condiciones, name='terminos_condiciones'),
    # Perfil
    path('perfil/', views.perfil, name='perfil'),
    path('editar/', views.editar_perfil, name='editar'),
    path('perfil/datos-navegacion/', views.datos_navegacion, name='datos_navegacion'),
    path('perfil/eliminar-cuenta/', views.eliminar_cuenta, name='eliminar_cuenta'),
    path('cuenta-eliminada/', views.cuenta_eliminada, name='cuenta_eliminada'),
    path('cambiar/', views.cambiar_contraseña, name='cambiar'),
    # Compras
    path('compras/', views.ver_compras, name='ver_compras'),
    path('compra/<int:compra_id>/detalle/', views.ver_detalle_compra, name='ver_detalle'),
    path('marcar-recibido/<int:compra_id>/', views.marcar_recibido, name='marcar_recibido'),
    # Opiniones
    path('opinion/enviar/<int:producto_id>/', views.enviar_opinion, name='enviar_opinion'),
    path('perfil/opiniones/',views.lista_opiniones, name='lista_opiniones'),
    # Reclamos
    path('crear_reclamo/<int:compra_id>/', views.crear_reclamo, name='crear_reclamo'),
    path('reclamos/', views.lista_reclamos, name='lista_reclamos'),
    path('reclamos/<int:reclamo_id>/detalle/', views.ver_detalle_reclamo, name='ver_detalle_reclamo'),
    # Devoluciones
    path('devolucion/crear/<int:compra_id>/<int:producto_id>/', views.crear_devolucion, name='crear_devolucion'),
    path('perfil/devoluciones/',views.listar_devoluciones, name='lista_devoluciones'),
    path('devoluciones/<int:devolucion_id>/detalle/', views.ver_detalle_devolucion, name='ver_detalle_devolucion'),
    # Carrito
    path('ver_carrito/', views.ver_carrito, name='ver_carrito'),
    path('agregar/<int:producto_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('eliminar/<int:producto_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('carrito/eliminar-seleccionados/', views.eliminar_seleccionados_carrito, name='eliminar_seleccionados_carrito'),
    path('carrito/vaciar/', views.vaciar_carrito, name='vaciar_carrito'),
    path('actualizar-cantidad/', views.actualizar_cantidad_carrito, name='actualizar_cantidad_carrito'),
    path('guardar_datos_envio/', views.guardar_datos_envio, name='guardar_datos_envio'),
    # Favoritos
    path('favorites/', views.lista_favoritos, name='lista_favorito'),
    path('agregar_favorito/<int:producto_id>/', views.agregar_favorito, name='agregar_favorito'),
    path('remove_favorito/<int:producto_id>/', views.eliminar_favorito, name='eliminar_favorito'),
    path('eliminar_favoritos_seleccionados/', views.eliminar_favoritos_seleccionados, name='eliminar_favoritos_seleccionados'),
    # Pago
    path('seleccionar-pago/', views.seleccionar_pago, name='seleccionar_pago'),
    path('pago/webpay/retorno/', views.webpay_retorno, name='webpay_retorno'),
    path('pago/<int:pago_id>/resultado/', views.resultado_pago, name='resultado_pago'),
    path('comprobante/<int:venta_id>/', views.ver_comprobante, name='ver_comprobante'),

    # Panel de administración

    # Principal
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/reportes/', views.admin_reportes, name='admin_reportes'),
    path('admin-panel/reportes/caja/', views.registrar_movimiento_caja, name='registrar_movimiento_caja'),
    # Usuarios
    path('admin-panel/usuarios/', views.admin_usuarios, name='admin_usuarios'),
    path('admin-panel/usuarios/buscar/', views.buscar_usuarios, name='buscar_usuarios'),
    path('admin-panel/usuarios/eliminar/<int:usuario_id>/',views.eliminar_usuario, name='eliminar_usuario'),
    path('admin-panel/usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('admin-panel/usuarios/detalle/<int:usuario_id>/', views.detalle_usuario, name='detalle_usuario'),
    # Productos
    path('admin-panel/productos/', views.admin_productos, name='admin_productos'),
    path('admin-panel/productos/agregar/', views.agregar_producto, name='agregar_producto'),
    path('admin-panel/productos/eliminar/<int:producto_id>/', views.eliminar_producto, name='eliminar_producto'),
    path('admin-panel/productos/editar/<int:producto_id>/', views.editar_producto, name='editar_producto'),
    path('admin-panel/productos/detalle/<int:producto_id>/', views.detalle_producto, name='detalle_producto'),
    # Ventas
    path('admin-panel/ventas/', views.admin_ventas, name='admin_ventas'),
    path('admin-panel/ventas/registrar/', views.registrar_venta, name='registrar_venta'),
    path('admin-panel/ventas/buscar-productos/', views.buscar_productos_venta, name='buscar_productos_venta'),
    path('admin-panel/ventas/detalle/<int:venta_id>/', views.detalle_venta, name='detalle_venta'),
    path('admin-panel/ventas/modificar/<int:venta_id>/', views.modificar_venta, name='modificar_venta'),
    path('ventas/anular/<int:venta_id>/', views.anular_venta, name='anular_venta'),

    path('admin-panel/compras/', views.admin_compras, name='admin_compras'),
    path('admin-panel/compras/registrar/', views.registrar_compra, name='registrar_compra'),
    path('admin-panel/compras/<int:compra_id>/', views.detalle_compra, name='detalle_compra'),
    path('admin-panel/compras/<int:compra_id>/recibir/', views.recibir_compra, name='recibir_compra'),
    path('admin-panel/compras/<int:compra_id>/eliminar/', views.eliminar_compra, name='eliminar_compra'),
    # Reclamos
    path('admin-panel/reclamos/', views.admin_reclamos, name='admin_reclamos'),
    path('admin-panel/reclamos/responder/<int:reclamo_id>/', views.responder_reclamo, name='responder_reclamo'),
    path('administracion/reclamos/detalle/<int:reclamo_id>/', views.detalle_reclamo, name='detalle_reclamo'),
    # Devoluciones
    path('admin-panel/devoluciones/', views.admin_devoluciones, name='admin_devoluciones'),
    path('admin-panel/devoluciones/responder/<int:devolucion_id>/', views.responder_devolucion, name='responder_devolucion'),
    path('admin-panel/devoluciones/recepcion/<int:devolucion_id>/', views.registrar_recepcion_devolucion,
         name='registrar_recepcion_devolucion'),
    path('admin-panel/devoluciones/reembolso-manual/<int:devolucion_id>/', views.registrar_reembolso_manual,
         name='registrar_reembolso_manual'),
    path('devolucion/detalle/<int:devolucion_id>/', views.detalle_devolucion, name='detalle_devolucion'),
    # Portada
    path('admin-panel/portada/', views.admin_portada, name='admin_portada'),
    path('admin-panel/portada/nuevo/', views.crear_destacado, name='crear_destacado'),
    path('admin-panel/portada/<int:destacado_id>/editar/', views.editar_destacado, name='editar_destacado'),
    path('admin-panel/portada/<int:destacado_id>/estado/', views.cambiar_estado_destacado, name='cambiar_estado_destacado'),
    path('admin-panel/portada/<int:destacado_id>/eliminar/', views.eliminar_destacado, name='eliminar_destacado'),
    # Configuración
    path('admin-panel/configuracion/', views.admin_configuracion, name='admin_configuracion'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns.append(path('admin/', admin.site.urls))
