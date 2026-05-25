from rest_framework.permissions import BasePermission
from .models import ApiClient


class EsApiClientActivo(BasePermission):
    """
    Permite acceso solo si el request viene autenticado con una API Key válida
    (es decir, request.user es una instancia de ApiClient).
    """
    message = "Se requiere una API Key válida de institución para acceder a este endpoint."

    def has_permission(self, request, view):
        return (
            request.user is not None
            and isinstance(request.user, ApiClient)
            and request.user.activo
            and request.user.institucion.activo
        )