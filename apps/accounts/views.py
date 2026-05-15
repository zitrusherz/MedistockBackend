from rest_framework import viewsets, permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import PerfilTrabajador, PerfilCliente
from .serializers import (CustomTokenObtainPairSerializer, PerfilTrabajadorSerializer, TrabajadorCreateSerializer,
                          PerfilClienteSerializer, ClienteCreateSerializer)

class CustomTokenObtainPairView(TokenObtainPairView):
    """
        Vista que recibe usuario/contraseña y devuelve el Token JWT
        con los datos personalizados (grupos, nombre).
    """
    serializer_class = CustomTokenObtainPairSerializer


class RegistroTrabajadorView(generics.CreateAPIView):

    serializer_class = TrabajadorCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

class RegistroClienteView(generics.CreateAPIView):
    serializer_class = ClienteCreateSerializer
    permission_classes = [permissions.AllowAny]

class TrabajadorViewSet(viewsets.ModelViewSet):
    queryset = PerfilTrabajador.objects.select_related('usuario').all()
    serializer_class = PerfilTrabajadorSerializer
    permission_classes = [permissions.IsAuthenticated]


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = PerfilCliente.objects.select_related('usuario', 'institucion').all()
    serializer_class = PerfilClienteSerializer
    permission_classes = [permissions.IsAuthenticated]

class MiPerfilView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):

        usuario_actual = request.user

        if hasattr(usuario_actual, 'perfilcliente'):
            serializer = PerfilClienteSerializer(usuario_actual.perfilcliente)
            return Response({'Rol': 'CLIENTE',
                             'datos': serializer.data
            })
        elif hasattr(usuario_actual, 'perfiltrabajador'):
            serializer = PerfilTrabajadorSerializer(usuario_actual.perfiltrabajador)
            return Response({
                'rol': 'TRABAJADOR',
                'datos': serializer.data
            })
        return Response(
            {'detail': 'El usuario no tiene un perfil asociado.'},
            status=404,)