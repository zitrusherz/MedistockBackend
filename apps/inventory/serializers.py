from rest_framework import serializers
from django.db.models import F, Sum
from .models import (
    Categoria, Marca, Producto, CategoriaProducto,
    Lote, Inventario, MovimientoInventario,
    TrasladoInventario, DetalleTrasladoInventario
)
from apps.locations.models import Sucursal
import os
from django.conf import settings
IVA = 0.19


# ============================================================
# HELPER — URL absoluta de imagen
# ============================================================

IMAGE_EXTENSIONS = (
    '.jpg', '.jpeg', '.png', '.webp',
    '.gif', '.bmp', '.svg', '.avif'
)

def get_imagen_url(obj, request):
    """
    Devuelve la URL absoluta de la imagen de un objeto (Producto, Categoria o Marca).

    El campo `imagen` en la BD puede venir con o sin extensión (ej: 'categorias/limpieza').
    Esta función busca en MEDIA_ROOT cualquier archivo cuyo nombre base coincida y
    tenga una extensión de imagen válida. Si lo encuentra, devuelve esa URL real.
    Si no, retorna None.
    """
    if not obj.imagen:
        return None

    # Ruta tal como está registrada (puede traer extensión o no)
    ruta_bd = obj.imagen.name  # p.ej. "categorias/limpieza" o "categorias/limpieza.jpg"

    directorio, nombre_archivo = os.path.split(ruta_bd)
    nombre_base, ext_bd = os.path.splitext(nombre_archivo)

    carpeta_abs = os.path.join(settings.MEDIA_ROOT, directorio)
    ruta_relativa = None

    if os.path.isdir(carpeta_abs):
        # 1) Si la ruta de la BD ya apunta a un archivo existente, úsala tal cual
        if ext_bd and os.path.isfile(os.path.join(settings.MEDIA_ROOT, ruta_bd)):
            ruta_relativa = ruta_bd
        else:
            # 2) Buscar por nombre base + cualquier extensión de imagen
            for archivo in os.listdir(carpeta_abs):
                base, ext = os.path.splitext(archivo)
                if base.lower() == nombre_base.lower() and ext.lower() in IMAGE_EXTENSIONS:
                    ruta_relativa = os.path.join(directorio, archivo).replace('\\', '/')
                    break

    if not ruta_relativa:
        return None

    url = settings.MEDIA_URL.rstrip('/') + '/' + ruta_relativa.lstrip('/')

    if request:
        return request.build_absolute_uri(url)
    return url

# ============================================================
# CATEGORÍA
# ============================================================

class CategoriaSerializer(serializers.ModelSerializer):
    """
    Serializer estándar de Categoria. Acepta 'padre_id' para asignar/cambiar
    la categoría padre, y expone 'subcategorias' (hijas directas) e 'imagen_url'.
    """
    padre_id = serializers.PrimaryKeyRelatedField(
        queryset=Categoria.objects.all(),
        source='padre',
        write_only=True,
        required=False,
        allow_null=True,
    )
    padre_nombre = serializers.CharField(source='padre.nombre', read_only=True)
    subcategorias = serializers.SerializerMethodField()
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Categoria
        fields = [
            'id', 'nombre', 'activo',
            'padre', 'padre_id', 'padre_nombre',
            'subcategorias', 'imagen_url',
        ]
        read_only_fields = ['padre']

    def get_subcategorias(self, obj):
        # Solo un nivel hacia abajo aquí; para el árbol completo usar
        # CategoriaArbolSerializer.
        hijas = obj.subcategorias.all().order_by('nombre')
        return [{'id': h.id, 'nombre': h.nombre, 'activo': h.activo} for h in hijas]

    def get_imagen_url(self, obj):
        return get_imagen_url(obj, self.context.get('request'))

    def validate_padre_id(self, padre):
        """Evita que una categoría sea padre de sí misma."""
        instancia = self.instance
        if instancia and padre and padre.id == instancia.id:
            raise serializers.ValidationError(
                'Una categoría no puede ser su propia categoría padre.'
            )
        return padre

    def validate(self, attrs):
        """Evita ciclos: el padre elegido no puede ser un descendiente de esta categoría."""
        instancia = self.instance
        nuevo_padre = attrs.get('padre')
        if instancia and nuevo_padre:
            actual = nuevo_padre
            visitados = set()
            while actual is not None:
                if actual.id == instancia.id:
                    raise serializers.ValidationError(
                        {'padre_id': 'No se puede asignar como padre a una de sus propias subcategorías (ciclo).'}
                    )
                if actual.id in visitados:
                    break
                visitados.add(actual.id)
                actual = actual.padre
        return attrs


class CategoriaArbolSerializer(serializers.ModelSerializer):
    """Serializer recursivo de solo lectura para representar el árbol completo de categorías."""
    subcategorias = serializers.SerializerMethodField()
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'activo', 'imagen_url', 'subcategorias']

    def get_subcategorias(self, obj):
        hijas = obj.subcategorias.all().order_by('nombre')
        return CategoriaArbolSerializer(hijas, many=True, context=self.context).data

    def get_imagen_url(self, obj):
        return get_imagen_url(obj, self.context.get('request'))


class CategoriaImagenSerializer(serializers.ModelSerializer):
    """Serializer exclusivo para subir/reemplazar la imagen de una categoría."""
    imagen = serializers.ImageField(required=True)
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'imagen', 'imagen_url']

    def get_imagen_url(self, obj):
        return get_imagen_url(obj, self.context.get('request'))


# ============================================================
# MARCA
# ============================================================

class MarcaSerializer(serializers.ModelSerializer):
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Marca
        fields = ['id', 'nombre', 'activo', 'imagen_url']

    def get_imagen_url(self, obj):
        return get_imagen_url(obj, self.context.get('request'))


class MarcaImagenSerializer(serializers.ModelSerializer):
    """Serializer exclusivo para subir/reemplazar la imagen de una marca."""
    imagen = serializers.ImageField(required=True)
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Marca
        fields = ['id', 'nombre', 'imagen', 'imagen_url']

    def get_imagen_url(self, obj):
        return get_imagen_url(obj, self.context.get('request'))


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
    precio_con_iva = serializers.SerializerMethodField()
    imagen_url = serializers.SerializerMethodField()

    stock_total = serializers.IntegerField(read_only=True)

    class Meta:
        model = Producto
        fields = [
            'id', 'sku',
            'nombre', 'descripcion',
            'valor_unitario','precio_con_iva',
            'marca', 'marca_id',
            'categorias',
            'unidad_medida',
            'largo_mm', 'ancho_mm', 'alto_mm', 'peso_mg', 'volumen_ml',
            'requiere_control_vencimiento', 'registro_sanitario',
            'stock_total',
            'activo',
            'es_caja',
            'imagen_url',
        ]

    def get_imagen_url(self, obj):
        return get_imagen_url(obj, self.context.get('request'))

    def get_precio_con_iva(self, obj):
        return round(obj.valor_unitario * (1 + IVA))

    def validate_valor_unitario(self, value):
        if value < 0:
            raise serializers.ValidationError('El valor unitario no puede ser negativo.')
        return value


class ProductoImagenSerializer(serializers.ModelSerializer):
    """Serializer exclusivo para subir/reemplazar la imagen de un producto."""
    imagen = serializers.ImageField(required=True)
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = ['id', 'nombre', 'imagen', 'imagen_url']

    def get_imagen_url(self, obj):
        return get_imagen_url(obj, self.context.get('request'))


class ProductoResumenSerializer(serializers.ModelSerializer):
    """Versión liviana para usar como campo anidado en lotes, pedidos, etc."""
    marca_nombre = serializers.CharField(source='marca.nombre', read_only=True)
    precio_con_iva = serializers.SerializerMethodField()
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id', 'sku', 'nombre', 'valor_unitario', 'precio_con_iva',
            'marca_nombre', 'unidad_medida', 'imagen_url',
        ]

    def get_imagen_url(self, obj):
        return get_imagen_url(obj, self.context.get('request'))

    def get_precio_con_iva(self, obj):
        return round(obj.valor_unitario * (1 + IVA))

class ProductoStockSerializer(serializers.ModelSerializer):
    """Para el endpoint de catálogo en tiempo real — incluye stock agregado."""
    marca_nombre = serializers.CharField(source='marca.nombre', read_only=True)
    categorias = serializers.SerializerMethodField()
    stock_total = serializers.IntegerField(read_only=True)
    precio_con_iva = serializers.SerializerMethodField()
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id', 'sku', 'nombre', 'descripcion', 'valor_unitario', 'precio_con_iva', 'categorias', 'unidad_medida',
            'largo_mm', 'ancho_mm', 'alto_mm', 'peso_mg', 'volumen_ml',
            'registro_sanitario', 'stock_total', 'es_caja',   'imagen_url',
        ]

    def get_precio_con_iva(self, obj):
        return round(obj.valor_unitario * (1 + IVA))
    def get_categorias(self, obj):
        return list(
            obj.categoriaproducto_set.values_list('categoria__nombre', flat=True)
        )


    def get_imagen_url(self, obj):
        return get_imagen_url(obj, self.context.get('request'))

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
    """Catálogo frontend: marca, categorías y stock (total + por sucursal).

    El stock por sucursal se toma de un 'stock_map' precalculado en la vista
    (una sola query para toda la página). Si no hay mapa en el contexto
    (ej. detalle de un producto), hace el cálculo individual como fallback.
    """
    marca = MarcaSerializer(read_only=True)
    categorias = serializers.SerializerMethodField()
    stock_total = serializers.SerializerMethodField()
    stock_por_sucursal = serializers.SerializerMethodField()
    precio_con_iva = serializers.SerializerMethodField()
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id', 'sku', 'nombre', 'descripcion', 'valor_unitario', 'precio_con_iva',
            'marca', 'unidad_medida',
            'largo_mm', 'ancho_mm', 'alto_mm', 'peso_mg', 'volumen_ml',
            'requiere_control_vencimiento', 'registro_sanitario', 'activo', 'es_caja',
            'categorias', 'stock_total', 'stock_por_sucursal',
            'imagen_url',
        ]

    # ── stock ──────────────────────────────────────────────────
    def _stock_sucursales(self, obj):
        """[{sucursal_id, sucursal_nombre, stock_neto}, ...] para este producto.

        Se cachea por id en la instancia del serializer (que DRF reutiliza
        para cada objeto en many=True) para no repetir el cálculo entre
        stock_total y stock_por_sucursal.
        """
        cache = getattr(self, '_stock_cache', None)
        if cache is None:
            cache = {}
            self._stock_cache = cache
        if obj.id in cache:
            return cache[obj.id]

        stock_map = self.context.get('stock_map')
        if stock_map is not None:
            filas = stock_map.get(obj.id, [])
        else:
            # Fallback: 1 query (caso de un solo producto, sin mapa)
            filas = list(
                Inventario.objects.filter(lote__producto=obj)
                .values('sucursal_id', sucursal_nombre=F('sucursal__nombre'))
                .annotate(stock_neto=Sum(F('cantidad_disponible') - F('cantidad_reservada')))
                .order_by('sucursal__nombre')
            )
        cache[obj.id] = filas
        return filas

    def get_stock_por_sucursal(self, obj):
        return ProductoStockSucursalSerializer(self._stock_sucursales(obj), many=True).data

    def get_stock_total(self, obj):
        return sum((fila['stock_neto'] or 0) for fila in self._stock_sucursales(obj))

    # ── resto ──────────────────────────────────────────────────
    def get_precio_con_iva(self, obj):
        return round(obj.valor_unitario * (1 + IVA))

    def get_categorias(self, obj):
        return list(
            obj.categoriaproducto_set.values_list('categoria__nombre', flat=True)
        )

    def get_imagen_url(self, obj):
        return get_imagen_url(obj, self.context.get('request'))


class IngresoProductoSerializer(serializers.Serializer):
    """
    Serializer de escritura para el endpoint de ingreso de producto a inventario.
    Opera en una sola transacción atómica.
    """

    # ── Producto ──────────────────────────────────────────────
    sku = serializers.CharField(max_length=80)
    nombre = serializers.CharField(max_length=180)
    descripcion = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=''
    )
    valor_unitario = serializers.IntegerField(min_value=0)
    marca_id = serializers.PrimaryKeyRelatedField(
        queryset=Marca.objects.all(),
        source='marca',
        required=False,
        allow_null=True,
    )
    unidad_medida = serializers.CharField(
        max_length=50, required=False, allow_blank=True, default=''
    )
    requiere_control_vencimiento = serializers.BooleanField(default=True)
    registro_sanitario = serializers.CharField(
        max_length=120, required=False, allow_blank=True, allow_null=True
    )
    es_caja = serializers.BooleanField(default=False)

    # Dimensiones (opcionales)
    largo_mm = serializers.IntegerField(min_value=0, required=False, default=0)
    ancho_mm = serializers.IntegerField(min_value=0, required=False, default=0)
    alto_mm  = serializers.IntegerField(min_value=0, required=False, default=0)
    peso_mg  = serializers.IntegerField(min_value=0, required=False, default=0)
    volumen_ml = serializers.IntegerField(min_value=0, required=False, default=0)

    # ── Categorías (1 o más IDs) ──────────────────────────────
    categoria_ids = serializers.PrimaryKeyRelatedField(
        queryset=Categoria.objects.all(),
        many=True,
        source='categorias',
    )

    # ── Lote ──────────────────────────────────────────────────
    codigo_lote = serializers.CharField(max_length=100)
    fecha_elaboracion = serializers.DateField(required=False, allow_null=True)
    fecha_vencimiento = serializers.DateField(required=False, allow_null=True)

    # ── Inventario ────────────────────────────────────────────
    sucursal_id = serializers.PrimaryKeyRelatedField(
        queryset=Sucursal.objects.all(),
        source='sucursal',
    )
    cantidad = serializers.IntegerField(min_value=1)
    stock_critico = serializers.IntegerField(min_value=0, default=0)

    # ── Movimiento ────────────────────────────────────────────
    motivo = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default='Ingreso inicial'
    )
    observacion = serializers.CharField(
        max_length=255, required=False, allow_blank=True, allow_null=True
    )

    # ── Validaciones cross-field ──────────────────────────────

    def validate_categoria_ids(self, categorias):
        if not categorias:
            raise serializers.ValidationError(
                'Debe especificar al menos una categoría.'
            )
        return categorias

    def validate(self, attrs):
        fecha_elaboracion = attrs.get('fecha_elaboracion')
        fecha_vencimiento = attrs.get('fecha_vencimiento')
        if fecha_elaboracion and fecha_vencimiento:
            if fecha_vencimiento <= fecha_elaboracion:
                raise serializers.ValidationError(
                    {'fecha_vencimiento': 'Debe ser posterior a la fecha de elaboración.'}
                )
        return attrs

    # ── Lógica de creación atómica ────────────────────────────

    def create(self, validated_data):
        from django.db import transaction
        from .models import MovimientoInventario

        usuario   = self.context['request'].user
        marca     = validated_data.pop('marca', None)
        categorias = validated_data.pop('categorias')
        sucursal  = validated_data.pop('sucursal')
        cantidad  = validated_data.pop('cantidad')
        stock_critico = validated_data.pop('stock_critico', 0)
        codigo_lote   = validated_data.pop('codigo_lote')
        fecha_elab    = validated_data.pop('fecha_elaboracion', None)
        fecha_venc    = validated_data.pop('fecha_vencimiento', None)
        motivo        = validated_data.pop('motivo', 'Ingreso inicial')
        observacion   = validated_data.pop('observacion', None)

        with transaction.atomic():
            # 1. Producto — get_or_create por SKU
            producto, creado = Producto.objects.get_or_create(
                sku=validated_data['sku'],
                defaults={
                    'nombre':      validated_data['nombre'],
                    'descripcion': validated_data.get('descripcion', ''),
                    'valor_unitario': validated_data['valor_unitario'],
                    'marca':       marca,
                    'unidad_medida': validated_data.get('unidad_medida', ''),
                    'requiere_control_vencimiento': validated_data.get('requiere_control_vencimiento', True),
                    'registro_sanitario': validated_data.get('registro_sanitario'),
                    'es_caja':     validated_data.get('es_caja', False),
                    'largo_mm':    validated_data.get('largo_mm', 0),
                    'ancho_mm':    validated_data.get('ancho_mm', 0),
                    'alto_mm':     validated_data.get('alto_mm', 0),
                    'peso_mg':     validated_data.get('peso_mg', 0),
                    'volumen_ml':  validated_data.get('volumen_ml', 0),
                    'activo':      True,
                }
            )

            # 2. Categorías — idempotente
            for categoria in categorias:
                CategoriaProducto.objects.get_or_create(
                    producto=producto,
                    categoria=categoria,
                )

            # 3. Lote — get_or_create por producto + codigo_lote
            lote, _ = Lote.objects.get_or_create(
                producto=producto,
                codigo_lote=codigo_lote,
                defaults={
                    'fecha_elaboracion': fecha_elab,
                    'fecha_vencimiento': fecha_venc,
                    'activo': True,
                }
            )

            # 4. Inventario — get_or_create por lote + sucursal
            inventario, inv_creado = Inventario.objects.get_or_create(
                lote=lote,
                sucursal=sucursal,
                defaults={
                    'cantidad_disponible': 0,
                    'cantidad_reservada':  0,
                    'stock_critico':       stock_critico,
                }
            )

            # Suma la cantidad independientemente de si ya existía
            inventario.cantidad_disponible += cantidad
            if not inv_creado:
                # Si ya existía, respetamos el stock_critico que traía
                # a menos que el payload lo traiga explícitamente mayor
                inventario.stock_critico = max(inventario.stock_critico, stock_critico)
            inventario.save()

            # 5. Movimiento de inventario tipo ENTRADA
            movimiento = MovimientoInventario.objects.create(
                inventario=inventario,
                usuario=usuario,
                tipo_movimiento='ENTRADA',
                cantidad=cantidad,
                motivo=motivo,
                observacion=observacion,
            )

        return {
            'producto':   producto,
            'lote':       lote,
            'inventario': inventario,
            'movimiento': movimiento,
            'producto_creado': creado,
        }