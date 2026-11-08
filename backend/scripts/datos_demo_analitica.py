"""Datos de demostración para la analítica con ML (CU-29, CU-30 y el aporte de anomalías).

PARA QUÉ
--------
Los modelos de demanda y de segmentos ya entrenan con datos sintéticos más los
reales, pero las ANOMALÍAS solo miran datos reales: hacen falta al menos 20
turnos de caja cerrados y 15 devoluciones. Una empresa de demostración recién
armada no los tiene, y en la defensa la pestaña «Anomalías» respondería 409.

Este script carga, en las últimas N semanas y para UNA empresa:

- turnos de caja cerrados en las cajas de sus sucursales, con arqueos casi
  exactos (±5 Bs);
- ventas presenciales en esos turnos, con estacionalidad semanal, una tendencia
  suave y preferencias por producto, para que la demanda semanal tenga señal;
- 24 clientes de demostración con perfiles RFM distintos (fieles, ocasionales,
  dormidos), para que el K-means encuentre segmentos;
- devoluciones en turnos posteriores a la venta;
- y, a propósito, unos pocos casos raros que el Isolation Forest tiene que
  marcar: un turno con un faltante grande, un turno con muchas devoluciones,
  un turno abierto de madrugada que dura 15 horas, una devolución de mucho
  valor y otra hecha a minutos de la venta.

TODO QUEDA MARCADO PARA PODER BORRARLO
--------------------------------------
- Ventas: el código empieza con `DEMO-`.
- Devoluciones: el motivo empieza con `[DEMO]`.
- Turnos: los que solo tienen ventas `DEMO-`.
- Clientes: el correo es `demo.analiticaNN.e<empresa>@analitica.demo.violetboutique.bo`.
- Cajas: se crea «Caja demo analítica» solo si la sucursal no tiene ninguna.

`--borrar` quita exactamente eso y nada más. Los entrenamientos que se hayan
hecho después (`modelo_analitica`) NO se borran: son resultados, y el
administrador los puede volver a generar.

POR QUÉ NO MUEVE EL INVENTARIO
------------------------------
Las ventas y devoluciones son HISTÓRICAS: no se descuentan ni se reponen
existencias. A propósito, por dos motivos:

1. El stock de hoy no cambia: lo que se muestra en la defensa (catálogo,
   existencias, traspasos) queda igual que antes de correrlo.
2. Mover stock dispara avisos reales: «stock bajo» al encargado y, con el
   aporte del aviso de talla, push y correo a clientes de verdad. Una carga
   de demostración no debe mandarle nada a nadie.

El invariante del inventario (existencia == suma de movimientos) se mantiene
porque no se escribe ningún movimiento. Se lee como «stock que ya se repuso».

CONTEXTO DE EMPRESA
-------------------
La sesión se abre con `info={CLAVE_EMPRESA: id}`, igual que los sembrados y la
aplicación: cada transacción fija `app.empresa_id` y el RLS más el DEFAULT de
`empresa_id` hacen el resto. Si `APP_DB_ROLE` está definida, la conexión hace
`SET ROLE` como la aplicación.

USO (desde backend/)
--------------------
    python -m scripts.datos_demo_analitica --empresa violet-boutique --dry-run
    python -m scripts.datos_demo_analitica --empresa violet-boutique
    python -m scripts.datos_demo_analitica --empresa violet-boutique --borrar
"""
from __future__ import annotations

import argparse
import math
import random
import secrets
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import delete, func, null, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core import tiempo
from app.core.security import hash_password
from app.modules.catalogo.models import Producto, VarianteProducto
from app.modules.organizacion.models import Sucursal
from app.modules.plataforma.models import ClienteEmpresa, Empresa
from app.modules.seguridad.models import Cliente, Rol, Usuario
from app.modules.ventas.models import (
    Caja,
    DetalleDevolucion,
    DetalleVenta,
    Devolucion,
    TurnoCaja,
    Venta,
)

PREFIJO_VENTA = "DEMO-"
PREFIJO_MOTIVO = "[DEMO]"
DOMINIO_CLIENTES = "analitica.demo.violetboutique.bo"
NOMBRE_CAJA = "Caja demo analítica"

#: Turnos normales por semana, repartidos entre las cajas.
TURNOS_POR_SEMANA = 4
#: Devoluciones normales en todo el período.
DEVOLUCIONES_NORMALES = 24
CLIENTES_DEMO = 24
MAX_PRODUCTOS = 25
APERTURA = Decimal("300.00")
CENTAVO = Decimal("0.01")

NOMBRES = ["Lucía", "Valeria", "Camila", "Daniela", "Sofía", "Mariana", "Paola",
           "Andrea", "Gabriela", "Natalia", "Carla", "Fernanda", "Diego", "Jorge",
           "Marcelo", "Rodrigo", "Andrés", "Luis", "Carlos", "Mateo", "Javier",
           "Ricardo", "Sergio", "Pablo"]
APELLIDOS = ["Rojas", "Vargas", "Gutiérrez", "Flores", "Mendoza", "Suárez", "Justiniano",
             "Pérez", "Rivero", "Añez", "Saucedo", "Molina"]

MOTIVOS = ["No le quedó bien la talla", "Cambió de opinión", "Tenía una falla de costura",
           "El color no era el esperado", "Regalo repetido"]


class ErrorDatosDemo(Exception):
    """Algo impide cargar los datos (falta una sucursal, ya están cargados...)."""


def _dinero(x: float | Decimal) -> Decimal:
    return Decimal(str(x)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


# =====================================================================
#  Lo que se arma en memoria antes de escribir
# =====================================================================

@dataclass
class LineaPlan:
    variante_id: int
    cantidad: int
    precio: Decimal
    descuento_unitario: Decimal


@dataclass
class VentaPlan:
    codigo: str
    momento: datetime
    sucursal_id: int
    cliente: int | None  # índice en la lista de clientes demo
    metodo: str
    lineas: list[LineaPlan]

    @property
    def subtotal(self) -> Decimal:
        return sum((l.precio * l.cantidad for l in self.lineas), Decimal("0"))

    @property
    def descuento(self) -> Decimal:
        return sum((l.descuento_unitario * l.cantidad for l in self.lineas), Decimal("0"))

    @property
    def total(self) -> Decimal:
        return self.subtotal - self.descuento


@dataclass
class DevolucionPlan:
    venta: VentaPlan
    momento: datetime
    lineas: list[tuple[int, int]]  # (variante_id, cantidad)
    motivo: str

    @property
    def monto(self) -> Decimal:
        por_variante = {l.variante_id: l for l in self.venta.lineas}
        return sum(
            ((por_variante[v].precio - por_variante[v].descuento_unitario) * c
             for v, c in self.lineas),
            Decimal("0"),
        )


@dataclass
class TurnoPlan:
    caja_id: int
    sucursal_id: int
    usuario_id: int
    abierto: datetime
    cerrado: datetime
    ventas: list[VentaPlan] = field(default_factory=list)
    devoluciones: list[DevolucionPlan] = field(default_factory=list)
    #: Lo que se aparta del esperado al contar (el arqueo).
    descuadre: Decimal = Decimal("0")
    raro: str | None = None


@dataclass
class Resumen:
    turnos: int = 0
    turnos_raros: dict[str, int] = field(default_factory=dict)
    ventas: int = 0
    lineas: int = 0
    devoluciones: int = 0
    devoluciones_raras: dict[str, int] = field(default_factory=dict)
    clientes: int = 0
    cajas_creadas: int = 0
    desde: date | None = None
    hasta: date | None = None

    def imprimir(self) -> None:
        print(f"  Período: {self.desde:%d/%m/%Y} a {self.hasta:%d/%m/%Y}")
        print(f"  Turnos de caja cerrados: {self.turnos}"
              f" (raros: {', '.join(f'{k} #{v}' for k, v in self.turnos_raros.items())})")
        print(f"  Ventas presenciales: {self.ventas} ({self.lineas} líneas)")
        print(f"  Devoluciones: {self.devoluciones}"
              f" (raras: {', '.join(f'{k} #{v}' for k, v in self.devoluciones_raras.items())})")
        print(f"  Clientes de demostración: {self.clientes}")
        if self.cajas_creadas:
            print(f"  Cajas creadas: {self.cajas_creadas}")


# =====================================================================
#  Lectura de lo que ya tiene la empresa
# =====================================================================

def empresa_por_slug(db: Session, slug: str) -> Empresa:
    empresa = db.scalar(select(Empresa).where(Empresa.slug == slug))
    if empresa is None:
        raise ErrorDatosDemo(f"No existe una empresa con el slug «{slug}».")
    return empresa


def hay_datos_demo(db: Session) -> bool:
    return bool(db.scalar(
        select(func.count(Venta.id)).where(Venta.codigo.like(f"{PREFIJO_VENTA}%"))
    ))


def _personal(db: Session, empresa_id: int) -> list[int]:
    """Quien puede abrir un turno: los cajeros; si no hay, encargados o el admin."""
    filas = db.execute(
        select(Usuario.id, Rol.nombre)
        .join(Rol, Rol.id == Usuario.rol_id)
        .where(Usuario.empresa_id == empresa_id, Usuario.activo.is_(True),
               Rol.nombre.in_(("CAJERO", "ENCARGADO", "ADMINISTRADOR")))
        .order_by(Usuario.id)
    ).all()
    for rol in ("CAJERO", "ENCARGADO", "ADMINISTRADOR"):
        ids = [i for i, r in filas if r == rol]
        if ids:
            return ids
    return []


def _variantes(db: Session) -> list[tuple[int, Decimal]]:
    """Una variante activa por producto activo (hasta MAX_PRODUCTOS), con su precio."""
    filas = db.execute(
        select(VarianteProducto.producto_id, VarianteProducto.id, VarianteProducto.precio)
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .where(Producto.activo.is_(True), VarianteProducto.activa.is_(True),
               VarianteProducto.precio > 0)
        .order_by(VarianteProducto.producto_id, VarianteProducto.id)
    ).all()
    una_por_producto: dict[int, tuple[int, Decimal]] = {}
    for producto_id, variante_id, precio in filas:
        una_por_producto.setdefault(producto_id, (variante_id, Decimal(precio)))
    return list(una_por_producto.values())[:MAX_PRODUCTOS]


def _cajas(db: Session, resumen: Resumen) -> list[tuple[int, int]]:
    """(caja_id, sucursal_id) de las sucursales activas; crea una si no hay."""
    sucursales = list(db.scalars(
        select(Sucursal.id).where(Sucursal.activa.is_(True)).order_by(Sucursal.id)
    ))
    if not sucursales:
        raise ErrorDatosDemo("La empresa no tiene sucursales activas.")
    cajas: list[tuple[int, int]] = []
    for sucursal_id in sucursales[:3]:
        caja_id = db.scalar(
            select(Caja.id).where(Caja.sucursal_id == sucursal_id, Caja.activa.is_(True))
            .order_by(Caja.id).limit(1)
        )
        if caja_id is None:
            caja = Caja(sucursal_id=sucursal_id, nombre=NOMBRE_CAJA)
            db.add(caja)
            db.flush()
            caja_id = caja.id
            resumen.cajas_creadas += 1
        cajas.append((caja_id, sucursal_id))
    return cajas


# =====================================================================
#  El plan
# =====================================================================

def _momento(dia: date, hora: float) -> datetime:
    """`hora` (decimal, hora boliviana) de `dia`, como instante en UTC."""
    h = int(hora)
    m = int(round((hora - h) * 60))
    local = datetime.combine(dia, time(0, 0), tzinfo=tiempo.BOLIVIA) + timedelta(hours=h, minutes=m)
    return local.astimezone(timezone.utc)


def _planear(azar: random.Random, *, semanas: int, cajas: list[tuple[int, int]],
             personal: list[int], variantes: list[tuple[int, Decimal]]) -> list[TurnoPlan]:
    hoy = tiempo.hoy()
    primero = hoy - timedelta(days=semanas * 7)
    # Cada producto tiene un peso base, una fase de estacionalidad y una
    # tendencia propia: así la demanda semanal por producto no es ruido.
    perfiles = [
        (azar.uniform(0.5, 2.0), azar.uniform(0, 2 * math.pi), azar.uniform(-0.03, 0.05))
        for _ in variantes
    ]
    # Clientes: 0-5 fieles de alto gasto, 6-15 ocasionales, 16-23 dormidos.
    fieles = list(range(0, 6))
    ocasionales = list(range(6, 16))
    dormidos = list(range(16, CLIENTES_DEMO))
    # El sábado se vende más; el domingo, menos.
    por_dia = {0: 0.9, 1: 0.85, 2: 0.9, 3: 1.0, 4: 1.15, 5: 1.4, 6: 0.75}

    turnos: list[TurnoPlan] = []
    n = 0
    for semana in range(semanas):
        inicio = primero + timedelta(days=semana * 7)
        dias = sorted(azar.sample(range(7), TURNOS_POR_SEMANA))
        for k, d in enumerate(dias):
            dia = inicio + timedelta(days=d)
            if dia >= hoy:
                continue
            caja_id, sucursal_id = cajas[(semana + k) % len(cajas)]
            abierto = _momento(dia, 9 + azar.uniform(-0.25, 0.5))
            cerrado = abierto + timedelta(hours=8 + azar.uniform(-0.5, 0.5))
            turno = TurnoPlan(caja_id=caja_id, sucursal_id=sucursal_id,
                              usuario_id=personal[(semana + k) % len(personal)],
                              abierto=abierto, cerrado=cerrado)
            tendencia = 1 + 0.025 * semana
            cuantas = max(3, int(round(azar.gauss(9 * por_dia[dia.weekday()] * tendencia, 1.5))))
            for _ in range(cuantas):
                n += 1
                momento = abierto + (cerrado - abierto) * azar.uniform(0.02, 0.98)
                pesos = [
                    base * (1 + 0.6 * math.sin(2 * math.pi * semana / max(semanas, 1) + fase))
                    * max(0.2, 1 + tend * semana)
                    for base, fase, tend in perfiles
                ]
                lineas = []
                for i in set(azar.choices(range(len(variantes)), weights=pesos,
                                          k=azar.choice([1, 1, 1, 2, 2, 3]))):
                    variante_id, precio = variantes[i]
                    descuento = _dinero(precio * Decimal("0.10")) if azar.random() < 0.1 else Decimal("0")
                    lineas.append(LineaPlan(variante_id, azar.choice([1, 1, 1, 2]),
                                            precio, descuento))
                # Quién compra, según el perfil.
                r = azar.random()
                if r < 0.30:
                    cliente = azar.choice(fieles)
                elif r < 0.50:
                    cliente = azar.choice(ocasionales)
                elif r < 0.58 and semana < semanas / 3:
                    cliente = azar.choice(dormidos)
                else:
                    cliente = None
                if cliente in fieles:  # gastan más: una prenda extra
                    variante_id, precio = variantes[azar.randrange(len(variantes))]
                    if all(l.variante_id != variante_id for l in lineas):
                        lineas.append(LineaPlan(variante_id, 1, precio, Decimal("0")))
                metodo = azar.choices(("EFECTIVO", "TARJETA", "QR"), weights=(5, 3, 2))[0]
                turno.ventas.append(VentaPlan(f"{PREFIJO_VENTA}{n:06d}", momento, sucursal_id,
                                              cliente, metodo, lineas))
            turno.descuadre = _dinero(azar.uniform(-5, 5) * 2) / 2
            turnos.append(turno)

    if len(turnos) < 10:
        raise ErrorDatosDemo("Con tan pocas semanas no alcanzan los turnos: use --semanas 6 o más.")

    # Que cada dormido tenga al menos una compra (vieja): si no, no existe para el RFM.
    viejas = [v for t in turnos[: max(3, len(turnos) // 4)] for v in t.ventas]
    for i, cliente in enumerate(dormidos):
        viejas[(i * 3) % len(viejas)].cliente = cliente

    _devoluciones_normales(azar, turnos)
    _raros(azar, turnos, variantes, personal)
    return turnos


def _devoluciones_normales(azar: random.Random, turnos: list[TurnoPlan]) -> None:
    """Una prenda de una venta vuelve en un turno posterior de la misma sucursal."""
    hechas = 0
    intentos = 0
    candidatos = list(range(len(turnos) - 1))
    while hechas < DEVOLUCIONES_NORMALES and intentos < 500:
        intentos += 1
        i = azar.choice(candidatos)
        origen = turnos[i]
        destino = next(
            (t for t in turnos[i + 1:]
             if t.sucursal_id == origen.sucursal_id and t.raro is None
             and timedelta(hours=12) < t.abierto - origen.cerrado < timedelta(days=10)),
            None,
        )
        if destino is None or not origen.ventas:
            continue
        venta = azar.choice(origen.ventas)
        if getattr(venta, "_devuelta", False):
            continue
        venta._devuelta = True  # type: ignore[attr-defined]
        linea = venta.lineas[0]
        momento = destino.abierto + (destino.cerrado - destino.abierto) * azar.uniform(0.05, 0.95)
        destino.devoluciones.append(DevolucionPlan(
            venta, momento, [(linea.variante_id, 1)], f"{PREFIJO_MOTIVO} {azar.choice(MOTIVOS)}"))
        hechas += 1


def _raros(azar: random.Random, turnos: list[TurnoPlan], variantes: list[tuple[int, Decimal]],
           personal: list[int]) -> None:
    """Los casos que el Isolation Forest tiene que encontrar."""
    # Se eligen en el último tercio, sin devoluciones previas, para que sean claros.
    ultimos = [t for t in turnos[len(turnos) * 2 // 3:] if not t.devoluciones]
    if len(ultimos) < 4:
        ultimos = turnos[-4:]
    faltante, devolvedor, madrugada, valor = ultimos[0], ultimos[1], ultimos[2], ultimos[3]

    # 1. Faltante de Bs 480 en el arqueo.
    faltante.descuadre = Decimal("-480.00")
    faltante.raro = "faltante_arqueo"

    # 2. Siete devoluciones en un mismo turno, de ventas de días anteriores.
    devolvedor.raro = "muchas_devoluciones"
    previas = [v for t in turnos if t.cerrado < devolvedor.abierto
               and t.sucursal_id == devolvedor.sucursal_id for v in t.ventas
               if not getattr(v, "_devuelta", False)]
    for venta in azar.sample(previas, min(7, len(previas))):
        venta._devuelta = True  # type: ignore[attr-defined]
        linea = venta.lineas[0]
        momento = devolvedor.abierto + (devolvedor.cerrado - devolvedor.abierto) * azar.uniform(0.05, 0.95)
        devolvedor.devoluciones.append(DevolucionPlan(
            venta, momento, [(linea.variante_id, linea.cantidad)],
            f"{PREFIJO_MOTIVO} {azar.choice(MOTIVOS)}"))

    # 3. Abierto a las 02:30 y cerrado 15 horas después.
    dia = tiempo.en_bolivia(madrugada.abierto).date()
    nuevo = _momento(dia, 2.5)
    corrimiento = nuevo - madrugada.abierto
    madrugada.abierto = nuevo
    madrugada.cerrado = nuevo + timedelta(hours=15)
    for v in madrugada.ventas:
        v.momento = v.momento + corrimiento
        if v.momento > madrugada.cerrado:
            v.momento = madrugada.cerrado - timedelta(minutes=5)
    madrugada.raro = "madrugada_15h"

    # 4. Devolución de mucho valor: 4 unidades de la prenda más cara, devueltas
    #    a los 8 minutos de venderlas (también es la «devolución rápida»).
    variante_id, precio = max(variantes, key=lambda x: x[1])
    momento = valor.abierto + (valor.cerrado - valor.abierto) * 0.4
    venta = VentaPlan(f"{PREFIJO_VENTA}9{len(turnos):05d}", momento, valor.sucursal_id, None,
                      "EFECTIVO", [LineaPlan(variante_id, 4, precio, Decimal("0"))])
    venta._devuelta = True  # type: ignore[attr-defined]
    valor.ventas.append(venta)
    valor.devoluciones.append(DevolucionPlan(
        venta, momento + timedelta(minutes=8), [(variante_id, 4)],
        f"{PREFIJO_MOTIVO} Devolución completa al rato de comprar"))
    valor.raro = "devolucion_de_valor"


# =====================================================================
#  Escritura
# =====================================================================

def _correo(numero: int | None, empresa_id: int) -> str:
    """El correo de un cliente demo; con `numero=None`, el patrón LIKE de todos.

    Lleva la empresa adentro: así dos empresas pueden tener sus clientes demo y
    `--borrar` en una no toca los de la otra.
    """
    parte = f"{numero:02d}" if numero is not None else "%"
    return f"demo.analitica{parte}.e{empresa_id}@{DOMINIO_CLIENTES}"


def _clientes(db: Session, empresa_id: int) -> list[int]:
    rol = db.scalar(select(Rol.id).where(Rol.nombre == "CLIENTE"))
    if rol is None:
        raise ErrorDatosDemo("No existe el rol CLIENTE.")
    # Nadie entra con estas cuentas: la contraseña es aleatoria y no se guarda.
    hash_ = hash_password(secrets.token_urlsafe(24))
    ahora = tiempo.ahora()
    ids = []
    for i in range(CLIENTES_DEMO):
        nombre = NOMBRES[i % len(NOMBRES)]
        apellido = f"{APELLIDOS[i % len(APELLIDOS)]} {APELLIDOS[(i * 5 + 3) % len(APELLIDOS)]}"
        usuario = Usuario(
            correo=_correo(i + 1, empresa_id),
            hash_contrasena=hash_, nombres=nombre, apellidos=apellido,
            rol_id=rol, activo=True, creado_en=ahora, actualizado_en=ahora,
            empresa_id=null(),  # el cliente no es de una empresa (RN-13)
        )
        db.add(usuario)
        db.flush()
        cliente = Cliente(usuario_id=usuario.id, documento=f"DEMOAN{empresa_id:04d}-{i + 1:03d}",
                          creado_en=ahora, actualizado_en=ahora)
        db.add(cliente)
        db.flush()
        db.add(ClienteEmpresa(cliente_id=cliente.id))
        ids.append(cliente.id)
    db.flush()
    return ids


def _escribir(db: Session, turnos: list[TurnoPlan], clientes: list[int], resumen: Resumen) -> None:
    for t in sorted(turnos, key=lambda x: x.abierto):
        efectivo = sum((v.total for v in t.ventas if v.metodo == "EFECTIVO"), Decimal("0"))
        devuelto = sum((d.monto for d in t.devoluciones), Decimal("0"))
        esperado = APERTURA + efectivo - devuelto
        turno = TurnoCaja(
            caja_id=t.caja_id, usuario_id=t.usuario_id, abierto_en=t.abierto,
            cerrado_en=t.cerrado, monto_apertura=APERTURA, monto_esperado=esperado,
            monto_cierre=esperado + t.descuadre,
        )
        db.add(turno)
        db.flush()
        t.id = turno.id  # type: ignore[attr-defined]
        if t.raro:
            resumen.turnos_raros[t.raro] = turno.id
        resumen.turnos += 1
        for v in t.ventas:
            venta = Venta(
                codigo=v.codigo, canal="PRESENCIAL", estado="PAGADA",
                cliente_id=clientes[v.cliente] if v.cliente is not None else None,
                sucursal_id=v.sucursal_id, turno_caja_id=turno.id, metodo_pago=v.metodo,
                subtotal=v.subtotal, descuento=v.descuento, total=v.total,
                creado_en=v.momento, actualizado_en=v.momento,
            )
            db.add(venta)
            db.flush()
            v.id = venta.id  # type: ignore[attr-defined]
            for l in v.lineas:
                db.add(DetalleVenta(venta_id=venta.id, variante_id=l.variante_id,
                                    cantidad=l.cantidad, precio_unitario=l.precio,
                                    descuento_unitario=l.descuento_unitario,
                                    creado_en=v.momento))
                resumen.lineas += 1
            resumen.ventas += 1
        db.flush()

    # Las devoluciones después: la venta puede estar en un turno anterior.
    for t in turnos:
        for d in t.devoluciones:
            dev = Devolucion(
                venta_id=d.venta.id, turno_caja_id=t.id, origen="CAJA",  # type: ignore[attr-defined]
                tipo="DEVOLUCION", motivo=d.motivo[:200], monto=d.monto,
                diferencia=Decimal("0"), estado="CERRADA", conforme=True,
                creado_en=d.momento,
            )
            db.add(dev)
            db.flush()
            for variante_id, cantidad in d.lineas:
                db.add(DetalleDevolucion(devolucion_id=dev.id, variante_id=variante_id,
                                         cantidad=cantidad, creado_en=d.momento))
            resumen.devoluciones += 1
            if t.raro in ("devolucion_de_valor",):
                resumen.devoluciones_raras["valor_alto_y_rapida"] = dev.id
    db.flush()


def sembrar(db: Session, *, semanas: int = 12, semilla: int = 42) -> Resumen:
    """Carga los datos en la empresa del contexto de `db`. No hace commit."""
    if hay_datos_demo(db):
        raise ErrorDatosDemo(
            "Esta empresa ya tiene datos de demostración (ventas DEMO-). "
            "Bórrelos primero con --borrar.")
    from app.core.tenencia import empresa_actual

    empresa_id = empresa_actual(db)
    if empresa_id is None:
        raise ErrorDatosDemo("La sesión no tiene empresa en el contexto.")
    personal = _personal(db, empresa_id)
    if not personal:
        raise ErrorDatosDemo("La empresa no tiene cajeros, encargados ni administrador activos.")
    variantes = _variantes(db)
    if len(variantes) < 3:
        raise ErrorDatosDemo("Hacen falta al menos 3 productos activos con variantes.")

    resumen = Resumen()
    cajas = _cajas(db, resumen)
    azar = random.Random(semilla)
    turnos = _planear(azar, semanas=semanas, cajas=cajas, personal=personal, variantes=variantes)
    clientes = _clientes(db, empresa_id)
    resumen.clientes = len(clientes)
    _escribir(db, turnos, clientes, resumen)
    resumen.desde = min(tiempo.en_bolivia(t.abierto).date() for t in turnos)
    resumen.hasta = max(tiempo.en_bolivia(t.cerrado).date() for t in turnos)
    return resumen


def borrar(db: Session) -> dict[str, int]:
    """Quita lo que cargó `sembrar` en la empresa del contexto. No hace commit."""
    ventas_demo = select(Venta.id).where(Venta.codigo.like(f"{PREFIJO_VENTA}%"))
    turnos_demo = set(db.scalars(
        select(Venta.turno_caja_id).where(Venta.codigo.like(f"{PREFIJO_VENTA}%"),
                                          Venta.turno_caja_id.is_not(None)).distinct()
    ))
    # Un turno solo se borra si no tiene NADA ajeno: ni ventas ni devoluciones reales.
    ajenos = set(db.scalars(
        select(Venta.turno_caja_id).where(Venta.turno_caja_id.in_(turnos_demo),
                                          Venta.codigo.not_like(f"{PREFIJO_VENTA}%"))
    )) | set(db.scalars(
        select(Devolucion.turno_caja_id).where(Devolucion.turno_caja_id.in_(turnos_demo),
                                               Devolucion.motivo.not_like(f"{PREFIJO_MOTIVO}%"))
    ))
    turnos_a_borrar = turnos_demo - ajenos
    devs = select(Devolucion.id).where(
        (Devolucion.motivo.like(f"{PREFIJO_MOTIVO}%")) | (Devolucion.venta_id.in_(ventas_demo)))
    cuenta: dict[str, int] = {}
    cuenta["detalle_devolucion"] = db.execute(
        delete(DetalleDevolucion).where(DetalleDevolucion.devolucion_id.in_(devs))).rowcount
    cuenta["devolucion"] = db.execute(
        delete(Devolucion).where(Devolucion.id.in_(devs))).rowcount
    cuenta["detalle_venta"] = db.execute(
        delete(DetalleVenta).where(DetalleVenta.venta_id.in_(ventas_demo))).rowcount
    cuenta["venta"] = db.execute(
        delete(Venta).where(Venta.codigo.like(f"{PREFIJO_VENTA}%"))).rowcount
    cuenta["turno_caja"] = db.execute(
        delete(TurnoCaja).where(TurnoCaja.id.in_(turnos_a_borrar))).rowcount if turnos_a_borrar else 0
    # La caja creada por el script, si quedó sin turnos.
    con_turnos = select(TurnoCaja.caja_id)
    cuenta["caja"] = db.execute(
        delete(Caja).where(Caja.nombre == NOMBRE_CAJA, Caja.id.not_in(con_turnos))).rowcount
    from app.core.tenencia import empresa_actual

    patron = _correo(None, empresa_actual(db))
    ids_clientes = list(db.scalars(
        select(Cliente.id).join(Usuario, Usuario.id == Cliente.usuario_id)
        .where(Usuario.correo.like(patron))))
    usuarios = list(db.scalars(select(Usuario.id).where(Usuario.correo.like(patron))))
    cuenta["cliente_empresa"] = db.execute(
        delete(ClienteEmpresa).where(ClienteEmpresa.cliente_id.in_(ids_clientes))).rowcount
    cuenta["cliente"] = db.execute(
        delete(Cliente).where(Cliente.id.in_(ids_clientes))).rowcount
    cuenta["usuario"] = db.execute(delete(Usuario).where(Usuario.id.in_(usuarios))).rowcount
    db.flush()
    return cuenta


# =====================================================================
#  Línea de comandos
# =====================================================================

def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Carga (o borra) datos de demostración para la analítica con ML.")
    p.add_argument("--empresa", required=True, help="slug de la empresa (p. ej. violet-boutique)")
    p.add_argument("--semanas", type=int, default=12, help="semanas hacia atrás (por omisión 12)")
    p.add_argument("--seed", type=int, default=42, help="semilla del azar (por omisión 42)")
    p.add_argument("--dry-run", action="store_true", help="muestra lo que haría y deshace todo")
    p.add_argument("--borrar", action="store_true", help="quita solo lo que cargó este script")
    p.add_argument("--si", action="store_true", help="no pedir confirmación")
    return p.parse_args(argv)


def _cargar_todos_los_modelos() -> None:
    """Importa el `models.py` de cada módulo, como hace alembic/env.py.

    Sin esto el mapeador no encuentra tablas como `reserva` a la que apunta
    una FK de `venta`, y el primer flush falla.
    """
    import importlib
    import pkgutil

    import app.modules as modulos

    for m in pkgutil.iter_modules(modulos.__path__):
        try:
            importlib.import_module(f"app.modules.{m.name}.models")
        except ModuleNotFoundError as e:
            if e.name != f"app.modules.{m.name}.models":
                raise


def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    _cargar_todos_los_modelos()
    from app.core.config import settings
    from app.core.tenencia import CLAVE_EMPRESA, CLAVE_PLATAFORMA
    from app.db.session import SessionLocal

    url = make_url(settings.DATABASE_URL)
    print("=" * 66)
    print(" DATOS DE DEMOSTRACIÓN PARA LA ANALÍTICA")
    print(f" Base:    {url.host}:{url.port or 5432} / {url.database}")
    print(f" Empresa: {args.empresa}")
    print(f" Acción:  {'BORRAR lo cargado' if args.borrar else 'CARGAR'}"
          f"{' (simulacro: no se guarda nada)' if args.dry_run else ''}")
    print("=" * 66)
    if not args.si and not args.dry_run:
        escrito = input(f"Escriba el slug de la empresa ({args.empresa}) para continuar: ").strip()
        if escrito != args.empresa:
            print("No coincide. No se hizo nada.")
            return 1

    with SessionLocal(info={CLAVE_PLATAFORMA: True}) as plataforma:
        try:
            empresa = empresa_por_slug(plataforma, args.empresa)
        except ErrorDatosDemo as e:
            print(f"ERROR: {e}")
            return 1
        empresa_id = empresa.id

    with SessionLocal(info={CLAVE_EMPRESA: empresa_id}) as db:
        try:
            if args.borrar:
                cuenta = borrar(db)
                for tabla, n in cuenta.items():
                    print(f"  - {tabla}: {n}")
            else:
                resumen = sembrar(db, semanas=args.semanas, semilla=args.seed)
                resumen.imprimir()
        except ErrorDatosDemo as e:
            db.rollback()
            print(f"ERROR: {e}")
            return 1
        if args.dry_run:
            db.rollback()
            print("Simulacro: se deshizo todo.")
        else:
            db.commit()
            print("Listo." if args.borrar else
                  "Listo. Ahora, como administrador: Analítica → Entrenar y Anomalías → Buscar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
