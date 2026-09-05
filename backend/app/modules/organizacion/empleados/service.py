"""
P2 - Organizacion / CU-06  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 1
Caso de uso: CU-06 Gestionar empleados

Regla: aqui viven las reglas de negocio y el control de la transaccion. El
servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.

Relacion con el CU-03
---------------------
El alta de un Encargado o un Cajero se puede hacer por dos puertas: la pantalla
de usuarios (CU-03, que crea la cuenta y la ficha juntas) y esta. Es lo decidido
en la seccion 6.11.1 de docs/06-decisiones-tecnicas.md. Las dos puertas crean lo
mismo; la diferencia es desde donde se mira el alta -- desde la cuenta o desde
la persona -- y que solo esta admite el flujo 3c.
"""
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.organizacion.empleados import repository
from app.modules.organizacion.empleados.schemas import (
    ROL_DE_CARGO,
    BajaEmpleadoIn,
    EmpleadoCrearIn,
    EmpleadoEditarIn,
    EmpleadoOut,
    UsuarioVinculableOut,
)

# Revocar sesiones es de P1 y se reutiliza tal cual. La direccion P2 -> P1 es
# la que permite la regla de dependencias de la seccion 2.4.
from app.modules.seguridad import repository as repositorio_seguridad


# --- Errores de negocio --------------------------------------------------
# El servicio no habla HTTP: senala el problema con una excepcion propia y el
# router la traduce al codigo de estado que corresponda.

class ErrorDeEmpleados(Exception):
    """Base de los errores previstos de CU-06."""


class EmpleadoInexistente(ErrorDeEmpleados):
    """No hay empleado con ese identificador."""


class DocumentoYaRegistrado(ErrorDeEmpleados):
    """Excepcion E1."""


class SucursalInexistente(ErrorDeEmpleados):
    """La sucursal indicada no existe."""


class SucursalInactiva(ErrorDeEmpleados):
    """Excepcion E2: no se asigna personal a una sucursal dada de baja."""


class CorreoYaRegistrado(ErrorDeEmpleados):
    """Ya existe una cuenta con ese correo."""


class UsuarioNoVinculable(ErrorDeEmpleados):
    """Flujo 3c: el usuario no existe, esta desactivado o ya tiene ficha."""


class RolInexistente(ErrorDeEmpleados):
    """Falta en la tabla rol el rol que corresponde al cargo (seed incompleto)."""


class EmpleadoYaDadoDeBaja(ErrorDeEmpleados):
    """Flujo 3b sobre un empleado que ya no esta en actividad."""


class FechaDeBajaInvalida(ErrorDeEmpleados):
    """La baja no puede ser anterior al ingreso (CHECK ck_empleado_fechas)."""


def _viola(exc: IntegrityError, restriccion: str) -> bool:
    """Indica si la violacion corresponde a esa restriccion.

    Se apoya en la convencion de nombres de app/db/base.py.
    """
    return restriccion in str(exc.orig)


def _fila_a_empleado(fila) -> EmpleadoOut:
    """Traduce una fila del listado al esquema de salida."""
    return EmpleadoOut(
        id=fila.id,
        usuario_id=fila.usuario_id,
        nombres=fila.nombres,
        apellidos=fila.apellidos,
        correo=fila.correo,
        documento=fila.documento,
        telefono=fila.telefono,
        cargo=fila.cargo,
        sucursal_id=fila.sucursal_id,
        sucursal=fila.sucursal,
        ciudad=fila.ciudad,
        fecha_ingreso=fila.fecha_ingreso,
        fecha_baja=fila.fecha_baja,
        activo=fila.fecha_baja is None,
        usuario_activo=fila.usuario_activo,
    )


# --- Consultas -----------------------------------------------------------

def listar_empleados(
    db: Session,
    *,
    busqueda: str | None = None,
    sucursal_id: int | None = None,
    cargo: str | None = None,
    activo: bool | None = None,
) -> list[EmpleadoOut]:
    """Paso 2: listado con filtro por sucursal y por cargo."""
    return [
        _fila_a_empleado(f)
        for f in repository.listar_empleados(
            db,
            busqueda=busqueda,
            sucursal_id=sucursal_id,
            cargo=cargo,
            activo=activo,
        )
    ]


def obtener_empleado(db: Session, empleado_id: int) -> EmpleadoOut:
    fila = repository.obtener_empleado_con_detalle(db, empleado_id)
    if fila is None:
        raise EmpleadoInexistente(str(empleado_id))
    return _fila_a_empleado(fila)


def listar_usuarios_vinculables(db: Session) -> list[UsuarioVinculableOut]:
    """Flujo alternativo 3c: cuentas existentes sin ficha de empleado."""
    return [
        UsuarioVinculableOut.model_validate(f, from_attributes=True)
        for f in repository.listar_usuarios_vinculables(db)
    ]


# --- Alta (pasos 4 a 7 y flujo 3c) ---------------------------------------

def _validar_sucursal(db: Session, sucursal_id: int) -> None:
    """Excepcion E2, distinguiendo «no existe» de «esta dada de baja»."""
    if repository.obtener_sucursal_activa(db, sucursal_id) is not None:
        return
    if repository.existe_sucursal(db, sucursal_id):
        raise SucursalInactiva(str(sucursal_id))
    raise SucursalInexistente(str(sucursal_id))


def crear_empleado(db: Session, datos: EmpleadoCrearIn) -> EmpleadoOut:
    """Registra un empleado y su cuenta.

    Paso 6: valida los datos, verifica que el documento no este registrado y
    que la sucursal este activa. Paso 7: crea el usuario con el rol que
    corresponde al cargo y lo vincula a la ficha, TODO en una transaccion. Si
    algo falla, no queda ni la cuenta ni la ficha (excepcion E3).
    """
    _validar_sucursal(db, datos.sucursal_id)

    # Excepcion E1.
    if repository.existe_documento(db, datos.documento):
        raise DocumentoYaRegistrado(datos.documento)

    rol = repository.obtener_rol_por_nombre(db, ROL_DE_CARGO[datos.cargo])
    if rol is None:
        raise RolInexistente(ROL_DE_CARGO[datos.cargo])

    try:
        if datos.usuario_id is not None:
            # Flujo 3c. Se vuelve a comprobar que siga libre: entre que la
            # interfaz mostro la lista y llego esta peticion, otro
            # administrador pudo haberlo vinculado.
            usuario = repository.obtener_usuario_vinculable(db, datos.usuario_id)
            if usuario is None:
                raise UsuarioNoVinculable(str(datos.usuario_id))

            # La cuenta pasa a tener el rol del cargo. Sus tokens vigentes
            # llevan el rol viejo y no llevan sucursal, asi que hay que
            # revocarlos o seguiria operando con el ambito anterior.
            usuario.rol_id = rol.id
            repositorio_seguridad.revocar_sesiones_de_usuario(db, usuario.id)
        else:
            if repository.obtener_usuario_por_correo(db, datos.correo) is not None:
                raise CorreoYaRegistrado(datos.correo)

            usuario = repository.agregar_usuario(
                db,
                correo=datos.correo,
                hash_contrasena=hash_password(datos.contrasena),
                nombres=datos.nombres,
                apellidos=datos.apellidos,
                rol_id=rol.id,
            )

        empleado = repository.agregar_empleado(
            db,
            usuario_id=usuario.id,
            sucursal_id=datos.sucursal_id,
            documento=datos.documento,
            telefono=datos.telefono,
            cargo=datos.cargo,
            fecha_ingreso=datos.fecha_ingreso,
        )
        db.commit()
    except IntegrityError as exc:
        # Entre la verificacion y el commit puede colarse otra alta con el
        # mismo documento o el mismo correo. Las restricciones UNIQUE son las
        # que lo impiden de verdad; las consultas previas solo sirven para dar
        # un mensaje claro en el caso normal. Sin este bloque, esa carrera
        # devolveria un 500.
        db.rollback()
        if _viola(exc, "uq_empleado_documento"):
            raise DocumentoYaRegistrado(datos.documento) from exc
        if _viola(exc, "uq_usuario_correo"):
            raise CorreoYaRegistrado(datos.correo or "") from exc
        raise
    except Exception:
        # Excepcion E3: cualquier otro fallo deja la base como estaba.
        db.rollback()
        raise

    return obtener_empleado(db, empleado.id)


# --- Flujo alternativo 3a: editar y reasignar ----------------------------

def editar_empleado(
    db: Session, empleado_id: int, datos: EmpleadoEditarIn
) -> EmpleadoOut:
    """Modifica los datos del empleado o lo reasigna a otra sucursal.

    Cuando cambia el cargo o la sucursal hay que tocar tambien el usuario
    vinculado, y revocar sus sesiones. El rol y el `sucursal_id` viajan DENTRO
    del token: sin revocar, un Encargado reasignado seguiria operando sobre su
    sucursal anterior hasta que el token venza unas horas despues, que es un
    agujero de ambito, no una demora cosmetica.
    """
    empleado = repository.obtener_empleado(db, empleado_id)
    if empleado is None:
        raise EmpleadoInexistente(str(empleado_id))

    if datos.sucursal_id is not None and datos.sucursal_id != empleado.sucursal_id:
        _validar_sucursal(db, datos.sucursal_id)

    if datos.documento is not None and repository.existe_documento(
        db, datos.documento, excepto_empleado_id=empleado_id
    ):
        raise DocumentoYaRegistrado(datos.documento)

    cambia_cargo = datos.cargo is not None and datos.cargo != empleado.cargo
    cambia_sucursal = (
        datos.sucursal_id is not None and datos.sucursal_id != empleado.sucursal_id
    )

    rol = None
    if cambia_cargo:
        rol = repository.obtener_rol_por_nombre(db, ROL_DE_CARGO[datos.cargo])
        if rol is None:
            raise RolInexistente(ROL_DE_CARGO[datos.cargo])

    if (
        datos.fecha_ingreso is not None
        and empleado.fecha_baja is not None
        and datos.fecha_ingreso > empleado.fecha_baja
    ):
        raise FechaDeBajaInvalida(str(datos.fecha_ingreso))

    try:
        if datos.documento is not None:
            empleado.documento = datos.documento
        if "telefono" in datos.model_fields_set:
            empleado.telefono = datos.telefono
        if datos.cargo is not None:
            empleado.cargo = datos.cargo
        if datos.sucursal_id is not None:
            empleado.sucursal_id = datos.sucursal_id
        if datos.fecha_ingreso is not None:
            empleado.fecha_ingreso = datos.fecha_ingreso

        usuario = repository.obtener_usuario(db, empleado.usuario_id)
        if datos.nombres is not None:
            usuario.nombres = datos.nombres
        if datos.apellidos is not None:
            usuario.apellidos = datos.apellidos
        if rol is not None:
            usuario.rol_id = rol.id

        if cambia_cargo or cambia_sucursal:
            repositorio_seguridad.revocar_sesiones_de_usuario(db, usuario.id)

        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, "uq_empleado_documento"):
            raise DocumentoYaRegistrado(datos.documento or "") from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener_empleado(db, empleado_id)


# --- Flujo alternativo 3b: dar de baja -----------------------------------

def dar_de_baja(db: Session, empleado_id: int, datos: BajaEmpleadoIn) -> EmpleadoOut:
    """Registra la fecha de baja y desactiva la cuenta del empleado.

    Desactivar sin revocar los tokens no cortaria el acceso: el token ya
    emitido seguiria siendo valido hasta vencer. Es el mismo razonamiento del
    CU-03 al desactivar una cuenta.
    """
    empleado = repository.obtener_empleado(db, empleado_id)
    if empleado is None:
        raise EmpleadoInexistente(str(empleado_id))
    if empleado.fecha_baja is not None:
        raise EmpleadoYaDadoDeBaja(str(empleado_id))

    fecha = datos.fecha_baja or date.today()
    if fecha < empleado.fecha_ingreso:
        raise FechaDeBajaInvalida(str(fecha))

    try:
        empleado.fecha_baja = fecha

        usuario = repository.obtener_usuario(db, empleado.usuario_id)
        usuario.activo = False
        repositorio_seguridad.revocar_sesiones_de_usuario(db, usuario.id)

        db.commit()
    except Exception:
        db.rollback()
        raise

    return obtener_empleado(db, empleado_id)
