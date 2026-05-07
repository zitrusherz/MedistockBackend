from django.urls import path
from apps.orders.views import CrearPedidoView, DetallePedidoView, AprobarPedidoView

urlpatterns = [
    path("pedidos/", CrearPedidoView.as_view(), name="orders-crear"),
    path("pedidos/<int:pedido_id>/", DetallePedidoView.as_view(), name="orders-detalle"),
    path("pedidos/<int:pedido_id>/aprobar/", AprobarPedidoView.as_view(), name="orders-aprobar"),
]
