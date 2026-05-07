# apps/accounts/serializers.py
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Usuario, Institucion, PerfilTrabajador, PerfilCliente, ConvenioInstitucion, DireccionEntrega


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
    grupos_ids = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), source='groups',
        many=True, write_only=True, required=False
    )

    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'rut', 'grupos', 'grupos_ids', 'is_active', 'is_staff', 'date_joined'
        ]
        read_only_fields = ['date_joined']


class UsuarioCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label='Confirmar contraseña')
    grupos_ids = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), source='groups',
        many=True, required=False
    )

    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'rut', 'grupos_ids', 'password', 'password2'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password2'):
            raise serializers.ValidationError({'password': 'Las contraseñas no coinciden.'})
        return attrs

    def create(self, validated_data):
        grupos = validated_data.pop('groups', [])
        user = Usuario(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        if grupos:
            user.groups.set(grupos)
        return user


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
    usuario_id = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.all(), source='usuario', write_only=True
    )

    class Meta:
        model = PerfilTrabajador
        fields = [
            'id', 'usuario', 'usuario_id', 'rut', 'telefono',
            'direccion', 'comuna', 'sucursal', 'cargo', 'activo'
        ]


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
    usuario_id = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.all(), source='usuario', write_only=True
    )
    institucion = InstitucionResumenSerializer(read_only=True)
    institucion_id = serializers.PrimaryKeyRelatedField(
        queryset=Institucion.objects.all(), source='institucion',
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = PerfilCliente
        fields = [
            'id', 'usuario', 'usuario_id', 'rut_o_pasaporte',
            'tipo_cliente', 'telefono', 'institucion', 'institucion_id', 'activo'
        ]


class PerfilClienteResumenSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = PerfilCliente
        fields = ['id', 'rut_o_pasaporte', 'tipo_cliente', 'nombre_completo']

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