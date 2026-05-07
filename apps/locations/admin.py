from django.contrib import admin
from .models import Region, Comuna, Sucursal, ComunaChilexpress


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'chilexpress_region_id']
    search_fields = ['nombre', 'chilexpress_region_id']


@admin.register(Comuna)
class ComunaAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'nombre_alt', 'region']
    search_fields = ['nombre', 'nombre_alt']
    list_filter = ['region']


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'direccion', 'num_direccion', 'comuna', 'telefono', 'activo']
    search_fields = ['nombre', 'direccion', 'num_direccion']
    list_filter = ['activo', 'comuna__region']


@admin.register(ComunaChilexpress)
class ComunaChilexpressAdmin(admin.ModelAdmin):
    list_display = ['id', 'comuna', 'county_code', 'county_name', 'coverage_name', 'retorna_respuesta']
    search_fields = ['comuna__nombre', 'county_code', 'county_name', 'coverage_name']
    list_filter = ['retorna_respuesta']
