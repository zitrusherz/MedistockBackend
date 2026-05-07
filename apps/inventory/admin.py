from django.contrib import admin
from .models import (
	Categoria,
	Marca,
	Producto,
	CategoriaProducto,
	Lote,
	Inventario,
	MovimientoInventario,
	TrasladoInventario,
	DetalleTrasladoInventario,
)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
	list_display = ['id', 'nombre', 'activo']
	search_fields = ['nombre']
	list_filter = ['activo']


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
	list_display = ['id', 'nombre', 'activo']
	search_fields = ['nombre']
	list_filter = ['activo']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
	list_display = ['id', 'sku', 'nombre', 'marca', 'valor_unitario', 'activo', 'es_caja']
	search_fields = ['sku', 'nombre', 'registro_sanitario']
	list_filter = ['activo', 'es_caja', 'marca']
	list_select_related = ['marca']


@admin.register(CategoriaProducto)
class CategoriaProductoAdmin(admin.ModelAdmin):
	list_display = ['id', 'producto', 'categoria']
	search_fields = ['producto__sku', 'producto__nombre', 'categoria__nombre']
	list_filter = ['categoria']
	list_select_related = ['producto', 'categoria']


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
	list_display = ['id', 'producto', 'codigo_lote', 'fecha_elaboracion', 'fecha_vencimiento', 'activo']
	search_fields = ['codigo_lote', 'producto__sku', 'producto__nombre']
	list_filter = ['activo', 'fecha_vencimiento']
	list_select_related = ['producto']


@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
	list_display = ['id', 'lote', 'sucursal', 'cantidad_disponible', 'cantidad_reservada', 'stock_critico', 'fecha_actualizacion']
	search_fields = ['lote__codigo_lote', 'lote__producto__sku', 'lote__producto__nombre', 'sucursal__nombre']
	list_filter = ['sucursal', 'lote__producto']
	list_select_related = ['lote', 'sucursal', 'lote__producto']


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
	list_display = ['id', 'inventario', 'tipo_movimiento', 'cantidad', 'usuario', 'fecha_movimiento']
	search_fields = ['inventario__lote__codigo_lote', 'inventario__lote__producto__sku', 'usuario__username']
	list_filter = ['tipo_movimiento', 'fecha_movimiento']
	list_select_related = ['inventario', 'usuario', 'inventario__lote', 'inventario__lote__producto']


@admin.register(TrasladoInventario)
class TrasladoInventarioAdmin(admin.ModelAdmin):
	list_display = ['id', 'sucursal_origen', 'sucursal_destino', 'estado', 'fecha_solicitud', 'fecha_envio', 'fecha_recepcion']
	search_fields = ['sucursal_origen__nombre', 'sucursal_destino__nombre']
	list_filter = ['estado', 'fecha_solicitud']
	list_select_related = ['sucursal_origen', 'sucursal_destino', 'solicitado_por']


@admin.register(DetalleTrasladoInventario)
class DetalleTrasladoInventarioAdmin(admin.ModelAdmin):
	list_display = ['id', 'traslado_inventario', 'lote', 'cantidad']
	search_fields = ['traslado_inventario__id', 'lote__codigo_lote', 'lote__producto__sku']
	list_filter = ['traslado_inventario']
	list_select_related = ['traslado_inventario', 'lote', 'lote__producto']
