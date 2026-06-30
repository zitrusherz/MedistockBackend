from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction, IntegrityError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Usuario, Institucion, PerfilTrabajador, PerfilCliente, ConvenioInstitucion, DireccionEntrega
from .validators import validar_rut
from apps.locations.models import Comuna, Sucursal


# ============================================================
# JWT PERSONALIZADO
# ============================================================

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):



    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email'] = user.email
        token['grupos'] = list(user.groups.values_list('name', flat=True))
        token['full_name'] = f'{user.first_name} {user.last_name}'.strip()
        return token


# ============================================================
# USUARIO
# ============================================================

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']


class UsuarioSerializer(serializers.ModelSerializer):
    grupos = GroupSerializer(source='groups', many=True, read_only=True)


    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'rut', 'grupos', 'is_active', 'is_staff', 'date_joined'
        ]
        read_only_fields = ['date_joined']


class UsuarioInternoCreateSerializer(serializers.ModelSerializer):
    """
    Serializer auxiliar de uso interno para la creación anidada de usuarios.
    Evitamos la creación directa y aislada desde el endpoint general.
    """
    username = serializers.EmailField(
        required=True,
        error_messages={
            'invalid': 'Por favor, ingrese una dirección de correo electrónico válida.'
        }
    )

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password2'):
            raise serializers.ValidationError({'password': 'Las contraseñas no coinciden.'})
        return attrs

class ChangePasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(write_only=True)
    password_nuevo = serializers.CharField(write_only=True, validators=[validate_password])
    password_nuevo2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['password_nuevo'] != attrs['password_nuevo2']:
            raise serializers.ValidationError({'password_nuevo': 'Las contraseñas no coinciden.'})
        return attrs

    def validate_password_actual(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('La contraseña actual es incorrecta.')
        return value


# ============================================================
# INSTITUCIÓN
# ============================================================

class InstitucionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institucion
        fields = [
            'id', 'razon_social', 'rut_empresa', 'giro',
            'direccion_comercial', 'comuna', 'telefono', 'email_contacto',
            'convenio_activo', 'credito_autorizado', 'limite_credito', 'activo'
        ]


class InstitucionResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institucion
        fields = ['id', 'razon_social', 'rut_empresa']


# ============================================================
# PERFIL TRABAJADOR
# ============================================================

class PerfilTrabajadorSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True)


    class Meta:
        model = PerfilTrabajador
        fields = [
            'id', 'usuario', 'rut', 'telefono',
            'direccion', 'comuna', 'sucursal', 'cargo', 'activo'
        ]

class TrabajadorCreateSerializer(serializers.Serializer):
    usuario = UsuarioInternoCreateSerializer()
    rut = serializers.CharField(max_length=13)
    telefono = serializers.CharField(max_length=30, required=False, allow_blank=True)
    direccion = serializers.CharField(max_length=255, required=False, allow_blank=True)
    comuna = serializers.PrimaryKeyRelatedField(queryset=Comuna.objects.all(),
                                                required=False, allow_null=True)
    sucursal = serializers.PrimaryKeyRelatedField(queryset=Sucursal.objects.all(), required=False, allow_null=True)
    cargo = serializers.CharField(max_length=120, required=False, allow_blank=True)



    def validate_rut(self, value):
        # El validador del modelo se ejecuta automáticamente al guardar,
        # pero podemos asegurar unicidad manual aquí si el perfil no es manejado por Django
        if PerfilTrabajador.objects.filter(rut=value).exists():
            raise serializers.ValidationError("Este RUT ya está registrado en un perfil de trabajador.")
        return value

    def create(self, validated_data):
        datos_usuario = validated_data.pop('usuario')

        # Usamos una transacción atómica: si falla la creación del perfil,
        # el usuario no se queda creado a medias en la base de datos.
        with transaction.atomic():
            # 1. Crear el usuario base
            password = datos_usuario.pop('password')
            usuario = Usuario(**datos_usuario)
            usuario.set_password(password)
            # Asignamos el RUT corporativo también al campo rut del usuario si lo requieres
            usuario.rut = validated_data.get('rut')
            usuario.save()

            # Asignar grupo de trabajadores si existe en tu BD
            grupo_trabajador, _ = Group.objects.get_or_create(name='Trabajadores')
            usuario.groups.add(grupo_trabajador)

            # 2. Crear el perfil asociado
            perfil = PerfilTrabajador.objects.create(usuario=usuario, **validated_data)
            return perfil


class PerfilTrabajadorResumenSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = PerfilTrabajador
        fields = ['id', 'rut', 'nombre_completo', 'cargo']

    def get_nombre_completo(self, obj):
        return f'{obj.usuario.first_name} {obj.usuario.last_name}'.strip()


# ============================================================
# PERFIL CLIENTE
# ============================================================

class PerfilClienteSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True)
    institucion = InstitucionResumenSerializer(read_only=True)

    class Meta:
        model = PerfilCliente
        fields = ['id', 'usuario', 'rut', 'pasaporte', 'tipo_cliente', 'telefono', 'institucion', 'activo']

class MiPerfilClienteSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='usuario.email', required=False, allow_blank=False)
    first_name = serializers.CharField(source='usuario.first_name', required=False, allow_blank=False)
    last_name = serializers.CharField(source='usuario.last_name', required=False, allow_blank=False)
    direccion_principal = serializers.SerializerMethodField()

    direccion = serializers.CharField(write_only=True, required=False, allow_blank=False)
    num_direccion = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    detalle_direccion = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    comuna = serializers.PrimaryKeyRelatedField(
        queryset=Comuna.objects.all(), write_only=True, required=False
    )

    class Meta:
        model = PerfilCliente
        fields = [
            'id',
            'rut',
            'pasaporte',
            'telefono',
            'email',
            'first_name',
            'last_name',
            'institucion',
            'direccion_principal',
            'direccion',
            'num_direccion',
            'detalle_direccion',
            'comuna',
        ]

        read_only_fields = ['id', 'institucion']

    def validate(self, attrs):
        instance = self.instance

        usuario_data = attrs.get('usuario', {})

        # Campos que nunca deberían aceptar null o blank si vienen en el request
        campos_no_vacios_perfil = ['rut']
        campos_no_vacios_usuario = ['email', 'first_name', 'last_name']

        for campo in campos_no_vacios_perfil:
            if campo in attrs and attrs[campo] in [None, '']:
                raise serializers.ValidationError({
                    campo: 'Este campo no puede quedar vacío.'
                })

        for campo in campos_no_vacios_usuario:
            if campo in usuario_data and usuario_data[campo] in [None, '']:
                raise serializers.ValidationError({
                    campo: 'Este campo no puede quedar vacío.'
                })

        # Evitar borrar información que ya existía
        if instance:
            for campo, valor_nuevo in attrs.items():
                if campo == 'usuario':
                    continue

                valor_actual = getattr(instance, campo, None)

                if valor_actual not in [None, ''] and valor_nuevo in [None, '']:
                    raise serializers.ValidationError({
                        campo: 'No puedes borrar información que ya estaba registrada.'
                    })

            for campo, valor_nuevo in usuario_data.items():
                valor_actual = getattr(instance.usuario, campo, None)

                if valor_actual not in [None, ''] and valor_nuevo in [None, '']:
                    raise serializers.ValidationError({
                        campo: 'No puedes borrar información que ya estaba registrada.'
                    })

        return attrs

    def update(self, instance, validated_data):
        usuario_data = validated_data.pop('usuario', {})

        direccion_data = {}
        for campo in ['direccion', 'num_direccion', 'detalle_direccion', 'comuna']:
            if campo in validated_data:
                direccion_data[campo] = validated_data.pop(campo)

        usuario = instance.usuario
        if 'email' in usuario_data:
            usuario_data['username'] = usuario_data['email']

        for attr, value in usuario_data.items():
            setattr(usuario, attr, value)
        usuario.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.full_clean()
        instance.save()

        if direccion_data:
            direccion = DireccionEntrega.objects.filter(
                cliente=instance, activo=True, es_principal=True
            ).first()
            if direccion:
                for attr, value in direccion_data.items():
                    setattr(direccion, attr, value)
                direccion.full_clean()
                direccion.save()

        return instance

    def get_direccion_principal(self, obj):
        direccion = (
            DireccionEntrega.objects
            .filter(cliente=obj, activo=True, es_principal=True)
            .select_related('comuna')
            .first()
        )
        if not direccion:
            direccion = (
                DireccionEntrega.objects
                .filter(cliente=obj, activo=True)
                .select_related('comuna')
                .first()
            )
        if not direccion:
            return None
        return MiDireccionEntregaSerializer(direccion).data


class DireccionRegistroClienteSerializer(serializers.Serializer):
    direccion = serializers.CharField(max_length=255, allow_blank=False)
    num_direccion = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True)
    detalle_direccion = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    comuna = serializers.PrimaryKeyRelatedField(queryset=Comuna.objects.all())
    referencia = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    nombre_receptor = serializers.CharField(max_length=150, required=False, allow_blank=True, allow_null=True)
    telefono_receptor = serializers.CharField(max_length=30, required=False, allow_blank=True, allow_null=True)
    es_principal = serializers.BooleanField(default=True)

# ============================================================
# HELPERS REGISTRO CLIENTE
# ============================================================

def limpiar_rut(value):
    """
    Deja el RUT sin puntos ni guion para comparar variantes.
    Ej: "12.345.678-5" -> "123456785".
    """
    if value in [None, ""]:
        return None

    return str(value).replace(".", "").replace("-", "").upper().strip()


def formatear_rut(value):
    """
    Normaliza el RUT al formato usado por la BD/frontend.
    Ej: "123456785" -> "12.345.678-5".
    """
    rut_limpio = limpiar_rut(value)

    if not rut_limpio:
        return None

    cuerpo = rut_limpio[:-1]
    dv = rut_limpio[-1]

    try:
        cuerpo_formateado = f"{int(cuerpo):,}".replace(",", ".")
    except ValueError:
        return value

    return f"{cuerpo_formateado}-{dv}"


def variantes_rut(value):
    """
    Genera variantes para detectar duplicados aunque la BD tenga RUTs
    guardados con o sin puntos/guion.
    """
    rut_limpio = limpiar_rut(value)

    if not rut_limpio:
        return []

    cuerpo = rut_limpio[:-1]
    dv = rut_limpio[-1]

    variantes = {
        str(value).strip(),
        rut_limpio,
        f"{cuerpo}-{dv}",
        formatear_rut(value),
    }

    return [v for v in variantes if v]


def django_error_to_drf(exc):
    """
    Convierte errores de Django full_clean()/validators a una estructura
    consumible por DRF y el frontend.
    """
    if hasattr(exc, "message_dict"):
        return exc.message_dict

    if hasattr(exc, "messages"):
        return {"non_field_errors": exc.messages}

    return {"non_field_errors": [str(exc)]}


class InstitucionRegistroSerializer(serializers.Serializer):
    razon_social = serializers.CharField(max_length=180)
    rut_empresa = serializers.CharField(max_length=20)
    giro = serializers.CharField(max_length=180, required=False, allow_blank=True, allow_null=True)
    direccion_comercial = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    comuna = serializers.PrimaryKeyRelatedField(
        queryset=Comuna.objects.all(),
        required=False,
        allow_null=True
    )
    telefono = serializers.CharField(max_length=30, required=False, allow_blank=True, allow_null=True)
    email_contacto = serializers.EmailField(required=False, allow_blank=True, allow_null=True)

    def validate_rut_empresa(self, value):
        if value in [None, ""]:
            raise serializers.ValidationError("El RUT de la empresa es obligatorio.")

        rut_formateado = formatear_rut(value)

        try:
            validar_rut(rut_formateado)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0])

        return rut_formateado


class ClienteCreateSerializer(serializers.Serializer):
    usuario = UsuarioInternoCreateSerializer()

    rut = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)
    pasaporte = serializers.CharField(max_length=30, required=False, allow_null=True, allow_blank=True)
    tipo_cliente = serializers.ChoiceField(choices=PerfilCliente.TIPO_CHOICES)
    telefono = serializers.CharField(max_length=30, required=False, allow_blank=True)

    institucion_id = serializers.PrimaryKeyRelatedField(
        queryset=Institucion.objects.all(),
        required=False,
        allow_null=True
    )

    datos_institucion = InstitucionRegistroSerializer(required=False, allow_null=True)
    direccion_entrega = DireccionRegistroClienteSerializer(required=True, write_only=True)

    def validate_rut(self, value):
        if value in [None, ""]:
            return None

        rut_formateado = formatear_rut(value)

        try:
            validar_rut(rut_formateado)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0])

        return rut_formateado

    def validate_pasaporte(self, value):
        if value in [None, ""]:
            return None

        return str(value).strip().upper()

    def validate(self, attrs):
        errors = {}

        usuario_data = attrs.get("usuario", {})
        username = usuario_data.get("username")
        email = usuario_data.get("email")

        rut = attrs.get("rut")
        pasaporte = attrs.get("pasaporte")
        tipo_cliente = attrs.get("tipo_cliente")
        institucion_id = attrs.get("institucion_id")
        datos_institucion = attrs.get("datos_institucion")

        # El registro público usa el correo como username.
        if email:
            email = email.strip().lower()
            usuario_data["email"] = email
            usuario_data["username"] = email
            username = email
        elif username:
            username = username.strip().lower()
            usuario_data["username"] = username

        # Duplicados de usuario.
        if username and Usuario.objects.filter(username__iexact=username).exists():
            errors.setdefault("usuario", {})["username"] = [
                "Ya existe un usuario registrado con este correo."
            ]

        if email and Usuario.objects.filter(email__iexact=email).exists():
            errors.setdefault("usuario", {})["email"] = [
                "Ya existe un usuario registrado con este email."
            ]

        # Duplicados de documento.
        if rut:
            rut_values = variantes_rut(rut)

            if PerfilCliente.objects.filter(rut__in=rut_values).exists():
                errors["rut"] = [
                    "Ya existe un cliente registrado con este RUT."
                ]

            if Usuario.objects.filter(rut__in=rut_values).exists():
                errors["rut"] = [
                    "Ya existe una cuenta registrada con este RUT."
                ]

        if pasaporte and PerfilCliente.objects.filter(pasaporte__iexact=pasaporte).exists():
            errors["pasaporte"] = [
                "Ya existe un cliente registrado con este pasaporte."
            ]

        # Reglas documento: rut XOR pasaporte.
        if not rut and not pasaporte:
            errors["non_field_errors"] = [
                "Debe proporcionar al menos un documento, RUT o Pasaporte."
            ]

        if rut and pasaporte:
            errors["non_field_errors"] = [
                "No se pueden registrar RUT y Pasaporte simultáneamente."
            ]

        # Reglas por tipo de cliente.
        if tipo_cliente == "INSTITUCIONAL":
            if not rut:
                errors["rut"] = [
                    "Los clientes institucionales requieren obligatoriamente un RUT."
                ]

            if not institucion_id and not datos_institucion:
                errors["datos_institucion"] = [
                    "Debe enviar los datos de la institución o un institucion_id."
                ]

            if institucion_id and datos_institucion:
                errors["institucion"] = [
                    "Envíe institucion_id o datos_institucion, pero no ambos."
                ]

        if tipo_cliente == "PARTICULAR":
            if institucion_id or datos_institucion:
                errors["institucion"] = [
                    "Un cliente particular no debe tener institución."
                ]

        if errors:
            raise serializers.ValidationError(errors)

        attrs["usuario"] = usuario_data
        return attrs

    def create(self, validated_data):
        datos_usuario = validated_data.pop("usuario")
        datos_direccion = validated_data.pop("direccion_entrega")
        institucion = validated_data.pop("institucion_id", None)
        datos_institucion = validated_data.pop("datos_institucion", None)

        tipo_cliente = validated_data.get("tipo_cliente")

        try:
            with transaction.atomic():
                password = datos_usuario.pop("password")
                datos_usuario.pop("password2", None)

                usuario = Usuario(**datos_usuario)
                usuario.set_password(password)

                if validated_data.get("rut"):
                    usuario.rut = validated_data.get("rut")

                try:
                    usuario.full_clean()
                except DjangoValidationError as exc:
                    raise serializers.ValidationError({
                        "usuario": django_error_to_drf(exc)
                    })

                usuario.save()

                if tipo_cliente == "INSTITUCIONAL":
                    if datos_institucion:
                        rut_empresa = datos_institucion["rut_empresa"]

                        institucion = Institucion.objects.filter(
                            rut_empresa__in=variantes_rut(rut_empresa)
                        ).first()

                        if not institucion:
                            institucion = Institucion(
                                rut_empresa=formatear_rut(rut_empresa),
                                razon_social=datos_institucion["razon_social"],
                                giro=datos_institucion.get("giro"),
                                direccion_comercial=datos_institucion.get("direccion_comercial"),
                                comuna=datos_institucion.get("comuna"),
                                telefono=datos_institucion.get("telefono"),
                                email_contacto=datos_institucion.get("email_contacto"),
                                activo=True,
                            )

                            try:
                                institucion.full_clean()
                            except DjangoValidationError as exc:
                                raise serializers.ValidationError({
                                    "datos_institucion": django_error_to_drf(exc)
                                })

                            institucion.save()

                    grupo_cliente, _ = Group.objects.get_or_create(
                        name="ClienteInstitucional"
                    )
                else:
                    institucion = None
                    grupo_cliente, _ = Group.objects.get_or_create(
                        name="ClienteParticular"
                    )

                usuario.groups.add(grupo_cliente)

                perfil = PerfilCliente(
                    usuario=usuario,
                    institucion=institucion,
                    **validated_data
                )

                try:
                    perfil.full_clean()
                except DjangoValidationError as exc:
                    raise serializers.ValidationError(
                        django_error_to_drf(exc)
                    )

                perfil.save()

                direccion = DireccionEntrega(
                    cliente=perfil,
                    institucion=institucion if tipo_cliente == "INSTITUCIONAL" else None,
                    direccion=datos_direccion["direccion"],
                    num_direccion=datos_direccion.get("num_direccion"),
                    detalle_direccion=datos_direccion.get("detalle_direccion"),
                    comuna=datos_direccion["comuna"],
                    referencia=datos_direccion.get("referencia"),
                    nombre_receptor=datos_direccion.get("nombre_receptor"),
                    telefono_receptor=datos_direccion.get("telefono_receptor"),
                    es_principal=datos_direccion.get("es_principal", True),
                    activo=True,
                )

                try:
                    direccion.full_clean()
                except DjangoValidationError as exc:
                    raise serializers.ValidationError({
                        "direccion_entrega": django_error_to_drf(exc)
                    })

                direccion.save()

                return perfil

        except serializers.ValidationError:
            raise

        except IntegrityError as e:
            error = str(e)

            if "username" in error:
                raise serializers.ValidationError({
                    "usuario": {
                        "username": ["Ya existe un usuario registrado con este correo."]
                    }
                })

            if "email" in error:
                raise serializers.ValidationError({
                    "usuario": {
                        "email": ["Ya existe un usuario registrado con este email."]
                    }
                })

            if "rut" in error:
                raise serializers.ValidationError({
                    "rut": ["Ya existe un registro con este RUT."]
                })

            raise serializers.ValidationError({
                "detail": ["No se pudo completar el registro porque algunos datos ya existen."],
                "debug": [error],
            })

    def to_representation(self, instance):
        return {
            "id": instance.id,
            "usuario": {
                "id": instance.usuario.id,
                "username": instance.usuario.username,
                "email": instance.usuario.email,
                "first_name": instance.usuario.first_name,
                "last_name": instance.usuario.last_name,
            },
            "rut": instance.rut,
            "pasaporte": instance.pasaporte,
            "tipo_cliente": instance.tipo_cliente,
            "telefono": instance.telefono,
            "institucion": instance.institucion.id if instance.institucion else None,
            "activo": instance.activo,
            "mensaje": "Cliente registrado correctamente.",
        }


class PerfilClienteResumenSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = PerfilCliente
        fields = ['id', 'rut', 'pasaporte', 'tipo_cliente', 'nombre_completo']

    def get_nombre_completo(self, obj):
        return f'{obj.usuario.first_name} {obj.usuario.last_name}'.strip()


# ============================================================
# CONVENIO INSTITUCIÓN
# ============================================================

class ConvenioInstitucionSerializer(serializers.ModelSerializer):
    institucion = InstitucionResumenSerializer(read_only=True)
    institucion_id = serializers.PrimaryKeyRelatedField(
        queryset=Institucion.objects.all(), source='institucion', write_only=True
    )

    class Meta:
        model = ConvenioInstitucion
        fields = [
            'id', 'institucion', 'institucion_id', 'fecha_inicio', 'fecha_fin',
            'descuento_porcentaje', 'condiciones_pago', 'activo', 'observacion'
        ]

    def validate_descuento_porcentaje(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError('El descuento debe estar entre 0 y 100.')
        return value


# ============================================================
# DIRECCIÓN DE ENTREGA
# ============================================================

class DireccionEntregaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DireccionEntrega
        fields = [
            'id', 'cliente', 'institucion', 'direccion', 'comuna',
            'ciudad', 'referencia', 'nombre_receptor',
            'telefono_receptor', 'es_principal', 'activo'
        ]

    def validate(self, attrs):
        cliente = attrs.get('cliente')
        institucion = attrs.get('institucion')
        if not cliente and not institucion:
            raise serializers.ValidationError(
                'La dirección debe pertenecer a un cliente o a una institución.'
            )
        if cliente and institucion:
            raise serializers.ValidationError(
                'La dirección no puede pertenecer a un cliente y a una institución simultáneamente.'
            )
        return attrs

class MiDireccionEntregaSerializer(serializers.ModelSerializer):
    comuna_detalle = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()

    class Meta:
        model = DireccionEntrega
        fields = [
            'id',
            'direccion',
            'num_direccion',
            'detalle_direccion',
            'comuna',
            'comuna_detalle',
            'region',
            'referencia',
            'nombre_receptor',
            'telefono_receptor',
            'es_principal',
        ]
        read_only_fields = ['id']

    def get_comuna_detalle(self, obj):
        if not obj.comuna:
            return None
        return {'id': obj.comuna.id, 'nombre': obj.comuna.nombre}

    def get_region(self, obj):
        if not obj.comuna or not obj.comuna.region:
            return None
        return {'id': obj.comuna.region.id, 'nombre': obj.comuna.region.nombre}

    def validate(self, attrs):
        instance = self.instance

        campos_obligatorios = ['direccion', 'comuna']

        for campo in campos_obligatorios:
            if campo in attrs and attrs[campo] in [None, '']:
                raise serializers.ValidationError({
                    campo: 'Este campo no puede quedar vacío.'
                })

        if instance:
            for campo, valor_nuevo in attrs.items():
                valor_actual = getattr(instance, campo, None)

                if valor_actual not in [None, ''] and valor_nuevo in [None, '']:
                    raise serializers.ValidationError({
                        campo: 'No puedes borrar información que ya estaba registrada.'
                    })

        return attrs