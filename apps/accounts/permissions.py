from rest_framework.permissions import BasePermission


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