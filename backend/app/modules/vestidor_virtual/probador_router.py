"""
P9 - Vestidor Virtual  |  capa: router (HTTP, validacion y autorizacion)
2do parcial, 3ra presentacion:
  CU-36 Preparar prenda para el probador     -> /catalogo/probador/...  (ADMINISTRADOR)
  CU-37 Probarse una prenda con su talla real -> /vestidor/...           (CLIENTE)
  CU-38 Generar foto realista de la prueba    -> /vestidor/sesiones/{id}/foto

DOS ROUTERS
-----------
La preparacion es del catalogo: va bajo `/catalogo`, asi el permiso
`catalogo.gestionar` de los roles propios (CU-41) la cubre sin tocar nada. La
prueba es del cliente y va con el vestidor del 1er parcial.

Regla: el router valida la entrada, resuelve la autorizacion y delega en el
servicio. Ninguna regla de negocio vive aqui.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Path, UploadFile, status

from app.core.dependencies import DbSession, Usuario, requiere_cupo, requiere_funcion, requiere_roles
from app.integrations.probador_ia import ErrorDelProbador, ProbadorNoConfigurado
from app.modules.vestidor_virtual import probador_service as service
from app.modules.vestidor_virtual.probador_schemas import (
    ProductoParaProbar,
    MedidasDelProducto,
    PrendaParaPreparar,
    ProductoDelProbador,
    PuntosDePrenda,
    PruebaDeProducto,
    SesionEntrada,
    SesionSalida,
)

Id = Annotated[int, Path(ge=1)]


def _http(e: service.Rechazo) -> HTTPException:
    return HTTPException(e.codigo, e.mensaje)


# --- CU-36 ---------------------------------------------------------------------

admin_router = APIRouter(
    prefix="/catalogo/probador",
    tags=["CU-36 · Preparar prenda para el probador"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
)


@admin_router.get("/productos", response_model=list[ProductoDelProbador],
                  summary="CU-36 Productos con imagen de vestidor y su avance")
def productos(db: DbSession):
    return service.productos(db)


@admin_router.get("/productos/{producto_id}", response_model=PrendaParaPreparar,
                  summary="CU-36 Imágenes, puntos y medidas de un producto")
def preparacion(producto_id: Id, db: DbSession):
    try:
        return service.preparacion(db, producto_id)
    except service.Rechazo as e:
        raise _http(e) from e


@admin_router.put("/imagenes/{imagen_id}/puntos", response_model=PuntosDePrenda,
                  summary="CU-36 Marcar los hombros y el ruedo de una imagen")
def guardar_puntos(imagen_id: Id, datos: PuntosDePrenda, db: DbSession):
    try:
        puntos = service.guardar_puntos(db, imagen_id, datos)
    except service.Rechazo as e:
        raise _http(e) from e
    db.commit()
    return puntos


@admin_router.put("/productos/{producto_id}/medidas", response_model=PrendaParaPreparar,
                  summary="CU-36 Cargar las medidas de la prenda por talla")
def guardar_medidas(producto_id: Id, datos: MedidasDelProducto, db: DbSession):
    try:
        salida = service.guardar_medidas(db, producto_id, datos.tallas)
    except service.Rechazo as e:
        raise _http(e) from e
    db.commit()
    return salida


# --- CU-37 y CU-38 ---------------------------------------------------------------

cliente_router = APIRouter(
    prefix="/vestidor",
    tags=["CU-37 y CU-38 · Probador con la talla real"],
    dependencies=[Depends(requiere_roles("CLIENTE"))],
)


@cliente_router.get("/productos-listos", response_model=list[ProductoParaProbar],
                    summary="CU-37 Prendas listas para probar (lo último calibrado primero)")
def listos(db: DbSession):
    return service.listos(db)


@cliente_router.get("/productos/{producto_id}/prueba", response_model=PruebaDeProducto,
                    summary="CU-37 Todo lo que hace falta para probarse un producto")
def prueba(producto_id: Id, db: DbSession, usuario: Usuario):
    try:
        return service.prueba(db, producto_id, usuario.id)
    except service.Rechazo as e:
        raise _http(e) from e


@cliente_router.post("/sesiones", response_model=SesionSalida,
                     status_code=status.HTTP_201_CREATED,
                     summary="CU-37 Registrar una prueba")
def registrar(datos: SesionEntrada, db: DbSession, usuario: Usuario):
    try:
        salida = service.registrar_sesion(db, usuario.id, datos.variante_id, datos.metodo)
    except service.Rechazo as e:
        raise _http(e) from e
    db.commit()
    return salida


@cliente_router.get("/sesiones", response_model=list[SesionSalida],
                    summary="CU-37 Mis pruebas (las últimas 20)")
def mis_sesiones(db: DbSession, usuario: Usuario):
    try:
        return service.mis_sesiones(db, usuario.id)
    except service.Rechazo as e:
        raise _http(e) from e


@cliente_router.delete("/sesiones/{sesion_id}", status_code=status.HTTP_204_NO_CONTENT,
                       summary="CU-37 Borrar una prueba (y su foto)")
def borrar(sesion_id: Id, db: DbSession, usuario: Usuario):
    try:
        service.borrar_sesion(db, usuario.id, sesion_id)
    except service.Rechazo as e:
        raise _http(e) from e
    db.commit()


@cliente_router.post(
    "/sesiones/{sesion_id}/foto",
    response_model=SesionSalida,
    summary="CU-38 Generar la foto realista de una prueba",
    # Incluye el CU-05: la foto con IA es una funcion del plan con cupo
    # mensual, que se descuenta del de la tienda y no del cliente.
    dependencies=[Depends(requiere_funcion("foto_ia")), Depends(requiere_cupo("fotos_ia"))],
    responses={
        403: {"description": "El plan no incluye la foto con IA o se agotó el cupo del mes."},
        409: {"description": "La prueba ya tiene su foto."},
        503: {"description": "La foto con IA está apagada en este entorno."},
    },
)
async def generar_foto(
    sesion_id: Id,
    db: DbSession,
    usuario: Usuario,
    composicion: Annotated[UploadFile, File(description="La composición del CU-37 (PNG o JPEG).")],
):
    contenido = await composicion.read()
    try:
        salida = service.generar_foto(
            db, usuario.id, sesion_id, contenido, composicion.content_type
        )
    except service.Rechazo as e:
        raise _http(e) from e
    except ProbadorNoConfigurado as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e
    except ErrorDelProbador as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e
    db.commit()
    return salida
