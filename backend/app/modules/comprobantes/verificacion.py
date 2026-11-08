"""
P16 - Mis comprobantes / CU-46  |  el token de verificación y el código QR

EL TOKEN NO SE GUARDA: SE FIRMA
-------------------------------
El QR de un comprobante lleva a una página pública de verificación. Para que
nadie pueda recorrer los comprobantes de la tienda cambiando un número en la
URL, el enlace lleva un token **no adivinable**.

Se podría guardar un token aleatorio por comprobante, pero eso pide una
columna nueva (una migración) y un relleno para los miles de recibos que ya
existen. En cambio se **firma** lo que identifica al comprobante con HMAC-SHA256
y la clave del servidor:

    V1-42.Xb3k...   →  «recibo de la venta 42 de la empresa 1» + firma

Sin la clave no se puede fabricar la firma de otro comprobante (la firma tiene
128 bits), y el servidor la comprueba sin leer nada de la base. El mismo
comprobante produce siempre el mismo token: el QR impreso en el recibo y el de
la pantalla son el mismo.

LA EMPRESA VIAJA EN EL TOKEN
----------------------------
Porque la página pública no tiene sesión: con la empresa del token se fija el
contexto del RLS, y la consulta solo puede ver filas de esa empresa. Un token
de la empresa 1 jamás encuentra una venta de la 2, aunque los números coincidan.

EL QR SE DIBUJA EN EL SERVIDOR, SIN DEPENDENCIAS NUEVAS
-------------------------------------------------------
ReportLab ---que ya genera los PDF--- trae un codificador QR. Se usa su matriz
para armar un SVG compacto (un `<path>` por módulo oscuro), que la web muestra
con un `<img>` y el PDF del recibo imprime. Así no hay que sumar una librería
de QR ni a Angular ni a Flutter.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
from dataclasses import dataclass

from app.core.config import settings

#: V = recibo de una venta; D = nota de devolución.
RECIBO = "V"
NOTA = "D"

_FORMATO = re.compile(r"^([VD])(\d{1,9})-(\d{1,18})\.([A-Za-z0-9_-]{22})$")


@dataclass(frozen=True)
class Referencia:
    clase: str
    empresa_id: int
    id: int


def _firma(cuerpo: str) -> str:
    clave = f"comprobante-publico:{settings.JWT_SECRET_KEY}".encode()
    digest = hmac.new(clave, cuerpo.encode(), hashlib.sha256).digest()[:16]
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def firmar(clase: str, empresa_id: int, identificador: int) -> str:
    cuerpo = f"{clase}{int(empresa_id)}-{int(identificador)}"
    return f"{cuerpo}.{_firma(cuerpo)}"


def leer(token: str) -> Referencia | None:
    """La referencia del token, o `None` si está mal formado o la firma no da."""
    m = _FORMATO.match(token or "")
    if not m:
        return None
    cuerpo = f"{m.group(1)}{m.group(2)}-{m.group(3)}"
    if not hmac.compare_digest(_firma(cuerpo), m.group(4)):
        return None
    return Referencia(clase=m.group(1), empresa_id=int(m.group(2)), id=int(m.group(3)))


def url_publica(token: str) -> str:
    """La página de la web que verifica el comprobante. Es lo que lleva el QR."""
    return f"{settings.WEB_BASE_URL.rstrip('/')}/verificar/{token}"


# --------------------------------------------------------------------------
#  El QR
# --------------------------------------------------------------------------
def modulos(texto: str) -> list[str]:
    """La matriz del QR como filas de «1» (oscuro) y «0» (claro), sin margen."""
    from reportlab.graphics.barcode import qrencoder

    codigo = qrencoder.QRCode(None, qrencoder.QRErrorCorrectLevel.M)
    codigo.addData(texto)
    codigo.make()
    n = codigo.getModuleCount()
    return [
        "".join("1" if codigo.isDark(fila, col) else "0" for col in range(n))
        for fila in range(n)
    ]


def svg(texto: str, *, margen: int = 4) -> str:
    """El QR como SVG. Un módulo = una unidad; el tamaño lo pone quien lo muestra."""
    filas = modulos(texto)
    lado = len(filas) + 2 * margen
    trazos = []
    for y, fila in enumerate(filas):
        x = 0
        while x < len(fila):
            if fila[x] == "1":
                inicio = x
                while x < len(fila) and fila[x] == "1":
                    x += 1
                # Se juntan los módulos seguidos de la fila en un solo rectángulo.
                trazos.append(f"M{inicio + margen} {y + margen}h{x - inicio}v1h-{x - inicio}z")
            else:
                x += 1
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {lado} {lado}" '
        f'shape-rendering="crispEdges">'
        f'<rect width="{lado}" height="{lado}" fill="#fff"/>'
        f'<path fill="#2e1f28" d="{"".join(trazos)}"/></svg>'
    )
