from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import PerfilCliente


@receiver(post_save, sender=PerfilCliente)
def asignar_grupo_cliente(sender, instance, created, **kwargs):
    usuario = instance.usuario

    if instance.tipo_cliente == "PARTICULAR":
        grupo_destino = Group.objects.get(name="ClienteParticular")
        grupos_cliente = ["ClienteInstitucional"]

    elif instance.tipo_cliente == "INSTITUCIONAL":
        grupo_destino = Group.objects.get(name="ClienteInstitucional")
        grupos_cliente = ["ClienteParticular"]

    else:
        return

    # Quita solo el grupo contrario
    usuario.groups.remove(
        *Group.objects.filter(name__in=grupos_cliente)
    )

    # Agrega el grupo correspondiente si no lo tiene
    if not usuario.groups.filter(id=grupo_destino.id).exists():
        usuario.groups.add(grupo_destino)