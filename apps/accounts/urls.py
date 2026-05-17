from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomTokenObtainPairView,
    RegistroTrabajadorView, RegistroClienteView,
    TrabajadorViewSet, ClienteViewSet,
    MiPerfilView, LogoutView
)
from rest_framework_simplejwt.views import TokenRefreshView

router = DefaultRouter()
router.register(r'trabajadores', TrabajadorViewSet, basename='trabajador')
router.register(r'clientes', ClienteViewSet, basename='cliente')

urlpatterns = [
    # 🔑 Rutas para Autenticación JWT
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("logout/", LogoutView.as_view(), name="logout"),

    # 👤 Ruta para obtener el perfil propio
    path('perfil/me/', MiPerfilView.as_view(), name='mi_perfil'),

    # 🔓 Rutas públicas para registro
    path('registro/trabajador/', RegistroTrabajadorView.as_view(), name='registro_trabajador'),
    path('registro/cliente/', RegistroClienteView.as_view(), name='registro_cliente'),

    # 🔒 Rutas automáticas del router
    path('', include(router.urls)),
]