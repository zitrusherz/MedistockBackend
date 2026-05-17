from rest_framework import viewsets, permissions, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import PerfilTrabajador, PerfilCliente, DireccionEntrega
from .serializers import (CustomTokenObtainPairSerializer, PerfilTrabajadorSerializer, TrabajadorCreateSerializer,
                          PerfilClienteSerializer, MiPerfilClienteSerializer, ClienteCreateSerializer,
                          MiDireccionEntregaSerializer)

class CustomTokenObtainPairView(TokenObtainPairView):
    """
        Vista que recibe usuario/contraseña y devuelve el Token JWT
        con los datos personalizados (grupos, nombre).
    """
    serializer_class = CustomTokenObtainPairSerializer


class RegistroTrabajadorView(generics.CreateAPIView):

    serializer_class = TrabajadorCreateSerializer
    permission_classes = [permissions.AllowAny]

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
            serializer = MiPerfilClienteSerializer(usuario_actual.perfilcliente)
            return Response({
                'rol': 'CLIENTE',
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
            status=status.HTTP_404_NOT_FOUND
        )

    def patch(self, request):
        usuario_actual = request.user

        if not hasattr(usuario_actual, 'perfilcliente'):
            return Response(
                {'detail': 'Solo los clientes pueden editar su perfil desde este endpoint.'},
                status=status.HTTP_403_FORBIDDEN
            )

        perfil = usuario_actual.perfilcliente

        serializer = MiPerfilClienteSerializer(
            perfil,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'rol': 'CLIENTE',
            'datos': serializer.data
        })

class MisDireccionesViewSet(viewsets.ModelViewSet):
    serializer_class = MiDireccionEntregaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DireccionEntrega.objects.filter(
            cliente__usuario=self.request.user,
            activo=True
        )

    def perform_create(self, serializer):
        serializer.save(cliente=self.request.user.perfilcliente)