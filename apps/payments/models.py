# apps/payments/models.py
from django.conf import settings
from django.db import models



class TransaccionPago(models.Model):
    METODO_CHOICES = [
        ('WEBPAY', 'WebPay'),
        ('MERCADOPAGO', 'MercadoPago'),
        ('TRANSFERENCIA', 'Transferencia'),
        ('CREDITO_INSTITUCIONAL', 'Crédito institucional'),
    ]

    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('INICIADO', 'Iniciado'),
        ('AUTORIZADO', 'Autorizado'),
        ('CONFIRMADO', 'Confirmado'),
        ('RECHAZADO', 'Rechazado'),
        ('ANULADO', 'Anulado'),
        ('REEMBOLSADO', 'Reembolsado'),
        ('ERROR', 'Error'),
    ]

    pedido = models.ForeignKey('orders.Pedido', on_delete=models.CASCADE)

    metodo_pago = models.CharField(
        max_length=30,
        choices=METODO_CHOICES
    )

    estado_pago = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE'
    )

    monto_confirmado = models.IntegerField(default=0)

    # ============================================================
    # CAMPOS WEBPAY / PASARELA EXTERNA
    # ============================================================

    buy_order = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Orden de compra enviada a Webpay.'
    )

    session_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Identificador de sesión enviado a Webpay.'
    )

    token_ws = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Token entregado por Webpay al crear o confirmar la transacción.'
    )

    id_transaccion_externa = models.CharField(
        max_length=180,
        blank=True,
        null=True,
        help_text='Identificador externo de la transacción, si la pasarela lo entrega.'
    )

    authorization_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Código de autorización entregado por Webpay.'
    )

    response_code = models.IntegerField(
        blank=True,
        null=True,
        help_text='Código de respuesta de Webpay. Normalmente 0 indica aprobación.'
    )

    payment_type_code = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text='Tipo de pago informado por Webpay.'
    )

    installments_number = models.IntegerField(
        blank=True,
        null=True,
        help_text='Cantidad de cuotas informadas por Webpay.'
    )

    card_last_digits = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        help_text='Últimos cuatro dígitos de la tarjeta.'
    )

    webpay_status = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Estado técnico devuelto por Webpay. Ej: AUTHORIZED.'
    )

    transaction_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text='Fecha de transacción informada por Webpay.'
    )

    raw_response = models.JSONField(
        blank=True,
        null=True,
        help_text='Respuesta completa devuelta por Webpay.'
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_confirmacion = models.DateTimeField(blank=True, null=True)

    observacion = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    class Meta:
        db_table = 'transaccion_pago'
        managed = False


class ComprobantePago(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE_REVISION', 'Pendiente revisión'),
        ('VALIDADO', 'Validado'),
        ('RECHAZADO', 'Rechazado'),
    ]

    pedido = models.ForeignKey('orders.Pedido', on_delete=models.CASCADE)
    archivo_url = models.CharField(max_length=500, blank=True, null=True)
    banco_origen = models.CharField(max_length=120, blank=True, null=True)
    numero_operacion = models.CharField(max_length=120, blank=True, null=True)
    fecha_transferencia = models.DateTimeField(blank=True, null=True)
    monto_reportado = models.IntegerField(default=0)
    estado_validacion = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE_REVISION')
    observacion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'comprobante_pago'
        managed = False


class ConciliacionPago(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('CONCILIADO', 'Conciliado'),
        ('DIFERENCIA_DE_MONTO', 'Diferencia de monto'),
        ('RECHAZADO', 'Rechazado'),
    ]

    transaccion_pago = models.OneToOneField(TransaccionPago, on_delete=models.CASCADE)
    analista = models.ForeignKey('accounts.PerfilTrabajador', on_delete=models.RESTRICT)
    fecha_conciliacion = models.DateTimeField(auto_now_add=True)
    estado_conciliacion = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    observacion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'conciliacion_pago'
        managed = False


class Aseguradora(models.Model):
    nombre = models.CharField(max_length=180)
    rut = models.CharField(max_length=20, unique=True, blank=True, null=True)
    contacto = models.CharField(max_length=150, blank=True, null=True)
    email = models.CharField(max_length=180, blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'aseguradora'
        managed = False


class PagoAseguradora(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
        ('PAGADO', 'Pagado'),
    ]

    pedido = models.ForeignKey('orders.Pedido', on_delete=models.CASCADE)
    aseguradora = models.ForeignKey(Aseguradora, on_delete=models.RESTRICT)
    monto_cubierto = models.IntegerField(default=0)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='PENDIENTE')
    fecha_registro = models.DateTimeField(auto_now_add=True)
    observacion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'pago_aseguradora'
        managed = False