"""
P10 - Inteligencia Artificial / CU-33  |  capa: servicio

Realiza el **RF25**: «el sistema deberá proporcionar al menos una funcionalidad
basada en inteligencia artificial». Es el único de los tres casos de uso de
P10 que se construyó — CU-34 y CU-35 son los que el plan deja caer primero.

EL ENFOQUE HÍBRIDO, Y POR QUÉ NO SE LE PIDE AL MODELO QUE ELIJA
----------------------------------------------------------------
Los tres pasos de la decisión técnica, en orden:

1. **Un filtro determinista en SQL** saca las candidatas: temporada vigente,
   existencia real, talla del cliente, categorías que le interesan.
2. **El modelo las ORDENA** y escribe una línea que explica cada una.
3. **Si el modelo falla, se muestra el paso 1** ordenado por popularidad.

La decisión de fondo está en el paso 1. Un modelo al que se le pide
«recomendale algo a esta clienta» inventa prendas que no existen y recomienda
tallas agotadas, y eso en una tienda no es un resultado malo: es una promesa
que no se puede cumplir. Filtrando primero, **lo peor que puede hacer el
modelo es ordenar mal**.

POR QUÉ SE GUARDA EL RESULTADO
-------------------------------
El paso 2 tarda segundos, depende de un tercero y consume cuota. Sin guardar,
entrar y salir cinco veces de la pantalla de inicio son cinco llamadas — y el
riesgo R9 del plan es justamente quedarse sin crédito antes de la defensa.

NADA DE ESTO PUEDE DEJAR LA PANTALLA VACÍA
-------------------------------------------
Es la regla que gobierna todo el módulo. Sin talla cargada, sin categorías
elegidas, sin historial, sin modelo o sin cuota, el cliente recibe
recomendaciones igual. Lo que se pierde es la personalización, nunca la
funcionalidad.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.integrations import recomendador
from app.integrations.recomendador import (
    Candidata,
    ErrorDelRecomendador,
    PerfilDelCliente,
)
from app.modules.ia import repository
from app.modules.inventario import service as inventario

_log = logging.getLogger("violetboutique.recomendador")

#: Cuántas prendas se le muestran al cliente.
CUANTAS_SUGERENCIAS = 6

#: Cuántas candidatas se le mandan al modelo.
#:
#: La decisión técnica dice «20 a 30». No más: cada candidata son unos 20
#: tokens y una lista larga hace que el modelo empiece a nombrar productos que
#: no están en ella. No menos: con diez, ordenar deja de aportar sobre el orden
#: por popularidad que ya trae el paso 1.
CUANTAS_CANDIDATAS = 30

#: Cuánto vale la recomendación guardada antes de volver a generarla.
VIGENCIA_HORAS = 12

#: El motor que se anota cuando no hubo modelo.
MOTOR_DEGRADADO = "popularidad"


@dataclass(frozen=True)
class PrendaSugerida:
    producto_id: int
    nombre: str
    categoria: str
    precio_desde: Decimal | None
    imagen_url: str | None
    motivo: str


@dataclass(frozen=True)
class Recomendaciones:
    prendas: list[PrendaSugerida]

    #: Con qué se generó. Viaja hasta la pantalla porque **una sugerencia
    #: hecha por un modelo tiene que poder decir que lo es**: presentarla como
    #: criterio de la tienda sería atribuirle a la tienda algo que no decidió.
    motor: str
    generada_en: datetime


def _perfil(db: Session, cliente) -> tuple[PerfilDelCliente, list[int]]:
    preferidas = repository.categorias_preferidas(db, cliente.id)
    temporada = repository.temporada_vigente(db)
    perfil = PerfilDelCliente(
        talla_habitual=cliente.talla_superior,
        categorias_preferidas=[nombre for _, nombre in preferidas],
        prendas_conocidas=repository.prendas_conocidas(db, cliente.id),
        temporada=temporada.nombre if temporada else None,
    )
    return perfil, [cid for cid, _ in preferidas]


def _candidatas(db: Session, cliente, categoria_ids: list[int]) -> list[Candidata]:
    temporada = repository.temporada_vigente(db)

    filas = repository.candidatas(
        db,
        talla_codigo=cliente.talla_superior,
        categoria_ids=categoria_ids,
        temporada_id=temporada.id if temporada else None,
        limite=CUANTAS_CANDIDATAS * 2,
    )

    # SI LOS FILTROS DEJAN LA LISTA VACÍA, SE AFLOJAN.
    #
    # Pasa con una clienta cuyas categorías preferidas están agotadas, o cuya
    # talla no existe en la temporada vigente. Devolverle nada sería correcto
    # según el filtro y pésimo como producto: la tienda tiene prendas, solo que
    # ninguna cumple las cuatro condiciones a la vez.
    if not filas and (categoria_ids or cliente.talla_superior):
        _log.info(
            "Sin candidatas con los filtros del cliente %s; se aflojan.",
            cliente.id,
        )
        filas = repository.candidatas(
            db,
            talla_codigo=None,
            categoria_ids=[],
            temporada_id=temporada.id if temporada else None,
            limite=CUANTAS_CANDIDATAS * 2,
        )

    # La existencia se pregunta DESPUÉS y en bloque, por la costura C1.
    con_stock = inventario.productos_con_stock(db, [f[0] for f in filas])

    return [
        Candidata(
            producto_id=f[0],
            nombre=f[1],
            categoria=f[2],
            precio_desde=str(f[3] or "—"),
            vendidas=int(f[4] or 0),
        )
        for f in filas
        if f[0] in con_stock
    ][:CUANTAS_CANDIDATAS]


def _por_popularidad(candidatas: list[Candidata]) -> list[dict]:
    """El paso 3: el resultado degradado.

    Sin motivo escrito. Se probó poner uno fijo ---«de lo más vendido de la
    temporada»--- y quedaba peor que nada: repetido seis veces se lee como un
    error de la aplicación, y además le atribuye a la tienda una razón que
    nadie eligió. La pantalla muestra la prenda sola.
    """
    return [
        {"producto_id": c.producto_id, "motivo": ""}
        for c in candidatas[:CUANTAS_SUGERENCIAS]
    ]


def _generar(db: Session, cliente) -> tuple[str, list[dict]]:
    perfil, categoria_ids = _perfil(db, cliente)
    candidatas = _candidatas(db, cliente, categoria_ids)
    if not candidatas:
        # No hay NADA que recomendar: ni una prenda activa con stock. Es un
        # catálogo vacío, no un fallo, y se guarda igual para no reintentar.
        return MOTOR_DEGRADADO, []

    try:
        sugerencias = recomendador.ordenar(perfil, candidatas, CUANTAS_SUGERENCIAS)
        return recomendador.nombre_del_proveedor(), [
            {"producto_id": s.producto_id, "motivo": s.motivo} for s in sugerencias
        ]
    except ErrorDelRecomendador as e:
        # DEGRADAR, NO FALLAR. El cliente ve las prendas igual.
        #
        # Se registra como aviso y no como error: que el modelo no esté es un
        # estado previsto del sistema, y anotarlo como error haría que los
        # registros de producción parezcan rotos cuando funcionan como se
        # diseñó.
        _log.warning(
            "El recomendador no ordenó para el cliente %s (%s). Se degrada a "
            "popularidad.",
            cliente.id,
            e,
        )
        return MOTOR_DEGRADADO, _por_popularidad(candidatas)


def _vencida(generada_en: datetime | None) -> bool:
    if generada_en is None:
        return True
    limite = datetime.now(timezone.utc) - timedelta(hours=VIGENCIA_HORAS)
    return generada_en < limite


def recomendaciones(
    db: Session, usuario_id: int, *, forzar: bool = False
) -> Recomendaciones | None:
    """Las prendas recomendadas para quien pregunta.

    Devuelve `None` si el usuario no es un cliente --- un administrador tiene
    usuario pero no perfil de compra, y no hay nada que recomendarle.
    """
    cliente = repository.cliente_de_usuario(db, usuario_id)
    if cliente is None:
        return None

    guardada = repository.guardada(db, cliente.id)
    if not forzar and guardada is not None and not _vencida(guardada.generada_en):
        return _armar(db, guardada.motor, guardada.generada_en, guardada.sugerencias)

    motor, sugerencias = _generar(db, cliente)
    fila = repository.guardar(db, cliente.id, motor, sugerencias)
    db.commit()
    db.refresh(fila)
    return _armar(db, fila.motor, fila.generada_en, fila.sugerencias)


def _armar(
    db: Session, motor: str, generada_en: datetime, sugerencias: list[dict]
) -> Recomendaciones:
    """Convierte lo guardado en prendas con nombre, precio y foto.

    Los datos del producto NO se guardan junto a la sugerencia: se leen del
    catálogo cada vez. Si se guardaran, una prenda que cambió de precio o que
    se descatalogó seguiría mostrándose con los datos de hace doce horas.
    """
    from app.modules.catalogo import imagenes_almacen as almacen
    from app.modules.catalogo_publico import repository as catalogo

    ids = [s.get("producto_id") for s in sugerencias if s.get("producto_id")]
    desde = repository.precio_desde_de(db, ids) if ids else {}
    productos = repository.productos_por_id(db, ids)
    # `Producto` no declara relacion con `Categoria`, asi que el nombre se
    # resuelve con una consulta aparte en vez de por navegacion.
    categorias = repository.nombres_de_categoria(
        db, [p.categoria_id for p in productos.values()]
    )
    principales = catalogo.imagen_principal(db, ids) if ids else {}

    prendas: list[PrendaSugerida] = []
    for sugerencia in sugerencias:
        producto = productos.get(sugerencia.get("producto_id"))
        # Una prenda descatalogada entre la generación y ahora se SALTA. No se
        # regenera todo: la recomendación sigue valiendo con cinco en vez de
        # seis, y regenerar aquí metería una llamada al modelo dentro de una
        # lectura.
        if producto is None or not producto.activo:
            continue
        ruta = principales.get(producto.id)
        prendas.append(
            PrendaSugerida(
                producto_id=producto.id,
                nombre=producto.nombre,
                categoria=categorias.get(producto.categoria_id, "—"),
                precio_desde=desde.get(producto.id),
                imagen_url=almacen.url_de(ruta) if ruta else None,
                motivo=str(sugerencia.get("motivo") or ""),
            )
        )

    return Recomendaciones(prendas=prendas, motor=motor, generada_en=generada_en)


def invalidar(db: Session, cliente_id: int) -> None:
    """Tira la recomendación vigente. **Sin commit.**

    La llama quien cambia el perfil del cliente o registra una compra: lo que
    se le recomendaba se calculó con un perfil que ya no es el suyo.
    """
    repository.invalidar(db, cliente_id)
