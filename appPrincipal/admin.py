from django.contrib import admin
from .models import Usuario, Producto, Venta, Reclamo, Opinion

# Edite admin.py para que se reflejen los datos de las tablas en el panel de administracion que ofrece django
# Las tablas "ItemCarritoProducto" y "Carrito" no aparecen en el panel de admin ya que no tiene mucho sentido que las pueda ver

class ProductoAdmin(admin.ModelAdmin):
    list_display = ("codigo_de_barra", "nombre", "precio", "stock", "imagen_display", "categoria", "genero")
    search_fields = ("nombre", "codigo_de_barra")
    list_editable = ("stock", "categoria", "genero")
    list_filter=("categoria", "genero")
    list_per_page = 20

    def imagen_display(self, obj):
        if obj.imagen_principal:
            return obj.imagen_principal.url
        return 'Sin imagen'
    imagen_display.allow_tags = True
    imagen_display.short_description = 'Imagen Principal'

class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "email", "rut", "telefono", "direccion", "ciudad", "region")
    search_fields = ("nombre", "email", "telefono",)
    list_per_page = 20

class VentaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "total", "estado", "fecha", "metodo_envio", "direccion_envio", "productos_comprados")
    list_filter = ("estado", "fecha",)
    list_editable = ("estado",)
    date_hierarchy = "fecha"
    list_per_page = 20

    def productos_comprados(self, obj):
        productos = obj.producto_venta.all()
        return ", ".join([f"{pv.producto.nombre} (x{pv.cantidad})" for pv in productos])

    productos_comprados.short_description = "Productos Comprados"



class ReclamoAdmin(admin.ModelAdmin):
    list_display=("usuario", "estado","asunto", "descripcion", "fecha", "respuesta")
    list_filter=("estado", "fecha",)
    list_editable = ("estado", "respuesta")
    date_hierarchy = "fecha"
    list_per_page=20

admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(Producto, ProductoAdmin)
admin.site.register(Venta, VentaAdmin)
admin.site.register(Reclamo, ReclamoAdmin)
admin.site.register(Opinion)