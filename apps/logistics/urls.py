from django.urls import path
from apps.logistics.views import CotizarEnvioView, CrearEnvioView, TrackingView

urlpatterns = [
    path("cotizar/", CotizarEnvioView.as_view(), name="logistics-cotizar"),
    path("envios/", CrearEnvioView.as_view(), name="logistics-crear-envio"),
    path("envios/<int:pedido_id>/tracking/", TrackingView.as_view(), name="logistics-tracking"),
]

