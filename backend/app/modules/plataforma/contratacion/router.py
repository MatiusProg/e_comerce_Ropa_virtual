"""
P12 - Plataforma SaaS / CU-11  |  capa: router (FastAPI)

Contratar un plan desde la web. PÚBLICO a propósito: el actor es una empresa
interesada que todavía no tiene cuenta. Solo lee planes y ciudades, que no son
de ninguna empresa, y lo único que escribe pasa por el alta del CU-01.
"""

from typing import Annotated

from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse

from app.core.dependencies import DbSession
from app.modules.plataforma.contratacion import service
from app.modules.plataforma.contratacion.schemas import (
    CiudadPublicaOut,
    ContratacionOut,
    ContratarIn,
    PlanPublicoOut,
    SlugOut,
)

router = APIRouter(prefix="/contratar", tags=["Plataforma · Contratar un plan"])


@router.get("/planes", response_model=list[PlanPublicoOut], summary="CU-11 Planes que se ofrecen")
def listar_planes(db: DbSession) -> list[PlanPublicoOut]:
    return service.listar_planes(db)


@router.get(
    "/ciudades",
    response_model=list[CiudadPublicaOut],
    summary="CU-11 Ciudades para la sucursal principal",
)
def listar_ciudades(db: DbSession) -> list[CiudadPublicaOut]:
    return service.listar_ciudades(db)


@router.get("/slug", response_model=SlugOut, summary="CU-11 Ver si un slug está libre (5a)")
def verificar_slug(
    db: DbSession, valor: Annotated[str, Query(min_length=1, max_length=40)]
) -> SlugOut:
    return service.verificar_slug(db, valor)


def _error(codigo_http: int, mensaje: str, codigo: str, **extra) -> JSONResponse:
    return JSONResponse(
        status_code=codigo_http, content={"detail": mensaje, "codigo": codigo, **extra}
    )


@router.post(
    "",
    response_model=ContratacionOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-11 Contratar: cobra (simulado) y da de alta la empresa",
    responses={
        402: {"description": "6a: el pago simulado se rechazó; no se creó nada."},
        409: {"description": "5a: el slug está ocupado (con sugerencias) o el correo ya existe."},
        422: {"description": "El plan no se ofrece, la ciudad no existe o un dato es inválido."},
    },
)
def contratar(datos: ContratarIn, db: DbSession):
    try:
        return service.contratar(db, datos)
    except service.SlugOcupado as error:
        return _error(
            status.HTTP_409_CONFLICT,
            "Ese slug ya lo usa otra empresa. Elija otro.",
            "slug_ocupado",
            sugerencias=error.sugerencias,
        )
    except service.PagoRechazado:
        return _error(
            status.HTTP_402_PAYMENT_REQUIRED,
            "El pago fue rechazado. No se creó la empresa ni se cobró nada: intente de nuevo.",
            "pago_rechazado",
        )
    except service.CorreoYaRegistrado:
        return _error(
            status.HTTP_409_CONFLICT,
            "Ese correo ya tiene una cuenta en esta empresa.",
            "correo_repetido",
        )
    except service.PlanNoOfrecido:
        return _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Ese plan ya no se ofrece.", "plan_no_ofrecido"
        )
    except service.CiudadInexistente:
        return _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "La ciudad de la sucursal no existe.",
            "ciudad_inexistente",
        )
