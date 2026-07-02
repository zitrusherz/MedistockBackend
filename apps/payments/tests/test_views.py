import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.payments import views


class FakeActivePaymentQuery:
    def __init__(self, existing=None):
        self.existing = existing
        self.order_by = Mock(return_value=self)
        self.first = Mock(return_value=existing)


class FakeTransaccionManager:
    def __init__(self, existing=None, created=None):
        self.active_query = FakeActivePaymentQuery(existing=existing)
        self.filter = Mock(return_value=self.active_query)
        self.create = Mock(return_value=created or SimpleNamespace(id=77))


class FakeCommitManager:
    def __init__(self, transaccion):
        self.transaccion = transaccion
        self.select_for_update = Mock(return_value=self)
        self.select_related = Mock(return_value=self)
        self.filter = Mock(return_value=self)
        self.first = Mock(return_value=transaccion)


class FakePedidoManager:
    def __init__(self, pedido=None, exception_to_raise=None):
        self.pedido = pedido
        self.exception_to_raise = exception_to_raise
        self.select_related = Mock(return_value=self)
        self.get = Mock(side_effect=self._get)

    def _get(self, *args, **kwargs):
        if self.exception_to_raise:
            raise self.exception_to_raise
        return self.pedido


class FakeTransaccionPagoSerializer:
    def __init__(self, obj, *args, **kwargs):
        self.data = {
            "id": getattr(obj, "id", None),
            "token_ws": getattr(obj, "token_ws", None),
            "estado_pago": getattr(obj, "estado_pago", None),
        }


def make_request(data=None, query_params=None, user=None):
    return SimpleNamespace(
        data=data or {},
        query_params=query_params or {},
        user=user or SimpleNamespace(id=1),
    )


class HelpersViewsTests(TestCase):
    def test_restar_meses_clamp_fin_de_mes_bisiesto(self):
        self.assertEqual(views._restar_meses(date(2024, 3, 31), 1), date(2024, 2, 29))

    def test_restar_meses_cruza_anio(self):
        self.assertEqual(views._restar_meses(date(2026, 1, 15), 2), date(2025, 11, 15))


class WebpayIniciarPagoViewTests(TestCase):
    @override_settings(BACKEND_BASE_URL="https://backend.example")
    def test_webpay_iniciar_pago_crea_transaccion(self):
        cliente = SimpleNamespace(id=5)
        user = SimpleNamespace(id=9, perfilcliente=cliente)
        pedido = SimpleNamespace(id=123, cliente=cliente, total=12990)
        fake_pedido_model = SimpleNamespace(objects=FakePedidoManager(pedido=pedido), DoesNotExist=Exception)
        fake_transaccion_manager = FakeTransaccionManager(created=SimpleNamespace(id=77))
        fake_transaccion_model = SimpleNamespace(objects=fake_transaccion_manager)
        fake_webpay_service = SimpleNamespace(
            crear_transaccion=Mock(
                return_value={
                    "token": "TOKEN-123",
                    "url": "https://webpay.example/pay",
                    "redirect_url": "https://webpay.example/pay?token_ws=TOKEN-123",
                }
            )
        )

        with patch.object(views, "Pedido", fake_pedido_model), \
             patch.object(views, "TransaccionPago", fake_transaccion_model), \
             patch.object(views, "WebpayService", fake_webpay_service):
            request = make_request(data={"pedido_id": 123}, user=user)
            response = views.WebpayIniciarPagoView().post(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data,
            {
                "transaccion_pago_id": 77,
                "pedido_id": 123,
                "buy_order": "PED-123",
                "session_id": "USER-9-PED-123",
                "amount": 12990,
                "token": "TOKEN-123",
                "url": "https://webpay.example/pay",
                "redirect_url": "https://webpay.example/pay?token_ws=TOKEN-123",
            },
        )
        fake_webpay_service.crear_transaccion.assert_called_once_with(
            buy_order="PED-123",
            session_id="USER-9-PED-123",
            amount=12990,
            return_url="https://backend.example/api/payments/webpay/commit/",
        )
        fake_transaccion_manager.create.assert_called_once_with(
            pedido=pedido,
            metodo_pago="WEBPAY",
            estado_pago="INICIADO",
            monto_confirmado=12990,
            buy_order="PED-123",
            session_id="USER-9-PED-123",
            token_ws="TOKEN-123",
            id_transaccion_externa="TOKEN-123",
            observacion="Transacción Webpay iniciada.",
        )

    def test_webpay_iniciar_pago_reutiliza_transaccion_existente_con_token(self):
        cliente = SimpleNamespace(id=5)
        user = SimpleNamespace(id=9, perfilcliente=cliente)
        pedido = SimpleNamespace(id=123, cliente=cliente, total=12990)
        existing = SimpleNamespace(id=55, token_ws="TOKEN-EXISTENTE", estado_pago="INICIADO")
        fake_pedido_model = SimpleNamespace(objects=FakePedidoManager(pedido=pedido), DoesNotExist=Exception)
        fake_transaccion_model = SimpleNamespace(objects=FakeTransaccionManager(existing=existing))

        with patch.object(views, "Pedido", fake_pedido_model), \
             patch.object(views, "TransaccionPago", fake_transaccion_model), \
             patch.object(views, "TransaccionPagoSerializer", FakeTransaccionPagoSerializer):
            request = make_request(data={"pedido_id": 123}, user=user)
            response = views.WebpayIniciarPagoView().post(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["transaccion_pago"], {
            "id": 55,
            "token_ws": "TOKEN-EXISTENTE",
            "estado_pago": "INICIADO",
        })

    def test_webpay_iniciar_pago_rechaza_usuario_no_cliente(self):
        pedido = SimpleNamespace(id=123, cliente=SimpleNamespace(id=5), total=12990)
        fake_pedido_model = SimpleNamespace(objects=FakePedidoManager(pedido=pedido), DoesNotExist=Exception)

        with patch.object(views, "Pedido", fake_pedido_model):
            request = make_request(data={"pedido_id": 123}, user=SimpleNamespace(id=9))
            with self.assertRaises(PermissionDenied):
                views.WebpayIniciarPagoView().post(request)

    def test_webpay_iniciar_pago_rechaza_pedido_de_otro_cliente(self):
        cliente_dueno = SimpleNamespace(id=5)
        cliente_actual = SimpleNamespace(id=6)
        user = SimpleNamespace(id=9, perfilcliente=cliente_actual)
        pedido = SimpleNamespace(id=123, cliente=cliente_dueno, total=12990)
        fake_pedido_model = SimpleNamespace(objects=FakePedidoManager(pedido=pedido), DoesNotExist=Exception)

        with patch.object(views, "Pedido", fake_pedido_model):
            request = make_request(data={"pedido_id": 123}, user=user)
            with self.assertRaises(PermissionDenied):
                views.WebpayIniciarPagoView().post(request)

    def test_webpay_iniciar_pago_rechaza_total_no_positivo(self):
        cliente = SimpleNamespace(id=5)
        user = SimpleNamespace(id=9, perfilcliente=cliente)
        pedido = SimpleNamespace(id=123, cliente=cliente, total=0)
        fake_pedido_model = SimpleNamespace(objects=FakePedidoManager(pedido=pedido), DoesNotExist=Exception)

        with patch.object(views, "Pedido", fake_pedido_model):
            request = make_request(data={"pedido_id": 123}, user=user)
            with self.assertRaises(ValidationError):
                views.WebpayIniciarPagoView().post(request)


class WebpayCommitViewTests(TestCase):
    def _transaccion(self):
        pedido = SimpleNamespace(id=123, estado_pedido="PENDIENTE")
        return SimpleNamespace(
            id=77,
            pedido=pedido,
            buy_order="PED-123",
            monto_confirmado=12990,
            save=Mock(),
        )

    def _resultado_webpay(self, **overrides):
        resultado = {
            "token_ws": "TOKEN-123",
            "response_code": -1,
            "status": "FAILED",
            "buy_order": "PED-123",
            "amount": 12990,
            "authorization_code": None,
            "payment_type_code": None,
            "installments_number": None,
            "card_detail": {},
            "transaction_date": None,
            "raw": {"status": "FAILED"},
            "aprobada": False,
        }
        resultado.update(overrides)
        return resultado

    @override_settings(FRONTEND_BASE_URL=None)
    def test_webpay_commit_rechazado_actualiza_transaccion(self):
        transaccion = self._transaccion()
        resultado = self._resultado_webpay()
        fake_webpay_service = SimpleNamespace(confirmar_transaccion=Mock(return_value=resultado))
        fake_transaccion_model = SimpleNamespace(objects=FakeCommitManager(transaccion))

        with patch.object(views, "WebpayService", fake_webpay_service), \
             patch.object(views, "TransaccionPago", fake_transaccion_model):
            request = make_request(query_params={"token_ws": "TOKEN-123"}, data={})
            response = views.WebpayCommitView()._commit(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIs(response.data["aprobada"], False)
        self.assertEqual(response.data["estado_pago"], "RECHAZADO")
        self.assertEqual(transaccion.estado_pago, "RECHAZADO")
        self.assertEqual(transaccion.observacion, "Pago rechazado o no autorizado por Webpay.")
        transaccion.save.assert_called_once()

    def test_webpay_commit_error_si_buy_order_no_coincide(self):
        transaccion = self._transaccion()
        resultado = self._resultado_webpay(
            response_code=0,
            status="AUTHORIZED",
            buy_order="PED-OTRO",
            raw={"buy_order": "PED-OTRO"},
            aprobada=True,
        )
        fake_webpay_service = SimpleNamespace(confirmar_transaccion=Mock(return_value=resultado))
        fake_transaccion_model = SimpleNamespace(objects=FakeCommitManager(transaccion))

        with patch.object(views, "WebpayService", fake_webpay_service), \
             patch.object(views, "TransaccionPago", fake_transaccion_model):
            request = make_request(query_params={"token_ws": "TOKEN-123"}, data={})
            with self.assertRaises(ValidationError):
                views.WebpayCommitView()._commit(request)

        self.assertEqual(transaccion.estado_pago, "ERROR")
        self.assertEqual(transaccion.observacion, "La orden de compra devuelta por Webpay no coincide.")
        transaccion.save.assert_called_once()

    def test_webpay_commit_error_si_monto_no_coincide(self):
        transaccion = self._transaccion()
        resultado = self._resultado_webpay(
            response_code=0,
            status="AUTHORIZED",
            amount=1000,
            raw={"amount": 1000},
            aprobada=True,
        )
        fake_webpay_service = SimpleNamespace(confirmar_transaccion=Mock(return_value=resultado))
        fake_transaccion_model = SimpleNamespace(objects=FakeCommitManager(transaccion))

        with patch.object(views, "WebpayService", fake_webpay_service), \
             patch.object(views, "TransaccionPago", fake_transaccion_model):
            request = make_request(query_params={"token_ws": "TOKEN-123"}, data={})
            with self.assertRaises(ValidationError):
                views.WebpayCommitView()._commit(request)

        self.assertEqual(transaccion.estado_pago, "ERROR")
        self.assertEqual(transaccion.observacion, "El monto devuelto por Webpay no coincide.")
        transaccion.save.assert_called_once()

    @unittest.expectedFailure
    @override_settings(FRONTEND_BASE_URL=None)
    def test_webpay_commit_aprobado_sin_frontend_documenta_bug_despacho_none(self):
        transaccion = self._transaccion()
        resultado = self._resultado_webpay(
            response_code=0,
            status="AUTHORIZED",
            authorization_code="AUTH-1",
            payment_type_code="VD",
            installments_number=0,
            card_detail={"card_number": "1234"},
            raw={"status": "AUTHORIZED"},
            aprobada=True,
        )
        fake_webpay_service = SimpleNamespace(confirmar_transaccion=Mock(return_value=resultado))
        fake_transaccion_model = SimpleNamespace(objects=FakeCommitManager(transaccion))

        with patch.object(views, "WebpayService", fake_webpay_service), \
             patch.object(views, "TransaccionPago", fake_transaccion_model), \
             patch.object(views, "aprobar_pedido_y_crear_despacho_pendiente", return_value=(transaccion.pedido, None, False)):
            request = make_request(query_params={"token_ws": "TOKEN-123"}, data={})
            response = views.WebpayCommitView()._commit(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
