"""
P19 - Analítica con ML / CU-29 y CU-30  |  capa: router

Todo es del ADMINISTRADOR y pide la función del plan `analitica_ml` (CU-05):
sin ella responde 403 con `plan_limit` y la pantalla muestra el candado.

- CU-29: `POST /analitica/entrenamientos` entrena los dos modelos.
- CU-30: `GET /analitica/resumen` es el dashboard; `/clientes` clasifica a los
  clientes de hoy con el modelo guardado; `/reporte.pdf|.xlsx` es el reporte
  inteligente.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from app.core import tiempo
from app.core.dependencies import DbSession, Usuario, requiere_funcion, requiere_roles
from app.modules.analitica import service
from app.modules.analitica.schemas import (
    ClienteSegmentoOut,
    EntrenarIn,
    HistorialOut,
    ResumenOut,
)
from app.modules.reportes import exportador

router = APIRouter(
    prefix="/analitica",
    tags=["CU-29 y CU-30 · Analítica con ML"],
    dependencies=[
        Depends(requiere_roles("ADMINISTRADOR")),
        Depends(requiere_funcion("analitica_ml")),
    ],
)


def _traducir(e: service.ErrorDeAnalitica) -> HTTPException:
    return HTTPException(e.codigo, detail=e.mensaje)


@router.post(
    "/entrenamientos",
    response_model=ResumenOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-29 Entrenar los modelos de analítica",
)
def entrenar(db: DbSession, usuario: Usuario, datos: EntrenarIn | None = None):
    """Demanda semanal (supervisado) y segmentos de clientes (no supervisado),
    con datos reales de la empresa completados con sintéticos."""
    return service.entrenar(db, usuario.id, (datos or EntrenarIn()).semilla)


@router.get("/entrenamientos", response_model=list[HistorialOut],
            summary="CU-29 Historial de entrenamientos")
def historial(db: DbSession):
    return service.historial(db)


@router.get("/resumen", response_model=ResumenOut, summary="CU-30 El dashboard analítico")
def resumen(db: DbSession):
    return service.resumen(db)


@router.get("/clientes", response_model=list[ClienteSegmentoOut],
            summary="CU-30 Los clientes reales en su segmento")
def clientes(db: DbSession):
    try:
        return service.clientes_por_segmento(db)
    except service.ErrorDeAnalitica as e:
        raise _traducir(e) from e


def _adjunto(contenido: bytes, extension: str, tipo: str) -> Response:
    nombre = f"analitica-{tiempo.ahora().strftime('%Y%m%d-%H%M')}.{extension}"
    return Response(content=contenido, media_type=tipo,
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


@router.get("/reporte.pdf", summary="CU-30 Reporte inteligente en PDF")
def reporte_pdf(db: DbSession):
    try:
        return _adjunto(exportador.a_pdf(service.reporte(db)), "pdf", "application/pdf")
    except service.ErrorDeAnalitica as e:
        raise _traducir(e) from e


@router.get("/reporte.xlsx", summary="CU-30 Reporte inteligente en Excel")
def reporte_excel(db: DbSession):
    try:
        return _adjunto(
            exportador.a_excel(service.reporte(db)), "xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except service.ErrorDeAnalitica as e:
        raise _traducir(e) from e
