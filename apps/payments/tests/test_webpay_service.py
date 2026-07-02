from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import ValidationError
from transbank.common.integration_type import IntegrationType

from apps.payments.services.webpay import WebpayService, WebpayServiceError


class WebpayServiceTests(SimpleTestCase):
    def test_normalizar_monto_acepta_enteros_positivos(self):
        casos = [
            (1, 1),
            ("12990", 12990),
            (Decimal("5000"), 5000),
        ]

        for amount, expected in casos:
            with self.subTest(amount=amount):
                self.assertEqual(WebpayService._normalizar_monto(amount), expected)

    def test_normalizar_monto_rechaza_montos_invalidos(self):
        for amount in [0, -1, "12.5", "abc", None]:
            with self.subTest(amount=amount):
                with self.assertRaises(ValidationError):
                    WebpayService._normalizar_monto(amount)

    def test_validar_texto_requerido_limpia_espacios(self):
        resultado = WebpayService._validar_texto_requerido("  PED-123  ", "buy_order")
        self.assertEqual(resultado, "PED-123")

    def test_validar_texto_requerido_rechaza_vacios(self):
        for value in [None, "", "   "]:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    WebpayService._validar_texto_requerido(value, "token_ws")

    @override_settings(TRANSBANK_ENVIRONMENT="LIVE")
    def test_get_environment_live(self):
        self.assertEqual(WebpayService._get_environment(), IntegrationType.LIVE)

    @override_settings(TRANSBANK_ENVIRONMENT="TEST")
    def test_get_environment_test_por_defecto(self):
        self.assertEqual(WebpayService._get_environment(), IntegrationType.TEST)

    @override_settings(
        TRANSBANK_ENVIRONMENT="TEST",
        TRANSBANK_WEBPAY_COMMERCE_CODE="",
        TRANSBANK_WEBPAY_API_KEY="api-key",
    )
    def test_get_transaction_exige_commerce_code(self):
        with self.assertRaises(WebpayServiceError):
            WebpayService._get_transaction()

    @override_settings(
        TRANSBANK_ENVIRONMENT="TEST",
        TRANSBANK_WEBPAY_COMMERCE_CODE="commerce-code",
        TRANSBANK_WEBPAY_API_KEY="",
    )
    def test_get_transaction_exige_api_key(self):
        with self.assertRaises(WebpayServiceError):
            WebpayService._get_transaction()

    @override_settings(BACKEND_BASE_URL="https://backend.example")
    def test_crear_transaccion_normaliza_datos_y_devuelve_redirect(self):
        fake_tx = Mock()
        fake_tx.create.return_value = {
            "token": "TOKEN-123",
            "url": "https://webpay.example/pay",
        }

        with patch.object(WebpayService, "_get_transaction", return_value=fake_tx):
            result = WebpayService.crear_transaccion(
                buy_order="  PED-1  ",
                session_id="  USER-9-PED-1  ",
                amount="12990",
            )

        fake_tx.create.assert_called_once_with(
            buy_order="PED-1",
            session_id="USER-9-PED-1",
            amount=12990,
            return_url="https://backend.example/api/payments/webpay/commit/",
        )
        self.assertEqual(
            result,
            {
                "token": "TOKEN-123",
                "url": "https://webpay.example/pay",
                "redirect_url": "https://webpay.example/pay?token_ws=TOKEN-123",
                "buy_order": "PED-1",
                "session_id": "USER-9-PED-1",
                "amount": 12990,
                "return_url": "https://backend.example/api/payments/webpay/commit/",
            },
        )

    def test_crear_transaccion_permite_return_url_explicita(self):
        fake_tx = Mock()
        fake_tx.create.return_value = {
            "token": "TOKEN-456",
            "url": "https://webpay.example/pay",
        }

        with patch.object(WebpayService, "_get_transaction", return_value=fake_tx):
            result = WebpayService.crear_transaccion(
                buy_order="PED-1",
                session_id="USER-9-PED-1",
                amount=12990,
                return_url="https://api.example/webpay/commit/",
            )

        fake_tx.create.assert_called_once_with(
            buy_order="PED-1",
            session_id="USER-9-PED-1",
            amount=12990,
            return_url="https://api.example/webpay/commit/",
        )
        self.assertEqual(result["return_url"], "https://api.example/webpay/commit/")

    def test_crear_transaccion_falla_si_webpay_no_entrega_token_o_url(self):
        fake_tx = Mock()
        fake_tx.create.return_value = {"token": "TOKEN-123"}

        with patch.object(WebpayService, "_get_transaction", return_value=fake_tx):
            with self.assertRaises(WebpayServiceError):
                WebpayService.crear_transaccion("PED-1", "USER-1", 1000)

    def test_confirmar_transaccion_mapea_respuesta_aprobada(self):
        fake_tx = Mock()
        fake_response = {
            "response_code": 0,
            "status": "AUTHORIZED",
            "buy_order": "PED-1",
            "session_id": "USER-9-PED-1",
            "amount": 12990,
            "authorization_code": "AUTH-1",
            "payment_type_code": "VD",
            "installments_number": 0,
            "card_detail": {"card_number": "1234"},
            "transaction_date": "2026-07-02T12:00:00Z",
        }
        fake_tx.commit.return_value = fake_response

        with patch.object(WebpayService, "_get_transaction", return_value=fake_tx):
            result = WebpayService.confirmar_transaccion("  TOKEN-123  ")

        fake_tx.commit.assert_called_once_with("TOKEN-123")
        self.assertEqual(result["token_ws"], "TOKEN-123")
        self.assertEqual(result["raw"], fake_response)
        self.assertIs(result["aprobada"], True)

    def test_confirmar_transaccion_marca_rechazada_si_no_viene_authorized(self):
        fake_tx = Mock()
        fake_tx.commit.return_value = {
            "response_code": -1,
            "status": "FAILED",
            "buy_order": "PED-1",
            "amount": 12990,
        }

        with patch.object(WebpayService, "_get_transaction", return_value=fake_tx):
            result = WebpayService.confirmar_transaccion("TOKEN-123")

        self.assertIs(result["aprobada"], False)

    def test_consultar_estado_mapea_respuesta(self):
        fake_tx = Mock()
        fake_tx.status.return_value = {
            "response_code": 0,
            "status": "AUTHORIZED",
            "buy_order": "PED-1",
            "session_id": "USER-9-PED-1",
            "amount": 12990,
        }

        with patch.object(WebpayService, "_get_transaction", return_value=fake_tx):
            result = WebpayService.consultar_estado("TOKEN-123")

        fake_tx.status.assert_called_once_with("TOKEN-123")
        self.assertEqual(result["buy_order"], "PED-1")
        self.assertIs(result["aprobada"], True)

    def test_es_transaccion_aprobada(self):
        casos = [
            ({"status": "AUTHORIZED", "response_code": 0}, True),
            ({"status": "AUTHORIZED", "response_code": "0"}, False),
            ({"status": "FAILED", "response_code": 0}, False),
            ({"status": "AUTHORIZED", "response_code": -1}, False),
            ({}, False),
            (None, False),
        ]

        for response, expected in casos:
            with self.subTest(response=response):
                self.assertIs(WebpayService.es_transaccion_aprobada(response), expected)
