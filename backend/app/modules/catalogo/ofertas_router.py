"""
P16 - Ofertas / CU-31 y CU-32  |  capa: router

Todo es del ADMINISTRADOR de la empresa. Las ofertas manuales (RF-58) siguen
en `/catalogo/promociones`; acá están los precios mayoristas y la regla de
fuera de temporada. Las tres funciones vienen en todos los planes, así que no
pasan por `requiere_funcion` (CU-05).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.core.dependencies import DbSession, requiere_roles
from app.modules.catalogo import ofertas_service as service
from app.modules.catalogo.ofertas_schemas import (
    AplicacionOut,
    CandidataOut,
    EstadoIn,
    MayoristaCrearIn,
    MayoristaEditarIn,
    MayoristaOut,
    PaginaMayoristas,
    ReglaIn,
    ReglaOut,
)

router = APIRouter(
    prefix="/ofertas",
    tags=["CU-31 y CU-32 · Ofertas y precios mayoristas"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
)

Id = Annotated[int, Path(ge=1)]


def _traducir(e: service.ErrorDeOfertas) -> HTTPException:
    return HTTPException(e.codigo, detail=e.mensaje)


# --- CU-31 · Precios mayoristas ----------------------------------------------
@router.get("/mayoristas", response_model=PaginaMayoristas, summary="CU-31 Listar mayoristas")
def listar_mayoristas(
    db: DbSession,
    busqueda: Annotated[str | None, Query(max_length=80)] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 20,
):
    total, items = service.listar_mayoristas(
        db, busqueda=busqueda, pagina=pagina, tamano=tamano
    )
    return PaginaMayoristas(total=total, pagina=pagina, tamano=tamano, items=items)


@router.post(
    "/mayoristas",
    response_model=MayoristaOut,
    status_code=201,
    summary="CU-31 Definir un precio mayorista",
)
def crear_mayorista(datos: MayoristaCrearIn, db: DbSession):
    """«Desde N prendas de este producto, a Bs X cada una» (RF-56). Las N se
    cuentan sumando tallas y colores del mismo producto."""
    try:
        return service.crear_mayorista(db, datos)
    except service.ErrorDeOfertas as e:
        raise _traducir(e) from e


@router.patch("/mayoristas/{mayorista_id}", response_model=MayoristaOut,
              summary="CU-31 Editar un precio mayorista")
def editar_mayorista(mayorista_id: Id, datos: MayoristaEditarIn, db: DbSession):
    try:
        return service.editar_mayorista(db, mayorista_id, datos)
    except service.ErrorDeOfertas as e:
        raise _traducir(e) from e


@router.patch("/mayoristas/{mayorista_id}/estado", response_model=MayoristaOut,
              summary="CU-31 Encender o apagar un precio mayorista")
def estado_mayorista(mayorista_id: Id, datos: EstadoIn, db: DbSession):
    try:
        return service.cambiar_estado_mayorista(db, mayorista_id, datos.activo)
    except service.ErrorDeOfertas as e:
        raise _traducir(e) from e


# --- CU-32 · Fuera de temporada ----------------------------------------------
@router.get("/fuera-de-temporada/regla", response_model=ReglaOut,
            summary="CU-32 Ver el factor de fuera de temporada")
def obtener_regla(db: DbSession):
    return service.obtener_regla(db)


@router.put("/fuera-de-temporada/regla", response_model=ReglaOut,
            summary="CU-32 Guardar el factor de fuera de temporada")
def guardar_regla(datos: ReglaIn, db: DbSession):
    """Los días desde el fin de la temporada y la existencia sobrante que hacen
    que una prenda entre en oferta, y con qué porcentaje (RF-57)."""
    return service.guardar_regla(db, datos)


@router.get("/fuera-de-temporada/candidatas", response_model=list[CandidataOut],
            summary="CU-32 Qué prendas cumplen hoy el factor")
def candidatas(db: DbSession):
    """No escribe nada: es lo que haría `aplicar` hoy."""
    return service.candidatas(db)


@router.post("/fuera-de-temporada/aplicar", response_model=AplicacionOut,
             summary="CU-32 Aplicar las ofertas de fuera de temporada")
def aplicar(db: DbSession):
    """Crea la oferta automática de cada prenda que cumple el factor y cierra
    las que dejaron de cumplirlo. **Idempotente**: pensado para un planificador
    (una tarea de Railway, un cron) y para dispararlo a mano en la defensa. Una
    oferta automática que el Administrador apagó no se vuelve a crear (RN-16)."""
    return service.aplicar(db)
