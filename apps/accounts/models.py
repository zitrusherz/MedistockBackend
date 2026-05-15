from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from .validators import validar_rut




class Usuario(AbstractUser):
    rut = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        validators=[validar_rut]
    )


    class Meta:
        db_table = 'usuario'

    def __str__(self):
        return self.username


class Institucion(models.Model):
    razon_social = models.CharField(max_length=180)
    rut_empresa = models.CharField(max_length=20, unique=True, validators=[validar_rut])
    giro = models.CharField(max_length=180, blank=True, null=True)
    direccion_comercial = models.CharField(max_length=255, blank=True, null=True)
    comuna = models.ForeignKey('locations.Comuna', on_delete=models.SET_NULL, null=True, blank=True)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    email_contacto = models.CharField(max_length=180, blank=True, null=True)
    convenio_activo = models.BooleanField(default=False)
    credito_autorizado = models.BooleanField(default=False)
    limite_credito = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'institucion'
        managed = False

    def __str__(self):
        return self.razon_social


class PerfilTrabajador(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rut = models.CharField(max_length=20, unique=True, validators=[validar_rut])
    telefono = models.CharField(max_length=30, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    comuna = models.ForeignKey('locations.Comuna', on_delete=models.SET_NULL, null=True, blank=True)
    sucursal = models.ForeignKey('locations.Sucursal', on_delete=models.SET_NULL, null=True, blank=True)
    cargo = models.CharField(max_length=120, blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'perfil_trabajador'
        managed = False

    def __str__(self):
        return self.rut


class PerfilCliente(models.Model):
    TIPO_CHOICES = [
        ('PARTICULAR', 'Particular'),
        ('INSTITUCIONAL', 'Institucional'),
    ]

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rut = models.CharField(max_length=13, unique=True, blank=True, null=True, validators=[validar_rut])
    pasaporte = models.CharField(max_length=30, unique=True, blank=True, null=True)
    tipo_cliente = models.CharField(max_length=20, choices=TIPO_CHOICES)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    institucion = models.ForeignKey(Institucion, on_delete=models.SET_NULL, null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'perfil_cliente'
        managed = False

    def __str__(self):
        return self.rut if self.rut else f"Pasaporte: {self.pasaporte}"

    def clean(self):
        """
                Validación a nivel de modelo (cross-field validation).
                Asegura la integridad: un cliente debe tener RUT o Pasaporte, pero no ninguno.
                """
        super().clean()

        # Regla 1: Obligatoriedad de al menos un documento
        if not self.rut and not self.pasaporte:
            raise ValidationError(
                "Debe proporcionar al menos un documento de identificación (RUT o Pasaporte)."
            )

        # Regla 2: Evitar redundancia (Opcional, según tus reglas de negocio)
        if self.rut and self.pasaporte:
            raise ValidationError(
                "No se pueden registrar ambos documentos (RUT y Pasaporte) a la vez. Elija uno."
            )

        # Regla 3: Si es institucional, típicamente se exige RUT en Chile
        if self.tipo_cliente == 'INSTITUCIONAL' and not self.rut:
            raise ValidationError(
                {"rut": "Los clientes de tipo Institucional requieren obligatoriamente un RUT."}
            )


class ConvenioInstitucion(models.Model):
    institucion = models.ForeignKey(Institucion, on_delete=models.CASCADE)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(blank=True, null=True)
    descuento_porcentaje = models.IntegerField(default=0)
    condiciones_pago = models.CharField(max_length=500, blank=True, null=True)
    activo = models.BooleanField(default=True)
    observacion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'convenio_institucion'
        managed = False


class DireccionEntrega(models.Model):
    cliente = models.ForeignKey(PerfilCliente, on_delete=models.CASCADE, null=True, blank=True)
    institucion = models.ForeignKey(Institucion, on_delete=models.CASCADE, null=True, blank=True)
    direccion = models.CharField(max_length=255)
    num_direccion = models.CharField(max_length=10, blank=True, null=True)
    detalle_direccion = models.CharField(max_length=255, blank=True, null=True)
    comuna = models.ForeignKey('locations.Comuna', on_delete=models.RESTRICT)
    referencia = models.CharField(max_length=255, blank=True, null=True)
    nombre_receptor = models.CharField(max_length=150, blank=True, null=True)
    telefono_receptor = models.CharField(max_length=30, blank=True, null=True)
    es_principal = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'direccion_entrega'
        managed = False