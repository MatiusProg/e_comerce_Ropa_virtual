"""
P17 - Roles y permisos por empresa / CU-41  |  capa: servicio

RF-64: el administrador de la empresa crea roles propios, les asigna permisos
y se los asigna a su personal, sin afectar a las otras empresas y dentro de lo
que permite su plan.

REGLAS QUE CUIDA ESTE SERVICIO
------------------------------
- Un rol propio parte de un rol base y solo conserva permisos DE ESE rol base
  (ver `app/core/permisos.py`): nunca da más de lo que el rol base ya da.
- RN-22: un permiso que es una función del plan no entra en un rol si el plan
  de la empresa no la incluye (403 `plan_limit`, como cualquier CU-05).
- Gestionar usuarios y gestionar roles no se delegan: quien los tuviera podría
  darse a sí mismo cualquier otro permiso.
- Al personal solo se le asigna un rol propio de SU rol base: un cajero no
  pasa a ser encargado por un rol propio.
- El administrador no se asigna un rol propio a sí mismo: se quedaría afuera
  de esta misma pantalla.
- Un rol con personas asignadas no se apaga: antes hay que reasignarlas, para
  que nadie pierda o gane permisos sin que el administrador lo vea.

El rol propio se lee de la base en cada petición (`get_usuario_actual`), así
que un cambio de permisos vale desde la petición siguiente.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import permisos as catalogo
from app.modules.organizacion.models import Empleado, Sucursal
from app.modules.plataforma import verificador
from app.modules.roles.models import RolEmpresa, RolEmpresaPermiso
from app.modules.roles.schemas import (
    AsignacionIn,
    PermisoOut,
    PersonaOut,
    RolEditarIn,
    RolIn,
    RolOut,
)
from app.modules.seguridad.models import Rol, Usuario


class ErrorDeRoles(Exception):
    def __init__(self, mensaje: str, codigo: int = 400) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


# =====================================================================
#  El catálogo
# =====================================================================

def catalogo_de_permisos(db: Session) -> list[PermisoOut]:
    """Los permisos que se pueden poner en un rol propio, con RN-22 resuelto."""
    return [
        PermisoOut(
            codigo=p.codigo,
            nombre=p.nombre,
            area=p.area,
            roles_base=list(p.roles_base),
            funcion=p.funcion,
            incluido_en_plan=p.funcion is None or verificador.incluye(db, p.funcion),
        )
        for p in catalogo.CATALOGO
        if p.asignable
    ]


def _validar_permisos(db: Session, rol_base: str, codigos: list[str]) -> list[str]:
    limpios = sorted(set(codigos))
    for codigo in limpios:
        permiso = catalogo.POR_CODIGO.get(codigo)
        if permiso is None:
            raise ErrorDeRoles(f"El permiso «{codigo}» no existe.", 422)
        if not permiso.asignable:
            raise ErrorDeRoles(f"«{permiso.nombre}» no se puede delegar en un rol propio.", 422)
        if rol_base not in permiso.roles_base:
            raise ErrorDeRoles(
                f"«{permiso.nombre}» no es de un {rol_base.lower()}: un rol propio no da "
                "más de lo que da su rol base.",
                422,
            )
        if permiso.funcion is not None:
            # RN-22. Rechaza con el 403 `plan_limit` de siempre (CU-05).
            verificador.verificar_funcion(db, permiso.funcion)
    return limpios


# =====================================================================
#  Roles
# =====================================================================

def _personas_por_rol(db: Session) -> dict[int, int]:
    filas = db.execute(
        select(Usuario.rol_empresa_id, func.count(Usuario.id))
        .where(Usuario.rol_empresa_id.is_not(None))
        .group_by(Usuario.rol_empresa_id)
    ).all()
    return {r: n for r, n in filas}


def _armar(rol: RolEmpresa, personas: int) -> RolOut:
    return RolOut(
        id=rol.id,
        nombre=rol.nombre,
        descripcion=rol.descripcion,
        rol_base=rol.rol_base,
        activo=rol.activo,
        permisos=sorted(p.permiso for p in rol.permisos),
        personas=personas,
    )


def listar(db: Session) -> list[RolOut]:
    personas = _personas_por_rol(db)
    roles = db.scalars(select(RolEmpresa).order_by(RolEmpresa.rol_base, RolEmpresa.nombre))
    return [_armar(r, personas.get(r.id, 0)) for r in roles]


def _rol(db: Session, rol_id: int) -> RolEmpresa:
    rol = db.get(RolEmpresa, rol_id)
    if rol is None:
        raise ErrorDeRoles("El rol no existe.", 404)
    return rol


def _nombre_libre(db: Session, nombre: str, excepto: int | None = None) -> None:
    consulta = select(RolEmpresa.id).where(func.lower(RolEmpresa.nombre) == nombre.lower())
    if excepto is not None:
        consulta = consulta.where(RolEmpresa.id != excepto)
    if db.scalar(consulta.limit(1)) is not None:
        raise ErrorDeRoles(f"Ya hay un rol que se llama «{nombre}».", 409)


def _poner_permisos(rol: RolEmpresa, codigos: list[str]) -> None:
    actuales = {p.permiso: p for p in rol.permisos}
    for codigo in list(actuales):
        if codigo not in codigos:
            rol.permisos.remove(actuales[codigo])
    for codigo in codigos:
        if codigo not in actuales:
            rol.permisos.append(RolEmpresaPermiso(permiso=codigo))


def crear(db: Session, datos: RolIn) -> RolOut:
    """Alta. **Hace commit.**"""
    _nombre_libre(db, datos.nombre)
    codigos = _validar_permisos(db, datos.rol_base, datos.permisos)
    rol = RolEmpresa(nombre=datos.nombre, descripcion=datos.descripcion, rol_base=datos.rol_base)
    _poner_permisos(rol, codigos)
    db.add(rol)
    db.commit()
    db.refresh(rol)
    return _armar(rol, 0)


def editar(db: Session, rol_id: int, datos: RolEditarIn) -> RolOut:
    """Edición parcial. **Hace commit.** El rol base no se cambia."""
    rol = _rol(db, rol_id)
    if datos.nombre is not None:
        nombre = " ".join(datos.nombre.split())
        _nombre_libre(db, nombre, excepto=rol_id)
        rol.nombre = nombre
    if datos.descripcion is not None:
        rol.descripcion = datos.descripcion or None
    if datos.permisos is not None:
        _poner_permisos(rol, _validar_permisos(db, rol.rol_base, datos.permisos))
    db.commit()
    db.refresh(rol)
    return _armar(rol, _personas_por_rol(db).get(rol.id, 0))


def cambiar_estado(db: Session, rol_id: int, activo: bool) -> RolOut:
    """Encender o apagar. **Hace commit.**"""
    rol = _rol(db, rol_id)
    personas = _personas_por_rol(db).get(rol.id, 0)
    if not activo and personas:
        raise ErrorDeRoles(
            f"El rol tiene {personas} persona{'s' if personas != 1 else ''} asignada"
            f"{'s' if personas != 1 else ''}. Reasígnelas antes de desactivarlo.",
            409,
        )
    rol.activo = activo
    db.commit()
    return _armar(rol, personas)


# =====================================================================
#  El personal
# =====================================================================

def _consulta_personal(empresa_id: int):
    return (
        select(
            Usuario.id,
            Usuario.nombres,
            Usuario.apellidos,
            Usuario.correo,
            Rol.nombre.label("rol_base"),
            Sucursal.nombre.label("sucursal"),
            Usuario.rol_empresa_id,
            RolEmpresa.nombre.label("rol_empresa"),
        )
        .join(Rol, Rol.id == Usuario.rol_id)
        .outerjoin(
            Empleado, (Empleado.usuario_id == Usuario.id) & Empleado.fecha_baja.is_(None)
        )
        .outerjoin(Sucursal, Sucursal.id == Empleado.sucursal_id)
        .outerjoin(RolEmpresa, RolEmpresa.id == Usuario.rol_empresa_id)
        # `usuario` no está bajo RLS (el cliente es de la plataforma): la
        # empresa se filtra a mano.
        .where(Usuario.empresa_id == empresa_id, Rol.nombre.in_(catalogo.ROLES_BASE))
    )


def _persona(f) -> PersonaOut:
    return PersonaOut(
        usuario_id=f.id,
        nombre=f"{f.nombres} {f.apellidos}".strip(),
        correo=f.correo,
        rol_base=f.rol_base,
        sucursal=f.sucursal,
        rol_empresa_id=f.rol_empresa_id,
        rol_empresa=f.rol_empresa,
    )


def personal(db: Session, empresa_id: int) -> list[PersonaOut]:
    filas = db.execute(
        _consulta_personal(empresa_id).order_by(Rol.nombre, Usuario.apellidos, Usuario.nombres)
    ).all()
    return [_persona(f) for f in filas]


def asignar(db: Session, empresa_id: int, quien_id: int, datos: AsignacionIn) -> PersonaOut:
    """Pone o quita el rol propio de alguien del personal. **Hace commit.**"""
    fila = db.execute(
        _consulta_personal(empresa_id).where(Usuario.id == datos.usuario_id)
    ).first()
    if fila is None:
        raise ErrorDeRoles("Esa persona no es del personal de la empresa.", 404)
    if datos.usuario_id == quien_id and datos.rol_empresa_id is not None:
        raise ErrorDeRoles(
            "No puede asignarse un rol propio a sí mismo: perdería el acceso a esta pantalla.",
            409,
        )
    if datos.rol_empresa_id is not None:
        rol = _rol(db, datos.rol_empresa_id)
        if not rol.activo:
            raise ErrorDeRoles("El rol está desactivado.", 409)
        if rol.rol_base != fila.rol_base:
            raise ErrorDeRoles(
                f"«{rol.nombre}» es un rol de {rol.rol_base.lower()} y esta persona es "
                f"{fila.rol_base.lower()}.",
                422,
            )
    usuario = db.get(Usuario, datos.usuario_id)
    usuario.rol_empresa_id = datos.rol_empresa_id
    db.commit()
    return _persona(
        db.execute(_consulta_personal(empresa_id).where(Usuario.id == datos.usuario_id)).first()
    )
