# apps/accounts/admin.py

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group

from .models import (
    Usuario,
    Institucion,
    PerfilTrabajador,
    PerfilCliente,
    ConvenioInstitucion,
    DireccionEntrega,
)


# ============================================================
# USUARIO
# ============================================================

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario

    list_display = (
        'id',
        'username',
        'email',
        'first_name',
        'last_name',
        'rut',
        'is_staff',
        'is_active',
        'mostrar_grupos',
    )

    list_filter = (
        'is_staff',
        'is_superuser',
        'is_active',
        'groups',
    )

    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
        'rut',
    )

    ordering = ('id',)

    fieldsets = UserAdmin.fieldsets + (
        ('Datos adicionales', {
            'fields': ('rut',),
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Datos adicionales', {
            'fields': ('email', 'first_name', 'last_name', 'rut'),
        }),
    )

    def mostrar_grupos(self, obj):
        return ', '.join(group.name for group in obj.groups.all())

    mostrar_grupos.short_description = 'Grupos'


# ============================================================
# FORMULARIOS ADMIN PARA EDITAR GRUPOS DESDE PERFILES
# ============================================================

class PerfilTrabajadorAdminForm(forms.ModelForm):
    grupos = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=admin.widgets.FilteredSelectMultiple(
            verbose_name="Grupos",
            is_stacked=False
        ),
        label="Grupos del usuario",
        help_text="Grupos y permisos asociados al usuario de este trabajador."
    )

    class Meta:
        model = PerfilTrabajador
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.usuario_id:
            self.fields['grupos'].initial = self.instance.usuario.groups.all()

    def save(self, commit=True):
        perfil = super().save(commit=commit)

        if perfil.usuario_id:
            perfil.usuario.groups.set(self.cleaned_data['grupos'])

        return perfil


class PerfilClienteAdminForm(forms.ModelForm):
    grupos = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=admin.widgets.FilteredSelectMultiple(
            verbose_name="Grupos",
            is_stacked=False
        ),
        label="Grupos del usuario",
        help_text="Grupos y permisos asociados al usuario de este cliente."
    )

    class Meta:
        model = PerfilCliente
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.usuario_id:
            self.fields['grupos'].initial = self.instance.usuario.groups.all()

    def save(self, commit=True):
        perfil = super().save(commit=commit)

        if perfil.usuario_id:
            perfil.usuario.groups.set(self.cleaned_data['grupos'])

        return perfil


# ============================================================
# PERFIL TRABAJADOR
# ============================================================

@admin.register(PerfilTrabajador)
class PerfilTrabajadorAdmin(admin.ModelAdmin):
    form = PerfilTrabajadorAdminForm

    list_display = (
        'id',
        'usuario',
        'nombre_usuario',
        'rut',
        'telefono',
        'cargo',
        'sucursal',
        'activo',
        'mostrar_grupos',
    )

    list_filter = (
        'activo',
        'cargo',
        'sucursal',
        'usuario__groups',
    )

    search_fields = (
        'rut',
        'telefono',
        'cargo',
        'usuario__username',
        'usuario__email',
        'usuario__first_name',
        'usuario__last_name',
    )

    autocomplete_fields = (
        'usuario',
        'comuna',
        'sucursal',
    )

    fieldsets = (
        ('Usuario asociado', {
            'fields': (
                'usuario',
                'grupos',
            )
        }),
        ('Datos del trabajador', {
            'fields': (
                'rut',
                'telefono',
                'direccion',
                'comuna',
                'sucursal',
                'cargo',
                'activo',
            )
        }),
    )

    def nombre_usuario(self, obj):
        return f'{obj.usuario.first_name} {obj.usuario.last_name}'.strip()

    nombre_usuario.short_description = 'Nombre'

    def mostrar_grupos(self, obj):
        return ', '.join(group.name for group in obj.usuario.groups.all())

    mostrar_grupos.short_description = 'Grupos del usuario'


# ============================================================
# PERFIL CLIENTE
# ============================================================

@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    form = PerfilClienteAdminForm

    list_display = (
        'id',
        'usuario',
        'nombre_usuario',
        'rut',
        'pasaporte',
        'tipo_cliente',
        'telefono',
        'institucion',
        'activo',
        'mostrar_grupos',
    )

    list_filter = (
        'activo',
        'tipo_cliente',
        'institucion',
        'usuario__groups',
    )

    search_fields = (
        'rut',
        'pasaporte',
        'telefono',
        'usuario__username',
        'usuario__email',
        'usuario__first_name',
        'usuario__last_name',
        'institucion__razon_social',
        'institucion__rut_empresa',
    )

    autocomplete_fields = (
        'usuario',
        'institucion',
    )

    fieldsets = (
        ('Usuario asociado', {
            'fields': (
                'usuario',
                'grupos',
            )
        }),
        ('Datos del cliente', {
            'fields': (
                'rut',
                'pasaporte',
                'tipo_cliente',
                'telefono',
                'institucion',
                'activo',
            )
        }),
    )

    def nombre_usuario(self, obj):
        return f'{obj.usuario.first_name} {obj.usuario.last_name}'.strip()

    nombre_usuario.short_description = 'Nombre'

    def mostrar_grupos(self, obj):
        return ', '.join(group.name for group in obj.usuario.groups.all())

    mostrar_grupos.short_description = 'Grupos del usuario'


# ============================================================
# INSTITUCIÓN
# ============================================================

@admin.register(Institucion)
class InstitucionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'razon_social',
        'rut_empresa',
        'telefono',
        'email_contacto',
        'convenio_activo',
        'credito_autorizado',
        'limite_credito',
        'activo',
    )

    list_filter = (
        'activo',
        'convenio_activo',
        'credito_autorizado',
    )

    search_fields = (
        'razon_social',
        'rut_empresa',
        'telefono',
        'email_contacto',
    )

    autocomplete_fields = (
        'comuna',
    )


# ============================================================
# CONVENIO INSTITUCIÓN
# ============================================================

@admin.register(ConvenioInstitucion)
class ConvenioInstitucionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'institucion',
        'fecha_inicio',
        'fecha_fin',
        'descuento_porcentaje',
        'activo',
    )

    list_filter = (
        'activo',
        'fecha_inicio',
        'fecha_fin',
    )

    search_fields = (
        'institucion__razon_social',
        'institucion__rut_empresa',
        'observacion',
    )

    autocomplete_fields = (
        'institucion',
    )


# ============================================================
# DIRECCIÓN DE ENTREGA
# ============================================================

@admin.register(DireccionEntrega)
class DireccionEntregaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'cliente',
        'institucion',
        'direccion',
        'num_direccion',
        'comuna',
        'nombre_receptor',
        'telefono_receptor',
        'es_principal',
        'activo',
    )

    list_filter = (
        'activo',
        'es_principal',
        'comuna',
    )

    search_fields = (
        'direccion',
        'num_direccion',
        'detalle_direccion',
        'referencia',
        'nombre_receptor',
        'telefono_receptor',
        'cliente__usuario__username',
        'cliente__usuario__email',
        'institucion__razon_social',
    )

    autocomplete_fields = (
        'cliente',
        'institucion',
        'comuna',
    )