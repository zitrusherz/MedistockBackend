from django.urls import path

from .views import (
    WebpayIniciarPagoView,
    WebpayCommitView,
    WebpayEstadoView,
    MisTransaccionesPagoView,
)

app_name = "payments"

urlpatterns = [
    path("webpay/iniciar/", WebpayIniciarPagoView.as_view(), name="webpay-iniciar"),
    path("webpay/commit/", WebpayCommitView.as_view(), name="webpay-commit"),
    path("webpay/estado/<str:token_ws>/", WebpayEstadoView.as_view(), name="webpay-estado"),
    path("mis-pagos/", MisTransaccionesPagoView.as_view(), name="mis-pagos"),
]