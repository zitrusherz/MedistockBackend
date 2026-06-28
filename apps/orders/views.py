from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from apps.orders.permissions import (
    EsPedidoPropioOTrabajador,
    ClientePuedeEditarPedidoHastaAprobado,
)
from django.db import transaction
from django.db.models import F, Sum
from rest_framework.exceptions import ValidationError

from apps.orders.models import Pedido, DetallePedido, AprobacionPedido, Cotizacion
from apps.orders.serializers import (
    CrearPedidoInputSerializer,
    PedidoOutputSerializer,
PedidoClienteUpdateSerializer
)
from apps.inventory.models import Inventario
from apps.orders.services.inventario import reservar_stock_pedido, consumir_reserva_pedido
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
        cantidad_disponible__gte=F("cantidad_reservada") + cantidad,
    ).order_by("lote__fecha_vencimiento").select_related("lote").first()


class CrearPedidoView(APIView):
    """
    POST /api/orders/pedidos/

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

        try:
            reservar_stock_pedido(pedido, request.user)
        except ValidationError as exc:
            transaction.set_rollback(True)
            return Response(exc.detail, status=status.HTTP_409_CONFLICT)

        return Response(
            PedidoOutputSerializer(pedido).data,
            status=status.HTTP_201_CREATED,
        )


class DetallePedidoView(APIView):
    """
    GET /api/orders/pedidos/{pedido_id}/

    Retorna el detalle completo de un pedido, incluyendo sus líneas.
    Solo el cliente dueño del pedido o un trabajador interno puede verlo.
    """
    permission_classes = [IsAuthenticated,EsPedidoPropioOTrabajador,
        ClientePuedeEditarPedidoHastaAprobado, ]

    def get_object(self, request, pedido_id):
        try:
            pedido = Pedido.objects.prefetch_related(
                "detallepedido_set__producto",
                "detallepedido_set__lote",
            ).select_related(
                "cliente__usuario",
                "sucursal_origen",
            ).get(pk=pedido_id)
        except Pedido.DoesNotExist:
            return None

        self.check_object_permissions(request, pedido)
        return pedido

    def get(self, request, pedido_id):
        pedido = self.get_object(request, pedido_id)

        if pedido is None:
            return Response(
                {"error": f"No existe un pedido con id={pedido_id}."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(PedidoOutputSerializer(pedido).data, status=status.HTTP_200_OK)

    def patch(self, request, pedido_id):
        pedido = self.get_object(request, pedido_id)

        if pedido is None:
            return Response(
                {"error": f"No existe un pedido con id={pedido_id}."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if hasattr(request.user, "perfilcliente"):
            serializer = PedidoClienteUpdateSerializer(
                pedido,
                data=request.data,
                partial=True,
                context={"request": request},
            )
        else:
            return Response(
                {"error": "Este endpoint de edición está pensado para clientes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        pedido.refresh_from_db()

        return Response(
            PedidoOutputSerializer(pedido).data,
            status=status.HTTP_200_OK,
        )


class AprobarPedidoView(APIView):
    """
    POST /api/orders/pedidos/{pedido_id}/aprobar/

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
        if not request.user.groups.filter(
                name__in=["Ejecutivo", "Administrador"]).exists() and not request.user.is_staff:
            return Response(
                {"error": "Solo los ejecutivos pueden aprobar pedidos."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            perfil_trabajador = PerfilTrabajador.objects.get(usuario=request.user)
        except PerfilTrabajador.DoesNotExist:
            return Response(
                {"error": "El usuario no tiene perfil de trabajador asociado."},
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
        if accion == "APROBADO":
            nuevo_estado_pedido = "APROBADO"
        else:
            nuevo_estado_pedido = "CANCELADO"

        pedido.estado_pedido = nuevo_estado_pedido
        pedido.save(update_fields=["estado_pedido"])

        if accion == "APROBADO":
            try:
                consumir_reserva_pedido(
                    pedido,
                    usuario=request.user,
                    motivo="Aprobacion de pedido",
                )
            except ValidationError as exc:
                transaction.set_rollback(True)
                return Response(exc.detail, status=status.HTTP_409_CONFLICT)

        # Registrar la aprobación
        AprobacionPedido.objects.update_or_create(
            pedido=pedido,
            defaults={
                "ejecutivo": perfil_trabajador,
                "estado_aprobacion": accion,
                "comentario": comentario,
                "fecha_aprobacion": timezone.now(),
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

class MisPedidosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not hasattr(request.user, "perfilcliente"):
            return Response(
                {"error": "Solo los clientes pueden ver sus pedidos desde este endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )

        pedidos = Pedido.objects.filter(
            cliente=request.user.perfilcliente
        ).select_related(
            "cliente__usuario",
            "sucursal_origen",
        ).prefetch_related(
            "detallepedido_set__producto",
            "detallepedido_set__lote",
        ).order_by("-fecha_creacion")

        serializer = PedidoOutputSerializer(pedidos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ListarPedidosView(APIView):
    """
    GET /api/orders/pedidos/todos/

    Lista todos los pedidos.
    Solo Administrador, Ejecutivo o usuarios staff pueden acceder.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        es_trabajador_autorizado = request.user.groups.filter(
            name__in=["Ejecutivo", "Administrador"]
        ).exists()

        if not es_trabajador_autorizado and not request.user.is_staff:
            return Response(
                {"error": "No tienes permiso para ver todos los pedidos."},
                status=status.HTTP_403_FORBIDDEN,
            )

        pedidos = Pedido.objects.select_related(
            "cliente__usuario",
            "institucion",
            "sucursal_origen",
            "direccion_entrega",
            "operador_asignado",
        ).prefetch_related(
            "detallepedido_set__producto",
            "detallepedido_set__lote",
        ).order_by("-fecha_creacion")

        serializer = PedidoOutputSerializer(pedidos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResumenCotizacionesView(APIView):
    """
    GET /api/orders/cotizaciones/resumen/

    Alimenta el KPI "Cotizaciones pendientes" del panel operativo (T4.1).
    Sin parámetros.

    - pendientes: cotizaciones aún sin convertir en pedido / sin resolver
      (estado BORRADOR o ENVIADA).
    - total: total histórico de cotizaciones.
    - monto_pendiente: suma de total_estimado de las cotizaciones pendientes.
    """

    permission_classes = [IsAuthenticated]

    ROLES_PERMITIDOS = ['Administrador', 'Ejecutivo', 'Analista']

    ESTADOS_PENDIENTES = ['BORRADOR', 'ENVIADA']

    def get(self, request):
        tiene_permiso = (
            request.user.is_staff
            or request.user.groups.filter(name__in=self.ROLES_PERMITIDOS).exists()
        )

        if not tiene_permiso:
            return Response(
                {"error": "Solo Administrador, Ejecutivo o Analista pueden ver este resumen."},
                status=status.HTTP_403_FORBIDDEN,
            )

        cotizaciones_pendientes = Cotizacion.objects.filter(
            estado__in=self.ESTADOS_PENDIENTES
        )

        pendientes = cotizaciones_pendientes.count()
        total = Cotizacion.objects.count()
        monto_pendiente = cotizaciones_pendientes.aggregate(
            suma=Sum('total_estimado')
        )['suma'] or 0

        return Response(
            {
                "pendientes": pendientes,
                "total": total,
                "monto_pendiente": monto_pendiente,
            },
            status=status.HTTP_200_OK,
        )