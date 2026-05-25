import time
from django.db import transaction
from django.db.models import F
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .authentication import ApiKeyAuthentication
from .permissions import EsApiClientActivo
from .models import RegistroIntegracion
from .serializers import PedidoB2BInputSerializer, PedidoB2BOutputSerializer
from apps.inventory.models import Producto, Inventario
from apps.orders.models import Pedido, DetallePedido
from apps.orders.services.inventario import reservar_stock_pedido
from rest_framework.exceptions import ValidationError

IVA = 0.19


def _elegir_lote_fefo(producto_id: int, sucursal_id: int, cantidad: int):
    return Inventario.objects.filter(
        lote__producto_id=producto_id,
        sucursal_id=sucursal_id,
        lote__activo=True,
        cantidad_disponible__gte=F('cantidad_reservada') + cantidad,
    ).order_by('lote__fecha_vencimiento').select_related('lote').first()


class PedidoB2BView(APIView):
    """
    POST /api/integrations/pedidos/

    Endpoint para que sistemas ERP de clínicas creen pedidos directamente,
    sin intervención humana. Se autentica con API Key (header X-Api-Key).

    La institución se determina desde la API Key — no se declara en el body.
    """
    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [EsApiClientActivo]

    @transaction.atomic
    def post(self, request):
        inicio = time.time()
        api_client = request.user  # Es el ApiClient, no un Usuario Django

        serializer = PedidoB2BInputSerializer(
            data=request.data,
            context={'request': request},
        )

        if not serializer.is_valid():
            self._registrar(api_client, request, None, 400, False,
                            str(serializer.errors), inicio)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        perfil_cliente = serializer._perfil_cliente
        direccion = serializer._direccion_entrega
        referencia_erp = data.get('referencia_erp', '')

        # Resolver productos, lotes y precios
        lineas_resueltas = []
        for linea in data['lineas']:
            producto = Producto.objects.get(sku=linea['producto_sku'])
            lote_id = linea.get('lote_id')

            if not lote_id:
                inv = _elegir_lote_fefo(producto.id, data['sucursal_id'], linea['cantidad'])
                if not inv:
                    transaction.set_rollback(True)
                    self._registrar(api_client, request, None, 409, False,
                                    f"Race condition de stock en SKU {linea['producto_sku']}", inicio)
                    return Response(
                        {'error': f"Sin stock para SKU '{linea['producto_sku']}'. Intenta de nuevo."},
                        status=status.HTTP_409_CONFLICT,
                    )
                lote_id = inv.lote_id

            lineas_resueltas.append({
                **linea,
                '_producto': producto,
                '_lote_id': lote_id,
                '_precio': producto.valor_unitario,
            })

        # Calcular montos
        subtotal = sum(l['_precio'] * l['cantidad'] for l in lineas_resueltas)
        monto_neto = subtotal
        monto_iva = int(monto_neto * IVA)
        total = monto_neto + monto_iva

        # Observación: incluir referencia ERP si viene
        observacion_final = data.get('observacion', '')
        if referencia_erp:
            observacion_final = f"[ERP:{referencia_erp}] {observacion_final}".strip()

        # Crear pedido
        pedido = Pedido.objects.create(
            cliente=perfil_cliente,
            institucion=perfil_cliente.institucion,
            sucursal_origen_id=data['sucursal_id'],
            direccion_entrega=direccion,
            tipo_venta=data.get('tipo_venta', 'CREDITO_INSTITUCIONAL'),
            tipo_despacho=data.get('tipo_despacho', 'NORMAL'),
            prioridad_medica=data.get('prioridad_medica', 'NORMAL'),
            fecha_requerida_entrega=data.get('fecha_requerida_entrega'),
            observacion=observacion_final,
            estado_pedido='PENDIENTE',
            subtotal=subtotal,
            descuento_total=0,
            monto_neto=monto_neto,
            monto_iva=monto_iva,
            total=total,
        )

        # Crear detalles
        lineas_output = []
        for linea in lineas_resueltas:
            subtotal_linea = linea['_precio'] * linea['cantidad']
            DetallePedido.objects.create(
                pedido=pedido,
                producto=linea['_producto'],
                lote_id=linea['_lote_id'],
                cantidad=linea['cantidad'],
                precio_unitario_historico=linea['_precio'],
                descuento=0,
                subtotal=subtotal_linea,
                observacion=linea.get('observacion', ''),
            )
            lineas_output.append({
                'producto_sku': linea['producto_sku'],
                'producto_nombre': linea['_producto'].nombre,
                'lote_id': linea['_lote_id'],
                'cantidad': linea['cantidad'],
                'precio_unitario': linea['_precio'],
                'subtotal': subtotal_linea,
            })

        # Reservar stock
        try:
            reservar_stock_pedido(pedido, request.user)
        except ValidationError as exc:
            transaction.set_rollback(True)
            self._registrar(api_client, request, None, 409, False, str(exc.detail), inicio)
            return Response(exc.detail, status=status.HTTP_409_CONFLICT)

        # Registrar el log de integración
        self._registrar(api_client, request, pedido, 201, True, None, inicio)

        output = {
            'pedido_id': pedido.id,
            'referencia_erp': referencia_erp or None,
            'estado': pedido.estado_pedido,
            'institucion': perfil_cliente.institucion.razon_social,
            'total': total,
            'monto_neto': monto_neto,
            'monto_iva': monto_iva,
            'lineas': lineas_output,
            'fecha_creacion': pedido.fecha_creacion,
            'mensaje': 'Pedido creado correctamente. Quedará en estado PENDIENTE hasta aprobación.',
        }

        return Response(
            PedidoB2BOutputSerializer(output).data,
            status=status.HTTP_201_CREATED,
        )

    def _registrar(self, api_client, request, pedido, status_code, exitoso, error, inicio):
        """Guarda un log en registro_integracion."""
        try:
            ms = int((time.time() - inicio) * 1000)
            RegistroIntegracion.objects.create(
                api_client=api_client,
                pedido=pedido,
                tipo_evento='REQUEST_ENTRANTE',
                endpoint=request.path,
                metodo=request.method,
                status_code=status_code,
                tiempo_respuesta_ms=ms,
                exitoso=exitoso,
                mensaje_error=error,
            )
        except Exception:
            pass  