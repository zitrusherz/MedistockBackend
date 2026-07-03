
from decimal import Decimal
from django.db import transaction
from apps.logistics.services.chilexpress import ChilexpressService
from apps.logistics.models import Despacho
from apps.orders.models import Pedido


class LogisticaService:

    def __init__(self):
        self.chilexpress = ChilexpressService()

    # -------------------------------------------------------------------------
    # Método principal: crear despacho para un pedido
    # -------------------------------------------------------------------------

    @transaction.atomic
    def crear_despacho(self, pedido_id: int) -> Despacho:
        """
        Orquesta la creación completa de un despacho:
            1. Valida que el pedido esté listo para despachar
            2. Consolida las dimensiones del paquete desde los productos
            3. Obtiene los códigos de cobertura desde los modelos
            4. Cotiza el envío en Chilexpress
            5. Crea la OT en Chilexpress
            6. Guarda el Despacho con el número de OT y tracking
            7. Actualiza el estado del Pedido

        :param pedido_id: ID del Pedido a despachar
        :return: Instancia de Despacho recién creada
        :raises ValueError: Si el pedido no está en estado válido o faltan datos
        :raises requests.RequestException: Si la API de Chilexpress falla
        """
        pedido = self._obtener_pedido_valido(pedido_id)
        paquete = self._calcular_paquete(pedido)
        cobertura_origen, cobertura_destino = self._obtener_coberturas(pedido)
        service_code = self._cotizar_y_elegir_servicio(
            cobertura_origen, cobertura_destino, paquete, pedido
        )
        contacto_remitente = self._contacto_remitente(pedido)
        contacto_destinatario = self._contacto_destinatario(pedido)
        direccion_destino = self._direccion_destino(pedido, cobertura_destino)

        respuesta_ot = self.chilexpress.crear_orden_transporte(
            codigo_cobertura_origen=cobertura_origen,
            direccion_destino=direccion_destino,
            contacto_remitente=contacto_remitente,
            contacto_destinatario=contacto_destinatario,
            paquete={
                **paquete,
                "serviceDeliveryCode": service_code,
                "deliveryReference": f"PED-{pedido.id:06d}",
                "groupReference": "MEDISTOCK",
                "declaredValue": str(pedido.total),
                "declaredContent": "5",  # 5 = Otros (insumos clínicos no tienen categoría específica)
            },
            guardar_log=True,
        )

        despacho = self._guardar_despacho(pedido, respuesta_ot)
        pedido.estado_pedido = "DESPACHADO"
        pedido.save(update_fields=["estado_pedido"])

        return despacho

    # -------------------------------------------------------------------------
    # Helpers privados
    # -------------------------------------------------------------------------

    def _obtener_pedido_valido(self, pedido_id: int) -> Pedido:
        try:
            pedido = (
                Pedido.objects
                .select_related(
                    "direccion_entrega__comuna__region",
                    "sucursal_origen__comuna",
                    "cliente",
                )
                .prefetch_related("detalle_pedido__producto")
                .get(id=pedido_id)
            )
        except Pedido.DoesNotExist:
            raise ValueError(f"No existe el pedido con id={pedido_id}.")

        ESTADOS_DESPACHABLES = {"EN_PICKING", "APROBADO"}
        if pedido.estado_pedido not in ESTADOS_DESPACHABLES:
            raise ValueError(
                f"El pedido {pedido_id} está en estado '{pedido.estado_pedido}'. "
                f"Solo se pueden despachar pedidos en: {ESTADOS_DESPACHABLES}."
            )

        if Despacho.objects.filter(pedido=pedido).exists():
            raise ValueError(f"El pedido {pedido_id} ya tiene un despacho registrado.")

        return pedido

    def _calcular_paquete(self, pedido: Pedido) -> dict:
        """
        Consolida las dimensiones de todos los productos del pedido en un
        paquete único. Estrategia: peso sumado, dimensiones máximas.
        Si algún producto no tiene dimensiones completas, lanza ValueError.
        """
        detalles = list(pedido.detalle_pedido.all())
        if not detalles:
            raise ValueError(f"El pedido {pedido.id} no tiene productos.")

        peso_total = Decimal("0")
        alto_max = ancho_max = largo_max = 0

        for detalle in detalles:
            producto = detalle.producto
            if not producto.tiene_dimensiones_completas():
                raise ValueError(
                    f"El producto '{producto.nombre}' (SKU: {producto.sku}) "
                    f"no tiene dimensiones completas. Completa peso, alto, ancho y largo."
                )
            peso_total += producto.peso_kg * detalle.cantidad
            alto_max = max(alto_max, producto.alto_cm)
            ancho_max = max(ancho_max, producto.ancho_cm)
            largo_max = max(largo_max, producto.largo_cm)

        return {
            "weight": str(round(peso_total, 3)),
            "height": str(alto_max),
            "width": str(ancho_max),
            "length": str(largo_max),
            "productCode": "3",  # 3 = Encomienda (siempre para insumos médicos)
        }

    def _obtener_coberturas(self, pedido: Pedido) -> tuple[str, str]:
        """
        Retorna (coverage_code_origen, coverage_code_destino).
        Los coverage codes deben estar cargados en los modelos Comuna.
        """
        # Origen: la sucursal desde donde se despacha
        comuna_origen = pedido.sucursal_origen.comuna
        if not comuna_origen.chilexpress_coverage_code:
            raise ValueError(
                f"La comuna '{comuna_origen.nombre}' de la sucursal de origen "
                f"no tiene código de cobertura Chilexpress configurado."
            )

        # Destino: la dirección de entrega del pedido
        comuna_destino = pedido.direccion_entrega.comuna
        if not comuna_destino.chilexpress_coverage_code:
            raise ValueError(
                f"La comuna '{comuna_destino.nombre}' de la dirección de entrega "
                f"no tiene código de cobertura Chilexpress configurado."
            )

        return (
            comuna_origen.chilexpress_coverage_code,
            comuna_destino.chilexpress_coverage_code,
        )

    def _cotizar_y_elegir_servicio(self, cobertura_origen: str, cobertura_destino: str,
                                   paquete: dict, pedido: Pedido) -> str:
        """
        Cotiza y elige el servicio según la prioridad médica del pedido:
        - prioridad CRITICA o ALTA → elige el servicio más rápido (prioritario)
        - prioridad NORMAL → elige el más económico
        """
        payload_cotizacion = {
            "originCountyCode": cobertura_origen,
            "destinationCountyCode": cobertura_destino,
            "package": {
                "weight": paquete["weight"],
                "height": paquete["height"],
                "width": paquete["width"],
                "length": paquete["length"],
            },
            "productType": 3,
            "contentType": 1,
            "declaredWorth": str(pedido.total),
            "deliveryTime": 0,  # 0 = consultar todos los servicios
        }

        respuesta = self.chilexpress.cotizar_envio(payload_cotizacion, guardar_log=False)
        servicios = respuesta.get("data", {}).get("courierServiceOptions", [])

        if not servicios:
            raise ValueError(
                f"Chilexpress no retornó servicios disponibles para la ruta "
                f"{cobertura_origen} → {cobertura_destino}."
            )

        prioridad_alta = pedido.prioridad_medica in ("CRITICA", "ALTA")

        if prioridad_alta:
            # Prioritarios primero; si no hay, toma el primero disponible
            prioritarios = [s for s in servicios if s.get("deliveryTime") == 1]
            elegido = prioritarios[0] if prioritarios else servicios[0]
        else:
            # El más económico
            elegido = min(servicios, key=lambda s: s.get("serviceValue", float("inf")))

        return str(elegido["serviceDeliveryCode"])

    def _contacto_remitente(self, pedido: Pedido) -> dict:
        sucursal = pedido.sucursal_origen
        return {
            "name": f"MEDISTOCK {sucursal.nombre}",
            "phoneNumber": getattr(sucursal, "telefono", "222000000"),
            "mail": getattr(sucursal, "email", "despacho@medistock.cl"),
        }

    def _contacto_destinatario(self, pedido: Pedido) -> dict:
        cliente = pedido.cliente
        return {
            "name": getattr(cliente, "nombre_completo", str(cliente)),
            "phoneNumber": getattr(cliente, "telefono", ""),
            "mail": cliente.email if hasattr(cliente, "email") else "",
        }

    def _direccion_destino(self, pedido: Pedido, cobertura_destino: str) -> dict:
        direccion = pedido.direccion_entrega
        return {
            "countyCoverageCode": cobertura_destino,
            "streetName": direccion.calle,
            "streetNumber": getattr(direccion, "numero", ""),
            "supplement": getattr(direccion, "complemento", ""),
            "deliveryOnCommercialOffice": False,
            "observation": getattr(direccion, "observaciones", ""),
        }

    def _guardar_despacho(self, pedido: Pedido, respuesta_ot: dict) -> Despacho:
        data = respuesta_ot.get("data", {})
        detalle = data.get("detail", [{}])[0]

        return Despacho.objects.create(
            pedido=pedido,
            courier_nombre="Chilexpress",
            numero_seguimiento=str(detalle.get("transportOrderNumber", "")),
            estado_envio="PENDIENTE",
            tipo_despacho=pedido.tipo_despacho,
            costo_despacho=0,  # En producción puedes guardar el costo de la cotización
        )

    # -------------------------------------------------------------------------
    # Tracking público (llamado desde la view de tracking)
    # -------------------------------------------------------------------------

    def consultar_tracking_pedido(self, pedido_id: int) -> dict:
        """
        Consulta el estado de envío de un pedido dado su ID.
        La view de tracking llama a esto, no a ChilexpressService directamente.
        """
        try:
            despacho = Despacho.objects.select_related("pedido").get(pedido_id=pedido_id)
        except Despacho.DoesNotExist:
            raise ValueError(f"El pedido {pedido_id} no tiene un despacho registrado.")

        if not despacho.numero_seguimiento:
            raise ValueError(f"El despacho del pedido {pedido_id} no tiene número de seguimiento.")

        from django.conf import settings
        return self.chilexpress.consultar_tracking(
            num_orden_transporte=int(despacho.numero_seguimiento),
            referencia=f"PED-{pedido_id:06d}",
            rut=settings.CHILEXPRESS_RUT_EMPRESA,
            guardar_log=False,
        )