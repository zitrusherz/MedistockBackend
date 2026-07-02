from collections import Counter

from rest_framework import serializers
from apps.locations.models import ComunaChilexpress, Sucursal
from apps.orders.models import Pedido, DetallePedido
from apps.inventory.models import Producto
from apps.logistics.models import Despacho
from apps.logistics.utils import dimensiones_a_chilexpress, calcular_caja_optima


# =============================================================================
# Helpers internos
# =============================================================================

def _productos_a_lista_empaque(detalles_pedido) -> list[dict]:
    """
    Convierte un QuerySet de DetallePedido en la lista de dicts que espera calcular_caja_optima.
    Expande cada detalle según su cantidad (un ítem por unidad).
    """
    items = []
    for detalle in detalles_pedido:
        prod = detalle.producto
        for i in range(detalle.cantidad):
            items.append({
                "id": f"{prod.sku}-{i}",
                "largo_mm": prod.largo_mm or 1,
                "ancho_mm": prod.ancho_mm or 1,
                "alto_mm":  prod.alto_mm  or 1,
                "peso_mg":  prod.peso_mg  or 1,
            })
    return items


def _productos_ids_a_lista_empaque(productos_por_id: dict[int, Producto], productos_ids: list[int]) -> list[dict]:
    """
    Convierte una lista de IDs de productos en la lista de dicts que espera
    calcular_caja_optima. Si un ID se repite, se interpreta como más de una unidad.
    """
    items = []
    ocurrencias = Counter()

    for producto_id in productos_ids:
        prod = productos_por_id[producto_id]
        ocurrencias[producto_id] += 1
        items.append({
            "id": f"{prod.sku}-{ocurrencias[producto_id]}",
            "largo_mm": prod.largo_mm or 1,
            "ancho_mm": prod.ancho_mm or 1,
            "alto_mm":  prod.alto_mm or 1,
            "peso_mg":  prod.peso_mg or 1,
        })
    return items


def _cajas_disponibles() -> list[dict]:
    """
    Retorna las cajas disponibles desde la BD en el formato que espera calcular_caja_optima.
    Las cajas son productos con is_caja=True (o el flag equivalente en tu modelo).
    Ajusta el filtro según tu campo real.
    """
    cajas_qs = Producto.objects.filter(es_caja=True, activo=True).values(
        "nombre", "largo_mm", "ancho_mm", "alto_mm", "volumen_ml"
    )
    return list(cajas_qs)


def _dimensiones_desde_resultado_empaque(resultado_empaque: list[dict], cajas_bd: list[dict]) -> dict:
    """
    A partir del resultado de calcular_caja_optima, obtiene las dimensiones
    de la caja más grande usada para pasarle a Chilexpress.

    Si se necesitaron varias cajas, Chilexpress cotiza por bulto individualmente.
    Por simplicidad, aquí se retorna la caja más grande como representativa
    del envío (el caso multi-caja se maneja al crear la OT, no en la cotización).
    """
    nombres_cajas_usadas = {r["caja"] for r in resultado_empaque}
    cajas_usadas = [c for c in cajas_bd if c["nombre"] in nombres_cajas_usadas]

    # La caja más grande determina las dimensiones del bulto principal
    caja_principal = max(cajas_usadas, key=lambda c: c["volumen_ml"])

    # El peso total es la suma de todos los productos (no el de la caja)
    # Se calcula aparte en quien llama a esta función
    return {
        "largo_mm": caja_principal["largo_mm"],
        "ancho_mm": caja_principal["ancho_mm"],
        "alto_mm":  caja_principal["alto_mm"],
    }


# =============================================================================
# Serializers de entrada
# =============================================================================

class ProductoManualSerializer(serializers.Serializer):
    """
    Representa un producto ingresado manualmente para cotización
    cuando no existe un pedido creado todavía.
    """
    peso_mg        = serializers.IntegerField(min_value=1)
    largo_mm       = serializers.IntegerField(min_value=1)
    ancho_mm       = serializers.IntegerField(min_value=1)
    alto_mm        = serializers.IntegerField(min_value=1)
    cantidad       = serializers.IntegerField(min_value=1, default=1)
    valor_unitario = serializers.IntegerField(min_value=0, required=False, default=0)


class CotizacionInputSerializer(serializers.Serializer):
    """
    Serializer para cotizar un envío.

    Modos:
      - Con pedido:  pedido_id + county_code_destino
      - Sin pedido:  sucursal_id + productos_ids + county_code_destino
    """
    pedido_id           = serializers.IntegerField(required=False, allow_null=True)
    sucursal_id         = serializers.IntegerField(required=False, allow_null=True)
    productos_ids       = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
    )
    county_code_destino = serializers.CharField(max_length=10)

    def validate(self, data):
        pedido_id   = data.get("pedido_id")
        sucursal_id = data.get("sucursal_id")
        productos_ids = data.get("productos_ids") or []

        if not pedido_id:
            if not sucursal_id:
                raise serializers.ValidationError(
                    "Si no se indica un pedido, debe especificar 'sucursal_id'."
                )
            if not productos_ids:
                raise serializers.ValidationError(
                    "Si no se indica un pedido, debe especificar al menos un producto en 'productos_ids'."
                )
        else:
            if not Pedido.objects.filter(pk=pedido_id).exists():
                raise serializers.ValidationError(f"No existe un pedido con id={pedido_id}.")

        if productos_ids:
            productos_existentes = set(
                Producto.objects.filter(pk__in=productos_ids, activo=True).values_list("pk", flat=True)
            )
            faltantes = sorted(set(productos_ids) - productos_existentes)
            if faltantes:
                raise serializers.ValidationError(
                    f"No existen o están inactivos los productos con id(s): {', '.join(str(pk) for pk in faltantes)}."
                )

        if not ComunaChilexpress.objects.filter(
            county_code=data["county_code_destino"],
            retorna_respuesta=True
        ).exists():
            raise serializers.ValidationError(
                f"El county_code '{data['county_code_destino']}' no es válido o sin cobertura disponible."
            )

        return data

    def get_payload_chilexpress(self) -> tuple:
        """
        Construye el payload listo para ChilexpressService.cotizar_envio().
        Ambos modos (con pedido y manual) pasan por calcular_caja_optima
        para obtener dimensiones reales de caja, no estimaciones.
        """
        data        = self.validated_data
        pedido_id   = data.get("pedido_id")
        cajas_bd    = _cajas_disponibles()

        if not cajas_bd:
            raise serializers.ValidationError(
                "No hay cajas disponibles en el sistema. Contacta al administrador."
            )

        if pedido_id:
            pedido          = Pedido.objects.get(pk=pedido_id)
            detalles        = DetallePedido.objects.filter(pedido=pedido).select_related("producto")
            items           = _productos_a_lista_empaque(detalles)
            sucursal        = pedido.sucursal_origen
            peso_total_mg   = sum((d.producto.peso_mg or 0) * d.cantidad for d in detalles)
            valor_declarado = pedido.total
        else:
            productos_ids   = data["productos_ids"]
            productos_qs    = Producto.objects.filter(pk__in=productos_ids, activo=True)
            productos_por_id = {producto.pk: producto for producto in productos_qs}
            items           = _productos_ids_a_lista_empaque(productos_por_id, productos_ids)
            sucursal        = Sucursal.objects.get(pk=data["sucursal_id"])
            peso_total_mg   = sum((productos_por_id[producto_id].peso_mg or 0) for producto_id in productos_ids)
            valor_declarado = sum((productos_por_id[producto_id].valor_unitario or 0) for producto_id in productos_ids)

        # Calcular empaque óptimo con cajas reales
        try:
            resultado_empaque = calcular_caja_optima(items, cajas_bd)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

        dims_caja = _dimensiones_desde_resultado_empaque(resultado_empaque, cajas_bd)

        # Cobertura de origen desde la sucursal
        county_origen = ComunaChilexpress.objects.filter(
            comuna=sucursal.comuna,
            retorna_respuesta=True
        ).first()
        if not county_origen:
            raise serializers.ValidationError(
                f"La sucursal '{sucursal.nombre}' no tiene cobertura Chilexpress configurada."
            )

        dims_chilexpress = dimensiones_a_chilexpress(
            peso_mg  = max(peso_total_mg, 1),
            largo_mm = dims_caja["largo_mm"],
            ancho_mm = dims_caja["ancho_mm"],
            alto_mm  = dims_caja["alto_mm"],
        )

        return {
            "originCountyCode":      county_origen.county_code,
            "destinationCountyCode": data["county_code_destino"],
            "package":               dims_chilexpress,
            "productType":           3,      # Encomienda
            "contentType":           1,
            "declaredWorth":         str(max(valor_declarado, 1000)),  # mínimo 1000 CLP si no se declaró valor
            "deliveryTime":          0,      # Todos los servicios
        }, len(resultado_empaque)


class CrearEnvioInputSerializer(serializers.Serializer):
    """
    Serializer para crear un envío (OT) en Chilexpress a partir de un pedido aprobado.
    """
    pedido_id         = serializers.IntegerField()
    service_type_code = serializers.IntegerField(
        help_text="serviceTypeCode obtenido de la cotización previa."
    )
    label_type        = serializers.IntegerField(
        default=2,
        help_text="0=Solo datos, 1=EPL Zebra, 2=Imagen binaria."
    )
    contacto_nombre   = serializers.CharField(max_length=100, required=False)
    contacto_telefono = serializers.CharField(max_length=15, required=False)
    contacto_email    = serializers.EmailField(required=False)

    def validate_pedido_id(self, value):
        try:
            pedido = Pedido.objects.select_related(
                "sucursal_origen", "direccion_entrega", "cliente"
            ).get(pk=value)
        except Pedido.DoesNotExist:
            raise serializers.ValidationError(f"No existe un pedido con id={value}.")

        if pedido.estado_pedido not in ["APROBADO", "EN_PICKING"]:
            raise serializers.ValidationError(
                f"El pedido debe estar APROBADO o EN_PICKING. Estado actual: {pedido.estado_pedido}."
            )

        if Despacho.objects.filter(pedido=pedido).exists():
            raise serializers.ValidationError(
                f"El pedido {value} ya tiene un despacho generado."
            )

        self._pedido = pedido
        return value


# =============================================================================
# Serializers de salida
# =============================================================================

class ServicioDisponibleSerializer(serializers.Serializer):
    serviceTypeCode     = serializers.IntegerField()
    serviceDescription  = serializers.CharField()
    finalWeight         = serializers.CharField()
    serviceValue        = serializers.CharField()
    deliveryType        = serializers.IntegerField()


class CotizacionOutputSerializer(serializers.Serializer):
    origin_county_code      = serializers.CharField()
    destination_county_code = serializers.CharField()
    servicios_disponibles   = ServicioDisponibleSerializer(many=True)
    pedido_id               = serializers.IntegerField(allow_null=True)
    num_cajas               = serializers.IntegerField(
        help_text="Número de cajas necesarias para este envío."
    )


class DespachoSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Despacho
        fields = [
            "id", "pedido_id", "courier_nombre", "numero_seguimiento",
            "estado_envio", "tipo_despacho", "fecha_despacho",
            "fecha_entrega_estimada", "costo_despacho", "url_etiqueta",
        ]
        read_only_fields = fields


TRANSICIONES_VALIDAS = {
    # estado_actual: [estados_a_los_que_puede_pasar]
    "PENDIENTE": ["RETIRADO", "CANCELADO"],
    "RETIRADO": ["EN_TRANSITO", "CANCELADO"],
    "EN_TRANSITO": ["ENTREGADO", "DEVUELTO", "CANCELADO"],
    "ENTREGADO": [],  # estado final
    "DEVUELTO": [],  # estado final
    "CANCELADO": [],  # estado final
}

# Qué transiciones puede hacer cada grupo de Django
TRANSICIONES_POR_ROL = {
    "Administradores": {
        "PENDIENTE": ["RETIRADO", "CANCELADO"],
        "RETIRADO": ["EN_TRANSITO", "CANCELADO"],
        "EN_TRANSITO": ["ENTREGADO", "DEVUELTO", "CANCELADO"],
    },
    "Ejecutivos": {
        "PENDIENTE": ["CANCELADO"],
        "RETIRADO": ["CANCELADO"],
        "EN_TRANSITO": ["CANCELADO"],
    },
    "OperadoresLogisticos": {
        "PENDIENTE": ["RETIRADO"],
        "RETIRADO": ["EN_TRANSITO"],
        "EN_TRANSITO": ["ENTREGADO", "DEVUELTO"],
    },
}


class ActualizarEstadoDespachoSerializer(serializers.Serializer):
    """
    Valida que la transición de estado sea permitida según el estado actual
    del despacho y el rol del usuario que hace la petición.
    """
    nuevo_estado = serializers.ChoiceField(
        choices=["RETIRADO", "EN_TRANSITO", "ENTREGADO", "DEVUELTO", "CANCELADO"]
    )
    observacion = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )

    def validate(self, data):
        despacho = self.context["despacho"]
        user = self.context["request"].user
        nuevo_estado = data["nuevo_estado"]
        estado_actual = despacho.estado_envio

        # Determinar el rol del usuario (primer grupo que coincida)
        grupos_usuario = set(user.groups.values_list("name", flat=True))
        rol = None
        for nombre_rol in TRANSICIONES_POR_ROL:
            if nombre_rol in grupos_usuario:
                rol = nombre_rol
                break

        if rol is None:
            raise serializers.ValidationError(
                "Tu usuario no pertenece a ningún rol autorizado para modificar despachos."
            )

        transiciones_permitidas = TRANSICIONES_POR_ROL[rol].get(estado_actual, [])

        if nuevo_estado not in transiciones_permitidas:
            permitidos_str = ", ".join(transiciones_permitidas) or "ninguno (estado final)"
            raise serializers.ValidationError(
                f"El rol '{rol}' no puede cambiar el estado '{estado_actual}' → '{nuevo_estado}'. "
                f"Transiciones permitidas desde '{estado_actual}': {permitidos_str}."
            )

        return data

