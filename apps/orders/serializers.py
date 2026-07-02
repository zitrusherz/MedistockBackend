from rest_framework import serializers
from apps.orders.models import Pedido, DetallePedido
from apps.inventory.models import Producto, Inventario
from apps.accounts.models import PerfilCliente, DireccionEntrega
from apps.locations.models import Sucursal


# =============================================================================
# Serializers de entrada
# =============================================================================

class DetallePedidoInputSerializer(serializers.Serializer):
    """
    Representa una línea del pedido al momento de crearlo.
    El precio se toma del producto en la BD — el cliente no lo declara.
    El lote es opcional: si no se indica, el backend elige el más próximo
    a vencer con stock disponible en la sucursal de origen (FEFO).
    """
    producto_id = serializers.IntegerField()
    cantidad    = serializers.IntegerField(min_value=1)
    lote_id     = serializers.IntegerField(required=False, allow_null=True)
    observacion = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_producto_id(self, value):
        if not Producto.objects.filter(pk=value, activo=True, es_caja=False).exists():
            raise serializers.ValidationError(f"No existe un producto activo con id={value}.")
        return value


class CrearPedidoInputSerializer(serializers.Serializer):
    """
    Serializer para crear un pedido nuevo.
    El cliente se toma del usuario autenticado — no se recibe en el body.
    Los montos (subtotal, iva, total) se calculan en el backend.
    """
    sucursal_origen_id      = serializers.IntegerField()
    direccion_entrega_id    = serializers.IntegerField()
    tipo_venta              = serializers.ChoiceField(choices=Pedido.TIPO_VENTA_CHOICES)
    tipo_despacho           = serializers.ChoiceField(choices=Pedido.TIPO_DESPACHO_CHOICES, default='NORMAL')
    prioridad_medica        = serializers.ChoiceField(choices=Pedido.PRIORIDAD_CHOICES, default='NORMAL')
    fecha_requerida_entrega = serializers.DateTimeField(required=False, allow_null=True)
    observacion             = serializers.CharField(max_length=255, required=False, allow_blank=True)
    detalles                = DetallePedidoInputSerializer(many=True)

    def validate_sucursal_origen_id(self, value):
        try:
            sucursal = Sucursal.objects.get(pk=value, activo=True)
        except Sucursal.DoesNotExist:
            raise serializers.ValidationError(f"No existe una sucursal activa con id={value}.")
        self._sucursal = sucursal
        return value

    def validate_direccion_entrega_id(self, value):
        # Solo verifica existencia aquí. La pertenencia al cliente se valida
        # en validate() donde ya tenemos acceso al request.
        if not DireccionEntrega.objects.filter(pk=value).exists():
            raise serializers.ValidationError(f"No existe una dirección de entrega con id={value}.")
        return value

    def validate_detalles(self, value):
        if not value:
            raise serializers.ValidationError("El pedido debe tener al menos un producto.")
        return value

    def validate(self, data):
        request = self.context.get("request")

        # Verificar que el usuario tiene perfil de cliente
        try:
            perfil_cliente = PerfilCliente.objects.get(usuario=request.user)
        except PerfilCliente.DoesNotExist:
            raise serializers.ValidationError(
                "El usuario autenticado no tiene un perfil de cliente asociado."
            )
        self._perfil_cliente = perfil_cliente

        # Verificar que la dirección pertenece al cliente autenticado
        if not DireccionEntrega.objects.filter(
            pk=data["direccion_entrega_id"],
            cliente=perfil_cliente
        ).exists():
            raise serializers.ValidationError(
                "La dirección de entrega no pertenece al cliente autenticado."
            )

        # Verificar stock por cada línea en CUALQUIER sucursal (no solo en la sucursal de origen)
        errores_stock = []

        for detalle in data["detalles"]:
            producto_id = detalle["producto_id"]
            cantidad    = detalle["cantidad"]
            lote_id     = detalle.get("lote_id")

            if lote_id:
                # Si se especifica un lote, debe existir en CUALQUIER sucursal con stock
                inventario = Inventario.objects.filter(
                    lote_id=lote_id,
                    lote__producto_id=producto_id,
                ).first()
                if not inventario:
                    errores_stock.append(
                        f"Producto id={producto_id}: lote id={lote_id} no existe en el sistema."
                    )
                else:
                    disponible_neto = (
                        inventario.cantidad_disponible - inventario.cantidad_reservada
                    )
                    if disponible_neto < cantidad:
                        errores_stock.append(
                        f"Producto id={producto_id}: stock insuficiente en lote id={lote_id}. "
                        f"Disponible neto: {disponible_neto}, solicitado: {cantidad}."
                    )
            else:
                # Buscar stock total en CUALQUIER sucursal
                stock_total = Inventario.objects.filter(
                    lote__producto_id=producto_id,
                    lote__activo=True,
                ).values_list("cantidad_disponible", "cantidad_reservada")
                stock_total = sum((d - r) for d, r in stock_total)

                if stock_total < cantidad:
                    errores_stock.append(
                        f"Producto id={producto_id}: stock insuficiente en el sistema. "
                        f"Disponible neto: {stock_total}, solicitado: {cantidad}."
                    )

        if errores_stock:
            raise serializers.ValidationError(errores_stock)

        return data


# =============================================================================
# Serializers de salida
# =============================================================================

class DetallePedidoOutputSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    producto_sku    = serializers.CharField(source="producto.sku", read_only=True)
    lote_codigo     = serializers.SerializerMethodField()

    def get_lote_codigo(self, obj):
        return obj.lote.codigo_lote if obj.lote else None

    class Meta:
        model  = DetallePedido
        fields = [
            "id", "producto_id", "producto_sku", "producto_nombre",
            "lote_id", "lote_codigo", "cantidad", "cantidad_preparada",
            "precio_unitario_historico", "descuento", "subtotal", "observacion",
        ]
        read_only_fields = fields


class PedidoOutputSerializer(serializers.ModelSerializer):
    detalles        = DetallePedidoOutputSerializer(many=True, source="detallepedido_set", read_only=True)
    cliente_nombre  = serializers.SerializerMethodField()
    sucursal_nombre = serializers.CharField(source="sucursal_origen.nombre", read_only=True)

    def get_cliente_nombre(self, obj):
        return obj.cliente.usuario.get_full_name() or obj.cliente.usuario.username

    class Meta:
        model  = Pedido
        fields = [
            "id", "cliente_id", "cliente_nombre",
            "sucursal_origen_id", "sucursal_nombre",
            "direccion_entrega_id", "estado_pedido",
            "tipo_venta", "tipo_despacho", "prioridad_medica",
            "fecha_creacion", "fecha_actualizacion", "fecha_requerida_entrega",
            "subtotal", "descuento_total", "monto_neto", "monto_iva", "total",
            "observacion", "detalles",
        ]
        read_only_fields = fields

class PedidoClienteOutputSerializer(serializers.ModelSerializer):
    detalles = DetallePedidoOutputSerializer(
        many=True,
        source="detallepedido_set",
        read_only=True
    )
    sucursal_nombre = serializers.CharField(source="sucursal_origen.nombre", read_only=True)

    class Meta:
        model = Pedido
        fields = [
            "id",
            "sucursal_nombre",
            "direccion_entrega_id",
            "estado_pedido",
            "tipo_venta",
            "tipo_despacho",
            "prioridad_medica",
            "fecha_creacion",
            "fecha_actualizacion",
            "fecha_requerida_entrega",
            "subtotal",
            "descuento_total",
            "monto_neto",
            "monto_iva",
            "total",
            "observacion",
            "detalles",
        ]
        read_only_fields = fields


#==============================================================
#
#Edicion de pedido
#
#==============================================================

class PedidoClienteUpdateSerializer(serializers.ModelSerializer):
    direccion_entrega_id = serializers.PrimaryKeyRelatedField(
        queryset=DireccionEntrega.objects.all(),
        source="direccion_entrega",
        required=False,
    )

    class Meta:
        model = Pedido
        fields = [
            "direccion_entrega",
            "tipo_despacho",
            "prioridad_medica",
            "fecha_requerida_entrega",
            "observacion",
        ]

    def validate_direccion_entrega(self, value):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Usuario no autenticado.")

        if not hasattr(request.user, "perfilcliente"):
            raise serializers.ValidationError("El usuario no tiene perfil de cliente.")

        if value.cliente_id != request.user.perfilcliente.id:
            raise serializers.ValidationError("La dirección no pertenece al cliente autenticado.")

        return value

    def validate(self, attrs):
        pedido = self.instance

        if pedido.estado_pedido not in ["PENDIENTE", "APROBADO"]:
            raise serializers.ValidationError(
                "Este pedido ya no puede ser modificado por el cliente."
            )

        return attrs

