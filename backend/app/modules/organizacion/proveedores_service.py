"""
P2 - Organizacion  |  CU-07 Gestionar proveedores  |  capa: servicio

Ciclo de desarrollo: 1

Archivos propios para no chocar con el CU-06; el motivo esta en
`proveedores_schemas.py`.

Este servicio orquesta tambien el repositorio de P1 (seguridad) para el flujo
alternativo 3c, que crea un usuario. Es la dependencia P2 -> P1 que el analisis
de arquitectura ya declara: el paquete de organizacion conoce al de seguridad,
nunca al reves.
"""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.organizacion import proveedores_repository as repository
from app.modules.organizacion.proveedores_schemas import (
    AccesoProveedorIn,
    ProveedorCrearIn,
    ProveedorEditarIn,
    ProveedorOut,
)
from app.modules.seguridad import repository as seguridad

# Regla: aqui viven las reglas de negocio y el control de la transaccion.
# El servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.

#: Rol que se asigna al habilitar acceso a un proveedor (flujo 3c). Debe
#: existir en la tabla rol, cargado por el seed, igual que ROL_CLIENTE en CU-01.
ROL_PROVEEDOR = "PROVEEDOR"


# --- Errores de negocio --------------------------------------------------
# El servicio no habla HTTP: senala el problema con una excepcion propia y el
# router la traduce al codigo de estado que corresponda.

class ErrorDeProveedores(Exception):
    """Base de los errores previstos de CU-07."""


class ProveedorInexistente(ErrorDeProveedores):
    """El identificador no corresponde a ningun proveedor."""


class IdentificacionDuplicada(ErrorDeProveedores):
    """Excepcion E1: la identificacion tributaria ya esta registrada."""


class CorreoYaRegistrado(ErrorDeProveedores):
    """El correo de acceso ya pertenece a otra cuenta del sistema."""


class AccesoYaHabilitado(ErrorDeProveedores):
    """El proveedor ya tiene un usuario vinculado (flujo 3c)."""


class RolProveedorInexistente(ErrorDeProveedores):
    """La tabla rol no tiene el rol PROVEEDOR. Falta correr el seed."""


class ProveedorSinFicha(ErrorDeProveedores):
    """El usuario tiene rol Proveedor pero no hay ficha vinculada a el."""


def _viola(exc: IntegrityError, restriccion: str) -> bool:
    """Indica si la violacion corresponde a esa restriccion.

    Se apoya en la convencion de nombres de app/db/base.py, que nombra los
    UNIQUE como uq_<tabla>_<columna>. PostgreSQL nombra asi tambien el indice
    implicito, de modo que alcanza con buscar el nombre en el mensaje.
    """
    return restriccion in str(exc.orig)


def _fila_a_salida(fila) -> ProveedorOut:
    return ProveedorOut(
        id=fila.id,
        razon_social=fila.razon_social,
        identificacion_tributaria=fila.identificacion_tributaria,
        contacto=fila.contacto,
        telefono=fila.telefono,
        correo=fila.correo,
        direccion=fila.direccion,
        activo=fila.activo,
        usuario_id=fila.usuario_id,
        tiene_acceso=fila.usuario_id is not None,
        correo_acceso=fila.correo_acceso,
    )


# --- Consultas -----------------------------------------------------------

def listar(
    db: Session, *, busqueda: str | None = None, activo: bool | None = None
) -> list[ProveedorOut]:
    """Listado del paso 2, con busqueda y filtro por estado."""
    return [
        _fila_a_salida(f)
        for f in repository.listar(db, busqueda=busqueda, activo=activo)
    ]


def obtener(db: Session, proveedor_id: int) -> ProveedorOut:
    fila = repository.obtener_detalle(db, proveedor_id)
    if fila is None:
        raise ProveedorInexistente(str(proveedor_id))
    return _fila_a_salida(fila)


def obtener_mi_ficha(db: Session, usuario_id: int) -> ProveedorOut:
    """Los datos del proveedor que porta el token.

    Es el segundo actor del caso de uso: el Proveedor consulta sus propios
    datos. No recibe identificador --- se resuelve desde el token --- para que
    no pueda pedir la ficha de otro cambiando un numero en la URL.
    """
    fila = repository.obtener_detalle_por_usuario(db, usuario_id)
    if fila is None:
        raise ProveedorSinFicha(str(usuario_id))
    return _fila_a_salida(fila)


# --- Flujo principal y flujo alternativo 3a ------------------------------

def crear(db: Session, datos: ProveedorCrearIn) -> ProveedorOut:
    """Alta de proveedor (pasos 5 a 7).

    El paso 6 pide validar los datos y verificar que la identificacion
    tributaria no este registrada.
    """
    if repository.existe_identificacion(db, datos.identificacion_tributaria):
        raise IdentificacionDuplicada(datos.identificacion_tributaria)

    try:
        proveedor = repository.agregar(
            db,
            razon_social=datos.razon_social,
            identificacion_tributaria=datos.identificacion_tributaria,
            contacto=datos.contacto,
            telefono=datos.telefono,
            correo=datos.correo,
            direccion=datos.direccion,
            activo=datos.activo,
        )
        db.commit()
    except IntegrityError as exc:
        # Entre la consulta previa y el commit puede colarse otra alta con la
        # misma identificacion. El UNIQUE de la base es el que lo impide de
        # verdad; la consulta previa solo da un mensaje claro en el caso normal.
        db.rollback()
        if _viola(exc, "uq_proveedor_identificacion_tributaria"):
            raise IdentificacionDuplicada(datos.identificacion_tributaria) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener(db, proveedor.id)


def editar(db: Session, proveedor_id: int, datos: ProveedorEditarIn) -> ProveedorOut:
    """Edicion de proveedor (flujo alternativo 3a)."""
    proveedor = repository.obtener(db, proveedor_id)
    if proveedor is None:
        raise ProveedorInexistente(str(proveedor_id))

    if (
        datos.identificacion_tributaria
        and datos.identificacion_tributaria != proveedor.identificacion_tributaria
        and repository.existe_identificacion(
            db, datos.identificacion_tributaria, excepto_id=proveedor_id
        )
    ):
        raise IdentificacionDuplicada(datos.identificacion_tributaria)

    try:
        if datos.razon_social is not None:
            proveedor.razon_social = datos.razon_social
        if datos.identificacion_tributaria is not None:
            proveedor.identificacion_tributaria = datos.identificacion_tributaria
        # Los cuatro opcionales se comparan contra los campos que llegaron, no
        # contra None: mandar cadena vacia --- que el esquema convirtio en
        # None --- significa borrar el dato, y eso hay que poder hacerlo.
        for campo in ("contacto", "telefono", "correo", "direccion"):
            if campo in datos.model_fields_set:
                setattr(proveedor, campo, getattr(datos, campo))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, "uq_proveedor_identificacion_tributaria"):
            raise IdentificacionDuplicada(
                datos.identificacion_tributaria or ""
            ) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener(db, proveedor_id)


# --- Flujo alternativo 3b ------------------------------------------------

def cambiar_estado(db: Session, proveedor_id: int, activo: bool) -> ProveedorOut:
    """Alta o baja de un proveedor.

    La baja no borra la ficha: sus productos historicos se conservan, que es
    lo que pide el caso de uso. Tampoco toca el usuario vinculado --- activar o
    desactivar una cuenta es CU-03 --- pero conviene saberlo: un proveedor dado
    de baja con acceso habilitado sigue pudiendo entrar a ver sus datos.
    """
    proveedor = repository.obtener(db, proveedor_id)
    if proveedor is None:
        raise ProveedorInexistente(str(proveedor_id))

    try:
        proveedor.activo = activo
        db.commit()
    except Exception:
        db.rollback()
        raise

    return obtener(db, proveedor_id)


# --- Flujo alternativo 3c ------------------------------------------------

def habilitar_acceso(
    db: Session, proveedor_id: int, datos: AccesoProveedorIn
) -> ProveedorOut:
    """Crea el usuario con rol Proveedor y lo vincula a la ficha.

    Las dos operaciones --- crear el usuario y vincularlo --- van en UNA sola
    transaccion: un usuario con rol Proveedor sin ficha asociada no es un
    estado valido, porque su ambito de datos son justamente los productos de
    esa ficha.
    """
    proveedor = repository.obtener(db, proveedor_id)
    if proveedor is None:
        raise ProveedorInexistente(str(proveedor_id))
    if proveedor.usuario_id is not None:
        raise AccesoYaHabilitado(str(proveedor_id))

    if seguridad.obtener_usuario_por_correo(db, datos.correo) is not None:
        raise CorreoYaRegistrado(datos.correo)

    rol = seguridad.obtener_rol_por_nombre(db, ROL_PROVEEDOR)
    if rol is None:
        raise RolProveedorInexistente(ROL_PROVEEDOR)

    try:
        usuario = seguridad.agregar_usuario(
            db,
            correo=datos.correo,
            hash_contrasena=hash_password(datos.contrasena),
            nombres=datos.nombres,
            apellidos=datos.apellidos,
            rol_id=rol.id,
        )
        proveedor.usuario_id = usuario.id
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, "uq_usuario_correo"):
            raise CorreoYaRegistrado(datos.correo) from exc
        if _viola(exc, "uq_proveedor_usuario_id"):
            raise AccesoYaHabilitado(str(proveedor_id)) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener(db, proveedor_id)
