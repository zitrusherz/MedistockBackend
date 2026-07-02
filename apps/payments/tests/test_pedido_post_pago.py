from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import TestCase

from apps.payments.services import pedido_post_pago


class FakePedidoQuery:
    def __init__(self, pedido):
        self.pedido = pedido
        self.get = Mock(return_value=pedido)

    def select_for_update(self):
        return self


class PedidoPostPagoTests(TestCase):
    def test_aprobar_pedido_cambia_estado_y_no_crea_despacho(self):
        pedido = SimpleNamespace(estado_pedido="PENDIENTE", save=Mock())
        fake_query = FakePedidoQuery(pedido)
        fake_pedido_model = SimpleNamespace(objects=fake_query)
        transaccion = SimpleNamespace(pedido_id=123)

        with patch.object(pedido_post_pago, "Pedido", fake_pedido_model):
            result_pedido, despacho, creado = pedido_post_pago.aprobar_pedido_y_crear_despacho_pendiente(transaccion)

        fake_query.get.assert_called_once_with(pk=123)
        self.assertIs(result_pedido, pedido)
        self.assertEqual(pedido.estado_pedido, "APROBADO")
        pedido.save.assert_called_once_with(update_fields=["estado_pedido", "fecha_actualizacion"])
        self.assertIsNone(despacho)
        self.assertIs(creado, False)

    def test_aprobar_pedido_cancelado_lanza_error(self):
        pedido = SimpleNamespace(estado_pedido="CANCELADO", save=Mock())
        fake_query = FakePedidoQuery(pedido)
        fake_pedido_model = SimpleNamespace(objects=fake_query)

        with patch.object(pedido_post_pago, "Pedido", fake_pedido_model):
            with self.assertRaisesRegex(ValueError, "cancelado"):
                pedido_post_pago.aprobar_pedido_y_crear_despacho_pendiente(SimpleNamespace(pedido_id=123))

        pedido.save.assert_not_called()

    def test_aprobar_pedido_en_estado_final_no_lo_modifica(self):
        for estado_final in ["DESPACHADO", "ENTREGADO"]:
            with self.subTest(estado_final=estado_final):
                pedido = SimpleNamespace(estado_pedido=estado_final, save=Mock())
                fake_query = FakePedidoQuery(pedido)
                fake_pedido_model = SimpleNamespace(objects=fake_query)

                with patch.object(pedido_post_pago, "Pedido", fake_pedido_model):
                    result_pedido, despacho, creado = pedido_post_pago.aprobar_pedido_y_crear_despacho_pendiente(
                        SimpleNamespace(pedido_id=123)
                    )

                self.assertIs(result_pedido, pedido)
                pedido.save.assert_not_called()
                self.assertIsNone(despacho)
                self.assertIs(creado, False)

    def test_aprobar_pedido_ya_aprobado_no_vuelve_a_guardar(self):
        pedido = SimpleNamespace(estado_pedido="APROBADO", save=Mock())
        fake_query = FakePedidoQuery(pedido)
        fake_pedido_model = SimpleNamespace(objects=fake_query)

        with patch.object(pedido_post_pago, "Pedido", fake_pedido_model):
            result_pedido, despacho, creado = pedido_post_pago.aprobar_pedido_y_crear_despacho_pendiente(
                SimpleNamespace(pedido_id=123)
            )

        self.assertIs(result_pedido, pedido)
        pedido.save.assert_not_called()
        self.assertIsNone(despacho)
        self.assertIs(creado, False)
