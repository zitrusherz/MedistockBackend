from rest_framework.permissions import BasePermission, SAFE_METHODS


class EsPedidoPropioOTrabajador(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_staff or user.groups.filter(name="Administrador").exists():
            return True

        if user.groups.filter(name__in=["Ejecutivo", "OperadorLogistico", "Trabajadores"]).exists():
            return True

        if hasattr(user, "perfilcliente"):
            return obj.cliente_id == user.perfilcliente.id

        return False


class ClientePuedeEditarPedidoHastaAprobado(BasePermission):
    estados_editables_cliente = ["PENDIENTE", "APROBADO"]

    def has_object_permission(self, request, view, obj):
        user = request.user

        if request.method in SAFE_METHODS:
            return True

        if user.is_staff or user.groups.filter(name="Administrador").exists():
            return True

        if user.groups.filter(name__in=["Ejecutivo", "OperadorLogistico", "Trabajadores"]).exists():
            return True

        if not hasattr(user, "perfilcliente"):
            return False

        if obj.cliente_id != user.perfilcliente.id:
            return False

        return obj.estado_pedido in self.estados_editables_cliente