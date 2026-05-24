from django.conf import settings
from django.db import transaction
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from apps.payments.services.pedido_post_pago import aprobar_pedido_y_crear_despacho_pendiente
from rest_framework import permissions, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Pedido

from .models import TransaccionPago
from .serializers import (
    TransaccionPagoSerializer,
    WebpayCrearTransaccionSerializer,
    WebpayCommitSerializer,
)
from .services.webpay import WebpayService


class WebpayIniciarPagoView(APIView):
    """
    Inicia una transacción Webpay para un pedido del cliente autenticado.

    Endpoint:
    POST /api/payments/webpay/iniciar/

    Body:
    {
        "pedido_id": 1
    }
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = WebpayCrearTransaccionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pedido_id = serializer.validated_data["pedido_id"]

        try:
            pedido = Pedido.objects.select_related("cliente", "cliente__usuario").get(id=pedido_id)
        except Pedido.DoesNotExist:
            raise NotFound("No existe un pedido con el ID indicado.")

        if not hasattr(request.user, "perfilcliente"):
            raise PermissionDenied("Solo los clientes pueden pagar pedidos con Webpay.")

        if pedido.cliente != request.user.perfilcliente:
            raise PermissionDenied("No puedes pagar un pedido que no pertenece a tu cuenta.")

        if getattr(pedido, "total", 0) <= 0:
            raise ValidationError({
                "pedido_id": "El pedido no tiene un total válido para pagar."
            })

        # Evitar crear múltiples pagos activos para el mismo pedido.
        transaccion_existente = TransaccionPago.objects.filter(
            pedido=pedido,
            metodo_pago="WEBPAY",
            estado_pago__in=["PENDIENTE", "INICIADO", "AUTORIZADO"]
        ).order_by("-fecha_creacion").first()

        if transaccion_existente and transaccion_existente.token_ws:
            return Response({
                "detail": "Ya existe una transacción Webpay iniciada para este pedido.",
                "transaccion_pago": TransaccionPagoSerializer(transaccion_existente).data,
            }, status=status.HTTP_200_OK)

        buy_order = f"PED-{pedido.id}"
        session_id = f"USER-{request.user.id}-PED-{pedido.id}"
        amount = int(pedido.total)

        backend_base_url = getattr(settings, "BACKEND_BASE_URL", "http://localhost:8000")
        return_url = f"{backend_base_url}/api/payments/webpay/commit/"

        resultado_webpay = WebpayService.crear_transaccion(
            buy_order=buy_order,
            session_id=session_id,
            amount=amount,
            return_url=return_url,
        )

        transaccion = TransaccionPago.objects.create(
            pedido=pedido,
            metodo_pago="WEBPAY",
            estado_pago="INICIADO",
            monto_confirmado=amount,
            buy_order=buy_order,
            session_id=session_id,
            token_ws=resultado_webpay["token"],
            id_transaccion_externa=resultado_webpay["token"],
            observacion="Transacción Webpay iniciada.",
        )

        return Response({
            "transaccion_pago_id": transaccion.id,
            "pedido_id": pedido.id,
            "buy_order": buy_order,
            "session_id": session_id,
            "amount": amount,
            "token": resultado_webpay["token"],
            "url": resultado_webpay["url"],
            "redirect_url": resultado_webpay["redirect_url"],
        }, status=status.HTTP_201_CREATED)


class WebpayCommitView(APIView):
    """
    Confirma una transacción Webpay.

    Este endpoint es llamado por Webpay cuando el usuario termina el flujo de pago.

    Webpay puede enviar:
    - token_ws por query param
    - token_ws por POST

    Flujo cuando el pago es aprobado:
    1. Confirma TransaccionPago.
    2. Cambia Pedido.estado_pedido a APROBADO.
    3. Crea o mantiene Despacho.estado_envio en PENDIENTE.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return self._commit(request)

    def post(self, request):
        return self._commit(request)

    @transaction.atomic
    def _commit(self, request):
        token_ws = request.query_params.get("token_ws") or request.data.get("token_ws")

        serializer = WebpayCommitSerializer(data={"token_ws": token_ws})
        serializer.is_valid(raise_exception=True)

        token_ws = serializer.validated_data["token_ws"]

        resultado = WebpayService.confirmar_transaccion(token_ws)

        transaccion = (
            TransaccionPago.objects
            .select_for_update()
            .select_related("pedido")
            .filter(token_ws=token_ws)
            .first()
        )

        if not transaccion:
            raise NotFound("No se encontró una transacción local asociada al token_ws recibido.")

        pedido = transaccion.pedido

        # Validar que la orden de compra coincida.
        if str(resultado.get("buy_order")) != str(transaccion.buy_order):
            transaccion.estado_pago = "ERROR"
            transaccion.observacion = "La orden de compra devuelta por Webpay no coincide."
            transaccion.raw_response = resultado.get("raw", resultado)
            transaccion.fecha_confirmacion = timezone.now()
            transaccion.save(update_fields=[
                "estado_pago",
                "observacion",
                "raw_response",
                "fecha_confirmacion",
            ])

            raise ValidationError({
                "buy_order": "La orden de compra devuelta por Webpay no coincide con la transacción local."
            })

        # Validar que el monto coincida.
        if int(resultado.get("amount") or 0) != int(transaccion.monto_confirmado):
            transaccion.estado_pago = "ERROR"
            transaccion.observacion = "El monto devuelto por Webpay no coincide."
            transaccion.raw_response = resultado.get("raw", resultado)
            transaccion.fecha_confirmacion = timezone.now()
            transaccion.save(update_fields=[
                "estado_pago",
                "observacion",
                "raw_response",
                "fecha_confirmacion",
            ])

            raise ValidationError({
                "amount": "El monto devuelto por Webpay no coincide con la transacción local."
            })

        aprobada = resultado.get("aprobada", False)

        transaccion.response_code = resultado.get("response_code")
        transaccion.webpay_status = resultado.get("status")
        transaccion.authorization_code = resultado.get("authorization_code")
        transaccion.payment_type_code = resultado.get("payment_type_code")
        transaccion.installments_number = resultado.get("installments_number")
        transaccion.raw_response = resultado.get("raw", resultado)

        card_detail = resultado.get("card_detail") or {}
        transaccion.card_last_digits = card_detail.get("card_number")

        transaction_date = resultado.get("transaction_date")
        if transaction_date:
            parsed_date = parse_datetime(str(transaction_date))
            if parsed_date:
                transaccion.transaction_date = parsed_date

        despacho_creado = False

        if aprobada:
            transaccion.estado_pago = "CONFIRMADO"
            transaccion.fecha_confirmacion = timezone.now()
            transaccion.observacion = "Pago confirmado correctamente por Webpay."
            transaccion.save(update_fields=[
                "response_code",
                "webpay_status",
                "authorization_code",
                "payment_type_code",
                "installments_number",
                "raw_response",
                "card_last_digits",
                "transaction_date",
                "estado_pago",
                "fecha_confirmacion",
                "observacion",
            ])

            # Actualiza Pedido y Despacho en apps distintas:
            # - Pedido.estado_pedido = APROBADO
            # - Despacho.estado_envio = PENDIENTE
            pedido, despacho, despacho_creado = aprobar_pedido_y_crear_despacho_pendiente(
                transaccion
            )

        else:
            transaccion.estado_pago = "RECHAZADO"
            transaccion.fecha_confirmacion = timezone.now()
            transaccion.observacion = "Pago rechazado o no autorizado por Webpay."
            transaccion.save(update_fields=[
                "response_code",
                "webpay_status",
                "authorization_code",
                "payment_type_code",
                "installments_number",
                "raw_response",
                "card_last_digits",
                "transaction_date",
                "estado_pago",
                "fecha_confirmacion",
                "observacion",
            ])

        frontend_base_url = getattr(settings, "FRONTEND_BASE_URL", None)

        if frontend_base_url:
            resultado_path = (
                f"{frontend_base_url}/resultado-pago"
                f"?pedido_id={pedido.id}"
                f"&transaccion_id={transaccion.id}"
                f"&estado={transaccion.estado_pago}"
            )
            return redirect(resultado_path)

        response_data = {
            "transaccion_pago_id": transaccion.id,
            "pedido_id": pedido.id,
            "aprobada": aprobada,
            "estado_pago": transaccion.estado_pago,
            "estado_pedido": pedido.estado_pedido,
            "webpay": resultado,
        }

        if aprobada:
            response_data["despacho"] = {
                "id": despacho.id,
                "estado_envio": despacho.estado_envio,
                "creado": despacho_creado,
            }

        return Response(response_data, status=status.HTTP_200_OK)

class WebpayEstadoView(APIView):
    """
    Consulta el estado de una transacción Webpay ya iniciada.

    Endpoint:
    GET /api/payments/webpay/estado/<token_ws>/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, token_ws):
        transaccion = TransaccionPago.objects.filter(token_ws=token_ws).select_related(
            "pedido",
            "pedido__cliente",
            "pedido__cliente__usuario"
        ).first()

        if not transaccion:
            raise NotFound("No se encontró una transacción asociada al token indicado.")

        if hasattr(request.user, "perfilcliente"):
            if transaccion.pedido.cliente != request.user.perfilcliente:
                raise PermissionDenied("No puedes consultar una transacción que no pertenece a tu cuenta.")

        resultado = WebpayService.consultar_estado(token_ws)

        return Response({
            "transaccion_pago": TransaccionPagoSerializer(transaccion).data,
            "webpay": resultado,
        }, status=status.HTTP_200_OK)


class MisTransaccionesPagoView(APIView):
    """
    Lista las transacciones de pago del cliente autenticado.

    Endpoint:
    GET /api/payments/mis-pagos/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not hasattr(request.user, "perfilcliente"):
            raise PermissionDenied("Solo los clientes pueden consultar sus pagos.")

        transacciones = TransaccionPago.objects.filter(
            pedido__cliente=request.user.perfilcliente
        ).select_related("pedido").order_by("-fecha_creacion")

        serializer = TransaccionPagoSerializer(transacciones, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)