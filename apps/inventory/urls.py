from django.urls import path

from .views import (
	CategoriaListCreateView,
	CategoriaDetailView,
	CategoriaPublicListView,
	MarcaListCreateView,
	MarcaDetailView,
	MarcaPublicListView,
	ProductoListCreateView,
	ProductoDetailView,
	ProductoPublicDetailView,
	LoteListCreateView,
	LoteDetailView,
	InventarioListCreateView,
	InventarioDetailView,
	MovimientoInventarioListCreateView,
	MovimientoInventarioDetailView,
	TrasladoInventarioListCreateView,
	TrasladoInventarioDetailView,
	CatalogoProductosView,
	CatalogoCajasView,
	IngresoProductoView
)

app_name = 'inventory'

urlpatterns = [
	path('categorias/', CategoriaListCreateView.as_view(), name='categorias-list'),
	path('categorias/<int:pk>/', CategoriaDetailView.as_view(), name='categorias-detail'),
	path('public/categorias/', CategoriaPublicListView.as_view(), name='categorias-public-list'),
	path('marcas/', MarcaListCreateView.as_view(), name='marcas-list'),
	path('marcas/<int:pk>/', MarcaDetailView.as_view(), name='marcas-detail'),
	path('public/marcas/', MarcaPublicListView.as_view(), name='marcas-public-list'),
	path('productos/', ProductoListCreateView.as_view(), name='productos-list'),
	path('productos/<int:pk>/', ProductoDetailView.as_view(), name='productos-detail'),
	path('public/productos/<int:pk>/', ProductoPublicDetailView.as_view(), name='productos-public-detail'),
	path('lotes/', LoteListCreateView.as_view(), name='lotes-list'),
	path('lotes/<int:pk>/', LoteDetailView.as_view(), name='lotes-detail'),
	path('inventarios/', InventarioListCreateView.as_view(), name='inventarios-list'),
	path('inventarios/<int:pk>/', InventarioDetailView.as_view(), name='inventarios-detail'),
	path('movimientos/', MovimientoInventarioListCreateView.as_view(), name='movimientos-list'),
	path('movimientos/<int:pk>/', MovimientoInventarioDetailView.as_view(), name='movimientos-detail'),
	path('traslados/', TrasladoInventarioListCreateView.as_view(), name='traslados-list'),
	path('traslados/<int:pk>/', TrasladoInventarioDetailView.as_view(), name='traslados-detail'),
	path('catalogo/', CatalogoProductosView.as_view(), name='catalogo-list'),
	path('catalogo-cajas/', CatalogoCajasView.as_view(), name='catalogo-cajas-list'),
	path('ingresar-producto/', IngresoProductoView.as_view(), name='ingreso-producto'),
]
