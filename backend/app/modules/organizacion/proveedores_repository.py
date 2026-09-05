"""
P2 - Organizacion  |  CU-07 Gestionar proveedores  |  capa: repositorio

Ciclo de desarrollo: 1

Archivos propios para no chocar con el CU-06; el motivo esta en
`proveedores_schemas.py`.
"""
from sqlalchemy import Row, func, or_, select
from sqlalchemy.orm import Session

from app.modules.organizacion.models import Proveedor
from app.modules.seguridad.models import Usuario

# Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna
# validacion de permisos, ningun commit de transaccion compuesta.


def _seleccion():
    """Las columnas del listado, con el correo del usuario vinculado.

    El `outerjoin` es lo que hace falta: la mayoria de los proveedores no
    tiene acceso al sistema --- `proveedor.usuario_id` es opcional --- y con un
    join normal esos no aparecerian en el listado.
    """
    return select(
        Proveedor.id,
        Proveedor.razon_social,
        Proveedor.identificacion_tributaria,
        Proveedor.contacto,
        Proveedor.telefono,
        Proveedor.correo,
        Proveedor.direccion,
        Proveedor.activo,
        Proveedor.usuario_id,
        Usuario.correo.label("correo_acceso"),
    ).outerjoin(Usuario, Usuario.id == Proveedor.usuario_id)


def listar(
    db: Session, *, busqueda: str | None = None, activo: bool | None = None
) -> list[Row]:
    """Proveedores ordenados por razon social (paso 2 del flujo principal)."""
    consulta = _seleccion()

    if busqueda:
        patron = f"%{busqueda.strip().lower()}%"
        consulta = consulta.where(
            or_(
                func.lower(Proveedor.razon_social).like(patron),
                func.lower(Proveedor.identificacion_tributaria).like(patron),
                func.lower(Proveedor.contacto).like(patron),
                func.lower(Proveedor.correo).like(patron),
            )
        )
    if activo is not None:
        consulta = consulta.where(Proveedor.activo.is_(activo))

    return list(db.execute(consulta.order_by(Proveedor.razon_social)).all())


def obtener_detalle(db: Session, proveedor_id: int) -> Row | None:
    """Una sola fila del listado, para devolver el proveedor recien tocado."""
    return db.execute(_seleccion().where(Proveedor.id == proveedor_id)).one_or_none()


def obtener_detalle_por_usuario(db: Session, usuario_id: int) -> Row | None:
    """La ficha del proveedor que porta el token.

    La usa el propio Proveedor para consultar sus datos, que es el segundo
    actor del caso de uso.
    """
    return db.execute(_seleccion().where(Proveedor.usuario_id == usuario_id)).one_or_none()


def obtener(db: Session, proveedor_id: int) -> Proveedor | None:
    """La fila de proveedor, para editarla."""
    return db.get(Proveedor, proveedor_id)


def existe_identificacion(
    db: Session, identificacion: str, *, excepto_id: int | None = None
) -> bool:
    """Excepcion E1: la identificacion tributaria ya esta registrada.

    `excepto_id` deja fuera al propio proveedor al editarlo; sin eso, guardar
    sin cambiarle la identificacion se rechazaria a si mismo.
    """
    consulta = select(Proveedor.id).where(
        func.lower(Proveedor.identificacion_tributaria)
        == identificacion.strip().lower()
    )
    if excepto_id is not None:
        consulta = consulta.where(Proveedor.id != excepto_id)
    return db.scalar(consulta) is not None


def agregar(
    db: Session,
    *,
    razon_social: str,
    identificacion_tributaria: str,
    contacto: str | None,
    telefono: str | None,
    correo: str | None,
    direccion: str | None,
    activo: bool,
) -> Proveedor:
    """Crea el proveedor. No confirma: la transaccion es del servicio."""
    proveedor = Proveedor(
        razon_social=razon_social,
        identificacion_tributaria=identificacion_tributaria,
        contacto=contacto,
        telefono=telefono,
        correo=correo,
        direccion=direccion,
        activo=activo,
    )
    db.add(proveedor)
    db.flush()
    return proveedor
