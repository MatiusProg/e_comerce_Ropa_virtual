"""
P9 - Vestidor Virtual (RA)  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 3
Caso de uso: CU-21 Utilizar vestidor virtual  (RF13)

DOS ENDPOINTS, Y UNO EXISTE SOLO PARA PODER ESCONDER UN BOTON
--------------------------------------------------------------
`GET /vestidor/probador` dice si el probado por IA esta habilitado. La app lo
consulta al abrir la camara y, si no lo esta, **no muestra el boton**. Un boton
que siempre da error es peor que no tenerlo.

`POST /vestidor/probar` es el probado en si, y es **OPCIONAL**: el recorrido de
CU-21 --- camara, prenda encima, capturar, al carrito o a la reserva ---
funciona entero sin tocarlo.

LA RESPUESTA ES LA IMAGEN, NO UN JSON CON LA IMAGEN ADENTRO
------------------------------------------------------------
Devolver el PNG crudo y no un base64 dentro de un JSON: base64 infla un tercio
el tamano, obliga al telefono a decodificar en el hilo de interfaz y no se
puede mostrar en un `Image.network`. El dato de quien la genero va en una
cabecera, que es donde van los metadatos de una respuesta binaria.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.core.dependencies import DbSession, requiere_roles
from app.integrations.probador_ia import ErrorDelProbador, ProbadorNoConfigurado
from app.modules.vestidor_virtual import service
from app.modules.vestidor_virtual.schemas import EstadoDelProbador

router = APIRouter(
    prefix="/vestidor",
    tags=["Vestidor virtual"],
    # El vestidor es del Cliente. Se declara una vez a nivel de router, igual
    # que en el carrito y en los pedidos.
    dependencies=[Depends(requiere_roles("CLIENTE"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Cliente."},
    },
)

# Regla: el router valida la entrada, resuelve la autorizacion y delega
# en el servicio. Ninguna regla de negocio vive aqui.


@router.get(
    "/probador",
    response_model=EstadoDelProbador,
    summary="CU-21 · ¿Se puede ofrecer el probado por IA?",
)
def estado_del_probador() -> EstadoDelProbador:
    """Si hay con qué componer la imagen.

    La app lo consulta **una vez, al abrir el vestidor**, y esconde el botón si
    la respuesta es que no. Por eso es un endpoint aparte y no un campo de otra
    respuesta: la pantalla necesita saberlo antes de pintar nada.
    """
    return service.estado()


@router.post(
    "/probar",
    summary="CU-21 · Amoldar la prenda al cuerpo (opcional)",
    response_class=Response,
    responses={
        200: {
            "content": {"image/png": {}},
            "description": "La imagen compuesta.",
        },
        404: {"description": "Esa variante no tiene imagen para el vestidor."},
        413: {"description": "La captura es demasiado grande."},
        502: {"description": "El servicio de imágenes falló."},
        503: {"description": "El probado por IA no está habilitado."},
    },
)
async def probar(
    db: DbSession,
    variante_id: Annotated[int, Form(description="La variante que se está probando.")],
    captura: Annotated[
        UploadFile,
        File(description="La captura del vestidor: la persona con la prenda encima."),
    ],
) -> Response:
    """Manda la captura y la prenda al modelo y devuelve la imagen compuesta.

    **No se guarda nada**: ni la captura que sube el cliente, ni lo que
    devuelve el modelo. La captura es la foto del cuerpo de una persona, y
    guardarla obligaría a decidir cuánto se conserva, quién puede verla y cómo
    se borra. La imagen vuelve por la respuesta y vive en el teléfono, que es
    de donde salió.
    """
    contenido = await captura.read()
    try:
        imagen, tipo, generada_por = service.probar(
            db,
            variante_id=variante_id,
            captura=contenido,
            tipo_mime=captura.content_type,
        )
    except ProbadorNoConfigurado as e:
        # 503 y no 500: no está roto, está apagado. La diferencia importa
        # porque la app esconde el botón con esto y no reintenta.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e
    except service.VarianteSinPrenda as e:
        raise HTTPException(404, str(e)) from e
    except service.CapturaInvalida as e:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            if "supera" in str(e)
            else status.HTTP_422_UNPROCESSABLE_ENTITY,
            str(e),
        ) from e
    except ErrorDelProbador as e:
        # 502: es un tercero el que falló, y el cliente se queda igual con su
        # captura, que es lo que el caso de uso le prometió.
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e

    return Response(
        content=imagen,
        media_type=tipo,
        headers={
            # Que la imagen fue generada tiene que poder leerse. Mostrarla sin
            # decirlo sería hacer pasar por foto algo que no lo es.
            "X-Generada-Por": generada_por,
            # No se cachea: cada captura es de una persona distinta.
            "Cache-Control": "no-store",
        },
    )
