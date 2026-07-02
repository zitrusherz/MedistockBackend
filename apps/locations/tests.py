from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory

from . import views as location_views
from .models import Comuna, ComunaChilexpress, Region, Sucursal
from .serializers import (
	ComunaPublicSerializer,
	ComunaSerializer,
	RegionSerializer,
	RegionWithComunasSerializer,
	SucursalPublicSerializer,
	SucursalSerializer,
)


def _make_queryset_mock():
	queryset = Mock(name='QuerySet')
	queryset.filter.return_value = queryset
	queryset.distinct.return_value = queryset
	queryset.select_related.return_value = queryset
	queryset.prefetch_related.return_value = queryset
	queryset.order_by.return_value = queryset
	return queryset


def _make_request(view, **query_params):
	request = APIRequestFactory().get('/', query_params)
	return view.initialize_request(request)


class LocationModelTests(SimpleTestCase):
	def test_model_str_methods(self):
		region = Region(id=1, nombre='Metropolitana', chilexpress_region_id='RM')
		comuna = Comuna(id=2, nombre='Providencia', nombre_alt='Providencia', region=region)
		chilexpress = ComunaChilexpress(
			id=3,
			comuna=comuna,
			county_code='123',
			county_name='Providencia',
			coverage_name='Cobertura Providencia',
			retorna_respuesta=True,
		)
		sucursal = Sucursal(
			id=4,
			nombre='Sucursal Central',
			direccion='Av. Principal',
			num_direccion='123',
			telefono='22223333',
			comuna=comuna,
			activo=True,
		)

		self.assertEqual(str(region), 'Metropolitana')
		self.assertEqual(str(comuna), 'Providencia')
		self.assertEqual(str(chilexpress), 'Cobertura Providencia (123)')
		self.assertEqual(str(sucursal), 'Sucursal Central')

	def test_model_metadata_is_unmanaged(self):
		self.assertFalse(Region._meta.managed)
		self.assertFalse(Comuna._meta.managed)
		self.assertFalse(ComunaChilexpress._meta.managed)
		self.assertFalse(Sucursal._meta.managed)

	def test_comuna_unique_together_configured(self):
		self.assertIn(('nombre', 'region'), Comuna._meta.unique_together)


class SerializerTests(SimpleTestCase):
	def test_region_serializer_representation(self):
		region = SimpleNamespace(id=1, nombre='Metropolitana', chilexpress_region_id='RM')

		serializer = RegionSerializer(region)

		self.assertEqual(
			serializer.data,
			{'id': 1, 'nombre': 'Metropolitana', 'chilexpress_region_id': 'RM'},
		)

	def test_comuna_serializer_representation(self):
		region = SimpleNamespace(id=1, nombre='Metropolitana', chilexpress_region_id='RM')
		comuna = SimpleNamespace(id=2, nombre='Providencia', nombre_alt='Providencia Centro', region=region)

		serializer = ComunaSerializer(comuna)

		self.assertEqual(
			serializer.data,
			{
				'id': 2,
				'nombre': 'Providencia',
				'nombre_alt': 'Providencia Centro',
				'region': {'id': 1, 'nombre': 'Metropolitana', 'chilexpress_region_id': 'RM'},
			},
		)
		self.assertNotIn('region_id', serializer.data)

	def test_comuna_public_serializer_includes_chilexpress_entry(self):
		region = SimpleNamespace(id=1, nombre='Metropolitana', chilexpress_region_id='RM')
		comuna = SimpleNamespace(id=2, nombre='Providencia', nombre_alt='Providencia Centro', region=region)
		entry = SimpleNamespace(
			id=3,
			comuna=comuna,
			county_code='123',
			county_name='Providencia',
			coverage_name='Cobertura Providencia',
			retorna_respuesta=True,
		)
		related_manager = Mock()
		related_manager.filter.return_value.first.return_value = entry
		comuna.comunas_chilexpress = related_manager

		serializer = ComunaPublicSerializer(comuna)

		self.assertEqual(
			serializer.data,
			{
				'id': 2,
				'nombre': 'Providencia',
				'region': {'id': 1, 'nombre': 'Metropolitana', 'chilexpress_region_id': 'RM'},
				'chilexpress': {
					'county_code': '123',
					'county_name': 'Providencia',
					'coverage_name': 'Cobertura Providencia',
					'retorna_respuesta': True,
				},
			},
		)
		related_manager.filter.assert_called_once_with(retorna_respuesta=True)

	def test_comuna_public_serializer_returns_none_without_cobertura(self):
		region = SimpleNamespace(id=1, nombre='Metropolitana', chilexpress_region_id='RM')
		comuna = SimpleNamespace(id=2, nombre='Providencia', nombre_alt='Providencia Centro', region=region)
		related_manager = Mock()
		related_manager.filter.return_value.first.return_value = None
		comuna.comunas_chilexpress = related_manager

		serializer = ComunaPublicSerializer(comuna)

		self.assertIsNone(serializer.data['chilexpress'])

	def test_region_with_comunas_serializer_embeds_public_comunas(self):
		region = SimpleNamespace(id=1, nombre='Metropolitana', chilexpress_region_id='RM')
		comuna = SimpleNamespace(id=2, nombre='Providencia', nombre_alt='Providencia Centro', region=region)
		entry = SimpleNamespace(
			id=3,
			comuna=comuna,
			county_code='123',
			county_name='Providencia',
			coverage_name='Cobertura Providencia',
			retorna_respuesta=True,
		)
		related_manager = Mock()
		related_manager.filter.return_value.first.return_value = entry
		comuna.comunas_chilexpress = related_manager
		region.comuna_set = [comuna]

		serializer = RegionWithComunasSerializer(region)

		self.assertEqual(
			serializer.data,
			{
				'id': 1,
				'nombre': 'Metropolitana',
				'chilexpress_region_id': 'RM',
				'comunas': [
					{
						'id': 2,
						'nombre': 'Providencia',
						'region': {'id': 1, 'nombre': 'Metropolitana', 'chilexpress_region_id': 'RM'},
						'chilexpress': {
							'county_code': '123',
							'county_name': 'Providencia',
							'coverage_name': 'Cobertura Providencia',
							'retorna_respuesta': True,
						},
					}
				],
			},
		)

	def test_sucursal_serializer_representation(self):
		region = Region(id=1, nombre='Metropolitana', chilexpress_region_id='RM')
		comuna = Comuna(id=2, nombre='Providencia', nombre_alt='Providencia Centro', region=region)
		sucursal = Sucursal(
			id=4,
			nombre='Sucursal Central',
			direccion='Av. Principal',
			num_direccion='123',
			telefono='22223333',
			comuna=comuna,
			activo=True,
		)

		serializer = SucursalSerializer(sucursal)

		self.assertEqual(
			serializer.data,
			{
				'id': 4,
				'nombre': 'Sucursal Central',
				'direccion': 'Av. Principal',
				'num_direccion': '123',
				'telefono': '22223333',
				'comuna': {
					'id': 2,
					'nombre': 'Providencia',
					'nombre_alt': 'Providencia Centro',
					'region': {'id': 1, 'nombre': 'Metropolitana', 'chilexpress_region_id': 'RM'},
				},
				'activo': True,
			},
		)
		self.assertNotIn('comuna_id', serializer.data)

	def test_sucursal_public_serializer_representation(self):
		region = SimpleNamespace(id=1, nombre='Metropolitana', chilexpress_region_id='RM')
		comuna = SimpleNamespace(id=2, nombre='Providencia', nombre_alt='Providencia Centro', region=region)
		entry = SimpleNamespace(
			id=3,
			comuna=comuna,
			county_code='123',
			county_name='Providencia',
			coverage_name='Cobertura Providencia',
			retorna_respuesta=True,
		)
		related_manager = Mock()
		related_manager.filter.return_value.first.return_value = entry
		comuna.comunas_chilexpress = related_manager
		sucursal = SimpleNamespace(
			id=4,
			nombre='Sucursal Central',
			direccion='Av. Principal',
			num_direccion='123',
			telefono='22223333',
			comuna=comuna,
			activo=True,
		)

		serializer = SucursalPublicSerializer(sucursal)

		self.assertEqual(
			serializer.data,
			{
				'id': 4,
				'nombre': 'Sucursal Central',
				'direccion': 'Av. Principal',
				'num_direccion': '123',
				'telefono': '22223333',
				'comuna': {'id': 2, 'nombre': 'Providencia'},
				'region': {'id': 1, 'nombre': 'Metropolitana'},
				'county_code': '123',
				'activo': True,
			},
		)

	def test_sucursal_public_serializer_returns_none_when_comuna_is_missing(self):
		sucursal = SimpleNamespace(
			id=4,
			nombre='Sucursal Central',
			direccion='Av. Principal',
			num_direccion='123',
			telefono='22223333',
			comuna=None,
			activo=True,
		)

		serializer = SucursalPublicSerializer(sucursal)

		self.assertIsNone(serializer.data['comuna'])
		self.assertIsNone(serializer.data['region'])
		self.assertIsNone(serializer.data['county_code'])


class ComunaListViewTests(SimpleTestCase):
	def test_get_queryset_filters_by_region_id(self):
		queryset = _make_queryset_mock()
		manager = Mock()
		manager.filter.return_value = queryset

		with patch.object(location_views.Comuna, 'objects', manager):
			view = location_views.ComunaListView()
			view.request = _make_request(view, region_id='3')

			result = view.get_queryset()

		self.assertIs(result, queryset)
		manager.filter.assert_called_once_with(comunas_chilexpress__retorna_respuesta=True)
		queryset.distinct.assert_called_once()
		queryset.select_related.assert_called_once_with('region')
		queryset.order_by.assert_called_once_with('nombre')
		self.assertEqual(queryset.filter.call_args_list, [call(region_id=3)])

	def test_get_queryset_rejects_invalid_region_id(self):
		view = location_views.ComunaListView()
		view.request = _make_request(view, region_id='abc')

		with self.assertRaises(ValidationError) as context:
			view.get_queryset()

		self.assertIn('region_id', context.exception.detail)
		self.assertIn('número válido', str(context.exception))


class ComunaChilexpressListViewTests(SimpleTestCase):
	def test_get_queryset_filters_by_flags_and_comuna(self):
		queryset = _make_queryset_mock()
		manager = Mock()
		manager.all.return_value = queryset

		with patch.object(location_views.ComunaChilexpress, 'objects', manager):
			view = location_views.ComunaChilexpressListView()
			view.request = _make_request(view, retorna_respuesta='yes', comuna_id='9')

			result = view.get_queryset()

		self.assertIs(result, queryset)
		manager.all.assert_called_once_with()
		self.assertEqual(
			queryset.filter.call_args_list,
			[call(retorna_respuesta=True), call(comuna_id='9')],
		)


class RegionsWithComunasViewTests(SimpleTestCase):
	def test_get_queryset_prefetches_only_comunas_with_cobertura(self):
		regiones_qs = _make_queryset_mock()
		comunas_qs = _make_queryset_mock()
		comuna_manager = Mock()
		region_manager = Mock()
		comuna_manager.filter.return_value = comunas_qs
		region_manager.prefetch_related.return_value = regiones_qs

		with patch.object(location_views, 'Prefetch', autospec=True) as prefetch_cls, patch.object(location_views.Comuna, 'objects', comuna_manager), patch.object(location_views.Region, 'objects', region_manager):
			prefetch_marker = object()
			prefetch_cls.return_value = prefetch_marker
			view = location_views.RegionsWithComunasView()
			result = view.get_queryset()

		self.assertIs(result, regiones_qs)
		comuna_manager.filter.assert_called_once_with(comunas_chilexpress__retorna_respuesta=True)
		comunas_qs.select_related.assert_called_once_with('region')
		comunas_qs.distinct.assert_called_once()
		prefetch_cls.assert_called_once_with('comuna_set', queryset=comunas_qs)
		region_manager.prefetch_related.assert_called_once()
		prefetch_arg = region_manager.prefetch_related.call_args.args[0]
		self.assertIs(prefetch_arg, prefetch_marker)
		regiones_qs.order_by.assert_called_once_with('nombre')


class SucursalListViewTests(SimpleTestCase):
	def test_get_queryset_filters_region_and_comuna(self):
		queryset = _make_queryset_mock()
		manager = Mock()
		manager.filter.return_value = queryset

		with patch.object(location_views.Sucursal, 'objects', manager):
			view = location_views.SucursalListView()
			view.request = _make_request(view, region_id='2', comuna_id='7')

			result = view.get_queryset()

		self.assertIs(result, queryset)
		manager.filter.assert_called_once_with(activo=True)
		queryset.select_related.assert_called_once_with('comuna__region')
		queryset.prefetch_related.assert_called_once_with('comuna__comunas_chilexpress')
		queryset.order_by.assert_called_once_with('nombre')
		self.assertEqual(
			queryset.filter.call_args_list,
			[call(comuna__region_id=2), call(comuna_id=7)],
		)

	def test_get_queryset_rejects_invalid_region_id(self):
		view = location_views.SucursalListView()
		view.request = _make_request(view, region_id='abc')

		with self.assertRaises(ValidationError) as context:
			view.get_queryset()

		self.assertIn('region_id', context.exception.detail)
		self.assertIn('número válido', str(context.exception))

	def test_get_queryset_rejects_invalid_comuna_id(self):
		view = location_views.SucursalListView()
		view.request = _make_request(view, comuna_id='xyz')

		with self.assertRaises(ValidationError) as context:
			view.get_queryset()

		self.assertIn('comuna_id', context.exception.detail)
		self.assertIn('número válido', str(context.exception))


class LocationUrlsTests(SimpleTestCase):
	def test_public_endpoints_are_reversible(self):
		self.assertEqual(reverse('regions-list'), '/api/locations/regions/')
		self.assertEqual(reverse('regions-with-comunas'), '/api/locations/regions-with-comunas/')
		self.assertEqual(reverse('comunas-list'), '/api/locations/comunas/')
		self.assertEqual(reverse('comunas-chilexpress-list'), '/api/locations/comunas-chilexpress/')
		self.assertEqual(reverse('sucursales-list'), '/api/locations/sucursales/')
		self.assertEqual(reverse('sucursal-detail', kwargs={'pk': 10}), '/api/locations/sucursales/10/')
