# apps/integrations/models.py
from django.db import models


class ApiClient(models.Model):
    institucion = models.ForeignKey('accounts.Institucion', on_delete=models.CASCADE)
    nombre_cliente_api = models.CharField(max_length=150)
    api_key_hash = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField(blank=True, null=True)
    limite_requests_diario = models.IntegerField(default=1000)

    class Meta:
        db_table = 'api_client'
        managed = False


class IntegracionExterna(models.Model):
    TIPO_CHOICES = [
        ('PASARELA_PAGO', 'Pasarela de pago'),
        ('COURIER', 'Courier'),
        ('SII', 'SII'),
    ]

    nombre = models.CharField(max_length=150)
    tipo_integracion = models.CharField(max_length=20, choices=TIPO_CHOICES)
    proveedor = models.CharField(max_length=150, blank=True, null=True)
    url_base = models.CharField(max_length=500, blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'integracion_externa'
        managed = False


class RegistroIntegracion(models.Model):
    TIPO_EVENTO_CHOICES = [
        ('REQUEST_ENTRANTE', 'Request entrante'),
        ('REQUEST_SALIENTE', 'Request saliente'),
    ]

    api_client = models.ForeignKey(ApiClient, on_delete=models.SET_NULL, null=True, blank=True)
    integracion_externa = models.ForeignKey(IntegracionExterna, on_delete=models.SET_NULL, null=True, blank=True)
    pedido = models.ForeignKey('orders.Pedido', on_delete=models.SET_NULL, null=True, blank=True)
    documento_tributario = models.ForeignKey('billing.DocumentoTributario', on_delete=models.SET_NULL, null=True, blank=True)
    tipo_evento = models.CharField(max_length=20, choices=TIPO_EVENTO_CHOICES)
    endpoint = models.CharField(max_length=255, blank=True, null=True)
    metodo = models.CharField(max_length=10, blank=True, null=True)
    status_code = models.IntegerField(blank=True, null=True)
    tiempo_respuesta_ms = models.IntegerField(blank=True, null=True)
    exitoso = models.BooleanField(default=False)
    mensaje_error = models.CharField(max_length=500, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'registro_integracion'
        managed = False