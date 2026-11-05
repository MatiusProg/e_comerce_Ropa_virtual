"""
P13 - Notificaciones / CU-40  |  capa: modelo

Realiza el **RF11**: el sistema notifica las reservas a la sucursal que
corresponde. Hasta el refinamiento del Ciclo 2 ese requisito estaba trazado a
CU-22 y CU-24 ---donde la reserva APARECE EN LA LISTA del Encargado cuando el
entra a mirarla---. Eso es consulta, no notificacion: nada salia a buscar al
destinatario. Esta tabla es lo que lo hace de verdad.

LOS CUATRO HECHOS QUE SE AVISAN
--------------------------------
Los fija docs/03-captura-requisitos.md, y no hay un quinto:

  RESERVA_EN_SUCURSAL   una reserva dirigida a su sucursal      -> Encargado
  RESERVA_PREPARADA     su reserva esta lista para retirar      -> Cliente
  PEDIDO_PAGADO         su pedido quedo pagado                  -> Cliente
  STOCK_BAJO            una prenda llego al punto de reposicion -> Encargado

POR QUE UNA TABLA Y NO SOLO UN CORREO
--------------------------------------
Porque son dos cosas distintas y una puede fallar sin la otra. El aviso DENTRO
de la aplicacion es el que siempre esta ---la degradacion acordada el 13/09 por
si no habia proveedor de correo--- y el correo es el que sale a buscar a la
persona. Guardar la fila primero y mandar el correo despues hace que un
proveedor caido no borre el aviso: queda PENDIENTE y se reintenta.

Es ademas lo que permite la campanita: `leida_en` es del aviso en la
aplicacion, no del correo, y un correo entregado no marca nada como leido.

`CanalDeAviso` DEL 2.3 NO ES UNA TABLA
---------------------------------------
En el diagrama de clases de analisis, CU-40 tiene tres clases: `Notificacion`,
`GestorNotificaciones` y `CanalDeAviso`. Las dos primeras son esta tabla y su
servicio; `CanalDeAviso` es la costura `app/integrations/correo`, que ya existia
desde CU-41 y no necesita persistirse: los canales no se dan de alta desde la
aplicacion, se eligen con la variable CORREO_PROVEEDOR. Una tabla de dos filas
fijas seria un maestro que nadie mantiene.

EL ESTADO DEL CORREO VIVE ACA Y NO EN UNA TABLA APARTE
-------------------------------------------------------
Un aviso sale por un solo canal ademas del de la aplicacion, asi que una
segunda tabla `envio` tendria exactamente una fila por notificacion. Cuando se
agregue un segundo canal ---SMS, push del movil--- ahi si corresponde separarla;
hoy seria una union sin ninguna pregunta que contestar.

INMUTABLE EN LO QUE IMPORTA
----------------------------
Ni el titulo ni el cuerpo se editan: son lo que se dijo en su momento. Lo unico
que cambia despues de nacer es `leida_en` y el resultado del envio. Por eso no
usa el mixin `Auditoria`: un `actualizado_en` sugeriria que el contenido se
puede corregir.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, DeEmpresa

#: Los cuatro hechos del RF11 y de la ficha de CU-40. La lista es cerrada a
#: proposito: un tipo nuevo es una decision de alcance, no un valor que alguien
#: pueda inventar desde el codigo que llama.
TIPOS_NOTIFICACION = (
    "RESERVA_EN_SUCURSAL",
    "RESERVA_PREPARADA",
    "PEDIDO_PAGADO",
    "STOCK_BAJO",
    # 3ra presentación: CU-33 y CU-34. Al origen le piden mercadería y al
    # destino le avisan que ya va en camino.
    "TRASPASO",
    # 3ra presentación · CU-26: las devoluciones por la web (CU-24 y CU-25).
    # Al encargado, que llegó una solicitud; al cliente, cómo se resolvió.
    "DEVOLUCION",
    # 3ra presentación: CU-42 y CU-43. El resultado de una operación hecha sin
    # conexión, y la devolución del dinero de una que se rechazó.
    "OPERACION_OFFLINE",
    "DEVOLUCION_PAGO",
)

#: OMITIDO es para el aviso que nace sin destinatario de correo ---un usuario
#: sin direccion--- o que se pide explicitamente solo en la aplicacion. No es lo
#: mismo que FALLIDO, y mezclarlos haria que el reintento persiguiera para
#: siempre correos que nunca hubo que mandar.
ESTADOS_CORREO = ("OMITIDO", "PENDIENTE", "ENVIADO", "FALLIDO")

#: CU-42: el push usa los mismos cuatro estados que el correo. OMITIDO = la
#: persona no tiene ningún dispositivo suscrito cuando nace el aviso.
ESTADOS_PUSH = ESTADOS_CORREO


class Notificacion(DeEmpresa, Base):
    """Un aviso dirigido a una persona por un hecho que ya ocurrio."""

    __tablename__ = "notificacion"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # CASCADE y no SET NULL, al reves que la bitacora: un aviso es PARA
    # alguien. Sin destinatario no queda un registro historico, queda una fila
    # que nadie puede leer y que nadie va a borrar.
    destinatario_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False
    )

    tipo: Mapped[str] = mapped_column(String(40), nullable=False)

    #: Lo que se ve en la campanita y lo que va como asunto del correo.
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)

    #: El texto plano del aviso. El HTML del correo se arma al enviarlo y no se
    #: guarda: es presentacion, y guardarla congelaria la plantilla.
    cuerpo: Mapped[str] = mapped_column(Text, nullable=False)

    #: Ruta RELATIVA de la web a donde lleva el aviso (`/mis-reservas/12`).
    #: Relativa y no absoluta porque el dominio cambia entre local y Railway, y
    #: un enlace guardado con el dominio de desarrollo no funciona en
    #: produccion. El correo la completa con WEB_BASE_URL al momento de enviar.
    enlace: Mapped[str | None] = mapped_column(String(300))

    #: A que apunta, para poder reconstruir el aviso o agrupar: `reserva`,
    #: `venta`, `existencia`. No es una clave foranea: las tres apuntan a
    #: tablas distintas y una FK por cada una dejaria dos columnas nulas
    #: siempre.
    entidad: Mapped[str | None] = mapped_column(String(60))
    entidad_id: Mapped[int | None] = mapped_column(BigInteger)

    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    #: Nulo mientras no se leyo. Es la columna por la que se cuenta la
    #: campanita, y por eso un booleano `leida` no alcanza: saber CUANDO se
    #: leyo es lo que permite decidir si todavia valia la pena el correo.
    leida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    correo_estado: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="PENDIENTE"
    )
    correo_enviado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    #: Por que fallo, recortado. Sirve para el reintento y para la defensa:
    #: distingue «el proveedor rechazo la direccion» de «no habia proveedor».
    correo_error: Mapped[str | None] = mapped_column(String(300))

    #: CU-42: el aviso push. Uno por notificación aunque la persona tenga
    #: varios dispositivos: ENVIADO = llegó al menos a uno. El detalle por
    #: dispositivo no se guarda porque no responde ninguna pregunta: el que
    #: falló porque se desinstaló la app se borra, y el resto llegó.
    push_estado: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="OMITIDO"
    )
    push_enviado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    push_error: Mapped[str | None] = mapped_column(String(300))

    __table_args__ = (
        CheckConstraint(
            "tipo IN ('RESERVA_EN_SUCURSAL', 'RESERVA_PREPARADA', "
            "'PEDIDO_PAGADO', 'STOCK_BAJO', 'TRASPASO', 'DEVOLUCION', "
            "'OPERACION_OFFLINE', 'DEVOLUCION_PAGO')",
            name="tipo_valido",
        ),
        CheckConstraint(
            "correo_estado IN ('OMITIDO', 'PENDIENTE', 'ENVIADO', 'FALLIDO')",
            name="correo_estado_valido",
        ),
        # Un correo ENVIADO tiene fecha de envio y ninguno de los otros tres la
        # tiene. Sin esto una fila puede decir PENDIENTE y traer fecha, y el
        # reintento no sabria a cual creerle.
        CheckConstraint(
            "(correo_estado = 'ENVIADO') = (correo_enviado_en IS NOT NULL)",
            name="enviado_tiene_fecha",
        ),
        CheckConstraint(
            "push_estado IN ('OMITIDO', 'PENDIENTE', 'ENVIADO', 'FALLIDO')",
            name="push_estado_valido",
        ),
        CheckConstraint(
            "(push_estado = 'ENVIADO') = (push_enviado_en IS NOT NULL)",
            name="push_enviado_tiene_fecha",
        ),
        # La consulta real es «las mias, de la mas nueva a la mas vieja». Sin el
        # indice compuesto hay que leer todas las de la persona antes de poder
        # ordenarlas.
        Index("ix_notificacion_destinatario_creada", "destinatario_id", "creada_en"),
        # El despachador busca SOLO las pendientes, que son pocas entre muchas.
        # Parcial a proposito: indexar las miles ya enviadas no sirve a nadie.
        Index(
            "ix_notificacion_pendientes",
            "creada_en",
            postgresql_where=text("correo_estado = 'PENDIENTE'"),
        ),
        Index(
            "ix_notificacion_push_pendientes",
            "creada_en",
            postgresql_where=text("push_estado = 'PENDIENTE'"),
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Notificacion {self.id} {self.tipo} -> {self.destinatario_id} "
            f"correo={self.correo_estado}>"
        )


class SuscripcionPush(DeEmpresa, Base):
    """CU-42: un dispositivo que acepta avisos push de una persona.

    Un teléfono con la app (FCM) o un navegador con la web instalada (Web
    Push). Una persona puede tener varios; un dispositivo es de una sola
    persona a la vez: si otra inicia sesión en él, la suscripción pasa a ella
    (no se le pueden seguir mandando a la primera los avisos de su caja).

    La unicidad es por empresa y no global por el RLS: un mismo navegador
    puede entrar a dos tiendas, y la fila de la otra es invisible desde acá.
    """

    __tablename__ = "suscripcion_push"
    __table_args__ = (
        CheckConstraint("canal IN ('FCM', 'WEBPUSH')", name="canal"),
        CheckConstraint(
            "canal <> 'WEBPUSH' OR (clave_p256dh IS NOT NULL AND clave_auth IS NOT NULL)",
            name="webpush_con_claves",
        ),
        UniqueConstraint("empresa_id", "direccion", name="uq_suscripcion_push_direccion"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuario.id", ondelete="CASCADE"), index=True, nullable=False
    )
    canal: Mapped[str] = mapped_column(String(10), nullable=False)
    #: El token de FCM o el endpoint de Web Push.
    direccion: Mapped[str] = mapped_column(Text, nullable=False)
    clave_p256dh: Mapped[str | None] = mapped_column(String(200))
    clave_auth: Mapped[str | None] = mapped_column(String(100))
    dispositivo: Mapped[str | None] = mapped_column(String(120))
    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    usada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
