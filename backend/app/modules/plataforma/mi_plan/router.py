"""
P12 - Plataforma SaaS / CU-04  |  capa: router

2do parcial. Caso de uso: CU-04 Consultar plan y consumo.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.plataforma.mi_plan import service
from app.modules.plataforma.mi_plan.schemas import MiPlanOut

router = APIRouter(
    prefix="/plataforma/mi-plan",
    tags=["Plataforma · Mi plan"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es administrador de una empresa."},
    },
)


@router.get("", response_model=MiPlanOut, summary="CU-04 Consultar plan y consumo")
def consultar_mi_plan(db: DbSession, usuario: Usuario) -> MiPlanOut:
    try:
        return service.consultar_mi_plan(db, usuario.empresa_id)
    except service.SinEmpresa:
        raise HTTPException(403, "Esta cuenta no pertenece a ninguna empresa.")
