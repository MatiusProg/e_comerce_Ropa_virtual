"""
P12 - Plataforma SaaS / CU-11  |  capa: servicio (la clase control GestorContratacion)

2do parcial. Caso de uso: CU-11 Contratar un plan desde la web. El actor es la
empresa interesada, sin sesión.

  2    los planes que se ofrecen, con su precio y sus funciones
  5    validar los datos y que el slug esté libre      (5a: sugerir otros)
  6    simular el pago y emitir el comprobante          (6a: rechazado)
  7    crear la empresa: lo hace GestorEmpresas (CU-01, paso 5)
  8    el correo de bienvenida, y a iniciar sesión con el slug

EL PAGO RECHAZADO NO CREA NADA (6a)
-----------------------------------
Todo lo que se puede validar sin escribir se valida antes de cobrar: el plan,
el slug, la ciudad. Recién entonces se cobra, y solo con el pago aprobado se
crea la empresa, en la transacción del CU-01. Si el cobro se rechaza no se
escribió ninguna fila.

LO QUE SE CREA ES LO MISMO QUE EN EL CU-01 (paso 7)
---------------------------------------------------
No hay un segundo camino de alta: se llama a `service.crear_empresa`, con la
contraseña que eligió el administrador y el comprobante del pago. Así la
empresa contratada por la web nace igual que la que da de alta la plataforma.
"""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import tiempo
from app.modules.organizacion.models import Ciudad
from app.modules.plataforma import service as gestor_empresas
from app.modules.plataforma.contratacion.schemas import (
    CiudadPublicaOut,
    ComprobanteOut,
    ContratacionOut,
    ContratarIn,
    FuncionPublicaOut,
    PlanPublicoOut,
    SlugOut,
)
from app.modules.plataforma.mi_plan.service import ETIQUETAS_FUNCIONES
from app.modules.plataforma.models import Empresa, PagoSimulado, Plan
from app.modules.plataforma.schemas import PATRON_SLUG
from app.modules.plataforma.suscripciones import monto_de, nuevo_comprobante
from app.modules.plataforma.verificador import FUNCIONES

#: Como las tarjetas de prueba de una pasarela: este código simula el rechazo.
CODIGO_RECHAZADO = "000000"
#: Cuántos slugs libres se sugieren cuando el pedido está ocupado (5a).
SUGERENCIAS = 3
LARGO_SLUG = 40


class ErrorDeContratacion(Exception):
    """Error de negocio del CU-11."""


class PlanNoOfrecido(ErrorDeContratacion):
    pass


class SlugOcupado(ErrorDeContratacion):
    """5a: el slug ya lo usa otra empresa. Lleva las sugerencias."""

    def __init__(self, slug: str, sugerencias: list[str]):
        super().__init__(slug)
        self.sugerencias = sugerencias


class CiudadInexistente(ErrorDeContratacion):
    pass


class PagoRechazado(ErrorDeContratacion):
    """6a: el cobro simulado no se aprobó; no se creó nada."""


class CorreoYaRegistrado(ErrorDeContratacion):
    pass


# --------------------------------------------------------------------------
#  Paso 2: los planes
# --------------------------------------------------------------------------
def listar_planes(db: Session) -> list[PlanPublicoOut]:
    planes = db.scalars(
        select(Plan).where(Plan.activo.is_(True)).order_by(Plan.precio_mensual, Plan.id)
    )
    return [
        PlanPublicoOut(
            codigo=p.codigo,
            nombre=p.nombre,
            precio_mensual=float(p.precio_mensual),
            duracion_dias=p.duracion_dias,
            max_sucursales=p.max_sucursales,
            max_empleados=p.max_empleados,
            cupo_reportes_ia=p.cupo_reportes_ia,
            cupo_fotos_ia=p.cupo_fotos_ia,
            bitacora_dias=(p.funciones or {}).get("bitacora_dias"),
            funciones=[
                FuncionPublicaOut(
                    clave=clave,
                    nombre=ETIQUETAS_FUNCIONES.get(clave, clave),
                    incluida=(p.funciones or {}).get(clave) is True,
                )
                for clave in FUNCIONES
            ],
        )
        for p in planes
    ]


def listar_ciudades(db: Session) -> list[CiudadPublicaOut]:
    """Para la sucursal principal. Son de la plataforma, sin datos de nadie."""
    return [
        CiudadPublicaOut(id=c.id, nombre=c.nombre, departamento=c.departamento)
        for c in db.scalars(select(Ciudad).order_by(Ciudad.nombre))
    ]


# --------------------------------------------------------------------------
#  Paso 5 y 5a: el slug
# --------------------------------------------------------------------------
def _ocupados(db: Session, candidatos: list[str]) -> set[str]:
    return set(db.scalars(select(Empresa.slug).where(Empresa.slug.in_(candidatos))))


def _sugerir(db: Session, slug: str) -> list[str]:
    """Variantes libres del slug pedido, con la misma regla (RN-14)."""
    hoy = tiempo.hoy()
    sufijos = ["bo", "tienda", "moda", str(hoy.year), *(str(n) for n in range(2, 10))]
    candidatos = []
    for sufijo in sufijos:
        base = slug[: LARGO_SLUG - len(sufijo) - 1].rstrip("-")
        candidatos.append(f"{base}-{sufijo}")
    ocupados = _ocupados(db, candidatos)
    return [c for c in candidatos if c not in ocupados][:SUGERENCIAS]


def verificar_slug(db: Session, slug: str) -> SlugOut:
    slug = slug.strip().lower()
    if not re.fullmatch(PATRON_SLUG, slug) or len(slug) < 2:
        return SlugOut(slug=slug, disponible=False, sugerencias=[])
    if not _ocupados(db, [slug]):
        return SlugOut(slug=slug, disponible=True, sugerencias=[])
    return SlugOut(slug=slug, disponible=False, sugerencias=_sugerir(db, slug))


# --------------------------------------------------------------------------
#  Pasos 5 a 8: contratar
# --------------------------------------------------------------------------
def _cobrar(datos: ContratarIn) -> str:
    """Paso 6: el cobro simulado. Devuelve el comprobante o rechaza (6a)."""
    if datos.pago.codigo_operacion == CODIGO_RECHAZADO:
        raise PagoRechazado()
    return nuevo_comprobante()


def contratar(db: Session, datos: ContratarIn) -> ContratacionOut:
    """**Hace commit** (el del CU-01), y solo si el pago se aprobó."""
    # Paso 5: lo que se valida sin escribir, antes de cobrar.
    plan = db.scalar(
        select(Plan).where(Plan.codigo == datos.plan_codigo.upper(), Plan.activo.is_(True))
    )
    if plan is None:
        raise PlanNoOfrecido(datos.plan_codigo)
    if _ocupados(db, [datos.slug]):
        raise SlugOcupado(datos.slug, _sugerir(db, datos.slug))
    if db.get(Ciudad, datos.sucursal.ciudad_id) is None:
        raise CiudadInexistente(str(datos.sucursal.ciudad_id))

    # Paso 6, y 6a: rechazado, se corta acá sin haber escrito nada.
    comprobante = _cobrar(datos)

    # Paso 7 y 8: el alta del CU-01, con el correo de bienvenida.
    try:
        creada = gestor_empresas.crear_empresa(
            db,
            datos,
            contrasena=datos.administrador.contrasena,
            comprobante=comprobante,
        )
    except gestor_empresas.SlugRepetido as error:
        # Otra contratación se llevó el slug entre la validación y el commit.
        raise SlugOcupado(datos.slug, _sugerir(db, datos.slug)) from error
    except gestor_empresas.CorreoYaRegistrado as error:
        raise CorreoYaRegistrado(datos.administrador.correo) from error

    pago = db.scalar(select(PagoSimulado).where(PagoSimulado.comprobante == comprobante))
    return ContratacionOut(
        empresa=creada.nombre,
        slug=creada.slug,
        plan=plan.nombre,
        vencimiento=creada.suscripcion.vencimiento,
        administrador_correo=creada.administrador_correo,
        correo_enviado=creada.correo_enviado,
        pago=ComprobanteOut(
            comprobante=comprobante,
            metodo=datos.pago.metodo,
            monto=float(pago.monto if pago else monto_de(plan)),
            pagado_en=pago.pagado_en if pago else tiempo.ahora(),
        ),
    )
