from django.contrib import admin
from .models import (
    Cotizacion,
    DetalleCotizacion,
    Pedido,
    DetallePedido,
    AprobacionPedido,
)


class DetalleCotizacionInline(admin.TabularInline):
    model = DetalleCotizacion
    extra = 0
    fields = (
        "producto",
        "cantidad",
        "precio_unitario_estimado",
        "descuento",
        "subtotal",
    )


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "institucion",
        "cliente",
        "ejecutivo",
        "estado",
        "total_estimado",
        "fecha_creacion",
        "fecha_vencimiento",
    )

    list_filter = (
        "estado",
        "fecha_creacion",
        "fecha_vencimiento",
    )

    search_fields = (
        "id",
        "institucion__nombre",
        "cliente__usuario__username",
        "cliente__usuario__email",
        "ejecutivo__usuario__username",
        "observacion",
    )

    readonly_fields = (
        "fecha_creacion",
    )

    ordering = (
        "-fecha_creacion",
    )

    inlines = [
        DetalleCotizacionInline,
    ]

    fieldsets = (
        ("Información general", {
            "fields": (
                "institucion",
                "cliente",
                "ejecutivo",
                "estado",
            )
        }),
        ("Fechas", {
            "fields": (
                "fecha_creacion",
                "fecha_vencimiento",
            )
        }),
        ("Montos", {
            "fields": (
                "total_estimado",
            )
        }),
        ("Observación", {
            "fields": (
                "observacion",
            )
        }),
    )


@admin.register(DetalleCotizacion)
class DetalleCotizacionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cotizacion",
        "producto",
        "cantidad",
        "precio_unitario_estimado",
        "descuento",
        "subtotal",
    )

    list_filter = (
        "producto",
    )

    search_fields = (
        "id",
        "cotizacion__id",
        "producto__nombre",
        "producto__sku",
    )

    ordering = (
        "cotizacion",
        "id",
    )


class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    fields = (
        "producto",
        "lote",
        "cantidad",
        "cantidad_preparada",
        "precio_unitario_historico",
        "descuento",
        "subtotal",
        "observacion",
    )


class AprobacionPedidoInline(admin.StackedInline):
    model = AprobacionPedido
    extra = 0
    max_num = 1
    fields = (
        "ejecutivo",
        "estado_aprobacion",
        "fecha_aprobacion",
        "comentario",
    )


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cliente",
        "institucion",
        "estado_pedido",
        "tipo_venta",
        "tipo_despacho",
        "prioridad_medica",
        "total",
        "fecha_creacion",
        "fecha_actualizacion",
    )

    list_filter = (
        "estado_pedido",
        "tipo_venta",
        "tipo_despacho",
        "prioridad_medica",
        "fecha_creacion",
        "fecha_actualizacion",
    )

    search_fields = (
        "id",
        "cliente__usuario__username",
        "cliente__usuario__email",
        "institucion__nombre",
        "cotizacion__id",
        "observacion",
    )

    readonly_fields = (
        "fecha_creacion",
        "fecha_actualizacion",
    )

    ordering = (
        "-fecha_creacion",
    )

    inlines = [
        DetallePedidoInline,
        AprobacionPedidoInline,
    ]

    fieldsets = (
        ("Información del pedido", {
            "fields": (
                "cliente",
                "institucion",
                "cotizacion",
                "sucursal_origen",
                "direccion_entrega",
                "operador_asignado",
            )
        }),
        ("Estado y clasificación", {
            "fields": (
                "estado_pedido",
                "tipo_venta",
                "tipo_despacho",
                "prioridad_medica",
            )
        }),
        ("Fechas", {
            "fields": (
                "fecha_creacion",
                "fecha_actualizacion",
                "fecha_requerida_entrega",
            )
        }),
        ("Montos", {
            "fields": (
                "subtotal",
                "descuento_total",
                "monto_neto",
                "monto_iva",
                "total",
            )
        }),
        ("Observación", {
            "fields": (
                "observacion",
            )
        }),
    )


@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pedido",
        "producto",
        "lote",
        "cantidad",
        "cantidad_preparada",
        "precio_unitario_historico",
        "descuento",
        "subtotal",
    )

    list_filter = (
        "producto",
        "lote",
    )

    search_fields = (
        "id",
        "pedido__id",
        "producto__nombre",
        "producto__sku",
        "observacion",
    )

    ordering = (
        "pedido",
        "id",
    )


@admin.register(AprobacionPedido)
class AprobacionPedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pedido",
        "ejecutivo",
        "estado_aprobacion",
        "fecha_aprobacion",
    )

    list_filter = (
        "estado_aprobacion",
        "fecha_aprobacion",
    )

    search_fields = (
        "id",
        "pedido__id",
        "ejecutivo__usuario__username",
        "ejecutivo__usuario__email",
        "comentario",
    )

    ordering = (
        "-fecha_aprobacion",
        "-id",
    )

    fieldsets = (
        ("Pedido", {
            "fields": (
                "pedido",
            )
        }),
        ("Aprobación", {
            "fields": (
                "ejecutivo",
                "estado_aprobacion",
                "fecha_aprobacion",
                "comentario",
            )
        }),
    )