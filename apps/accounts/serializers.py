from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Usuario, Institucion, PerfilTrabajador, PerfilCliente, ConvenioInstitucion, DireccionEntrega
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

            usuario = instance.usuario

            for attr, value in usuario_data.items():
                setattr(usuario, attr, value)

            usuario.save()

            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            instance.full_clean()
            instance.save()

            return instance



class ClienteCreateSerializer(serializers.Serializer):
    """
    Serializer Compuesto para registrar un Cliente con la nueva separación de RUT/Pasaporte.
    """
    usuario = UsuarioInternoCreateSerializer()
    rut = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)
    pasaporte = serializers.CharField(max_length=30, required=False, allow_null=True, allow_blank=True)
    tipo_cliente = serializers.ChoiceField(choices=PerfilCliente.TIPO_CHOICES)
    telefono = serializers.CharField(max_length=30, required=False, allow_blank=True)
    institucion_id = serializers.PrimaryKeyRelatedField(
        queryset=Institucion.objects.all(), source='institucion', required=False, allow_null=True
    )

    def validate(self, attrs):
        rut = attrs.get('rut')
        pasaporte = attrs.get('pasaporte')
        tipo_cliente = attrs.get('tipo_cliente')

        # Acoplamos las reglas de negocio del Clean del modelo aquí para el Frontend
        if not rut and not pasaporte:
            raise serializers.ValidationError("Debe proporcionar al menos un documento (RUT o Pasaporte).")

        if rut and pasaporte:
            raise serializers.ValidationError("No se pueden registrar ambos documentos simultáneamente.")

        if tipo_cliente == 'INSTITUCIONAL' and not rut:
            raise serializers.ValidationError(
                {'rut': "Los clientes institucionales requieren obligatoriamente un RUT."})

        return attrs

    def create(self, validated_data):
        datos_usuario = validated_data.pop('usuario')

        with transaction.atomic():
            # 1. Crear el usuario
            password = datos_usuario.pop('password')
            usuario = Usuario(**datos_usuario)
            usuario.set_password(password)
            if validated_data.get('rut'):
                usuario.rut = validated_data.get('rut')
            usuario.save()

            grupo_cliente, _ = Group.objects.get_or_create(name='Clientes')
            usuario.groups.add(grupo_cliente)

            # 2. Crear el perfil de cliente
            perfil = PerfilCliente.objects.create(usuario=usuario, **validated_data)
            return perfil

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
    class Meta:
        model = DireccionEntrega
        fields = [
            'id',
            'direccion',
            'num_direccion',
            'detalle_direccion',
            'comuna',
            'referencia',
            'nombre_receptor',
            'telefono_receptor',
            'es_principal',
        ]
        read_only_fields = ['id']

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