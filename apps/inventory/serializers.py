from rest_framework import serializers
from django.db.models import F, Sum
from .models import (
    Categoria, Marca, Producto, CategoriaProducto,
    Lote, Inventario, MovimientoInventario,
    TrasladoInventario, DetalleTrasladoInventario
)


# ============================================================
# CATEGORÍA
# ============================================================

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'activo']


# ============================================================
# MARCA
# ============================================================

class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = ['id', 'nombre', 'activo']


# ============================================================
# PRODUCTO
# ============================================================

class CategoriaProductoSerializer(serializers.ModelSerializer):
    categoria = CategoriaSerializer(read_only=True)
    categoria_id = serializers.PrimaryKeyRelatedField(
        queryset=Categoria.objects.all(), source='categoria', write_only=True
    )

    class Meta:
        model = CategoriaProducto
        fields = ['id', 'categoria', 'categoria_id']


class ProductoSerializer(serializers.ModelSerializer):
    marca = MarcaSerializer(read_only=True)
    marca_id = serializers.PrimaryKeyRelatedField(
        queryset=Marca.objects.all(), source='marca',
        write_only=True, required=False, allow_null=True
    )
    categorias = CategoriaProductoSerializer(
        source='categoriaproducto_set', many=True, read_only=True
    )

    class Meta:
        model = Producto
        fields = [
            'id', 'sku', 'nombre', 'descripcion', 'valor_unitario',
            'marca', 'marca_id', 'categorias', 'unidad_medida',
            'largo_mm', 'ancho_mm', 'alto_mm', 'peso_mg', 'volumen_ml',
            'requiere_control_vencimiento', 'registro_sanitario', 'activo', 'es_caja'
        ]

    def validate_valor_unitario(self, value):
        if value < 0:
            raise serializers.ValidationError('El valor unitario no puede ser negativo.')
        return value


class ProductoResumenSerializer(serializers.ModelSerializer):
    """Versión liviana para usar como campo anidado en lotes, pedidos, etc."""
    marca_nombre = serializers.CharField(source='marca.nombre', read_only=True)

    class Meta:
        model = Producto
        fields = ['id', 'sku', 'nombre', 'valor_unitario', 'marca_nombre', 'unidad_medida']


class ProductoStockSerializer(serializers.ModelSerializer):
    """Para el endpoint de catálogo en tiempo real — incluye stock agregado."""
    marca_nombre = serializers.CharField(source='marca.nombre', read_only=True)
    categorias = serializers.SerializerMethodField()
    stock_total = serializers.IntegerField(read_only=True)  # anotado en la query

    class Meta:
        model = Producto
        fields = [
            'id', 'sku', 'nombre', 'descripcion', 'valor_unitario',
            'marca_nombre', 'categorias', 'unidad_medida',
            'largo_mm', 'ancho_mm', 'alto_mm', 'peso_mg', 'volumen_ml',
            'registro_sanitario', 'stock_total', 'es_caja'
        ]

    def get_categorias(self, obj):
        return list(
            obj.categoriaproducto_set.values_list('categoria__nombre', flat=True)
        )


# ============================================================
# LOTE
# ============================================================

class LoteSerializer(serializers.ModelSerializer):
    producto = ProductoResumenSerializer(read_only=True)
    producto_id = serializers.PrimaryKeyRelatedField(
        queryset=Producto.objects.all(), source='producto', write_only=True
    )
    dias_para_vencer = serializers.SerializerMethodField()

    class Meta:
        model = Lote
        fields = [
            'id', 'producto', 'producto_id', 'codigo_lote',
            'fecha_elaboracion', 'fecha_vencimiento', 'dias_para_vencer', 'activo'
        ]

    def get_dias_para_vencer(self, obj):
        if not obj.fecha_vencimiento:
            return None
        from django.utils import timezone
        delta = obj.fecha_vencimiento - timezone.now().date()
        return delta.days

    def validate(self, attrs):
        fecha_elaboracion = attrs.get('fecha_elaboracion')
        fecha_vencimiento = attrs.get('fecha_vencimiento')
        if fecha_elaboracion and fecha_vencimiento:
            if fecha_vencimiento <= fecha_elaboracion:
                raise serializers.ValidationError(
                    {'fecha_vencimiento': 'La fecha de vencimiento debe ser posterior a la de elaboración.'}
                )
        return attrs


class LoteResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lote
        fields = ['id', 'codigo_lote', 'fecha_vencimiento']


# ============================================================
# INVENTARIO
# ============================================================

class InventarioSerializer(serializers.ModelSerializer):
    lote = LoteSerializer(read_only=True)
    lote_id = serializers.PrimaryKeyRelatedField(
        queryset=Lote.objects.all(), source='lote', write_only=True
    )
    sucursal_nombre = serializers.CharField(source='sucursal.nombre', read_only=True)
    stock_neto = serializers.SerializerMethodField()
    alerta_stock_critico = serializers.SerializerMethodField()

    class Meta:
        model = Inventario
        fields = [
            'id', 'lote', 'lote_id', 'sucursal', 'sucursal_nombre',
            'cantidad_disponible', 'cantidad_reservada', 'stock_neto',
            'stock_critico', 'alerta_stock_critico', 'fecha_actualizacion'
        ]
        read_only_fields = ['fecha_actualizacion']

    def get_stock_neto(self, obj):
        return obj.cantidad_disponible - obj.cantidad_reservada

    def get_alerta_stock_critico(self, obj):
        return obj.cantidad_disponible <= obj.stock_critico

    def validate(self, attrs):
        # En PATCH, usar valores actuales si no vienen en el payload.
        cantidad_disponible = attrs.get(
            'cantidad_disponible',
            self.instance.cantidad_disponible if self.instance else 0
        )
        cantidad_reservada = attrs.get(
            'cantidad_reservada',
            self.instance.cantidad_reservada if self.instance else 0
        )
        if cantidad_reservada > cantidad_disponible:
            raise serializers.ValidationError(
                {'cantidad_reservada': 'La cantidad reservada no puede superar la disponible.'}
            )
        return attrs


class InventarioResumenSerializer(serializers.ModelSerializer):
    """Para mostrar stock por sucursal en el catálogo."""
    sucursal_nombre = serializers.CharField(source='sucursal.nombre', read_only=True)
    stock_neto = serializers.SerializerMethodField()

    class Meta:
        model = Inventario
        fields = ['sucursal', 'sucursal_nombre', 'cantidad_disponible', 'stock_neto']

    def get_stock_neto(self, obj):
        return obj.cantidad_disponible - obj.cantidad_reservada


# ============================================================
# MOVIMIENTO DE INVENTARIO
# ============================================================

class MovimientoInventarioSerializer(serializers.ModelSerializer):
    inventario_id = serializers.PrimaryKeyRelatedField(
        queryset=Inventario.objects.all(), source='inventario'
    )
    usuario_nombre = serializers.SerializerMethodField()
    tipo_movimiento_display = serializers.CharField(
        source='get_tipo_movimiento_display', read_only=True
    )

    class Meta:
        model = MovimientoInventario
        fields = [
            'id', 'inventario_id', 'usuario', 'usuario_nombre',
            'pedido', 'compra_proveedor', 'traslado_inventario',
            'tipo_movimiento', 'tipo_movimiento_display',
            'cantidad', 'fecha_movimiento', 'motivo', 'observacion'
        ]
        read_only_fields = ['usuario', 'fecha_movimiento']

    def get_usuario_nombre(self, obj):
        return f'{obj.usuario.first_name} {obj.usuario.last_name}'.strip()

    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError('La cantidad debe ser mayor a 0.')
        return value

    def create(self, validated_data):
        # El usuario siempre viene del request, no del payload
        validated_data['usuario'] = self.context['request'].user
        return super().create(validated_data)


# ============================================================
# TRASLADO DE INVENTARIO
# ============================================================

class DetalleTrasladoSerializer(serializers.ModelSerializer):
    lote = LoteResumenSerializer(read_only=True)
    lote_id = serializers.PrimaryKeyRelatedField(
        queryset=Lote.objects.all(), source='lote', write_only=True
    )

    class Meta:
        model = DetalleTrasladoInventario
        fields = ['id', 'lote', 'lote_id', 'cantidad']

    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError('La cantidad debe ser mayor a 0.')
        return value


class TrasladoInventarioSerializer(serializers.ModelSerializer):
    detalles = DetalleTrasladoSerializer(
        source='detalletrasladoinventario_set', many=True, read_only=True
    )
    detalles_write = DetalleTrasladoSerializer(many=True, write_only=True)
    sucursal_origen_nombre = serializers.CharField(
        source='sucursal_origen.nombre', read_only=True
    )
    sucursal_destino_nombre = serializers.CharField(
        source='sucursal_destino.nombre', read_only=True
    )

    class Meta:
        model = TrasladoInventario
        fields = [
            'id', 'sucursal_origen', 'sucursal_origen_nombre',
            'sucursal_destino', 'sucursal_destino_nombre',
            'solicitado_por', 'fecha_solicitud', 'fecha_envio',
            'fecha_recepcion', 'estado', 'observacion',
            'detalles', 'detalles_write'
        ]
        read_only_fields = ['fecha_solicitud', 'solicitado_por']

    def validate(self, attrs):
        if attrs.get('sucursal_origen') == attrs.get('sucursal_destino'):
            raise serializers.ValidationError(
                'La sucursal de origen y destino no pueden ser la misma.'
            )
        if not attrs.get('detalles_write'):
            raise serializers.ValidationError(
                'El traslado debe incluir al menos un producto.'
            )
        # TODO: habilitar cuando se active control de acceso por perfil
        # user = self.context.get('request').user
        # if not hasattr(user, 'perfiltrabajador'):
        # 	raise serializers.ValidationError(
        # 		'Solo trabajadores pueden crear traslados de inventario.'
        # 	)
        return attrs

    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles_write')
        validated_data['solicitado_por'] = self.context['request'].user.perfiltrabajador
        traslado = TrasladoInventario.objects.create(**validated_data)
        for detalle in detalles_data:
            DetalleTrasladoInventario.objects.create(
                traslado_inventario=traslado, **detalle
            )
        return traslado


class ProductoStockSucursalSerializer(serializers.Serializer):
    """Stock agregado por sucursal para un producto."""
    sucursal_id = serializers.IntegerField()
    sucursal_nombre = serializers.CharField()
    stock_neto = serializers.IntegerField()


class ProductoCatalogoSerializer(serializers.ModelSerializer):
    """Serializer para catálogo frontend con info de marca, categorías y stock por sucursal.

    Para evitar N+1, es recomendable prefetch en la vista si se lista en volumen.
    """
    marca = MarcaSerializer(read_only=True)
    categorias = serializers.SerializerMethodField()
    stock_por_sucursal = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id', 'sku', 'nombre', 'descripcion', 'valor_unitario',
            'marca', 'unidad_medida',
            'largo_mm', 'ancho_mm', 'alto_mm', 'peso_mg', 'volumen_ml',
            'requiere_control_vencimiento', 'registro_sanitario', 'activo', 'es_caja',
            'categorias', 'stock_por_sucursal'
        ]

    def get_categorias(self, obj):
        return list(
            obj.categoriaproducto_set.values_list('categoria__nombre', flat=True)
        )

    def get_stock_por_sucursal(self, obj):
        stock_qs = (
            Inventario.objects.filter(lote__producto=obj)
            .values('sucursal_id', sucursal_nombre=F('sucursal__nombre'))
            .annotate(stock_neto=Sum(F('cantidad_disponible') - F('cantidad_reservada')))
            .order_by('sucursal__nombre')
        )
        return ProductoStockSucursalSerializer(stock_qs, many=True).data
