from django.db import transaction
from apps.orders.models import Pedido


@transaction.atomic
def aprobar_pedido_y_crear_despacho_pendiente(transaccion_pago):
    """
    Se ejecuta cuando Webpay confirma correctamente el pago.

    IMPORTANTE:
    Esta función NO debe crear un Despacho.

    Motivo:
    El despacho real debe crearse solamente cuando se llama a Chilexpress
    y Chilexpress responde con una Orden de Transporte / número de seguimiento.

    Flujo correcto:
    1. Webpay confirma pago.
    2. Pedido pasa a APROBADO.
    3. Luego el módulo logístico llama a Chilexpress.
    4. Si Chilexpress responde correctamente, recién ahí se crea Despacho.

    La función conserva el nombre antiguo para no romper imports existentes.
    Retorna:
        pedido, despacho, creado

    Pero despacho será None y creado será False.
    """

    pedido = Pedido.objects.select_for_update().get(pk=transaccion_pago.pedido_id)

    if pedido.estado_pedido == "CANCELADO":
        raise ValueError("No se puede aprobar un pedido cancelado.")

    estados_finales = ["DESPACHADO", "ENTREGADO"]

    if pedido.estado_pedido in estados_finales:
        return pedido, None, False

    if pedido.estado_pedido != "APROBADO":
        pedido.estado_pedido = "APROBADO"
        pedido.save(update_fields=["estado_pedido", "fecha_actualizacion"])

    return pedido, None, False