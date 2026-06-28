from django.urls import path

from .views import (
    CategoriaListCreateView,
    CategoriaDetailView,
    CategoriaArbolView,
    CategoriaArbolPublicoView,
    CategoriaImagenView,
    CategoriaPublicListView,
    MarcaListCreateView,
    MarcaDetailView,
    MarcaImagenView,
    MarcaPublicListView,
    ProductoListCreateView,
    ProductoDetailView,
    ProductoPublicDetailView,
    ProductoImagenView,
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
    IngresoProductoView,
)

app_name = 'inventory'

urlpatterns = [
    # ── Categorías ────────────────────────────────────────────
    path('categorias/', CategoriaListCreateView.as_view(), name='categorias-list'),
    path('categorias/arbol/', CategoriaArbolView.as_view(), name='categorias-arbol'),
    path('categorias/<int:pk>/', CategoriaDetailView.as_view(), name='categorias-detail'),
    path('categorias/<int:pk>/imagen/', CategoriaImagenView.as_view(), name='categorias-imagen'),
    path('public/categorias/', CategoriaPublicListView.as_view(), name='categorias-public-list'),
    path('public/categorias/arbol/', CategoriaArbolPublicoView.as_view(), name='categorias-public-arbol'),

    # ── Marcas ────────────────────────────────────────────────
    path('marcas/', MarcaListCreateView.as_view(), name='marcas-list'),
    path('marcas/<int:pk>/', MarcaDetailView.as_view(), name='marcas-detail'),
    path('marcas/<int:pk>/imagen/', MarcaImagenView.as_view(), name='marcas-imagen'),
    path('public/marcas/', MarcaPublicListView.as_view(), name='marcas-public-list'),

    # ── Productos ─────────────────────────────────────────────
    path('productos/', ProductoListCreateView.as_view(), name='productos-list'),
    path('productos/<int:pk>/', ProductoDetailView.as_view(), name='productos-detail'),
    path('productos/<int:pk>/imagen/', ProductoImagenView.as_view(), name='productos-imagen'),
    path('public/productos/<str:sku>/', ProductoPublicDetailView.as_view(), name='productos-public-detail'),

    # ── Lotes ─────────────────────────────────────────────────
    path('lotes/', LoteListCreateView.as_view(), name='lotes-list'),
    path('lotes/<int:pk>/', LoteDetailView.as_view(), name='lotes-detail'),

    # ── Inventario ────────────────────────────────────────────
    path('inventarios/', InventarioListCreateView.as_view(), name='inventarios-list'),
    path('inventarios/<int:pk>/', InventarioDetailView.as_view(), name='inventarios-detail'),

    # ── Movimientos ───────────────────────────────────────────
    path('movimientos/', MovimientoInventarioListCreateView.as_view(), name='movimientos-list'),
    path('movimientos/<int:pk>/', MovimientoInventarioDetailView.as_view(), name='movimientos-detail'),

    # ── Traslados ─────────────────────────────────────────────
    path('traslados/', TrasladoInventarioListCreateView.as_view(), name='traslados-list'),
    path('traslados/<int:pk>/', TrasladoInventarioDetailView.as_view(), name='traslados-detail'),

    # ── Catálogo público ──────────────────────────────────────
    path('catalogo/', CatalogoProductosView.as_view(), name='catalogo-list'),
    path('catalogo-cajas/', CatalogoCajasView.as_view(), name='catalogo-cajas-list'),

    # ── Ingreso de producto ───────────────────────────────────
    path('ingresar-producto/', IngresoProductoView.as_view(), name='ingreso-producto'),
]