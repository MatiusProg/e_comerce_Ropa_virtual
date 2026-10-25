"""
P12 - Plataforma SaaS / CU-12  |  capa: servicio (la clase control GestorMarca)

2do parcial. Caso de uso: CU-12 Personalizar la tienda de la empresa.

  1.4  verificar que el plan incluya `marca_propia`   (1a: funcionNoIncluida)
  1.9  validar el logo                                (4a: imagenInvalida)
  1.10 guardar la marca en `empresa`
  1.11 la tienda en linea la aplica (`marca_de_la_tienda`)

Guardar exige la funcion: lo hace la dependencia `requiere_funcion` en el
router (CU-05), que responde el 403 `plan_limit`. Ver la pantalla no la exige:
el administrador tiene que poder ver que su plan no la incluye.

El archivo del logo se guarda como las imagenes de producto (CU-11): en
MEDIA_ROOT, con la base guardando solo la ruta relativa, y validado abriendolo
con Pillow, no por su extension.
"""
import secrets
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.catalogo import imagenes_almacen
from app.modules.plataforma import verificador
from app.modules.plataforma.mi_tienda.schemas import ColoresIn, MarcaOut, MarcaTiendaOut
from app.modules.plataforma.models import Empresa

FUNCION = "marca_propia"

#: Los problemas del archivo (4a). Se reexporta para que el router no tenga
#: que conocer el modulo del catalogo.
ErrorDeArchivo = imagenes_almacen.ErrorDeArchivo


class SinEmpresa(Exception):
    """La cuenta no es de una empresa: no tiene tienda que personalizar."""


def _empresa(db: Session, empresa_id: int | None) -> Empresa:
    empresa = db.get(Empresa, empresa_id) if empresa_id is not None else None
    if empresa is None:
        raise SinEmpresa()
    return empresa


def _incluida(db: Session) -> bool:
    """1.4: si el plan vigente de la empresa de la sesion incluye la funcion."""
    try:
        return bool(verificador.plan_vigente(db).funciones.get(FUNCION))
    except verificador.SinSuscripcionVigente:
        return False


def _url(ruta: str | None) -> str | None:
    return imagenes_almacen.url_de(ruta) if ruta else None


def _marca(db: Session, empresa: Empresa) -> MarcaOut:
    return MarcaOut(
        empresa=empresa.nombre,
        slug=empresa.slug,
        logo_url=_url(empresa.logo),
        color_principal=empresa.color_principal,
        color_secundario=empresa.color_secundario,
        incluida=_incluida(db),
    )


def obtener_marca(db: Session, empresa_id: int | None) -> MarcaOut:
    """1.2 a 1.6: la marca actual, para la vista previa."""
    return _marca(db, _empresa(db, empresa_id))


def guardar_colores(db: Session, empresa_id: int | None, datos: ColoresIn) -> MarcaOut:
    """1.8 y 1.10: los colores. La funcion ya la verifico el router."""
    empresa = _empresa(db, empresa_id)
    empresa.color_principal = datos.color_principal
    empresa.color_secundario = datos.color_secundario
    db.commit()
    return _marca(db, empresa)


def _guardar_archivo(contenido: bytes, *, empresa_id: int, formato: str) -> str:
    """El archivo en `empresas/<id>/`, con un nombre que pone el servidor."""
    extension = imagenes_almacen.FORMATOS[formato]
    relativa = Path("empresas") / str(empresa_id) / f"logo-{secrets.token_hex(8)}{extension}"
    destino = Path(settings.MEDIA_ROOT) / relativa
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    # Con barras hacia adelante: va a la base y se sirve como URL.
    return relativa.as_posix()


def guardar_logo(db: Session, empresa_id: int | None, contenido: bytes) -> MarcaOut:
    """1.9 y 1.10: valida el logo (4a) y reemplaza el anterior."""
    empresa = _empresa(db, empresa_id)
    datos = imagenes_almacen.inspeccionar(contenido)  # 4a: ErrorDeArchivo

    anterior = empresa.logo
    nuevo = _guardar_archivo(contenido, empresa_id=empresa.id, formato=datos.formato)
    empresa.logo = nuevo
    try:
        db.commit()
    except Exception:
        db.rollback()
        imagenes_almacen.borrar(nuevo)
        raise
    # El archivo viejo se borra recien con la fila ya apuntando al nuevo.
    if anterior:
        imagenes_almacen.borrar(anterior)
    return _marca(db, empresa)


def quitar_logo(db: Session, empresa_id: int | None) -> MarcaOut:
    """Vuelve al logo de Violet."""
    empresa = _empresa(db, empresa_id)
    anterior, empresa.logo = empresa.logo, None
    db.commit()
    if anterior:
        imagenes_almacen.borrar(anterior)
    return _marca(db, empresa)


def marca_de_la_tienda(db: Session) -> MarcaTiendaOut:
    """1.11: la marca de la tienda que se esta mirando.

    La empresa es la del contexto: la del usuario con sesion o la de la tienda
    (`X-Empresa`) para el visitante. Sin `marca_propia` en el plan la tienda se
    ve con la de Violet aunque la empresa haya guardado una antes: al bajar de
    plan no se borra nada (RN-04), y vuelve a verse si la vuelve a contratar.
    """
    empresa_id = db.scalar(select(func.app_empresa_actual()))
    empresa = db.get(Empresa, empresa_id) if empresa_id is not None else None
    if empresa is None or not _incluida(db):
        return MarcaTiendaOut(
            empresa=empresa.nombre if empresa else None,
            logo_url=None,
            color_principal=None,
            color_secundario=None,
        )
    return MarcaTiendaOut(
        empresa=empresa.nombre,
        logo_url=_url(empresa.logo),
        color_principal=empresa.color_principal,
        color_secundario=empresa.color_secundario,
    )
