from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.html import format_html
from .models import Usuario, Producto, Venta, Reclamo, Opinion, PagoWebpay

# Configuración del admin de Django (/admin/), disponible solo con DEBUG=True (ver Akaispace/urls.py).
# No es el panel de la tienda: ese es /admin-panel/ (appPrincipal/views/panel/).
# Las tablas "ItemCarritoProducto" y "Carrito" no aparecen en el panel de admin ya que no tiene mucho sentido que las pueda ver

class ProductoAdmin(admin.ModelAdmin):
    list_display = ("codigo_de_barra", "nombre", "precio", "stock", "imagen_display", "categoria", "genero", "is_deleted")
    search_fields = ("nombre", "codigo_de_barra")
    list_editable = ("stock", "categoria", "genero")
    list_filter=("categoria", "genero", "is_deleted")
    list_per_page = 20

    # muestra también los productos eliminados (borrado lógico) para poder revisarlos o restaurarlos
    def get_queryset(self, request):
        return Producto.todos.all()

    # el borrado de productos es lógico (no elimina filas), así que no hace falta revisar
    # las relaciones protegidas (ventas, devoluciones) antes de confirmar
    def get_deleted_objects(self, objs, request):
        return [str(obj) for obj in objs], {}, set(), []

    @admin.display(description='Imagen Principal')
    def imagen_display(self, obj):
        if obj.imagen_principal:
            return format_html('<img src="{}" style="height: 50px;">', obj.imagen_principal.url)
        return 'Sin imagen'

class UsuarioCreationForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ("email", "nombre")


class UsuarioChangeForm(UserChangeForm):
    class Meta:
        model = Usuario
        fields = "__all__"


class UsuarioAdmin(UserAdmin):
    form = UsuarioChangeForm
    add_form = UsuarioCreationForm
    list_display = ("nombre", "email", "rut", "telefono", "ciudad", "region", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active", "is_deleted")
    search_fields = ("nombre", "email", "rut", "telefono")
    ordering = ("email",)
    list_per_page = 20

    # UserAdmin usa "username"; este modelo inicia sesión con el email
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Datos personales", {"fields": ("nombre", "rut", "telefono", "direccion", "region", "ciudad")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Eliminación", {"fields": ("is_deleted", "deleted_at")}),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "nombre", "password1", "password2", "is_staff"),
        }),
    )

class VentaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "total", "estado_envio", "fecha", "metodo_envio", "direccion_envio", "productos_comprados")
    list_filter = ("datos_envio__estado", "fecha",)
    list_per_page = 20

    def productos_comprados(self, obj):
        productos = obj.producto_venta.all()
        return ", ".join([f"{pv.producto.nombre} (x{pv.cantidad})" for pv in productos])

    productos_comprados.short_description = "Productos Comprados"

    @admin.display(description="Estado", ordering="datos_envio__estado")
    def estado_envio(self, obj):
        envio = getattr(obj, 'datos_envio', None)
        return envio.estado if envio else '-'



class ReclamoAdmin(admin.ModelAdmin):
    list_display=("usuario", "estado","asunto", "descripcion", "fecha", "respuesta")
    list_filter=("estado", "fecha",)
    list_editable = ("estado", "respuesta")
    list_per_page=20

admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(Producto, ProductoAdmin)
admin.site.register(Venta, VentaAdmin)
admin.site.register(Reclamo, ReclamoAdmin)
admin.site.register(Opinion)

# historial de intentos de pago con Webpay (HU-05), solo lectura: lo escribe el flujo de pago
@admin.register(PagoWebpay)
class PagoWebpayAdmin(admin.ModelAdmin):
    list_display = ("orden_compra", "usuario", "monto", "estado", "tipo_pago", "venta", "creado")
    list_filter = ("estado", "tipo_pago")
    search_fields = ("orden_compra", "usuario__email", "codigo_autorizacion")
    readonly_fields = [campo.name for campo in PagoWebpay._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
