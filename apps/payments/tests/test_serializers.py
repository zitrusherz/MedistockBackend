from django.test import SimpleTestCase
from rest_framework import serializers

from apps.payments.serializers import (
    ComprobantePagoRevisionSerializer,
    ComprobantePagoSerializer,
    PagoAseguradoraSerializer,
    WebpayCommitSerializer,
    WebpayCrearTransaccionSerializer,
    WebpayStatusSerializer,
)


class WebpaySerializerTests(SimpleTestCase):
    def test_webpay_crear_transaccion_serializer_acepta_pedido_id_valido(self):
        serializer = WebpayCrearTransaccionSerializer(data={"pedido_id": 10})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data, {"pedido_id": 10})

    def test_webpay_crear_transaccion_serializer_rechaza_pedido_id_no_positivo(self):
        for pedido_id in [0, -1]:
            with self.subTest(pedido_id=pedido_id):
                serializer = WebpayCrearTransaccionSerializer(data={"pedido_id": pedido_id})

                self.assertFalse(serializer.is_valid())
                self.assertIn("pedido_id", serializer.errors)

    def test_serializers_token_ws_limpian_espacios(self):
        for serializer_class in [WebpayCommitSerializer, WebpayStatusSerializer]:
            with self.subTest(serializer_class=serializer_class.__name__):
                serializer = serializer_class(data={"token_ws": "  TOKEN-123  "})

                self.assertTrue(serializer.is_valid(), serializer.errors)
                self.assertEqual(serializer.validated_data["token_ws"], "TOKEN-123")

    def test_serializers_token_ws_rechazan_vacios(self):
        for serializer_class in [WebpayCommitSerializer, WebpayStatusSerializer]:
            for token_ws in ["", "   "]:
                with self.subTest(serializer_class=serializer_class.__name__, token_ws=repr(token_ws)):
                    serializer = serializer_class(data={"token_ws": token_ws})

                    self.assertFalse(serializer.is_valid())
                    self.assertIn("token_ws", serializer.errors)


class ComprobantePagoSerializerTests(SimpleTestCase):
    def test_comprobante_pago_serializer_acepta_monto_reportado_positivo(self):
        serializer = ComprobantePagoSerializer()

        self.assertEqual(serializer.validate_monto_reportado(1), 1)

    def test_comprobante_pago_serializer_rechaza_monto_reportado_no_positivo(self):
        serializer = ComprobantePagoSerializer()

        for monto in [0, -1]:
            with self.subTest(monto=monto):
                with self.assertRaises(serializers.ValidationError):
                    serializer.validate_monto_reportado(monto)

    def test_comprobante_revision_serializer_acepta_estados_permitidos(self):
        serializer = ComprobantePagoRevisionSerializer()

        for estado in ["VALIDADO", "RECHAZADO"]:
            with self.subTest(estado=estado):
                self.assertEqual(serializer.validate_estado_validacion(estado), estado)

    def test_comprobante_revision_serializer_rechaza_estados_no_permitidos(self):
        serializer = ComprobantePagoRevisionSerializer()

        for estado in ["PENDIENTE_REVISION", "PENDIENTE", "ANULADO"]:
            with self.subTest(estado=estado):
                with self.assertRaises(serializers.ValidationError):
                    serializer.validate_estado_validacion(estado)


class PagoAseguradoraSerializerTests(SimpleTestCase):
    def test_pago_aseguradora_serializer_acepta_monto_cubierto_cero_o_positivo(self):
        serializer = PagoAseguradoraSerializer()

        self.assertEqual(serializer.validate_monto_cubierto(0), 0)
        self.assertEqual(serializer.validate_monto_cubierto(1000), 1000)

    def test_pago_aseguradora_serializer_rechaza_monto_cubierto_negativo(self):
        serializer = PagoAseguradoraSerializer()

        with self.assertRaises(serializers.ValidationError):
            serializer.validate_monto_cubierto(-1)
