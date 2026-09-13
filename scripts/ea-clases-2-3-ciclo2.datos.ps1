# GENERADO por scripts/gen-ops-2-3.py --- NO editar a mano.
# Los nombres y los tipos salen del codigo (ast sobre el backend, regex sobre los
# servicios de Angular) y de information_schema de la base construida con las
# migraciones. Es lo que permite defender el diagrama: cada operacion se puede
# abrir en el repositorio.

$ATTRS = @{
  'Producto' = @(@{n='id';t='BIGSERIAL'}; @{n='codigo';t='VARCHAR(30)'}; @{n='nombre';t='VARCHAR(120)'}; @{n='descripcion';t='VARCHAR(500)'}; @{n='categoria_id';t='INTEGER'}; @{n='proveedor_id';t='BIGINT'}; @{n='temporada_id';t='INTEGER'}; @{n='coleccion_id';t='INTEGER'}; @{n='precio_base';t='NUMERIC(10,2)'}; @{n='activo';t='BOOLEAN'}; @{n='creado_en';t='TIMESTAMPTZ'}; @{n='actualizado_en';t='TIMESTAMPTZ'})
  'VarianteProducto' = @(@{n='id';t='BIGSERIAL'}; @{n='producto_id';t='BIGINT'}; @{n='talla_id';t='INTEGER'}; @{n='color_id';t='INTEGER'}; @{n='sku';t='VARCHAR(40)'}; @{n='precio';t='NUMERIC(10,2)'}; @{n='activa';t='BOOLEAN'}; @{n='creado_en';t='TIMESTAMPTZ'}; @{n='actualizado_en';t='TIMESTAMPTZ'})
  'ImagenProducto' = @(@{n='id';t='BIGSERIAL'}; @{n='producto_id';t='BIGINT'}; @{n='variante_id';t='BIGINT'}; @{n='ruta';t='VARCHAR(255)'}; @{n='es_principal';t='BOOLEAN'}; @{n='es_transparente';t='BOOLEAN'}; @{n='orden';t='SMALLINT'}; @{n='creado_en';t='TIMESTAMPTZ'}; @{n='actualizado_en';t='TIMESTAMPTZ'})
  'Existencia' = @(@{n='id';t='BIGSERIAL'}; @{n='variante_id';t='BIGINT'}; @{n='sucursal_id';t='INTEGER'}; @{n='cantidad_disponible';t='INTEGER'}; @{n='cantidad_reservada';t='INTEGER'}; @{n='creado_en';t='TIMESTAMPTZ'}; @{n='actualizado_en';t='TIMESTAMPTZ'}; @{n='stock_minimo';t='INTEGER'})
  'MovimientoInventario' = @(@{n='id';t='BIGSERIAL'}; @{n='existencia_id';t='BIGINT'}; @{n='tipo';t='VARCHAR(15)'}; @{n='cantidad';t='INTEGER'}; @{n='motivo';t='VARCHAR(200)'}; @{n='proveedor_id';t='BIGINT'}; @{n='referencia';t='VARCHAR(40)'}; @{n='usuario_id';t='BIGINT'}; @{n='creado_en';t='TIMESTAMPTZ'})
  'Reserva' = @(@{n='id';t='BIGSERIAL'}; @{n='cliente_id';t='BIGINT'}; @{n='sucursal_id';t='INTEGER'}; @{n='franja_inicio';t='TIMESTAMPTZ'}; @{n='franja_fin';t='TIMESTAMPTZ'}; @{n='estado';t='VARCHAR(10)'}; @{n='observacion';t='VARCHAR(200)'}; @{n='creado_en';t='TIMESTAMPTZ'}; @{n='actualizado_en';t='TIMESTAMPTZ'})
  'ReservaDetalle' = @(@{n='id';t='BIGSERIAL'}; @{n='reserva_id';t='BIGINT'}; @{n='variante_id';t='BIGINT'}; @{n='cantidad';t='INTEGER'}; @{n='resultado_prueba';t='VARCHAR(10)'}; @{n='creado_en';t='TIMESTAMPTZ'}; @{n='actualizado_en';t='TIMESTAMPTZ'})
}

$OPS = @{
  'Producto' = @(
    @{n='contar_productos'; r='int'; p=@(@{n='db';t='Session'})},
    @{n='listar_productos'; r='list[Producto]'; p=@(@{n='db';t='Session'})},
    @{n='obtener_producto'; r='Producto | None'; p=@(@{n='db';t='Session'}; @{n='producto_id';t='int'})},
    @{n='existe_codigo'; r='bool'; p=@(@{n='db';t='Session'}; @{n='codigo';t='str'})},
    @{n='agregar_producto'; r='Producto'; p=@(@{n='db';t='Session'})},
    @{n='eliminar_producto'; r='None'; p=@(@{n='db';t='Session'}; @{n='producto';t='Producto'})},
    @{n='conteo_de_variantes'; r='dict[int, tuple[int, int]]'; p=@(@{n='db';t='Session'}; @{n='producto_ids';t='list[int]'})},
    @{n='conteo_de_imagenes'; r='dict[int, tuple[int, int]]'; p=@(@{n='db';t='Session'}; @{n='producto_ids';t='list[int]'})},
    @{n='nombre_de_categoria'; r='str | None'; p=@(@{n='db';t='Session'}; @{n='categoria_id';t='int'})}
  )
  'VarianteProducto' = @(
    @{n='obtener_variante'; r='VarianteProducto | None'; p=@(@{n='db';t='Session'}; @{n='variante_id';t='int'})},
    @{n='combinaciones_existentes'; r='set[tuple[int, int]]'; p=@(@{n='db';t='Session'}; @{n='producto_id';t='int'})},
    @{n='agregar_variante'; r='VarianteProducto'; p=@(@{n='db';t='Session'})},
    @{n='eliminar_variante'; r='None'; p=@(@{n='db';t='Session'}; @{n='variante';t='VarianteProducto'})},
    @{n='codigos_de_talla'; r='dict[int, str]'; p=@(@{n='db';t='Session'}; @{n='ids';t='list[int]'})},
    @{n='nombres_de_color'; r='dict[int, str]'; p=@(@{n='db';t='Session'}; @{n='ids';t='list[int]'})},
    @{n='variante_ofrecible'; r='VarianteProducto | None'; p=@(@{n='db';t='Session'}; @{n='variante_id';t='int'})},
    @{n='rango_de_precios'; r='dict[int, tuple[Decimal, Decimal]]'; p=@(@{n='db';t='Session'}; @{n='producto_ids';t='list[int]'})},
    @{n='colores_por_producto'; r='dict[int, list[tuple[int, str, str]]]'; p=@(@{n='db';t='Session'}; @{n='producto_ids';t='list[int]'})},
    @{n='variantes_con_vestidor'; r='set[int]'; p=@(@{n='db';t='Session'}; @{n='producto_ids';t='list[int]'})}
  )
  'ImagenProducto' = @(
    @{n='listar_de_producto'; r='list[ImagenProducto]'; p=@(@{n='db';t='Session'}; @{n='producto_id';t='int'})},
    @{n='obtener'; r='ImagenProducto | None'; p=@(@{n='db';t='Session'}; @{n='imagen_id';t='int'})},
    @{n='variante_de_producto'; r='VarianteProducto | None'; p=@(@{n='db';t='Session'})},
    @{n='principal_de'; r='ImagenProducto | None'; p=@(@{n='db';t='Session'}; @{n='producto_id';t='int'})},
    @{n='transparente_de_variante'; r='ImagenProducto | None'; p=@(@{n='db';t='Session'}; @{n='variante_id';t='int'})},
    @{n='siguiente_orden'; r='int'; p=@(@{n='db';t='Session'}; @{n='producto_id';t='int'})},
    @{n='contar_de_producto'; r='int'; p=@(@{n='db';t='Session'}; @{n='producto_id';t='int'})},
    @{n='agregar'; r='ImagenProducto'; p=@(@{n='db';t='Session'})},
    @{n='eliminar'; r='None'; p=@(@{n='db';t='Session'}; @{n='imagen';t='ImagenProducto'})}
  )
  'Existencia' = @(
    @{n='obtener_existencia'; r='Existencia | None'; p=@(@{n='db';t='Session'})},
    @{n='obtener_existencia_con_detalle'; r='Row | None'; p=@(@{n='db';t='Session'}; @{n='existencia_id';t='int'})},
    @{n='obtener_existencia_por_id'; r='Existencia | None'; p=@(@{n='db';t='Session'}; @{n='existencia_id';t='int'})},
    @{n='agregar_existencia'; r='Existencia'; p=@(@{n='db';t='Session'})},
    @{n='listar_alertas'; r='list[Row]'; p=@(@{n='db';t='Session'})},
    @{n='disponibilidad_por_sucursal'; r='list[Row]'; p=@(@{n='db';t='Session'}; @{n='variante_id';t='int'})},
    @{n='inventario_consolidado'; r='list[Row]'; p=@(@{n='db';t='Session'})}
  )
  'MovimientoInventario' = @(
    @{n='agregar_movimiento'; r='MovimientoInventario'; p=@(@{n='db';t='Session'})},
    @{n='obtener_movimiento'; r='Row | None'; p=@(@{n='db';t='Session'}; @{n='movimiento_id';t='int'})},
    @{n='contar_movimientos'; r='int'; p=@(@{n='db';t='Session'})},
    @{n='listar_movimientos'; r='list[Row]'; p=@(@{n='db';t='Session'})},
    @{n='contar_ingresos'; r='int'; p=@(@{n='db';t='Session'})},
    @{n='listar_ingresos'; r='list[Row]'; p=@(@{n='db';t='Session'})},
    @{n='lineas_de_ingreso'; r='list[Row]'; p=@(@{n='db';t='Session'})}
  )
  'Reserva' = @(
    @{n='obtener_reserva'; r='Row | None'; p=@(@{n='db';t='Session'}; @{n='reserva_id';t='int'})},
    @{n='obtener_reserva_entidad'; r='Reserva | None'; p=@(@{n='db';t='Session'}; @{n='reserva_id';t='int'})},
    @{n='contar_reservas_solapadas'; r='int'; p=@(@{n='db';t='Session'})},
    @{n='listar_vencidas'; r='list[Reserva]'; p=@(@{n='db';t='Session'})},
    @{n='agregar_reserva'; r='Reserva'; p=@(@{n='db';t='Session'})},
    @{n='contar_reservas'; r='int'; p=@(@{n='db';t='Session'})},
    @{n='listar_reservas'; r='list[Row]'; p=@(@{n='db';t='Session'})},
    @{n='obtener_cliente_de_usuario'; r='Cliente | None'; p=@(@{n='db';t='Session'}; @{n='usuario_id';t='int'})},
    @{n='obtener_sucursal'; r='Sucursal | None'; p=@(@{n='db';t='Session'}; @{n='sucursal_id';t='int'})}
  )
  'ReservaDetalle' = @(
    @{n='agregar_detalle'; r='DetalleReserva'; p=@(@{n='db';t='Session'})},
    @{n='detalles_de'; r='list[DetalleReserva]'; p=@(@{n='db';t='Session'}; @{n='reserva_id';t='int'})},
    @{n='listar_detalles'; r='list[Row]'; p=@(@{n='db';t='Session'}; @{n='reserva_id';t='int'})},
    @{n='listar_variantes'; r='list[Row]'; p=@(@{n='db';t='Session'}; @{n='ids';t='list[int]'})}
  )
  'GestorProductos' = @(
    @{n='listar_productos'; r='PaginaProductos'; p=@(@{n='db';t='Session'})},
    @{n='obtener_producto'; r='ProductoOut'; p=@(@{n='db';t='Session'}; @{n='producto_id';t='int'})},
    @{n='crear_producto'; r='ProductoOut'; p=@(@{n='db';t='Session'}; @{n='datos';t='ProductoCrearIn'})},
    @{n='editar_producto'; r='ProductoOut'; p=@(@{n='db';t='Session'}; @{n='producto_id';t='int'}; @{n='datos';t='ProductoEditarIn'})},
    @{n='cambiar_estado_producto'; r='ProductoOut'; p=@(@{n='db';t='Session'}; @{n='producto_id';t='int'}; @{n='datos';t='CambioEstadoIn'})},
    @{n='eliminar_producto'; r='None'; p=@(@{n='db';t='Session'}; @{n='producto_id';t='int'})},
    @{n='generar_variantes'; r='GenerarVariantesOut'; p=@(@{n='db';t='Session'}; @{n='producto_id';t='int'}; @{n='datos';t='GenerarVariantesIn'})},
    @{n='crear_variante'; r='VarianteOut'; p=@(@{n='db';t='Session'}; @{n='producto_id';t='int'}; @{n='datos';t='VarianteCrearIn'})},
    @{n='editar_variante'; r='VarianteOut'; p=@(@{n='db';t='Session'}; @{n='variante_id';t='int'}; @{n='datos';t='VarianteEditarIn'})},
    @{n='eliminar_variante'; r='None'; p=@(@{n='db';t='Session'}; @{n='variante_id';t='int'})},
    @{n='armar_sku'; r='str'; p=@(@{n='codigo_producto';t='str'}; @{n='codigo_talla';t='str'}; @{n='nombre_color';t='str'})},
    @{n='_validar_maestros'; r='None'; p=@(@{n='db';t='Session'})},
    @{n='_resolver_temporada'; r='int | None'; p=@(@{n='db';t='Session'})},
    @{n='_precio_de'; r='Decimal'; p=@(@{n='datos_precio';t='Decimal | None'}; @{n='producto';t='Producto'})},
    @{n='_viola'; r='bool'; p=@(@{n='exc';t='IntegrityError'}; @{n='restriccion';t='str'})}
  )
  'GestorImagenes' = @(
    @{n='listar'; r='list[ImagenOut]'; p=@(@{n='db';t='Session'}; @{n='producto_id';t='int'})},
    @{n='obtener'; r='ImagenOut'; p=@(@{n='db';t='Session'}; @{n='imagen_id';t='int'})},
    @{n='subir'; r='ImagenOut'; p=@(@{n='db';t='Session'}; @{n='producto_id';t='int'})},
    @{n='editar'; r='ImagenOut'; p=@(@{n='db';t='Session'}; @{n='imagen_id';t='int'}; @{n='datos';t='ImagenEditarIn'})},
    @{n='marcar_principal'; r='list[ImagenOut]'; p=@(@{n='db';t='Session'}; @{n='imagen_id';t='int'}; @{n='datos';t='MarcarPrincipalIn'})},
    @{n='marcar_transparente'; r='list[ImagenOut]'; p=@(@{n='db';t='Session'}; @{n='imagen_id';t='int'}; @{n='datos';t='MarcarTransparenteIn'})},
    @{n='reordenar'; r='list[ImagenOut]'; p=@(@{n='db';t='Session'}; @{n='producto_id';t='int'}; @{n='datos';t='ReordenarIn'})},
    @{n='eliminar'; r='None'; p=@(@{n='db';t='Session'}; @{n='imagen_id';t='int'})},
    @{n='_asegurar_producto'; r='None'; p=@(@{n='db';t='Session'}; @{n='producto_id';t='int'})},
    @{n='_asegurar_variante'; r='None'; p=@(@{n='db';t='Session'})},
    @{n='_archivo_tiene_transparencia'; r='bool'; p=@(@{n='ruta';t='str'})}
  )
  'GestorInventario' = @(
    @{n='registrar_ingreso'; r='IngresoOut'; p=@(@{n='db';t='Session'}; @{n='datos';t='IngresoIn'})},
    @{n='listar_ingresos'; r='PaginaIngresos'; p=@(@{n='db';t='Session'})},
    @{n='detalle_de_ingreso'; r='list[MovimientoOut]'; p=@(@{n='db';t='Session'})},
    @{n='registrar_ajuste'; r='AjusteOut'; p=@(@{n='db';t='Session'}; @{n='datos';t='AjusteIn'})},
    @{n='registrar_transferencia'; r='TransferenciaOut'; p=@(@{n='db';t='Session'}; @{n='datos';t='TransferenciaIn'})},
    @{n='listar_movimientos'; r='PaginaMovimientos'; p=@(@{n='db';t='Session'})},
    @{n='existencia_por_id'; r='ExistenciaOut | None'; p=@(@{n='db';t='Session'}; @{n='existencia_id';t='int'})},
    @{n='fijar_stock_minimo'; r='ExistenciaOut'; p=@(@{n='db';t='Session'}; @{n='existencia_id';t='int'}; @{n='valor';t='int'})},
    @{n='alertas_de_stock'; r='list[ExistenciaOut]'; p=@(@{n='db';t='Session'})},
    @{n='apartar_para_reserva'; r='Existencia'; p=@(@{n='db';t='Session'})},
    @{n='liberar_de_reserva'; r='Existencia'; p=@(@{n='db';t='Session'})},
    @{n='descontar_por_venta'; r='Existencia'; p=@(@{n='db';t='Session'})},
    @{n='disponibilidad_por_sucursal'; r='list[dict]'; p=@(@{n='db';t='Session'}; @{n='variante_id';t='int'})},
    @{n='inventario_consolidado'; r='list[ExistenciaOut]'; p=@(@{n='db';t='Session'})},
    @{n='_aplicar_movimiento'; r='None'; p=@(@{n='db';t='Session'}; @{n='existencia';t='Existencia'})},
    @{n='_existencia_o_crearla'; r='Existencia'; p=@(@{n='db';t='Session'})},
    @{n='_sucursal_activa'; r='None'; p=@(@{n='db';t='Session'}; @{n='sucursal_id';t='int'})},
    @{n='_variantes_validas'; r='dict[int, object]'; p=@(@{n='db';t='Session'}; @{n='ids';t='list[int]'})}
  )
  'GestorConsolidado' = @(
    @{n='consultar'; r='tuple[PaginaInventarioConsolidado, ResumenInventarioOut]'; p=@(@{n='db';t=''})},
    @{n='_estado'; r='EstadoExistencia'; p=@(@{n='disponible';t='int'}; @{n='reservado';t='int'})},
    @{n='_agrupar'; r='list[ExistenciaConsolidadaOut]'; p=@(@{n='filas';t=''})},
    @{n='_ordenar'; r='None'; p=@(@{n='items';t='list[ExistenciaConsolidadaOut]'}; @{n='orden';t='str'})}
  )
  'GestorVitrina' = @(
    @{n='listar_productos'; r='PaginaVitrina'; p=@(@{n='db';t='Session'})},
    @{n='obtener_ficha'; r='FichaProductoOut'; p=@(@{n='db';t='Session'}; @{n='producto_id';t='int'})},
    @{n='disponibilidad_de_variante'; r='DisponibilidadOut'; p=@(@{n='db';t='Session'}; @{n='variante_id';t='int'})},
    @{n='obtener_filtros'; r='FiltrosOut'; p=@(@{n='db';t='Session'})},
    @{n='_ordenadas'; r='list'; p=@(@{n='variantes';t='list'})},
    @{n='_variante'; r='VarianteVitrinaOut'; p=@(@{n='variante';t=''}; @{n='vestidor';t='dict[int, str]'})},
    @{n='_opciones'; r='tuple[list[TallaOut], list[ColorOut]]'; p=@(@{n='variantes';t='list'})}
  )
  'GestorReservas' = @(
    @{n='crear_reserva'; r='ReservaOut'; p=@(@{n='db';t='Session'}; @{n='datos';t='ReservaCrearIn'})},
    @{n='cancelar_reserva'; r='ReservaOut'; p=@(@{n='db';t='Session'}; @{n='reserva_id';t='int'}; @{n='datos';t='CancelarReservaIn'})},
    @{n='preparar_reserva'; r='ReservaOut'; p=@(@{n='db';t='Session'}; @{n='reserva_id';t='int'})},
    @{n='atender_reserva'; r='ReservaOut'; p=@(@{n='db';t='Session'}; @{n='reserva_id';t='int'}; @{n='datos';t='AtenderReservaIn'})},
    @{n='listar_reservas_de_sucursal'; r='PaginaReservas'; p=@(@{n='db';t='Session'})},
    @{n='obtener_reserva_de_sucursal'; r='ReservaOut'; p=@(@{n='db';t='Session'}; @{n='reserva_id';t='int'})},
    @{n='expirar_reservas_vencidas'; r='ExpiracionOut'; p=@(@{n='db';t='Session'})},
    @{n='obtener_reserva_de_cliente'; r='ReservaOut'; p=@(@{n='db';t='Session'}; @{n='reserva_id';t='int'})},
    @{n='listar_mis_reservas'; r='PaginaReservas'; p=@(@{n='db';t='Session'})},
    @{n='_validar_franja'; r='None'; p=@(@{n='datos';t='ReservaCrearIn'}; @{n='sucursal';t=''})},
    @{n='_armar_reserva'; r='ReservaOut'; p=@(@{n='db';t='Session'}; @{n='reserva_id';t='int'})},
    @{n='_reserva_de_la_sucursal'; r='None'; p=@(@{n='db';t='Session'}; @{n='reserva_id';t='int'})},
    @{n='_ahora'; r='datetime'; p=@()}
  )
  'PantallaProductos' = @(
    @{n='listar'; r='Observable<PaginaProductos>'; p=@(@{n='filtros';t='FiltrosProductos'})},
    @{n='obtener'; r='Observable<Producto>'; p=@(@{n='id';t='number'})},
    @{n='crear'; r='Observable<Producto>'; p=@(@{n='datos';t='ProductoCrear'})},
    @{n='editar'; r='Observable<Producto>'; p=@(@{n='id';t='number'}; @{n='datos';t='ProductoEditar'})},
    @{n='cambiarEstado'; r='Observable<Producto>'; p=@(@{n='id';t='number'}; @{n='activo';t='boolean'})},
    @{n='eliminar'; r='Observable<void>'; p=@(@{n='id';t='number'})},
    @{n='generarVariantes'; r='Observable<ResultadoGeneracion>'; p=@(@{n='productoId';t='number'}; @{n='datos';t='GenerarVariantes'})},
    @{n='crearVariante'; r='Observable<Variante>'; p=@(@{n='productoId';t='number'}; @{n='datos';t='VarianteCrear'})},
    @{n='editarVariante'; r='Observable<Variante>'; p=@(@{n='id';t='number'}; @{n='datos';t='VarianteEditar'})},
    @{n='eliminarVariante'; r='Observable<void>'; p=@(@{n='id';t='number'})},
    @{n='listar_productos'; r='PaginaProductos'; p=@(@{n='db';t='DbSession'}; @{n='busqueda';t='Annotated[str | None, Query(max_length=120, description=Nombre o código)]'}; @{n='categoria_id';t='Annotated[int | None, Query()]'}; @{n='temporada_id';t='Annotated[int | None, Query()]'}; @{n='coleccion_id';t='Annotated[int | None, Query()]'}; @{n='proveedor_id';t='Annotated[int | None, Query()]'}; @{n='activo';t='Annotated[bool | None, Query()]'}; @{n='pagina';t='Annotated[int, Query(ge=1)]'}; @{n='tamano';t='Annotated[int, Query(ge=1, le=100)]'})},
    @{n='crear_producto'; r='ProductoOut'; p=@(@{n='datos';t='ProductoCrearIn'}; @{n='db';t='DbSession'})},
    @{n='obtener_producto'; r='ProductoOut'; p=@(@{n='producto_id';t='int'}; @{n='db';t='DbSession'})},
    @{n='editar_producto'; r='ProductoOut'; p=@(@{n='producto_id';t='int'}; @{n='datos';t='ProductoEditarIn'}; @{n='db';t='DbSession'})},
    @{n='cambiar_estado_producto'; r='ProductoOut'; p=@(@{n='producto_id';t='int'}; @{n='datos';t='CambioEstadoIn'}; @{n='db';t='DbSession'})},
    @{n='eliminar_producto'; r='Response'; p=@(@{n='producto_id';t='int'}; @{n='db';t='DbSession'})},
    @{n='generar_variantes'; r='GenerarVariantesOut'; p=@(@{n='producto_id';t='int'}; @{n='datos';t='GenerarVariantesIn'}; @{n='db';t='DbSession'})},
    @{n='crear_variante'; r='VarianteOut'; p=@(@{n='producto_id';t='int'}; @{n='datos';t='VarianteCrearIn'}; @{n='db';t='DbSession'})},
    @{n='editar_variante'; r='VarianteOut'; p=@(@{n='variante_id';t='int'}; @{n='datos';t='VarianteEditarIn'}; @{n='db';t='DbSession'})},
    @{n='eliminar_variante'; r='Response'; p=@(@{n='variante_id';t='int'}; @{n='db';t='DbSession'})}
  )
  'PantallaImagenes' = @(
    @{n='listarImagenes'; r='Observable<Imagen[]>'; p=@(@{n='productoId';t='number'})},
    @{n='subirImagen'; r='Observable<Imagen>'; p=@(@{n='productoId';t='number'}; @{n='archivo';t='File'}; @{n='varianteId';t='number | null'})},
    @{n='editarImagen'; r='Observable<Imagen>'; p=@(@{n='id';t='number'}; @{n='datos';t='ImagenEditar'})},
    @{n='marcarPrincipal'; r='Observable<Imagen[]>'; p=@(@{n='id';t='number'}; @{n='esPrincipal';t='boolean'})},
    @{n='marcarTransparente'; r='Observable<Imagen[]>'; p=@(@{n='id';t='number'}; @{n='esTransparente';t='boolean'})},
    @{n='reordenarImagenes'; r='Observable<Imagen[]>'; p=@(@{n='productoId';t='number'}; @{n='datos';t='ReordenarImagenes'})},
    @{n='eliminarImagen'; r='Observable<void>'; p=@(@{n='id';t='number'})},
    @{n='urlDeImagen'; r='string'; p=@(@{n='imagen';t='Imagen'})},
    @{n='listar'; r='list[ImagenOut]'; p=@(@{n='producto_id';t='int'}; @{n='db';t='DbSession'})},
    @{n='editar'; r='ImagenOut'; p=@(@{n='imagen_id';t='int'}; @{n='datos';t='ImagenEditarIn'}; @{n='db';t='DbSession'})},
    @{n='marcar_principal'; r='list[ImagenOut]'; p=@(@{n='imagen_id';t='int'}; @{n='datos';t='MarcarPrincipalIn'}; @{n='db';t='DbSession'})},
    @{n='marcar_transparente'; r='list[ImagenOut]'; p=@(@{n='imagen_id';t='int'}; @{n='datos';t='MarcarTransparenteIn'}; @{n='db';t='DbSession'})},
    @{n='reordenar'; r='list[ImagenOut]'; p=@(@{n='producto_id';t='int'}; @{n='datos';t='ReordenarIn'}; @{n='db';t='DbSession'})},
    @{n='eliminar'; r='Response'; p=@(@{n='imagen_id';t='int'}; @{n='db';t='DbSession'})}
  )
  'PantallaInventario' = @(
    @{n='registrarIngreso'; r='Observable<IngresoRegistrado>'; p=@(@{n='datos';t='IngresoCrear'})},
    @{n='listarIngresos'; r='Observable<PaginaIngresos>'; p=@(@{n='filtros';t='FiltrosIngresos'})},
    @{n='detalleDeIngreso'; r='Observable<Movimiento[]>'; p=@(@{n='ingreso';t='IngresoResumen'})},
    @{n='listarExistencias'; r='Observable<Existencia[]>'; p=@(@{n='filtros';t='FiltrosExistencias'})},
    @{n='listarMovimientos'; r='Observable<PaginaMovimientos>'; p=@(@{n='filtros';t='FiltrosMovimientos'})},
    @{n='tiposManuales'; r='Observable<TipoManual[]>'; p=@()},
    @{n='registrarAjuste'; r='Observable<AjusteRegistrado>'; p=@(@{n='datos';t='AjusteCrear'})},
    @{n='registrarTransferencia'; r='Observable<TransferenciaRegistrada>'; p=@(@{n='datos';t='TransferenciaCrear'})},
    @{n='registrar_ingreso'; r='IngresoOut'; p=@(@{n='datos';t='IngresoIn'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='listar_ingresos'; r='PaginaIngresos'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'}; @{n='sucursal_id';t='Annotated[int | None, Query()]'}; @{n='proveedor_id';t='Annotated[int | None, Query()]'}; @{n='pagina';t='Annotated[int, Query(ge=1)]'}; @{n='tamano';t='Annotated[int, Query(ge=1, le=100)]'})},
    @{n='detalle_de_ingreso'; r='list[MovimientoOut]'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'}; @{n='registrado_en';t='Annotated[datetime, Query(description=Instante exacto del ingreso)]'}; @{n='sucursal_id';t='Annotated[int, Query()]'}; @{n='referencia';t='Annotated[str | None, Query(max_length=40)]'})},
    @{n='listar_existencias'; r='list[ExistenciaOut]'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'}; @{n='sucursal_id';t='Annotated[int | None, Query()]'}; @{n='producto_id';t='Annotated[int | None, Query()]'}; @{n='solo_con_saldo';t='Annotated[bool, Query()]'})},
    @{n='listar_movimientos'; r='PaginaMovimientos'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'}; @{n='sucursal_id';t='Annotated[int | None, Query()]'}; @{n='variante_id';t='Annotated[int | None, Query()]'}; @{n='tipo';t='Annotated[str | None, Query(pattern=_PATRON_TIPO)]'}; @{n='desde';t='Annotated[datetime | None, Query()]'}; @{n='hasta';t='Annotated[datetime | None, Query()]'}; @{n='pagina';t='Annotated[int, Query(ge=1)]'}; @{n='tamano';t='Annotated[int, Query(ge=1, le=100)]'})},
    @{n='listar_tipos_manuales'; r='list[str]'; p=@()},
    @{n='registrar_ajuste'; r='AjusteOut'; p=@(@{n='datos';t='AjusteIn'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='registrar_transferencia'; r='TransferenciaOut'; p=@(@{n='datos';t='TransferenciaIn'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})}
  )
  'PantallaConsolidado' = @(
    @{n='consultar'; r='Observable<InventarioConsolidado>'; p=@(@{n='consulta';t='ConsultaConsolidado'})},
    @{n='consultar_consolidado'; r='InventarioConsolidadoOut'; p=@(@{n='db';t='DbSession'}; @{n='busqueda';t='Annotated[str | None, Query(max_length=120, description=SKU, prenda o color)]'}; @{n='sucursal_id';t='Annotated[int | None, Query()]'}; @{n='producto_id';t='Annotated[int | None, Query()]'}; @{n='estado';t='Annotated[EstadoExistencia | None, Query()]'}; @{n='orden';t='Annotated[str, Query(pattern=^(prenda|disponible_asc|disponible_desc|sucursales)$)]'}; @{n='pagina';t='Annotated[int, Query(ge=1)]'}; @{n='tamano';t='Annotated[int, Query(ge=1, le=100)]'})}
  )
  'PantallaDisponibilidad' = @(
    @{n='listarAlertas'; r='Observable<Existencia[]>'; p=@(@{n='sucursal_id';t='number'})},
    @{n='fijarStockMinimo'; r='Observable<Existencia>'; p=@(@{n='existencia_id';t='number'}; @{n='datos';t='StockMinimoCrear'})},
    @{n='listarExistencias'; r='Observable<Existencia[]>'; p=@(@{n='filtros';t='FiltrosExistencias'})},
    @{n='registrarAjuste'; r='Observable<AjusteRegistrado>'; p=@(@{n='datos';t='AjusteCrear'})},
    @{n='listar_alertas'; r='list[ExistenciaOut]'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'}; @{n='sucursal_id';t='Annotated[int | None, Query()]'})},
    @{n='fijar_stock_minimo'; r='ExistenciaOut'; p=@(@{n='existencia_id';t='int'}; @{n='datos';t='StockMinimoIn'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='listar_existencias'; r='list[ExistenciaOut]'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'}; @{n='sucursal_id';t='Annotated[int | None, Query()]'}; @{n='producto_id';t='Annotated[int | None, Query()]'}; @{n='solo_con_saldo';t='Annotated[bool, Query()]'})}
  )
  'PantallaCatalogo' = @(
    @{n='listar'; r='Observable<PaginaVitrina>'; p=@(@{n='consulta';t='ConsultaVitrina'})},
    @{n='obtenerFiltros'; r='Observable<FiltrosDisponibles>'; p=@()},
    @{n='urlDeImagen'; r='string | null'; p=@(@{n='url';t='string | null'})},
    @{n='listar_productos'; r='PaginaVitrina'; p=@(@{n='db';t='DbSession'}; @{n='busqueda';t='Annotated[str | None, Query(max_length=120, description=Nombre, descripción o código)]'}; @{n='categoria_id';t='Annotated[int | None, Query(description=Incluye las subcategorías que cuelgan de ella)]'}; @{n='talla_id';t='Annotated[int | None, Query()]'}; @{n='color_id';t='Annotated[int | None, Query()]'}; @{n='temporada_id';t='Annotated[int | None, Query()]'}; @{n='coleccion_id';t='Annotated[int | None, Query()]'}; @{n='precio_min';t='Annotated[Decimal | None, Query(ge=0)]'}; @{n='precio_max';t='Annotated[Decimal | None, Query(ge=0)]'}; @{n='orden';t='Annotated[Literal[novedades, precio_asc, precio_desc, nombre], Query()]'}; @{n='pagina';t='Annotated[int, Query(ge=1)]'}; @{n='tamano';t='Annotated[int, Query(ge=1, le=48)]'})},
    @{n='obtener_filtros'; r='FiltrosOut'; p=@(@{n='db';t='DbSession'})}
  )
  'PantallaFichaProducto' = @(
    @{n='obtenerFicha'; r='Observable<FichaProducto>'; p=@(@{n='productoId';t='number'})},
    @{n='obtenerDisponibilidad'; r='Observable<Disponibilidad>'; p=@(@{n='varianteId';t='number'})},
    @{n='urlDeImagen'; r='string | null'; p=@(@{n='url';t='string | null'})},
    @{n='obtener_ficha'; r='FichaProductoOut'; p=@(@{n='db';t='DbSession'}; @{n='producto_id';t='Annotated[int, Path(ge=1)]'})},
    @{n='disponibilidad_de_variante'; r='DisponibilidadOut'; p=@(@{n='db';t='DbSession'}; @{n='variante_id';t='Annotated[int, Path(ge=1)]'})}
  )
  'PantallaReservas' = @(
    @{n='crear'; r='Observable<Reserva>'; p=@(@{n='datos';t='ReservaCrear'})},
    @{n='misReservas'; r='Observable<PaginaReservas>'; p=@(@{n='filtros';t='FiltrosReservas'})},
    @{n='obtener'; r='Observable<Reserva>'; p=@(@{n='id';t='number'})},
    @{n='cancelar'; r='Observable<Reserva>'; p=@(@{n='id';t='number'}; @{n='datos';t='CancelarReserva'})},
    @{n='crear_reserva'; r='ReservaOut'; p=@(@{n='datos';t='ReservaCrearIn'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='listar_mis_reservas'; r='PaginaReservas'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'}; @{n='estado';t='Annotated[str | None, Query(pattern=_PATRON_ESTADO)]'}; @{n='vivas';t='Annotated[bool | None, Query(description=true: solo PENDIENTE o PREPARADA; false: las cerradas)]'}; @{n='pagina';t='Annotated[int, Query(ge=1)]'}; @{n='tamano';t='Annotated[int, Query(ge=1, le=100)]'})},
    @{n='obtener_reserva'; r='ReservaOut'; p=@(@{n='reserva_id';t='int'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='cancelar_reserva'; r='ReservaOut'; p=@(@{n='reserva_id';t='int'}; @{n='datos';t='CancelarReservaIn'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})}
  )
  'PantallaReservasSucursal' = @(
    @{n='deMiSucursal'; r='Observable<PaginaReservas>'; p=@(@{n='filtros';t='FiltrosReservas'})},
    @{n='obtenerDeSucursal'; r='Observable<Reserva>'; p=@(@{n='id';t='number'})},
    @{n='preparar'; r='Observable<Reserva>'; p=@(@{n='id';t='number'})},
    @{n='atender'; r='Observable<Reserva>'; p=@(@{n='id';t='number'}; @{n='datos';t='AtenderReserva'})},
    @{n='listar_reservas_de_sucursal'; r='PaginaReservas'; p=@(@{n='db';t='DbSession'}; @{n='usuario';t='Usuario'}; @{n='estado';t='Annotated[str | None, Query(pattern=_PATRON_ESTADO)]'}; @{n='vivas';t='Annotated[bool | None, Query()]'}; @{n='pagina';t='Annotated[int, Query(ge=1)]'}; @{n='tamano';t='Annotated[int, Query(ge=1, le=100)]'})},
    @{n='obtener_reserva_de_sucursal'; r='ReservaOut'; p=@(@{n='reserva_id';t='int'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='preparar_reserva'; r='ReservaOut'; p=@(@{n='reserva_id';t='int'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})},
    @{n='atender_reserva'; r='ReservaOut'; p=@(@{n='reserva_id';t='int'}; @{n='datos';t='AtenderReservaIn'}; @{n='db';t='DbSession'}; @{n='usuario';t='Usuario'})}
  )
  'PlanificadorTareas' = @(
    @{n='expirarVencidas'; r='Observable<Expiracion>'; p=@()},
    @{n='expirar_reservas_vencidas'; r='ExpiracionOut'; p=@(@{n='db';t='DbSession'})}
  )
}
