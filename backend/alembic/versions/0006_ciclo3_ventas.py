"""Ciclo 3 - ventas, punto de venta y pagos: las nueve tablas de P7 y P8.

Crea `caja`, `turno_caja`, `venta`, `detalle_venta`, `comprobante`,
`devolucion` y `detalle_devolucion` (P7), mas `pago` y `transaccion_pasarela`
(P8), con las columnas fijadas en
docs/entregas/ciclo-3/00-esquema-de-ventas-y-pagos.md.

Escrita a mano, no con `--autogenerate`: autogenerar con los modelos del otro a
medio escribir produce migraciones que borran tablas ajenas.

SOBRE EL NUMERO Y DE QUIEN CUELGA
---------------------------------
El numero del archivo es un nombre reservado desde el Ciclo 2; el orden lo fija
`down_revision`. Cuando este identificador se reservo, la cabeza era la `0005`.
Ya no: entraron la `0008` (CU-41) y la `0009` (CU-26), las dos de Karen, asi que
esta cuelga de la `0009_ciclo3_carrito`.

    0005 -> 0008 -> 0009 -> 0006 -> 0007

Se lee raro y es correcta. Colgarla de la `0008` dejaria el arbol con dos
cabezas y `alembic upgrade head` fallaria pidiendo cual.

LO QUE ESTA MIGRACION NO CREA
-----------------------------
`carrito` y `carrito_detalle`. Ya existen desde la `0009`, y la version del
15/09 del documento de esquema las reservaba para aca por error. Se corrigio el
17/09.

QUE DESBLOQUEA
--------------
`tablero_service._ventas()` de CU-36, que hoy devuelve `disponible: false`
porque `venta` y `detalle_venta` no existian. Con esta migracion existen, y los
cuatro indicadores que faltaban -ventas del dia y del mes, ticket promedio y
prendas mas vendidas- ya tienen de donde salir.

P8 VIAJA EN ESTA MIGRACION
--------------------------
Los identificadores reservados solo nombran `ventas` y `promociones`: pagos no
tiene numero propio, y una venta digital sin su fila de pago esta a medias.

LOS NOMBRES DE LOS CHECK: SOLO EL SUFIJO
----------------------------------------
En los CHECK va **solo el sufijo** ('estado', no 'ck_venta_estado'): la
convencion de app/db/base.py antepone 'ck_<tabla>_' sola, y pasar el nombre
completo lo DUPLICA -- queda 'ck_venta_ck_venta_estado'.

No es teorico: la 0003 lo hizo mal y la 0004 tuvo que ir a arreglarlo. Esta
migracion tambien lo hizo mal en su primera escritura y lo atrapo
`alembic check`, que es la razon de correrlo antes de subir nada. El ejemplo
correcto a imitar es la 0009 de Karen, no la 0003.

Los FK, PK, UNIQUE e indices, en cambio, SI se escriben con el nombre completo:
ahi no hay convencion que anteponga nada.

Revision ID: 0006_ciclo3_ventas
Revises: 0009_ciclo3_carrito
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_ciclo3_ventas"
down_revision: str | None = "0009_ciclo3_carrito"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ================= P7 - Punto de venta ===============================
    # Caja y turno van PRIMERO: `venta.turno_caja_id` los referencia.
    op.create_table(
        "caja",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sucursal_id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=50), nullable=False),
        sa.Column("activa", sa.Boolean(), server_default="true", nullable=False),
        sa.ForeignKeyConstraint(
            ["sucursal_id"], ["sucursal.id"], name="fk_caja_sucursal_id_sucursal"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_caja"),
        # Dos cajas con el mismo nombre en la misma sucursal harian imposible
        # saber en cual se cobro. Entre sucursales si se repite.
        sa.UniqueConstraint("sucursal_id", "nombre", name="uq_caja_sucursal_id"),
    )
    op.create_index("ix_caja_sucursal_id", "caja", ["sucursal_id"], unique=False)

    op.create_table(
        "turno_caja",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("caja_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "abierto_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("cerrado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("monto_apertura", sa.Numeric(precision=10, scale=2), nullable=False),
        # Nulos hasta cerrar: uno lo cuenta la persona, el otro lo calcula el
        # sistema, y la diferencia entre los dos ES el arqueo.
        sa.Column("monto_cierre", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("monto_esperado", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.CheckConstraint(
            "cerrado_en IS NULL OR cerrado_en >= abierto_en",
            name="cierre_posterior",
        ),
        # Cerrar exige haber contado: un turno cerrado sin monto es un arqueo
        # que nadie hizo.
        sa.CheckConstraint(
            "cerrado_en IS NULL OR monto_cierre IS NOT NULL",
            name="cierre_con_monto",
        ),
        sa.ForeignKeyConstraint(
            ["caja_id"], ["caja.id"], name="fk_turno_caja_caja_id_caja"
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name="fk_turno_caja_usuario_id_usuario"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_turno_caja"),
    )
    op.create_index("ix_turno_caja_caja_id", "turno_caja", ["caja_id"], unique=False)
    op.create_index(
        "ix_turno_caja_usuario_id", "turno_caja", ["usuario_id"], unique=False
    )
    # UN SOLO TURNO ABIERTO POR CAJA, y es un indice unico PARCIAL porque el
    # UNIQUE normal prohibiria tambien los turnos ya cerrados, que son muchos y
    # legitimos. Dos turnos abiertos a la vez hacen que el arqueo no cierre
    # nunca: no se sabria a cual imputar lo cobrado.
    op.create_index(
        "ix_turno_caja_abierto",
        "turno_caja",
        ["caja_id"],
        unique=True,
        postgresql_where=sa.text("cerrado_en IS NULL"),
    )

    # ================= P7 - Ventas =======================================
    op.create_table(
        "venta",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        # Legible para el cliente. No es la PK: el numero que se muestra y el
        # que referencian las otras tablas son cosas distintas.
        sa.Column("codigo", sa.String(length=20), nullable=False),
        sa.Column("canal", sa.String(length=12), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        # Nulo a proposito: la venta presencial puede ser anonima.
        sa.Column("cliente_id", sa.BigInteger(), nullable=True),
        sa.Column("sucursal_id", sa.Integer(), nullable=False),
        sa.Column("turno_caja_id", sa.BigInteger(), nullable=True),
        # El puente de D2: una reserva atendida se cobra como venta presencial.
        sa.Column("reserva_id", sa.BigInteger(), nullable=True),
        sa.Column("modalidad_entrega", sa.String(length=10), nullable=True),
        sa.Column("direccion_id", sa.BigInteger(), nullable=True),
        sa.Column("subtotal", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "descuento",
            sa.Numeric(precision=10, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column("total", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "canal IN ('DIGITAL', 'PRESENCIAL')", name="canal"
        ),
        sa.CheckConstraint(
            "estado IN ('PENDIENTE_PAGO', 'PAGADA', 'ENTREGADA', 'CANCELADA')",
            name="estado",
        ),
        sa.CheckConstraint(
            "modalidad_entrega IS NULL OR modalidad_entrega IN ('RETIRO', 'ENVIO')",
            name="modalidad",
        ),
        # Los tres montos coherentes EN LA BASE, no solo en el servicio.
        sa.CheckConstraint("total = subtotal - descuento", name="total_coherente"),
        sa.CheckConstraint(
            "subtotal >= 0 AND descuento >= 0", name="montos_no_negativos"
        ),
        # Una venta presencial se cobra en una caja abierta; una digital no
        # pasa por ninguna. Sin esto un pedido web podria colgarse de un turno
        # y descuadrar el arqueo de una sucursal que no lo cobro.
        sa.CheckConstraint(
            "(canal = 'PRESENCIAL' AND turno_caja_id IS NOT NULL)"
            " OR (canal = 'DIGITAL' AND turno_caja_id IS NULL)",
            name="turno_segun_canal",
        ),
        sa.CheckConstraint(
            "(canal = 'DIGITAL' AND modalidad_entrega IS NOT NULL)"
            " OR (canal = 'PRESENCIAL' AND modalidad_entrega IS NULL)",
            name="modalidad_segun_canal",
        ),
        # Si es ENVIO hay que saber adonde, y si no lo es no hay direccion que
        # guardar.
        #
        # OJO CON DONDE VA EL `IS NOT DISTINCT FROM`: va en la comparacion con
        # 'ENVIO', no entre las dos mitades. En una venta PRESENCIAL
        # `modalidad_entrega` es NULL, y `NULL = 'ENVIO'` da NULL, no falso.
        # Escrito al reves, este CHECK rechazaba TODA venta presencial --- y
        # asi estuvo escrito hasta que lo atrapo el humo de esta migracion.
        sa.CheckConstraint(
            "(modalidad_entrega IS NOT DISTINCT FROM 'ENVIO')"
            " = (direccion_id IS NOT NULL)",
            name="direccion_si_envio",
        ),
        sa.ForeignKeyConstraint(
            ["cliente_id"], ["cliente.id"], name="fk_venta_cliente_id_cliente"
        ),
        sa.ForeignKeyConstraint(
            ["direccion_id"],
            ["direccion_cliente.id"],
            name="fk_venta_direccion_id_direccion_cliente",
        ),
        sa.ForeignKeyConstraint(
            ["reserva_id"], ["reserva.id"], name="fk_venta_reserva_id_reserva"
        ),
        sa.ForeignKeyConstraint(
            ["sucursal_id"], ["sucursal.id"], name="fk_venta_sucursal_id_sucursal"
        ),
        sa.ForeignKeyConstraint(
            ["turno_caja_id"],
            ["turno_caja.id"],
            name="fk_venta_turno_caja_id_turno_caja",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_venta"),
        sa.UniqueConstraint("codigo", name="uq_venta_codigo"),
        # Una reserva no se puede cobrar dos veces.
        sa.UniqueConstraint("reserva_id", name="uq_venta_reserva_id"),
    )
    op.create_index("ix_venta_canal", "venta", ["canal"], unique=False)
    op.create_index("ix_venta_estado", "venta", ["estado"], unique=False)
    op.create_index("ix_venta_cliente_id", "venta", ["cliente_id"], unique=False)
    op.create_index("ix_venta_sucursal_id", "venta", ["sucursal_id"], unique=False)
    op.create_index("ix_venta_turno_caja_id", "venta", ["turno_caja_id"], unique=False)
    # Indexado porque TODO el tablero de CU-36 corta por fecha: ventas del dia,
    # del mes y ticket promedio del periodo son tres consultas sobre esto.
    op.create_index("ix_venta_creado_en", "venta", ["creado_en"], unique=False)

    op.create_table(
        "detalle_venta",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("venta_id", sa.BigInteger(), nullable=False),
        sa.Column("variante_id", sa.BigInteger(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        # CONGELADO. Es el primer lugar donde el precio queda fijo: el carrito
        # de CU-26 lo lee en vivo a proposito. Si aca se leyera en vivo, el
        # historial de CU-29 y el ticket promedio de CU-36 cambiarian solos.
        sa.Column("precio_unitario", sa.Numeric(precision=10, scale=2), nullable=False),
        # Existe desde ahora aunque CU-12 no exista: agregarla despues obligaria
        # a decidir que descuento tenian las filas ya vendidas.
        sa.Column(
            "descuento_unitario",
            sa.Numeric(precision=10, scale=2),
            server_default="0",
            nullable=False,
        ),
        # Sin `actualizado_en`: INMUTABLE, como movimiento_inventario (D4). Una
        # correccion es una devolucion (CU-32), no un UPDATE.
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("cantidad > 0", name="cantidad_positiva"),
        sa.CheckConstraint(
            "precio_unitario >= 0 AND descuento_unitario >= 0",
            name="montos_no_negativos",
        ),
        # Regalar no es vender por menos que cero.
        sa.CheckConstraint(
            "descuento_unitario <= precio_unitario",
            name="descuento_acotado",
        ),
        sa.ForeignKeyConstraint(
            ["venta_id"],
            ["venta.id"],
            name="fk_detalle_venta_venta_id_venta",
            ondelete="CASCADE",
        ),
        # Sin CASCADE a la variante: una variante vendida no se borra, se
        # desactiva. Borrarla haria desaparecer la linea de una venta cerrada.
        sa.ForeignKeyConstraint(
            ["variante_id"],
            ["variante_producto.id"],
            name="fk_detalle_venta_variante_id_variante_producto",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_detalle_venta"),
        # Una variante aparece una vez por venta; dos unidades son cantidad 2.
        sa.UniqueConstraint("venta_id", "variante_id", name="uq_detalle_venta_venta_id"),
    )
    op.create_index(
        "ix_detalle_venta_venta_id", "detalle_venta", ["venta_id"], unique=False
    )
    op.create_index(
        "ix_detalle_venta_variante_id", "detalle_venta", ["variante_id"], unique=False
    )

    op.create_table(
        "comprobante",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("venta_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("numero", sa.String(length=20), nullable=False),
        # Se COPIAN del cliente al facturar: si despues cambia su NIT, la
        # factura ya emitida no cambia.
        sa.Column("nit_ci", sa.String(length=20), nullable=True),
        sa.Column("razon_social", sa.String(length=120), nullable=True),
        sa.Column(
            "emitido_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("tipo IN ('RECIBO', 'FACTURA')", name="tipo"),
        # Una factura sin datos de facturacion no es una factura.
        sa.CheckConstraint(
            "tipo = 'RECIBO' OR (nit_ci IS NOT NULL AND razon_social IS NOT NULL)",
            name="factura_con_datos",
        ),
        sa.ForeignKeyConstraint(
            ["venta_id"], ["venta.id"], name="fk_comprobante_venta_id_venta"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_comprobante"),
        # Una venta no tiene dos comprobantes: reimprimir no es reemitir.
        sa.UniqueConstraint("venta_id", name="uq_comprobante_venta_id"),
        sa.UniqueConstraint("numero", name="uq_comprobante_numero"),
    )

    # ================= P7 - Devoluciones =================================
    op.create_table(
        "devolucion",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("venta_id", sa.BigInteger(), nullable=False),
        # El dinero sale de una caja concreta. Sin esto el arqueo de CU-30 no
        # cerraria: `monto_esperado` resta justamente esto.
        sa.Column("turno_caja_id", sa.BigInteger(), nullable=False),
        sa.Column("motivo", sa.String(length=200), nullable=False),
        sa.Column("monto", sa.Numeric(precision=10, scale=2), nullable=False),
        # Sin `actualizado_en`: INMUTABLE.
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("monto >= 0", name="monto_no_negativo"),
        sa.ForeignKeyConstraint(
            ["venta_id"], ["venta.id"], name="fk_devolucion_venta_id_venta"
        ),
        sa.ForeignKeyConstraint(
            ["turno_caja_id"],
            ["turno_caja.id"],
            name="fk_devolucion_turno_caja_id_turno_caja",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_devolucion"),
    )
    op.create_index("ix_devolucion_venta_id", "devolucion", ["venta_id"], unique=False)
    op.create_index(
        "ix_devolucion_turno_caja_id", "devolucion", ["turno_caja_id"], unique=False
    )
    op.create_index(
        "ix_devolucion_creado_en", "devolucion", ["creado_en"], unique=False
    )

    op.create_table(
        "detalle_devolucion",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("devolucion_id", sa.BigInteger(), nullable=False),
        sa.Column("variante_id", sa.BigInteger(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "cantidad > 0", name="cantidad_positiva"
        ),
        sa.ForeignKeyConstraint(
            ["devolucion_id"],
            ["devolucion.id"],
            name="fk_detalle_devolucion_devolucion_id_devolucion",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["variante_id"],
            ["variante_producto.id"],
            name="fk_detalle_devolucion_variante_id_variante_producto",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_detalle_devolucion"),
        sa.UniqueConstraint(
            "devolucion_id", "variante_id", name="uq_detalle_devolucion_devolucion_id"
        ),
    )
    op.create_index(
        "ix_detalle_devolucion_devolucion_id",
        "detalle_devolucion",
        ["devolucion_id"],
        unique=False,
    )
    op.create_index(
        "ix_detalle_devolucion_variante_id",
        "detalle_devolucion",
        ["variante_id"],
        unique=False,
    )

    # ================= P8 - Pagos ========================================
    op.create_table(
        "pago",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("venta_id", sa.BigInteger(), nullable=False),
        sa.Column("metodo", sa.String(length=12), nullable=False),
        sa.Column("estado", sa.String(length=12), nullable=False),
        # Congelado, igual que detalle_venta.precio_unitario: es lo que se
        # cobro, no lo que la venta valdria hoy.
        sa.Column("monto", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("referencia_externa", sa.String(length=100), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "metodo IN ('PASARELA', 'EFECTIVO', 'TARJETA_POS')", name="metodo"
        ),
        sa.CheckConstraint(
            "estado IN ('INICIADO', 'APROBADO', 'RECHAZADO', 'REEMBOLSADO')",
            name="estado",
        ),
        sa.CheckConstraint("monto >= 0", name="monto_no_negativo"),
        # Solo el pago por pasarela tiene sesion externa.
        sa.CheckConstraint(
            "metodo = 'PASARELA' OR referencia_externa IS NULL",
            name="referencia_solo_pasarela",
        ),
        sa.ForeignKeyConstraint(
            ["venta_id"], ["venta.id"], name="fk_pago_venta_id_venta"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_pago"),
        # Un pago por venta. Un cobro en dos partes seria otro caso de uso.
        sa.UniqueConstraint("venta_id", name="uq_pago_venta_id"),
        # Dos ventas no pueden colgar de la misma sesion de pago: asi es como
        # un reintento mal hecho cobraria dos veces lo mismo.
        sa.UniqueConstraint("referencia_externa", name="uq_pago_referencia_externa"),
    )
    op.create_index("ix_pago_estado", "pago", ["estado"], unique=False)

    op.create_table(
        "transaccion_pasarela",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        # NULLABLE A PROPOSITO: un evento puede llegar sin que sepamos aun a
        # que pago corresponde, o con firma invalida. Esos tambien se guardan:
        # son los que uno quiere mirar cuando algo sale mal.
        sa.Column("pago_id", sa.BigInteger(), nullable=True),
        sa.Column("evento_id", sa.String(length=100), nullable=False),
        sa.Column("tipo_evento", sa.String(length=50), nullable=False),
        sa.Column("firma_valida", sa.Boolean(), nullable=False),
        # El JSON crudo, tal cual llego. Text y no JSONB: no se consulta por
        # adentro, se guarda para poder releerlo como la pasarela lo mando.
        sa.Column("carga_util", sa.Text(), nullable=False),
        sa.Column(
            "recibido_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["pago_id"], ["pago.id"], name="fk_transaccion_pasarela_pago_id_pago"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_transaccion_pasarela"),
        # ACA ESTA TODA LA IDEMPOTENCIA DE CU-28, Y ES ESTA SOLA RESTRICCION.
        # Una notificacion repetida NO descuenta el inventario dos veces: el
        # INSERT falla, el servicio lo trata como "ya visto" y no vuelve a
        # tocar la venta. Resolverlo con logica -leer si existe, y si no
        # insertar- se equivoca justamente cuando dos webhooks llegan a la vez,
        # que es cuando importa. Es D5 y RNF09.
        sa.UniqueConstraint("evento_id", name="uq_transaccion_pasarela_evento_id"),
    )
    op.create_index(
        "ix_transaccion_pasarela_pago_id",
        "transaccion_pasarela",
        ["pago_id"],
        unique=False,
    )
    op.create_index(
        "ix_transaccion_pasarela_recibido_en",
        "transaccion_pasarela",
        ["recibido_en"],
        unique=False,
    )


def downgrade() -> None:
    # Al reves de la creacion: primero lo que referencia, despues lo
    # referenciado.
    op.drop_table("transaccion_pasarela")
    op.drop_table("pago")
    op.drop_table("detalle_devolucion")
    op.drop_table("devolucion")
    op.drop_table("comprobante")
    op.drop_table("detalle_venta")
    op.drop_table("venta")
    op.drop_table("turno_caja")
    op.drop_table("caja")
