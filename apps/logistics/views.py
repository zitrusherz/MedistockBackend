from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
#from rest_framework.permissions import IsAuthenticated

from apps.logistics.serializers import (
    CotizacionInputSerializer,
    CrearEnvioInputSerializer,
    CotizacionOutputSerializer,
    DespachoSerializer,
    _cajas_disponibles,
    _productos_a_lista_empaque,
    _dimensiones_desde_resultado_empaque,
)
from apps.logistics.services.chilexpress import ChilexpressService
from apps.logistics.models import Despacho
from apps.orders.models import DetallePedido
from apps.logistics.utils import calcular_caja_optima, dimensiones_a_chilexpress
from apps.locations.models import ComunaChilexpress


class CotizarEnvioView(APIView):
    """
    POST /api/v1/logistics/cotizar/

    Cotiza un envío con Chilexpress. No requiere que exista un pedido.

    Modos de uso:

    1. Con pedido existente:
        { "pedido_id": 42, "county_code_destino": "PROV" }

    2. Sin pedido (consulta libre):
        {
            "sucursal_id": 1,
            "county_code_destino": "CONC",
            "productos": [
                {"peso_mg": 500000, "largo_mm": 200, "ancho_mm": 150, "alto_mm": 100, "cantidad": 3}
            ]
        }
    """
    #permission_classes = [IsAuthenticated]

    permission_classes = []

    def post(self, request):
        serializer = CotizacionInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload_chilexpress, num_cajas = serializer.get_payload_chilexpress()

        except Exception as e:
            return Response(
                {"error": f"Error al construir los parámetros de cotización: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = ChilexpressService()
        try:
            respuesta = service.cotizar_envio(payload_chilexpress, guardar_log=False)
        except Exception as e:
            return Response(
                {"error": f"Error al consultar Chilexpress: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        servicios = respuesta.get("data", {}).get("courierServiceOptions", [])

        output = {
            "origin_county_code":      payload_chilexpress["originCountyCode"],
            "destination_county_code": payload_chilexpress["destinationCountyCode"],
            "servicios_disponibles":   servicios,
            "pedido_id":               serializer.validated_data.get("pedido_id"),
            "num_cajas":               num_cajas,
        }

        if not servicios:
            output["mensaje"] = "No hay servicios disponibles para esta combinación de origen y destino."

        return Response(CotizacionOutputSerializer(output).data, status=status.HTTP_200_OK)


class CrearEnvioView(APIView):
    """
    POST /api/v1/logistics/envios/

    Crea una Orden de Transporte (OT) en Chilexpress para un pedido aprobado.
    Requiere haber cotizado previamente para obtener el serviceTypeCode.

    Body:
        {
            "pedido_id": 42,
            "service_type_code": 3,
            "label_type": 2,
            "contacto_nombre": "Clínica Bío-Bío",   // opcional
            "contacto_telefono": "412223344",        // opcional
            "contacto_email": "bodega@clinica.cl"    // opcional
        }
    """
    #permission_classes = [IsAuthenticated]
    permission_classes = []

    def post(self, request):
        serializer = CrearEnvioInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data   = serializer.validated_data
        pedido = serializer._pedido

        # --- Cobertura origen ---
        sucursal     = pedido.sucursal_origen
        county_origen = ComunaChilexpress.objects.filter(
            comuna=sucursal.comuna,
            retorna_respuesta=True
        ).first()

        if not county_origen:
            return Response(
                {"error": f"La sucursal '{sucursal.nombre}' no tiene cobertura Chilexpress configurada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- Cobertura destino ---
        dir_entrega    = pedido.direccion_entrega
        county_destino = ComunaChilexpress.objects.filter(
            comuna=dir_entrega.comuna,
            retorna_respuesta=True
        ).first()

        if not county_destino:
            return Response(
                {"error": "La dirección de entrega del pedido no tiene cobertura Chilexpress configurada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- Dimensiones reales usando cajas de la BD ---
        detalles = DetallePedido.objects.filter(pedido=pedido).select_related("producto")
        items    = _productos_a_lista_empaque(detalles)
        cajas_bd = _cajas_disponibles()

        if not cajas_bd:
            return Response(
                {"error": "No hay cajas disponibles en el sistema. Contacta al administrador."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            resultado_empaque = calcular_caja_optima(items, cajas_bd)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        dims_caja = _dimensiones_desde_resultado_empaque(resultado_empaque, cajas_bd)
        peso_total_mg = sum((d.producto.peso_mg or 0) * d.cantidad for d in detalles)

        dims_cx = dimensiones_a_chilexpress(
            peso_mg  = max(peso_total_mg, 1),
            largo_mm = dims_caja["largo_mm"],
            ancho_mm = dims_caja["ancho_mm"],
            alto_mm  = dims_caja["alto_mm"],
        )

        # --- Contactos ---
        cliente = pedido.cliente
        contacto_destinatario = {
            "name":        data.get("contacto_nombre")   or getattr(cliente, "nombre_completo", str(cliente)),
            "phoneNumber": data.get("contacto_telefono") or getattr(dir_entrega, "telefono", "000000000"),
            "mail":        data.get("contacto_email")    or cliente.email,
        }
        contacto_remitente = {
            "name":        f"MEDISTOCK {sucursal.nombre}",
            "phoneNumber": sucursal.telefono or "225551234",
            "mail":        "despacho@medistock.cl",
        }

        # --- Dirección y paquete ---
        direccion_destino = {
            "countyCoverageCode":       county_destino.county_code,
            "streetName":               dir_entrega.calle,
            "streetNumber":             getattr(dir_entrega, "numero", ""),
            "supplement":               getattr(dir_entrega, "complemento", ""),
            "deliveryOnCommercialOffice": False,
        }
        paquete = {
            **dims_cx,
            "serviceDeliveryCode": str(data["service_type_code"]),
            "productCode":         "3",
            "deliveryReference":   f"PED-{pedido.id:05d}",
            "groupReference":      "MEDISTOCK",
            "declaredValue":       str(pedido.total),
            "declaredContent":     "5",
        }

        # --- Crear OT en Chilexpress ---
        service = ChilexpressService()
        try:
            respuesta_cx = service.crear_orden_transporte(
                codigo_cobertura_origen = county_origen.county_code,
                direccion_destino       = direccion_destino,
                contacto_remitente      = contacto_remitente,
                contacto_destinatario   = contacto_destinatario,
                paquete                 = paquete,
                label_type              = data.get("label_type", 2),
            )
        except Exception as e:
            return Response(
                {"error": f"Error al crear la OT en Chilexpress: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # --- Persistir despacho ---
        detalle_ot       = respuesta_cx.get("data", {}).get("detail", [{}])[0]
        numero_ot        = detalle_ot.get("transportOrderNumber")
        etiqueta_binaria = detalle_ot.get("label", {}).get("labelData", "")

        despacho = Despacho.objects.create(
            pedido            = pedido,
            courier_nombre    = "Chilexpress",
            numero_seguimiento= str(numero_ot),
            estado_envio      = "PENDIENTE",
            tipo_despacho     = pedido.tipo_despacho,
            costo_despacho    = 0,
            url_etiqueta      = "",
        )

        pedido.estado_pedido = "EN_PICKING"
        pedido.save(update_fields=["estado_pedido"])

        return Response(
            {
                "despacho":            DespachoSerializer(despacho).data,
                "numero_ot":           numero_ot,
                "num_cajas":           len(resultado_empaque),
                "etiqueta_disponible": bool(etiqueta_binaria),
                "service_description": detalle_ot.get("serviceDescriptionFull", ""),
            },
            status=status.HTTP_201_CREATED,
        )


class TrackingView(APIView):
    """
    GET /api/v1/logistics/envios/{pedido_id}/tracking/

    Consulta el estado actual de un envío en Chilexpress.
    Query param: ?historial=true para ver todos los eventos.
    """
    #permission_classes = [IsAuthenticated]

    def get(self, request, pedido_id):
        try:
            despacho = Despacho.objects.select_related("pedido").get(pedido_id=pedido_id)
        except Despacho.DoesNotExist:
            return Response(
                {"error": f"No existe despacho para el pedido {pedido_id}."},
                status=status.HTTP_404_NOT_FOUND,
            )

        service = ChilexpressService()
        try:
            tracking = service.consultar_tracking(
                num_orden_transporte    = int(despacho.numero_seguimiento),
                referencia              = f"PED-{pedido_id:05d}",
                rut                     = "0",  # producción: settings.MEDISTOCK_RUT
                mostrar_todos_los_eventos = request.query_params.get("historial", "false").lower() == "true",
            )
        except Exception as e:
            return Response(
                {"error": f"Error al consultar tracking: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(tracking, status=status.HTTP_200_OK)