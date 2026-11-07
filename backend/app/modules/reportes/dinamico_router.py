"""
P11 - Reportes / CU-27 Generar reporte con IA por texto o voz  |  capa: router

Dos pasos, como el pedido por voz del 1er parcial:

1. `POST /reportes/ia/consulta` con la frase (escrita o dictada): devuelve qué
   se entendió, la tabla, el gráfico y una lectura en castellano.
2. `POST /reportes/ia/exportar.{pdf|xlsx}` con la especificación que devolvió
   el paso 1: vuelve a correrla y entrega el archivo. Se re-ejecuta en vez de
   guardar el resultado: el archivo tiene los datos de ESE momento y no hay
   estado que limpiar.

QUIÉN: ADMINISTRADOR y ENCARGADO; el encargado, solo su sucursal (se le
impone, no se le pregunta). Plan: función `reportes_ia` y su cupo mensual,
que se descuenta solo cuando el pedido se entendió y se generó.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from pydantic import BaseModel, Field

from app.core import tiempo
from app.core.dependencies import (
    DbSession,
    Usuario,
    requiere_cupo,
    requiere_funcion,
    requiere_roles,
)
from app.modules.plataforma import verificador
from app.modules.reportes import dinamico, interprete_reglas
from app.modules.reportes.exportador import FORMATOS, Tabla

_log = logging.getLogger("violetboutique.reportes_ia")

router = APIRouter(
    prefix="/reportes/ia",
    tags=["CU-27 · Generar reporte con IA por texto o voz"],
    dependencies=[
        Depends(requiere_roles("ADMINISTRADOR", "ENCARGADO")),
        Depends(requiere_funcion("reportes_ia")),
    ],
)

EJEMPLOS = [
    "Mostrame las ventas de septiembre agrupadas por sucursal",
    "¿Cuáles fueron los diez productos más vendidos este mes?",
    "Generá un gráfico de ventas por semana",
    "Compará las ventas de las sucursales durante los últimos tres meses",
    "Mostrame los productos con menor existencia",
    "¿Qué categorías generaron mayores ingresos este mes?",
    "Devoluciones del mes pasado por producto",
]


class ConsultaIn(BaseModel):
    texto: str = Field(min_length=2, max_length=500)


class EspecificacionIn(BaseModel):
    """Lo que devolvió `/consulta`, tal cual. Se vuelve a validar entero."""

    medida: str
    agrupar: list[str] = []
    filtros: dict[str, object] = {}
    desde: str | None = None
    hasta: str | None = None
    orden: str = "desc"
    limite: int | None = None
    grafico: str = "barras"
    resumen: str = ""


class ResultadoOut(BaseModel):
    entendido: bool
    #: `ia` si lo interpretó el modelo; `reglas` si fue el intérprete de
    #: respaldo porque el modelo no estaba o no contestó.
    interprete: str | None = None
    resumen: str | None = None
    motivo: str | None = None
    ejemplos: list[str] = []

    titulo: str | None = None
    subtitulos: list[str] = []
    encabezados: list[str] = []
    filas: list[list[object]] = []
    total: list[object] | None = None
    grafico: dict | None = None
    narrativa: str | None = None
    especificacion: dict | None = None


def _sucursal_forzada(usuario) -> int | None:
    if usuario.rol == "ADMINISTRADOR":
        return None
    if usuario.sucursal_id is None:
        raise HTTPException(
            409,
            detail="Su usuario no está asignado a ninguna sucursal. Pídale al administrador que lo asigne.",
        )
    return usuario.sucursal_id


def _no_entendido(motivo: str, interprete: str | None = None) -> ResultadoOut:
    return ResultadoOut(entendido=False, motivo=motivo, ejemplos=EJEMPLOS, interprete=interprete)


@router.post(
    "/consulta",
    response_model=ResultadoOut,
    dependencies=[Depends(requiere_cupo("reportes_ia"))],
    summary="CU-27 Pedir un reporte en lenguaje natural (texto o voz transcrita)",
)
def consultar(datos: ConsultaIn, db: DbSession, usuario: Usuario):
    from app.integrations import interprete

    forzada = _sucursal_forzada(usuario)
    vocabulario = dinamico.vocabulario(db, sucursal_forzada=forzada)
    hoy = tiempo.hoy()

    crudo = None
    origen = "ia"
    try:
        crudo = interprete.interpretar_consulta(datos.texto, vocabulario, hoy)
    except interprete.ErrorDelInterprete as e:
        # Sin modelo, o el modelo no contestó: entra el de respaldo.
        _log.info("Reporte con IA por reglas (%s): %r", e, datos.texto[:80])
        origen = "reglas"
        crudo = interprete_reglas.interpretar(datos.texto, vocabulario, hoy)

    if not crudo:
        return _no_entendido(
            "No entendí qué reporte pide. Diga qué quiere ver (ventas, devoluciones, "
            "existencias o reservas), cómo agruparlo y de qué período.", origen,
        )
    if crudo.get("entendido") is False:
        return _no_entendido(
            str(crudo.get("motivo") or "El pedido es ambiguo. ¿Puede precisarlo?")[:300], origen
        )

    try:
        espec = dinamico.validar(db, crudo)
        resultado = dinamico.ejecutar(db, espec, sucursal_forzada=forzada)
    except dinamico.ErrorDeEspecificacion as e:
        return _no_entendido(str(e), origen)

    # El cupo se gasta recién con el reporte armado.
    verificador.consumir_cupo(db, "reportes_ia")
    db.commit()

    return ResultadoOut(
        entendido=True,
        interprete=origen,
        resumen=espec.resumen or resultado.titulo,
        titulo=resultado.titulo,
        subtitulos=resultado.subtitulos,
        encabezados=resultado.encabezados,
        filas=resultado.filas,
        total=resultado.total,
        grafico=resultado.grafico,
        narrativa=resultado.narrativa,
        especificacion=resultado.especificacion,
    )


@router.post(
    "/exportar.{formato}",
    summary="CU-27 Exportar a PDF o Excel el reporte que se armó",
    response_class=Response,
)
def exportar(
    formato: Annotated[str, Path(pattern="^(pdf|xlsx)$")],
    datos: EspecificacionIn,
    db: DbSession,
    usuario: Usuario,
):
    forzada = _sucursal_forzada(usuario)
    try:
        espec = dinamico.validar(db, datos.model_dump())
        resultado = dinamico.ejecutar(db, espec, sucursal_forzada=forzada)
    except dinamico.ErrorDeEspecificacion as e:
        raise HTTPException(400, detail=str(e)) from e

    tabla = Tabla(
        titulo=resultado.titulo,
        encabezados=resultado.encabezados,
        filas=resultado.filas,
        subtitulos=resultado.subtitulos + [resultado.narrativa],
        total=resultado.total,
    )
    tipo_mime, extension, convertir = FORMATOS[formato]
    nombre = f"reporte-ia-{tiempo.hoy().isoformat()}.{extension}"
    return Response(
        content=convertir(tabla),
        media_type=tipo_mime,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
