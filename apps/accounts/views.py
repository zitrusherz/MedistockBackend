from django.db.models import Prefetch
from rest_framework import viewsets, permissions, generics, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import PerfilTrabajador, PerfilCliente, DireccionEntrega
from .permissions import EsEjecutivoOAdministrador
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
    """
    Listado/detalle de clientes para uso administrativo.
    Solo Administrador o Ejecutivo pueden acceder, y cada cliente
    viene acompañado de sus direcciones de entrega activas.
    """
    queryset = PerfilCliente.objects.select_related('usuario', 'institucion').prefetch_related(
        Prefetch(
            'direccionentrega_set',
            queryset=DireccionEntrega.objects.filter(
                activo=True
            ).select_related('comuna', 'comuna__region').order_by('-es_principal', 'id'),
            to_attr='direcciones_activas'
        )
    ).all()
    serializer_class = PerfilClienteSerializer
    permission_classes = [EsEjecutivoOAdministrador]

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
        if not hasattr(self.request.user, 'perfilcliente'):
            return DireccionEntrega.objects.none()

        return DireccionEntrega.objects.filter(
            cliente=self.request.user.perfilcliente,
            activo=True
        ).select_related('comuna')

    def perform_create(self, serializer):
        if not hasattr(self.request.user, 'perfilcliente'):
            raise PermissionDenied(
                'Solo los clientes pueden registrar direcciones de entrega.'
            )

        serializer.save(cliente=self.request.user.perfilcliente)

    @action(detail=False, methods=['get'], url_path='principal')
    def principal(self, request):
        if not hasattr(request.user, 'perfilcliente'):
            raise PermissionDenied(
                'Solo los clientes pueden consultar direcciones de entrega.'
            )

        direccion = self.get_queryset().filter(es_principal=True).first()

        if not direccion:
            return Response(
                {'detail': 'El cliente no tiene una dirección principal registrada.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(direccion)
        return Response(serializer.data)

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"error": "Debes enviar el refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {"detail": "Logout realizado correctamente."},
                status=status.HTTP_205_RESET_CONTENT,
            )

        except Exception:
            return Response(
                {"error": "Token inválido o ya cerrado."},
                status=status.HTTP_400_BAD_REQUEST,
            )