from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from django.db.models import Prefetch

from .models import Region, Comuna, ComunaChilexpress, Sucursal
from .serializers import (
	RegionSerializer,
	ComunaPublicSerializer,
	ComunaChilexpressSerializer,
	SucursalPublicSerializer,
	RegionWithComunasSerializer,
)


class RegionListView(generics.ListAPIView):
	"""Lista todas las regiones."""
	queryset = Region.objects.all().order_by('nombre')
	serializer_class = RegionSerializer
	permission_classes = [AllowAny]


class ComunaListView(generics.ListAPIView):
    """Lista comunas que tienen una entrada en ComunaChilexpress con
    `retorna_respuesta=True`. Se puede filtrar por `region_id` query param.
    """
    serializer_class = ComunaPublicSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Comuna.objects.filter(
            comunas_chilexpress__retorna_respuesta=True
        ).distinct().select_related('region')

        region_id = self.request.query_params.get('region_id')

        if region_id in [None, '', 'undefined', 'null']:
            return qs.order_by('nombre')

        if not str(region_id).isdigit():
            raise ValidationError({
                'region_id': 'El parámetro region_id debe ser un número válido.'
            })

        qs = qs.filter(region_id=int(region_id))

        return qs.order_by('nombre')


class ComunaChilexpressListView(generics.ListAPIView):
	"""Opcionalmente listar entradas de ComunaChilexpress. Por defecto devuelve
	solo las que `retorna_respuesta=True` si se pasa el query param
	`retorna_respuesta=true`.
	"""
	serializer_class = ComunaChilexpressSerializer
	permission_classes = [AllowAny]

	def get_queryset(self):
		qs = ComunaChilexpress.objects.all()
		retorna = self.request.query_params.get('retorna_respuesta')
		comuna_id = self.request.query_params.get('comuna_id')
		if retorna is not None:
			if str(retorna).lower() in ('1', 'true', 'yes'):
				qs = qs.filter(retorna_respuesta=True)
			elif str(retorna).lower() in ('0', 'false', 'no'):
				qs = qs.filter(retorna_respuesta=False)
		if comuna_id:
			qs = qs.filter(comuna_id=comuna_id)
		return qs


class SucursalDetailView(generics.RetrieveAPIView):
	"""Retorna datos de una sucursal, incluyendo su comuna (id/nombre) y el
	`county_code` asociado en ComunaChilexpress (cuando exista una entrada con
	`retorna_respuesta=True`)."""
	queryset = Sucursal.objects.select_related('comuna__region').prefetch_related('comuna__comunas_chilexpress')
	serializer_class = SucursalPublicSerializer
	permission_classes = [AllowAny]


class RegionsWithComunasView(generics.ListAPIView):
	"""Endpoint compuesto: devuelve regiones con sus comunas que tienen
	cobertura Chilexpress (retorna_respuesta=True).

	Conserva los endpoints individuales existentes; este es un endpoint
	adicional para que el frontend haga una sola llamada inicial.
	"""
	serializer_class = RegionWithComunasSerializer
	permission_classes = [AllowAny]

	def get_queryset(self):
		comunas_qs = Comuna.objects.filter(
			comunas_chilexpress__retorna_respuesta=True
		).select_related('region').distinct()
		return Region.objects.prefetch_related(
			Prefetch('comuna_set', queryset=comunas_qs)
		).order_by('nombre')
