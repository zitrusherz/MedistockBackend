import json
import os
import requests
from django.conf import settings

# ChilexpressApiLog se importa solo si está disponible, para no romper
# si alguien usa el service antes de correr las migraciones
try:
    from apps.logistics.models import ChilexpressApiLog
    _LOG_MODEL_AVAILABLE = True
except ImportError:
    _LOG_MODEL_AVAILABLE = False

# Directorio donde se guardan datos estáticos de cobertura
STATIC_DATA_DIR = os.path.join(os.path.dirname(__file__), "static_data")


class ChilexpressService:
    """
    Service para interactuar con la API de Chilexpress.

    Flujo principal para crear un envío:
        1. obtener_cobertura_por_region() → obtener códigos de cobertura (ej. "STGO", "PROV")
           └─ usa caché local en static_data/ para no repetir llamadas
        2. cotizar_envio() → obtener serviceDeliveryCode
        3. crear_orden_transporte() → generar OT y etiqueta

    Logging:
        Por defecto el log NO se guarda. Pasa guardar_log=True en los métodos
        que te interesa trazar (típicamente: cotizar_envio, crear_orden_transporte,
        consultar_tracking).
    """

    def __init__(self):
        self.base_url = settings.CHILEXPRESS_BASE_URL
        self.api_key_cobertura = settings.CHILEXPRESS_API_KEY_COBERTURA
        self.api_key_cotizador = settings.CHILEXPRESS_API_KEY_COTIZADOR
        self.api_key_ot = settings.CHILEXPRESS_API_KEY_OT
        self.tcc = settings.CHILEXPRESS_TCC
        self.api_version = settings.CHILEXPRESS_API_VERSION

    # -------------------------------------------------------------------------
    # Helpers internos
    # -------------------------------------------------------------------------

    def _headers(self, api_key: str) -> dict:
        return {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Ocp-Apim-Subscription-Key": api_key,
        }

    def _guardar_log(self, method, endpoint, request_payload=None,
                     response_payload=None, status_code=None,
                     success=False, error_message=None):
        if not _LOG_MODEL_AVAILABLE:
            return
        ChilexpressApiLog.objects.create(
            method=method,
            endpoint=endpoint,
            request_payload=request_payload,
            response_payload=response_payload,
            status_code=status_code,
            success=success,
            error_message=error_message,
        )

    def _get(self, url: str, api_key: str, params: dict = None, guardar_log: bool = False) -> dict:
        response = None
        try:
            response = requests.get(url, headers=self._headers(api_key), params=params)
            response.raise_for_status()
            data = response.json()
            if guardar_log:
                self._guardar_log("GET", url, request_payload=params,
                                  response_payload=data, status_code=response.status_code, success=True)
            return data
        except requests.exceptions.RequestException as e:
            status_code = response.status_code if response is not None else None
            if guardar_log:
                self._guardar_log("GET", url, request_payload=params,
                                  status_code=status_code, success=False, error_message=str(e))
            raise

    def _post(self, url: str, api_key: str, payload: dict, guardar_log: bool = False) -> dict:
        response = None
        try:
            response = requests.post(url, json=payload, headers=self._headers(api_key))
            response.raise_for_status()
            data = response.json()
            if guardar_log:
                self._guardar_log("POST", url, request_payload=payload,
                                  response_payload=data, status_code=response.status_code, success=True)
            return data
        except requests.exceptions.RequestException as e:
            status_code = response.status_code if response is not None else None
            if guardar_log:
                self._guardar_log("POST", url, request_payload=payload,
                                  status_code=status_code, success=False, error_message=str(e))
            raise

    # -------------------------------------------------------------------------
    # Caché local en static_data/
    # Los datos de cobertura (regiones, comunas) cambian rarísimo.
    # Se guardan en JSON para no llamar a Chilexpress en cada request.
    # -------------------------------------------------------------------------

    def _ruta_cache(self, nombre_archivo: str) -> str:
        os.makedirs(STATIC_DATA_DIR, exist_ok=True)
        return os.path.join(STATIC_DATA_DIR, nombre_archivo)

    def _leer_cache(self, nombre_archivo: str):
        """Retorna el contenido del archivo JSON o None si no existe."""
        ruta = self._ruta_cache(nombre_archivo)
        if os.path.exists(ruta):
            with open(ruta, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _escribir_cache(self, nombre_archivo: str, data: dict):
        ruta = self._ruta_cache(nombre_archivo)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # -------------------------------------------------------------------------
    # Cobertura geográfica — con caché
    # -------------------------------------------------------------------------

    def obtener_regiones(self, usar_cache: bool = True) -> dict:
        """
        Retorna las regiones con cobertura Chilexpress.
        Se cachea en static_data/regiones.json porque cambia muy poco.

        :param usar_cache: Si True, lee el JSON local antes de llamar a la API.
                           Pasa False para forzar actualización del caché.
        """
        nombre_cache = "regiones.json"

        if usar_cache:
            cached = self._leer_cache(nombre_cache)
            if cached:
                return cached

        url = f"{self.base_url}/georeference/api/v{self.api_version}/georeference/regions"
        # Este endpoint no requiere API key
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        self._escribir_cache(nombre_cache, data)
        return data

    def obtener_cobertura_por_region(self, codigo_region: str, tipo: int = 1,
                                     usar_cache: bool = True) -> dict:
        """
        Retorna comunas (tipo=1) o sectores (tipo=2) para una región.
        Se cachea en static_data/comunas_{codigo_region}.json

        :param codigo_region: ID de región de Chilexpress (ej. "13" para RM)
        :param tipo: 0=Todas, 1=Comunas, 2=Sectores
        :param usar_cache: Si True, usa archivo local. False forza actualización.
        :return: Dict con lista coverageAreas. Cada ítem tiene 'countyCode' y 'countyName'.

        Uso típico:
            data = service.obtener_cobertura_por_region("13")
            areas = data["coverageAreas"]
            # areas[0] → {"countyCode": "STGO", "countyName": "SANTIAGO", ...}
        """
        if tipo not in [0, 1, 2]:
            raise ValueError("El parámetro 'tipo' debe ser 0, 1 o 2.")

        nombre_cache = f"comunas_{codigo_region}.json"

        if usar_cache:
            cached = self._leer_cache(nombre_cache)
            if cached:
                return cached

        url = f"{self.base_url}/georeference/api/v{self.api_version}/coverage-areas"
        data = self._get(url, self.api_key_cobertura,
                         params={"RegionCode": codigo_region, "type": tipo})

        self._escribir_cache(nombre_cache, data)
        return data

    def buscar_coverage_code(self, nombre_comuna: str, codigo_region: str) -> str | None:
        """
        Busca el countyCode de Chilexpress a partir del nombre de una comuna.
        Útil para poblar el campo chilexpress_coverage_code en tu modelo Comuna.

        :param nombre_comuna: Nombre como aparece en tu BD (ej. "Providencia")
        :param codigo_region: ID de región Chilexpress (ej. "13")
        :return: Código de cobertura (ej. "PROV") o None si no se encuentra.
        """
        data = self.obtener_cobertura_por_region(codigo_region)
        areas = data.get("coverageAreas", [])
        nombre_buscar = nombre_comuna.upper().strip()
        for area in areas:
            if area.get("countyName", "").upper().strip() == nombre_buscar:
                return area.get("countyCode")
        return None

    # -------------------------------------------------------------------------
    # Cotización
    # -------------------------------------------------------------------------

    def cotizar_envio(self, payload: dict, guardar_log: bool = False) -> dict:
        """
        Cotiza un envío. El serviceDeliveryCode del resultado es REQUERIDO
        para crear la OT.

        :param payload: {
            "originCountyCode": "STGO",
            "destinationCountyCode": "PROV",
            "package": {"weight": "2", "height": "10", "width": "15", "length": "20"},
            "productType": 3,
            "contentType": 1,
            "declaredWorth": "5000",
            "deliveryTime": 0
        }
        :param guardar_log: Si True, guarda la llamada en ChilexpressApiLog.
        :return: Dict con los servicios disponibles y sus precios.
        """
        self._validar_payload_cotizacion(payload)
        url = f"{self.base_url}/rating/api/v{self.api_version}/rates/courier"
        return self._post(url, self.api_key_cotizador, payload, guardar_log=guardar_log)

    def cotizar_envio_empresa(self, payload: dict, guardar_log: bool = False) -> dict:
        """Igual que cotizar_envio pero con TCC para tarifas corporativas."""
        self._validar_payload_cotizacion(payload)
        payload_empresa = {**payload, "customerCardNumber": self.tcc}
        url = f"{self.base_url}/rating/api/v{self.api_version}/rates/courier"
        return self._post(url, self.api_key_cotizador, payload_empresa, guardar_log=guardar_log)

    def _validar_payload_cotizacion(self, payload: dict):
        keys_requeridas = {"originCountyCode", "destinationCountyCode", "package",
                           "productType", "contentType", "declaredWorth", "deliveryTime"}
        keys_package = {"weight", "height", "width", "length"}

        faltantes = keys_requeridas - payload.keys()
        if faltantes:
            raise ValueError(f"Faltan campos requeridos en cotización: {faltantes}")

        package = payload.get("package", {})
        faltantes_pkg = keys_package - package.keys()
        if faltantes_pkg:
            raise ValueError(f"Faltan campos en package: {faltantes_pkg}")

        if payload["productType"] not in [1, 3]:
            raise ValueError("productType debe ser 1 (Documento) o 3 (Encomienda).")
        if payload["deliveryTime"] not in [0, 1, 2, 3]:
            raise ValueError("deliveryTime debe ser 0, 1, 2 o 3.")

    # -------------------------------------------------------------------------
    # Crear orden de transporte
    # -------------------------------------------------------------------------

    def crear_orden_transporte(
        self,
        codigo_cobertura_origen: str,
        direccion_destino: dict,
        contacto_remitente: dict,
        contacto_destinatario: dict,
        paquete: dict,
        direccion_devolucion: dict = None,
        label_type: int = 2,
        guardar_log: bool = True,  # Para OTs sí conviene loguear por defecto
    ) -> dict:
        """
        Crea una Orden de Transporte (OT) en Chilexpress.

        :param codigo_cobertura_origen: Código de la sucursal que despacha (ej. "PUDA")
        :param direccion_destino: {
            "countyCoverageCode": "PROV",
            "streetName": "Avenida Manuel Montt",
            "streetNumber": "427",          # opcional
            "supplement": "Dpto 5",         # opcional
            "deliveryOnCommercialOffice": False,
            "commercialOfficeId": None,      # requerido si deliveryOnCommercialOffice=True
            "observation": ""               # opcional
        }
        :param contacto_remitente: {"name": ..., "phoneNumber": ..., "mail": ...}
        :param contacto_destinatario: {"name": ..., "phoneNumber": ..., "mail": ...}
        :param paquete: {
            "weight": "2",
            "height": "10",
            "width": "15",
            "length": "20",
            "serviceDeliveryCode": "3",      # de cotizar_envio()
            "productCode": "3",
            "deliveryReference": "PED-0042",
            "groupReference": "MEDISTOCK",
            "declaredValue": "50000",
            "declaredContent": "5"
        }
        :param guardar_log: True por defecto porque cada OT debe quedar registrada.
        :return: Respuesta Chilexpress con transportOrderNumber, barcode, label, etc.
        """
        self._validar_datos_orden(direccion_destino, contacto_remitente, contacto_destinatario, paquete)

        dev = direccion_devolucion or {
            "countyCoverageCode": codigo_cobertura_origen,
            "streetName": "Dirección de devolución MEDISTOCK",
            "deliveryOnCommercialOffice": False,
        }

        payload = {
            "header": {
                "customerCardNumber": self.tcc,
                "countyOfOriginCoverageCode": codigo_cobertura_origen,
                "labelType": label_type,
                "marketplaceRut": getattr(settings, "CHILEXPRESS_MARKETPLACE_RUT", "96756430"),
                "sellerRut": "DEFAULT",
            },
            "details": [{
                "addresses": [
                    {
                        "addressId": 0,
                        "countyCoverageCode": direccion_destino["countyCoverageCode"],
                        "streetName": direccion_destino["streetName"],
                        "streetNumber": direccion_destino.get("streetNumber", ""),
                        "supplement": direccion_destino.get("supplement", ""),
                        "addressType": "DEST",
                        "deliveryOnCommercialOffice": direccion_destino.get("deliveryOnCommercialOffice", False),
                        "commercialOfficeId": direccion_destino.get("commercialOfficeId"),
                        "observation": direccion_destino.get("observation", ""),
                    },
                    {
                        "addressId": 0,
                        "countyCoverageCode": dev["countyCoverageCode"],
                        "streetName": dev["streetName"],
                        "streetNumber": dev.get("streetNumber", ""),
                        "supplement": dev.get("supplement", ""),
                        "addressType": "DEV",
                        "deliveryOnCommercialOffice": dev.get("deliveryOnCommercialOffice", False),
                        "observation": dev.get("observation", ""),
                    },
                ],
                "contacts": [
                    {
                        "name": contacto_remitente["name"],
                        "phoneNumber": contacto_remitente["phoneNumber"],
                        "mail": contacto_remitente["mail"],
                        "contactType": "R",
                    },
                    {
                        "name": contacto_destinatario["name"],
                        "phoneNumber": contacto_destinatario["phoneNumber"],
                        "mail": contacto_destinatario["mail"],
                        "contactType": "D",
                    },
                ],
                "packages": [{
                    "weight": str(paquete["weight"]),
                    "height": str(paquete["height"]),
                    "width": str(paquete["width"]),
                    "length": str(paquete["length"]),
                    "serviceDeliveryCode": str(paquete["serviceDeliveryCode"]),
                    "productCode": str(paquete.get("productCode", "3")),
                    "deliveryReference": paquete["deliveryReference"],
                    "groupReference": paquete.get("groupReference", "MEDISTOCK"),
                    "declaredValue": str(paquete.get("declaredValue", "0")),
                    "declaredContent": str(paquete.get("declaredContent", "5")),
                }],
            }],
        }

        url = f"{self.base_url}/transport-orders/api/v{self.api_version}/transport-orders"
        return self._post(url, self.api_key_ot, payload, guardar_log=guardar_log)

    def _validar_datos_orden(self, direccion_destino, contacto_remitente, contacto_destinatario, paquete):
        for campo in ["countyCoverageCode", "streetName"]:
            if not direccion_destino.get(campo):
                raise ValueError(f"Campo requerido en direccion_destino: '{campo}'")
        for contacto, rol in [(contacto_remitente, "remitente"), (contacto_destinatario, "destinatario")]:
            for campo in ["name", "phoneNumber", "mail"]:
                if not contacto.get(campo):
                    raise ValueError(f"Campo requerido en contacto_{rol}: '{campo}'")
        for campo in ["weight", "height", "width", "length", "serviceDeliveryCode", "deliveryReference"]:
            if paquete.get(campo) is None:
                raise ValueError(f"Campo requerido en paquete: '{campo}'")

    # -------------------------------------------------------------------------
    # Tracking
    # -------------------------------------------------------------------------

    def consultar_tracking(self, num_orden_transporte: int, referencia: str,
                           rut: str, mostrar_todos_los_eventos: bool = False,
                           guardar_log: bool = False) -> dict:
        """
        Consulta el estado de una OT.
        No se loguea por defecto porque puede llamarse frecuentemente
        desde el frontend para mostrar el estado del envío.
        """
        if not all([num_orden_transporte, referencia, rut]):
            raise ValueError("num_orden_transporte, referencia y rut son requeridos.")

        url = f"{self.base_url}/transport-orders/api/v{self.api_version}/tracking"
        payload = {
            "reference": referencia,
            "transportOrderNumber": num_orden_transporte,
            "rut": rut,
            "showTrackingEvents": 1 if mostrar_todos_los_eventos else 0,
        }
        return self._post(url, self.api_key_ot, payload, guardar_log=guardar_log)

    # -------------------------------------------------------------------------
    # Certificados
    # -------------------------------------------------------------------------

    def generar_certificado(self, guardar_log: bool = False) -> dict:
        url = f"{self.base_url}/transport-orders/api/v{self.api_version}/transport-order-certificates"
        return self._get(url, self.api_key_ot,
                         params={"customerCardNumber": self.tcc}, guardar_log=guardar_log)

    def cerrar_certificado(self, num_certificado: int, tipo_certificado: int,
                           num_retiro: int, guardar_log: bool = True) -> dict:
        url = f"{self.base_url}/transport-orders/api/v{self.api_version}/transport-order-certificates"
        payload = {
            "certificateNumber": num_certificado,
            "certificateType": tipo_certificado,
            "dropNumber": num_retiro,
        }
        response = None
        try:
            response = requests.put(url, json=payload, headers=self._headers(self.api_key_ot))
            response.raise_for_status()
            data = response.json()
            if guardar_log:
                self._guardar_log("PUT", url, request_payload=payload,
                                  response_payload=data, status_code=response.status_code, success=True)
            return data
        except requests.exceptions.RequestException as e:
            if guardar_log:
                self._guardar_log("PUT", url, request_payload=payload,
                                  status_code=response.status_code if response else None,
                                  success=False, error_message=str(e))
            raise