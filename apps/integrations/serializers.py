from rest_framework import serializers
from apps.inventory.models import Producto, Inventario
from apps.locations.models import Sucursal
from apps.accounts.models import DireccionEntrega, PerfilCliente
from apps.orders.models import Pedido


class LineaPedidoB2BSerializer(serializers.Serializer):
    """
    Una línea del pedido B2B. Igual que el pedido normal, pero
    el ERP siempre puede especificar el lote (tiene visibilidad de stock via catálogo).
    """
    producto_sku = serializers.CharField(
        max_length=80,
        help_text="SKU del producto. Úsalo desde GET /api/inventory/catalogo/"
    )
    cantidad = serializers.IntegerField(min_value=1)
    lote_id = serializers.IntegerField(required=False, allow_null=True)
    observacion = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=''
    )

    def validate_producto_sku(self, value):
        if not Producto.objects.filter(sku=value, activo=True, es_caja=False).exists():
            raise serializers.ValidationError(
                f"No existe un producto activo con SKU '{value}'."
            )
        return value


class PedidoB2BInputSerializer(serializers.Serializer):
    """
    Serializer para pedidos creados por sistemas ERP externos via API Key.

    Diferencias respecto al pedido de cliente web:
    - Se identifica por producto SKU (más estable que IDs internos para ERPs)
    - La institución se toma del ApiClient autenticado, no del body
    - tipo_venta siempre es CREDITO_INSTITUCIONAL o TRANSFERENCIA
    - No requiere direccion_entrega_id si la institución tiene una principal
    """
    sucursal_id = serializers.IntegerField(
        help_text="ID de la sucursal desde donde despachar. "
                  "Obtén la lista en GET /api/locations/sucursales/"
    )
    direccion_entrega_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID de dirección de entrega de la institución. "
                  "Si se omite, se usa la dirección principal registrada."
    )
    tipo_venta = serializers.ChoiceField(
        choices=[('TRANSFERENCIA', 'Transferencia'), ('CREDITO_INSTITUCIONAL', 'Crédito institucional')],
        default='CREDITO_INSTITUCIONAL',
    )
    tipo_despacho = serializers.ChoiceField(
        choices=Pedido.TIPO_DESPACHO_CHOICES,
        default='NORMAL',
    )
    prioridad_medica = serializers.ChoiceField(
        choices=Pedido.PRIORIDAD_CHOICES,
        default='NORMAL',
    )
    fecha_requerida_entrega = serializers.DateTimeField(required=False, allow_null=True)
    referencia_erp = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text="Número de orden interna del ERP de la clínica (para trazabilidad)."
    )
    observacion = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=''
    )
    lineas = LineaPedidoB2BSerializer(many=True)

    # Guardamos el perfil_cliente y la sucursal resueltos para usarlos en la view
    _perfil_cliente = None
    _sucursal = None
    _direccion_entrega = None

    def validate_sucursal_id(self, value):
        try:
            sucursal = Sucursal.objects.get(pk=value, activo=True)
        except Sucursal.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe una sucursal activa con id={value}."
            )
        self._sucursal = sucursal
        return value

    def validate_lineas(self, value):
        if not value:
            raise serializers.ValidationError(
                "El pedido debe incluir al menos una línea de producto."
            )
        return value

    def validate(self, attrs):
        # El api_client viene del request (autenticado via API Key)
        api_client = self.context['request'].user
        institucion = api_client.institucion

        # Resolver el PerfilCliente institucional
        try:
            perfil_cliente = PerfilCliente.objects.get(
                institucion=institucion,
                tipo_cliente='INSTITUCIONAL',
                activo=True,
            )
        except PerfilCliente.DoesNotExist:
            raise serializers.ValidationError(
                f"La institución '{institucion.razon_social}' no tiene un perfil de cliente "
                "activo configurado en el sistema. Contacta a MEDISTOCK."
            )
        except PerfilCliente.MultipleObjectsReturned:
            perfil_cliente = PerfilCliente.objects.filter(
                institucion=institucion,
                tipo_cliente='INSTITUCIONAL',
                activo=True,
            ).first()

        self._perfil_cliente = perfil_cliente

        # Resolver dirección de entrega
        direccion_id = attrs.get('direccion_entrega_id')
        if direccion_id:
            try:
                direccion = DireccionEntrega.objects.get(
                    pk=direccion_id,
                    institucion=institucion,
                    activo=True,
                )
            except DireccionEntrega.DoesNotExist:
                raise serializers.ValidationError(
                    {'direccion_entrega_id': 'La dirección no pertenece a tu institución o no está activa.'}
                )
        else:
            # Usar la dirección principal de la institución
            direccion = DireccionEntrega.objects.filter(
                institucion=institucion,
                es_principal=True,
                activo=True,
            ).first()
            if not direccion:
                raise serializers.ValidationError(
                    {
                        'direccion_entrega_id': 'No se especificó dirección y la institución no tiene dirección principal registrada.'}
                )

        self._direccion_entrega = direccion

        # Verificar stock por cada línea
        sucursal_id = attrs.get('sucursal_id')
        errores_stock = []

        for linea in attrs['lineas']:
            sku = linea['producto_sku']
            cantidad = linea['cantidad']
            lote_id = linea.get('lote_id')

            producto = Producto.objects.get(sku=sku)

            if lote_id:
                inv = Inventario.objects.filter(
                    lote_id=lote_id,
                    lote__producto=producto,
                    sucursal_id=sucursal_id,
                ).first()
                if not inv:
                    errores_stock.append(
                        f"SKU '{sku}': lote id={lote_id} no existe en esa sucursal."
                    )
                elif (inv.cantidad_disponible - inv.cantidad_reservada) < cantidad:
                    neto = inv.cantidad_disponible - inv.cantidad_reservada
                    errores_stock.append(
                        f"SKU '{sku}': stock insuficiente en lote {lote_id}. "
                        f"Disponible: {neto}, solicitado: {cantidad}."
                    )
            else:
                stock_neto = sum(
                    d - r for d, r in Inventario.objects.filter(
                        lote__producto=producto,
                        sucursal_id=sucursal_id,
                        lote__activo=True,
                    ).values_list('cantidad_disponible', 'cantidad_reservada')
                )
                if stock_neto < cantidad:
                    errores_stock.append(
                        f"SKU '{sku}': stock insuficiente en la sucursal. "
                        f"Disponible: {stock_neto}, solicitado: {cantidad}."
                    )

        if errores_stock:
            raise serializers.ValidationError({'stock': errores_stock})

        return attrs


class PedidoB2BOutputSerializer(serializers.Serializer):
    """Respuesta minimalista pensada para consumo por ERPs."""
    pedido_id = serializers.IntegerField()
    referencia_erp = serializers.CharField(allow_null=True)
    estado = serializers.CharField()
    institucion = serializers.CharField()
    total = serializers.IntegerField()
    monto_iva = serializers.IntegerField()
    monto_neto = serializers.IntegerField()
    lineas = serializers.ListField()
    fecha_creacion = serializers.DateTimeField()
    mensaje = serializers.CharField()