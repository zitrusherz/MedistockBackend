from rest_framework import serializers

from .models import (
    TransaccionPago,
    ComprobantePago,
    ConciliacionPago,
    Aseguradora,
    PagoAseguradora,
)


# ============================================================
# TRANSACCIONES DE PAGO
# ============================================================

class TransaccionPagoSerializer(serializers.ModelSerializer):
    pedido_id = serializers.IntegerField(source='pedido.id', read_only=True)
    pedido_total = serializers.IntegerField(source='pedido.total', read_only=True)

    class Meta:
        model = TransaccionPago
        fields = [
            'id',
            'pedido',
            'pedido_id',
            'pedido_total',

            'metodo_pago',
            'estado_pago',
            'monto_confirmado',

            # Datos Webpay / pasarela
            'buy_order',
            'session_id',
            'token_ws',
            'id_transaccion_externa',
            'authorization_code',
            'response_code',
            'payment_type_code',
            'installments_number',
            'card_last_digits',
            'webpay_status',
            'transaction_date',
            'raw_response',

            'fecha_creacion',
            'fecha_confirmacion',
            'observacion',
        ]

        read_only_fields = [
            'id',
            'pedido_id',
            'pedido_total',
            'fecha_creacion',
            'fecha_confirmacion',
            'raw_response',
        ]


class TransaccionPagoResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransaccionPago
        fields = [
            'id',
            'metodo_pago',
            'estado_pago',
            'monto_confirmado',
            'authorization_code',
            'response_code',
            'payment_type_code',
            'installments_number',
            'card_last_digits',
            'webpay_status',
            'transaction_date',
            'fecha_creacion',
            'fecha_confirmacion',
        ]


# ============================================================
# WEBPAY - INICIAR PAGO
# ============================================================

class WebpayCrearTransaccionSerializer(serializers.Serializer):
    """
    Serializer de entrada para iniciar una transacción Webpay.

    Espera:
    {
        "pedido_id": 1
    }

    El monto debe obtenerse desde el pedido en backend,
    no desde el frontend, para evitar manipulación de precio.
    """

    pedido_id = serializers.IntegerField()

    def validate_pedido_id(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'El pedido_id debe ser un número válido.'
            )
        return value


class WebpayCrearTransaccionResponseSerializer(serializers.Serializer):
    """
    Respuesta entregada al frontend para redirigir al usuario a Webpay.
    """

    transaccion_pago_id = serializers.IntegerField()
    pedido_id = serializers.IntegerField()
    buy_order = serializers.CharField()
    session_id = serializers.CharField()
    amount = serializers.IntegerField()
    token = serializers.CharField()
    url = serializers.URLField()
    redirect_url = serializers.CharField()


# ============================================================
# WEBPAY - CONFIRMAR PAGO
# ============================================================

class WebpayCommitSerializer(serializers.Serializer):
    """
    Serializer de entrada para confirmar una transacción Webpay.

    Webpay normalmente retorna token_ws por query param o POST.
    """

    token_ws = serializers.CharField(required=True, allow_blank=False)

    def validate_token_ws(self, value):
        value = str(value).strip()

        if not value:
            raise serializers.ValidationError(
                'El token_ws es obligatorio.'
            )

        return value


class WebpayCommitResponseSerializer(serializers.Serializer):
    """
    Respuesta normalizada del commit de Webpay.
    """

    transaccion_pago_id = serializers.IntegerField(required=False)
    pedido_id = serializers.IntegerField(required=False)
    aprobada = serializers.BooleanField()
    estado_pago = serializers.CharField(required=False)

    token_ws = serializers.CharField()
    response_code = serializers.IntegerField(allow_null=True)
    status = serializers.CharField(allow_null=True, required=False)
    buy_order = serializers.CharField(allow_null=True, required=False)
    session_id = serializers.CharField(allow_null=True, required=False)
    amount = serializers.IntegerField(allow_null=True, required=False)
    authorization_code = serializers.CharField(allow_null=True, required=False)
    payment_type_code = serializers.CharField(allow_null=True, required=False)
    installments_number = serializers.IntegerField(allow_null=True, required=False)
    card_detail = serializers.DictField(required=False)
    transaction_date = serializers.CharField(allow_null=True, required=False)


# ============================================================
# WEBPAY - CONSULTAR ESTADO
# ============================================================

class WebpayStatusSerializer(serializers.Serializer):
    token_ws = serializers.CharField(required=True, allow_blank=False)

    def validate_token_ws(self, value):
        value = str(value).strip()

        if not value:
            raise serializers.ValidationError(
                'El token_ws es obligatorio.'
            )

        return value


# ============================================================
# COMPROBANTE DE PAGO / TRANSFERENCIA
# ============================================================

class ComprobantePagoSerializer(serializers.ModelSerializer):
    pedido_id = serializers.IntegerField(source='pedido.id', read_only=True)

    class Meta:
        model = ComprobantePago
        fields = [
            'id',
            'pedido',
            'pedido_id',
            'archivo_url',
            'banco_origen',
            'numero_operacion',
            'fecha_transferencia',
            'monto_reportado',
            'estado_validacion',
            'observacion',
        ]

        read_only_fields = [
            'id',
            'pedido_id',
            'estado_validacion',
        ]

    def validate_monto_reportado(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'El monto reportado debe ser mayor a cero.'
            )
        return value


class ComprobantePagoRevisionSerializer(serializers.ModelSerializer):
    """
    Serializer para que el analista valide o rechace un comprobante.
    """

    class Meta:
        model = ComprobantePago
        fields = [
            'estado_validacion',
            'observacion',
        ]

    def validate_estado_validacion(self, value):
        estados_permitidos = ['VALIDADO', 'RECHAZADO']

        if value not in estados_permitidos:
            raise serializers.ValidationError(
                'El estado debe ser VALIDADO o RECHAZADO.'
            )

        return value


# ============================================================
# CONCILIACIÓN DE PAGOS
# ============================================================

class ConciliacionPagoSerializer(serializers.ModelSerializer):
    transaccion_pago = TransaccionPagoResumenSerializer(read_only=True)
    transaccion_pago_id = serializers.PrimaryKeyRelatedField(
        queryset=TransaccionPago.objects.all(),
        source='transaccion_pago',
        write_only=True
    )

    analista_nombre = serializers.SerializerMethodField()

    class Meta:
        model = ConciliacionPago
        fields = [
            'id',
            'transaccion_pago',
            'transaccion_pago_id',
            'analista',
            'analista_nombre',
            'fecha_conciliacion',
            'estado_conciliacion',
            'observacion',
        ]

        read_only_fields = [
            'id',
            'analista',
            'analista_nombre',
            'fecha_conciliacion',
        ]

    def get_analista_nombre(self, obj):
        if not obj.analista or not obj.analista.usuario:
            return None

        return f'{obj.analista.usuario.first_name} {obj.analista.usuario.last_name}'.strip()


# ============================================================
# ASEGURADORAS
# ============================================================

class AseguradoraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aseguradora
        fields = [
            'id',
            'nombre',
            'rut',
            'contacto',
            'email',
            'telefono',
            'activo',
        ]


class AseguradoraResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aseguradora
        fields = [
            'id',
            'nombre',
            'rut',
        ]


# ============================================================
# PAGO ASEGURADORA
# ============================================================

class PagoAseguradoraSerializer(serializers.ModelSerializer):
    aseguradora = AseguradoraResumenSerializer(read_only=True)
    aseguradora_id = serializers.PrimaryKeyRelatedField(
        queryset=Aseguradora.objects.filter(activo=True),
        source='aseguradora',
        write_only=True
    )

    pedido_id = serializers.IntegerField(source='pedido.id', read_only=True)

    class Meta:
        model = PagoAseguradora
        fields = [
            'id',
            'pedido',
            'pedido_id',
            'aseguradora',
            'aseguradora_id',
            'monto_cubierto',
            'estado',
            'fecha_registro',
            'observacion',
        ]

        read_only_fields = [
            'id',
            'pedido_id',
            'fecha_registro',
        ]

    def validate_monto_cubierto(self, value):
        if value < 0:
            raise serializers.ValidationError(
                'El monto cubierto no puede ser negativo.'
            )
        return value