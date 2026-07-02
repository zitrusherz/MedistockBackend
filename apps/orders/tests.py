from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import PerfilCliente, PerfilTrabajador
from apps.orders.permissions import (
	ClientePuedeEditarPedidoHastaAprobado,
	EsPedidoPropioOTrabajador,
)
from apps.orders.serializers import (
	CrearPedidoInputSerializer,
	DetallePedidoInputSerializer,
	PedidoClienteUpdateSerializer,
	PedidoOutputSerializer,
)
from apps.orders.services.inventario import (
	consumir_reserva_pedido,
	reservar_stock_pedido,
)
from apps.orders.views import (
	AprobarPedidoView,
	CrearPedidoView,
	DetallePedidoView,
	ListarPedidosView,
	MisPedidosView,
	ResumenCotizacionesView,
	_calcular_montos,
	_elegir_lote,
)


def _group_manager(*group_names):
	manager = Mock()

	def _filter(*args, **kwargs):
		requested = kwargs.get("name")
		requested_many = kwargs.get("name__in") or []
		if requested is not None:
			allowed = requested in group_names
		else:
			allowed = any(name in group_names for name in requested_many)

		result = Mock()
		result.exists.return_value = allowed
		return result

	manager.filter.side_effect = _filter
	return manager


def _make_user(
	*,
	username="usuario",
	groups=(),
	is_authenticated=True,
	is_staff=False,
	perfil_cliente_id=None,
	full_name="",
):
	user = SimpleNamespace(
		username=username,
		is_authenticated=is_authenticated,
		is_staff=is_staff,
		groups=_group_manager(*groups),
		get_full_name=Mock(return_value=full_name),
	)
	if perfil_cliente_id is not None:
		user.perfilcliente = SimpleNamespace(id=perfil_cliente_id, usuario=user)
	return user


def _make_request(*, user=None, data=None, method="GET"):
	return SimpleNamespace(
		user=user or _make_user(),
		data=data or {},
		method=method,
	)


def _call_unwrapped(func, *args, **kwargs):
	target = getattr(func, "__wrapped__", func)
	return target(*args, **kwargs)


class OrdersHelperTests(SimpleTestCase):
	def test_calcular_montos_suma_subtotales_y_descuentos(self):
		resultado = _calcular_montos(
			[
				{"_precio_unitario": 1000, "cantidad": 2, "descuento": 100},
				{"_precio_unitario": 500, "cantidad": 1},
			]
		)

		self.assertEqual(
			resultado,
			{
				"subtotal": 2500,
				"descuento_total": 200,
				"monto_neto": 2300,
				"monto_iva": 437,
				"total": 2737,
			},
		)

	def test_elegir_lote_devuelve_primer_inventario_disponible(self):
		inventario = SimpleNamespace(lote_id=44)
		inventario_qs = Mock()
		inventario_qs.order_by.return_value.select_related.return_value.first.return_value = inventario

		with patch("apps.orders.views.Inventario.objects.filter", return_value=inventario_qs) as filter_mock:
			resultado = _elegir_lote(producto_id=9, cantidad=3)

		self.assertIs(resultado, inventario)
		filter_mock.assert_called_once()


class OrdersPermissionTests(SimpleTestCase):
	def test_es_pedido_propio_o_trabajador_allows_staff(self):
		request = _make_request(user=_make_user(is_staff=True), method="GET")
		permiso = EsPedidoPropioOTrabajador()

		self.assertTrue(permiso.has_object_permission(request, None, SimpleNamespace(cliente_id=1)))

	def test_es_pedido_propio_o_trabajador_allows_owner_client(self):
		request = _make_request(user=_make_user(perfil_cliente_id=7), method="GET")
		permiso = EsPedidoPropioOTrabajador()

		self.assertTrue(permiso.has_object_permission(request, None, SimpleNamespace(cliente_id=7)))

	def test_es_pedido_propio_o_trabajador_denies_foreign_client(self):
		request = _make_request(user=_make_user(perfil_cliente_id=7), method="GET")
		permiso = EsPedidoPropioOTrabajador()

		self.assertFalse(permiso.has_object_permission(request, None, SimpleNamespace(cliente_id=9)))

	def test_cliente_puede_editar_hasta_aprobado_allows_safe_methods(self):
		request = _make_request(user=_make_user(perfil_cliente_id=1), method="GET")
		permiso = ClientePuedeEditarPedidoHastaAprobado()

		self.assertTrue(permiso.has_object_permission(request, None, SimpleNamespace(cliente_id=2, estado_pedido="CANCELADO")))

	def test_cliente_puede_editar_hasta_aprobado_allows_owner_pending(self):
		request = _make_request(user=_make_user(perfil_cliente_id=1), method="PATCH")
		permiso = ClientePuedeEditarPedidoHastaAprobado()

		self.assertTrue(permiso.has_object_permission(request, None, SimpleNamespace(cliente_id=1, estado_pedido="PENDIENTE")))

	def test_cliente_puede_editar_hasta_aprobado_denies_closed_state(self):
		request = _make_request(user=_make_user(perfil_cliente_id=1), method="PATCH")
		permiso = ClientePuedeEditarPedidoHastaAprobado()

		self.assertFalse(permiso.has_object_permission(request, None, SimpleNamespace(cliente_id=1, estado_pedido="CANCELADO")))


class OrdersSerializerTests(SimpleTestCase):
	def test_detalle_pedido_input_serializer_rejects_inactive_product(self):
		with patch("apps.orders.serializers.Producto.objects.filter") as filter_mock:
			filter_mock.return_value.exists.return_value = False
			serializer = DetallePedidoInputSerializer(data={"producto_id": 10, "cantidad": 1})

			self.assertFalse(serializer.is_valid())
			self.assertIn("No existe un producto activo", str(serializer.errors))

	def test_detalle_pedido_input_serializer_accepts_active_product(self):
		with patch("apps.orders.serializers.Producto.objects.filter") as filter_mock:
			filter_mock.return_value.exists.return_value = True
			serializer = DetallePedidoInputSerializer(data={"producto_id": 10, "cantidad": 1})

			self.assertTrue(serializer.is_valid(), serializer.errors)

	def test_crear_pedido_input_serializer_rejects_missing_cliente_profile(self):
		request = _make_request(user=_make_user())
		payload = {
			"sucursal_origen_id": 1,
			"direccion_entrega_id": 2,
			"tipo_venta": "WEBPAY",
			"detalles": [{"producto_id": 10, "cantidad": 1}],
		}

		with patch("apps.orders.serializers.DetallePedidoInputSerializer.validate_producto_id", side_effect=lambda value: value), \
			patch("apps.orders.serializers.Sucursal.objects.get", return_value=SimpleNamespace(id=1, activo=True)), \
			patch("apps.orders.serializers.DireccionEntrega.objects.filter") as direccion_filter, \
			patch("apps.orders.serializers.PerfilCliente.objects.get", side_effect=PerfilCliente.DoesNotExist):

			direccion_filter.return_value.exists.return_value = True
			serializer = CrearPedidoInputSerializer(data=payload, context={"request": request})

			self.assertFalse(serializer.is_valid())
			self.assertIn("perfil de cliente", str(serializer.errors))

	def test_crear_pedido_input_serializer_rejects_foreign_delivery_address(self):
		request = _make_request(user=_make_user(perfil_cliente_id=5))
		payload = {
			"sucursal_origen_id": 1,
			"direccion_entrega_id": 2,
			"tipo_venta": "WEBPAY",
			"detalles": [{"producto_id": 10, "cantidad": 1}],
		}

		direccion_ok = Mock()
		direccion_ok.exists.return_value = True
		direccion_bad = Mock()
		direccion_bad.exists.return_value = False

		with patch("apps.orders.serializers.DetallePedidoInputSerializer.validate_producto_id", side_effect=lambda value: value), \
			patch("apps.orders.serializers.Sucursal.objects.get", return_value=SimpleNamespace(id=1, activo=True)), \
			patch("apps.orders.serializers.DireccionEntrega.objects.filter", side_effect=[direccion_ok, direccion_bad]), \
			patch("apps.orders.serializers.PerfilCliente.objects.get", return_value=SimpleNamespace(id=5)):

			serializer = CrearPedidoInputSerializer(data=payload, context={"request": request})

			self.assertFalse(serializer.is_valid())
			self.assertIn("no pertenece al cliente autenticado", str(serializer.errors))

	def test_crear_pedido_input_serializer_rejects_insufficient_stock_without_lote(self):
		request = _make_request(user=_make_user(perfil_cliente_id=5))
		payload = {
			"sucursal_origen_id": 1,
			"direccion_entrega_id": 2,
			"tipo_venta": "WEBPAY",
			"detalles": [{"producto_id": 10, "cantidad": 8}],
		}

		direccion_ok = Mock()
		direccion_ok.exists.return_value = True
		inventario_qs = Mock()
		inventario_qs.values_list.return_value = [(5, 1)]

		with patch("apps.orders.serializers.DetallePedidoInputSerializer.validate_producto_id", side_effect=lambda value: value), \
			patch("apps.orders.serializers.Sucursal.objects.get", return_value=SimpleNamespace(id=1, activo=True)), \
			patch("apps.orders.serializers.DireccionEntrega.objects.filter", side_effect=[direccion_ok, direccion_ok]), \
			patch("apps.orders.serializers.PerfilCliente.objects.get", return_value=SimpleNamespace(id=5)), \
			patch("apps.orders.serializers.Inventario.objects.filter", return_value=inventario_qs):

			serializer = CrearPedidoInputSerializer(data=payload, context={"request": request})

			self.assertFalse(serializer.is_valid())
			self.assertIn("stock insuficiente", str(serializer.errors))

	def test_crear_pedido_input_serializer_accepts_valid_payload(self):
		request = _make_request(user=_make_user(perfil_cliente_id=5))
		payload = {
			"sucursal_origen_id": 1,
			"direccion_entrega_id": 2,
			"tipo_venta": "WEBPAY",
			"tipo_despacho": "NORMAL",
			"prioridad_medica": "ALTA",
			"observacion": "urgente",
			"detalles": [{"producto_id": 10, "cantidad": 2}],
		}

		direccion_ok = Mock()
		direccion_ok.exists.return_value = True
		inventario_qs = Mock()
		inventario_qs.values_list.return_value = [(10, 1)]

		with patch("apps.orders.serializers.DetallePedidoInputSerializer.validate_producto_id", side_effect=lambda value: value), \
			patch("apps.orders.serializers.Sucursal.objects.get", return_value=SimpleNamespace(id=1, activo=True)) as sucursal_get, \
			patch("apps.orders.serializers.DireccionEntrega.objects.filter", side_effect=[direccion_ok, direccion_ok]), \
			patch("apps.orders.serializers.PerfilCliente.objects.get", return_value=SimpleNamespace(id=5)) as perfil_get, \
			patch("apps.orders.serializers.Inventario.objects.filter", return_value=inventario_qs):

			serializer = CrearPedidoInputSerializer(data=payload, context={"request": request})

			self.assertTrue(serializer.is_valid(), serializer.errors)
			self.assertEqual(serializer._perfil_cliente.id, 5)
			self.assertEqual(serializer._sucursal.id, 1)
			perfil_get.assert_called_once()
			sucursal_get.assert_called_once()

	def test_pedido_output_serializer_mapea_cliente_detalles_y_lote(self):
		producto = SimpleNamespace(id=7, sku="SKU-1", nombre="Producto 1")
		lote = SimpleNamespace(id=11, codigo_lote="L-11")
		detalle = SimpleNamespace(
			id=21,
			producto_id=7,
			producto=producto,
			lote_id=11,
			lote=lote,
			cantidad=2,
			cantidad_preparada=1,
			precio_unitario_historico=500,
			descuento=10,
			subtotal=980,
			observacion="nota",
		)
		usuario = SimpleNamespace(username="juan", get_full_name=Mock(return_value=""))
		pedido = SimpleNamespace(
			id=1,
			cliente=SimpleNamespace(id=3, usuario=usuario),
			sucursal_origen=SimpleNamespace(id=2, nombre="Central"),
			direccion_entrega_id=9,
			estado_pedido="PENDIENTE",
			tipo_venta="WEBPAY",
			tipo_despacho="NORMAL",
			prioridad_medica="NORMAL",
			fecha_creacion=timezone.now(),
			fecha_actualizacion=timezone.now(),
			fecha_requerida_entrega=None,
			subtotal=1000,
			descuento_total=20,
			monto_neto=980,
			monto_iva=186,
			total=1166,
			observacion="ok",
			detallepedido_set=[detalle],
		)

		data = PedidoOutputSerializer(pedido).data

		self.assertEqual(data["cliente_nombre"], "juan")
		self.assertEqual(data["sucursal_nombre"], "Central")
		self.assertEqual(data["detalles"][0]["lote_codigo"], "L-11")

	def test_pedido_cliente_update_serializer_rejects_foreign_address(self):
		request = _make_request(user=_make_user(perfil_cliente_id=1), method="PATCH")
		serializer = PedidoClienteUpdateSerializer(context={"request": request})
		direccion = SimpleNamespace(cliente_id=2)

		with self.assertRaises(ValidationError) as context:
			serializer.validate_direccion_entrega(direccion)

		self.assertIn("no pertenece al cliente autenticado", str(context.exception))

	def test_pedido_cliente_update_serializer_rejects_non_editable_state(self):
		request = _make_request(user=_make_user(perfil_cliente_id=1), method="PATCH")
		pedido = SimpleNamespace(cliente_id=1, estado_pedido="CANCELADO")
		serializer = PedidoClienteUpdateSerializer(instance=pedido, context={"request": request})

		with self.assertRaises(ValidationError) as context:
			serializer.validate({})

		self.assertIn("ya no puede ser modificado", str(context.exception))


class OrdersServiceTests(SimpleTestCase):
	def test_reservar_stock_pedido_actualiza_reserva_y_crea_movimiento(self):
		pedido = SimpleNamespace(id=100, cliente=SimpleNamespace(usuario=SimpleNamespace(username="cliente")))
		detalle = SimpleNamespace(lote_id=7, cantidad=3)
		detalle_qs = Mock()
		detalle_qs.select_related.return_value = [detalle]
		inventario = SimpleNamespace(
			cantidad_disponible=10,
			cantidad_reservada=2,
			sucursal_id=4,
			save=Mock(),
		)
		inventario_qs = Mock()
		inventario_qs.filter.return_value.first.return_value = inventario

		with patch("apps.orders.services.inventario.DetallePedido.objects.filter", return_value=detalle_qs), \
			patch("apps.orders.services.inventario.Inventario.objects.select_for_update", return_value=inventario_qs), \
			patch("apps.orders.services.inventario.MovimientoInventario.objects.create") as movimiento_create:

			_call_unwrapped(reservar_stock_pedido, pedido)

		self.assertEqual(inventario.cantidad_reservada, 5)
		inventario.save.assert_called_once_with(update_fields=["cantidad_reservada", "fecha_actualizacion"])
		movimiento_create.assert_called_once()

	def test_consumir_reserva_pedido_devuelve_false_si_ya_existe_salida(self):
		pedido = SimpleNamespace(id=200)

		with patch("apps.orders.services.inventario.MovimientoInventario.objects.filter") as filter_mock:
			filter_mock.return_value.exists.return_value = True
			resultado = _call_unwrapped(consumir_reserva_pedido, pedido)

		self.assertFalse(resultado)


class OrdersViewTests(SimpleTestCase):
	def test_crear_pedido_view_returns_201_and_creates_details(self):
		user = _make_user(perfil_cliente_id=5)
		request = _make_request(user=user, data={"detalles": [{"producto_id": 10, "cantidad": 2}]}, method="POST")
		perfil_cliente = SimpleNamespace(id=5)
		inventario = SimpleNamespace(lote_id=321)
		pedido = SimpleNamespace(id=99)
		serializer_instance = Mock()
		serializer_instance.is_valid.return_value = True
		serializer_instance.validated_data = {
			"sucursal_origen_id": 1,
			"direccion_entrega_id": 2,
			"tipo_venta": "WEBPAY",
			"tipo_despacho": "NORMAL",
			"prioridad_medica": "NORMAL",
			"observacion": "nota",
			"detalles": [{"producto_id": 10, "cantidad": 2, "observacion": "obs"}],
		}
		serializer_instance._perfil_cliente = perfil_cliente

		with patch("apps.orders.views.CrearPedidoInputSerializer", return_value=serializer_instance), \
			patch("apps.orders.views._calcular_montos", return_value={"subtotal": 2000, "descuento_total": 0, "monto_neto": 2000, "monto_iva": 380, "total": 2380}), \
			patch("apps.inventory.models.Producto.objects.get", return_value=SimpleNamespace(valor_unitario=1000)), \
			patch("apps.orders.views._elegir_lote", return_value=inventario), \
			patch("apps.orders.views.Pedido.objects.create", return_value=pedido) as pedido_create, \
			patch("apps.orders.views.DetallePedido.objects.create") as detalle_create, \
			patch("apps.orders.views.reservar_stock_pedido") as reservar_mock, \
			patch("apps.orders.views.PedidoOutputSerializer") as output_serializer:

			output_serializer.return_value.data = {"id": 99, "total": 2380}
			response = _call_unwrapped(CrearPedidoView.post, CrearPedidoView(), request)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data, {"id": 99, "total": 2380})
		pedido_create.assert_called_once()
		detalle_create.assert_called_once_with(
			pedido=pedido,
			producto_id=10,
			lote_id=321,
			cantidad=2,
			precio_unitario_historico=1000,
			descuento=0,
			subtotal=2000,
			observacion="obs",
		)
		reservar_mock.assert_called_once_with(pedido, request.user)

	def test_crear_pedido_view_returns_409_when_stock_reservation_fails(self):
		user = _make_user(perfil_cliente_id=5)
		request = _make_request(user=user, data={"detalles": [{"producto_id": 10, "cantidad": 2}]}, method="POST")
		perfil_cliente = SimpleNamespace(id=5)
		inventario = SimpleNamespace(lote_id=321)
		pedido = SimpleNamespace(id=99)
		serializer_instance = Mock()
		serializer_instance.is_valid.return_value = True
		serializer_instance.validated_data = {
			"sucursal_origen_id": 1,
			"direccion_entrega_id": 2,
			"tipo_venta": "WEBPAY",
			"detalles": [{"producto_id": 10, "cantidad": 2}],
		}
		serializer_instance._perfil_cliente = perfil_cliente

		with patch("apps.orders.views.CrearPedidoInputSerializer", return_value=serializer_instance), \
			patch("apps.orders.views._calcular_montos", return_value={"subtotal": 2000, "descuento_total": 0, "monto_neto": 2000, "monto_iva": 380, "total": 2380}), \
			patch("apps.inventory.models.Producto.objects.get", return_value=SimpleNamespace(valor_unitario=1000)), \
			patch("apps.orders.views._elegir_lote", return_value=inventario), \
			patch("apps.orders.views.Pedido.objects.create", return_value=pedido), \
			patch("apps.orders.views.DetallePedido.objects.create"), \
			patch("apps.orders.views.reservar_stock_pedido", side_effect=ValidationError({"stock": "sin stock"})), \
			patch("apps.orders.views.transaction.set_rollback") as rollback_mock:

			response = _call_unwrapped(CrearPedidoView.post, CrearPedidoView(), request)

		self.assertEqual(response.status_code, 409)
		self.assertEqual(response.data, {"stock": "sin stock"})
		rollback_mock.assert_called_once_with(True)

	def test_detalle_pedido_view_get_returns_404_when_missing(self):
		view = DetallePedidoView()
		request = _make_request(user=_make_user(perfil_cliente_id=1))

		with patch.object(view, "get_object", return_value=None):
			response = view.get(request, 44)

		self.assertEqual(response.status_code, 404)

	def test_detalle_pedido_view_get_returns_serializer_payload(self):
		view = DetallePedidoView()
		request = _make_request(user=_make_user(perfil_cliente_id=1))
		pedido = SimpleNamespace(id=44)

		with patch.object(view, "get_object", return_value=pedido), patch("apps.orders.views.PedidoOutputSerializer") as serializer_mock:
			serializer_mock.return_value.data = {"id": 44}
			response = view.get(request, 44)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data, {"id": 44})

	def test_detalle_pedido_view_patch_updates_client_order(self):
		view = DetallePedidoView()
		request = _make_request(user=_make_user(perfil_cliente_id=1), data={"observacion": "cambio"}, method="PATCH")
		pedido = SimpleNamespace(id=44, estado_pedido="PENDIENTE", refresh_from_db=Mock())
		serializer_instance = Mock()
		serializer_instance.is_valid.return_value = True
		serializer_instance.save.return_value = None

		with patch.object(view, "get_object", return_value=pedido), \
			patch("apps.orders.views.PedidoClienteUpdateSerializer", return_value=serializer_instance) as update_serializer, \
			patch("apps.orders.views.PedidoOutputSerializer") as output_serializer:

			output_serializer.return_value.data = {"id": 44, "observacion": "cambio"}
			response = view.patch(request, 44)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data, {"id": 44, "observacion": "cambio"})
		update_serializer.assert_called_once()
		pedido.refresh_from_db.assert_called_once()

	def test_detalle_pedido_view_patch_forbids_non_client_users(self):
		view = DetallePedidoView()
		request = _make_request(user=_make_user(groups=("Ejecutivo",)), data={"observacion": "x"}, method="PATCH")
		pedido = SimpleNamespace(id=44)

		with patch.object(view, "get_object", return_value=pedido):
			response = view.patch(request, 44)

		self.assertEqual(response.status_code, 403)

	def test_aprobar_pedido_view_rejects_unauthorized_roles(self):
		view = AprobarPedidoView()
		request = _make_request(user=_make_user(), data={"accion": "APROBADO"}, method="POST")

		response = _call_unwrapped(AprobarPedidoView.post, view, request, 44)

		self.assertEqual(response.status_code, 403)

	def test_aprobar_pedido_view_rejects_when_worker_profile_missing(self):
		view = AprobarPedidoView()
		request = _make_request(user=_make_user(groups=("Ejecutivo",)), data={"accion": "APROBADO"}, method="POST")

		with patch("apps.orders.views.PerfilTrabajador.objects.get", side_effect=PerfilTrabajador.DoesNotExist):
			response = _call_unwrapped(AprobarPedidoView.post, view, request, 44)

		self.assertEqual(response.status_code, 403)

	def test_aprobar_pedido_view_rejects_non_pending_orders(self):
		view = AprobarPedidoView()
		request = _make_request(user=_make_user(groups=("Ejecutivo",)), data={"accion": "APROBADO"}, method="POST")
		pedido = SimpleNamespace(id=44, estado_pedido="CANCELADO")

		with patch("apps.orders.views.PerfilTrabajador.objects.get", return_value=SimpleNamespace(id=2)), \
			patch("apps.orders.views.Pedido.objects.get", return_value=pedido):

			response = _call_unwrapped(AprobarPedidoView.post, view, request, 44)

		self.assertEqual(response.status_code, 400)

	def test_aprobar_pedido_view_rejects_invalid_action(self):
		view = AprobarPedidoView()
		request = _make_request(user=_make_user(groups=("Ejecutivo",)), data={"accion": "OTRO"}, method="POST")
		pedido = SimpleNamespace(id=44, estado_pedido="PENDIENTE")

		with patch("apps.orders.views.PerfilTrabajador.objects.get", return_value=SimpleNamespace(id=2)), \
			patch("apps.orders.views.Pedido.objects.get", return_value=pedido):

			response = _call_unwrapped(AprobarPedidoView.post, view, request, 44)

		self.assertEqual(response.status_code, 400)

	def test_aprobar_pedido_view_approves_order_and_consumes_reservation(self):
		view = AprobarPedidoView()
		request = _make_request(user=_make_user(groups=("Ejecutivo",)), data={"accion": "APROBADO", "comentario": "ok"}, method="POST")
		pedido = SimpleNamespace(id=44, estado_pedido="PENDIENTE", save=Mock())

		with patch("apps.orders.views.PerfilTrabajador.objects.get", return_value=SimpleNamespace(id=2)), \
			patch("apps.orders.views.Pedido.objects.get", return_value=pedido), \
			patch("apps.orders.views.consumir_reserva_pedido") as consumir_mock, \
			patch("apps.orders.views.AprobacionPedido.objects.update_or_create") as update_mock:

			response = _call_unwrapped(AprobarPedidoView.post, view, request, 44)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(pedido.estado_pedido, "APROBADO")
		consumir_mock.assert_called_once_with(pedido, usuario=request.user, motivo="Aprobacion de pedido")
		update_mock.assert_called_once()

	def test_aprobar_pedido_view_rejects_order(self):
		view = AprobarPedidoView()
		request = _make_request(user=_make_user(groups=("Ejecutivo",)), data={"accion": "RECHAZADO", "comentario": "sin stock"}, method="POST")
		pedido = SimpleNamespace(id=44, estado_pedido="PENDIENTE", save=Mock())

		with patch("apps.orders.views.PerfilTrabajador.objects.get", return_value=SimpleNamespace(id=2)), \
			patch("apps.orders.views.Pedido.objects.get", return_value=pedido), \
			patch("apps.orders.views.AprobacionPedido.objects.update_or_create") as update_mock:

			response = _call_unwrapped(AprobarPedidoView.post, view, request, 44)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(pedido.estado_pedido, "CANCELADO")
		update_mock.assert_called_once()

	def test_aprobar_pedido_view_returns_409_when_consumption_fails(self):
		view = AprobarPedidoView()
		request = _make_request(user=_make_user(groups=("Ejecutivo",)), data={"accion": "APROBADO"}, method="POST")
		pedido = SimpleNamespace(id=44, estado_pedido="PENDIENTE", save=Mock())

		with patch("apps.orders.views.PerfilTrabajador.objects.get", return_value=SimpleNamespace(id=2)), \
			patch("apps.orders.views.Pedido.objects.get", return_value=pedido), \
			patch("apps.orders.views.consumir_reserva_pedido", side_effect=ValidationError({"stock": "sin reserva"})), \
			patch("apps.orders.views.transaction.set_rollback") as rollback_mock:

			response = _call_unwrapped(AprobarPedidoView.post, view, request, 44)

		self.assertEqual(response.status_code, 409)
		self.assertEqual(response.data, {"stock": "sin reserva"})
		rollback_mock.assert_called_once_with(True)

	def test_mis_pedidos_view_rejects_non_clients(self):
		view = MisPedidosView()
		request = _make_request(user=_make_user(groups=("Ejecutivo",)), method="GET")

		response = view.get(request)

		self.assertEqual(response.status_code, 403)

	def test_mis_pedidos_view_returns_client_orders(self):
		view = MisPedidosView()
		request = _make_request(user=_make_user(perfil_cliente_id=1), method="GET")
		pedidos = [SimpleNamespace(id=1)]

		with patch("apps.orders.views.Pedido.objects.filter") as filter_mock, patch("apps.orders.views.PedidoOutputSerializer") as serializer_mock:
			filter_mock.return_value.select_related.return_value.prefetch_related.return_value.order_by.return_value = pedidos
			serializer_mock.return_value.data = [{"id": 1}]
			response = view.get(request)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data, [{"id": 1}])
		serializer_mock.assert_called_once()

	def test_listar_pedidos_view_rejects_non_authorized_users(self):
		view = ListarPedidosView()
		request = _make_request(user=_make_user(perfil_cliente_id=1), method="GET")

		response = view.get(request)

		self.assertEqual(response.status_code, 403)

	def test_listar_pedidos_view_returns_all_orders_for_staff(self):
		view = ListarPedidosView()
		request = _make_request(user=_make_user(is_staff=True), method="GET")
		pedidos = [SimpleNamespace(id=1), SimpleNamespace(id=2)]

		with patch("apps.orders.views.Pedido.objects.select_related") as select_related_mock, patch("apps.orders.views.PedidoOutputSerializer") as serializer_mock:
			select_related_mock.return_value.prefetch_related.return_value.order_by.return_value = pedidos
			serializer_mock.return_value.data = [{"id": 1}, {"id": 2}]
			response = view.get(request)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data, [{"id": 1}, {"id": 2}])

	def test_resumen_cotizaciones_view_rejects_non_allowed_users(self):
		view = ResumenCotizacionesView()
		request = _make_request(user=_make_user(perfil_cliente_id=1), method="GET")

		response = view.get(request)

		self.assertEqual(response.status_code, 403)

	def test_resumen_cotizaciones_view_returns_counts_and_sum(self):
		view = ResumenCotizacionesView()
		request = _make_request(user=_make_user(groups=("Analista",)), method="GET")
		cotizaciones_pendientes = Mock()
		cotizaciones_pendientes.count.return_value = 2
		cotizaciones_pendientes.aggregate.return_value = {"suma": 4500}

		with patch("apps.orders.views.Cotizacion.objects.filter", return_value=cotizaciones_pendientes) as filter_mock, \
			patch("apps.orders.views.Cotizacion.objects.count", return_value=5):

			response = view.get(request)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data, {"pendientes": 2, "total": 5, "monto_pendiente": 4500})
		filter_mock.assert_called_once()
