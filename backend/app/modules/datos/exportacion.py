"""
P18 - Datos de la empresa / CU-39 Exportar los datos de la empresa (RF-48)

Todos los datos de la empresa, para LEERLOS: un Excel con una hoja por tabla,
o un ZIP con un CSV por tabla. No es la copia de seguridad (CU-40): esa es
para restaurar y va en JSON firmado.

Es una función del plan (`exportar_datos`, CU-05): la ruta la pide con
`requiere_funcion`.

Del personal sale lo que se ve en la pantalla de usuarios, nunca el hash de la
contraseña. Tampoco salen los dispositivos push ni el cuerpo crudo de la
pasarela (`tablas.FUERA_DE_LA_EXPORTACION`), y todo texto que una planilla
tomaría por fórmula sale escapado (`tablas.sin_formula`).
"""
from __future__ import annotations

import csv
import io
import json
import zipfile

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.datos import tablas
from app.modules.seguridad.models import Rol, Usuario

#: Excel no admite más de 31 caracteres en el nombre de una hoja.
_LARGO_HOJA = 31


def _personal(db: Session, empresa_id: int) -> tuple[list[str], list[list]]:
    columnas = ["id", "correo", "nombres", "apellidos", "rol", "activo", "rol_empresa_id",
                "creado_en"]
    filas = db.execute(
        select(Usuario.id, Usuario.correo, Usuario.nombres, Usuario.apellidos, Rol.nombre,
               Usuario.activo, Usuario.rol_empresa_id, Usuario.creado_en)
        .join(Rol, Rol.id == Usuario.rol_id)
        .where(Usuario.empresa_id == empresa_id)
        .order_by(Usuario.id)
    ).all()
    return columnas, [list(f) for f in filas]


def _hojas(db: Session, empresa_id: int):
    """(nombre, columnas, filas) de cada tabla, en orden de dependencias."""
    columnas, filas = _personal(db, empresa_id)
    yield "personal", columnas, filas
    for tabla in tablas.tablas_de_empresa(tablas.FUERA_DE_LA_EXPORTACION):
        fuera = tablas.COLUMNAS_FUERA_DE_LA_EXPORTACION.get(tabla.name, frozenset())
        nombres = [c.name for c in tabla.columns if c.name not in fuera]
        yield tabla.name, nombres, [[f[n] for n in nombres] for f in tablas.filas_de(db, tabla)]


def a_excel(db: Session, empresa_id: int) -> bytes:
    libro = Workbook(write_only=True)
    resumen = libro.create_sheet("resumen")
    resumen.append(["tabla", "filas"])
    cuentas: list[tuple[str, int]] = []
    for nombre, columnas, filas in _hojas(db, empresa_id):
        hoja = libro.create_sheet(nombre[:_LARGO_HOJA])
        hoja.append(columnas)
        for fila in filas:
            hoja.append([tablas.sin_formula(tablas.a_celda(v)) for v in fila])
        cuentas.append((nombre, len(filas)))
    for nombre, n in cuentas:
        resumen.append([nombre, n])
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


def _texto(valor) -> str:
    if valor is None:
        return ""
    valor = tablas.a_json(valor)
    if isinstance(valor, (dict, list)):
        return tablas.sin_formula(json.dumps(valor, ensure_ascii=False))
    return tablas.sin_formula(str(valor))


def a_zip_csv(db: Session, empresa_id: int) -> bytes:
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for nombre, columnas, filas in _hojas(db, empresa_id):
            texto = io.StringIO()
            escritor = csv.writer(texto)
            escritor.writerow(columnas)
            for fila in filas:
                escritor.writerow([_texto(v) for v in fila])
            # Con BOM: Excel en español abre bien las tildes del CSV.
            zf.writestr(f"{nombre}.csv", "﻿" + texto.getvalue())
    return salida.getvalue()
