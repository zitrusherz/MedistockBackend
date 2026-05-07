# apps/orders/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from apps.orders.models import Pedido, DetallePedido, AprobacionPedido
from apps.orders.serializers import (
    CrearPedidoInputSerializer,
    PedidoOutputSerializer,
)
from apps.inventory.models import Inventario
from apps.accounts.models import PerfilTrabajador

IVA = 0.19


def _calcular_montos(detalles_data: list[dict]) -> dict:
    """
    Calcula subtotal, descuento_total, monto_neto, monto_iva y total
    a partir de los detalles validados.
    Todos los valores en CLP como int (sin decimales).
    """
    subtotal = 0
    descuento_total = 0

    for detalle in detalles_data:
        precio = detalle["_precio_unitario"]
        cantidad = detalle["cantidad"]
        descuento = detalle.get("descuento", 0)

        linea_bruta = precio * cantidad
        linea_descuento = descuento * cantidad
        subtotal += linea_bruta
        descuento_total += linea_descuento

    monto_neto = subtotal - descuento_total
    monto_iva = int(monto_neto * IVA)
    total = monto_neto + monto_iva

    return {
        "subtotal": subtotal,
        "descuento_total": descuento_total,
        "monto_neto": monto_neto,
        "monto_iva": monto_iva,
        "total": total,
    }


def _elegir_lote(producto_id: int, sucursal_id: int, cantidad: int):
    """
    Elige el lote más próximo a vencer con stock suficiente (FEFO).
    Retorna la instancia de Inventario o None si no hay stock.
    """
    return Inventario.objects.filter(
        lote__producto_id=producto_id,
        sucursal_id=sucursal_id,
        lote__activo=True,
        cantidad_disponible__gte=cantidad,
    ).order_by("lote__fecha_vencimiento").select_related("lote").first()


class CrearPedidoView(APIView):
    """
    POST /api/v1/orders/pedidos/

    Crea un pedido con sus detalles. El cliente se toma del usuario autenticado.
    Los montos se calculan en el backend usando el precio actual del producto.

    Body mínimo:
        {
            "sucursal_origen_id": 1,
            "direccion_entrega_id": 3,
            "tipo_venta": "WEBPAY",
            "detalles": [
                {"producto_id": 5, "cantidad": 2},
                {"producto_id": 8, "cantidad": 1, "lote_id": 12}
            ]
        }
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = CrearPedidoInputSerializer(
            data=request.data,
            context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        perfil_cliente = serializer._perfil_cliente

        # --- Resolver precios y lotes para cada detalle ---
        detalles_resueltos = []
        for detalle_data in data["detalles"]:
            producto_id = detalle_data["producto_id"]
            cantidad = detalle_data["cantidad"]
            lote_id = detalle_data.get("lote_id")

            # Precio al momento de la venta (histórico)
            # _producto fue seteado en validate_producto_id del DetallePedidoInputSerializer
            # pero como estamos en el serializer padre, lo buscamos directo
            from apps.inventory.models import Producto
            producto = Producto.objects.get(pk=producto_id)

            # Elegir lote si no se especificó
            if not lote_id:
                inventario = _elegir_lote(producto_id, data["sucursal_origen_id"], cantidad)
                if not inventario:
                    # No debería llegar aquí porque validate() ya verificó stock,
                    # pero puede haber una race condition entre validate y atomic
                    return Response(
                        {"error": f"Sin stock disponible para producto id={producto_id} en la sucursal indicada."},
                        status=status.HTTP_409_CONFLICT,
                    )
                lote_id = inventario.lote_id

            detalles_resueltos.append({
                **detalle_data,
                "_precio_unitario": producto.valor_unitario,
                "_lote_id": lote_id,
            })

        # --- Calcular montos totales ---
        montos = _calcular_montos(detalles_resueltos)

        # --- Crear el pedido ---
        pedido = Pedido.objects.create(
            cliente=perfil_cliente,
            sucursal_origen_id=data["sucursal_origen_id"],
            direccion_entrega_id=data["direccion_entrega_id"],
            tipo_venta=data["tipo_venta"],
            tipo_despacho=data.get("tipo_despacho", "NORMAL"),
            prioridad_medica=data.get("prioridad_medica", "NORMAL"),
            fecha_requerida_entrega=data.get("fecha_requerida_entrega"),
            observacion=data.get("observacion", ""),
            estado_pedido="PENDIENTE",
            **montos,
        )

        # --- Crear los detalles ---
        for detalle in detalles_resueltos:
            precio = detalle["_precio_unitario"]
            cantidad = detalle["cantidad"]
            descuento = detalle.get("descuento", 0)
            subtotal = (precio - descuento) * cantidad

            DetallePedido.objects.create(
                pedido=pedido,
                producto_id=detalle["producto_id"],
                lote_id=detalle["_lote_id"],
                cantidad=cantidad,
                precio_unitario_historico=precio,
                descuento=descuento,
                subtotal=subtotal,
                observacion=detalle.get("observacion", ""),
            )

        return Response(
            PedidoOutputSerializer(pedido).data,
            status=status.HTTP_201_CREATED,
        )


class DetallePedidoView(APIView):
    """
    GET /api/v1/orders/pedidos/{pedido_id}/

    Retorna el detalle completo de un pedido, incluyendo sus líneas.
    Solo el cliente dueño del pedido o un trabajador interno puede verlo.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pedido_id):
        try:
            pedido = Pedido.objects.prefetch_related(
                "detallepedido_set__producto",
                "detallepedido_set__lote",
            ).select_related(
                "cliente__usuario",
                "sucursal_origen",
            ).get(pk=pedido_id)
        except Pedido.DoesNotExist:
            return Response(
                {"error": f"No existe un pedido con id={pedido_id}."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Solo el dueño o un trabajador puede ver el pedido
        es_trabajador = PerfilTrabajador.objects.filter(usuario=request.user).exists()
        es_dueno = pedido.cliente.usuario_id == request.user.pk

        if not es_trabajador and not es_dueno:
            return Response(
                {"error": "No tienes permiso para ver este pedido."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(PedidoOutputSerializer(pedido).data, status=status.HTTP_200_OK)


class AprobarPedidoView(APIView):
    """
    POST /api/v1/orders/pedidos/{pedido_id}/aprobar/

    Aprueba o rechaza un pedido. Solo ejecutivos pueden hacer esto.

    Body:
        {
            "accion": "APROBADO",       // o "RECHAZADO"
            "comentario": "ok"          // opcional
        }
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pedido_id):
        # Verificar que es un trabajador (ejecutivo)
        try:
            perfil_trabajador = PerfilTrabajador.objects.get(usuario=request.user)
        except PerfilTrabajador.DoesNotExist:
            return Response(
                {"error": "Solo los ejecutivos pueden aprobar pedidos."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            pedido = Pedido.objects.get(pk=pedido_id)
        except Pedido.DoesNotExist:
            return Response(
                {"error": f"No existe un pedido con id={pedido_id}."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if pedido.estado_pedido != "PENDIENTE":
            return Response(
                {
                    "error": f"Solo se pueden aprobar pedidos en estado PENDIENTE. Estado actual: {pedido.estado_pedido}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        accion = request.data.get("accion")
        comentario = request.data.get("comentario", "")

        if accion not in ["APROBADO", "RECHAZADO"]:
            return Response(
                {"error": "El campo 'accion' debe ser 'APROBADO' o 'RECHAZADO'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Actualizar el pedido
        pedido.estado_pedido = accion
        pedido.save(update_fields=["estado_pedido"])

        # Registrar la aprobación
        AprobacionPedido.objects.update_or_create(
            pedido=pedido,
            defaults={
                "ejecutivo": perfil_trabajador,
                "estado_aprobacion": accion,
                "comentario": comentario,
                "fecha_aprobacion": __import__("django.utils.timezone", fromlist=["now"]).now(),
            }
        )

        return Response(
            {
                "pedido_id": pedido.id,
                "estado_pedido": pedido.estado_pedido,
                "comentario": comentario,
            },
            status=status.HTTP_200_OK,
        )



