# GENERADO por scripts/gen-ops-2-3-ciclo3.py --- NO editar a mano.
# Los nombres y los tipos salen del codigo (ast sobre el backend, regex sobre
# los servicios de Angular) y de information_schema de la base de pruebas, que
# `alembic upgrade head` deja al dia. Es lo que permite defender el diagrama:
# cada operacion se puede abrir en el repositorio.

$ATTRS = @{
  'Promocion' = @(@{n='id';t='SERIAL'}; @{n='nombre';t='VARCHAR(80)'}; @{n='alcance';t='VARCHAR(10)'}; @{n='producto_id';t='BIGINT'}; @{n='categoria_id';t='INTEGER'}; @{n='temporada_id';t='INTEGER'}; @{n='porcentaje';t='NUMERIC(5,2)'}; @{n='desde';t='DATE'}; @{n='hasta';t='DATE'}; @{n='activa';t='BOOLEAN'}; @{n='creado_en';t='TIMESTAMPTZ'}; @{n='actualizado_en';t='TIMESTAMPTZ'})
  'Favorito' = @(@{n='cliente_id';t='BIGINT'}; @{n='producto_id';t='BIGINT'}; @{n='creado_en';t='TIMESTAMPTZ'})
  'Carrito' = @(@{n='id';t='BIGSERIAL'}; @{n='cliente_id';t='BIGINT'}; @{n='creado_en';t='TIMESTAMPTZ'}; @{n='actualizado_en';t='TIMESTAMPTZ'})
  'CarritoDetalle' = @(@{n='id';t='BIGSERIAL'}; @{n='carrito_id';t='BIGINT'}; @{n='variante_id';t='BIGINT'}; @{n='cantidad';t='INTEGER'}; @{n='creado_en';t='TIMESTAMPTZ'}; @{n='actualizado_en';t='TIMESTAMPTZ'})
  'Venta' = @(@{n='id';t='BIGSERIAL'}; @{n='codigo';t='VARCHAR(20)'}; @{n='canal';t='VARCHAR(12)'}; @{n='estado';t='VARCHAR(20)'}; @{n='cliente_id';t='BIGINT'}; @{n='sucursal_id';t='INTEGER'}; @{n='turno_caja_id';t='BIGINT'}; @{n='reserva_id';t='BIGINT'}; @{n='modalidad_entrega';t='VARCHAR(10)'}; @{n='direccion_id';t='BIGINT'}; @{n='metodo_pago';t='VARCHAR(20)'}; @{n='subtotal';t='NUMERIC(10,2)'}; @{n='descuento';t='NUMERIC(10,2)'}; @{n='total';t='NUMERIC(10,2)'}; @{n='creado_en';t='TIMESTAMPTZ'}; @{n='actualizado_en';t='TIMESTAMPTZ'})
  'DetalleVenta' = @(@{n='id';t='BIGSERIAL'}; @{n='venta_id';t='BIGINT'}; @{n='variante_id';t='BIGINT'}; @{n='cantidad';t='INTEGER'}; @{n='precio_unitario';t='NUMERIC(10,2)'}; @{n='descuento_unitario';t='NUMERIC(10,2)'}; @{n='creado_en';t='TIMESTAMPTZ'})
  'Pago' = @(@{n='id';t='BIGSERIAL'}; @{n='venta_id';t='BIGINT'}; @{n='metodo';t='VARCHAR(12)'}; @{n='estado';t='VARCHAR(12)'}; @{n='monto';t='NUMERIC(10,2)'}; @{n='referencia_externa';t='VARCHAR(100)'}; @{n='creado_en';t='TIMESTAMPTZ'}; @{n='actualizado_en';t='TIMESTAMPTZ'})
  'TransaccionPasarela' = @(@{n='id';t='BIGSERIAL'}; @{n='pago_id';t='BIGINT'}; @{n='evento_id';t='VARCHAR(100)'}; @{n='tipo_evento';t='VARCHAR(50)'}; @{n='firma_valida';t='BOOLEAN'}; @{n='carga_util';t='TEXT'}; @{n='recibido_en';t='TIMESTAMPTZ'})
  'Comprobante' = @(@{n='id';t='BIGSERIAL'}; @{n='venta_id';t='BIGINT'}; @{n='tipo';t='VARCHAR(10)'}; @{n='numero';t='VARCHAR(20)'}; @{n='nit_ci';t='VARCHAR(20)'}; @{n='razon_social';t='VARCHAR(120)'}; @{n='emitido_en';t='TIMESTAMPTZ'})
  'Caja' = @(@{n='id';t='SERIAL'}; @{n='sucursal_id';t='INTEGER'}; @{n='nombre';t='VARCHAR(50)'}; @{n='activa';t='BOOLEAN'})
  'TurnoCaja' = @(@{n='id';t='BIGSERIAL'}; @{n='caja_id';t='INTEGER'}; @{n='usuario_id';t='BIGINT'}; @{n='abierto_en';t='TIMESTAMPTZ'}; @{n='cerrado_en';t='TIMESTAMPTZ'}; @{n='monto_apertura';t='NUMERIC(10,2)'}; @{n='monto_cierre';t='NUMERIC(10,2)'}; @{n='monto_esperado';t='NUMERIC(10,2)'})
  'Devolucion' = @(@{n='id';t='BIGSERIAL'}; @{n='venta_id';t='BIGINT'}; @{n='turno_caja_id';t='BIGINT'}; @{n='motivo';t='VARCHAR(200)'}; @{n='monto';t='NUMERIC(10,2)'}; @{n='creado_en';t='TIMESTAMPTZ'})
  'DetalleDevolucion' = @(@{n='id';t='BIGSERIAL'}; @{n='devolucion_id';t='BIGINT'}; @{n='variante_id';t='BIGINT'}; @{n='cantidad';t='INTEGER'}; @{n='creado_en';t='TIMESTAMPTZ'})
  'Recomendacion' = @(@{n='id';t='BIGSERIAL'}; @{n='cliente_id';t='BIGINT'}; @{n='generada_en';t='TIMESTAMPTZ'}; @{n='motor';t='VARCHAR(30)'}; @{n='sugerencias';t='JSONB'}; @{n='creado_en';t='TIMESTAMPTZ'}; @{n='actualizado_en';t='TIMESTAMPTZ'})
  'Abastecimiento' = @(@{n='id';t='BIGSERIAL'}; @{n='proveedor_id';t='BIGINT'}; @{n='variante_id';t='BIGINT'}; @{n='cantidad';t='INTEGER'}; @{n='dias_plazo';t='INTEGER'}; @{n='observacion';t='VARCHAR(200)'}; @{n='estado';t='VARCHAR(20)'}; @{n='cantidad_recibida';t='INTEGER'}; @{n='recibido_en';t='TIMESTAMPTZ'}; @{n='creado_en';t='TIMESTAMPTZ'}; @{n='actualizado_en';t='TIMESTAMPTZ'})
  'Bitacora' = @(@{n='id';t='BIGSERIAL'}; @{n='ocurrido_en';t='TIMESTAMPTZ'}; @{n='usuario_id';t='BIGINT'}; @{n='actor';t='VARCHAR(160)'}; @{n='rol';t='VARCHAR(40)'}; @{n='accion';t='VARCHAR(40)'}; @{n='entidad';t='VARCHAR(60)'}; @{n='entidad_id';t='VARCHAR(60)'}; @{n='metodo';t='VARCHAR(10)'}; @{n='ruta';t='VARCHAR(300)'}; @{n='estado_http';t='INTEGER'}; @{n='exito';t='BOOLEAN'}; @{n='ip';t='VARCHAR(60)'}; @{n='agente';t='VARCHAR(200)'}; @{n='detalle';t='JSONB'})
  'TokenRecuperacion' = @(@{n='id';t='BIGSERIAL'}; @{n='usuario_id';t='BIGINT'}; @{n='hash_token';t='VARCHAR(64)'}; @{n='solicitado_en';t='TIMESTAMPTZ'}; @{n='expira_en';t='TIMESTAMPTZ'}; @{n='usado_en';t='TIMESTAMPTZ'})
  'MedidaCliente' = @(@{n='id';t='BIGSERIAL'}; @{n='cliente_id';t='BIGINT'}; @{n='busto_cm';t='NUMERIC(5,1)'}; @{n='cintura_cm';t='NUMERIC(5,1)'}; @{n='cadera_cm';t='NUMERIC(5,1)'}; @{n='altura_cm';t='NUMERIC(5,1)'}; @{n='creado_en';t='TIMESTAMPTZ'}; @{n='actualizado_en';t='TIMESTAMPTZ'})
}

$OPS = @{
  'Promocion' = @(
    @{n='descuentos_de_variantes'; r='list[Row]'; p=@(@{n='db';t='Session'})},
    @{n='descuentos_de_productos'; r='list[Row]'; p=@(@{n='db';t='Session'})},
    @{n='listar'; r='tuple[int, list[Row]]'; p=@(@{n='db';t='Session'})},
    @{n='obtener'; r='Row | None'; p=@(@{n='db';t='Session'}; @{n='promocion_id';t='int'})},
    @{n='entidad'; r='Promocion | None'; p=@(@{n='db';t='Session'}; @{n='promocion_id';t='int'})},
    @{n='existe_nombre'; r='bool'; p=@(@{n='db';t='Session'}; @{n='nombre';t='str'})},
    @{n='agregar'; r='Promocion'; p=@(@{n='db';t='Session'}; @{n='promocion';t='Promocion'})}
  )
  'Favorito' = @(
    @{n='listar_favoritos'; r='list[Producto]'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'})},
    @{n='ids_de_favoritos'; r='list[int]'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'})},
    @{n='es_favorito'; r='bool'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'}; @{n='producto_id';t='int'})},
    @{n='agregar_favorito'; r='None'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'}; @{n='producto_id';t='int'})},
    @{n='quitar_favorito'; r='None'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'}; @{n='producto_id';t='int'})},
    @{n='contar_favoritos'; r='int'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'})}
  )
  'Carrito' = @(
    @{n='obtener_carrito'; r='Carrito | None'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'})},
    @{n='agregar_carrito'; r='Carrito'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'})},
    @{n='vaciar'; r='int'; p=@(@{n='db';t='Session'}; @{n='carrito_id';t='int'})}
  )
  'CarritoDetalle' = @(
    @{n='lineas_resueltas'; r='list[Row]'; p=@(@{n='db';t='Session'}; @{n='carrito_id';t='int'})},
    @{n='obtener_linea'; r='CarritoDetalle | None'; p=@(@{n='db';t='Session'}; @{n='carrito_id';t='int'}; @{n='variante_id';t='int'})},
    @{n='agregar_linea'; r='CarritoDetalle'; p=@(@{n='db';t='Session'})},
    @{n='eliminar_linea'; r='None'; p=@(@{n='db';t='Session'}; @{n='linea';t='CarritoDetalle'})},
    @{n='stock_de_variantes'; r='dict[int, int]'; p=@(@{n='db';t='Session'}; @{n='variante_ids';t='list[int]'})},
    @{n='imagen_principal'; r='dict[int, str]'; p=@(@{n='db';t='Session'}; @{n='producto_ids';t='list[int]'})}
  )
  'Venta' = @(
    @{n='obtener_pedido'; r='Row | None'; p=@(@{n='db';t='Session'})},
    @{n='obtener_venta_entidad'; r='Venta | None'; p=@(@{n='db';t='Session'})},
    @{n='agregar_venta'; r='Venta'; p=@(@{n='db';t='Session'})},
    @{n='existe_codigo'; r='bool'; p=@(@{n='db';t='Session'}; @{n='codigo';t='str'})},
    @{n='pedido_pendiente_de'; r='Venta | None'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'})},
    @{n='listar_pendientes_vencidos'; r='list[Venta]'; p=@(@{n='db';t='Session'})},
    @{n='bloquear_cliente'; r='None'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'})},
    @{n='stock_por_sucursal'; r='dict[int, dict[int, int]]'; p=@(@{n='db';t='Session'}; @{n='variante_ids';t='list[int]'})},
    @{n='agregar_venta_presencial'; r='Venta'; p=@(@{n='db';t='Session'})},
    @{n='venta_de_sucursal'; r='Venta | None'; p=@(@{n='db';t='Session'})},
    @{n='pedidos_del_cliente'; r='list[tuple]'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'}; @{n='limite';t='int'})}
  )
  'DetalleVenta' = @(
    @{n='agregar_detalle'; r='DetalleVenta'; p=@(@{n='db';t='Session'})},
    @{n='lineas_de_pedido'; r='list[Row]'; p=@(@{n='db';t='Session'}; @{n='venta_id';t='int'})},
    @{n='detalles_de'; r='list[DetalleVenta]'; p=@(@{n='db';t='Session'}; @{n='venta_id';t='int'})},
    @{n='lineas_llevadas'; r='list[Row]'; p=@(@{n='db';t='Session'})}
  )
  'Pago' = @(
    @{n='iniciar_cobro'; r='tuple[str, str]'; p=@(@{n='db';t='Session'})},
    @{n='confirmar_pago'; r='str'; p=@(@{n='db';t='Session'})},
    @{n='cobra_de_verdad'; r='bool'; p=@()}
  )
  'TransaccionPasarela' = @(
    @{n='fabricar_notificacion_simulada'; r='tuple[bytes, str | None]'; p=@()}
  )
  'Comprobante' = @(
    @{n='obtener_comprobante'; r='Comprobante | None'; p=@(@{n='db';t='Session'}; @{n='venta_id';t='int'})},
    @{n='agregar_comprobante'; r='Comprobante'; p=@(@{n='db';t='Session'})},
    @{n='listar_compras'; r='list[Row]'; p=@(@{n='db';t='Session'})},
    @{n='contar_compras'; r='int'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'})}
  )
  'Caja' = @(
    @{n='caja_por_id'; r='Caja | None'; p=@(@{n='db';t='Session'}; @{n='caja_id';t='int'})},
    @{n='cajas_de_sucursal'; r='list[Caja]'; p=@(@{n='db';t='Session'}; @{n='sucursal_id';t='int'})},
    @{n='bloquear_caja'; r='Caja | None'; p=@(@{n='db';t='Session'}; @{n='caja_id';t='int'})},
    @{n='sucursal_activa'; r='Sucursal | None'; p=@(@{n='db';t='Session'}; @{n='sucursal_id';t='int'})}
  )
  'TurnoCaja' = @(
    @{n='turno_abierto_de_caja'; r='TurnoCaja | None'; p=@(@{n='db';t='Session'}; @{n='caja_id';t='int'})},
    @{n='turno_abierto_de_usuario'; r='TurnoCaja | None'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'})},
    @{n='turno_por_id'; r='TurnoCaja | None'; p=@(@{n='db';t='Session'}; @{n='turno_id';t='int'})},
    @{n='abrir'; r='TurnoCaja'; p=@(@{n='db';t='Session'})},
    @{n='efectivo_cobrado'; r='Decimal'; p=@(@{n='db';t='Session'}; @{n='turno_id';t='int'})},
    @{n='devoluciones_del_turno'; r='Decimal'; p=@(@{n='db';t='Session'}; @{n='turno_id';t='int'})},
    @{n='ventas_del_turno'; r='list[tuple[str, int, Decimal]]'; p=@(@{n='db';t='Session'}; @{n='turno_id';t='int'})}
  )
  'Devolucion' = @(
    @{n='venta_devolvible'; r='Venta | None'; p=@(@{n='db';t='Session'})},
    @{n='ya_devuelto'; r='dict[int, int]'; p=@(@{n='db';t='Session'}; @{n='venta_id';t='int'})},
    @{n='bloquear_venta'; r='Venta | None'; p=@(@{n='db';t='Session'}; @{n='venta_id';t='int'})},
    @{n='agregar_devolucion'; r='Devolucion'; p=@(@{n='db';t='Session'})}
  )
  'DetalleDevolucion' = @(
    @{n='lineas_vendidas'; r='list[Row]'; p=@(@{n='db';t='Session'}; @{n='venta_id';t='int'})},
    @{n='agregar_detalle'; r='DetalleDevolucion'; p=@(@{n='db';t='Session'})}
  )
  'Recomendacion' = @(
    @{n='guardada'; r='Recomendacion | None'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'})},
    @{n='guardar'; r='Recomendacion'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'}; @{n='motor';t='str'}; @{n='sugerencias';t='list[dict]'})},
    @{n='invalidar'; r='None'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'})},
    @{n='candidatas'; r='list[tuple[int, str, str, Decimal | None, int]]'; p=@(@{n='db';t='Session'})},
    @{n='categorias_preferidas'; r='list[tuple[int, str]]'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'})},
    @{n='prendas_conocidas'; r='list[str]'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'}; @{n='limite';t='int'})}
  )
  'Abastecimiento' = @(
    @{n='mios'; r='list[tuple]'; p=@(@{n='db';t='Session'}; @{n='proveedor_id';t='int'})},
    @{n='variantes_del_proveedor'; r='list[tuple]'; p=@(@{n='db';t='Session'}; @{n='proveedor_id';t='int'})},
    @{n='crear'; r='Abastecimiento'; p=@(@{n='db';t='Session'})},
    @{n='vigente'; r='Abastecimiento | None'; p=@(@{n='db';t='Session'}; @{n='proveedor_id';t='int'}; @{n='variante_id';t='int'})},
    @{n='por_id'; r='Abastecimiento | None'; p=@(@{n='db';t='Session'}; @{n='anuncio_id';t='int'})},
    @{n='pendientes_de_recibir'; r='list[tuple]'; p=@(@{n='db';t='Session'})},
    @{n='para_recibir'; r='dict[int, Abastecimiento]'; p=@(@{n='db';t='Session'}; @{n='anuncio_ids';t='list[int]'})}
  )
  'Bitacora' = @(
    @{n='agregar'; r='AsientoBitacora'; p=@(@{n='db';t='Session'})},
    @{n='listar'; r='list[tuple]'; p=@(@{n='db';t='Session'})},
    @{n='contar'; r='int'; p=@(@{n='db';t='Session'})},
    @{n='acciones'; r='list[str]'; p=@(@{n='db';t='Session'})},
    @{n='roles'; r='list[str]'; p=@(@{n='db';t='Session'})},
    @{n='entidades'; r='list[str]'; p=@(@{n='db';t='Session'})}
  )
  'TokenRecuperacion' = @(
    @{n='agregar_token_recuperacion'; r='TokenRecuperacion'; p=@(@{n='db';t='Session'})},
    @{n='canjear_token_de_recuperacion'; r='int | None'; p=@(@{n='db';t='Session'}; @{n='hash_token';t='str'})},
    @{n='invalidar_tokens_de_recuperacion'; r='int'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'})}
  )
  'MedidaCliente' = @(
    @{n='medidas_de'; r='MedidaCliente | None'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'})},
    @{n='guardar_medidas'; r='MedidaCliente'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'}; @{n='busto_cm';t='Decimal'}; @{n='cintura_cm';t='Decimal'}; @{n='cadera_cm';t='Decimal'}; @{n='altura_cm';t='Decimal | None'})},
    @{n='tabla_de_producto'; r='list[tuple]'; p=@(@{n='db';t='Session'}; @{n='producto_id';t='int'})}
  )
}

$CTRL = @{
  'GestorPromociones' = @(
    @{n='descuentos_por_variante'; r='dict[int, Descuento]'; p=@(@{n='db';t='Session'}; @{n='precios';t='dict[int, Decimal]'})},
    @{n='descuentos_por_producto'; r='dict[int, Descuento]'; p=@(@{n='db';t='Session'}; @{n='precios';t='dict[int, Decimal]'})},
    @{n='a_contrato'; r='DescuentoOut | None'; p=@(@{n='descuento';t='Descuento | None'})},
    @{n='listar'; r='tuple[int, list[PromocionOut]]'; p=@(@{n='db';t='Session'})},
    @{n='obtener'; r='PromocionOut'; p=@(@{n='db';t='Session'}; @{n='promocion_id';t='int'})},
    @{n='crear'; r='PromocionOut'; p=@(@{n='db';t='Session'}; @{n='datos';t='PromocionCrearIn'})},
    @{n='editar'; r='PromocionOut'; p=@(@{n='db';t='Session'}; @{n='promocion_id';t='int'}; @{n='datos';t='PromocionEditarIn'})},
    @{n='cambiar_estado'; r='PromocionOut'; p=@(@{n='db';t='Session'}; @{n='promocion_id';t='int'}; @{n='datos';t='CambioEstadoIn'})}
  )
  'GestorCarrito' = @(
    @{n='ver_carrito'; r='CarritoOut'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'})},
    @{n='agregar'; r='CarritoOut'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='datos';t='AgregarAlCarritoIn'})},
    @{n='cambiar_cantidad'; r='CarritoOut'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='variante_id';t='int'}; @{n='datos';t='CambiarCantidadIn'})},
    @{n='quitar'; r='CarritoOut'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='variante_id';t='int'})},
    @{n='vaciar'; r='CarritoOut'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'})}
  )
  'GestorPedidos' = @(
    @{n='opciones_de_pedido'; r='OpcionesDePedidoOut'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'})},
    @{n='crear_pedido'; r='CrearPedidoOut'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='datos';t='CrearPedidoIn'})},
    @{n='ver_pedido'; r='PedidoOut'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='codigo';t='str'})},
    @{n='cancelar_pedido'; r='PedidoOut'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='codigo';t='str'})},
    @{n='expirar_pedidos_vencidos'; r='ExpiracionDePedidosOut'; p=@(@{n='db';t='Session'})}
  )
  'GestorPagos' = @(
    @{n='iniciar_cobro'; r='tuple[str, str]'; p=@(@{n='db';t='Session'})},
    @{n='confirmar_pago'; r='str'; p=@(@{n='db';t='Session'})},
    @{n='cobra_de_verdad'; r='bool'; p=@()},
    @{n='fabricar_notificacion_simulada'; r='tuple[bytes, str | None]'; p=@()}
  )
  'GestorHistorial' = @(
    @{n='listar_compras'; r='PaginaCompras'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'})},
    @{n='asegurar_comprobante'; r='Comprobante'; p=@(@{n='db';t='Session'}; @{n='venta';t='Venta'})},
    @{n='comprobante_en_pdf'; r='tuple[str, bytes]'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='codigo';t='str'})}
  )
  'GestorCaja' = @(
    @{n='cajas_disponibles'; r='list[tuple]'; p=@(@{n='db';t='Session'}; @{n='sucursal_id';t='int'})},
    @{n='mi_turno'; r='EstadoDelTurno | None'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'})},
    @{n='abrir'; r='EstadoDelTurno'; p=@(@{n='db';t='Session'})},
    @{n='cerrar'; r='EstadoDelTurno'; p=@(@{n='db';t='Session'})}
  )
  'GestorMostrador' = @(
    @{n='mostrador_de'; r='Mostrador'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'})},
    @{n='buscar_prendas'; r='tuple[int, list[PrendaEnMostradorOut]]'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'})},
    @{n='reservas_por_cobrar'; r='list[ReservaPorCobrarOut]'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'})},
    @{n='ver_reserva'; r='ReservaPorCobrarOut'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='reserva_id';t='int'})},
    @{n='registrar_venta'; r='VentaPresencialOut'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='datos';t='VentaPresencialIn'})},
    @{n='ver_venta'; r='VentaPresencialOut'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='codigo';t='str'})},
    @{n='comprobante_en_pdf'; r='tuple[str, bytes]'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='codigo';t='str'})}
  )
  'GestorDevoluciones' = @(
    @{n='buscar_venta'; r='VentaDevolvibleOut'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='codigo';t='str'})},
    @{n='registrar'; r='DevolucionOut'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='datos';t='DevolucionIn'})}
  )
  'GestorRecomendaciones' = @(
    @{n='recomendaciones'; r='Recomendaciones | None'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'})},
    @{n='invalidar'; r='None'; p=@(@{n='db';t='Session'}; @{n='cliente_id';t='int'})}
  )
  'GestorTablero' = @(
    @{n='consultar'; r='TableroOut'; p=@(@{n='db';t='Session'})}
  )
  'GestorReportes' = @(
    @{n='opciones_de'; r='list[dict]'; p=@(@{n='db';t='Session'}; @{n='filtro';t='Filtro'})},
    @{n='generar'; r='Tabla'; p=@(@{n='db';t='Session'})},
    @{n='catalogo_para_el_interprete'; r='list'; p=@(@{n='db';t='Session'}; @{n='es_admin';t='bool'})}
  )
  'GestorAbastecimiento' = @(
    @{n='mis_anuncios'; r='list[Anuncio]'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'})},
    @{n='mis_variantes'; r='list[dict]'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'})},
    @{n='anunciar'; r='Anuncio'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'})},
    @{n='cancelar'; r='None'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='anuncio_id';t='int'})},
    @{n='avisos_de_ingreso'; r='list[AvisoDeIngreso]'; p=@(@{n='db';t='Session'})},
    @{n='recibir'; r='dict[int, int]'; p=@(@{n='db';t='Session'}; @{n='recepciones';t='dict[int, int]'})},
    @{n='variante_del_aviso'; r='int | None'; p=@(@{n='db';t='Session'}; @{n='anuncio_id';t='int'})}
  )
  'GestorBitacora' = @(
    @{n='registrar'; r='None'; p=@(@{n='db';t='Session'})},
    @{n='listar'; r='Pagina'; p=@(@{n='db';t='Session'})},
    @{n='opciones'; r='dict[str, list[str]]'; p=@(@{n='db';t='Session'})}
  )
  'GestorRecuperacion' = @(
    @{n='solicitar_recuperacion'; r='None'; p=@(@{n='db';t='Session'}; @{n='datos';t='RecuperacionSolicitudIn'})},
    @{n='confirmar_recuperacion'; r='None'; p=@(@{n='db';t='Session'}; @{n='datos';t='RecuperacionConfirmarIn'})}
  )
  'GestorFavoritos' = @(
    @{n='listar_favoritos'; r='PaginaFavoritos'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'})},
    @{n='ids_de_favoritos'; r='list[int]'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'})},
    @{n='marcar_favorito'; r='None'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='producto_id';t='int'})},
    @{n='desmarcar_favorito'; r='None'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='producto_id';t='int'})}
  )
  'GestorVestidor' = @(
    @{n='estado'; r='EstadoDelProbador'; p=@()},
    @{n='probar'; r='tuple[bytes, str, str]'; p=@(@{n='db';t='Session'})},
    @{n='ajuste_de_producto'; r='AjusteDeProducto'; p=@(@{n='db';t='Session'}; @{n='producto_id';t='int'}; @{n='usuario_id';t='int'})}
  )
  'GestorAsistente' = @(
    @{n='esta_disponible'; r='bool'; p=@()},
    @{n='armar_contexto'; r='Contexto'; p=@(@{n='db';t='Session'}; @{n='cliente';t=''}; @{n='nombre';t='str'})},
    @{n='responder'; r='RespuestaAlCliente'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'})},
    @{n='esta_disponible'; r='bool'; p=@()},
    @{n='responder'; r='Respuesta'; p=@(@{n='pregunta';t='str'}; @{n='contexto';t='Contexto'}; @{n='historial';t='list[tuple[str, str]]'})}
  )
  'GestorCatalogoProveedor' = @(
    @{n='listas_del_formulario'; r='ListasDelFormularioOut'; p=@(@{n='db';t='Session'})},
    @{n='listar_mis_productos'; r='PaginaProductos'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'})},
    @{n='obtener_mi_producto'; r='ProductoOut'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='producto_id';t='int'})},
    @{n='registrar_mi_producto'; r='ProductoOut'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='datos';t='MiProductoCrearIn'})},
    @{n='editar_mi_producto'; r='ProductoOut'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='producto_id';t='int'}; @{n='datos';t='MiProductoEditarIn'})},
    @{n='cambiar_estado_de_mi_producto'; r='ProductoOut'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='producto_id';t='int'}; @{n='activo';t='bool'})},
    @{n='generar_variantes_de_mi_producto'; r='GenerarVariantesOut'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'}; @{n='producto_id';t='int'}; @{n='datos';t='GenerarVariantesIn'})}
  )
  'GestorReportePorVoz' = @(
    @{n='esta_disponible'; r='bool'; p=@()},
    @{n='interpretar'; r='Pedido | None'; p=@(@{n='texto';t='str'}; @{n='reportes';t='list[ReporteConocido]'}; @{n='hoy';t='date'})},
    @{n='obtener_proveedor'; r='ProveedorInterprete'; p=@()}
  )
}

$FRONT = @{
  'PantallaPromociones' = @(
    @{n='listar'; r='Observable<PaginaPromociones>'; p=@(@{n='pagina = 1';t=''}; @{n='tamano = 20';t=''}; @{n='alcance';t='Alcance | null'}; @{n='soloVigentes = false';t=''})},
    @{n='crear'; r='Observable<Promocion>'; p=@(@{n='datos';t='CrearPromocion'})},
    @{n='editar'; r='Observable<Promocion>'; p=@(@{n='id';t='number'}; @{n='datos';t='EditarPromocion'})},
    @{n='cambiarEstado'; r='Observable<Promocion>'; p=@(@{n='id';t='number'}; @{n='activa';t='boolean'})},
    @{n='listar_promociones'; r='None'; p=@(@{n='db';t='DbSession'}; @{n='pagina';t='Annotated[int, Query(ge=1)]'}; @{n='tamano';t='Annotated[int, Query(ge=1, le=100)]'}; @{n='alcance';t='Alcance | None'}; @{n='solo_vigentes';t='bool'})},
    @{n='crear_promocion'; r='None'; p=@(@{n='datos';t='PromocionCrearIn'}; @{n='db';t='DbSession'})},
    @{n='obtener_promocion'; r='None'; p=@(@{n='promocion_id';t='Annotated[int, Path(ge=1)]'}; @{n='db';t='DbSession'})},
    @{n='editar_promocion'; r='None'; p=@(@{n='promocion_id';t='Annotated[int, Path(ge=1)]'}; @{n='datos';t='PromocionEditarIn'}; @{n='db';t='DbSession'})},
    @{n='cambiar_estado'; r='None'; p=@(@{n='promocion_id';t='Annotated[int, Path(ge=1)]'}; @{n='datos';t='CambioEstadoIn'}; @{n='db';t='DbSession'})}
  )
  'PantallaCarrito' = @(
    @{n='olvidar'; r='void'; p=@()},
    @{n='ver'; r='Observable<Carrito>'; p=@()},
    @{n='agregar'; r='Observable<Carrito>'; p=@(@{n='datos';t='AgregarAlCarrito'})},
    @{n='cambiarCantidad'; r='Observable<Carrito>'; p=@(@{n='varianteId';t='number'}; @{n='cantidad';t='number'})},
    @{n='quitar'; r='Observable<Carrito>'; p=@(@{n='varianteId';t='number'})},
    @{n='vaciar'; r='Observable<Carrito>'; p=@()},
    @{n='ver_carrito'; r='CarritoOut'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='agregar'; r='CarritoOut'; p=@(@{n='datos';t='AgregarAlCarritoIn'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='cambiar_cantidad'; r='CarritoOut'; p=@(@{n='variante_id';t='Annotated[int, Path(ge=1)]'}; @{n='datos';t='CambiarCantidadIn'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='quitar'; r='CarritoOut'; p=@(@{n='variante_id';t='Annotated[int, Path(ge=1)]'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='vaciar'; r='CarritoOut'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})}
  )
  'PantallaCheckout' = @(
    @{n='opciones'; r='Observable<OpcionesDePedido>'; p=@()},
    @{n='crear'; r='Observable<CrearPedidoRespuesta>'; p=@(@{n='datos';t='CrearPedidoIn'})},
    @{n='ver'; r='Observable<Pedido>'; p=@(@{n='codigo';t='string'})},
    @{n='cancelar'; r='Observable<Pedido>'; p=@(@{n='codigo';t='string'})},
    @{n='opciones_de_pedido'; r='OpcionesDePedidoOut'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='crear_pedido'; r='CrearPedidoOut'; p=@(@{n='datos';t='CrearPedidoIn'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='ver_pedido'; r='PedidoOut'; p=@(@{n='codigo';t='Codigo'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='cancelar_pedido'; r='PedidoOut'; p=@(@{n='codigo';t='Codigo'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='expirar_pedidos_vencidos'; r='ExpiracionDePedidosOut'; p=@(@{n='db';t='DbSession'})}
  )
  'WebhookPasarela' = @(
    @{n='simular_notificacion'; r='RespuestaWebhookOut'; p=@(@{n='datos';t='SimularPagoIn'}; @{n='db';t='DbSession'})},
    @{n='configuracion'; r='dict'; p=@()}
  )
  'PantallaCompras' = @(
    @{n='listar'; r='Observable<PaginaCompras>'; p=@(@{n='pagina = 1';t=''}; @{n='tamano = 10';t=''})},
    @{n='comprobante'; r='Observable<Blob>'; p=@(@{n='codigo';t='string'})},
    @{n='listar_compras'; r='PaginaCompras'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'}; @{n='pagina';t='Annotated[int, Query(ge=1)]'}; @{n='tamano';t='Annotated[int, Query(ge=1, le=50)]'})},
    @{n='descargar_comprobante'; r='Response'; p=@(@{n='codigo';t='str'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})}
  )
  'PantallaTurno' = @(
    @{n='cajas'; r='Observable<Caja[]>'; p=@()},
    @{n='miTurno'; r='Observable<Turno | null>'; p=@()},
    @{n='abrir'; r='Observable<Turno>'; p=@(@{n='datos';t='AbrirTurno'})},
    @{n='cerrar'; r='Observable<Turno>'; p=@(@{n='turnoId';t='number'}; @{n='datos';t='CerrarTurno'})},
    @{n='cajas_de_mi_sucursal'; r='None'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='mi_turno_abierto'; r='None'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='abrir_turno'; r='None'; p=@(@{n='datos';t='AbrirTurnoIn'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='cerrar_turno'; r='None'; p=@(@{n='turno_id';t='Annotated[int, Path(ge=1)]'}; @{n='datos';t='CerrarTurnoIn'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})}
  )
  'PantallaVenta' = @(
    @{n='prendas'; r='Observable<PaginaDePrendas>'; p=@(@{n='busqueda';t='string'}; @{n='pagina = 1';t=''}; @{n='tamano = 20';t=''})},
    @{n='reservasPorCobrar'; r='Observable<ReservaPorCobrar[]>'; p=@()},
    @{n='cobrar'; r='Observable<Ticket>'; p=@(@{n='datos';t='VentaPresencial'})},
    @{n='comprobante'; r='Observable<Blob>'; p=@(@{n='codigo';t='string'})},
    @{n='prendas_del_mostrador'; r='None'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'}; @{n='busqueda';t='Annotated[str | None, Query(max_length=80)]'}; @{n='pagina';t='Annotated[int, Query(ge=1)]'}; @{n='tamano';t='Annotated[int, Query(ge=1, le=100)]'})},
    @{n='reservas_por_cobrar'; r='None'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='ver_reserva'; r='None'; p=@(@{n='reserva_id';t='Annotated[int, Path(ge=1)]'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='registrar_venta'; r='None'; p=@(@{n='datos';t='VentaPresencialIn'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='ver_venta'; r='None'; p=@(@{n='codigo';t='Annotated[str, Path(min_length=3, max_length=20)]'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='comprobante'; r='None'; p=@(@{n='codigo';t='Annotated[str, Path(min_length=3, max_length=20)]'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})}
  )
  'PantallaDevolucion' = @(
    @{n='buscarVenta'; r='Observable<VentaDevolvible>'; p=@(@{n='codigo';t='string'})},
    @{n='registrar'; r='Observable<ComprobanteDevolucion>'; p=@(@{n='datos';t='Devolucion'})},
    @{n='venta_a_devolver'; r='None'; p=@(@{n='codigo';t='Annotated[str, Path(min_length=3, max_length=20)]'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='registrar_devolucion'; r='None'; p=@(@{n='datos';t='DevolucionIn'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})}
  )
  'PantallaParaVos' = @(
    @{n='mis_recomendaciones'; r='None'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'}; @{n='forzar';t='Annotated[bool, Query(description=Vuelve a generar aunque la guardada siga vigente. Es para la demostración: sin esto, mostrar el efecto de cambiar las preferencias obligaría a esperar doce horas.)]'})}
  )
  'PantallaTablero' = @(
    @{n='consultar'; r='Observable<Tablero>'; p=@(@{n='consulta';t='ConsultaTablero'})},
    @{n='consultar_tablero'; r='TableroOut'; p=@(@{n='db';t='DbSession'}; @{n='desde';t='Annotated[date | None, Query(description=Primer día del período. Por omisión, 30 días atrás.)]'}; @{n='hasta';t='Annotated[date | None, Query(description=Último día, incluido. Por omisión, hoy.)]'}; @{n='sucursal_id';t='Annotated[int | None, Query(description=Acota a una sucursal. Sin esto, la red entera.)]'})}
  )
  'PantallaReportes' = @(
    @{n='catalogo'; r='Observable<ReporteDisponible[]>'; p=@()},
    @{n='descargar'; r='Observable<'; p=@(@{n='tipo';t='string'}; @{n='formato';t='pdf | xlsx'}; @{n='filtros';t='FiltrosDeReporte'})},
    @{n='hayVoz'; r='Observable<boolean>'; p=@()},
    @{n='interpretarVoz'; r='Observable<PedidoEntendido>'; p=@(@{n='texto';t='string'})},
    @{n='catalogo_de_reportes'; r='None'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='descargar'; r='None'; p=@(@{n='tipo';t='Annotated[str, Path(pattern=^[a-z]+$)]'}; @{n='formato';t='Annotated[str, Path(pattern=^(pdf|xlsx)$)]'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'}; @{n='desde';t='Annotated[date | None, Query()]'}; @{n='hasta';t='Annotated[date | None, Query()]'}; @{n='sucursal_id';t='Annotated[int | None, Query(ge=1)]'}; @{n='canal';t='Annotated[str | None, Query()]'}; @{n='estado';t='Annotated[str | None, Query()]'}; @{n='metodo_pago';t='Annotated[str | None, Query()]'}; @{n='tipo_movimiento';t='Annotated[str | None, Query(alias=tipo)]'}; @{n='bajo_minimo';t='Annotated[str | None, Query()]'}; @{n='temporada_id';t='Annotated[int | None, Query(ge=1)]'}; @{n='proveedor_id';t='Annotated[int | None, Query(ge=1)]'})}
  )
  'PantallaAbastecimiento' = @(
    @{n='variantes'; r='Observable<VarianteAnunciable[]>'; p=@()},
    @{n='mios'; r='Observable<Anuncio[]>'; p=@(@{n='incluirCancelados = false';t=''})},
    @{n='informar'; r='Observable<Anuncio>'; p=@(@{n='datos';t='AnunciarIn'})},
    @{n='cancelar'; r='Observable<void>'; p=@(@{n='id';t='number'})},
    @{n='variantes_que_puedo_anunciar'; r='None'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='mis_avisos'; r='None'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'}; @{n='incluir_cancelados';t='Annotated[bool, Query()]'})},
    @{n='informar'; r='None'; p=@(@{n='datos';t='AnunciarIn'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='cancelar'; r='None'; p=@(@{n='anuncio_id';t='Annotated[int, Path(ge=1)]'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})}
  )
  'PantallaBitacora' = @(
    @{n='consultar'; r='PaginaBitacoraOut'; p=@(@{n='db';t='DbSession'}; @{n='desde';t='Annotated[date | None, Query(description=Desde este día, inclusive.)]'}; @{n='hasta';t='Annotated[date | None, Query(description=Hasta este día, inclusive.)]'}; @{n='usuario_id';t='Annotated[int | None, Query()]'}; @{n='rol';t='Annotated[str | None, Query(description=Un rol, o «EMPLEADOS» para los tres internos.)]'}; @{n='accion';t='Annotated[str | None, Query()]'}; @{n='entidad';t='Annotated[str | None, Query()]'}; @{n='exito';t='Annotated[bool | None, Query(description=Solo las que salieron bien, o solo las que no.)]'}; @{n='busqueda';t='Annotated[str | None, Query(description=Busca en el correo y en la ruta.)]'}; @{n='pagina';t='Annotated[int, Query(ge=1)]'}; @{n='tamano';t='Annotated[int, Query(ge=1, le=service.TAMANO_MAXIMO)]'})},
    @{n='opciones'; r='OpcionesBitacoraOut'; p=@(@{n='db';t='DbSession'})}
  )
  'PantallaFavoritos' = @(
    @{n='listar_favoritos'; r='PaginaFavoritos'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'}; @{n='pagina';t='Annotated[int, Query(ge=1)]'}; @{n='tamano';t='Annotated[int, Query(ge=1, le=48)]'})},
    @{n='ids_de_favoritos'; r='list[int]'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='marcar_favorito'; r='Response'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'}; @{n='producto_id';t='Annotated[int, Path(ge=1)]'})},
    @{n='desmarcar_favorito'; r='Response'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'}; @{n='producto_id';t='Annotated[int, Path(ge=1)]'})}
  )
  'PantallaVestidor' = @(
    @{n='ver_mis_medidas'; r='None'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='guardar_mis_medidas'; r='None'; p=@(@{n='datos';t='MedidasEntrada'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='ajuste_del_producto'; r='None'; p=@(@{n='producto_id';t='Annotated[int, Path(ge=1)]'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})}
  )
  'PantallaMisProductos' = @(
    @{n='listas_del_formulario'; r='ListasDelFormularioOut'; p=@(@{n='db';t='DbSession'})},
    @{n='listar_mis_productos'; r='PaginaProductos'; p=@(@{n='usuario';t='Usuario'}; @{n='db';t='DbSession'}; @{n='pagina';t='Annotated[int, Query(ge=1)]'}; @{n='tamano';t='Annotated[int, Query(ge=1, le=100)]'}; @{n='busqueda';t='Annotated[str | None, Query(max_length=120)]'}; @{n='categoria_id';t='Annotated[int | None, Query()]'}; @{n='temporada_id';t='Annotated[int | None, Query()]'}; @{n='coleccion_id';t='Annotated[int | None, Query()]'}; @{n='activo';t='Annotated[bool | None, Query()]'})},
    @{n='registrar_mi_producto'; r='ProductoOut'; p=@(@{n='datos';t='MiProductoCrearIn'}; @{n='usuario';t='Usuario'}; @{n='db';t='DbSession'})},
    @{n='obtener_mi_producto'; r='ProductoOut'; p=@(@{n='producto_id';t='int'}; @{n='usuario';t='Usuario'}; @{n='db';t='DbSession'})},
    @{n='editar_mi_producto'; r='ProductoOut'; p=@(@{n='producto_id';t='int'}; @{n='datos';t='MiProductoEditarIn'}; @{n='usuario';t='Usuario'}; @{n='db';t='DbSession'})},
    @{n='retirar_mi_producto'; r='ProductoOut'; p=@(@{n='producto_id';t='int'}; @{n='datos';t='CambioEstadoIn'}; @{n='usuario';t='Usuario'}; @{n='db';t='DbSession'})},
    @{n='generar_variantes'; r='GenerarVariantesOut'; p=@(@{n='producto_id';t='int'}; @{n='datos';t='GenerarVariantesIn'}; @{n='usuario';t='Usuario'}; @{n='db';t='DbSession'})}
  )
  'PantallaReportePorVoz' = @(
    @{n='hay_pedido_por_voz'; r='None'; p=@()},
    @{n='pedir_por_voz'; r='None'; p=@(@{n='datos';t='PedidoPorVozIn'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})}
  )
  'PantallaRecuperacion' = @(
    @{n='solicitar_recuperacion'; r='RecuperacionAceptadaOut'; p=@(@{n='datos';t='RecuperacionSolicitudIn'}; @{n='db';t='DbSession'})},
    @{n='confirmar_recuperacion'; r='None'; p=@(@{n='datos';t='RecuperacionConfirmarIn'}; @{n='db';t='DbSession'})}
  )
  'CanalDeAviso' = @(
    @{n='obtener_proveedor'; r='ProveedorCorreo'; p=@()},
    @{n='enviar'; r='None'; p=@(@{n='mensaje';t='Mensaje'})}
  )
  'PantallaAsistente' = @(
    @{n='agregar'; r='void'; p=@(@{n='turno';t='Turno'})},
    @{n='limpiar'; r='void'; p=@()},
    @{n='disponible'; r='Observable<EstadoAsistente>'; p=@()},
    @{n='preguntar'; r='Observable<RespuestaAsistente>'; p=@(@{n='pregunta';t='string'}; @{n='historial';t='Turno[]'})},
    @{n='hay_asistente'; r='DisponibleOut'; p=@()},
    @{n='preguntar'; r='RespuestaOut'; p=@(@{n='datos';t='PreguntaIn'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})}
  )
}
