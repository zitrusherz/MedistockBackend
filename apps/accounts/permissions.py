from rest_framework.permissions import BasePermission, SAFE_METHODS


def tiene_rol(user, *roles):
    return user.groups.filter(name__in=roles).exists()


class EsAdministrador(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and tiene_rol(request.user, 'Administrador')


class EsEjecutivo(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and tiene_rol(request.user, 'Ejecutivo')


class EsOperadorLogistico(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and tiene_rol(request.user, 'OperadorLogistico')


class EsAnalista(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and tiene_rol(request.user, 'Analista')


class EsCliente(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and tiene_rol(
            request.user, 'ClienteInstitucional', 'ClienteParticular'
        )


class EsEjecutivoOAdministrador(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and tiene_rol(
            request.user, 'Ejecutivo', 'Administrador'
        )

class EsDuennoDelPedidoYEditableHastaAprobado(BasePermission):
    estados_editables =  ['PENDIENTE', 'APROBADO']

    def has_object_permission(self, request, view, obj):
        usuario = request.user

        if not usuario or not usuario.is_authenticated:
            return False

        # Admin puede todo
        if usuario.is_staff or usuario.groups.filter(name='Administrador').exists():
            return True

        # El pedido debe pertenecer al cliente autenticado
        if obj.cliente.usuario != usuario:
            return False

        # Puede ver sus pedidos siempre
        if request.method in SAFE_METHODS:
            return True

        # Puede editar solo hasta APROBADO incluido
        return obj.estado in self.estados_editables


class EsTrabajador(BasePermission):
    """
    Permite acceso solo a usuarios autenticados que tengan un PerfilTrabajador asociado.
    """
    message = "Solo los trabajadores de MEDISTOCK pueden realizar esta acción."

    def has_permission(self, request, view):
        return (
                request.user
                and request.user.is_authenticated
                and hasattr(request.user, 'perfiltrabajador')
                and request.user.perfiltrabajador.activo
            )