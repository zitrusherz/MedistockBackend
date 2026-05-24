from django.urls import path
from apps.orders.views import (
    CrearPedidoView,
    DetallePedidoView,
    AprobarPedidoView,
    MisPedidosView,
    ListarPedidosView,
)

urlpatterns = [
    path("pedidos/", CrearPedidoView.as_view(), name="orders-crear"),
    path("pedidos/mis-pedidos/", MisPedidosView.as_view(), name="orders-mis-pedidos"),
    path("pedidos/todos/", ListarPedidosView.as_view(), name="orders-listar-todos"),
    path("pedidos/<int:pedido_id>/", DetallePedidoView.as_view(), name="orders-detalle"),
    path("pedidos/<int:pedido_id>/aprobar/", AprobarPedidoView.as_view(), name="orders-aprobar"),
]