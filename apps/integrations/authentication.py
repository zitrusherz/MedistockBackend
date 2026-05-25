import time
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import ApiClient


class ApiKeyAuthentication(BaseAuthentication):
    """
    Autenticación mediante API Key para sistemas ERP externos (B2B).
    La key se envía en el header: X-Api-Key: <clave>

    No retorna un Usuario de Django — retorna el ApiClient directamente
    como el "usuario" de la request. Las views deben tratarlo como tal.
    """
    keyword = 'X-Api-Key'

    def authenticate(self, request):
        raw_key = request.headers.get(self.keyword)
        if not raw_key:
            return None  # No intenta autenticar — deja pasar a otros backends

        api_client = ApiClient.verificar_key(raw_key)
        if not api_client:
            raise AuthenticationFailed('API Key inválida, expirada o desactivada.')

        # Retorna (user, auth) — aquí "user" es el ApiClient
        return (api_client, raw_key)

    def authenticate_header(self, request):
        return self.keyword