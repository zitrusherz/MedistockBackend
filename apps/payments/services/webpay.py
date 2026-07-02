from decimal import Decimal, InvalidOperation

from django.conf import settings
from rest_framework.exceptions import ValidationError, APIException

from transbank.common.integration_type import IntegrationType
from transbank.common.options import WebpayOptions
from transbank.webpay.webpay_plus.transaction import Transaction


class WebpayServiceError(APIException):
    status_code = 502
    default_detail = "Error al comunicarse con Webpay."
    default_code = "webpay_service_error"


class WebpayService:
    """
    Servicio de integración con Webpay Plus.

    Responsabilidades:
    - Crear transacciones de pago.
    - Confirmar transacciones mediante commit.
    - Consultar estado de una transacción.
    """

    @staticmethod
    def _get_environment():
        environment = settings.TRANSBANK_ENVIRONMENT

        if str(environment).upper() == "LIVE":
            return IntegrationType.LIVE

        return IntegrationType.TEST

    @classmethod
    def _get_transaction(cls):
        commerce_code = settings.TRANSBANK_WEBPAY_COMMERCE_CODE
        api_key = settings.TRANSBANK_WEBPAY_API_KEY

        if not commerce_code:
            raise WebpayServiceError(
                "No está configurado TRANSBANK_WEBPAY_COMMERCE_CODE."
            )

        if not api_key:
            raise WebpayServiceError(
                "No está configurado TRANSBANK_WEBPAY_API_KEY."
            )

        options = WebpayOptions(
            commerce_code,
            api_key,
            cls._get_environment()
        )

        return Transaction(options)

    @staticmethod
    def _normalizar_monto(amount):
        """
        Webpay trabaja con montos enteros en CLP.
        Ejemplo válido: 12990
        """
        try:
            monto = Decimal(str(amount))
        except (InvalidOperation, TypeError):
            raise ValidationError({
                "amount": "El monto debe ser numérico."
            })

        if monto <= 0:
            raise ValidationError({
                "amount": "El monto debe ser mayor a cero."
            })

        if monto != monto.to_integral_value():
            raise ValidationError({
                "amount": "El monto para Webpay debe ser un entero en pesos chilenos."
            })

        return int(monto)

    @staticmethod
    def _validar_texto_requerido(valor, campo):
        if valor is None or str(valor).strip() == "":
            raise ValidationError({
                campo: f"El campo {campo} es obligatorio."
            })

        return str(valor).strip()

    @classmethod
    def crear_transaccion(cls, buy_order, session_id, amount, return_url=None):
        """
        Crea una transacción Webpay Plus.

        Parámetros:
        - buy_order: orden de compra interna. Ej: PED-123
        - session_id: identificador de sesión o usuario. Ej: user-5
        - amount: monto entero en CLP.
        - return_url: URL backend donde Webpay devolverá el token_ws.

        Retorna:
        {
            "token": "...",
            "url": "...",
            "redirect_url": "url + ?token_ws=..."
        }
        """

        buy_order = cls._validar_texto_requerido(buy_order, "buy_order")
        session_id = cls._validar_texto_requerido(session_id, "session_id")
        amount = cls._normalizar_monto(amount)

        if return_url is None:
            backend_base_url = getattr(settings, "BACKEND_BASE_URL", "http://localhost:8000")
            return_url = f"{backend_base_url}/api/payments/webpay/commit/"

        try:
            tx = cls._get_transaction()
            response = tx.create(
                buy_order=buy_order,
                session_id=session_id,
                amount=amount,
                return_url=return_url,
            )

            token = response.get("token")
            url = response.get("url")

            if not token or not url:
                raise WebpayServiceError(
                    "Webpay no entregó token o URL de redirección."
                )

            return {
                "token": token,
                "url": url,
                "redirect_url": f"{url}?token_ws={token}",
                "buy_order": buy_order,
                "session_id": session_id,
                "amount": amount,
                "return_url": return_url,
            }

        except ValidationError:
            raise

        except Exception as exc:
            raise WebpayServiceError(
                f"No se pudo crear la transacción Webpay: {str(exc)}"
            )

    @classmethod
    def confirmar_transaccion(cls, token_ws):
        """
        Confirma una transacción Webpay Plus.

        Este método debe ejecutarse cuando Webpay retorna al backend
        con el parámetro token_ws.
        """

        token_ws = cls._validar_texto_requerido(token_ws, "token_ws")

        try:
            tx = cls._get_transaction()
            response = tx.commit(token_ws)

            return {
                "token_ws": token_ws,
                "response_code": response.get("response_code"),
                "status": response.get("status"),
                "buy_order": response.get("buy_order"),
                "session_id": response.get("session_id"),
                "amount": response.get("amount"),
                "authorization_code": response.get("authorization_code"),
                "payment_type_code": response.get("payment_type_code"),
                "installments_number": response.get("installments_number"),
                "card_detail": response.get("card_detail"),
                "transaction_date": response.get("transaction_date"),
                "raw": response,
                "aprobada": cls.es_transaccion_aprobada(response),
            }

        except ValidationError:
            raise

        except Exception as exc:
            raise WebpayServiceError(
                f"No se pudo confirmar la transacción Webpay: {str(exc)}"
            )

    @classmethod
    def consultar_estado(cls, token_ws):
        """
        Consulta el estado de una transacción Webpay Plus.
        """

        token_ws = cls._validar_texto_requerido(token_ws, "token_ws")

        try:
            tx = cls._get_transaction()
            response = tx.status(token_ws)

            return {
                "token_ws": token_ws,
                "response_code": response.get("response_code"),
                "status": response.get("status"),
                "buy_order": response.get("buy_order"),
                "session_id": response.get("session_id"),
                "amount": response.get("amount"),
                "authorization_code": response.get("authorization_code"),
                "payment_type_code": response.get("payment_type_code"),
                "installments_number": response.get("installments_number"),
                "card_detail": response.get("card_detail"),
                "transaction_date": response.get("transaction_date"),
                "raw": response,
                "aprobada": cls.es_transaccion_aprobada(response),
            }

        except ValidationError:
            raise

        except Exception as exc:
            raise WebpayServiceError(
                f"No se pudo consultar el estado de la transacción Webpay: {str(exc)}"
            )

    @staticmethod
    def es_transaccion_aprobada(response):
        """
        En Webpay Plus normalmente una transacción aprobada viene con:
        - status = AUTHORIZED
        - response_code = 0
        """

        if not response:
            return False

        status = response.get("status")
        response_code = response.get("response_code")

        return status == "AUTHORIZED" and response_code == 0