"""CU-21 · Medidas del cliente y ajuste por talla.

DOS ROUTERS Y NO UNO
--------------------
Las medidas son del cliente y van bajo `/clientes/me`; el ajuste es del
catalogo y va bajo `/tienda`. Separarlos permite que el ajuste lo pueda pedir
cualquiera que este autenticado ---incluido un empleado atendiendo en el
mostrador--- mientras que las medidas solo las toca su dueno.

POR QUE EL AJUSTE NO SE METIO EN LA FICHA DE PRODUCTO
------------------------------------------------------
Seria comodo devolverlo dentro de `/tienda/productos/{id}`, que el vestidor ya
pide. No se hizo por dos razones. La primera es que la ficha la consume tambien
quien no inicio sesion, y el ajuste no existe sin cliente. La segunda es de
oportunidad: al 18/09 Karen esta trabajando sobre el backend en CU-28, y
agregar campos al esquema de la ficha ---que es de los mas compartidos--- es la
forma mas facil de chocar. Un endpoint aparte no toca nada de lo suyo.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status
from typing import Annotated

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.medidas import repository, service
from app.modules.medidas.schemas import AjusteDeProducto, MedidasEntrada, MedidasSalida

router = APIRouter(
    prefix="/clientes/me/medidas",
    tags=["CU-21 · Medidas del cliente"],
    dependencies=[Depends(requiere_roles("CLIENTE"))],
)

ajuste_router = APIRouter(prefix="/tienda", tags=["CU-21 · Vestidor virtual"])


def _cliente_o_404(db, usuario_id: int) -> int:
    cliente = repository.cliente_de_usuario(db, usuario_id)
    if cliente is None:
        # Pasa con el administrador, que tiene usuario pero no ficha de
        # cliente. No es un 403: el token es valido, lo que no hay es a quien
        # atribuirle las medidas.
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Esta cuenta no tiene ficha de cliente.",
        )
    return cliente.id


@router.get("", response_model=MedidasSalida | None)
def ver_mis_medidas(db: DbSession, usuario: Usuario):
    """Devuelve `null` ---y no 404--- cuando todavia no se cargaron.

    Que no esten cargadas es el estado normal de un cliente nuevo, no un error.
    Con 404 la pantalla tendria que tratar un caso corriente por el camino de
    los fallos.
    """
    return repository.medidas_de(db, _cliente_o_404(db, usuario.id))


@router.put("", response_model=MedidasSalida)
def guardar_mis_medidas(datos: MedidasEntrada, db: DbSession, usuario: Usuario):
    """PUT y no POST: hay una sola fila por cliente y se reemplaza entera."""
    fila = repository.guardar_medidas(
        db,
        _cliente_o_404(db, usuario.id),
        busto_cm=datos.busto_cm,
        cintura_cm=datos.cintura_cm,
        cadera_cm=datos.cadera_cm,
        altura_cm=datos.altura_cm,
    )
    db.commit()
    db.refresh(fila)
    return fila


@ajuste_router.get(
    "/productos/{producto_id}/ajuste", response_model=AjusteDeProducto
)
def ajuste_del_producto(
    producto_id: Annotated[int, Path(ge=1)], db: DbSession, usuario: Usuario
):
    """Como le queda cada talla de este producto a quien pregunta.

    Nunca falla por falta de datos: si no hay medidas o no hay tabla lo dice en
    la respuesta y el vestidor dibuja como siempre.
    """
    return service.ajuste_de_producto(db, producto_id, usuario.id)
