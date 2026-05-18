from rest_framework import serializers

from .models import Region, Comuna, Sucursal, ComunaChilexpress


class RegionSerializer(serializers.ModelSerializer):
	class Meta:
		model = Region
		# Incluye el id que viene de la integración Chilexpress
		fields = ['id', 'nombre', 'chilexpress_region_id']


class ComunaSerializer(serializers.ModelSerializer):
	region = RegionSerializer(read_only=True)
	region_id = serializers.PrimaryKeyRelatedField(
		queryset=Region.objects.all(), source='region', write_only=True
	)

	class Meta:
		model = Comuna
		fields = ['id', 'nombre', 'nombre_alt', 'region', 'region_id']


class ComunaChilexpressSerializer(serializers.ModelSerializer):
	class Meta:
		model = ComunaChilexpress
		# Campos relevantes para el frontend
		fields = ['county_code', 'county_name', 'coverage_name', 'retorna_respuesta']


class ComunaPublicSerializer(serializers.ModelSerializer):
	"""Serializer público para listar comunas que tienen cobertura Chilexpress.

	No incluye `nombre_alt` por defecto en las respuestas públicas (aunque el
	modelo lo tiene). Se expone la información relevante de Chilexpress cuando
	`retorna_respuesta` es True.
	"""
	region = RegionSerializer(read_only=True)
	chilexpress = serializers.SerializerMethodField()

	def get_chilexpress(self, obj):
		entry = obj.comunas_chilexpress.filter(retorna_respuesta=True).first()
		if not entry:
			return None
		return ComunaChilexpressSerializer(entry).data

	class Meta:
		model = Comuna
		fields = ['id', 'nombre', 'region', 'chilexpress']


class RegionWithComunasSerializer(serializers.ModelSerializer):
	"""Serializer que incluye comunas embebidas (usado por el endpoint compuesto).

	Las comunas deben ser prefetched en la vista filtradas por
	`comunas_chilexpress__retorna_respuesta=True` para que aquí sólo se devuelvan
	las comunas con cobertura. El campo `comunas` usa el serializer público
	para no exponer `nombre_alt`.
	 """
	comunas = ComunaPublicSerializer(many=True, source='comuna_set', read_only=True)

	class Meta:
		model = Region
		fields = ['id', 'nombre', 'chilexpress_region_id', 'comunas']


class SucursalSerializer(serializers.ModelSerializer):
	comuna = ComunaSerializer(read_only=True)
	comuna_id = serializers.PrimaryKeyRelatedField(
		queryset=Comuna.objects.all(), source='comuna', write_only=True
	)

	class Meta:
		model = Sucursal
		# Se añadió `num_direccion` según el modelo
		fields = ['id', 'nombre', 'direccion', 'num_direccion', 'telefono', 'comuna', 'comuna_id', 'activo']


class SucursalPublicSerializer(serializers.ModelSerializer):
	"""Datos públicos de sucursal: incluimos la comuna (id/nombre) y el
	`county_code` de ComunaChilexpress cuando exista una entrada con
	`retorna_respuesta=True`.
	"""
	comuna = serializers.SerializerMethodField()
	region = serializers.SerializerMethodField()
	county_code = serializers.SerializerMethodField()

	def get_comuna(self, obj):
		if not obj.comuna:
			return None
		return {"id": obj.comuna.id, "nombre": obj.comuna.nombre}

	def get_region(self, obj):
		if not obj.comuna or not obj.comuna.region:
			return None
		return {"id": obj.comuna.region.id, "nombre": obj.comuna.region.nombre}

	def get_county_code(self, obj):
		if not obj.comuna:
			return None
		entry = obj.comuna.comunas_chilexpress.filter(retorna_respuesta=True).first()
		return entry.county_code if entry else None

	class Meta:
		model = Sucursal
		fields = [
			'id', 'nombre', 'direccion', 'num_direccion', 'telefono',
			'comuna', 'region', 'county_code', 'activo'
		]


class SucursalResumenSerializer(serializers.ModelSerializer):

	class Meta:
		model = Sucursal
		fields = ['id', 'nombre']