from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

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
)


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
