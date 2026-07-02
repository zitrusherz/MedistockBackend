from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.inventory.models import Inventario, MovimientoInventario
from apps.orders.models import DetallePedido


def _usuario_default(pedido, usuario):
    return usuario or pedido.cliente.usuario


@transaction.atomic
def reservar_stock_pedido(pedido, usuario=None):
    """Reserva stock para un pedido, buscando en cualquier sucursal disponible."""
    detalles = DetallePedido.objects.filter(pedido=pedido).select_related("lote")
    if not detalles:
        return

    usuario = _usuario_default(pedido, usuario)

    for detalle in detalles:
        # Buscar inventario en CUALQUIER sucursal (no solo en la sucursal de origen)
        inventario = (
            Inventario.objects
            .select_for_update()
            .filter(lote_id=detalle.lote_id)
            .first()
        )
        if not inventario:
            raise ValidationError({
                "stock": f"No existe inventario para lote id={detalle.lote_id} en ninguna sucursal."
            })

        disponible_neto = inventario.cantidad_disponible - inventario.cantidad_reservada
        if disponible_neto < detalle.cantidad:
            raise ValidationError({
                "stock": (
                    f"Stock insuficiente para lote id={detalle.lote_id}. "
                    f"Disponible neto: {disponible_neto}, solicitado: {detalle.cantidad}."
                )
            })

        inventario.cantidad_reservada += detalle.cantidad
        inventario.fecha_actualizacion = timezone.now()
        inventario.save(update_fields=["cantidad_reservada", "fecha_actualizacion"])

        MovimientoInventario.objects.create(
            inventario=inventario,
            usuario=usuario,
            pedido=pedido,
            tipo_movimiento="RESERVA",
            cantidad=detalle.cantidad,
            motivo="Reserva por pedido",
            observacion=f"Pedido {pedido.id} (Sucursal {inventario.sucursal_id})",
        )


@transaction.atomic
def consumir_reserva_pedido(pedido, usuario=None, motivo="Consumo de reserva"):
    """Consume la reserva de un pedido, buscando stock en cualquier sucursal."""
    if MovimientoInventario.objects.filter(
        pedido=pedido,
        tipo_movimiento="SALIDA",
    ).exists():
        return False

    detalles = DetallePedido.objects.filter(pedido=pedido).select_related("lote")
    if not detalles:
        return False

    usuario = _usuario_default(pedido, usuario)

    for detalle in detalles:
        # Buscar inventario en CUALQUIER sucursal (no solo en la sucursal de origen)
        inventario = (
            Inventario.objects
            .select_for_update()
            .filter(lote_id=detalle.lote_id)
            .first()
        )
        if not inventario:
            raise ValidationError({
                "stock": f"No existe inventario para lote id={detalle.lote_id} en ninguna sucursal."
            })

        if inventario.cantidad_reservada < detalle.cantidad:
            raise ValidationError({
                "stock": (
                    f"Reserva insuficiente para lote id={detalle.lote_id}. "
                    f"Reservado: {inventario.cantidad_reservada}, requerido: {detalle.cantidad}."
                )
            })

        if inventario.cantidad_disponible < detalle.cantidad:
            raise ValidationError({
                "stock": (
                    f"Stock disponible insuficiente para consumir reserva en lote id={detalle.lote_id}. "
                    f"Disponible: {inventario.cantidad_disponible}, requerido: {detalle.cantidad}."
                )
            })

        inventario.cantidad_reservada -= detalle.cantidad
        inventario.cantidad_disponible -= detalle.cantidad
        inventario.fecha_actualizacion = timezone.now()
        inventario.save(update_fields=["cantidad_reservada", "cantidad_disponible", "fecha_actualizacion"])

        MovimientoInventario.objects.create(
            inventario=inventario,
            usuario=usuario,
            pedido=pedido,
            tipo_movimiento="SALIDA",
            cantidad=detalle.cantidad,
            motivo=motivo,
            observacion=f"Pedido {pedido.id} (Sucursal {inventario.sucursal_id})",
        )

    return True

