from django.urls import path
from .views import (
    PedidoB2BView,
    CrearApiClientView,
    ListarApiClientsView,
    GestionarApiClientView,
)
urlpatterns = [
    # B2B — para los ERPs de las clínicas
    path('pedidos/', PedidoB2BView.as_view(), name='b2b-crear-pedido'),

    # Gestión de API Keys — solo trabajadores MEDISTOCK
    path('api-clients/',      ListarApiClientsView.as_view(),  name='api-clients-listar'),
    path('api-clients/crear/', CrearApiClientView.as_view(),   name='api-clients-crear'),
    path('api-clients/<int:pk>/', GestionarApiClientView.as_view(), name='api-clients-gestionar'),
]