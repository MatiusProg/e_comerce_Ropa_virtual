"""
P16 - Mis comprobantes / CU-46 Consultar mis comprobantes por voz  |  capa: router

Dos routers:

- `POST /tienda/mis-comprobantes/consulta` (rol CLIENTE): la frase entra, la
  lista sale. Es un POST porque lleva un cuerpo ---la frase--- y por eso la
  bitácora (CU-42) lo anota sola, como toda petición que no es GET.
- `GET /publico/comprobantes/{token}` y su QR (sin sesión): lo que abre el QR.
  Solo tienda, número, fecha, total y estado; nada del cliente. El token es una
  firma HMAC (ver `verificacion.py`): sin la clave del servidor no se fabrica.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.comprobantes import service, verificacion
from app.modules.comprobantes.schemas import ConsultaIn, ConsultaOut, QrOut, VerificacionOut
from app.modules.seguridad import service as seguridad

router = APIRouter(
    prefix="/tienda/mis-comprobantes",
    tags=["Mis comprobantes · CU-46"],
    dependencies=[Depends(requiere_roles("CLIENTE"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Cliente."},
    },
)

publico_router = APIRouter(prefix="/publico/comprobantes", tags=["Mis comprobantes · CU-46"])


@router.post("/consulta", response_model=ConsultaOut, summary="CU-46 Consultar mis comprobantes")
def consultar(datos: ConsultaIn, db: DbSession, usuario: Usuario) -> ConsultaOut:
    """«Mis últimas 3 compras», «mis recibos de octubre», «mis devoluciones».

    Si el pedido no se entiende, responde `entendido: false` con ejemplos y
    **sin datos**: nunca se adivina un criterio para mostrar algo.
    """
    try:
        return service.consultar(db, usuario.id, datos.texto)
    except seguridad.PerfilInexistente as error:
        raise HTTPException(403, "Esta cuenta no tiene ficha de cliente.") from error


_NO_EXISTE = "Ese comprobante no existe o el código no es válido."


@publico_router.get("/{token}", response_model=VerificacionOut, summary="CU-46 Verificar un comprobante")
def verificar(token: str, db: DbSession) -> VerificacionOut:
    try:
        return service.verificar(db, token)
    except service.ComprobanteInexistente as error:
        raise HTTPException(404, _NO_EXISTE) from error


def _texto_del_qr(token: str) -> str:
    try:
        service.referencia(token)
    except service.ComprobanteInexistente as error:
        raise HTTPException(404, _NO_EXISTE) from error
    return verificacion.url_publica(token)


@publico_router.get(
    "/{token}/qr.svg",
    summary="CU-46 El QR del comprobante (SVG)",
    responses={200: {"content": {"image/svg+xml": {}}}},
)
def qr_svg(token: str) -> Response:
    """El QR que lleva a la página de verificación.

    No consulta la base: el token firmado ya dice que el comprobante es de
    verdad, y el QR es solo su URL dibujada. Se puede guardar en caché.
    """
    return Response(
        content=verificacion.svg(_texto_del_qr(token)),
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@publico_router.get("/{token}/qr", response_model=QrOut, summary="CU-46 La matriz del QR")
def qr_matriz(token: str) -> QrOut:
    """La misma URL como matriz de módulos, para dibujarla en el móvil sin librerías."""
    texto = _texto_del_qr(token)
    return QrOut(texto=texto, modulos=verificacion.modulos(texto))
