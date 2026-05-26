from django.contrib import admin
from django.utils.html import format_html

from .models import (
    TransaccionPago,
    ComprobantePago,
    ConciliacionPago,
    Aseguradora,
    PagoAseguradora,
)


# ============================================================
# HELPERS
# ============================================================

def badge_estado_pago(estado):
    colores = {
        'PENDIENTE':             '#888888',
        'INICIADO':              '#3b82f6',
        'AUTORIZADO':            '#8b5cf6',
        'CONFIRMADO':            '#22c55e',
        'RECHAZADO':             '#ef4444',
        'ANULADO':               '#f97316',
        'REEMBOLSADO':           '#06b6d4',
        'ERROR':                 '#dc2626',
    }
    color = colores.get(estado, '#888888')
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 8px;'
        'border-radius:4px;font-size:11px;font-weight:bold;">{}</span>',
        color, estado,
    )


def badge_estado_validacion(estado):
    colores = {
        'PENDIENTE_REVISION': '#f59e0b',
        'VALIDADO':           '#22c55e',
        'RECHAZADO':          '#ef4444',
    }
    color = colores.get(estado, '#888888')
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 8px;'
        'border-radius:4px;font-size:11px;font-weight:bold;">{}</span>',
        color, estado,
    )


# ============================================================
# INLINE — ConciliacionPago dentro de TransaccionPago
# ============================================================

class ConciliacionPagoInline(admin.StackedInline):
    model = ConciliacionPago
    extra = 0
    max_num = 1
    fields = ['analista', 'estado_conciliacion', 'observacion', 'fecha_conciliacion']
    readonly_fields = ['fecha_conciliacion']
    verbose_name = 'Conciliación'
    verbose_name_plural = 'Conciliación'


# ============================================================
# TRANSACCIÓN DE PAGO
# ============================================================

@admin.register(TransaccionPago)
class TransaccionPagoAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'pedido', 'metodo_pago', 'estado_badge',
        'monto_confirmado', 'card_last_digits',
        'authorization_code', 'fecha_creacion', 'fecha_confirmacion',
    ]
    search_fields = [
        'buy_order', 'token_ws', 'authorization_code',
        'id_transaccion_externa', 'pedido__id',
    ]
    list_filter = ['metodo_pago', 'estado_pago', 'fecha_creacion']
    list_select_related = ['pedido']
    readonly_fields = [
        'buy_order', 'session_id', 'token_ws', 'id_transaccion_externa',
        'authorization_code', 'response_code', 'payment_type_code',
        'installments_number', 'card_last_digits', 'webpay_status',
        'transaction_date', 'raw_response',
        'fecha_creacion', 'fecha_confirmacion',
    ]
    inlines = [ConciliacionPagoInline]

    fieldsets = (
        ('Pedido', {
            'fields': ('pedido', 'metodo_pago', 'estado_pago', 'monto_confirmado', 'observacion'),
        }),
        ('Datos Webpay / Pasarela', {
            'classes': ('collapse',),
            'fields': (
                'buy_order', 'session_id', 'token_ws', 'id_transaccion_externa',
                'authorization_code', 'response_code', 'payment_type_code',
                'installments_number', 'card_last_digits', 'webpay_status',
                'transaction_date',
            ),
        }),
        ('Respuesta raw', {
            'classes': ('collapse',),
            'fields': ('raw_response',),
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_confirmacion'),
        }),
    )

    def estado_badge(self, obj):
        return badge_estado_pago(obj.estado_pago)
    estado_badge.short_description = 'Estado'

    # Los pagos no se deben crear ni eliminar desde el admin
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# ============================================================
# COMPROBANTE DE PAGO (Transferencia)
# ============================================================

@admin.register(ComprobantePago)
class ComprobantePagoAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'pedido', 'banco_origen', 'numero_operacion',
        'monto_reportado', 'estado_badge', 'fecha_transferencia',
    ]
    search_fields = ['pedido__id', 'numero_operacion', 'banco_origen']
    list_filter = ['estado_validacion', 'banco_origen']
    list_select_related = ['pedido']
    readonly_fields = ['pedido']

    fieldsets = (
        ('Pedido', {
            'fields': ('pedido',),
        }),
        ('Datos de la transferencia', {
            'fields': (
                'banco_origen', 'numero_operacion',
                'fecha_transferencia', 'monto_reportado', 'archivo_url',
            ),
        }),
        ('Validación', {
            'fields': ('estado_validacion', 'observacion'),
        }),
    )

    def estado_badge(self, obj):
        return badge_estado_validacion(obj.estado_validacion)
    estado_badge.short_description = 'Estado validación'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# ============================================================
# CONCILIACIÓN DE PAGOS
# ============================================================

@admin.register(ConciliacionPago)
class ConciliacionPagoAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'transaccion_pago', 'analista',
        'estado_conciliacion', 'fecha_conciliacion',
    ]
    search_fields = [
        'transaccion_pago__buy_order',
        'transaccion_pago__id',
        'analista__usuario__username',
    ]
    list_filter = ['estado_conciliacion', 'fecha_conciliacion']
    list_select_related = ['transaccion_pago', 'analista', 'analista__usuario']
    readonly_fields = ['fecha_conciliacion', 'transaccion_pago']

    fieldsets = (
        ('Transacción', {
            'fields': ('transaccion_pago',),
        }),
        ('Conciliación', {
            'fields': ('analista', 'estado_conciliacion', 'observacion', 'fecha_conciliacion'),
        }),
    )


# ============================================================
# ASEGURADORA
# ============================================================

@admin.register(Aseguradora)
class AseguradoraAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'rut', 'contacto', 'email', 'telefono', 'activo']
    search_fields = ['nombre', 'rut', 'email']
    list_filter = ['activo']

    fieldsets = (
        ('Datos de la aseguradora', {
            'fields': ('nombre', 'rut', 'activo'),
        }),
        ('Contacto', {
            'fields': ('contacto', 'email', 'telefono'),
        }),
    )


# ============================================================
# PAGO ASEGURADORA
# ============================================================

@admin.register(PagoAseguradora)
class PagoAseguradoraAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'pedido', 'aseguradora', 'monto_cubierto',
        'estado_badge', 'fecha_registro',
    ]
    search_fields = ['pedido__id', 'aseguradora__nombre', 'aseguradora__rut']
    list_filter = ['estado', 'aseguradora']
    list_select_related = ['pedido', 'aseguradora']
    readonly_fields = ['fecha_registro', 'pedido']

    fieldsets = (
        ('Pedido', {
            'fields': ('pedido',),
        }),
        ('Aseguradora', {
            'fields': ('aseguradora', 'monto_cubierto', 'estado'),
        }),
        ('Observación y fecha', {
            'fields': ('observacion', 'fecha_registro'),
        }),
    )

    def estado_badge(self, obj):
        colores = {
            'PENDIENTE': '#f59e0b',
            'APROBADO':  '#22c55e',
            'RECHAZADO': '#ef4444',
            'PAGADO':    '#3b82f6',
        }
        color = colores.get(obj.estado, '#888888')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:bold;">{}</span>',
            color, obj.estado,
        )
    estado_badge.short_description = 'Estado'