"""
P11 - Reportes / CU-37  |  capa: router

Realiza el **RF36**: descargar los reportes en PDF y Excel.

QUIEN PUEDE, Y SOBRE QUE
------------------------
ADMINISTRADOR y ENCARGADO, que es lo que dice el caso de uso. Pero **el
encargado solo ve su sucursal**: se le fuerza el filtro en vez de confiar en
el parametro. Sin eso, quitar `?sucursal_id=` de la URL le daria los numeros
de toda la red --- y un reporte de ventas es exactamente el dato que no
corresponde que vea de las demas.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.reportes import reportes_service as service
from app.modules.reportes.exportador import FORMATOS

router = APIRouter(
    prefix="/reportes",
    tags=["CU-37 · Generar reportes de gestión"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR", "ENCARGADO"))],
)


@router.get("/catalogo")
def catalogo_de_reportes(db: DbSession, usuario: Usuario):
    """Que reportes hay y que columnas trae cada uno.

    Existe para que la pantalla no tenga la lista escrita a mano: si se agrega
    un reporte, aparece solo. Sin esto, agregar el septimo obliga a tocar el
    backend y la web, y alguien se olvida de la segunda mitad.
    """
    # Los filtros viajan CON SUS OPCIONES ya resueltas: las sucursales, los
    # proveedores y las temporadas salen de la base. Si la pantalla tuviera
    # que pedirlas por separado serian tres consultas mas y tres formas de
    # quedar desincronizada con lo que el reporte de verdad acepta.
    #
    # El ENCARGADO no ve el filtro de sucursal: se le fuerza la suya en la
    # descarga, asi que ofrecerselo seria un control que no hace nada.
    es_admin = usuario.rol == "ADMINISTRADOR"
    return [
        {
            "tipo": tipo,
            "titulo": definicion.titulo,
            "columnas": definicion.encabezados,
            "usa_periodo": not definicion.sin_periodo,
            "filtros": [
                {
                    "campo": f.campo,
                    "etiqueta": f.etiqueta,
                    "opciones": service.opciones_de(db, f),
                }
                for f in definicion.filtros
                if es_admin or f.campo != "sucursal_id"
            ],
        }
        for tipo, definicion in sorted(service.REPORTES.items())
    ]


@router.get("/{tipo}.{formato}")
def descargar(
    tipo: Annotated[str, Path(pattern="^[a-z]+$")],
    formato: Annotated[str, Path(pattern="^(pdf|xlsx)$")],
    db: DbSession,
    usuario: Usuario,
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
    sucursal_id: Annotated[int | None, Query(ge=1)] = None,
    canal: Annotated[str | None, Query()] = None,
    estado: Annotated[str | None, Query()] = None,
    metodo_pago: Annotated[str | None, Query()] = None,
    tipo_movimiento: Annotated[str | None, Query(alias="tipo")] = None,
    bajo_minimo: Annotated[str | None, Query()] = None,
    temporada_id: Annotated[int | None, Query(ge=1)] = None,
    proveedor_id: Annotated[int | None, Query(ge=1)] = None,
):
    """El reporte, como archivo para descargar.

    La extension va en la RUTA y no en un parametro (`/ventas.pdf` y no
    `/ventas?formato=pdf`) porque asi el navegador y el sistema operativo
    saben que es sin mirar las cabeceras: al guardarlo, el archivo ya se llama
    como debe.
    """
    # EL ENCARGADO NO ELIGE SUCURSAL: se le impone la suya.
    if usuario.rol != "ADMINISTRADOR":
        if usuario.sucursal_id is None:
            raise HTTPException(
                409,
                detail=(
                    "Su usuario no está asignado a ninguna sucursal. "
                    "Pídale al administrador que lo asigne."
                ),
            )
        sucursal_id = usuario.sucursal_id

    # Se mandan TODOS; el servicio descarta los que ese reporte no declara.
    # Asi el router no tiene que saber cual acepta cual, que es justamente lo
    # que permite agregar un filtro tocando solo el catalogo del servicio.
    extras = {
        "canal": canal,
        "estado": estado,
        "metodo_pago": metodo_pago,
        "tipo": tipo_movimiento,
        "bajo_minimo": bajo_minimo,
        "temporada_id": temporada_id,
        "proveedor_id": proveedor_id,
    }

    try:
        tabla = service.generar(
            db,
            tipo=tipo,
            desde=desde,
            hasta=hasta,
            sucursal_id=sucursal_id,
            extras=extras,
        )
    except service.ErrorDeReporte as e:
        raise HTTPException(e.codigo, detail=e.mensaje) from e

    tipo_mime, extension, convertir = FORMATOS[formato]
    contenido = convertir(tabla)
    nombre = f"{tipo}-{date.today().isoformat()}.{extension}"

    return Response(
        content=contenido,
        media_type=tipo_mime,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
