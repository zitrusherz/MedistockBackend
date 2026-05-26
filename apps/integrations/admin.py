import hashlib
import secrets
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html, mark_safe
from .models import ApiClient, IntegracionExterna, RegistroIntegracion


# ============================================================
# API CLIENT
# ============================================================

@admin.register(ApiClient)
class ApiClientAdmin(admin.ModelAdmin):
    list_display = [
        'nombre_cliente_api',
        'institucion',
        'badge_activo',
        'limite_requests_diario',
        'fecha_creacion',
        'badge_vencimiento',
    ]
    list_filter   = ['activo', 'institucion']
    search_fields = ['nombre_cliente_api', 'institucion__razon_social']
    readonly_fields = [
        'api_key_hash',
        'fecha_creacion',
        'info_key',
    ]
    ordering = ['-fecha_creacion']
    actions  = ['desactivar_clientes', 'activar_clientes', 'rotar_api_key']

    fieldsets = (
        ('Identificacion', {
            'fields': ('nombre_cliente_api', 'institucion'),
        }),
        ('Seguridad', {
            'fields': ('api_key_hash', 'info_key'),
            'description': (
                'La API Key se genera automáticamente al guardar por primera vez. '
                'Nunca se almacena en texto plano — solo su hash SHA-256. '
                'Para regenerarla usa la acción "Rotar API Key" desde el listado.'
            ),
        }),
        ('Control de acceso', {
            'fields': ('activo', 'limite_requests_diario', 'fecha_expiracion'),
        }),
        ('Auditoria', {
            'fields': ('fecha_creacion',),
        }),
    )

    # ── Campos calculados para el listado ──────────────────────

    @admin.display(description='Activo', boolean=False, ordering='activo')
    def badge_activo(self, obj):
        if obj.activo:
            return mark_safe(
                '<span style="color:#2ecc71;font-weight:bold;">✔ Activo</span>'
            )
        return mark_safe(
            '<span style="color:#e74c3c;font-weight:bold;">✘ Inactivo</span>'
        )

    @admin.display(description='Vencimiento')
    def badge_vencimiento(self, obj):
        if obj.fecha_expiracion is None:
            return mark_safe('<span style="color:#95a5a6;">Sin vencimiento</span>')
        if obj.fecha_expiracion < timezone.now():
            return format_html(
                '<span style="color:#e74c3c;font-weight:bold;">Vencida {}</span>',
                obj.fecha_expiracion.strftime('%d/%m/%Y'),
            )
        return format_html(
            '<span style="color:#f39c12;">{}</span>',
            obj.fecha_expiracion.strftime('%d/%m/%Y'),
        )

    @admin.display(description='Sobre la API Key')
    def info_key(self, obj):
        if obj.pk:
            # Objeto ya guardado — key generada, no recuperable
            return mark_safe(
                '<p style="color:#7f8c8d;">'
                'Solo se guarda el hash SHA-256. '
                'Para generar una nueva, vuelve al listado '
                'y usa la acción <strong>"Rotar API Key"</strong>.'
                '</p>'
            )
        # Objeto nuevo — todavía no guardado
        return mark_safe(
            '<p style="color:#2980b9;">'
            'La API Key se generará automáticamente al guardar. '
            'Aparecerá en el mensaje de confirmación — <strong>cópiala en ese momento</strong>.'
            '</p>'
        )

    # ── Creación y edición ─────────────────────────────────────

    def save_model(self, request, obj, form, change):
        """
        Al crear un ApiClient nuevo desde el admin:
          1. Genera una key criptográficamente segura.
          2. Guarda solo el hash SHA-256 en la BD.
          3. Muestra la key en crudo en el mensaje de éxito (única oportunidad).

        En edición (change=True) no toca la key.
        """
        if not change:
            # --- Creación ---
            raw_key = secrets.token_hex(32)   # 64 caracteres hex
            obj.api_key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
            super().save_model(request, obj, form, change)

            self.message_user(
                request,
                format_html(
                    '<strong>✔ ApiClient creado correctamente.</strong><br>'
                    'API Key para <em>"{}"</em>:<br>'
                    '<code style="'
                    'display:block;margin-top:6px;padding:8px 12px;'
                    'background:#f4f4f4;border:1px solid #ddd;'
                    'font-size:13px;letter-spacing:.5px;word-break:break-all;'
                    '">{}</code>'
                    '<span style="color:#e74c3c;font-weight:bold;">'
                    '⚠ Cópiala ahora — no se puede recuperar después.'
                    '</span>',
                    obj.nombre_cliente_api,
                    raw_key,
                ),
            )
        else:
            # --- Edición: guardar sin tocar la key ---
            super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj:
            # En edición la institución no se puede cambiar
            readonly.append('institucion')
        return readonly

    # ── Acciones masivas ───────────────────────────────────────

    @admin.action(description='Desactivar clientes seleccionados')
    def desactivar_clientes(self, request, queryset):
        total = queryset.update(activo=False)
        self.message_user(request, f'{total} cliente(s) desactivado(s).')

    @admin.action(description='Activar clientes seleccionados')
    def activar_clientes(self, request, queryset):
        total = queryset.update(activo=True)
        self.message_user(request, f'{total} cliente(s) activado(s).')

    @admin.action(description='Rotar API Key — genera una nueva key')
    def rotar_api_key(self, request, queryset):
        if queryset.count() > 1:
            self.message_user(
                request,
                'Solo puedes rotar la key de un cliente a la vez.',
                level='error',
            )
            return

        cliente = queryset.first()
        raw_key = secrets.token_hex(32)
        cliente.api_key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        cliente.save(update_fields=['api_key_hash'])

        self.message_user(
            request,
            format_html(
                '<strong>Nueva API Key para "{}":</strong><br>'
                '<code style="'
                'display:block;margin-top:6px;padding:8px 12px;'
                'background:#f4f4f4;border:1px solid #ddd;'
                'font-size:13px;letter-spacing:.5px;word-break:break-all;'
                '">{}</code>'
                '<span style="color:#e74c3c;font-weight:bold;">'
                '⚠ La key anterior quedó inválida. Actualiza el ERP de la clínica ahora.'
                '</span>',
                cliente.nombre_cliente_api,
                raw_key,
            ),
        )


# ============================================================
# INTEGRACION EXTERNA
# ============================================================

@admin.register(IntegracionExterna)
class IntegracionExternaAdmin(admin.ModelAdmin):
    list_display  = ['nombre', 'tipo_integracion', 'proveedor', 'badge_activo', 'url_base']
    list_filter   = ['tipo_integracion', 'activo']
    search_fields = ['nombre', 'proveedor']
    ordering      = ['tipo_integracion', 'nombre']

    fieldsets = (
        ('Identificacion', {
            'fields': ('nombre', 'tipo_integracion', 'proveedor'),
        }),
        ('Conexion', {
            'fields': ('url_base', 'activo'),
        }),
    )

    @admin.display(description='Activo', boolean=True, ordering='activo')
    def badge_activo(self, obj):
        return obj.activo


# ============================================================
# REGISTRO INTEGRACION
# ============================================================

class RegistroIntegracionExitosoFilter(admin.SimpleListFilter):
    title          = 'Resultado'
    parameter_name = 'exitoso'

    def lookups(self, request, model_admin):
        return [('1', 'Exitoso'), ('0', 'Con error')]

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(exitoso=True)
        if self.value() == '0':
            return queryset.filter(exitoso=False)
        return queryset


@admin.register(RegistroIntegracion)
class RegistroIntegracionAdmin(admin.ModelAdmin):
    list_display = [
        'fecha_registro',
        'tipo_evento',
        'metodo',
        'endpoint',
        'badge_status',
        'badge_exitoso',
        'tiempo_respuesta_ms',
        'api_client',
        'pedido',
    ]
    list_filter   = ['tipo_evento', 'metodo', RegistroIntegracionExitosoFilter, 'api_client']
    search_fields = [
        'endpoint',
        'api_client__nombre_cliente_api',
        'api_client__institucion__razon_social',
        'mensaje_error',
    ]
    readonly_fields = [
        'api_client', 'integracion_externa', 'pedido',
        'tipo_evento', 'endpoint', 'metodo',
        'status_code', 'tiempo_respuesta_ms',
        'exitoso', 'mensaje_error', 'fecha_registro',
    ]
    ordering      = ['-fecha_registro']
    date_hierarchy = 'fecha_registro'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description='Status', ordering='status_code')
    def badge_status(self, obj):
        if obj.status_code is None:
            return '-'
        color = '#2ecc71' if obj.status_code < 300 else ('#f39c12' if obj.status_code < 500 else '#e74c3c')
        return format_html(
            '<span style="color:{};font-weight:bold;">{}</span>',
            color, obj.status_code,
        )

    @admin.display(description='Resultado', boolean=False, ordering='exitoso')
    def badge_exitoso(self, obj):
        if obj.exitoso:
            return mark_safe('<span style="color:#2ecc71;font-weight:bold;">✔ OK</span>')
        return mark_safe('<span style="color:#e74c3c;font-weight:bold;">✘ Error</span>')