"""
P12 - Plataforma SaaS  |  capa: servicio

CU-01 Gestionar empresas. Lo opera el administrador de la plataforma, en modo
plataforma (ve todas las empresas: ver app/core/tenencia.py).

EL ALTA ES UNA SOLA TRANSACCIÓN (paso 5 y alternativo 5a)
----------------------------------------------------------
Empresa, suscripción, sucursal principal con su caja y administrador se crean
juntos o no se crea nada. Una empresa sin administrador no la puede operar
nadie, y una sin suscripción quedaría en modo solo consulta desde el primer
minuto.

Para escribir las filas de la empresa nueva, la sesión pasa del modo
plataforma a esa empresa apenas se conoce su id: así el DEFAULT de
`empresa_id` y el WITH CHECK del RLS hacen su trabajo igual que para cualquier
empresa, y no hay un camino especial que se salte la política.

EL CORREO VA DESPUÉS DEL COMMIT
-------------------------------
Si el correo falla, la empresa ya existe y se devuelve la contraseña temporal
en la respuesta, una sola vez. Revertir el alta porque Brevo no respondió
dejaría sin empresa a alguien que ya pagó.
"""

import logging
import secrets
import string
from datetime import time, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import tiempo
from app.core.config import settings
from app.core.security import hash_password
from app.core.tenencia import EMPRESA_DE_BAJA, fijar_empresa, modo_plataforma
from app.integrations.correo import ErrorDeEnvio, Mensaje, enviar
from app.modules.organizacion.models import Ciudad, Sucursal
from app.modules.plataforma.models import Empresa, Plan, Suscripcion
from app.modules.plataforma.suscripciones import estado_efectivo, registrar_pago
from app.modules.plataforma.schemas import (
    EmpresaCrearIn,
    EmpresaCreadaOut,
    EmpresaEditarIn,
    EmpresaOut,
    SuscripcionResumenOut,
)
from app.modules.seguridad.models import Rol, SesionToken, Usuario
from app.modules.ventas.models import Caja

_log = logging.getLogger(__name__)

ROL_ADMINISTRADOR = "ADMINISTRADOR"
EMPRESA_ACTIVA = "ACTIVA"
#: El horario con el que nace la sucursal principal. El administrador de la
#: empresa lo ajusta después (CU-09).
APERTURA, CIERRE = time(9), time(20)


class ErrorDePlataforma(Exception):
    """Base de los errores previstos del CU-01."""


class EmpresaInexistente(ErrorDePlataforma):
    pass


class SlugRepetido(ErrorDePlataforma):
    """Alternativo 4a: el slug ya lo usa otra empresa (RN-14)."""


class CorreoYaRegistrado(ErrorDePlataforma):
    """El correo del administrador ya tiene cuenta en la plataforma."""


class PlanInexistente(ErrorDePlataforma):
    pass


class CiudadInexistente(ErrorDePlataforma):
    pass


# --------------------------------------------------------------------------
#  Lectura
# --------------------------------------------------------------------------
def _resumenes(db: Session, empresas: list[Empresa]) -> list[EmpresaOut]:
    """Arma las filas con su suscripción vigente y sus conteos, en tres consultas."""
    ids = [e.id for e in empresas]
    if not ids:
        return []
    # La actual de cada empresa; si no tiene, la última (vencida). Por id
    # descendente la actual va primero: cambiar de plan siempre abre una fila
    # nueva, y la reemplazada queda con un id menor.
    suscripciones: dict[int, tuple[Suscripcion, Plan]] = {}
    for s, p in db.execute(
        select(Suscripcion, Plan)
        .join(Plan, Plan.id == Suscripcion.plan_id)
        .where(Suscripcion.empresa_id.in_(ids), Suscripcion.estado != "REEMPLAZADA")
        .order_by(Suscripcion.id.desc())
    ).all():
        suscripciones.setdefault(s.empresa_id, (s, p))
    hoy = tiempo.hoy()
    sucursales = dict(
        db.execute(
            select(Sucursal.empresa_id, func.count())
            .where(Sucursal.empresa_id.in_(ids), Sucursal.activa.is_(True))
            .group_by(Sucursal.empresa_id)
        ).all()
    )
    usuarios = dict(
        db.execute(
            select(Usuario.empresa_id, func.count())
            .where(Usuario.empresa_id.in_(ids), Usuario.activo.is_(True))
            .group_by(Usuario.empresa_id)
        ).all()
    )

    filas = []
    for e in empresas:
        par = suscripciones.get(e.id)
        filas.append(
            EmpresaOut(
                id=e.id,
                nombre=e.nombre,
                razon_social=e.razon_social,
                nit=e.nit,
                slug=e.slug,
                correo_contacto=e.correo_contacto,
                estado=e.estado,
                creado_en=e.creado_en,
                suscripcion=(
                    SuscripcionResumenOut(
                        plan_codigo=par[1].codigo,
                        plan_nombre=par[1].nombre,
                        inicio=par[0].inicio,
                        vencimiento=par[0].vencimiento,
                        estado=estado_efectivo(par[0], hoy),
                    )
                    if par
                    else None
                ),
                sucursales=sucursales.get(e.id, 0),
                usuarios=usuarios.get(e.id, 0),
            )
        )
    return filas


def listar_empresas(db: Session, *, busqueda: str | None = None) -> list[EmpresaOut]:
    """Paso 2: las empresas con su slug, su plan y su estado."""
    consulta = select(Empresa).order_by(Empresa.nombre)
    if busqueda:
        patron = f"%{busqueda.strip().lower()}%"
        consulta = consulta.where(
            func.lower(Empresa.nombre).like(patron) | Empresa.slug.like(patron)
        )
    return _resumenes(db, list(db.scalars(consulta)))


def obtener_empresa(db: Session, empresa_id: int) -> EmpresaOut:
    empresa = db.get(Empresa, empresa_id)
    if empresa is None:
        raise EmpresaInexistente(str(empresa_id))
    return _resumenes(db, [empresa])[0]


# --------------------------------------------------------------------------
#  Alta (flujo principal)
# --------------------------------------------------------------------------
def _contrasena_temporal() -> str:
    """Diez caracteres con letras y dígitos: cumple la regla del RNF01."""
    alfabeto = string.ascii_letters + string.digits
    while True:
        clave = "".join(secrets.choice(alfabeto) for _ in range(10))
        if any(c.isalpha() for c in clave) and any(c.isdigit() for c in clave):
            return clave


def _correo_de_acceso(empresa: Empresa, correo: str, clave: str) -> Mensaje:
    url = settings.WEB_BASE_URL.rstrip("/")
    texto = (
        f"Se dio de alta la empresa {empresa.nombre} en Violet Boutique.\n\n"
        f"Ingrese en {url}/login con estos datos:\n"
        f"  Empresa (slug): {empresa.slug}\n"
        f"  Correo: {correo}\n"
        f"  Contraseña temporal: {clave}\n\n"
        "Cámbiela apenas ingrese."
    )
    html = (
        f"<p>Se dio de alta la empresa <strong>{empresa.nombre}</strong> en Violet Boutique.</p>"
        f"<p>Ingrese en <a href=\"{url}/login\">{url}/login</a> con estos datos:</p>"
        f"<ul><li>Empresa (slug): <strong>{empresa.slug}</strong></li>"
        f"<li>Correo: {correo}</li><li>Contraseña temporal: <strong>{clave}</strong></li></ul>"
        "<p>Cámbiela apenas ingrese.</p>"
    )
    return Mensaje(
        destinatario=correo,
        asunto=f"Acceso a {empresa.nombre} en Violet Boutique",
        cuerpo_texto=texto,
        cuerpo_html=html,
    )


def crear_empresa(db: Session, datos: EmpresaCrearIn) -> EmpresaCreadaOut:
    """Pasos 4 a 6 del CU-01. **Hace commit.**"""
    # Paso 4: validar. Lo que no depende de la empresa nueva, antes de escribir.
    if db.scalar(select(Empresa.id).where(Empresa.slug == datos.slug)) is not None:
        raise SlugRepetido(datos.slug)
    # El correo del administrador no se valida contra las demás empresas: es
    # único por empresa (CU-06), y la empresa nueva todavía no tiene a nadie.
    correo = datos.administrador.correo.lower()
    plan = db.scalar(
        select(Plan).where(Plan.codigo == datos.plan_codigo.upper(), Plan.activo.is_(True))
    )
    if plan is None:
        raise PlanInexistente(datos.plan_codigo)
    if db.get(Ciudad, datos.sucursal.ciudad_id) is None:
        raise CiudadInexistente(str(datos.sucursal.ciudad_id))
    rol = db.scalar(select(Rol).where(Rol.nombre == ROL_ADMINISTRADOR))

    clave = _contrasena_temporal()
    # Paso 5: todo en una transacción.
    try:
        empresa = Empresa(
            nombre=datos.nombre,
            razon_social=datos.razon_social,
            nit=datos.nit,
            slug=datos.slug,
            correo_contacto=datos.correo_contacto,
        )
        db.add(empresa)
        db.flush()

        # Desde acá, lo que se escribe es de la empresa nueva.
        fijar_empresa(db, empresa.id)
        inicio = tiempo.hoy()
        suscripcion = Suscripcion(
            plan_id=plan.id,
            inicio=inicio,
            vencimiento=inicio + timedelta(days=plan.duracion_dias),
        )
        db.add(suscripcion)
        db.flush()
        # CU-03, paso 4: el alta también deja su pago simulado.
        registrar_pago(db, suscripcion, plan, "ALTA")
        sucursal = Sucursal(
            ciudad_id=datos.sucursal.ciudad_id,
            nombre=datos.sucursal.nombre,
            direccion=datos.sucursal.direccion,
            horario_apertura=APERTURA,
            horario_cierre=CIERRE,
        )
        db.add(sucursal)
        db.flush()
        db.add(Caja(sucursal_id=sucursal.id, nombre="Caja 1", activa=True))
        db.add(
            Usuario(
                correo=correo,
                hash_contrasena=hash_password(clave),
                nombres=datos.administrador.nombres,
                apellidos=datos.administrador.apellidos,
                rol_id=rol.id,
            )
        )
        db.commit()
    except IntegrityError as error:
        # Alternativo 5a: entre la validación y el commit se coló otra alta con
        # el mismo slug o el mismo correo. No queda nada a medias.
        db.rollback()
        mensaje = str(error.orig)
        if "uq_empresa_slug" in mensaje:
            raise SlugRepetido(datos.slug) from error
        if "uq_usuario_empresa_correo" in mensaje:
            raise CorreoYaRegistrado(correo) from error
        raise
    finally:
        modo_plataforma(db)

    # Paso 6: el acceso por correo, después del commit.
    correo_enviado = True
    try:
        enviar(_correo_de_acceso(empresa, correo, clave))
    except ErrorDeEnvio as error:
        correo_enviado = False
        _log.warning("No se pudo enviar el acceso de la empresa %s: %s", empresa.slug, error)

    resumen = obtener_empresa(db, empresa.id)
    return EmpresaCreadaOut(
        **resumen.model_dump(),
        administrador_correo=correo,
        contrasena_temporal=clave,
        correo_enviado=correo_enviado,
    )


# --------------------------------------------------------------------------
#  Alternativos 3a y 3b
# --------------------------------------------------------------------------
def editar_empresa(db: Session, empresa_id: int, datos: EmpresaEditarIn) -> EmpresaOut:
    """3a: todo menos el slug, que no se cambia (RN-14)."""
    empresa = db.get(Empresa, empresa_id)
    if empresa is None:
        raise EmpresaInexistente(str(empresa_id))
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        if campo == "nombre" and valor is None:
            continue
        setattr(empresa, campo, valor)
    db.commit()
    return obtener_empresa(db, empresa_id)


def cambiar_estado(db: Session, empresa_id: int, *, activa: bool) -> EmpresaOut:
    """3b: dar de baja no borra nada; corta el acceso de todos sus usuarios.

    Además de rechazar los logins nuevos (ver `seguridad.service.autenticar`),
    revoca las sesiones vigentes: sin eso, un token emitido antes de la baja
    seguiría sirviendo hasta expirar.
    """
    empresa = db.get(Empresa, empresa_id)
    if empresa is None:
        raise EmpresaInexistente(str(empresa_id))
    empresa.estado = EMPRESA_ACTIVA if activa else EMPRESA_DE_BAJA
    if not activa:
        db.execute(
            update(SesionToken)
            .where(
                SesionToken.revocado_en.is_(None),
                SesionToken.usuario_id.in_(
                    select(Usuario.id).where(Usuario.empresa_id == empresa_id)
                ),
            )
            .values(revocado_en=tiempo.ahora())
        )
    db.commit()
    return obtener_empresa(db, empresa_id)
