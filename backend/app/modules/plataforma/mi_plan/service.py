"""
P12 - Plataforma SaaS / CU-04  |  capa: servicio

2do parcial. Caso de uso: CU-04 Consultar plan y consumo.

Arma la vista del plan de la empresa: la suscripción, cada límite con su uso y
las funciones incluidas y no incluidas. No modifica ningún dato.
"""
from sqlalchemy.orm import Session

from app.core import tiempo
from app.modules.plataforma.mi_plan import repository
from app.modules.plataforma.mi_plan.schemas import (
    FuncionOut,
    LimiteOut,
    MiPlanOut,
    PlanOut,
    SuscripcionOut,
)
from app.modules.plataforma.models import Plan, Suscripcion


class ErrorDeMiPlan(Exception):
    """Base de los errores previstos del CU-04."""


class SinEmpresa(ErrorDeMiPlan):
    """El usuario no pertenece a ninguna empresa (el de la plataforma)."""


#: Nombre en pantalla de cada clave de `plan.funciones`, en el orden de la
#: tabla de planes del Word (sección 2.1.1). Una clave que no esté acá se
#: muestra con su código: así una función nueva aparece sin tocar este archivo.
ETIQUETAS_FUNCIONES = {
    "reportes_ia": "Reportes generativos con IA",
    "correo": "Avisos por correo a clientes y empleados",
    "ia_cliente": "Recomendaciones y asistente virtual con IA",
    "marca_propia": "Tienda en línea con el logo y los colores de la empresa",
    "traspasos_sugeridos": "Traspasos sugeridos por lo más vendido",
    "foto_ia": "Foto realista con IA en el probador",
    "analitica_ml": "Analítica con ML y su dashboard",
    "exportar_datos": "Exportación completa de los datos de la empresa",
    "bitacora_dias": "Historial de la bitácora",
    "respaldo_intervalo_horas": "Copias de seguridad manuales",
    "respaldo_retencion": "Copias automáticas que se conservan",
}


def _detalle(codigo: str, valor) -> tuple[bool, str | None]:
    """Traduce el valor de una función a (incluida, detalle).

    Las numéricas no son sí o no: el valor dice cuánto, y None es sin límite.
    """
    if isinstance(valor, bool):
        return valor, None
    if codigo == "bitacora_dias":
        return True, "Completo" if valor is None else f"{valor} días"
    if codigo == "respaldo_intervalo_horas":
        if valor is None:
            return True, "A voluntad"
        return True, "Una por día" if valor == 24 else f"Una cada {valor // 24} días"
    if codigo == "respaldo_retencion":
        return True, "Sin límite" if valor is None else f"Las últimas {valor}"
    if valor is None:
        return True, "Sin límite"
    return bool(valor), str(valor)


def _funciones(plan: Plan) -> list[FuncionOut]:
    datos = plan.funciones or {}
    orden = [c for c in ETIQUETAS_FUNCIONES if c in datos] + [
        c for c in datos if c not in ETIQUETAS_FUNCIONES
    ]
    salida = []
    for codigo in orden:
        incluida, detalle = _detalle(codigo, datos[codigo])
        salida.append(
            FuncionOut(
                codigo=codigo,
                etiqueta=ETIQUETAS_FUNCIONES.get(codigo, codigo),
                incluida=incluida,
                detalle=detalle,
            )
        )
    return salida


def _plan(plan: Plan) -> PlanOut:
    return PlanOut(
        id=plan.id,
        codigo=plan.codigo,
        nombre=plan.nombre,
        precio_mensual=plan.precio_mensual,
        duracion_dias=plan.duracion_dias,
        max_sucursales=plan.max_sucursales,
        max_empleados=plan.max_empleados,
        cupo_reportes_ia=plan.cupo_reportes_ia,
        cupo_fotos_ia=plan.cupo_fotos_ia,
        funciones=_funciones(plan),
    )


def _limite(codigo: str, etiqueta: str, usado: int | None, limite: int | None) -> LimiteOut:
    alcanzado = usado is not None and limite is not None and usado >= limite
    return LimiteOut(
        codigo=codigo, etiqueta=etiqueta, usado=usado, limite=limite, alcanzado=alcanzado
    )


def _suscripcion(suscripcion: Suscripcion) -> SuscripcionOut:
    hoy = tiempo.hoy()
    dias = (suscripcion.vencimiento - hoy).days
    # Una VIGENTE cuya fecha ya pasó pero que el proceso diario todavía no
    # marcó como VENCIDA (CU-03, E1) también es solo consulta.
    solo_consulta = suscripcion.estado != "VIGENTE" or dias < 0
    return SuscripcionOut(
        estado="VENCIDA" if suscripcion.estado == "VIGENTE" and dias < 0 else suscripcion.estado,
        inicio=suscripcion.inicio,
        vencimiento=suscripcion.vencimiento,
        dias_restantes=dias,
        solo_consulta=solo_consulta,
    )


def consultar_mi_plan(db: Session, empresa_id: int | None) -> MiPlanOut:
    """Flujo principal del CU-04, pasos 2 a 4."""
    if empresa_id is None:
        raise SinEmpresa()
    empresa = repository.obtener_empresa(db, empresa_id)
    if empresa is None:
        raise SinEmpresa()

    suscripcion = repository.obtener_suscripcion_actual(db)
    plan = suscripcion.plan if suscripcion is not None else None

    sucursales = repository.contar_sucursales_activas(db)
    empleados = repository.contar_empleados_activos(db)
    limites = [
        _limite("sucursales", "Sucursales activas", sucursales,
                plan.max_sucursales if plan else None),
        _limite("empleados", "Empleados activos", empleados,
                plan.max_empleados if plan else None),
    ]
    # Los cupos del mes se miden desde el CU-27 (reportes con IA) y el CU-38
    # (foto realista): mientras no existan, el uso es None y no un 0 que
    # mentiría.
    cupos = [
        _limite("reportes_ia", "Reportes con IA del mes", None,
                plan.cupo_reportes_ia if plan else None),
        _limite("fotos_ia", "Fotos realistas con IA del mes", None,
                plan.cupo_fotos_ia if plan else None),
    ]

    return MiPlanOut(
        empresa=empresa.nombre,
        slug=empresa.slug,
        suscripcion=_suscripcion(suscripcion) if suscripcion is not None else None,
        plan=_plan(plan) if plan is not None else None,
        limites=limites,
        cupos=cupos,
        otros_planes=[
            _plan(p) for p in repository.listar_planes_activos(db)
            if plan is None or p.id != plan.id
        ],
    )
