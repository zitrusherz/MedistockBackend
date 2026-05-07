from django.db import models


class Region(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    chilexpress_region_id = models.CharField(max_length=5, unique=True)

    class Meta:
        db_table = 'region'
        managed = False

    def __str__(self):
        return self.nombre


class Comuna(models.Model):
    nombre = models.CharField(max_length=100)
    nombre_alt = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.RESTRICT)

    class Meta:
        db_table = 'comuna'
        managed = False
        unique_together = [('nombre', 'region')]

    def __str__(self):
        return self.nombre

class ComunaChilexpress(models.Model):
    comuna = models.ForeignKey(
        'Comuna',
        on_delete=models.CASCADE,
        related_name='comunas_chilexpress',
        db_column='comuna_id'
    )
    county_code = models.CharField(max_length=10)
    county_name = models.CharField(max_length=100)
    coverage_name = models.CharField(max_length=100)
    retorna_respuesta = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = 'comunas_chilexpress'

    def __str__(self):
        return f"{self.coverage_name} ({self.county_code})"

class Sucursal(models.Model):
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=255)
    num_direccion = models.CharField(max_length=7)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    comuna = models.ForeignKey(Comuna, on_delete=models.RESTRICT)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'sucursal'
        managed = False

    def __str__(self):
        return self.nombre