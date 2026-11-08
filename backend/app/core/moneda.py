"""Los importes como los lee una persona en Bolivia: «Bs 3.600,00».

Separador de miles con punto y decimales con coma. Python formatea al revés
(`f"{x:,.2f}"` da `3,600.00`), y esa cifra llegaba tal cual al aviso de pago y
a los PDF de reportes.

`PAGO_MONEDA` (config) NO tiene nada que ver con esto: es la moneda en la que
se le cobra a Stripe en modo de prueba. Lo que ve el cliente es siempre en Bs.
"""

from __future__ import annotations

from decimal import Decimal


def numero(valor: Decimal | float | int, decimales: int = 2) -> str:
    """`2732.5` -> `2.732,50`."""
    if not isinstance(valor, Decimal):
        valor = float(valor)
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def bs(valor: Decimal | float | int) -> str:
    """`3600` -> `Bs 3.600,00`."""
    return f"Bs {numero(valor)}"
