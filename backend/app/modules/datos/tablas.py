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
})

#: En la exportación (CU-39) entra casi todo; se deja afuera solo el contenido
#: cifrado de las copias, que no se lee.
FUERA_DE_LA_EXPORTACION = frozenset({"respaldo"})


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
