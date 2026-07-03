from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date
from datetime import datetime, time, timedelta, date
from collections import defaultdict
from typing import cast
from apps.payments.services.pedido_post_pago import aprobar_pedido_y_crear_despacho_pendiente
from rest_framework import permissions, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Pedido, DetallePedido
from apps.inventory.models import CategoriaProducto

from .models import TransaccionPago
from .serializers import (
    TransaccionPagoSerializer,
    WebpayCrearTransaccionSerializer,
    WebpayCommitSerializer,
)
from .services.webpay import WebpayService


def _restar_meses(fecha: date, meses: int) -> date:
    """Resta `meses` meses a `fecha` sin dependencias externas (clamp de día)."""
    mes_total = fecha.month - 1 - meses
    anio = fecha.year + mes_total // 12
    mes = mes_total % 12 + 1
    dia = fecha.day
    while True:
        try:
            return date(anio, mes, dia)
        except ValueError:
            dia -= 1  # clamp si el mes destino tiene menos días (ej. 31 -> 30/28)


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

        backend_base_url = getattr(settings, "BACKEND_BASE_URL", "http://98.95.174.251:8000")
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
        despacho = None

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
            response_data["despacho"] = None if despacho is None else {
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



# Reemplazar MisTransaccionesPagoView completo:

class MisTransaccionesPagoView(APIView):
    """
    GET /api/payments/mis-pagos/
    Solo clientes: lista sus propias transacciones.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not hasattr(request.user, 'perfilcliente'):
            raise PermissionDenied("Solo los clientes pueden consultar sus pagos.")

        transacciones = TransaccionPago.objects.filter(
            pedido__cliente=request.user.perfilcliente
        ).select_related('pedido').order_by('-fecha_creacion')

        serializer = TransaccionPagoSerializer(transacciones, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# Agregar nueva vista:

class TodosLosPagosView(APIView):
    """
    GET /api/payments/todos/
    Solo Administrador, Ejecutivo y Analista pueden acceder.
    Devuelve todos los pagos con datos del cliente y pedido.
    """
    permission_classes = [permissions.IsAuthenticated]

    ROLES_PERMITIDOS = ['Administrador', 'Ejecutivo', 'Analista']

    def get(self, request):
        tiene_permiso = (
            request.user.is_staff
            or request.user.groups.filter(name__in=self.ROLES_PERMITIDOS).exists()
        )

        if not tiene_permiso:
            raise PermissionDenied(
                "Solo Administrador, Ejecutivo o Analista pueden ver todos los pagos."
            )

        transacciones = (
            TransaccionPago.objects
            .select_related(
                'pedido',
                'pedido__cliente',
                'pedido__cliente__usuario',
            )
            .order_by('-fecha_creacion')
        )

        # Filtros opcionales por query params
        estado = request.query_params.get('estado_pago')
        if estado:
            transacciones = transacciones.filter(estado_pago=estado)

        metodo = request.query_params.get('metodo_pago')
        if metodo:
            transacciones = transacciones.filter(metodo_pago=metodo)

        from .serializers import TransaccionPagoAdminSerializer
        serializer = TransaccionPagoAdminSerializer(transacciones, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VentasPorCategoriaView(APIView):
    """
    GET /api/payments/stats/ventas-por-categoria/

    Alimenta el donut "Ventas por categoría" del dashboard Admin (T4.1).

    Query params opcionales:
        desde: YYYY-MM-DD (inclusive)
        hasta: YYYY-MM-DD (inclusive)
    Si se omiten ambos, se usan los últimos 12 meses.

    Solo cuenta ventas efectivas: pedidos con TransaccionPago en estado
    CONFIRMADO (mismo criterio que el KPI "Ventas (12m)"). El monto incluye
    IVA. El monto confirmado de cada pedido se reparte entre sus líneas a
    prorrata del subtotal de cada línea, y cada línea se imputa a la
    primera categoría (menor id de CategoriaProducto) del producto.
    """

    permission_classes = [permissions.IsAuthenticated]

    ROLES_PERMITIDOS = ['Administrador', 'Ejecutivo', 'Analista']

    def get(self, request):
        tiene_permiso = (
            request.user.is_staff
            or request.user.groups.filter(name__in=self.ROLES_PERMITIDOS).exists()
        )

        if not tiene_permiso:
            raise PermissionDenied(
                "Solo Administrador, Ejecutivo o Analista pueden ver estadísticas de ventas."
            )

        desde_str = request.query_params.get('desde')
        hasta_str = request.query_params.get('hasta')

        hoy = timezone.localdate()

        desde = parse_date(desde_str) if desde_str else None
        if desde_str and desde is None:
            raise ValidationError({'desde': 'Formato inválido. Use YYYY-MM-DD.'})

        hasta = parse_date(hasta_str) if hasta_str else None
        if hasta_str and hasta is None:
            raise ValidationError({'hasta': 'Formato inválido. Use YYYY-MM-DD.'})

        if desde is None and hasta is None:
            hasta = hoy
            desde = _restar_meses(hoy, 12)
        elif desde is None:
            desde = _restar_meses(cast(date, hasta), 12)
        elif hasta is None:
            hasta = hoy

        tz = timezone.get_current_timezone()
        desde_inclusive = timezone.make_aware(datetime.combine(desde, time.min), tz)
        hasta_exclusive = timezone.make_aware(datetime.combine(hasta + timedelta(days=1), time.min), tz)

        # 1. Monto confirmado por pedido en el rango.
        transacciones = (
            TransaccionPago.objects
            .filter(
                estado_pago='CONFIRMADO',
                fecha_confirmacion__gte=desde_inclusive,
                fecha_confirmacion__lt=hasta_exclusive,
            )
            .values('pedido_id')
            .annotate(monto_confirmado_pedido=Sum('monto_confirmado'))
        )

        monto_confirmado_por_pedido = {
            t['pedido_id']: t['monto_confirmado_pedido'] for t in transacciones
        }

        if not monto_confirmado_por_pedido:
            return Response([], status=status.HTTP_200_OK)

        pedido_ids = list(monto_confirmado_por_pedido.keys())

        # 2. Líneas de esos pedidos.
        detalles = (
            DetallePedido.objects
            .filter(pedido_id__in=pedido_ids)
            .values('pedido_id', 'producto_id', 'cantidad', 'subtotal')
        )

        detalles_por_pedido = defaultdict(list)
        productos_ids = set()

        for d in detalles:
            detalles_por_pedido[d['pedido_id']].append(d)
            productos_ids.add(d['producto_id'])

        # 3. Primera categoría (menor id de CategoriaProducto) por producto.
        categoria_por_producto = {}
        categorias_info = {}

        relaciones = (
            CategoriaProducto.objects
            .filter(producto_id__in=productos_ids)
            .select_related('categoria')
            .order_by('producto_id', 'id')
        )

        for rel in relaciones:
            if rel.producto_id not in categoria_por_producto:
                categoria_por_producto[rel.producto_id] = rel.categoria_id
                categorias_info[rel.categoria_id] = rel.categoria.nombre

        # 4. Acumular total / unidades / pedidos por categoría.
        total_por_categoria = defaultdict(int)
        unidades_por_categoria = defaultdict(int)
        pedidos_por_categoria = defaultdict(set)

        for pedido_id, lineas in detalles_por_pedido.items():
            monto_confirmado_pedido = monto_confirmado_por_pedido.get(pedido_id, 0)
            subtotal_pedido = sum(l['subtotal'] for l in lineas)

            if subtotal_pedido <= 0:
                continue

            for linea in lineas:
                categoria_id = categoria_por_producto.get(linea['producto_id'])
                if categoria_id is None:
                    continue  # producto sin categoría asignada: se excluye

                factor = linea['subtotal'] / subtotal_pedido
                monto_linea = round(monto_confirmado_pedido * factor)

                total_por_categoria[categoria_id] += monto_linea
                unidades_por_categoria[categoria_id] += linea['cantidad']
                pedidos_por_categoria[categoria_id].add(pedido_id)

        resultado = [
            {
                'categoria_id': categoria_id,
                'categoria': categorias_info[categoria_id],
                'total': total,
                'pedidos': len(pedidos_por_categoria[categoria_id]),
                'unidades': unidades_por_categoria[categoria_id],
            }
            for categoria_id, total in total_por_categoria.items()
        ]

        resultado.sort(key=lambda r: r['total'], reverse=True)

        return Response(resultado, status=status.HTTP_200_OK)