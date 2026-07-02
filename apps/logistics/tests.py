from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from django.test import SimpleTestCase
from django.urls import reverse

from apps.inventory.models import Producto
from .models import ChilexpressApiLog, Despacho
from .serializers import (
	ActualizarEstadoDespachoSerializer,
	CotizacionInputSerializer,
	CrearEnvioInputSerializer,
	_dimensiones_desde_resultado_empaque,
	_productos_a_lista_empaque,
	_productos_ids_a_lista_empaque,
)
from .utils import calcular_caja_optima, dimensiones_a_chilexpress, mg_a_kg, mm_a_cm


def _make_request(user_groups=None):
	user = SimpleNamespace(
		groups=SimpleNamespace(values_list=Mock(return_value=user_groups or [])),
	)
	return SimpleNamespace(user=user)


def _make_queryset_mock():
	queryset = Mock(name='QuerySet')
	queryset.filter.return_value = queryset
	queryset.exists.return_value = False
	queryset.values.return_value = []
	queryset.values_list.return_value = []
	queryset.select_related.return_value = queryset
	queryset.first.return_value = None
	return queryset


class LogisticsModelTests(SimpleTestCase):
	def test_model_str_and_metadata(self):
		despacho = Despacho(pedido_id=1, courier_nombre='Chilexpress', numero_seguimiento='OT-1')
		log = ChilexpressApiLog(method='POST', endpoint='/cotizar/', status_code=200)

		self.assertFalse(Despacho._meta.managed)
		self.assertEqual(str(log), 'POST /cotizar/ - 200')
		self.assertEqual(despacho.estado_envio, 'PENDIENTE')
		self.assertEqual(despacho.tipo_despacho, 'NORMAL')

	def test_choice_sets_include_expected_values(self):
		self.assertIn(('PENDIENTE', 'Pendiente'), Despacho.ESTADO_CHOICES)
		self.assertIn(('NORMAL', 'Normal'), Despacho.TIPO_CHOICES)
		self.assertIn(('GET', 'GET'), ChilexpressApiLog.METHOD_CHOICES)


class LogisticsUtilsTests(SimpleTestCase):
	def test_mg_a_kg_converts_and_rounds_up(self):
		self.assertEqual(mg_a_kg(1), '0.01')
		self.assertEqual(mg_a_kg(9999), '0.01')
		self.assertEqual(mg_a_kg(1000000), '1.00')
		self.assertEqual(mg_a_kg(1234500), '1.24')

	def test_mm_a_cm_converts_default_and_decimal(self):
		self.assertEqual(mm_a_cm(0), '1.0')
		self.assertEqual(mm_a_cm(10), '1.0')
		self.assertEqual(mm_a_cm(125), '12.5')

	def test_dimensiones_a_chilexpress_maps_all_fields(self):
		self.assertEqual(
			dimensiones_a_chilexpress(peso_mg=1500000, largo_mm=120, ancho_mm=80, alto_mm=50),
			{'weight': '1.50', 'height': '5.0', 'width': '8.0', 'length': '12.0'},
		)

	def test_calcular_caja_optima_returns_empty_when_no_products(self):
		self.assertEqual(calcular_caja_optima([], [{'nombre': 'Caja S', 'largo_mm': 100, 'ancho_mm': 100, 'alto_mm': 100, 'volumen_ml': 1000}]), [])

	def test_calcular_caja_optima_rejects_when_no_boxes(self):
		with self.assertRaises(ValueError) as context:
			calcular_caja_optima([{'id': 'p1', 'largo_mm': 10, 'ancho_mm': 10, 'alto_mm': 10, 'peso_mg': 100}], [])
		self.assertIn('No hay cajas disponibles', str(context.exception))

	def test_calcular_caja_optima_uses_smallest_box_that_fits(self):
		productos = [{'id': 'p1', 'largo_mm': 10, 'ancho_mm': 10, 'alto_mm': 10, 'peso_mg': 100}]
		cajas = [
			{'nombre': 'Caja XS', 'largo_mm': 40, 'ancho_mm': 40, 'alto_mm': 40, 'volumen_ml': 1000},
			{'nombre': 'Caja L', 'largo_mm': 100, 'ancho_mm': 100, 'alto_mm': 100, 'volumen_ml': 10000},
		]

		resultado = calcular_caja_optima(productos, cajas)

		self.assertEqual(resultado, [{'caja': 'Caja XS', 'productos_dentro': ['p1']}])

	def test_calcular_caja_optima_fails_when_product_does_not_fit_any_box(self):
		productos = [{'id': 'p1', 'largo_mm': 1000, 'ancho_mm': 1000, 'alto_mm': 1000, 'peso_mg': 100}]
		cajas = [{'nombre': 'Caja XS', 'largo_mm': 40, 'ancho_mm': 40, 'alto_mm': 40, 'volumen_ml': 1000}]

		with self.assertRaises(ValueError) as context:
			calcular_caja_optima(productos, cajas)

		self.assertIn('p1', str(context.exception))


class LogisticsSerializerHelperTests(SimpleTestCase):
	def test_productos_a_lista_empaque_expande_cantidad(self):
		detalles = [
			SimpleNamespace(
				cantidad=2,
				producto=SimpleNamespace(sku='SKU1', largo_mm=10, ancho_mm=20, alto_mm=30, peso_mg=40),
			)
		]

		resultado = _productos_a_lista_empaque(detalles)

		self.assertEqual(
			resultado,
			[
				{'id': 'SKU1-0', 'largo_mm': 10, 'ancho_mm': 20, 'alto_mm': 30, 'peso_mg': 40},
				{'id': 'SKU1-1', 'largo_mm': 10, 'ancho_mm': 20, 'alto_mm': 30, 'peso_mg': 40},
			],
		)

	def test_productos_ids_a_lista_empaque_expands_repeated_ids(self):
		productos_por_id = {
			1: Producto(sku='SKU1', nombre='Producto 1', largo_mm=10, ancho_mm=20, alto_mm=30, peso_mg=40),
		}

		resultado = _productos_ids_a_lista_empaque(productos_por_id, [1, 1])

		self.assertEqual(
			resultado,
			[
				{'id': 'SKU1-1', 'largo_mm': 10, 'ancho_mm': 20, 'alto_mm': 30, 'peso_mg': 40},
				{'id': 'SKU1-2', 'largo_mm': 10, 'ancho_mm': 20, 'alto_mm': 30, 'peso_mg': 40},
			],
		)

	def test_dimensiones_desde_resultado_empaque_chooses_largest_box(self):
		resultado = [
			{'caja': 'Caja S', 'productos_dentro': ['p1']},
			{'caja': 'Caja L', 'productos_dentro': ['p2']},
		]
		cajas_bd = [
			{'nombre': 'Caja S', 'largo_mm': 100, 'ancho_mm': 80, 'alto_mm': 60, 'volumen_ml': 1000},
			{'nombre': 'Caja L', 'largo_mm': 200, 'ancho_mm': 150, 'alto_mm': 120, 'volumen_ml': 5000},
		]

		self.assertEqual(
			_dimensiones_desde_resultado_empaque(resultado, cajas_bd),
			{'largo_mm': 200, 'ancho_mm': 150, 'alto_mm': 120},
		)


class CotizacionInputSerializerTests(SimpleTestCase):
	def test_validate_requires_sucursal_or_pedido(self):
		serializer = CotizacionInputSerializer(data={'county_code_destino': '123'})

		self.assertFalse(serializer.is_valid())
		self.assertIn('sucursal_id', str(serializer.errors))

	def test_validate_rejects_missing_products_when_no_pedido(self):
		with patch('apps.logistics.serializers.Producto.objects') as producto_objects, patch('apps.logistics.serializers.ComunaChilexpress.objects') as cx_objects:
			producto_objects.filter.return_value.values_list.return_value = []
			cx_objects.filter.return_value.exists.return_value = True
			serializer = CotizacionInputSerializer(data={'sucursal_id': 1, 'county_code_destino': 'DEST'})

			self.assertFalse(serializer.is_valid())
			self.assertIn('productos_ids', str(serializer.errors))

	def test_validate_success_and_payload_manual_mode(self):
		sucursal = SimpleNamespace(nombre='Central', comuna=SimpleNamespace(id=10), telefono='9999')
		producto = Producto(pk=1, sku='SKU1', nombre='Producto 1', peso_mg=50, valor_unitario=2000, largo_mm=10, ancho_mm=20, alto_mm=30)

		with patch('apps.logistics.serializers.Producto.objects') as producto_objects, \
			patch('apps.logistics.serializers.ComunaChilexpress.objects') as cx_objects, \
			patch('apps.logistics.serializers.Sucursal.objects') as sucursal_objects, \
			patch('apps.logistics.serializers.calcular_caja_optima') as calcular_mock, \
			patch('apps.logistics.serializers.dimensiones_a_chilexpress') as dims_mock:

			producto_qs = MagicMock()
			producto_qs.values_list.return_value = [1]
			producto_qs.values.return_value = [
				{'nombre': 'Caja S', 'largo_mm': 100, 'ancho_mm': 100, 'alto_mm': 100, 'volumen_ml': 1000}
			]
			producto_qs.__iter__.return_value = iter([producto])
			producto_objects.filter.return_value = producto_qs
			cx_objects.filter.return_value.exists.return_value = True
			cx_objects.filter.return_value.first.return_value = SimpleNamespace(county_code='ORIG')
			sucursal_objects.get.return_value = sucursal
			calcular_mock.return_value = [{'caja': 'Caja S', 'productos_dentro': ['SKU1-1']}]
			dims_mock.return_value = {'weight': '0.01', 'height': '10.0', 'width': '10.0', 'length': '10.0'}

			serializer = CotizacionInputSerializer(data={
				'sucursal_id': 1,
				'productos_ids': [1, 1],
				'county_code_destino': 'DEST',
			})

			self.assertTrue(serializer.is_valid(), serializer.errors)
			payload, num_cajas = serializer.get_payload_chilexpress()

		self.assertEqual(num_cajas, 1)
		self.assertEqual(payload['originCountyCode'], 'ORIG')
		self.assertEqual(payload['destinationCountyCode'], 'DEST')
		self.assertEqual(payload['declaredWorth'], '4000')
		self.assertEqual(payload['package'], {'weight': '0.01', 'height': '10.0', 'width': '10.0', 'length': '10.0'})
		calcular_mock.assert_called_once()

	def test_validate_success_and_payload_pedido_mode(self):
		pedido = SimpleNamespace(id=7, total=1500, sucursal_origen=SimpleNamespace(nombre='Origen', comuna=SimpleNamespace(id=1)))
		detalle = SimpleNamespace(cantidad=2, producto=SimpleNamespace(sku='SKU1', peso_mg=100, largo_mm=10, ancho_mm=20, alto_mm=30))

		pedido_queryset = _make_queryset_mock()
		pedido_queryset.exists.return_value = True
		productos_filter_queryset = _make_queryset_mock()
		detalles_filter_queryset = _make_queryset_mock()

		with patch('apps.logistics.serializers.Pedido.objects') as pedido_objects, \
			patch('apps.logistics.serializers.DetallePedido.objects') as detalle_objects, \
			patch('apps.logistics.serializers.Producto.objects') as producto_objects, \
			patch('apps.logistics.serializers.ComunaChilexpress.objects') as cx_objects, \
			patch('apps.logistics.serializers.calcular_caja_optima') as calcular_mock, \
			patch('apps.logistics.serializers.dimensiones_a_chilexpress') as dims_mock:

			pedido_objects.filter.return_value.exists.return_value = True
			pedido_objects.get.return_value = pedido
			producto_objects.filter.return_value.values.return_value = [
				{'nombre': 'Caja S', 'largo_mm': 100, 'ancho_mm': 100, 'alto_mm': 100, 'volumen_ml': 1000}
			]
			detalle_objects.filter.return_value.select_related.return_value = [detalle]
			cx_objects.filter.return_value.exists.return_value = True
			cx_objects.filter.return_value.first.return_value = SimpleNamespace(county_code='ORIG')
			calcular_mock.return_value = [{'caja': 'Caja S', 'productos_dentro': ['SKU1-1']}]
			dims_mock.return_value = {'weight': '0.01', 'height': '10.0', 'width': '10.0', 'length': '10.0'}

			serializer = CotizacionInputSerializer(data={'pedido_id': 7, 'county_code_destino': 'DEST'})

			self.assertTrue(serializer.is_valid(), serializer.errors)
			payload, num_cajas = serializer.get_payload_chilexpress()

		self.assertEqual(num_cajas, 1)
		self.assertEqual(payload['originCountyCode'], 'ORIG')
		self.assertEqual(payload['destinationCountyCode'], 'DEST')
		self.assertEqual(payload['declaredWorth'], '1500')


class CrearEnvioInputSerializerTests(SimpleTestCase):
	def test_validate_pedido_id_requires_aprobado_or_en_picking(self):
		pedido = SimpleNamespace(estado_pedido='PENDIENTE')

		with patch('apps.logistics.serializers.Pedido.objects') as pedido_objects:
			pedido_objects.select_related.return_value.get.return_value = pedido
			serializer = CrearEnvioInputSerializer(data={'pedido_id': 1, 'service_type_code': 3})

			self.assertFalse(serializer.is_valid())
			self.assertIn('APROBADO o EN_PICKING', str(serializer.errors))

	def test_validate_pedido_id_rejects_when_despacho_exists(self):
		pedido = SimpleNamespace(estado_pedido='APROBADO')

		with patch('apps.logistics.serializers.Pedido.objects') as pedido_objects, patch('apps.logistics.serializers.Despacho.objects') as despacho_objects:
			pedido_objects.select_related.return_value.get.return_value = pedido
			despacho_objects.filter.return_value.exists.return_value = True
			serializer = CrearEnvioInputSerializer(data={'pedido_id': 1, 'service_type_code': 3})

			self.assertFalse(serializer.is_valid())
			self.assertIn('ya tiene un despacho', str(serializer.errors))


class ActualizarEstadoDespachoSerializerTests(SimpleTestCase):
	def test_validate_allows_valid_admin_transition(self):
		despacho = SimpleNamespace(estado_envio='PENDIENTE')
		serializer = ActualizarEstadoDespachoSerializer(
			data={'nuevo_estado': 'RETIRADO'},
			context={'despacho': despacho, 'request': _make_request(['Administradores'])},
		)

		self.assertTrue(serializer.is_valid(), serializer.errors)

	def test_validate_rejects_users_without_authorized_role(self):
		despacho = SimpleNamespace(estado_envio='PENDIENTE')
		serializer = ActualizarEstadoDespachoSerializer(
			data={'nuevo_estado': 'RETIRADO'},
			context={'despacho': despacho, 'request': _make_request([])},
		)

		self.assertFalse(serializer.is_valid())
		self.assertIn('rol autorizado', str(serializer.errors))

	def test_validate_rejects_invalid_transition_for_role(self):
		despacho = SimpleNamespace(estado_envio='RETIRADO')
		serializer = ActualizarEstadoDespachoSerializer(
			data={'nuevo_estado': 'CANCELADO'},
			context={'despacho': despacho, 'request': _make_request(['OperadoresLogisticos'])},
		)

		self.assertFalse(serializer.is_valid())
		self.assertIn('no puede cambiar el estado', str(serializer.errors))


class LogisticsUrlsTests(SimpleTestCase):
	def test_public_endpoints_are_reversible(self):
		self.assertEqual(reverse('logistics-cotizar'), '/api/logistics/cotizar/')
		self.assertEqual(reverse('logistics-crear-envio'), '/api/logistics/envios/')
		self.assertEqual(reverse('logistics-tracking', kwargs={'pedido_id': 10}), '/api/logistics/envios/10/tracking/')
		self.assertEqual(reverse('logistics-actualizar-estado', kwargs={'pedido_id': 10}), '/api/logistics/envios/10/estado/')
