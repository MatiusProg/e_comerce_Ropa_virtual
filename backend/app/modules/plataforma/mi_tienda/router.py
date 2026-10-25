"""
P12 - Plataforma SaaS / CU-12  |  capa: router

2do parcial. Caso de uso: CU-12 Personalizar la tienda de la empresa.
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.dependencies import DbSession, Usuario, requiere_funcion, requiere_roles
from app.modules.plataforma.mi_tienda import service
from app.modules.plataforma.mi_tienda.schemas import ColoresIn, MarcaOut, MarcaTiendaOut

router = APIRouter(
    prefix="/plataforma/mi-tienda",
    tags=["Plataforma · Mi tienda"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "No es administrador de una empresa, o el plan no incluye "
                             "la marca propia (plan_limit)."},
    },
)

#: Guardar exige la función del plan (1a). Ver la pantalla, no.
_CON_MARCA_PROPIA = [Depends(requiere_funcion(service.FUNCION))]

_SIN_EMPRESA = "Esta cuenta no pertenece a ninguna empresa."


@router.get("", response_model=MarcaOut, summary="CU-12 Ver la marca de la tienda")
def obtener_marca(db: DbSession, usuario: Usuario) -> MarcaOut:
    try:
        return service.obtener_marca(db, usuario.empresa_id)
    except service.SinEmpresa:
        raise HTTPException(status.HTTP_403_FORBIDDEN, _SIN_EMPRESA)


@router.put(
    "/colores",
    response_model=MarcaOut,
    summary="CU-12 Guardar los colores de la tienda",
    dependencies=_CON_MARCA_PROPIA,
)
def guardar_colores(datos: ColoresIn, db: DbSession, usuario: Usuario) -> MarcaOut:
    try:
        return service.guardar_colores(db, usuario.empresa_id, datos)
    except service.SinEmpresa:
        raise HTTPException(status.HTTP_403_FORBIDDEN, _SIN_EMPRESA)


@router.post(
    "/logo",
    response_model=MarcaOut,
    summary="CU-12 Subir el logo de la tienda",
    dependencies=_CON_MARCA_PROPIA,
    responses={422: {"description": "El archivo no es una imagen válida (4a)."}},
)
async def subir_logo(
    db: DbSession,
    usuario: Usuario,
    archivo: UploadFile = File(..., description="PNG, JPEG o WEBP, hasta 5 MB"),
) -> MarcaOut:
    contenido = await archivo.read()
    try:
        return service.guardar_logo(db, usuario.empresa_id, contenido)
    except service.SinEmpresa:
        raise HTTPException(status.HTTP_403_FORBIDDEN, _SIN_EMPRESA)
    except service.ErrorDeArchivo:
        # 4a: un solo mensaje. Para quien sube da igual si estaba vacío, era
        # enorme o no era una imagen: lo que tiene que hacer es elegir otra.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "El logo tiene que ser una imagen PNG, JPEG o WEBP de hasta 5 MB y "
            "4000 px de lado.",
        )


@router.delete(
    "/logo",
    response_model=MarcaOut,
    summary="CU-12 Quitar el logo de la tienda",
    dependencies=_CON_MARCA_PROPIA,
)
def quitar_logo(db: DbSession, usuario: Usuario) -> MarcaOut:
    try:
        return service.quitar_logo(db, usuario.empresa_id)
    except service.SinEmpresa:
        raise HTTPException(status.HTTP_403_FORBIDDEN, _SIN_EMPRESA)


#: 1.11: la marca de la tienda en línea. Pública, como el catálogo.
tienda_router = APIRouter(prefix="/tienda", tags=["Plataforma · Mi tienda"])


@tienda_router.get(
    "/marca", response_model=MarcaTiendaOut, summary="CU-12 La marca de la tienda que se mira"
)
def marca_de_la_tienda(db: DbSession) -> MarcaTiendaOut:
    return service.marca_de_la_tienda(db)
