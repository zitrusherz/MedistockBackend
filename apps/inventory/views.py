from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import (
	Categoria,
	Marca,
	Producto,
	Lote,
	Inventario,
	MovimientoInventario,
	TrasladoInventario,
)
from .serializers import (
	CategoriaSerializer,
	MarcaSerializer,
	ProductoSerializer,
	LoteSerializer,
	InventarioSerializer,
	MovimientoInventarioSerializer,
	TrasladoInventarioSerializer,
	ProductoCatalogoSerializer,
	IngresoProductoSerializer
)
from apps.accounts.permissions import EsTrabajador

class CategoriaListCreateView(generics.ListCreateAPIView):
	queryset = Categoria.objects.all().order_by('nombre')
	serializer_class = CategoriaSerializer
	permission_classes = [IsAuthenticated]


class CategoriaDetailView(generics.RetrieveUpdateDestroyAPIView):
	queryset = Categoria.objects.all()
	serializer_class = CategoriaSerializer
	permission_classes = [IsAuthenticated]


class MarcaListCreateView(generics.ListCreateAPIView):
	queryset = Marca.objects.all().order_by('nombre')
	serializer_class = MarcaSerializer
	permission_classes = [IsAuthenticated]


class MarcaDetailView(generics.RetrieveUpdateDestroyAPIView):
	queryset = Marca.objects.all()
	serializer_class = MarcaSerializer
	permission_classes = [IsAuthenticated]


class ProductoListCreateView(generics.ListCreateAPIView):
	queryset = Producto.objects.all().order_by('nombre')
	serializer_class = ProductoSerializer
	permission_classes = [IsAuthenticated]


class ProductoDetailView(generics.RetrieveUpdateDestroyAPIView):
	queryset = Producto.objects.all()
	serializer_class = ProductoSerializer
	permission_classes = [IsAuthenticated]


class ProductoImagenView(APIView):
	"""
    PATCH /api/inventory/productos/<pk>/imagen/

    Sube o reemplaza la imagen de un producto existente.
    Acepta multipart/form-data con el campo 'imagen'.
    Solo accesible para usuarios autenticados.

    Ejemplo con fetch:
        const form = new FormData();
        form.append('imagen', archivoFile);
        fetch(`/api/inventory/productos/${id}/imagen/`, {
            method: 'PATCH',
            headers: { 'Authorization': `Bearer ${token}` },
            body: form,
        });
    """
	permission_classes = [IsAuthenticated]
	parser_classes = [MultiPartParser, FormParser]

	def patch(self, request, pk):
		producto = generics.get_object_or_404(Producto, pk=pk)

		serializer = ProductoImagenSerializer(
			producto,
			data=request.data,
			partial=True,
			context={'request': request},
		)
		serializer.is_valid(raise_exception=True)
		serializer.save()

		return Response(serializer.data, status=status.HTTP_200_OK)

	def delete(self, request, pk):
		"""Elimina la imagen del producto dejando el campo vacío."""
		producto = generics.get_object_or_404(Producto, pk=pk)

		if not producto.imagen:
			return Response(
				{'detail': 'Este producto no tiene imagen.'},
				status=status.HTTP_404_NOT_FOUND,
			)

		producto.imagen.delete(save=True)  # borra el archivo físico y guarda el modelo
		return Response(
			{'detail': 'Imagen eliminada correctamente.'},
			status=status.HTTP_200_OK,
		)


class LoteListCreateView(generics.ListCreateAPIView):
	queryset = Lote.objects.select_related('producto').all().order_by('fecha_vencimiento')
	serializer_class = LoteSerializer
	permission_classes = [IsAuthenticated]


class LoteDetailView(generics.RetrieveUpdateDestroyAPIView):
	queryset = Lote.objects.select_related('producto').all()
	serializer_class = LoteSerializer
	permission_classes = [IsAuthenticated]


class InventarioListCreateView(generics.ListCreateAPIView):
	queryset = Inventario.objects.select_related('lote', 'sucursal', 'lote__producto').all()
	serializer_class = InventarioSerializer
	permission_classes = [IsAuthenticated]


class InventarioDetailView(generics.RetrieveUpdateDestroyAPIView):
	queryset = Inventario.objects.select_related('lote', 'sucursal', 'lote__producto').all()
	serializer_class = InventarioSerializer
	permission_classes = [IsAuthenticated]


class MovimientoInventarioListCreateView(generics.ListCreateAPIView):
	queryset = MovimientoInventario.objects.select_related(
		'inventario',
		'usuario',
		'inventario__lote',
		'inventario__lote__producto',
	).all().order_by('-fecha_movimiento')
	serializer_class = MovimientoInventarioSerializer
	permission_classes = [IsAuthenticated]


class MovimientoInventarioDetailView(generics.RetrieveAPIView):
	queryset = MovimientoInventario.objects.select_related(
		'inventario',
		'usuario',
		'inventario__lote',
		'inventario__lote__producto',
	).all()
	serializer_class = MovimientoInventarioSerializer
	permission_classes = [IsAuthenticated]


class TrasladoInventarioListCreateView(generics.ListCreateAPIView):
	queryset = TrasladoInventario.objects.select_related(
		'sucursal_origen',
		'sucursal_destino',
		'solicitado_por',
	).all().order_by('-fecha_solicitud')
	serializer_class = TrasladoInventarioSerializer
	permission_classes = [IsAuthenticated]


class TrasladoInventarioDetailView(generics.RetrieveUpdateDestroyAPIView):
	queryset = TrasladoInventario.objects.select_related(
		'sucursal_origen',
		'sucursal_destino',
		'solicitado_por',
	).all()
	serializer_class = TrasladoInventarioSerializer
	permission_classes = [IsAuthenticated]


class CatalogoProductosView(generics.ListAPIView):
	"""Catálogo público con info de producto, marca, categorías y stock por sucursal."""
	serializer_class = ProductoCatalogoSerializer
	permission_classes = [AllowAny]

	def get_queryset(self):
		queryset = (
			Producto.objects.filter(activo=True, es_caja=False)
			.select_related('marca')
			.prefetch_related('categoriaproducto_set__categoria')
			.order_by('nombre')
		)

		marca_id = self.request.query_params.get('marca_id')
		categoria_id = self.request.query_params.get('categoria_id')
		sucursal_id = self.request.query_params.get('sucursal_id')

		if marca_id:
			queryset = queryset.filter(marca_id=marca_id)
		if categoria_id:
			queryset = queryset.filter(categoriaproducto__categoria_id=categoria_id)
		if sucursal_id:
			queryset = queryset.filter(
				lote__inventario__sucursal_id=sucursal_id
			)

		return queryset.distinct()


class CatalogoCajasView(generics.ListAPIView):
	"""Catálogo público exclusivo para productos caja (no se muestran en catálogo general)."""
	serializer_class = ProductoCatalogoSerializer
	permission_classes = [AllowAny]

	def get_queryset(self):
		queryset = (
			Producto.objects.filter(activo=True, es_caja=True)
			.select_related('marca')
			.prefetch_related('categoriaproducto_set__categoria')
			.order_by('nombre')
		)

		marca_id = self.request.query_params.get('marca_id')
		categoria_id = self.request.query_params.get('categoria_id')
		sucursal_id = self.request.query_params.get('sucursal_id')

		if marca_id:
			queryset = queryset.filter(marca_id=marca_id)
		if categoria_id:
			queryset = queryset.filter(categoriaproducto__categoria_id=categoria_id)
		if sucursal_id:
			queryset = queryset.filter(
				lote__inventario__sucursal_id=sucursal_id
			)

		return queryset.distinct()


class CategoriaPublicListView(generics.ListAPIView):
	"""Listado público (solo lectura) de categorías."""
	queryset = Categoria.objects.filter(activo=True).order_by('nombre')
	serializer_class = CategoriaSerializer
	permission_classes = [AllowAny]


class MarcaPublicListView(generics.ListAPIView):
	"""Listado público (solo lectura) de marcas."""
	queryset = Marca.objects.filter(activo=True).order_by('nombre')
	serializer_class = MarcaSerializer
	permission_classes = [AllowAny]


class ProductoPublicDetailView(generics.RetrieveAPIView):
	"""Detalle público (solo lectura) de producto."""
	queryset = Producto.objects.filter(activo=True).select_related('marca')
	serializer_class = ProductoSerializer
	permission_classes = [AllowAny]


class IngresoProductoView(APIView):
    """
    POST /api/inventory/ingresar-producto/

    Crea (o recupera) un producto con su lote, lo asigna a una sucursal
    con el stock indicado y registra el movimiento de ENTRADA.
    Solo accesible para trabajadores activos.
    """
    permission_classes = [EsTrabajador]

    def post(self, request):
        serializer = IngresoProductoSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        producto = result['producto']
        inventario = result['inventario']

        return Response(
            {
                'mensaje': (
                    'Producto creado e ingresado al inventario.'
                    if result['producto_creado']
                    else 'Producto existente. Stock actualizado.'
                ),
                'producto_id':    producto.id,
                'sku':            producto.sku,
                'lote_id':        result['lote'].id,
                'codigo_lote':    result['lote'].codigo_lote,
                'inventario_id':  inventario.id,
                'sucursal_id':    inventario.sucursal_id,
                'stock_actual':   inventario.cantidad_disponible,
                'movimiento_id':  result['movimiento'].id,
            },
            status=status.HTTP_201_CREATED,
        )