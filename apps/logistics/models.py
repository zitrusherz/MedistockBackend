from django.db import models


class Despacho(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('RETIRADO', 'Retirado'),
        ('EN_TRANSITO', 'En tránsito'),
        ('ENTREGADO', 'Entregado'),
        ('DEVUELTO', 'Devuelto'),
        ('CANCELADO', 'Cancelado'),
    ]
    TIPO_CHOICES = [
        ('NORMAL', 'Normal'),
        ('EXPRESS', 'Express'),
    ]

    pedido = models.OneToOneField('orders.Pedido', on_delete=models.CASCADE)
    courier_nombre = models.CharField(max_length=120, blank=True, null=True)
    numero_seguimiento = models.CharField(max_length=150, blank=True, null=True)
    estado_envio = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='PENDIENTE')
    url_etiqueta = models.CharField(max_length=500, blank=True, null=True)
    tipo_despacho = models.CharField(max_length=10, choices=TIPO_CHOICES, default='NORMAL')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_despacho = models.DateTimeField(blank=True, null=True)
    fecha_entrega_estimada = models.DateTimeField(blank=True, null=True)
    fecha_entrega_real = models.DateTimeField(blank=True, null=True)
    costo_despacho = models.IntegerField(default=0)
    observacion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'despacho'
        managed = False

class ChilexpressApiLog(models.Model):
        METHOD_CHOICES = [
            ("GET", "GET"),
            ("POST", "POST"),
        ]

        method = models.CharField(max_length=10, choices=METHOD_CHOICES)
        endpoint = models.CharField(max_length=255)

        request_payload = models.JSONField(null=True, blank=True)
        response_payload = models.JSONField(null=True, blank=True)

        status_code = models.IntegerField(null=True, blank=True)
        success = models.BooleanField(default=False)

        error_message = models.TextField(null=True, blank=True)

        created_at = models.DateTimeField(auto_now_add=True)

        def __str__(self):
            return f"{self.method} {self.endpoint} - {self.status_code}"


