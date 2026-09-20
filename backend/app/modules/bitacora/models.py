"""
P12 - Bitacora / CU-42  |  capa: modelo

Realiza el **RNF14**: dejar rastro de quien hizo que y cuando.

QUE HUECO CIERRA
-----------------
El RNF10 ya exigia trazabilidad, pero **solo de existencias**: cada
modificacion de inventario queda como un `MovimientoInventario` inmutable.
Eso cubre la mercaderia y nada mas. No hay registro de quien entro al
sistema, quien cambio un precio, quien desactivo un producto, quien dio de
baja a un empleado ni quien abrio una caja.

En un sistema con cinco roles y operaciones sobre dinero, eso es un agujero:
cuando algo aparece cambiado, no hay forma de saber quien lo cambio.

POR QUE ES UNA TABLA Y NO UN ARCHIVO DE LOG
--------------------------------------------
El log de la aplicacion se pierde en cada despliegue ---Railway reinicia el
contenedor--- y no se puede consultar desde la aplicacion. Una bitacora que
el Administrador no puede leer no sirve para lo unico que se le pide.

INMUTABLE, COMO EL MOVIMIENTO DE INVENTARIO
--------------------------------------------
Misma decision **D4** que `MovimientoInventario`: no hay `actualizado_en`, y
el modulo no expone ninguna forma de editar ni borrar un asiento. Una
bitacora que se puede corregir no prueba nada --- justamente quien tendria
motivo para alterarla es quien tiene el rol para hacerlo.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AsientoBitacora(Base):
    """Una linea de la bitacora. Se escribe una vez y no se toca mas."""

    __tablename__ = "bitacora"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    #: Cuando paso. `timestamptz`, como todo lo demas: el instante es
    #: absoluto y la pantalla lo muestra en hora boliviana.
    ocurrido_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Queda nulo cuando no hay usuario: un intento de sesion con un correo
    # que no existe es JUSTO lo que hay que registrar, y exigir un usuario
    # dejaria fuera el caso mas interesante.
    #
    # `ondelete=SET NULL` y no `CASCADE`: borrar una cuenta no puede borrar
    # el rastro de lo que hizo. Por eso ademas se guarda el correo aparte.
    usuario_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuario.id", ondelete="SET NULL"), index=True
    )

    #: El correo TAL COMO ESTABA en ese momento, copiado a proposito.
    #:
    #: Duplica un dato que ya esta en `usuario`, y esta bien que lo duplique:
    #: si la cuenta se borra o cambia de correo, la bitacora tiene que seguir
    #: diciendo a nombre de quien se hizo la operacion. Una bitacora que se
    #: reescribe sola cuando cambian los datos maestros no es un registro
    #: historico.
    actor: Mapped[str | None] = mapped_column(String(160))

    #: El rol con el que actuo, tambien copiado: los roles se reasignan.
    rol: Mapped[str | None] = mapped_column(String(40))

    #: Que se hizo, en el vocabulario del negocio: INICIAR_SESION, CREAR,
    #: MODIFICAR, ELIMINAR, INTENTO_FALLIDO...
    accion: Mapped[str] = mapped_column(String(40), index=True)

    #: Sobre que. El nombre del recurso tal como aparece en la ruta
    #: (`producto`, `venta`, `sucursal`), no el de la tabla.
    entidad: Mapped[str | None] = mapped_column(String(60), index=True)

    #: Texto y no entero: hay recursos identificados por codigo y otros por
    #: una clave compuesta, y un entero obligaria a dejarlo nulo justo ahi.
    entidad_id: Mapped[str | None] = mapped_column(String(60))

    metodo: Mapped[str] = mapped_column(String(10))
    ruta: Mapped[str] = mapped_column(String(300))
    estado_http: Mapped[int] = mapped_column()

    #: Si la operacion salio bien. Se guarda calculado y no se deduce del
    #: codigo al leer: es la columna por la que se filtra para buscar
    #: intentos fallidos, y deducirla obligaria a un rango en cada consulta.
    exito: Mapped[bool] = mapped_column()

    #: Desde donde. Detras de Railway la de verdad viene en
    #: `X-Forwarded-For`; ver `middleware._ip_de`.
    ip: Mapped[str | None] = mapped_column(String(60))

    #: Recortado: hay agentes de usuario de 400 caracteres y no aportan nada
    #: despues del producto y la version.
    agente: Mapped[str | None] = mapped_column(String(200))

    #: Lo que no entra en columnas. **Nunca credenciales**: ver
    #: `service.registrar`, que filtra las claves sensibles antes de guardar.
    detalle: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    __table_args__ = (
        # El uso real es «que paso ultimamente», y casi siempre acotado a una
        # persona. Sin este indice compuesto, filtrar por usuario obliga a
        # ordenar por fecha despues de leer todas sus filas.
        Index("ix_bitacora_usuario_fecha", "usuario_id", "ocurrido_en"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<AsientoBitacora {self.ocurrido_en} {self.actor} "
            f"{self.accion} {self.entidad}>"
        )
