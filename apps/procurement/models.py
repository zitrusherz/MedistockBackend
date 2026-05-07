# apps/procurement/models.py
from django.conf import settings
from django.db import models


class Proveedor(models.Model):
    nombre_empresa = models.CharField(max_length=180)
    rut = models.CharField(max_length=20, unique=True)
    contacto = models.CharField(max_length=150, blank=True, null=True)
    email = models.CharField(max_length=180, blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'proveedor'
        managed = False

    def __str__(self):
        return self.nombre_empresa


class CompraProveedor(models.Model):
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('EMITIDA', 'Emitida'),
        ('RECIBIDA_PARCIAL', 'Recibida parcial'),
        ('RECIBIDA_TOTAL', 'Recibida total'),
        ('CANCELADA', 'Cancelada'),
    ]

    proveedor = models.ForeignKey(Proveedor, on_delete=models.RESTRICT)
    sucursal = models.ForeignKey('locations.Sucursal', on_delete=models.RESTRICT)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT)
    fecha_compra = models.DateTimeField(auto_now_add=True)
    fecha_recepcion = models.DateTimeField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='BORRADOR')
    subtotal = models.IntegerField(default=0)
    monto_iva = models.IntegerField(default=0)
    total = models.IntegerField(default=0)
    observacion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'compra_proveedor'
        managed = False


class DetalleCompraProveedor(models.Model):
    compra_proveedor = models.ForeignKey(CompraProveedor, on_delete=models.CASCADE)
    producto = models.ForeignKey('inventory.Producto', on_delete=models.RESTRICT)
    lote = models.ForeignKey('inventory.Lote', on_delete=models.RESTRICT)
    cantidad = models.IntegerField()
    costo_unitario = models.IntegerField(default=0)
    subtotal = models.IntegerField(default=0)

    class Meta:
        db_table = 'detalle_compra_proveedor'
        managed = False