# apps/billing/models.py
from django.conf import settings
from django.db import models


class TipoDocumentoTributario(models.Model):
    codigo_sii = models.IntegerField(unique=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    afecta_iva = models.BooleanField(default=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'tipo_documento_tributario'
        managed = False

    def __str__(self):
        return f'{self.codigo_sii} - {self.nombre}'


class FolioDte(models.Model):
    tipo_documento = models.ForeignKey(TipoDocumentoTributario, on_delete=models.RESTRICT)
    folio_desde = models.IntegerField()
    folio_hasta = models.IntegerField()
    folio_actual = models.IntegerField()
    fecha_autorizacion = models.DateField(blank=True, null=True)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    archivo_caf_url = models.CharField(max_length=500, blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'folio_dte'
        managed = False


class DocumentoTributario(models.Model):
    ESTADO_DTE_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('GENERADO', 'Generado'),
        ('FIRMADO', 'Firmado'),
        ('ENVIADO_SII', 'Enviado SII'),
        ('ACEPTADO_SII', 'Aceptado SII'),
        ('RECHAZADO_SII', 'Rechazado SII'),
        ('ENVIADO_CLIENTE', 'Enviado cliente'),
        ('ANULADO_POR_NOTA_CREDITO', 'Anulado por nota de crédito'),
    ]
    FORMA_PAGO_CHOICES = [
        ('CONTADO', 'Contado'),
        ('CREDITO', 'Crédito'),
        ('TRANSFERENCIA', 'Transferencia'),
        ('TARJETA', 'Tarjeta'),
    ]

    tipo_documento = models.ForeignKey(TipoDocumentoTributario, on_delete=models.RESTRICT)
    pedido = models.ForeignKey('orders.Pedido', on_delete=models.SET_NULL, null=True, blank=True)
    cliente = models.ForeignKey('accounts.PerfilCliente', on_delete=models.SET_NULL, null=True, blank=True)
    institucion = models.ForeignKey('accounts.Institucion', on_delete=models.SET_NULL, null=True, blank=True)
    folio_dte = models.ForeignKey(FolioDte, on_delete=models.SET_NULL, null=True, blank=True)
    folio = models.IntegerField()
    fecha_emision = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    estado_dte = models.CharField(max_length=30, choices=ESTADO_DTE_CHOICES, default='BORRADOR')
    monto_neto = models.IntegerField(default=0)
    monto_exento = models.IntegerField(default=0)
    monto_iva = models.IntegerField(default=0)
    monto_total = models.IntegerField(default=0)
    tasa_iva = models.IntegerField(default=19)
    forma_pago = models.CharField(max_length=15, choices=FORMA_PAGO_CHOICES, default='CONTADO')
    observacion = models.CharField(max_length=255, blank=True, null=True)
    xml_url = models.CharField(max_length=500, blank=True, null=True)
    pdf_url = models.CharField(max_length=500, blank=True, null=True)
    track_id_sii = models.CharField(max_length=150, blank=True, null=True)
    estado_sii = models.CharField(max_length=120, blank=True, null=True)

    class Meta:
        db_table = 'documento_tributario'
        managed = False
        unique_together = [('tipo_documento', 'folio')]


class DocumentoTributarioEmisor(models.Model):
    documento_tributario = models.OneToOneField(DocumentoTributario, on_delete=models.CASCADE)
    rut_emisor = models.CharField(max_length=20)
    razon_social = models.CharField(max_length=180)
    giro = models.CharField(max_length=180, blank=True, null=True)
    direccion_casa_matriz = models.CharField(max_length=255, blank=True, null=True)
    comuna = models.CharField(max_length=120, blank=True, null=True)
    ciudad = models.CharField(max_length=120, blank=True, null=True)
    email = models.CharField(max_length=180, blank=True, null=True)

    class Meta:
        db_table = 'documento_tributario_emisor'
        managed = False


class DocumentoTributarioReceptor(models.Model):
    documento_tributario = models.OneToOneField(DocumentoTributario, on_delete=models.CASCADE)
    rut_receptor = models.CharField(max_length=20)
    razon_social = models.CharField(max_length=180)
    giro = models.CharField(max_length=180, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    comuna = models.CharField(max_length=120, blank=True, null=True)
    ciudad = models.CharField(max_length=120, blank=True, null=True)
    email = models.CharField(max_length=180, blank=True, null=True)

    class Meta:
        db_table = 'documento_tributario_receptor'
        managed = False


class DetalleDocumentoTributario(models.Model):
    documento_tributario = models.ForeignKey(DocumentoTributario, on_delete=models.CASCADE)
    producto = models.ForeignKey('inventory.Producto', on_delete=models.SET_NULL, null=True, blank=True)
    codigo_producto = models.CharField(max_length=80, blank=True, null=True)
    nombre_producto = models.CharField(max_length=180)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    cantidad = models.IntegerField()
    precio_unitario = models.IntegerField()
    descuento = models.IntegerField(default=0)
    monto_neto_linea = models.IntegerField(default=0)
    monto_exento_linea = models.IntegerField(default=0)
    monto_iva_linea = models.IntegerField(default=0)
    monto_total_linea = models.IntegerField(default=0)

    class Meta:
        db_table = 'detalle_documento_tributario'
        managed = False


class ReferenciaDocumentoTributario(models.Model):
    TIPO_CHOICES = [
        ('ANULA_DOCUMENTO', 'Anula documento'),
        ('CORRIGE_MONTO', 'Corrige monto'),
        ('CORRIGE_TEXTO', 'Corrige texto'),
        ('REFERENCIA_GUIA', 'Referencia guía'),
        ('REFERENCIA_ORDEN_COMPRA', 'Referencia orden de compra'),
    ]

    documento_tributario = models.ForeignKey(DocumentoTributario, on_delete=models.CASCADE, related_name='referencias')
    documento_referenciado = models.ForeignKey(DocumentoTributario, on_delete=models.SET_NULL, null=True, blank=True, related_name='referenciado_por')
    tipo_documento_referenciado = models.CharField(max_length=120, blank=True, null=True)
    folio_referenciado = models.IntegerField(blank=True, null=True)
    fecha_documento_referenciado = models.DateField(blank=True, null=True)
    tipo_referencia = models.CharField(max_length=30, choices=TIPO_CHOICES)
    razon_referencia = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'referencia_documento_tributario'
        managed = False


class GuiaDespacho(models.Model):
    MOTIVO_CHOICES = [
        ('VENTA', 'Venta'),
        ('TRASLADO_ENTRE_SUCURSALES', 'Traslado entre sucursales'),
        ('CONSIGNACION', 'Consignación'),
        ('DEVOLUCION', 'Devolución'),
        ('OTRO', 'Otro'),
    ]

    documento_tributario = models.OneToOneField(DocumentoTributario, on_delete=models.CASCADE)
    despacho = models.OneToOneField('logistics.Despacho', on_delete=models.CASCADE)
    pedido = models.ForeignKey('orders.Pedido', on_delete=models.CASCADE)
    motivo_traslado = models.CharField(max_length=30, choices=MOTIVO_CHOICES, default='VENTA')
    patente_vehiculo = models.CharField(max_length=20, blank=True, null=True)
    rut_transportista = models.CharField(max_length=20, blank=True, null=True)
    nombre_transportista = models.CharField(max_length=150, blank=True, null=True)
    direccion_origen = models.CharField(max_length=255, blank=True, null=True)
    direccion_destino = models.CharField(max_length=255, blank=True, null=True)
    comuna_origen = models.CharField(max_length=120, blank=True, null=True)
    comuna_destino = models.CharField(max_length=120, blank=True, null=True)

    class Meta:
        db_table = 'guia_despacho'
        managed = False


class EnvioDteSii(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('ENVIADO', 'Enviado'),
        ('ACEPTADO', 'Aceptado'),
        ('RECHAZADO', 'Rechazado'),
        ('ERROR', 'Error'),
        ('REINTENTANDO', 'Reintentando'),
    ]

    documento_tributario = models.ForeignKey(DocumentoTributario, on_delete=models.CASCADE)
    fecha_envio = models.DateTimeField(auto_now_add=True)
    track_id = models.CharField(max_length=150, blank=True, null=True)
    estado_envio = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='PENDIENTE')
    respuesta_xml = models.TextField(blank=True, null=True)
    mensaje_error = models.CharField(max_length=500, blank=True, null=True)
    intentos = models.IntegerField(default=0)

    class Meta:
        db_table = 'envio_dte_sii'
        managed = False


class EstadoDteHistorial(models.Model):
    documento_tributario = models.ForeignKey(DocumentoTributario, on_delete=models.CASCADE)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    estado = models.CharField(max_length=120)
    fecha_estado = models.DateTimeField(auto_now_add=True)
    respuesta_sii = models.CharField(max_length=500, blank=True, null=True)
    observacion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'estado_dte_historial'
        managed = False