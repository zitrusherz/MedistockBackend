from django.contrib import admin
from .models import Despacho, ChilexpressApiLog


@admin.register(Despacho)
class DespachoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pedido",
        "courier_nombre",
        "numero_seguimiento",
        "estado_envio",
        "tipo_despacho",
        "costo_despacho",
        "fecha_creacion",
        "fecha_despacho",
        "fecha_entrega_estimada",
        "fecha_entrega_real",
    )

    list_filter = (
        "estado_envio",
        "tipo_despacho",
        "courier_nombre",
        "fecha_creacion",
        "fecha_despacho",
        "fecha_entrega_estimada",
        "fecha_entrega_real",
    )

    search_fields = (
        "id",
        "pedido__id",
        "courier_nombre",
        "numero_seguimiento",
        "observacion",
    )

    readonly_fields = (
        "fecha_creacion",
    )

    ordering = (
        "-fecha_creacion",
    )

    fieldsets = (
        ("Información del pedido", {
            "fields": (
                "pedido",
                "tipo_despacho",
                "estado_envio",
            )
        }),
        ("Información del courier", {
            "fields": (
                "courier_nombre",
                "numero_seguimiento",
                "url_etiqueta",
            )
        }),
        ("Fechas", {
            "fields": (
                "fecha_creacion",
                "fecha_despacho",
                "fecha_entrega_estimada",
                "fecha_entrega_real",
            )
        }),
        ("Costo y observación", {
            "fields": (
                "costo_despacho",
                "observacion",
            )
        }),
    )


@admin.register(ChilexpressApiLog)
class ChilexpressApiLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "method",
        "endpoint",
        "status_code",
        "success",
        "created_at",
    )

    list_filter = (
        "method",
        "success",
        "status_code",
        "created_at",
    )

    search_fields = (
        "endpoint",
        "error_message",
    )

    readonly_fields = (
        "method",
        "endpoint",
        "request_payload",
        "response_payload",
        "status_code",
        "success",
        "error_message",
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    fieldsets = (
        ("Información de la petición", {
            "fields": (
                "method",
                "endpoint",
                "request_payload",
            )
        }),
        ("Información de la respuesta", {
            "fields": (
                "status_code",
                "success",
                "response_payload",
            )
        }),
        ("Error", {
            "fields": (
                "error_message",
            )
        }),
        ("Fecha", {
            "fields": (
                "created_at",
            )
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False