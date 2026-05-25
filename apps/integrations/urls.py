from django.urls import path
from .views import PedidoB2BView

urlpatterns = [
    path('pedidos/', PedidoB2BView.as_view(), name='b2b-crear-pedido'),
]