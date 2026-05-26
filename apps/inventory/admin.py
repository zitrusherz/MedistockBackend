from django.contrib import admin
from django.utils.html import format_html, mark_safe  # ← añadir mark_safe
from .models import (
    Categoria, Marca, Producto, CategoriaProducto,
    Lote, Inventario, MovimientoInventario,
    TrasladoInventario, DetalleTrasladoInventario,
)

# ============================================================
# INLINES
# ============================================================

class CategoriaProductoInline(admin.TabularInline):
    model = CategoriaProducto
    extra = 1
    autocomplete_fields = ['categoria']

class LoteInline(admin.TabularInline):
    model = Lote
    extra = 0
    fields = ['codigo_lote', 'fecha_elaboracion', 'fecha_vencimiento', 'activo']
    show_change_link = True

class InventarioInline(admin.TabularInline):
    model = Inventario
    extra = 0
    fields = ['sucursal', 'cantidad_disponible', 'cantidad_reservada', 'stock_critico']
    readonly_fields = ['cantidad_reservada']

class DetalleTrasladoInline(admin.TabularInline):
    model = DetalleTrasladoInventario
    extra = 1
    fields = ['lote', 'cantidad']
    autocomplete_fields = ['lote']

# ============================================================
# CATEGORÍA
# ============================================================

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'activo']
    search_fields = ['nombre']
    list_filter = ['activo']

# ============================================================
# MARCA
# ============================================================

@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'activo']
    search_fields = ['nombre']
    list_filter = ['activo']

# ============================================================
# PRODUCTO
# ============================================================

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'sku', 'nombre', 'marca', 'valor_unitario',
        'activo', 'es_caja', 'miniatura',
    ]
    search_fields = ['sku', 'nombre', 'registro_sanitario']
    list_filter = ['activo', 'es_caja', 'marca']
    list_select_related = ['marca']
    readonly_fields = ['miniatura_grande']
    inlines = [CategoriaProductoInline, LoteInline]

    fieldsets = (
        ('Identificación', {
            'fields': ('sku', 'nombre', 'descripcion', 'marca', 'activo', 'es_caja'),
        }),
        ('Precio', {
            'fields': ('valor_unitario', 'unidad_medida'),
        }),
        ('Dimensiones y peso', {
            'classes': ('collapse',),
            'fields': ('largo_mm', 'ancho_mm', 'alto_mm', 'peso_mg', 'volumen_ml'),
        }),
        ('Registro sanitario', {
            'classes': ('collapse',),
            'fields': ('registro_sanitario', 'requiere_control_vencimiento'),
        }),
        ('Imagen', {
            'fields': ('imagen', 'miniatura_grande'),
        }),
    )

    def miniatura(self, obj):
        if obj.imagen:
            return format_html(
                '<img src="{}" style="height:40px; border-radius:4px;" />',
                obj.imagen.url,
            )
        return '—'
    miniatura.short_description = 'Imagen'

    def miniatura_grande(self, obj):
        if obj.imagen:
            return format_html(
                '<img src="{}" style="max-height:200px; border-radius:6px;" />',
                obj.imagen.url,
            )
        return mark_safe('Sin imagen')
    miniatura_grande.short_description = 'Preview actual'

# ============================================================
# CATEGORÍA-PRODUCTO
# ============================================================

@admin.register(CategoriaProducto)
class CategoriaProductoAdmin(admin.ModelAdmin):
    list_display = ['id', 'producto', 'categoria']
    search_fields = ['producto__sku', 'producto__nombre', 'categoria__nombre']
    list_filter = ['categoria']
    list_select_related = ['producto', 'categoria']
    autocomplete_fields = ['producto', 'categoria']

# ============================================================
# LOTE
# ============================================================

@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'producto', 'codigo_lote',
        'fecha_elaboracion', 'fecha_vencimiento', 'activo',
    ]
    search_fields = ['codigo_lote', 'producto__sku', 'producto__nombre']
    list_filter = ['activo', 'fecha_vencimiento']
    list_select_related = ['producto']
    autocomplete_fields = ['producto']
    inlines = [InventarioInline]

    fieldsets = (
        (None, {
            'fields': ('producto', 'codigo_lote', 'activo'),
        }),
        ('Fechas', {
            'fields': ('fecha_elaboracion', 'fecha_vencimiento'),
        }),
    )

# ============================================================
# INVENTARIO
# ============================================================

@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'producto_sku', 'lote', 'sucursal',
        'cantidad_disponible', 'cantidad_reservada',
        'stock_neto', 'stock_critico', 'alerta',
        'fecha_actualizacion',
    ]
    search_fields = [
        'lote__codigo_lote', 'lote__producto__sku',
        'lote__producto__nombre', 'sucursal__nombre',
    ]
    list_filter = ['sucursal', 'lote__producto']
    list_select_related = ['lote', 'sucursal', 'lote__producto']
    readonly_fields = ['fecha_actualizacion', 'stock_neto', 'alerta']

    def producto_sku(self, obj):
        return obj.lote.producto.sku
    producto_sku.short_description = 'SKU'
    producto_sku.admin_order_field = 'lote__producto__sku'

    def stock_neto(self, obj):
        return obj.cantidad_disponible - obj.cantidad_reservada
    stock_neto.short_description = 'Stock neto'

    def alerta(self, obj):
        neto = obj.cantidad_disponible - obj.cantidad_reservada
        if neto <= obj.stock_critico:
            # ✅ mark_safe — HTML estático, sin datos variables del objeto
            return mark_safe('<span style="color:red; font-weight:bold;">⚠ Crítico</span>')
        return mark_safe('<span style="color:green;">OK</span>')
    alerta.short_description = 'Estado'

# ============================================================
# MOVIMIENTO DE INVENTARIO
# ============================================================

@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'inventario', 'tipo_movimiento',
        'cantidad', 'usuario', 'fecha_movimiento',
    ]
    search_fields = [
        'inventario__lote__codigo_lote',
        'inventario__lote__producto__sku',
        'usuario__username',
    ]
    list_filter = ['tipo_movimiento', 'fecha_movimiento']
    list_select_related = [
        'inventario', 'usuario',
        'inventario__lote', 'inventario__lote__producto',
    ]
    readonly_fields = ['fecha_movimiento']

    def has_change_permission(self, request, obj=None):
        return False

# ============================================================
# TRASLADO DE INVENTARIO
# ============================================================

@admin.register(TrasladoInventario)
class TrasladoInventarioAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'sucursal_origen', 'sucursal_destino',
        'estado', 'fecha_solicitud', 'fecha_envio', 'fecha_recepcion',
    ]
    search_fields = ['sucursal_origen__nombre', 'sucursal_destino__nombre']
    list_filter = ['estado', 'fecha_solicitud']
    list_select_related = ['sucursal_origen', 'sucursal_destino', 'solicitado_por']
    readonly_fields = ['fecha_solicitud']
    inlines = [DetalleTrasladoInline]

    fieldsets = (
        ('Sucursales', {
            'fields': ('sucursal_origen', 'sucursal_destino'),
        }),
        ('Estado', {
            'fields': ('estado', 'fecha_solicitud', 'fecha_envio', 'fecha_recepcion'),
        }),
        ('Observación', {
            'fields': ('observacion',),
        }),
    )

# ============================================================
# DETALLE TRASLADO
# ============================================================

@admin.register(DetalleTrasladoInventario)
class DetalleTrasladoInventarioAdmin(admin.ModelAdmin):
    list_display = ['id', 'traslado_inventario', 'lote', 'cantidad']
    search_fields = [
        'traslado_inventario__id',
        'lote__codigo_lote',
        'lote__producto__sku',
    ]
    list_filter = ['traslado_inventario']
    list_select_related = ['traslado_inventario', 'lote', 'lote__producto']
    autocomplete_fields = ['lote']