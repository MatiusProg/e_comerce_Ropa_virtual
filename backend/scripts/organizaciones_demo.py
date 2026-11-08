"""Cuatro organizaciones (empresas) de demostración para mostrar el multitenant.

PARA QUÉ
--------
En la defensa hay una sola empresa con datos: Violet Boutique. Para que se vea
que la plataforma es multitenant —cada empresa con su plan, sus sucursales, su
catálogo, su personal y sus clientes, sin ver nada de las otras— este script
da de alta cuatro boutiques más, con datos suficientes para que los reportes
no salgan vacíos:

=========  ===================  =============  ==========  =====================
slug       empresa              plan           sucursales  para mostrar
=========  ===================  =============  ==========  =====================
alpaca     Alpaca Real          Empresarial    3           todo, con analítica
chiquitana Chiquitana Moda      Empresarial    3           todo, con analítica
illimani   Illimani Urbano      Profesional    3           IA sí, analítica no
awayu      Awayu Boutique       Básico         2           sin IA ni analítica
=========  ===================  =============  ==========  =====================

(Las sucursales dependen de las ciudades que existan y del `max_sucursales`
del plan: el script nunca pasa los límites del plan.)

Cada una lleva: suscripción vigente con su pago simulado (como el CU-01),
sucursales en ciudades distintas con sus cajas, administrador, un encargado
por sucursal, cajeros, un proveedor con cuenta, 20 clientes, un catálogo propio
de 16 a 22 productos con variantes de talla y color, existencias por sucursal
(con su historial de movimientos), turnos de caja cerrados con ventas, alguna
devolución y reservas en todos los estados.

CREDENCIALES
------------
- Empresa (slug): el de la tabla.
- Correo: rol + número + @<slug>.test
    admin@alpaca.test, encargado1@alpaca.test, cajero1@alpaca.test,
    proveedor1@alpaca.test, cliente1@alpaca.test ... cliente20@alpaca.test
- Contraseña de todas: la de `DEMO_ORGANIZACIONES_CLAVE` (por omisión
  `si2ex22026`), con el mismo hash que usa el sistema.

El cliente tiene UNA cuenta en la plataforma (RN-13): `usuario.empresa_id` es
NULL y la empresa donde compra la dice `cliente_empresa`. Entra con el slug de
su tienda; también podría entrar a otra y el login lo asociaría a esa.

CÓMO SE CREA CADA EMPRESA
-------------------------
En el mismo orden que el alta del CU-01 (`plataforma/service.crear_empresa`):
empresa en modo plataforma, y apenas se conoce su id, `fijar_empresa` para
que el DEFAULT de `empresa_id` y el WITH CHECK del RLS hagan su trabajo. No se
llama a `crear_empresa` porque hace commit y manda el correo de acceso (a una
dirección .test); acá todo va en UNA transacción y el simulacro la deshace.

El inventario cumple el invariante del paquete (existencia == suma de
movimientos): cada existencia nace con un INGRESO y después se escriben la
VENTA, la DEVOLUCION, la RESERVA y la LIBERACION de lo que se cargó. No se
dispara ningún aviso: se escribe en la base, no por los servicios.

TODO SE PUEDE BORRAR
--------------------
`--borrar` quita las empresas enteras: todas las filas con su `empresa_id` (lo
que cargó el script y lo que se haya hecho después en la defensa: ventas,
logins en la bitácora, respaldos...), su personal, la empresa, y las cuentas
`clienteN@<slug>.test` de la plataforma. Solo borra una empresa si su slug es
uno de los cuatro Y tiene la cuenta `admin@<slug>.test`: la marca de que la
creó este script.

USO (desde backend/, con APP_DB_ROLE=violet_app)
-------------------------------------------------
    python -m scripts.organizaciones_demo --dry-run
    python -m scripts.organizaciones_demo
    python -m scripts.organizaciones_demo --borrar
    python -m scripts.organizaciones_demo --empresa awayu      # solo una

Ver también docs/entregas/Presentacion-3/organizaciones-demo.md.
"""
from __future__ import annotations

import argparse
import os
import random
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import delete, func, null, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core import tiempo
from app.core.security import hash_password

CLAVE_POR_OMISION = "si2ex22026"
DOMINIO = "test"
APERTURA = Decimal("300.00")
CENTAVO = Decimal("0.01")
CLIENTES_POR_EMPRESA = 20


class ErrorOrganizaciones(Exception):
    """Algo impide cargar o borrar (ya están cargadas, falta un plan...)."""


def _dinero(x) -> Decimal:
    return Decimal(str(x)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


# =====================================================================
#  Las cuatro organizaciones
# =====================================================================

TALLAS = {
    "SUPERIOR": ["S", "M", "L", "XL"],
    "INFERIOR": ["36", "38", "40", "42"],
    "UNICA": ["U"],
}

#: Barrio y dirección de una sucursal según la ciudad. Si la ciudad no está acá
#: (otra que exista en producción), se usa «Centro».
BARRIOS = {
    "La Paz": [("Sopocachi", "Av. 20 de Octubre #2150, Sopocachi"),
               ("San Miguel", "Calle 21 de Calacoto #8320, San Miguel"),
               ("Prado", "Av. 16 de Julio (El Prado) #1490")],
    "Santa Cruz de la Sierra": [("Equipetrol", "Av. San Martín #455, Equipetrol"),
                                ("Ventura", "Ventura Mall, 4to anillo Av. San Martín"),
                                ("Centro", "Calle 24 de Septiembre #120, casco viejo")],
    "Cochabamba": [("Av. América", "Av. América #E-0412 casi Pando"),
                   ("Recoleta", "Av. Pando #1180, La Recoleta"),
                   ("Centro", "Calle España #245")],
}


@dataclass
class ProductoDemo:
    subcategoria: str
    nombre: str
    tipo_talla: str
    precio: int
    colores: list[str]


@dataclass
class Organizacion:
    slug: str
    nombre: str
    razon_social: str
    nit: str
    plan: str
    #: Letra del código de venta: VP-AAAAMMDD-<letra>NNN. No es hexadecimal,
    #: así que nunca choca con los códigos del punto de venta (VP-...-A3F2).
    letra: str
    prefijo: str
    ciudades: list[str]
    sucursales: int
    cajeros_por_sucursal: int
    semanas: int
    turnos_por_semana: int
    devoluciones: int
    categorias: dict[str, list[str]]
    colores: dict[str, str]
    productos: list[ProductoDemo]
    temporada: str
    coleccion: str
    proveedor: tuple[str, str]
    administrador: tuple[str, str]


ORGANIZACIONES: list[Organizacion] = [
    Organizacion(
        slug="alpaca", nombre="Alpaca Real", razon_social="Alpaca Real S.R.L.",
        nit="1028475023", plan="EMPRESARIAL", letra="K", prefijo="ALP",
        ciudades=["La Paz", "Cochabamba", "Santa Cruz de la Sierra"],
        sucursales=3, cajeros_por_sucursal=2, semanas=6, turnos_por_semana=3, devoluciones=18,
        categorias={"Tejidos": ["Chompas", "Ponchos y capas", "Cárdigans"],
                    "Accesorios": ["Chalinas", "Gorros y guantes"]},
        colores={"Natural": "#EDE3D1", "Gris andino": "#8A8D8F", "Café vicuña": "#7B5B3A",
                 "Negro": "#1A1A1A", "Terracota": "#B5523B", "Azul noche": "#22304A"},
        productos=[
            ProductoDemo("Chompas", "Chompa de baby alpaca cuello alto", "SUPERIOR", 590, ["Natural", "Gris andino", "Negro"]),
            ProductoDemo("Chompas", "Chompa trenzada clásica", "SUPERIOR", 520, ["Natural", "Café vicuña"]),
            ProductoDemo("Chompas", "Chompa cuello V liviana", "SUPERIOR", 430, ["Gris andino", "Azul noche", "Terracota"]),
            ProductoDemo("Chompas", "Chompa con diseño andino", "SUPERIOR", 560, ["Natural", "Terracota"]),
            ProductoDemo("Chompas", "Sweater oversize de alpaca", "SUPERIOR", 610, ["Gris andino", "Negro"]),
            ProductoDemo("Ponchos y capas", "Poncho de alpaca con flecos", "UNICA", 780, ["Natural", "Café vicuña", "Gris andino"]),
            ProductoDemo("Ponchos y capas", "Capa tejida a mano", "UNICA", 690, ["Terracota", "Negro"]),
            ProductoDemo("Ponchos y capas", "Ruana de alpaca", "UNICA", 640, ["Gris andino", "Azul noche"]),
            ProductoDemo("Cárdigans", "Cárdigan largo con bolsillos", "SUPERIOR", 650, ["Natural", "Café vicuña"]),
            ProductoDemo("Cárdigans", "Cárdigan corto de botones", "SUPERIOR", 480, ["Negro", "Terracota", "Gris andino"]),
            ProductoDemo("Cárdigans", "Kimono tejido", "SUPERIOR", 540, ["Natural", "Azul noche"]),
            ProductoDemo("Chalinas", "Chalina de baby alpaca", "UNICA", 220, ["Natural", "Gris andino", "Terracota", "Azul noche"]),
            ProductoDemo("Chalinas", "Bufanda tejido punto inglés", "UNICA", 180, ["Negro", "Café vicuña"]),
            ProductoDemo("Chalinas", "Pashmina de alpaca y seda", "UNICA", 260, ["Natural", "Terracota"]),
            ProductoDemo("Gorros y guantes", "Chullo andino", "UNICA", 120, ["Natural", "Terracota", "Azul noche"]),
            ProductoDemo("Gorros y guantes", "Gorro de lana con pompón", "UNICA", 110, ["Gris andino", "Negro"]),
            ProductoDemo("Gorros y guantes", "Guantes de alpaca", "UNICA", 95, ["Negro", "Café vicuña"]),
            ProductoDemo("Gorros y guantes", "Mitones tejidos", "UNICA", 90, ["Natural", "Gris andino"]),
            ProductoDemo("Chompas", "Polera de alpaca manga larga", "SUPERIOR", 380, ["Negro", "Natural"]),
            ProductoDemo("Cárdigans", "Chaleco tejido sin mangas", "SUPERIOR", 350, ["Café vicuña", "Gris andino"]),
        ],
        temporada="Invierno andino 2026", coleccion="Altiplano",
        proveedor=("Tejidos Apolobamba S.R.L.", "2047711019"),
        administrador=("Mariela", "Quispe Condori"),
    ),
    Organizacion(
        slug="chiquitana", nombre="Chiquitana Moda", razon_social="Chiquitana Moda S.A.",
        nit="3061874016", plan="EMPRESARIAL", letra="M", prefijo="CHQ",
        ciudades=["Santa Cruz de la Sierra", "Cochabamba", "La Paz"],
        sucursales=3, cajeros_por_sucursal=2, semanas=6, turnos_por_semana=3, devoluciones=18,
        categorias={"Mujer": ["Vestidos", "Blusas", "Faldas y shorts"],
                    "Hombre": ["Camisas", "Bermudas"],
                    "Playa": ["Trajes de baño"]},
        colores={"Blanco": "#FAFAFA", "Coral": "#F2765C", "Turquesa": "#2BB3B1",
                 "Amarillo tajibo": "#F2C230", "Verde selva": "#2F6B3A", "Arena": "#D9C4A0"},
        productos=[
            ProductoDemo("Vestidos", "Vestido de lino tirantes", "SUPERIOR", 340, ["Blanco", "Coral", "Arena"]),
            ProductoDemo("Vestidos", "Vestido largo estampado tajibo", "SUPERIOR", 420, ["Amarillo tajibo", "Turquesa"]),
            ProductoDemo("Vestidos", "Vestido camisero de algodón", "SUPERIOR", 360, ["Blanco", "Verde selva"]),
            ProductoDemo("Vestidos", "Vestido corto con vuelos", "SUPERIOR", 310, ["Coral", "Turquesa", "Blanco"]),
            ProductoDemo("Blusas", "Blusa bordada tipoy", "SUPERIOR", 260, ["Blanco", "Arena"]),
            ProductoDemo("Blusas", "Blusa off-shoulder", "SUPERIOR", 220, ["Coral", "Blanco", "Amarillo tajibo"]),
            ProductoDemo("Blusas", "Top de lino anudado", "SUPERIOR", 180, ["Arena", "Verde selva"]),
            ProductoDemo("Blusas", "Musculosa de algodón", "SUPERIOR", 120, ["Blanco", "Turquesa", "Coral"]),
            ProductoDemo("Faldas y shorts", "Falda midi plisada", "INFERIOR", 280, ["Arena", "Verde selva"]),
            ProductoDemo("Faldas y shorts", "Short de lino tiro alto", "INFERIOR", 190, ["Blanco", "Arena", "Coral"]),
            ProductoDemo("Faldas y shorts", "Falda cruzada estampada", "INFERIOR", 240, ["Amarillo tajibo", "Turquesa"]),
            ProductoDemo("Camisas", "Camisa guayabera de lino", "SUPERIOR", 330, ["Blanco", "Arena"]),
            ProductoDemo("Camisas", "Camisa hawaiana", "SUPERIOR", 260, ["Turquesa", "Verde selva", "Coral"]),
            ProductoDemo("Camisas", "Camisa de manga corta oxford", "SUPERIOR", 240, ["Blanco", "Turquesa"]),
            ProductoDemo("Bermudas", "Bermuda chino", "INFERIOR", 230, ["Arena", "Verde selva"]),
            ProductoDemo("Bermudas", "Bermuda de lino con cordón", "INFERIOR", 250, ["Blanco", "Arena"]),
            ProductoDemo("Trajes de baño", "Bikini estampado", "SUPERIOR", 210, ["Coral", "Turquesa", "Amarillo tajibo"]),
            ProductoDemo("Trajes de baño", "Enterizo con escote en V", "SUPERIOR", 270, ["Verde selva", "Coral"]),
            ProductoDemo("Trajes de baño", "Short de baño hombre", "INFERIOR", 160, ["Turquesa", "Verde selva"]),
            ProductoDemo("Trajes de baño", "Pareo de gasa", "UNICA", 110, ["Coral", "Turquesa", "Blanco"]),
            ProductoDemo("Vestidos", "Solero de gasa", "SUPERIOR", 290, ["Amarillo tajibo", "Blanco"]),
            ProductoDemo("Blusas", "Kimono playero", "UNICA", 200, ["Arena", "Coral"]),
        ],
        temporada="Verano tropical 2026-2027", coleccion="Chiquitanía",
        proveedor=("Confecciones del Oriente Ltda.", "1015873026"),
        administrador=("Daniela", "Justiniano Áñez"),
    ),
    Organizacion(
        slug="illimani", nombre="Illimani Urbano", razon_social="Illimani Urbano S.R.L.",
        nit="4123908011", plan="PROFESIONAL", letra="R", prefijo="ILL",
        ciudades=["La Paz", "Santa Cruz de la Sierra", "Cochabamba"],
        sucursales=3, cajeros_por_sucursal=1, semanas=3, turnos_por_semana=2, devoluciones=6,
        categorias={"Urbano": ["Poleras", "Hoodies", "Jeans", "Joggers"],
                    "Outdoor": ["Casacas"]},
        colores={"Negro": "#1A1A1A", "Blanco": "#FAFAFA", "Gris jaspe": "#A7A9AC",
                 "Azul índigo": "#2E3F6E", "Verde oliva": "#5B6236", "Mostaza": "#C9A227"},
        productos=[
            ProductoDemo("Poleras", "Polera básica de algodón", "SUPERIOR", 120, ["Negro", "Blanco", "Gris jaspe"]),
            ProductoDemo("Poleras", "Polera oversize estampada", "SUPERIOR", 160, ["Negro", "Blanco"]),
            ProductoDemo("Poleras", "Polera manga larga", "SUPERIOR", 150, ["Gris jaspe", "Verde oliva", "Mostaza"]),
            ProductoDemo("Poleras", "Polo piqué", "SUPERIOR", 170, ["Azul índigo", "Blanco"]),
            ProductoDemo("Hoodies", "Hoodie con capucha", "SUPERIOR", 280, ["Negro", "Gris jaspe", "Mostaza"]),
            ProductoDemo("Hoodies", "Polerón cuello redondo", "SUPERIOR", 240, ["Verde oliva", "Azul índigo"]),
            ProductoDemo("Hoodies", "Hoodie con cierre", "SUPERIOR", 300, ["Negro", "Gris jaspe"]),
            ProductoDemo("Jeans", "Jean slim fit", "INFERIOR", 320, ["Azul índigo", "Negro"]),
            ProductoDemo("Jeans", "Jean mom tiro alto", "INFERIOR", 330, ["Azul índigo", "Blanco"]),
            ProductoDemo("Jeans", "Jean recto clásico", "INFERIOR", 300, ["Azul índigo", "Gris jaspe"]),
            ProductoDemo("Joggers", "Jogger de algodón", "INFERIOR", 210, ["Negro", "Gris jaspe", "Verde oliva"]),
            ProductoDemo("Joggers", "Cargo con bolsillos", "INFERIOR", 260, ["Verde oliva", "Negro"]),
            ProductoDemo("Casacas", "Casaca rompeviento", "SUPERIOR", 380, ["Negro", "Azul índigo", "Mostaza"]),
            ProductoDemo("Casacas", "Parka acolchada", "SUPERIOR", 520, ["Negro", "Verde oliva"]),
            ProductoDemo("Casacas", "Chamarra de jean", "SUPERIOR", 420, ["Azul índigo"]),
            ProductoDemo("Casacas", "Chaleco puffer", "SUPERIOR", 340, ["Negro", "Mostaza"]),
            ProductoDemo("Casacas", "Polar de montaña", "SUPERIOR", 290, ["Gris jaspe", "Azul índigo"]),
            ProductoDemo("Poleras", "Camiseta deportiva dry-fit", "SUPERIOR", 140, ["Negro", "Blanco", "Mostaza"]),
        ],
        temporada="Urbano 2026", coleccion="Cumbre",
        proveedor=("Textiles El Alto S.R.L.", "6120034018"),
        administrador=("Rodrigo", "Mamani Choque"),
    ),
    Organizacion(
        slug="awayu", nombre="Awayu Boutique", razon_social="Awayu Boutique (unipersonal)",
        nit="7734512010", plan="BASICO", letra="T", prefijo="AWY",
        ciudades=["Cochabamba", "La Paz"],
        sucursales=2, cajeros_por_sucursal=1, semanas=3, turnos_por_semana=2, devoluciones=5,
        categorias={"Mujer": ["Blusas bordadas", "Faldas", "Vestidos"],
                    "Accesorios": ["Bolsos de aguayo"]},
        colores={"Multicolor": "#C2185B", "Rojo carmín": "#B0122E", "Negro": "#1A1A1A",
                 "Blanco": "#FAFAFA", "Verde andino": "#2E7D32"},
        productos=[
            ProductoDemo("Blusas bordadas", "Blusa bordada a mano", "SUPERIOR", 230, ["Blanco", "Negro"]),
            ProductoDemo("Blusas bordadas", "Blusa con pechera de aguayo", "SUPERIOR", 260, ["Blanco", "Rojo carmín"]),
            ProductoDemo("Blusas bordadas", "Camisa con detalle andino", "SUPERIOR", 240, ["Blanco", "Verde andino"]),
            ProductoDemo("Blusas bordadas", "Top de aguayo", "SUPERIOR", 180, ["Multicolor"]),
            ProductoDemo("Faldas", "Falda de aguayo midi", "INFERIOR", 280, ["Multicolor", "Rojo carmín"]),
            ProductoDemo("Faldas", "Falda plisada con franja tejida", "INFERIOR", 250, ["Negro", "Verde andino"]),
            ProductoDemo("Faldas", "Minifalda de aguayo", "INFERIOR", 190, ["Multicolor"]),
            ProductoDemo("Vestidos", "Vestido con faja tejida", "SUPERIOR", 360, ["Negro", "Blanco"]),
            ProductoDemo("Vestidos", "Vestido de aguayo", "SUPERIOR", 390, ["Multicolor", "Rojo carmín"]),
            ProductoDemo("Vestidos", "Vestido camisero bordado", "SUPERIOR", 340, ["Blanco", "Verde andino"]),
            ProductoDemo("Bolsos de aguayo", "Bolso tote de aguayo", "UNICA", 150, ["Multicolor", "Rojo carmín"]),
            ProductoDemo("Bolsos de aguayo", "Mochila de aguayo", "UNICA", 210, ["Multicolor", "Negro"]),
            ProductoDemo("Bolsos de aguayo", "Riñonera tejida", "UNICA", 95, ["Multicolor", "Verde andino"]),
            ProductoDemo("Bolsos de aguayo", "Cartera de mano", "UNICA", 130, ["Rojo carmín", "Negro"]),
            ProductoDemo("Bolsos de aguayo", "Monedero de aguayo", "UNICA", 45, ["Multicolor"]),
            ProductoDemo("Blusas bordadas", "Chaqueta de aguayo", "SUPERIOR", 420, ["Multicolor", "Negro"]),
        ],
        temporada="Raíces 2026", coleccion="Aguayo vivo",
        proveedor=("Artesanías Tiquipaya", "5201876015"),
        administrador=("Valeria", "Rojas Villarroel"),
    ),
]

NOMBRES_F = ["Lucía", "Valeria", "Camila", "Daniela", "Sofía", "Mariana", "Paola", "Andrea",
             "Gabriela", "Natalia", "Carla", "Fernanda", "Ximena", "Wara", "Inés", "Rocío"]
NOMBRES_M = ["Diego", "Jorge", "Marcelo", "Rodrigo", "Andrés", "Luis", "Carlos", "Mateo",
             "Javier", "Ricardo", "Sergio", "Pablo", "Iván", "Gonzalo", "Álvaro", "Mauricio"]
APELLIDOS = ["Rojas", "Vargas", "Gutiérrez", "Flores", "Mendoza", "Suárez", "Justiniano",
             "Pérez", "Rivero", "Áñez", "Saucedo", "Molina", "Quispe", "Mamani", "Choque",
             "Villarroel", "Arce", "Paz", "Salvatierra", "Céspedes"]
MOTIVOS_DEVOLUCION = ["No le quedó bien la talla", "Cambió de opinión",
                      "Tenía una falla de costura", "El color no era el esperado",
                      "Regalo repetido"]


def correo(rol: str, numero: int | None, slug: str) -> str:
    """rol + número + @<slug>.test; el administrador va sin número."""
    return f"{rol}{'' if numero is None else numero}@{slug}.{DOMINIO}"


def documento_cliente(org: Organizacion, n: int) -> str:
    """Único en toda la plataforma (`cliente.documento`); con letras, no choca con un CI."""
    return f"{org.slug[:6].upper()}-C{n:02d}"


# =====================================================================
#  Lo que se arma en memoria antes de escribir
# =====================================================================

@dataclass
class Linea:
    variante: int  # índice en la lista de variantes de la empresa
    cantidad: int
    precio: Decimal
    descuento: Decimal


@dataclass
class VentaPlan:
    momento: datetime
    cliente: int | None
    metodo: str
    lineas: list[Linea]
    reserva: "ReservaPlan | None" = None
    devuelta: bool = False
    codigo: str = ""
    id: int | None = None

    @property
    def subtotal(self) -> Decimal:
        return sum((l.precio * l.cantidad for l in self.lineas), Decimal("0"))

    @property
    def descuento(self) -> Decimal:
        return sum((l.descuento * l.cantidad for l in self.lineas), Decimal("0"))

    @property
    def total(self) -> Decimal:
        return self.subtotal - self.descuento


@dataclass
class DevolucionPlan:
    venta: VentaPlan
    momento: datetime
    linea: Linea
    motivo: str

    @property
    def monto(self) -> Decimal:
        return self.linea.precio - self.linea.descuento


@dataclass
class TurnoPlan:
    sucursal: int  # índice
    caja: int  # índice dentro de las cajas de la sucursal
    cajero: int  # usuario_id
    abierto: datetime
    cerrado: datetime
    ventas: list[VentaPlan] = field(default_factory=list)
    devoluciones: list[DevolucionPlan] = field(default_factory=list)
    descuadre: Decimal = Decimal("0")
    id: int | None = None


@dataclass
class ReservaPlan:
    sucursal: int
    cliente: int
    inicio: datetime
    fin: datetime
    estado: str
    lineas: list[tuple[int, int]]  # (variante, cantidad)
    observacion: str | None = None
    id: int | None = None


@dataclass
class Movimiento:
    tipo: str
    cantidad: int
    momento: datetime
    motivo: str
    usuario_id: int | None
    reservada: int = 0
    referencia: str | None = None


@dataclass
class Resumen:
    slug: str
    plan: str
    sucursales: list[str] = field(default_factory=list)
    usuarios: dict[str, int] = field(default_factory=dict)
    productos: int = 0
    variantes: int = 0
    existencias: int = 0
    movimientos: int = 0
    turnos: int = 0
    ventas: int = 0
    devoluciones: int = 0
    reservas: dict[str, int] = field(default_factory=dict)

    def imprimir(self) -> None:
        print(f"  [{self.slug}] plan {self.plan} · sucursales: {', '.join(self.sucursales)}")
        print("     usuarios: " + ", ".join(f"{k} {v}" for k, v in self.usuarios.items()))
        print(f"     catálogo: {self.productos} productos, {self.variantes} variantes,"
              f" {self.existencias} existencias, {self.movimientos} movimientos")
        print(f"     caja: {self.turnos} turnos cerrados, {self.ventas} ventas,"
              f" {self.devoluciones} devoluciones")
        print("     reservas: " + ", ".join(f"{k} {v}" for k, v in self.reservas.items()))


# =====================================================================
#  Carga
# =====================================================================

def _momento(dia: date, hora: float) -> datetime:
    """`hora` (decimal, hora boliviana) de `dia`, como instante en UTC."""
    local = datetime.combine(dia, time(0, 0), tzinfo=tiempo.BOLIVIA) + timedelta(minutes=round(hora * 60))
    return local.astimezone(timezone.utc)


def verificar_que_no_esten(db: Session, orgs: list[Organizacion]) -> None:
    """Se niega a correr dos veces: ni el slug ni las cuentas pueden existir."""
    from app.modules.plataforma.models import Empresa
    from app.modules.seguridad.models import Cliente, Usuario

    problemas = []
    for org in orgs:
        if db.scalar(select(Empresa.id).where(Empresa.slug == org.slug)) is not None:
            problemas.append(f"ya existe la empresa «{org.slug}»")
        cuentas = db.scalar(select(func.count(Usuario.id)).where(
            Usuario.correo.like(f"%@{org.slug}.{DOMINIO}")))
        if cuentas:
            problemas.append(f"ya hay {cuentas} cuentas @{org.slug}.{DOMINIO}")
        docs = db.scalar(select(func.count(Cliente.id)).where(
            Cliente.documento.like(f"{org.slug[:6].upper()}-C%")))
        if docs:
            problemas.append(f"ya hay clientes con documento {org.slug[:6].upper()}-C..")
    if problemas:
        raise ErrorOrganizaciones(
            "Las organizaciones de demostración ya están cargadas: " + "; ".join(problemas)
            + ". Bórrelas primero con --borrar.")


def _catalogos_de_la_plataforma(db: Session, orgs: list[Organizacion]):
    from app.modules.organizacion.models import Ciudad
    from app.modules.plataforma.models import Plan
    from app.modules.seguridad.models import Rol

    planes = {p.codigo: p for p in db.scalars(select(Plan).where(Plan.activo.is_(True)))}
    faltan = sorted({o.plan for o in orgs} - planes.keys())
    if faltan:
        raise ErrorOrganizaciones(f"No hay plan activo con código {', '.join(faltan)}.")
    roles = {r.nombre: r.id for r in db.scalars(select(Rol))}
    for r in ("ADMINISTRADOR", "ENCARGADO", "CAJERO", "PROVEEDOR", "CLIENTE"):
        if r not in roles:
            raise ErrorOrganizaciones(f"No existe el rol {r}.")
    ciudades = {c.nombre: c.id for c in db.scalars(select(Ciudad).order_by(Ciudad.id))}
    if not ciudades:
        raise ErrorOrganizaciones("No hay ciudades cargadas.")
    return planes, roles, ciudades


def _elegir_ciudades(org: Organizacion, ciudades: dict[str, int], cuantas: int) -> list[str]:
    """Las preferidas que existan; si faltan, otras existentes; distintas entre sí."""
    elegidas = [c for c in org.ciudades if c in ciudades]
    elegidas += [c for c in ciudades if c not in elegidas]
    return elegidas[:cuantas]


def cargar_organizacion(db: Session, org: Organizacion, *, planes, roles, ciudades,
                        hash_: str) -> Resumen:
    """Da de alta una empresa con todos sus datos. No hace commit.

    Al volver, la sesión queda en modo plataforma (como `crear_empresa`).
    """
    from app.core.tenencia import fijar_empresa, modo_plataforma
    from app.modules.catalogo.models import (
        Categoria, Coleccion, Color, Producto, Talla, Temporada, VarianteProducto)
    from app.modules.catalogo.service import armar_sku
    from app.modules.inventario.models import Existencia, MovimientoInventario
    from app.modules.organizacion.models import Empleado, Proveedor, Sucursal
    from app.modules.plataforma.models import ClienteEmpresa, Empresa, Suscripcion
    from app.modules.plataforma.suscripciones import registrar_pago
    from app.modules.reservas.models import DetalleReserva, Reserva
    from app.modules.seguridad.models import Cliente, Usuario
    from app.modules.ventas.models import (
        Caja, DetalleDevolucion, DetalleVenta, Devolucion, TurnoCaja, Venta)

    azar = random.Random(f"organizaciones-demo-{org.slug}")
    plan = planes[org.plan]
    resumen = Resumen(slug=org.slug, plan=plan.nombre)
    hoy = tiempo.hoy()
    ahora = tiempo.ahora()

    # --- Límites del plan (RN-04): nunca se pasan --------------------------
    n_suc = org.sucursales
    if plan.max_sucursales is not None:
        n_suc = min(n_suc, plan.max_sucursales)
    nombres_ciudad = _elegir_ciudades(org, ciudades, n_suc)
    n_suc = max(1, len(nombres_ciudad))
    cajeros = org.cajeros_por_sucursal
    if plan.max_empleados is not None:
        # encargado + cajeros por sucursal son empleados (el admin y el proveedor no).
        while n_suc * (1 + cajeros) > plan.max_empleados and cajeros > 1:
            cajeros -= 1
        if n_suc * (1 + cajeros) > plan.max_empleados:
            raise ErrorOrganizaciones(f"El plan {plan.nombre} no alcanza para {org.slug}.")

    # --- 1. Empresa (modo plataforma), como el CU-01 ------------------------
    modo_plataforma(db)
    empresa = Empresa(nombre=org.nombre, razon_social=org.razon_social, nit=org.nit,
                      slug=org.slug, correo_contacto=correo("admin", None, org.slug))
    db.add(empresa)
    db.flush()
    try:
        # Desde acá, lo que se escribe es de la empresa nueva.
        fijar_empresa(db, empresa.id)

        suscripcion = Suscripcion(plan_id=plan.id, inicio=hoy,
                                  vencimiento=hoy + timedelta(days=plan.duracion_dias))
        db.add(suscripcion)
        db.flush()
        registrar_pago(db, suscripcion, plan, "ALTA")

        # --- 2. Sucursales y cajas ------------------------------------------
        sucursales = []
        usados: dict[str, int] = {}
        for nombre_ciudad in nombres_ciudad:
            barrios = BARRIOS.get(nombre_ciudad, [("Centro", f"Calle Comercio #100, {nombre_ciudad}")])
            barrio, direccion = barrios[usados.get(nombre_ciudad, 0) % len(barrios)]
            usados[nombre_ciudad] = usados.get(nombre_ciudad, 0) + 1
            sucursales.append(Sucursal(
                ciudad_id=ciudades[nombre_ciudad], nombre=f"{org.nombre} {barrio}",
                direccion=direccion, telefono=f"7{azar.randint(1000000, 9999999)}",
                horario_apertura=time(9), horario_cierre=time(20),
                capacidad_vestidores=azar.choice([2, 3])))
        db.add_all(sucursales)
        db.flush()
        resumen.sucursales = [s.nombre for s in sucursales]
        n_cajas = 2 if org.cajeros_por_sucursal >= 2 else 1
        cajas = {i: [Caja(sucursal_id=s.id, nombre=f"Caja {k + 1}", activa=True)
                     for k in range(n_cajas)] for i, s in enumerate(sucursales)}
        db.add_all([c for lista in cajas.values() for c in lista])

        # --- 3. Personal ------------------------------------------------------
        def usuario(rol: str, numero: int | None, nombres: str, apellidos: str) -> Usuario:
            return Usuario(correo=correo(rol.lower() if rol != "ADMINISTRADOR" else "admin",
                                         numero, org.slug),
                           hash_contrasena=hash_, nombres=nombres, apellidos=apellidos,
                           rol_id=roles[rol], activo=True, empresa_id=empresa.id)

        admin = usuario("ADMINISTRADOR", None, *org.administrador)
        encargados = [usuario("ENCARGADO", i + 1, azar.choice(NOMBRES_F + NOMBRES_M),
                              f"{azar.choice(APELLIDOS)} {azar.choice(APELLIDOS)}")
                      for i in range(n_suc)]
        lista_cajeros = [usuario("CAJERO", i + 1, azar.choice(NOMBRES_F + NOMBRES_M),
                                 f"{azar.choice(APELLIDOS)} {azar.choice(APELLIDOS)}")
                         for i in range(n_suc * cajeros)]
        proveedor_usuario = usuario("PROVEEDOR", 1, azar.choice(NOMBRES_M),
                                    f"{azar.choice(APELLIDOS)} {azar.choice(APELLIDOS)}")
        db.add_all([admin, *encargados, *lista_cajeros, proveedor_usuario])
        db.flush()
        cajeros_de = {i: lista_cajeros[i * cajeros:(i + 1) * cajeros] for i in range(n_suc)}
        empleados = []
        for i, u in enumerate(encargados):
            empleados.append(Empleado(usuario_id=u.id, sucursal_id=sucursales[i].id,
                                      documento=f"{org.prefijo}-E{i + 1:02d}", cargo="ENCARGADO",
                                      fecha_ingreso=hoy - timedelta(days=200)))
        for i, lista in cajeros_de.items():
            for u in lista:
                n = lista_cajeros.index(u) + 1
                empleados.append(Empleado(usuario_id=u.id, sucursal_id=sucursales[i].id,
                                          documento=f"{org.prefijo}-C{n:02d}", cargo="CAJERO",
                                          fecha_ingreso=hoy - timedelta(days=150)))
        proveedor = Proveedor(usuario_id=proveedor_usuario.id, razon_social=org.proveedor[0],
                              identificacion_tributaria=org.proveedor[1],
                              contacto="Atención a tiendas",
                              correo=correo("proveedor", 1, org.slug),
                              telefono=f"4{azar.randint(100000, 999999)}")
        db.add_all([*empleados, proveedor])
        db.flush()
        resumen.usuarios = {"admin": 1, "encargado": len(encargados),
                            "cajero": len(lista_cajeros), "proveedor": 1}

        # --- 4. Catálogo ------------------------------------------------------
        raices = {nombre: Categoria(nombre=nombre, orden=k)
                  for k, nombre in enumerate(org.categorias)}
        db.add_all(raices.values())
        db.flush()
        subcategorias = {}
        for raiz, hijas in org.categorias.items():
            for k, hija in enumerate(hijas):
                subcategorias[hija] = Categoria(nombre=hija, orden=k,
                                                categoria_padre_id=raices[raiz].id)
        tallas = {(tipo, codigo): Talla(tipo_prenda=tipo, codigo=codigo, orden=k)
                  for tipo, codigos in TALLAS.items() for k, codigo in enumerate(codigos)}
        colores = {n: Color(nombre=n, hexadecimal=h) for n, h in org.colores.items()}
        temporada = Temporada(nombre=org.temporada, descripcion=f"Temporada de {org.nombre}",
                              fecha_inicio=hoy - timedelta(days=90),
                              fecha_fin=hoy + timedelta(days=150))
        db.add_all([*subcategorias.values(), *tallas.values(), *colores.values(), temporada])
        db.flush()
        coleccion = Coleccion(temporada_id=temporada.id, nombre=org.coleccion,
                              descripcion=f"Colección {org.coleccion}")
        db.add(coleccion)
        db.flush()

        productos = []
        for k, p in enumerate(org.productos):
            productos.append(Producto(
                codigo=f"{org.prefijo}-{k + 1:02d}", nombre=p.nombre,
                descripcion=f"{p.nombre}. Colección {org.coleccion} de {org.nombre}.",
                categoria_id=subcategorias[p.subcategoria].id, proveedor_id=proveedor.id,
                temporada_id=temporada.id, coleccion_id=coleccion.id,
                precio_base=Decimal(p.precio)))
        db.add_all(productos)
        db.flush()
        variantes: list[VarianteProducto] = []
        precios: list[Decimal] = []
        for producto, p in zip(productos, org.productos):
            codigos = TALLAS[p.tipo_talla]
            for codigo in codigos:
                for nombre_color in p.colores:
                    variantes.append(VarianteProducto(
                        producto_id=producto.id, talla_id=tallas[(p.tipo_talla, codigo)].id,
                        color_id=colores[nombre_color].id,
                        sku=armar_sku(producto.codigo, codigo, nombre_color),
                        precio=Decimal(p.precio)))
                    precios.append(Decimal(p.precio))
        db.add_all(variantes)
        db.flush()
        resumen.productos = len(productos)
        resumen.variantes = len(variantes)

        # --- 5. Clientes (cuenta de la plataforma + cliente_empresa) -----------
        usuarios_cli = []
        for n in range(1, CLIENTES_POR_EMPRESA + 1):
            femenino = n % 3 != 0
            usuarios_cli.append(Usuario(
                correo=correo("cliente", n, org.slug), hash_contrasena=hash_,
                nombres=azar.choice(NOMBRES_F if femenino else NOMBRES_M),
                apellidos=f"{azar.choice(APELLIDOS)} {azar.choice(APELLIDOS)}",
                rol_id=roles["CLIENTE"], activo=True,
                empresa_id=null()))  # el cliente no es de una empresa (RN-13)
        db.add_all(usuarios_cli)
        db.flush()
        clientes = [Cliente(usuario_id=u.id, documento=documento_cliente(org, n),
                            telefono=f"7{azar.randint(1000000, 9999999)}",
                            talla_superior=azar.choice(TALLAS["SUPERIOR"]),
                            talla_inferior=azar.choice(TALLAS["INFERIOR"]))
                    for n, u in enumerate(usuarios_cli, start=1)]
        db.add_all(clientes)
        db.flush()
        db.add_all([ClienteEmpresa(cliente_id=c.id) for c in clientes])
        db.flush()
        resumen.usuarios["cliente"] = len(clientes)

        # --- 6. El plan de la operación (en memoria) ----------------------------
        turnos, reservas = _planear(azar, org, n_suc=n_suc, n_cajas=n_cajas,
                                    cajeros_de={i: [u.id for u in l] for i, l in cajeros_de.items()},
                                    precios=precios, hoy=hoy)
        movs: dict[tuple[int, int], list[Movimiento]] = {}

        def mover(suc: int, var: int, m: Movimiento) -> None:
            movs.setdefault((suc, var), []).append(m)

        for t in turnos:
            for v in t.ventas:
                for l in v.lineas:
                    if v.reserva is not None:
                        mover(t.sucursal, l.variante, Movimiento(
                            "LIBERACION", l.cantidad, v.momento, "Reserva atendida, el cliente se la lleva",
                            t.cajero, reservada=-l.cantidad))
                    mover(t.sucursal, l.variante, Movimiento(
                        "VENTA", -l.cantidad, v.momento, "Venta en caja", t.cajero))
            for d in t.devoluciones:
                mover(t.sucursal, d.linea.variante, Movimiento(
                    "DEVOLUCION", 1, d.momento, "Devolución en caja", t.cajero))
        for r in reservas:
            for var, cant in r.lineas:
                mover(r.sucursal, var, Movimiento(
                    "RESERVA", -cant, r.inicio - timedelta(hours=20), "Reserva del cliente",
                    None, reservada=cant))
                if r.estado in ("CANCELADA", "EXPIRADA"):
                    cuando = (r.inicio - timedelta(hours=4) if r.estado == "CANCELADA"
                              else r.fin + timedelta(hours=24))
                    mover(r.sucursal, var, Movimiento(
                        "LIBERACION", cant, cuando,
                        "Reserva cancelada por el cliente" if r.estado == "CANCELADA"
                        else "Reserva expirada", None, reservada=-cant))

        # --- 7. Escritura: turnos, reservas, ventas, devoluciones ---------------
        filas_turno = []
        for t in turnos:
            efectivo = sum((v.total for v in t.ventas if v.metodo == "EFECTIVO"), Decimal("0"))
            devuelto = sum((d.monto for d in t.devoluciones), Decimal("0"))
            esperado = APERTURA + efectivo - devuelto
            filas_turno.append(TurnoCaja(
                caja_id=cajas[t.sucursal][t.caja].id, usuario_id=t.cajero,
                abierto_en=t.abierto, cerrado_en=t.cerrado, monto_apertura=APERTURA,
                monto_esperado=esperado, monto_cierre=esperado + t.descuadre))
        filas_reserva = [Reserva(
            cliente_id=clientes[r.cliente].id, sucursal_id=sucursales[r.sucursal].id,
            franja_inicio=r.inicio, franja_fin=r.fin, estado=r.estado,
            observacion=r.observacion, creado_en=r.inicio - timedelta(hours=20),
            actualizado_en=r.inicio - timedelta(hours=20)) for r in reservas]
        db.add_all(filas_turno + filas_reserva)
        db.flush()
        for t, f in zip(turnos, filas_turno):
            t.id = f.id
        for r, f in zip(reservas, filas_reserva):
            r.id = f.id
        db.add_all([DetalleReserva(reserva_id=r.id, variante_id=variantes[var].id, cantidad=cant,
                                   resultado_prueba="LLEVA" if r.estado == "ATENDIDA" else None)
                    for r in reservas for var, cant in r.lineas])

        contador: dict[date, int] = {}
        filas_venta = []
        planes_venta = []
        for t in turnos:
            for v in t.ventas:
                dia = tiempo.en_bolivia(v.momento).date()
                contador[dia] = contador.get(dia, 0) + 1
                v.codigo = f"VP-{dia:%Y%m%d}-{org.letra}{contador[dia]:03d}"
                filas_venta.append(Venta(
                    codigo=v.codigo, canal="PRESENCIAL", estado="PAGADA",
                    cliente_id=clientes[v.cliente].id if v.cliente is not None else None,
                    sucursal_id=sucursales[t.sucursal].id, turno_caja_id=t.id,
                    reserva_id=v.reserva.id if v.reserva else None, metodo_pago=v.metodo,
                    subtotal=v.subtotal, descuento=v.descuento, total=v.total,
                    creado_en=v.momento, actualizado_en=v.momento))
                planes_venta.append(v)
        db.add_all(filas_venta)
        db.flush()
        for v, f in zip(planes_venta, filas_venta):
            v.id = f.id
        db.add_all([DetalleVenta(venta_id=v.id, variante_id=variantes[l.variante].id,
                                 cantidad=l.cantidad, precio_unitario=l.precio,
                                 descuento_unitario=l.descuento, creado_en=v.momento)
                    for v in planes_venta for l in v.lineas])
        planes_dev = [(t, d) for t in turnos for d in t.devoluciones]
        filas_dev = [Devolucion(
            venta_id=d.venta.id, turno_caja_id=t.id, origen="CAJA", tipo="DEVOLUCION",
            motivo=d.motivo, monto=d.monto, diferencia=Decimal("0"), estado="CERRADA",
            conforme=True, creado_en=d.momento) for t, d in planes_dev]
        db.add_all(filas_dev)
        db.flush()
        db.add_all([DetalleDevolucion(devolucion_id=f.id, variante_id=variantes[d.linea.variante].id,
                                      cantidad=1, creado_en=d.momento)
                    for (t, d), f in zip(planes_dev, filas_dev)])
        resumen.turnos = len(turnos)
        resumen.ventas = len(planes_venta)
        resumen.devoluciones = len(planes_dev)
        for r in reservas:
            resumen.reservas[r.estado] = resumen.reservas.get(r.estado, 0) + 1

        # --- 8. Existencias con su historial ------------------------------------
        primer_dia = min((t.abierto for t in turnos), default=ahora) - timedelta(days=3)
        filas_existencia = []
        historiales = []
        for suc in range(n_suc):
            for var in range(len(variantes)):
                lista = sorted(movs.get((suc, var), []), key=lambda m: m.momento)
                salida = -sum(m.cantidad for m in lista if m.cantidad < 0)
                bajo = azar.random() < 0.05
                ingreso = salida + (1 if bajo else azar.randint(3, 12))
                lista.insert(0, Movimiento(
                    "INGRESO", ingreso, primer_dia, f"Ingreso inicial de {org.proveedor[0]}"[:200],
                    encargados[suc].id, referencia=f"REM-{org.prefijo}-{suc + 1:02d}"))
                disponible = sum(m.cantidad for m in lista)
                reservada = sum(m.reservada for m in lista)
                filas_existencia.append(Existencia(
                    variante_id=variantes[var].id, sucursal_id=sucursales[suc].id,
                    cantidad_disponible=disponible, cantidad_reservada=reservada,
                    stock_minimo=3 if bajo else 2, creado_en=primer_dia))
                historiales.append(lista)
        db.add_all(filas_existencia)
        db.flush()
        filas_mov = []
        for e, lista in zip(filas_existencia, historiales):
            for m in lista:
                filas_mov.append(MovimientoInventario(
                    existencia_id=e.id, tipo=m.tipo, cantidad=m.cantidad, motivo=m.motivo,
                    proveedor_id=proveedor.id if m.tipo == "INGRESO" else None,
                    referencia=m.referencia, usuario_id=m.usuario_id, creado_en=m.momento))
        db.add_all(filas_mov)
        db.flush()
        resumen.existencias = len(filas_existencia)
        resumen.movimientos = len(filas_mov)
    finally:
        modo_plataforma(db)
    return resumen


def _planear(azar: random.Random, org: Organizacion, *, n_suc: int, n_cajas: int,
             cajeros_de: dict[int, list[int]], precios: list[Decimal], hoy: date):
    """Turnos con ventas y devoluciones, y reservas en todos los estados."""
    n_var = len(precios)
    pesos_var = [azar.uniform(0.3, 2.0) for _ in range(n_var)]
    por_dia = {0: 0.9, 1: 0.85, 2: 0.9, 3: 1.0, 4: 1.15, 5: 1.4, 6: 0.75}
    fieles = list(range(0, 6))
    turnos: list[TurnoPlan] = []
    primero = hoy - timedelta(days=org.semanas * 7)

    def lineas_al_azar() -> list[Linea]:
        elegidas = set(azar.choices(range(n_var), weights=pesos_var, k=azar.choice([1, 1, 2, 2, 3])))
        resultado = []
        for var in elegidas:
            descuento = _dinero(precios[var] * Decimal("0.10")) if azar.random() < 0.12 else Decimal("0")
            resultado.append(Linea(var, azar.choice([1, 1, 1, 2]), precios[var], descuento))
        return resultado

    for suc in range(n_suc):
        for semana in range(org.semanas):
            inicio = primero + timedelta(days=semana * 7)
            for k, d in enumerate(sorted(azar.sample(range(7), org.turnos_por_semana))):
                dia = inicio + timedelta(days=d)
                if dia >= hoy:
                    continue
                abierto = _momento(dia, 9 + azar.uniform(-0.2, 0.4))
                cerrado = abierto + timedelta(hours=10 + azar.uniform(-0.5, 0.5))
                lista = cajeros_de[suc]
                t = TurnoPlan(sucursal=suc, caja=(semana + k) % n_cajas,
                              cajero=lista[(semana + k) % len(lista)],
                              abierto=abierto, cerrado=cerrado)
                for _ in range(max(2, round(azar.gauss(6 * por_dia[dia.weekday()], 1.5)))):
                    r = azar.random()
                    cliente = (azar.choice(fieles) if r < 0.3 else
                               azar.randrange(CLIENTES_POR_EMPRESA) if r < 0.6 else None)
                    t.ventas.append(VentaPlan(
                        momento=abierto + (cerrado - abierto) * azar.uniform(0.03, 0.97),
                        cliente=cliente,
                        metodo=azar.choices(("EFECTIVO", "TARJETA", "QR"), weights=(5, 3, 2))[0],
                        lineas=lineas_al_azar()))
                t.descuadre = _dinero(azar.uniform(-3, 3))
                turnos.append(t)

    turnos.sort(key=lambda t: t.abierto)
    # Un faltante notorio en una empresa con analítica: lo marca la búsqueda de anomalías.
    if org.plan == "EMPRESARIAL" and len(turnos) > 6:
        turnos[len(turnos) * 3 // 4].descuadre = Decimal("-180.00")

    # Devoluciones: una prenda de una venta vuelve 1 a 6 días después, en la misma sucursal.
    hechas = intentos = 0
    while hechas < org.devoluciones and intentos < 1000:
        intentos += 1
        origen = azar.choice(turnos)
        destino = next((t for t in turnos if t.sucursal == origen.sucursal
                        and timedelta(hours=12) < t.abierto - origen.cerrado < timedelta(days=6)
                        and azar.random() < 0.6), None)
        libres = [v for v in origen.ventas if not v.devuelta and v.reserva is None]
        if destino is None or not libres:
            continue
        venta = azar.choice(libres)
        venta.devuelta = True
        destino.devoluciones.append(DevolucionPlan(
            venta, destino.abierto + (destino.cerrado - destino.abierto) * azar.uniform(0.05, 0.95),
            venta.lineas[0], azar.choice(MOTIVOS_DEVOLUCION)))
        hechas += 1

    # Reservas por sucursal: 2 pendientes (mañana y pasado), 2 atendidas con su
    # venta en un turno, 1 cancelada y 1 expirada.
    reservas: list[ReservaPlan] = []
    for suc in range(n_suc):
        def lineas_reserva() -> list[tuple[int, int]]:
            return [(v, 1) for v in sorted(set(azar.sample(range(n_var), azar.choice([1, 2]))))]

        for dias, hora in ((1, 11.0), (2, 16.5)):
            ini = _momento(hoy + timedelta(days=dias), hora)
            reservas.append(ReservaPlan(suc, azar.randrange(CLIENTES_POR_EMPRESA), ini,
                                        ini + timedelta(minutes=30), "PENDIENTE", lineas_reserva(),
                                        "Quiere probarse antes de llevar"))
        propios = [t for t in turnos if t.sucursal == suc]
        for t in azar.sample(propios, min(2, len(propios))):
            ini = t.abierto + timedelta(hours=2)
            r = ReservaPlan(suc, azar.randrange(CLIENTES_POR_EMPRESA), ini,
                            ini + timedelta(minutes=30), "ATENDIDA", lineas_reserva())
            reservas.append(r)
            t.ventas.append(VentaPlan(
                momento=r.fin - timedelta(minutes=5), cliente=r.cliente, metodo="TARJETA",
                lineas=[Linea(v, c, precios[v], Decimal("0")) for v, c in r.lineas], reserva=r))
        for estado, hace in (("CANCELADA", 9), ("EXPIRADA", 5)):
            ini = _momento(hoy - timedelta(days=hace), 15.0)
            reservas.append(ReservaPlan(suc, azar.randrange(CLIENTES_POR_EMPRESA), ini,
                                        ini + timedelta(minutes=30), estado, lineas_reserva()))
    for t in turnos:
        t.ventas.sort(key=lambda v: v.momento)
    return turnos, reservas


# =====================================================================
#  Borrado
# =====================================================================

def _tablas_de_empresa_en_orden():
    """Las tablas con `empresa_id`, de las hijas a las madres (sin usuario ni empresa)."""
    from app.db.base import Base

    return [t for t in reversed(Base.metadata.sorted_tables)
            if "empresa_id" in t.c and t.name not in ("usuario", "empresa")]


def borrar_organizacion(db: Session, org: Organizacion) -> dict[str, int]:
    """Quita la empresa entera y las cuentas de sus clientes. No hace commit."""
    from app.core.tenencia import fijar_empresa, modo_plataforma
    from app.modules.plataforma.models import Empresa
    from app.modules.seguridad.models import Usuario

    cuenta: dict[str, int] = {}
    modo_plataforma(db)
    empresa = db.scalar(select(Empresa).where(Empresa.slug == org.slug))
    if empresa is not None:
        marca = db.scalar(select(Usuario.id).where(
            Usuario.empresa_id == empresa.id, Usuario.correo == correo("admin", None, org.slug)))
        if marca is None:
            raise ErrorOrganizaciones(
                f"La empresa «{org.slug}» existe pero no tiene la cuenta "
                f"{correo('admin', None, org.slug)}: no la creó este script y no se toca.")
        empresa_id = empresa.id
        try:
            # Con el contexto de la empresa, el RLS impide tocar filas de otra.
            fijar_empresa(db, empresa_id)
            for tabla in _tablas_de_empresa_en_orden():
                n = db.execute(tabla.delete().where(tabla.c.empresa_id == empresa_id)).rowcount
                if n:
                    cuenta[tabla.name] = n
            cuenta["usuario (personal)"] = db.execute(
                delete(Usuario).where(Usuario.empresa_id == empresa_id)).rowcount
        finally:
            modo_plataforma(db)
        db.execute(delete(Empresa).where(Empresa.id == empresa_id))
        cuenta["empresa"] = 1
    # Los inicios de sesión con estas cuentas: la bitácora del login los anota en
    # la empresa por omisión (la del encabezado, todavía sin slug), no en la
    # demo. Se borran por el actor, que solo puede ser una cuenta @<slug>.test.
    from app.modules.bitacora.models import AsientoBitacora

    n = db.execute(delete(AsientoBitacora).where(
        AsientoBitacora.actor.like(f"%@{org.slug}.{DOMINIO}"))).rowcount
    if n:
        cuenta["bitacora (logins)"] = n
    # Las cuentas de la plataforma de sus clientes: borrar el usuario borra en
    # cascada `cliente`, sus `cliente_empresa`, direcciones y preferencias.
    patron = [correo("cliente", n, org.slug) for n in range(1, CLIENTES_POR_EMPRESA + 1)]
    n = db.execute(delete(Usuario).where(Usuario.empresa_id.is_(None),
                                         Usuario.correo.in_(patron))).rowcount
    if n:
        cuenta["usuario (clientes)"] = n
    db.flush()
    return cuenta


# =====================================================================
#  Línea de comandos
# =====================================================================

def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Carga (o borra) cuatro organizaciones de demostración.")
    p.add_argument("--empresa", choices=[o.slug for o in ORGANIZACIONES],
                   help="solo esta organización (por omisión, las cuatro)")
    p.add_argument("--dry-run", action="store_true", help="muestra lo que haría y deshace todo")
    p.add_argument("--borrar", action="store_true", help="quita las organizaciones de demostración")
    p.add_argument("--si", action="store_true", help="no pedir confirmación")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    from scripts.datos_demo_analitica import _cargar_todos_los_modelos

    _cargar_todos_los_modelos()
    from app.core.config import settings
    from app.core.tenencia import CLAVE_PLATAFORMA
    from app.db.session import SessionLocal

    if not settings.APP_DB_ROLE:
        print("ERROR: falta APP_DB_ROLE (p. ej. violet_app). Sin él la conexión se salta el RLS"
              " y el script podría escribir en la empresa equivocada.")
        return 1

    orgs = [o for o in ORGANIZACIONES if args.empresa in (None, o.slug)]
    url = make_url(settings.DATABASE_URL)
    accion = "BORRAR" if args.borrar else "CARGAR"
    print("=" * 70)
    print(" ORGANIZACIONES DE DEMOSTRACIÓN (multitenant)")
    print(f" Base:    {url.host}:{url.port or 5432} / {url.database}  (rol {settings.APP_DB_ROLE})")
    print(f" Empresas: {', '.join(f'{o.slug} ({o.plan})' for o in orgs)}")
    print(f" Acción:  {accion}{' (simulacro: no se guarda nada)' if args.dry_run else ''}")
    print("=" * 70)
    if not args.si and not args.dry_run:
        escrito = input(f"Escriba {accion} para continuar: ").strip()
        if escrito != accion:
            print("No coincide. No se hizo nada.")
            return 1

    clave = os.environ.get("DEMO_ORGANIZACIONES_CLAVE") or CLAVE_POR_OMISION
    with SessionLocal(info={CLAVE_PLATAFORMA: True}) as db:
        try:
            if args.borrar:
                for org in orgs:
                    cuenta = borrar_organizacion(db, org)
                    print(f"  [{org.slug}] " + (", ".join(f"{t}: {n}" for t, n in cuenta.items())
                                                 or "no había nada"))
            else:
                verificar_que_no_esten(db, orgs)
                planes, roles, ciudades = _catalogos_de_la_plataforma(db, orgs)
                hash_ = hash_password(clave)
                for org in orgs:
                    cargar_organizacion(db, org, planes=planes, roles=roles,
                                        ciudades=ciudades, hash_=hash_).imprimir()
        except ErrorOrganizaciones as e:
            db.rollback()
            print(f"ERROR: {e}")
            return 1
        except Exception:
            db.rollback()
            print("ERROR inesperado: se deshizo todo, no quedó nada a medias.")
            raise
        if args.dry_run:
            db.rollback()
            print("Simulacro: se deshizo todo.")
        else:
            db.commit()
            if args.borrar:
                print("Listo: se borraron.")
            else:
                print(f"Listo. Entrar con el slug, rol+número@<slug>.{DOMINIO} y la clave"
                      f"{' de DEMO_ORGANIZACIONES_CLAVE' if 'DEMO_ORGANIZACIONES_CLAVE' in os.environ else f' {CLAVE_POR_OMISION}'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
