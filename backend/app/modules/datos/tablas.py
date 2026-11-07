"""
P18 - Datos de la empresa / CU-39 y CU-40  |  las tablas y sus valores

Lo que comparten la exportación (CU-39) y la copia de seguridad (CU-40): qué
tablas son de la empresa, en qué orden se recorren y cómo pasa cada valor a
texto y de vuelta.

Las tablas salen de `TABLAS_DE_EMPRESA`, la misma lista que recibe el RLS. Se
leen con la sesión de la petición, así que el RLS garantiza que no entra ni
una fila de otra empresa: no hay un `WHERE empresa_id` que olvidarse.
"""
from __future__ import annotations

import base64
import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Table, select
from sqlalchemy.orm import Session

from app.core.tenencia import TABLAS_DE_EMPRESA
from app.db.base import Base

#: No van en la copia ni se tocan al restaurar:
#: - lo que la plataforma le cobra a la empresa (suscripción, cupos, pagos):
#:   restaurar no puede devolverle cupo gastado ni cambiarle el plan;
#: - el historial de lo que pasó (bitácora, avisos) y el de las propias copias:
#:   una restauración no puede borrar el rastro de quién restauró (RN-19), y
#:   reponer avisos PENDIENTES volvería a mandar correos viejos.
FUERA_DE_LA_COPIA = frozenset({
    "suscripcion",
    "consumo_cupo",
    "pago_simulado",
    "bitacora",
    "notificacion",
    "respaldo",
    "restauracion",
    # CU-29: los modelos se vuelven a entrenar en segundos, y restaurar un
    # modelo serializado (joblib) desde un archivo subido sería ejecutar lo
    # que ese archivo traiga. Nunca entra ni sale por la copia.
    "modelo_analitica",
})

#: En la exportación (CU-39) entra casi todo. Se deja afuera lo que no se lee
#: o lo que es un secreto aunque sea de la propia empresa:
#: - el contenido cifrado de las copias;
#: - los dispositivos push: el endpoint y sus claves bastan para mandarle
#:   avisos a ese teléfono o navegador.
FUERA_DE_LA_EXPORTACION = frozenset({"respaldo", "suscripcion_push", "modelo_analitica"})

#: Columnas sueltas que no salen en la exportación, por tabla. El cuerpo crudo
#: de la pasarela trae datos del pago (correo, últimos dígitos, metadatos de
#: Stripe) que la tabla ya resume en sus columnas propias.
COLUMNAS_FUERA_DE_LA_EXPORTACION: dict[str, frozenset[str]] = {
    "transaccion_pasarela": frozenset({"carga_util"}),
}

#: Lo que una planilla toma como fórmula si la celda empieza con eso.
_INICIO_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def sin_formula(valor):
    """Inyección de fórmulas (CSV/Excel): un texto que empieza con `=`, `+`,
    `-` o `@` —el nombre de un cliente, una nota— se abriría como fórmula.
    Se le antepone un apóstrofo, que la planilla muestra como texto."""
    if isinstance(valor, str) and valor.startswith(_INICIO_DE_FORMULA):
        return "'" + valor
    return valor


def tablas_de_empresa(excluir: frozenset[str] = frozenset()) -> list[Table]:
    """Las tablas de empresa en orden de dependencias: primero las apuntadas.

    `sorted_tables` ordena por claves foráneas, así que insertar en este orden
    y borrar en el inverso no choca con ninguna restricción.
    """
    nombres = set(TABLAS_DE_EMPRESA) - excluir
    return [t for t in Base.metadata.sorted_tables if t.name in nombres]


def filas_de(db: Session, tabla: Table) -> list[dict]:
    clave = list(tabla.primary_key.columns)
    filas = db.execute(select(tabla).order_by(*clave)).mappings().all()
    return [dict(f) for f in filas]


# --- Valores -----------------------------------------------------------------

def a_json(valor):
    """Un valor de la base, a algo que JSON sabe escribir sin perder nada."""
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, (datetime, date, time)):
        return valor.isoformat()
    if isinstance(valor, uuid.UUID):
        return str(valor)
    if isinstance(valor, (bytes, bytearray, memoryview)):
        return {"$b64": base64.b64encode(bytes(valor)).decode()}
    return valor


def de_json(columna, valor):
    """De vuelta: el texto de la copia, al tipo de la columna."""
    if valor is None:
        return None
    if isinstance(valor, dict) and "$b64" in valor:
        return base64.b64decode(valor["$b64"])
    try:
        tipo = columna.type.python_type
    except NotImplementedError:
        return valor
    if tipo is Decimal:
        return Decimal(valor)
    if tipo is datetime:
        return datetime.fromisoformat(valor)
    if tipo is date:
        return date.fromisoformat(valor)
    if tipo is time:
        return time.fromisoformat(valor)
    if tipo is uuid.UUID:
        return uuid.UUID(valor)
    return valor


def a_celda(valor):
    """Para Excel: sin zona horaria (openpyxl no la acepta) y sin estructuras."""
    if isinstance(valor, datetime):
        return valor.replace(tzinfo=None) if valor.tzinfo else valor
    if isinstance(valor, (dict, list)):
        import json

        return json.dumps(valor, ensure_ascii=False)
    if isinstance(valor, uuid.UUID):
        return str(valor)
    if isinstance(valor, (bytes, bytearray, memoryview)):
        return f"<{len(bytes(valor))} bytes>"
    return valor
