from django.core.exceptions import ValidationError


def validar_rut(value):
    """
    Validador para asegurar que el string ingresado sea un RUT chileno válido.
    Si no es válido, lanza una ValidationError de Django.
    """
    # Limpiamos el texto para la validación algorítmica
    rut_limpio = str(value).replace(".", "").replace("-", "").upper().strip()

    if len(rut_limpio) < 2:
        raise ValidationError("El RUT es demasiado corto o inválido.")

    cuerpo, dv = rut_limpio[:-1], rut_limpio[-1]

    try:
        # Algoritmo del módulo 11
        reverso = map(int, reversed(cuerpo))
        factores = [2, 3, 4, 5, 6, 7, 2, 3, 4, 5]
        suma = sum(d * f for d, f in zip(reverso, factores))
        dv_esperado = 11 - (suma % 11)

        if dv_esperado == 11:
            dv_esperado = '0'
        elif dv_esperado == 10:
            dv_esperado = 'K'
        else:
            dv_esperado = str(dv_esperado)

        if dv != dv_esperado:
            raise ValidationError("El dígito verificador del RUT no es válido.")

    except ValueError:
        raise ValidationError("El RUT contiene caracteres no permitidos.")