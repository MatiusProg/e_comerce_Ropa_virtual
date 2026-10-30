"""
P14 - Offline y sincronización / CU-13 a CU-19  |  capa: contrato (Pydantic)

EL CONTRATO DE SINCRONIZACIÓN (CU-17) ES EL MISMO PARA LA WEB Y EL MÓVIL
------------------------------------------------------------------------
La web (IndexedDB) y el móvil (SQLite) guardan la operación con la misma
forma y la mandan igual. Lo que cambia entre los dos es dónde la guardan, no
qué mandan.

LO QUE NO VIAJA, A PROPÓSITO
----------------------------
- La venta no trae `sucursal_id`: sale del turno que el dispositivo descargó
  al prepararse (CU-13) y que el servidor comprueba que sea de quien vende.
- Ningún dato de tarjeta: sin conexión solo se cobra en efectivo o con QR
  (RN-05), y del QR viaja solo la referencia que da el banco.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.modules.catalogo.promociones_schemas import DescuentoOut

MetodoOffline = Literal["EFECTIVO", "QR"]

#: Un lote por pedido. Un dispositivo que estuvo una semana sin red manda
#: varios lotes; uno de mil operaciones tendría tomados los bloqueos de
#: inventario mientras lo procesa.
MAXIMO_POR_LOTE = 50


# =====================================================================
# CU-13 Preparar el dispositivo
# =====================================================================

class PrendaOfflineOut(BaseModel):
    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str
    precio: Decimal
    descuento: DescuentoOut | None = None
    #: El saldo AL DESCARGAR. El dispositivo lo va restando con lo que vende,
    #: pero quien decide si alcanzó es el servidor al sincronizar (RN-06).
    disponible: int


class ClienteOfflineOut(BaseModel):
    """Lo mínimo para anotar a quién se le reservó (RF-11). Sin correo ni
    dirección: el dispositivo puede perderse."""

    id: int
    nombre: str
    documento: str | None


class SucursalOfflineOut(BaseModel):
    id: int
    nombre: str
    horario_apertura: str
    horario_cierre: str


class PaqueteDeMostradorOut(BaseModel):
    """Lo que el cajero se lleva al dispositivo para vender sin conexión."""

    generado_en: datetime
    #: Después de esta hora, la pantalla avisa que los datos pueden estar
    #: desactualizados (RF-13). No bloquea: vender con precios de ayer es
    #: mejor que no vender, y el servidor igual confirma cada venta.
    vigente_hasta: datetime
    empresa_id: int
    usuario_id: int
    sucursal: SucursalOfflineOut
    turno_caja_id: int
    caja_nombre: str
    prendas: list[PrendaOfflineOut]
    clientes: list[ClienteOfflineOut]


class DisponibleEnSucursalOut(BaseModel):
    sucursal_id: int
    disponible: int


class PrendaParaReservarOut(BaseModel):
    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str
    precio: Decimal
    sucursales: list[DisponibleEnSucursalOut]


class PaqueteDeClienteOut(BaseModel):
    """Lo que el cliente se lleva al móvil para reservar sin conexión (CU-15)."""

    generado_en: datetime
    vigente_hasta: datetime
    empresa_id: int
    sucursales: list[SucursalOfflineOut]
    prendas: list[PrendaParaReservarOut]


# =====================================================================
# CU-17 Sincronizar
# =====================================================================

class LineaOfflineIn(BaseModel):
    variante_id: int
    cantidad: int = Field(gt=0, le=1_000)
    #: El precio que se COBRÓ, el que el dispositivo tenía descargado. El
    #: servidor lo respeta: el cliente ya pagó eso y ya se fue.
    precio_unitario: Decimal = Field(gt=0)
    descuento_unitario: Decimal = Field(default=Decimal("0.00"), ge=0)


class PagoOfflineIn(BaseModel):
    """CU-16. Cobrar no confirma la operación: la confirma el servidor (RN-05)."""

    metodo: MetodoOffline
    monto: Decimal = Field(gt=0)
    #: El número de operación del QR. Obligatorio con QR: sin él, si hay que
    #: devolver (CU-19), no hay cómo encontrar el pago en el banco.
    referencia: str | None = Field(default=None, max_length=60)

    @model_validator(mode="after")
    def _qr_con_referencia(self) -> "PagoOfflineIn":
        if self.metodo == "QR" and not (self.referencia or "").strip():
            raise ValueError("Un pago con QR necesita la referencia del banco.")
        return self


class OperacionOfflineIn(BaseModel):
    uuid: UUID
    tipo: Literal["VENTA", "RESERVA"]
    creada_en: datetime
    lineas: list[LineaOfflineIn] = Field(min_length=1, max_length=50)
    pago: PagoOfflineIn | None = None

    #: VENTA: el turno del paquete de CU-13.
    turno_caja_id: int | None = None

    #: RESERVA: la sucursal y la franja (como en CU-22). Si la hace el
    #: cajero, la sucursal es la suya y el cliente es uno del paquete.
    sucursal_id: int | None = None
    cliente_id: int | None = None
    franja_inicio: datetime | None = None
    franja_fin: datetime | None = None

    @model_validator(mode="after")
    def _campos_segun_tipo(self) -> "OperacionOfflineIn":
        if self.tipo == "VENTA":
            if self.turno_caja_id is None:
                raise ValueError("Una venta offline necesita el turno de caja.")
            if self.pago is None:
                raise ValueError("Una venta offline se cobra en el acto (RN-05).")
        else:
            if self.franja_inicio is None or self.franja_fin is None:
                raise ValueError("Una reserva necesita su franja.")
            if self.franja_fin <= self.franja_inicio:
                raise ValueError("La franja termina antes de empezar.")
        vistas = [l.variante_id for l in self.lineas]
        if len(vistas) != len(set(vistas)):
            raise ValueError("La misma prenda aparece dos veces.")
        for linea in self.lineas:
            if linea.descuento_unitario > linea.precio_unitario:
                raise ValueError("El descuento no puede superar al precio.")
        return self


class LoteIn(BaseModel):
    dispositivo: str | None = Field(default=None, max_length=80)
    operaciones: list[OperacionOfflineIn] = Field(
        min_length=1, max_length=MAXIMO_POR_LOTE
    )

    @model_validator(mode="after")
    def _uuid_unico_en_el_lote(self) -> "LoteIn":
        uuids = [o.uuid for o in self.operaciones]
        if len(uuids) != len(set(uuids)):
            raise ValueError("Una operación aparece dos veces en el mismo lote.")
        return self


class ResultadoOut(BaseModel):
    """Lo que el dispositivo necesita para sacar la operación de su cola
    (RNF06: sale solo cuando el servidor la confirma o la rechaza)."""

    uuid: UUID
    tipo: str
    estado: Literal["CONFIRMADA", "RECHAZADA"]
    motivo: str | None
    venta_codigo: str | None
    reserva_id: int | None
    #: Rechazada y cobrada: hay que devolverle el dinero al cliente (CU-19).
    requiere_devolucion: bool
    devuelta: bool
    #: Ya había llegado antes: esta respuesta es la de la primera vez.
    repetida: bool
    recibida_en: datetime


class LoteOut(BaseModel):
    resultados: list[ResultadoOut]
    confirmadas: int
    rechazadas: int


# =====================================================================
# CU-18 y CU-19
# =====================================================================

class OperacionOut(ResultadoOut):
    """Una operación ya sincronizada, vista desde la sucursal."""

    sucursal_id: int
    usuario: str
    creada_en_cliente: datetime
    intentos: int
    metodo_pago: str | None
    monto_cobrado: Decimal | None
    referencia_pago: str | None
    devuelto_en: datetime | None
    metodo_devolucion: str | None
    referencia_devolucion: str | None


class DevolucionIn(BaseModel):
    """CU-19: el encargado le devolvió el dinero al cliente."""

    metodo: MetodoOffline
    referencia: str | None = Field(default=None, max_length=60)
    observacion: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _qr_con_referencia(self) -> "DevolucionIn":
        if self.metodo == "QR" and not (self.referencia or "").strip():
            raise ValueError("Una devolución por QR necesita la referencia del banco.")
        return self
