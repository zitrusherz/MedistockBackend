from django.conf import settings
from django.db import models


class Cotizacion(models.Model):
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('ENVIADA', 'Enviada'),
        ('ACEPTADA', 'Aceptada'),
        ('RECHAZADA', 'Rechazada'),
        ('VENCIDA', 'Vencida'),
        ('CONVERTIDA_EN_PEDIDO', 'Convertida en pedido'),
    ]

    institucion = models.ForeignKey('accounts.Institucion', on_delete=models.RESTRICT)
    cliente = models.ForeignKey('accounts.PerfilCliente', on_delete=models.RESTRICT)
    ejecutivo = models.ForeignKey('accounts.PerfilTrabajador', on_delete=models.RESTRICT)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    estado = models.CharField(max_length=30, choices=ESTADO_CHOICES, default='BORRADOR')
    total_estimado = models.IntegerField(default=0)
    observacion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'cotizacion'
        managed = False


class DetalleCotizacion(models.Model):
    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE)
    producto = models.ForeignKey('inventory.Producto', on_delete=models.RESTRICT)
    cantidad = models.IntegerField()
    precio_unitario_estimado = models.IntegerField(default=0)
    descuento = models.IntegerField(default=0)
    subtotal = models.IntegerField(default=0)

    class Meta:
        db_table = 'detalle_cotizacion'
        managed = False


class Pedido(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('EN_PICKING', 'En picking'),
        ('DESPACHADO', 'Despachado'),
        ('ENTREGADO', 'Entregado'),
        ('CANCELADO', 'Cancelado'),
    ]
    TIPO_VENTA_CHOICES = [
        ('WEBPAY', 'WebPay'),
        ('TRANSFERENCIA', 'Transferencia'),
        ('MAYORISTA', 'Mayorista'),
        ('CREDITO_INSTITUCIONAL', 'Crédito institucional'),
    ]
    TIPO_DESPACHO_CHOICES = [
        ('NORMAL', 'Normal'),
        ('EXPRESS', 'Express'),
    ]
    PRIORIDAD_CHOICES = [
        ('NORMAL', 'Normal'),
        ('ALTA', 'Alta'),
        ('CRITICA', 'Crítica'),
    ]

    cliente = models.ForeignKey('accounts.PerfilCliente', on_delete=models.RESTRICT)
    institucion = models.ForeignKey('accounts.Institucion', on_delete=models.SET_NULL, null=True, blank=True)
    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.SET_NULL, null=True, blank=True)
    sucursal_origen = models.ForeignKey('locations.Sucursal', on_delete=models.RESTRICT)
    direccion_entrega = models.ForeignKey('accounts.DireccionEntrega', on_delete=models.RESTRICT)
    operador_asignado = models.ForeignKey('accounts.PerfilTrabajador', on_delete=models.SET_NULL, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    estado_pedido = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    tipo_venta = models.CharField(max_length=30, choices=TIPO_VENTA_CHOICES)
    tipo_despacho = models.CharField(max_length=10, choices=TIPO_DESPACHO_CHOICES, default='NORMAL')
    prioridad_medica = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default='NORMAL')
    fecha_requerida_entrega = models.DateTimeField(blank=True, null=True)
    subtotal = models.IntegerField(default=0)
    descuento_total = models.IntegerField(default=0)
    monto_neto = models.IntegerField(default=0)
    monto_iva = models.IntegerField(default=0)
    total = models.IntegerField(default=0)
    observacion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'pedido'
        managed = False


class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    producto = models.ForeignKey('inventory.Producto', on_delete=models.RESTRICT)
    lote = models.ForeignKey('inventory.Lote', on_delete=models.SET_NULL, null=True, blank=True)
    cantidad = models.IntegerField()
    cantidad_preparada = models.IntegerField(default=0)
    precio_unitario_historico = models.IntegerField()
    descuento = models.IntegerField(default=0)
    subtotal = models.IntegerField(default=0)
    observacion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'detalle_pedido'
        managed = False


class AprobacionPedido(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
    ]

    pedido = models.OneToOneField(Pedido, on_delete=models.CASCADE)
    ejecutivo = models.ForeignKey('accounts.PerfilTrabajador', on_delete=models.RESTRICT)
    fecha_aprobacion = models.DateTimeField(blank=True, null=True)
    estado_aprobacion = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='PENDIENTE')
    comentario = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'aprobacion_pedido'
        managed = False