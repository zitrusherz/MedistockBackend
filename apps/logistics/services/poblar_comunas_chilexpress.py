import os
import sys
import django
import time
# 1. Configuración del entorno de Django
# Esto es necesario para poder usar los modelos del ORM fuera de una vista o comando habitual.
# Obtén la ruta del directorio principal del proyecto (donde está manage.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# IMPORTANTE: Cambia 'medistock.settings' por el nombre real de tu carpeta de settings.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medistockbackend.settings")
django.setup()

# 2. Importaciones de modelos y servicio
# IMPORTANTE: Cambia 'apps.core.models' por la ruta real donde están tus modelos
from apps.locations.models import Comuna, Region, ComunaChilexpress
from chilexpress import ChilexpressService


def normalizar_texto(texto):
    """Quita tildes, espacios extra y pasa a mayúsculas"""
    if not texto:
        return ""
    import unicodedata
    texto = str(texto).upper().strip()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto


def poblar_coberturas():
    service = ChilexpressService()

    # Obtenemos las regiones mapeadas
    regiones = Region.objects.exclude(chilexpress_region_id__isnull=True)

    print("Iniciando la extracción de coberturas de Chilexpress...\n")

    for region in regiones:
        region_code = region.chilexpress_region_id
        print(f"\nConsultando región: {region.nombre} (Código: {region_code})")

        try:
            # type=0 trae tanto comunas como sectores
            data = service.obtener_cobertura_por_region(region_code, tipo=0, usar_cache=False)
            areas = data.get("coverageAreas", [])

            for area in areas:
                county_code = area.get("countyCode")
                county_name = area.get("countyName")
                coverage_name = area.get("coverageName")

                comunas_bd = Comuna.objects.filter(region=region)
                comuna_match = None

                # Normalizamos el nombre que viene de Chilexpress
                chilexpress_normalizado = normalizar_texto(county_name).replace("Ñ", "N")

                for c in comunas_bd:
                    # 1. Prioridad: Revisar si existe 'nombre_alt' y si coincide
                    # (Usamos try/except o getattr por si acaso el campo no estuviera bien migrado)
                    nombre_alt = getattr(c, 'nombre_alt', None)
                    if nombre_alt:
                        alt_normalizado = normalizar_texto(nombre_alt).replace("Ñ", "N")
                        if alt_normalizado == chilexpress_normalizado:
                            comuna_match = c
                            break  # Encontramos match exacto con el alternativo

                    # 2. Secundario: Si no tiene nombre_alt o no coincide, probamos con el nombre original
                    nombre_normalizado = normalizar_texto(c.nombre).replace("Ñ", "N")
                    if nombre_normalizado == chilexpress_normalizado:
                        comuna_match = c
                        break  # Encontramos match con el nombre regular

                if not comuna_match:
                    print(f"  [⚠️] NO ENCONTRADA: '{county_name}' (Cobertura: {coverage_name}).")
                    continue

                # Actualizar o Crear
                cobertura, created = ComunaChilexpress.objects.update_or_create(
                    county_code=county_code,
                    defaults={
                        'comuna': comuna_match,
                        'county_name': county_name,
                        'coverage_name': coverage_name,
                        # No pisamos 'retorna_respuesta' por si luego lo cambias.
                    }
                )

                estado = "CREADA" if created else "ACTUALIZADA"
                print(
                    f"  - {estado}: {coverage_name} ({county_code}) -> Mapeada a ID {comuna_match.id} ({comuna_match.nombre})")

        except Exception as e:
            print(f"  [❌] Error al procesar la región {region_code}: {str(e)}")

    print("\n¡Proceso finalizado!")


def validar_coberturas_cotizacion():
    service = ChilexpressService()

    # Obtenemos todas las coberturas.
    # Podrías filtrar por .filter(retorna_respuesta=False) si solo quieres
    # evaluar las que fallaron antes, pero evaluar todas asegura que la BD
    # esté 100% sincronizada con la realidad actual de Chilexpress.
    coberturas = ComunaChilexpress.objects.filter(retorna_respuesta = False)
    total = coberturas.count()
    if total == 0:
        print("Todas las coberturas ya están validadas (retorna_respuesta=True). No hay nada que procesar.")
        return
    print(f"Iniciando validación de {total} coberturas de Chilexpress...\n")

    coberturas_validas = 0
    coberturas_invalidas = 0



    for i, cobertura in enumerate(coberturas, 1):
        destination_code = cobertura.county_code
        print(f"[{i}/{total}] Evaluando destino: {destination_code} ({cobertura.coverage_name})... ", end="")
        if destination_code != "PROV":
            payload_cotizacion = {
                "originCountyCode": "PROV",
                "destinationCountyCode": destination_code,
                "package": {
                    "weight": "16",
                    "height": "1",
                    "width": "1",
                    "length": "1"
                },
                "productType": 3,
                "contentType": 1,
                "declaredWorth": "2333",
                "deliveryTime": 0
            }
        else:
            payload_cotizacion = {
                "originCountyCode": "SANT",
                "destinationCountyCode": destination_code,
                "package": {
                    "weight": "16",
                    "height": "1",
                    "width": "1",
                    "length": "1"
                },
                "productType": 3,
                "contentType": 1,
                "declaredWorth": "2333",
                "deliveryTime": 0
            }

        es_valida = False

        try:
            # Usamos el método existente en tu servicio.
            # Ponemos guardar_log=False para no llenar tu BD de logs inútiles en este proceso masivo.
            respuesta = service.cotizar_envio(payload=payload_cotizacion, guardar_log=False)

            # Navegamos la estructura del JSON de respuesta
            data_dict = respuesta.get("data", {})
            opciones_servicio = data_dict.get("courierServiceOptions", [])

            if opciones_servicio:
                # Verificamos si al menos una opción tiene un serviceValue > 0
                for opcion in opciones_servicio:
                    service_value_str = opcion.get("serviceValue", "0")
                    try:
                        service_value = int(service_value_str)
                    except ValueError:
                        service_value = 0

                    if service_value > 0:
                        es_valida = True
                        break  # Ya confirmamos que es válida, no necesitamos seguir mirando opciones

        except Exception as e:
            # Capturamos excepciones de requests (ej. 400 Bad Request, 500)
            # Chilexpress a veces devuelve un error HTTP si el countyCode no admite envíos
            pass

        # Actualizamos la base de datos según el resultado
        if es_valida:
            print("✅ VÁLIDA (Retorna opciones de precio)")
            cobertura.retorna_respuesta = True
            coberturas_validas += 1
        else:
            print("❌ INVÁLIDA (Sin opciones de precio o error)")
            cobertura.retorna_respuesta = False
            coberturas_invalidas += 1

        cobertura.save()

        # Pausa para no saturar la API de Chilexpress (Rate Limiting preventivo)
        # 0.2 segundos = 5 peticiones por segundo máximo.
        # Si la API te bloquea, sube este número a 0.5 o 1.0.
        time.sleep(1.0)

    print("\n" + "=" * 40)
    print("RESUMEN DE VALIDACIÓN")
    print("=" * 40)
    print(f"Total procesadas: {total}")
    print(f"Válidas (True)  : {coberturas_validas}")
    print(f"Inválidas (False): {coberturas_invalidas}")
    print("=" * 40)

poblar = False
valida_retorno = True
try:
    if poblar:
        poblar_coberturas()
    elif valida_retorno:
        validar_coberturas_cotizacion()
    else:
        print("Nada que hacer")
except Exception as e:
    print(e)