from django.urls import path

from .views import (
	CategoriaListCreateView,
	CategoriaDetailView,
	MarcaListCreateView,
	MarcaDetailView,
	ProductoListCreateView,
	ProductoDetailView,
	LoteListCreateView,
	LoteDetailView,
	InventarioListCreateView,
	InventarioDetailView,
	MovimientoInventarioListCreateView,
	MovimientoInventarioDetailView,
	TrasladoInventarioListCreateView,
	TrasladoInventarioDetailView,
)

app_name = 'inventory'

urlpatterns = [
	path('categorias/', CategoriaListCreateView.as_view(), name='categorias-list'),
	path('categorias/<int:pk>/', CategoriaDetailView.as_view(), name='categorias-detail'),
	path('marcas/', MarcaListCreateView.as_view(), name='marcas-list'),
	path('marcas/<int:pk>/', MarcaDetailView.as_view(), name='marcas-detail'),
	path('productos/', ProductoListCreateView.as_view(), name='productos-list'),
	path('productos/<int:pk>/', ProductoDetailView.as_view(), name='productos-detail'),
	path('lotes/', LoteListCreateView.as_view(), name='lotes-list'),
	path('lotes/<int:pk>/', LoteDetailView.as_view(), name='lotes-detail'),
	path('inventarios/', InventarioListCreateView.as_view(), name='inventarios-list'),
	path('inventarios/<int:pk>/', InventarioDetailView.as_view(), name='inventarios-detail'),
	path('movimientos/', MovimientoInventarioListCreateView.as_view(), name='movimientos-list'),
	path('movimientos/<int:pk>/', MovimientoInventarioDetailView.as_view(), name='movimientos-detail'),
	path('traslados/', TrasladoInventarioListCreateView.as_view(), name='traslados-list'),
	path('traslados/<int:pk>/', TrasladoInventarioDetailView.as_view(), name='traslados-detail'),
]

