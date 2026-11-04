"""
P18 - Datos de la empresa / CU-39 y CU-40  |  capa: router

Todo es del ADMINISTRADOR de la empresa.
- CU-39: `/exportacion`, con la función del plan `exportar_datos` (CU-05).
- CU-40: `/respaldos`. La copia manual la limita el plan (RN-18); restaurar,
  nunca. `respaldos.gestionar` no se delega en un rol propio (CU-41): solo el
  administrador restaura (RN-19).
- La copia automática: `/mantenimiento/respaldos`, como el despacho de avisos.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Path, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.core import tiempo
from app.core.dependencies import DbSession, Usuario, requiere_funcion, requiere_roles
from app.modules.datos import exportacion, respaldos

Id = Annotated[int, Path(ge=1)]

#: Una copia más grande que esto no se acepta por la web.
TOPE_ARCHIVO = 50 * 1024 * 1024


def _traducir(e: respaldos.ErrorDeDatos) -> HTTPException:
    return HTTPException(e.codigo, detail=e.mensaje)


def _adjunto(contenido: bytes, nombre: str, tipo: str) -> Response:
    return Response(
        content=contenido,
        media_type=tipo,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


def _sello(empresa_id: int) -> str:
    return f"empresa-{empresa_id}-{tiempo.ahora().strftime('%Y%m%d-%H%M')}"


# =====================================================================
#  CU-39 · Exportar
# =====================================================================

exportacion_router = APIRouter(
    prefix="/exportacion",
    tags=["CU-39 · Exportar los datos de la empresa"],
    dependencies=[
        Depends(requiere_roles("ADMINISTRADOR")),
        Depends(requiere_funcion("exportar_datos")),
    ],
)


@exportacion_router.get("/datos.xlsx", summary="CU-39 Todos los datos en Excel")
def exportar_excel(db: DbSession, usuario: Usuario):
    """Una hoja por tabla, más una de resumen con las filas de cada una (RF-48)."""
    return _adjunto(
        exportacion.a_excel(db, usuario.empresa_id),
        f"datos-{_sello(usuario.empresa_id)}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@exportacion_router.get("/datos.zip", summary="CU-39 Todos los datos en CSV")
def exportar_csv(db: DbSession, usuario: Usuario):
    """Un ZIP con un CSV por tabla (RF-48)."""
    return _adjunto(
        exportacion.a_zip_csv(db, usuario.empresa_id),
        f"datos-{_sello(usuario.empresa_id)}.zip",
        "application/zip",
    )


# =====================================================================
#  CU-40 · Copias de seguridad
# =====================================================================

router = APIRouter(
    prefix="/respaldos",
    tags=["CU-40 · Copias de seguridad de la empresa"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
)


class CopiaOut(BaseModel):
    id: int
    tipo: str
    archivo: str
    tamano_bytes: int
    sha256: str
    filas: dict[str, int]
    creado_en: datetime
    creado_por: str | None
    descargable: bool


class RestauracionOut(BaseModel):
    id: int
    origen: str
    archivo: str
    sha256: str
    datos_del: datetime
    filas: dict[str, int]
    creado_en: datetime
    restaurado_por: str | None


class HistorialOut(BaseModel):
    plan: str | None
    intervalo_manual_horas: int | None
    retencion_automaticas: int
    proxima_manual: datetime | None
    copias: list[CopiaOut]
    restauraciones: list[RestauracionOut]


class RestauradoOut(BaseModel):
    id: int
    archivo: str
    datos_del: datetime
    filas: dict[str, int]


def _restaurado(r) -> RestauradoOut:
    return RestauradoOut(id=r.id, archivo=r.archivo, datos_del=r.datos_del, filas=r.filas)


@router.get("", response_model=HistorialOut, summary="CU-40 Historial de copias y restauraciones")
def historial(db: DbSession):
    """RF-63: cuándo, quién, tamaño y filas por tabla; y lo que permite el plan."""
    return respaldos.historial(db)


@router.post("/manual", summary="CU-40 Generar y descargar una copia")
def manual(db: DbSession, usuario: Usuario):
    """RF-60. Se descarga y no queda en el servidor (RNF17). El plan dice cada
    cuánto (RN-18): si todavía no toca, 403 `plan_limit` con la fecha."""
    archivo, nombre = respaldos.manual(db, usuario.empresa_id, usuario.id)
    return _adjunto(archivo, nombre, "application/json")


@router.get("/{respaldo_id}/descarga", summary="CU-40 Descargar una copia automática")
def descargar(respaldo_id: Id, db: DbSession):
    try:
        archivo, respaldo = respaldos.contenido_de(db, respaldo_id)
    except respaldos.ErrorDeDatos as e:
        raise _traducir(e) from e
    return _adjunto(archivo, respaldo.archivo, "application/json")


@router.post("/restaurar", response_model=RestauradoOut,
             summary="CU-40 Restaurar desde un archivo")
async def restaurar_archivo(
    db: DbSession, usuario: Usuario, archivo: Annotated[UploadFile, File()]
):
    """RF-62. Reemplaza TODOS los datos de la empresa, en una sola transacción,
    después de verificar que la copia sea de esta empresa y no esté alterada.
    El plan nunca la limita (RN-18)."""
    contenido = await archivo.read(TOPE_ARCHIVO + 1)
    if len(contenido) > TOPE_ARCHIVO:
        raise HTTPException(413, detail="La copia supera los 50 MB.")
    try:
        r = respaldos.restaurar(
            db, contenido, nombre=archivo.filename or "copia.json",
            empresa_id=usuario.empresa_id, usuario_id=usuario.id,
        )
    except respaldos.ErrorDeDatos as e:
        raise _traducir(e) from e
    return _restaurado(r)


@router.post("/{respaldo_id}/restaurar", response_model=RestauradoOut,
             summary="CU-40 Restaurar desde una copia automática")
def restaurar_guardada(respaldo_id: Id, db: DbSession, usuario: Usuario):
    try:
        r = respaldos.restaurar_copia_guardada(
            db, respaldo_id, empresa_id=usuario.empresa_id, usuario_id=usuario.id
        )
    except respaldos.ErrorDeDatos as e:
        raise _traducir(e) from e
    return _restaurado(r)


mantenimiento_router = APIRouter(
    prefix="/mantenimiento/respaldos",
    tags=["CU-40 · Copias de seguridad · Mantenimiento"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
)


@mantenimiento_router.post("", summary="CU-40 Generar la copia automática si toca")
def automatica(db: DbSession, usuario: Usuario) -> dict:
    """RF-61. Pensado para un planificador: **idempotente**. Crea la copia
    cifrada si ya pasó el intervalo del plan y conserva solo las últimas que el
    plan indica. No gasta la cuota de las manuales (RN-18)."""
    return respaldos.automatica(db, usuario.empresa_id)
