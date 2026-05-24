from django.conf import settings
from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'categoria'
        managed = False

    def __str__(self):
        return self.nombre


class Marca(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'marca'
        managed = False

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    sku = models.CharField(max_length=80, unique=True)
    nombre = models.CharField(max_length=180)
    descripcion = models.CharField(max_length=500, blank=True, null=True)
    valor_unitario = models.IntegerField(default=0)
    marca = models.ForeignKey(Marca, on_delete=models.SET_NULL, null=True, blank=True)
    unidad_medida = models.CharField(max_length=50, blank=True, null=True)
    largo_mm = models.PositiveIntegerField(blank=True, null=True, default=0)
    ancho_mm = models.PositiveIntegerField(blank=True, null=True, default=0)
    alto_mm = models.PositiveIntegerField(blank=True, null=True, default=0)
    peso_mg = models.PositiveIntegerField(blank=True, null=True, default=0)
    volumen_ml = models.PositiveIntegerField(blank=True, null=True, default=0)
    requiere_control_vencimiento = models.BooleanField(default=True)
    registro_sanitario = models.CharField(max_length=120, blank=True, null=True)
    activo = models.BooleanField(default=True)
    es_caja = models.BooleanField(default=False)

    class Meta:
        db_table = 'producto'
        managed = False

    def __str__(self):
        return f'{self.sku} - {self.nombre}'


class CategoriaProducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.RESTRICT)

    class Meta:
        db_table = 'categoria_producto'
        managed = False
        unique_together = [('producto', 'categoria')]


class Lote(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.RESTRICT)
    codigo_lote = models.CharField(max_length=100)
    fecha_elaboracion = models.DateField(blank=True, null=True)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'lote'
        managed = False
        unique_together = [('producto', 'codigo_lote')]

    def __str__(self):
        return self.codigo_lote


class Inventario(models.Model):
    lote = models.ForeignKey(Lote, on_delete=models.RESTRICT)
    sucursal = models.ForeignKey('locations.Sucursal', on_delete=models.RESTRICT)
    cantidad_disponible = models.IntegerField(default=0)
    cantidad_reservada = models.IntegerField(default=0)
    stock_critico = models.IntegerField(default=0)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventario'
        managed = False
        unique_together = [('lote', 'sucursal')]


class MovimientoInventario(models.Model):
    TIPO_CHOICES = [
        ('ENTRADA', 'Entrada'),
        ('SALIDA', 'Salida'),
        ('AJUSTE', 'Ajuste'),
        ('MERMA', 'Merma'),
        ('DEVOLUCION', 'Devolución'),
        ('TRASLADO', 'Traslado'),
        ('RESERVA', 'Reserva'),
    ]

    inventario = models.ForeignKey(Inventario, on_delete=models.RESTRICT)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT)
    pedido = models.ForeignKey('orders.Pedido', on_delete=models.SET_NULL, null=True, blank=True)
    compra_proveedor = models.ForeignKey('procurement.CompraProveedor', on_delete=models.SET_NULL, null=True, blank=True)
    traslado_inventario = models.ForeignKey('TrasladoInventario', on_delete=models.SET_NULL, null=True, blank=True)
    tipo_movimiento = models.CharField(max_length=20, choices=TIPO_CHOICES)
    cantidad = models.IntegerField()
    fecha_movimiento = models.DateTimeField(auto_now_add=True)
    motivo = models.CharField(max_length=255, blank=True, null=True)
    observacion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'movimiento_inventario'
        managed = False


class TrasladoInventario(models.Model):
    ESTADO_CHOICES = [
        ('SOLICITADO', 'Solicitado'),
        ('APROBADO', 'Aprobado'),
        ('EN_TRANSITO', 'En tránsito'),
        ('RECIBIDO', 'Recibido'),
        ('CANCELADO', 'Cancelado'),
    ]

    sucursal_origen = models.ForeignKey('locations.Sucursal', on_delete=models.RESTRICT, related_name='traslados_origen')
    sucursal_destino = models.ForeignKey('locations.Sucursal', on_delete=models.RESTRICT, related_name='traslados_destino')
    solicitado_por = models.ForeignKey('accounts.PerfilTrabajador', on_delete=models.RESTRICT)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_envio = models.DateTimeField(blank=True, null=True)
    fecha_recepcion = models.DateTimeField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='SOLICITADO')
    observacion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'traslado_inventario'
        managed = False


class DetalleTrasladoInventario(models.Model):
    traslado_inventario = models.ForeignKey(TrasladoInventario, on_delete=models.CASCADE)
    lote = models.ForeignKey(Lote, on_delete=models.RESTRICT)
    cantidad = models.IntegerField()

    class Meta:
        db_table = 'detalle_traslado_inventario'
        managed = False