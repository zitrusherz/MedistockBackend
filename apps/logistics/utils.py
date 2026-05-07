import math
from py3dbp import Packer, Bin, Item


# =============================================================================
# Conversiones de unidades
# =============================================================================

def mg_a_kg(miligramos: int) -> str:
    if not miligramos or miligramos <= 0:
        return "0.01"
    kg_redondeado = math.ceil((miligramos / 1_000_000) * 100) / 100
    return f"{max(kg_redondeado, 0.01):.2f}"


def mm_a_cm(milimetros: int) -> str:
    if not milimetros or milimetros <= 0:
        return "1.0"
    return f"{milimetros / 10:.1f}"


def dimensiones_a_chilexpress(peso_mg: int, largo_mm: int, ancho_mm: int, alto_mm: int) -> dict:
    return {
        "weight": mg_a_kg(peso_mg),
        "height": mm_a_cm(alto_mm),
        "width":  mm_a_cm(ancho_mm),
        "length": mm_a_cm(largo_mm),
    }


# =============================================================================
# Lógica de empaque en cajas
# =============================================================================

_PESO_MAX_MG_POR_VOLUMEN = [
    (8_000,   8_000_000),
    (18_564, 15_000_000),
]
_PESO_MAX_MG_DEFAULT = 25_000_000


def _peso_max_mg(volumen_ml: int) -> int:
    for limite_vol, peso_max in _PESO_MAX_MG_POR_VOLUMEN:
        if volumen_ml <= limite_vol:
            return peso_max
    return _PESO_MAX_MG_DEFAULT


def calcular_caja_optima(productos: list, cajas: list, holgura_mm: int = 10) -> list:
    """
    Determina la combinación mínima de cajas necesarias para empacar todos los productos.

    :param productos: Lista de dicts. Cada uno debe tener:
        - id (str o int): identificador único del ítem
        - largo, ancho, alto (int): dimensiones en mm
        - peso (int): en mg
        Si un producto tiene cantidad > 1, debe venir ya expandido con ids únicos.

    :param cajas: Lista de dicts (modelos Producto de tipo caja). Cada uno debe tener:
        - nombre (str)
        - largo_mm, ancho_mm, alto_mm (int)
        - volumen_ml (int)

    :param holgura_mm: Margen interior a descontar de cada dimensión de la caja.

    :return: Lista de dicts: [{"caja": "Caja S", "productos_dentro": ["det-001", ...]}, ...]

    :raises ValueError: Si un producto no cabe en ninguna caja o no se proporcionan cajas.
    """
    if not productos:
        return []
    if not cajas:
        raise ValueError("No hay cajas disponibles para empacar los productos.")

    cajas_ordenadas = sorted(cajas, key=lambda c: c["volumen_ml"])
    reduccion = holgura_mm * 2
    pendientes = list(productos)
    resultado = []

    while pendientes:
        caja_elegida = None
        items_dentro = []
        items_fuera = []

        # Paso 1: buscar la caja más pequeña que contenga todos los pendientes
        for caja in cajas_ordenadas:
            largo_util = caja["largo_mm"] - reduccion
            ancho_util = caja["ancho_mm"] - reduccion
            alto_util  = caja["alto_mm"]  - reduccion

            if largo_util <= 0 or ancho_util <= 0 or alto_util <= 0:
                continue

            packer = Packer()
            packer.add_bin(Bin(
                caja["nombre"],
                largo_util, ancho_util, alto_util,
                _peso_max_mg(caja["volumen_ml"]),
            ))
            for prod in pendientes:
                packer.add_item(Item(str(prod["id"]), prod["largo_mm"], prod["ancho_mm"], prod["alto_mm"], prod["peso_mg"]))

            packer.pack()
            bin_resultado = packer.bins[0]

            if not bin_resultado.unfitted_items:
                caja_elegida = caja["nombre"]
                items_dentro = [item.name for item in bin_resultado.items]
                items_fuera  = []
                break

        # Paso 2: si ninguna caja alcanza, usar la más grande y dejar sobrantes para siguiente vuelta
        if caja_elegida is None:
            caja_grande = cajas_ordenadas[-1]
            largo_util = caja_grande["largo_mm"] - reduccion
            ancho_util = caja_grande["ancho_mm"] - reduccion
            alto_util  = caja_grande["alto_mm"]  - reduccion

            packer = Packer()
            packer.add_bin(Bin(
                caja_grande["nombre"],
                largo_util, ancho_util, alto_util,
                _peso_max_mg(caja_grande["volumen_ml"]),
            ))
            for prod in pendientes:
                packer.add_item(Item(str(prod["id"]), prod["largo_mm"], prod["ancho_mm"], prod["alto_mm"], prod["peso_mg"]))

            packer.pack()
            bin_resultado = packer.bins[0]

            if not bin_resultado.items:
                ids_no_caben = [item.name for item in bin_resultado.unfitted_items]
                raise ValueError(
                    f"Los siguientes productos no caben en ninguna caja disponible "
                    f"(holgura={holgura_mm}mm): {ids_no_caben}"
                )

            caja_elegida = caja_grande["nombre"]
            items_dentro = [item.name for item in bin_resultado.items]
            items_fuera  = [item.name for item in bin_resultado.unfitted_items]

        resultado.append({"caja": caja_elegida, "productos_dentro": items_dentro})
        pendientes = [p for p in pendientes if str(p["id"]) in items_fuera]

    return resultado