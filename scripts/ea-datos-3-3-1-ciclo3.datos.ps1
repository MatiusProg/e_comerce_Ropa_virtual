# GENERADO por scripts/gen-dominio-3-3-1-ciclo3.py --- NO editar a mano.
# El sistema ENTERO: las 43 tablas. Las columnas, sus tipos y los
# estereotipos PK/FK salen de information_schema de la base de pruebas, que
# `alembic upgrade head` deja al dia. Las cardinalidades salen de lo que la
# base OBLIGA --- NOT NULL y UNIQUE ---, no de la prosa.

$TABLAS_C3 = @(
  @{ n='ABASTECIMIENTO'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='proveedor_id'; t='BIGINT'; k='FK'},
       @{n='variante_id'; t='BIGINT'; k='FK'},
       @{n='cantidad'; t='INTEGER'},
       @{n='dias_plazo'; t='INTEGER'},
       @{n='observacion'; t='VARCHAR(200)'},
       @{n='estado'; t='VARCHAR(20)'},
       @{n='cantidad_recibida'; t='INTEGER'},
       @{n='recibido_en'; t='TIMESTAMPTZ'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='BITACORA'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='ocurrido_en'; t='TIMESTAMPTZ'},
       @{n='usuario_id'; t='BIGINT'; k='FK'},
       @{n='actor'; t='VARCHAR(160)'},
       @{n='rol'; t='VARCHAR(40)'},
       @{n='accion'; t='VARCHAR(40)'},
       @{n='entidad'; t='VARCHAR(60)'},
       @{n='entidad_id'; t='VARCHAR(60)'},
       @{n='metodo'; t='VARCHAR(10)'},
       @{n='ruta'; t='VARCHAR(300)'},
       @{n='estado_http'; t='INTEGER'},
       @{n='exito'; t='BOOLEAN'},
       @{n='ip'; t='VARCHAR(60)'},
       @{n='agente'; t='VARCHAR(200)'},
       @{n='detalle'; t='JSONB'}
     ) },
  @{ n='CAJA'
     cols=@(
       @{n='id'; t='SERIAL'; k='PK'},
       @{n='sucursal_id'; t='INTEGER'; k='FK'},
       @{n='nombre'; t='VARCHAR(50)'},
       @{n='activa'; t='BOOLEAN'}
     ) },
  @{ n='CARRITO'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='cliente_id'; t='BIGINT'; k='FK'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='CARRITO_DETALLE'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='carrito_id'; t='BIGINT'; k='FK'},
       @{n='variante_id'; t='BIGINT'; k='FK'},
       @{n='cantidad'; t='INTEGER'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='CATEGORIA'
     cols=@(
       @{n='id'; t='SERIAL'; k='PK'},
       @{n='categoria_padre_id'; t='INTEGER'; k='FK'},
       @{n='nombre'; t='VARCHAR(60)'},
       @{n='orden'; t='SMALLINT'},
       @{n='activa'; t='BOOLEAN'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='CIUDAD'
     cols=@(
       @{n='id'; t='SERIAL'; k='PK'},
       @{n='nombre'; t='VARCHAR(60)'},
       @{n='departamento'; t='VARCHAR(60)'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='CLIENTE'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='usuario_id'; t='BIGINT'; k='FK'},
       @{n='documento'; t='VARCHAR(20)'},
       @{n='telefono'; t='VARCHAR(20)'},
       @{n='talla_superior'; t='VARCHAR(10)'},
       @{n='talla_inferior'; t='VARCHAR(10)'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='CLIENTE_CATEGORIA'
     cols=@(
       @{n='cliente_id'; t='BIGINT'; k='PK,FK'},
       @{n='categoria_id'; t='INTEGER'; k='PK,FK'}
     ) },
  @{ n='COLECCION'
     cols=@(
       @{n='id'; t='SERIAL'; k='PK'},
       @{n='temporada_id'; t='INTEGER'; k='FK'},
       @{n='nombre'; t='VARCHAR(60)'},
       @{n='descripcion'; t='VARCHAR(200)'},
       @{n='activa'; t='BOOLEAN'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='COLOR'
     cols=@(
       @{n='id'; t='SERIAL'; k='PK'},
       @{n='nombre'; t='VARCHAR(40)'},
       @{n='hexadecimal'; t='CHARACTER'},
       @{n='activo'; t='BOOLEAN'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='COMPROBANTE'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='venta_id'; t='BIGINT'; k='FK'},
       @{n='tipo'; t='VARCHAR(10)'},
       @{n='numero'; t='VARCHAR(20)'},
       @{n='nit_ci'; t='VARCHAR(20)'},
       @{n='razon_social'; t='VARCHAR(120)'},
       @{n='emitido_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='DETALLE_DEVOLUCION'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='devolucion_id'; t='BIGINT'; k='FK'},
       @{n='variante_id'; t='BIGINT'; k='FK'},
       @{n='cantidad'; t='INTEGER'},
       @{n='creado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='DETALLE_VENTA'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='venta_id'; t='BIGINT'; k='FK'},
       @{n='variante_id'; t='BIGINT'; k='FK'},
       @{n='cantidad'; t='INTEGER'},
       @{n='precio_unitario'; t='NUMERIC(10,2)'},
       @{n='descuento_unitario'; t='NUMERIC(10,2)'},
       @{n='creado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='DEVOLUCION'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='venta_id'; t='BIGINT'; k='FK'},
       @{n='turno_caja_id'; t='BIGINT'; k='FK'},
       @{n='motivo'; t='VARCHAR(200)'},
       @{n='monto'; t='NUMERIC(10,2)'},
       @{n='creado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='DIRECCION_CLIENTE'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='cliente_id'; t='BIGINT'; k='FK'},
       @{n='ciudad_id'; t='INTEGER'; k='FK'},
       @{n='alias'; t='VARCHAR(40)'},
       @{n='direccion'; t='VARCHAR(200)'},
       @{n='referencia'; t='VARCHAR(200)'},
       @{n='predeterminada'; t='BOOLEAN'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='EMPLEADO'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='usuario_id'; t='BIGINT'; k='FK'},
       @{n='sucursal_id'; t='INTEGER'; k='FK'},
       @{n='documento'; t='VARCHAR(20)'},
       @{n='telefono'; t='VARCHAR(20)'},
       @{n='cargo'; t='VARCHAR(30)'},
       @{n='fecha_ingreso'; t='DATE'},
       @{n='fecha_baja'; t='DATE'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='EXISTENCIA'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='variante_id'; t='BIGINT'; k='FK'},
       @{n='sucursal_id'; t='INTEGER'; k='FK'},
       @{n='cantidad_disponible'; t='INTEGER'},
       @{n='cantidad_reservada'; t='INTEGER'},
       @{n='stock_minimo'; t='INTEGER'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='FAVORITO'
     cols=@(
       @{n='cliente_id'; t='BIGINT'; k='PK,FK'},
       @{n='producto_id'; t='BIGINT'; k='PK,FK'},
       @{n='creado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='IMAGEN_PRODUCTO'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='producto_id'; t='BIGINT'; k='FK'},
       @{n='variante_id'; t='BIGINT'; k='FK'},
       @{n='ruta'; t='VARCHAR(255)'},
       @{n='es_principal'; t='BOOLEAN'},
       @{n='es_transparente'; t='BOOLEAN'},
       @{n='es_silueta_generada'; t='BOOLEAN'},
       @{n='orden'; t='SMALLINT'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='MEDIDA_CLIENTE'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='cliente_id'; t='BIGINT'; k='FK'},
       @{n='busto_cm'; t='NUMERIC(5,1)'},
       @{n='cintura_cm'; t='NUMERIC(5,1)'},
       @{n='cadera_cm'; t='NUMERIC(5,1)'},
       @{n='altura_cm'; t='NUMERIC(5,1)'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='MEDIDA_TALLA'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='producto_id'; t='BIGINT'; k='FK'},
       @{n='talla_id'; t='INTEGER'; k='FK'},
       @{n='busto_cm'; t='NUMERIC(5,1)'},
       @{n='cintura_cm'; t='NUMERIC(5,1)'},
       @{n='cadera_cm'; t='NUMERIC(5,1)'},
       @{n='largo_cm'; t='NUMERIC(5,1)'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='MOVIMIENTO_INVENTARIO'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='existencia_id'; t='BIGINT'; k='FK'},
       @{n='tipo'; t='VARCHAR(15)'},
       @{n='cantidad'; t='INTEGER'},
       @{n='motivo'; t='VARCHAR(200)'},
       @{n='proveedor_id'; t='BIGINT'; k='FK'},
       @{n='referencia'; t='VARCHAR(40)'},
       @{n='usuario_id'; t='BIGINT'; k='FK'},
       @{n='creado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='PAGO'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='venta_id'; t='BIGINT'; k='FK'},
       @{n='metodo'; t='VARCHAR(12)'},
       @{n='estado'; t='VARCHAR(12)'},
       @{n='monto'; t='NUMERIC(10,2)'},
       @{n='referencia_externa'; t='VARCHAR(100)'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='PERMISO'
     cols=@(
       @{n='id'; t='SMALLINT'; k='PK'},
       @{n='codigo'; t='VARCHAR(60)'},
       @{n='descripcion'; t='VARCHAR(150)'}
     ) },
  @{ n='PRODUCTO'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='codigo'; t='VARCHAR(30)'},
       @{n='nombre'; t='VARCHAR(120)'},
       @{n='descripcion'; t='VARCHAR(500)'},
       @{n='categoria_id'; t='INTEGER'; k='FK'},
       @{n='proveedor_id'; t='BIGINT'; k='FK'},
       @{n='temporada_id'; t='INTEGER'; k='FK'},
       @{n='coleccion_id'; t='INTEGER'; k='FK'},
       @{n='precio_base'; t='NUMERIC(10,2)'},
       @{n='activo'; t='BOOLEAN'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='PROMOCION'
     cols=@(
       @{n='id'; t='SERIAL'; k='PK'},
       @{n='nombre'; t='VARCHAR(80)'},
       @{n='alcance'; t='VARCHAR(10)'},
       @{n='producto_id'; t='BIGINT'; k='FK'},
       @{n='categoria_id'; t='INTEGER'; k='FK'},
       @{n='temporada_id'; t='INTEGER'; k='FK'},
       @{n='porcentaje'; t='NUMERIC(5,2)'},
       @{n='desde'; t='DATE'},
       @{n='hasta'; t='DATE'},
       @{n='activa'; t='BOOLEAN'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='PROVEEDOR'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='usuario_id'; t='BIGINT'; k='FK'},
       @{n='razon_social'; t='VARCHAR(120)'},
       @{n='identificacion_tributaria'; t='VARCHAR(30)'},
       @{n='contacto'; t='VARCHAR(80)'},
       @{n='telefono'; t='VARCHAR(20)'},
       @{n='correo'; t='VARCHAR(120)'},
       @{n='direccion'; t='VARCHAR(200)'},
       @{n='activo'; t='BOOLEAN'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='RECOMENDACION'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='cliente_id'; t='BIGINT'; k='FK'},
       @{n='generada_en'; t='TIMESTAMPTZ'},
       @{n='motor'; t='VARCHAR(30)'},
       @{n='sugerencias'; t='JSONB'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='RESERVA'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='cliente_id'; t='BIGINT'; k='FK'},
       @{n='sucursal_id'; t='INTEGER'; k='FK'},
       @{n='franja_inicio'; t='TIMESTAMPTZ'},
       @{n='franja_fin'; t='TIMESTAMPTZ'},
       @{n='estado'; t='VARCHAR(10)'},
       @{n='observacion'; t='VARCHAR(200)'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='RESERVA_DETALLE'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='reserva_id'; t='BIGINT'; k='FK'},
       @{n='variante_id'; t='BIGINT'; k='FK'},
       @{n='cantidad'; t='INTEGER'},
       @{n='resultado_prueba'; t='VARCHAR(10)'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='ROL'
     cols=@(
       @{n='id'; t='SMALLINT'; k='PK'},
       @{n='nombre'; t='VARCHAR(30)'},
       @{n='descripcion'; t='VARCHAR(150)'}
     ) },
  @{ n='ROL_PERMISO'
     cols=@(
       @{n='rol_id'; t='SMALLINT'; k='PK,FK'},
       @{n='permiso_id'; t='SMALLINT'; k='PK,FK'}
     ) },
  @{ n='SESION_TOKEN'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='usuario_id'; t='BIGINT'; k='FK'},
       @{n='jti'; t='UUID'},
       @{n='emitido_en'; t='TIMESTAMPTZ'},
       @{n='expira_en'; t='TIMESTAMPTZ'},
       @{n='revocado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='SUCURSAL'
     cols=@(
       @{n='id'; t='SERIAL'; k='PK'},
       @{n='ciudad_id'; t='INTEGER'; k='FK'},
       @{n='nombre'; t='VARCHAR(80)'},
       @{n='direccion'; t='VARCHAR(200)'},
       @{n='telefono'; t='VARCHAR(20)'},
       @{n='horario_apertura'; t='TIME'},
       @{n='horario_cierre'; t='TIME'},
       @{n='capacidad_vestidores'; t='SMALLINT'},
       @{n='activa'; t='BOOLEAN'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='TALLA'
     cols=@(
       @{n='id'; t='SERIAL'; k='PK'},
       @{n='tipo_prenda'; t='VARCHAR(30)'},
       @{n='codigo'; t='VARCHAR(10)'},
       @{n='orden'; t='SMALLINT'},
       @{n='activa'; t='BOOLEAN'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='TEMPORADA'
     cols=@(
       @{n='id'; t='SERIAL'; k='PK'},
       @{n='nombre'; t='VARCHAR(60)'},
       @{n='descripcion'; t='VARCHAR(200)'},
       @{n='fecha_inicio'; t='DATE'},
       @{n='fecha_fin'; t='DATE'},
       @{n='activa'; t='BOOLEAN'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='TOKEN_RECUPERACION'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='usuario_id'; t='BIGINT'; k='FK'},
       @{n='hash_token'; t='VARCHAR(64)'},
       @{n='solicitado_en'; t='TIMESTAMPTZ'},
       @{n='expira_en'; t='TIMESTAMPTZ'},
       @{n='usado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='TRANSACCION_PASARELA'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='pago_id'; t='BIGINT'; k='FK'},
       @{n='evento_id'; t='VARCHAR(100)'},
       @{n='tipo_evento'; t='VARCHAR(50)'},
       @{n='firma_valida'; t='BOOLEAN'},
       @{n='carga_util'; t='TEXT'},
       @{n='recibido_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='TURNO_CAJA'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='caja_id'; t='INTEGER'; k='FK'},
       @{n='usuario_id'; t='BIGINT'; k='FK'},
       @{n='abierto_en'; t='TIMESTAMPTZ'},
       @{n='cerrado_en'; t='TIMESTAMPTZ'},
       @{n='monto_apertura'; t='NUMERIC(10,2)'},
       @{n='monto_cierre'; t='NUMERIC(10,2)'},
       @{n='monto_esperado'; t='NUMERIC(10,2)'}
     ) },
  @{ n='USUARIO'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='correo'; t='VARCHAR(120)'},
       @{n='hash_contrasena'; t='VARCHAR(255)'},
       @{n='nombres'; t='VARCHAR(80)'},
       @{n='apellidos'; t='VARCHAR(80)'},
       @{n='rol_id'; t='SMALLINT'; k='FK'},
       @{n='activo'; t='BOOLEAN'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='VARIANTE_PRODUCTO'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='producto_id'; t='BIGINT'; k='FK'},
       @{n='talla_id'; t='INTEGER'; k='FK'},
       @{n='color_id'; t='INTEGER'; k='FK'},
       @{n='sku'; t='VARCHAR(40)'},
       @{n='precio'; t='NUMERIC(10,2)'},
       @{n='activa'; t='BOOLEAN'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='VENTA'
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='codigo'; t='VARCHAR(20)'},
       @{n='canal'; t='VARCHAR(12)'},
       @{n='estado'; t='VARCHAR(20)'},
       @{n='cliente_id'; t='BIGINT'; k='FK'},
       @{n='sucursal_id'; t='INTEGER'; k='FK'},
       @{n='turno_caja_id'; t='BIGINT'; k='FK'},
       @{n='reserva_id'; t='BIGINT'; k='FK'},
       @{n='modalidad_entrega'; t='VARCHAR(10)'},
       @{n='direccion_id'; t='BIGINT'; k='FK'},
       @{n='metodo_pago'; t='VARCHAR(20)'},
       @{n='subtotal'; t='NUMERIC(10,2)'},
       @{n='descuento'; t='NUMERIC(10,2)'},
       @{n='total'; t='NUMERIC(10,2)'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) }
)

$RELACIONES_C3 = @(
  @{ o='CAJA'; v='REGISTRA'; d='TURNO_CAJA'; co='1'; cd='0..*' },
  @{ o='CARRITO'; v='SE_DESGLOSA_EN'; d='CARRITO_DETALLE'; co='1'; cd='0..*' },
  @{ o='CATEGORIA'; v='SE_SUBDIVIDE_EN'; d='CATEGORIA'; co='0..1'; cd='0..*' },
  @{ o='CATEGORIA'; v='SE_PREFIERE_EN'; d='CLIENTE_CATEGORIA'; co='1'; cd='0..*' },
  @{ o='CATEGORIA'; v='CLASIFICA'; d='PRODUCTO'; co='1'; cd='0..*' },
  @{ o='CATEGORIA'; v='AGRUPA_PROMOCION'; d='PROMOCION'; co='0..1'; cd='0..*' },
  @{ o='CIUDAD'; v='UBICA'; d='DIRECCION_CLIENTE'; co='1'; cd='0..*' },
  @{ o='CIUDAD'; v='ALOJA'; d='SUCURSAL'; co='1'; cd='0..*' },
  @{ o='CLIENTE'; v='TIENE'; d='CARRITO'; co='1'; cd='0..1' },
  @{ o='CLIENTE'; v='PREFIERE_EN'; d='CLIENTE_CATEGORIA'; co='1'; cd='0..*' },
  @{ o='CLIENTE'; v='REGISTRA'; d='DIRECCION_CLIENTE'; co='1'; cd='0..*' },
  @{ o='CLIENTE'; v='MARCA_EN'; d='FAVORITO'; co='1'; cd='0..*' },
  @{ o='CLIENTE'; v='SE_MIDE_EN'; d='MEDIDA_CLIENTE'; co='1'; cd='0..1' },
  @{ o='CLIENTE'; v='RECIBE'; d='RECOMENDACION'; co='1'; cd='0..1' },
  @{ o='CLIENTE'; v='REALIZA'; d='RESERVA'; co='1'; cd='0..*' },
  @{ o='CLIENTE'; v='COMPRA_EN'; d='VENTA'; co='0..1'; cd='0..*' },
  @{ o='COLECCION'; v='AGRUPA'; d='PRODUCTO'; co='0..1'; cd='0..*' },
  @{ o='COLOR'; v='TINE'; d='VARIANTE_PRODUCTO'; co='1'; cd='0..*' },
  @{ o='DEVOLUCION'; v='SE_DESGLOSA_EN'; d='DETALLE_DEVOLUCION'; co='1'; cd='0..*' },
  @{ o='DIRECCION_CLIENTE'; v='ES_DESTINO_DE'; d='VENTA'; co='0..1'; cd='0..*' },
  @{ o='EXISTENCIA'; v='SE_EXPLICA_POR'; d='MOVIMIENTO_INVENTARIO'; co='1'; cd='0..*' },
  @{ o='PAGO'; v='SE_NOTIFICA_EN'; d='TRANSACCION_PASARELA'; co='0..1'; cd='0..*' },
  @{ o='PERMISO'; v='SE_OTORGA_EN'; d='ROL_PERMISO'; co='1'; cd='0..*' },
  @{ o='PRODUCTO'; v='SE_MARCA_EN'; d='FAVORITO'; co='1'; cd='0..*' },
  @{ o='PRODUCTO'; v='SE_ILUSTRA_CON'; d='IMAGEN_PRODUCTO'; co='1'; cd='0..*' },
  @{ o='PRODUCTO'; v='SE_TABULA_EN'; d='MEDIDA_TALLA'; co='1'; cd='0..*' },
  @{ o='PRODUCTO'; v='SE_PROMOCIONA_EN'; d='PROMOCION'; co='0..1'; cd='0..*' },
  @{ o='PRODUCTO'; v='SE_OFRECE_COMO'; d='VARIANTE_PRODUCTO'; co='1'; cd='0..*' },
  @{ o='PROVEEDOR'; v='ANUNCIA_EN'; d='ABASTECIMIENTO'; co='1'; cd='0..*' },
  @{ o='PROVEEDOR'; v='ABASTECE_EN'; d='MOVIMIENTO_INVENTARIO'; co='0..1'; cd='0..*' },
  @{ o='PROVEEDOR'; v='ABASTECE'; d='PRODUCTO'; co='0..1'; cd='0..*' },
  @{ o='RESERVA'; v='SE_DETALLA_EN'; d='RESERVA_DETALLE'; co='1'; cd='0..*' },
  @{ o='RESERVA'; v='SE_CONCRETA_EN'; d='VENTA'; co='0..1'; cd='0..1' },
  @{ o='ROL'; v='SE_HABILITA_EN'; d='ROL_PERMISO'; co='1'; cd='0..*' },
  @{ o='ROL'; v='DEFINE'; d='USUARIO'; co='1'; cd='0..*' },
  @{ o='SUCURSAL'; v='TIENE_CAJA'; d='CAJA'; co='1'; cd='0..*' },
  @{ o='SUCURSAL'; v='EMPLEA_A'; d='EMPLEADO'; co='1'; cd='0..*' },
  @{ o='SUCURSAL'; v='ALBERGA'; d='EXISTENCIA'; co='1'; cd='0..*' },
  @{ o='SUCURSAL'; v='ATIENDE'; d='RESERVA'; co='1'; cd='0..*' },
  @{ o='SUCURSAL'; v='VENDE_EN'; d='VENTA'; co='1'; cd='0..*' },
  @{ o='TALLA'; v='DIMENSIONA_EN'; d='MEDIDA_TALLA'; co='1'; cd='0..*' },
  @{ o='TALLA'; v='DIMENSIONA'; d='VARIANTE_PRODUCTO'; co='1'; cd='0..*' },
  @{ o='TEMPORADA'; v='CONTIENE'; d='COLECCION'; co='1'; cd='0..*' },
  @{ o='TEMPORADA'; v='ENMARCA'; d='PRODUCTO'; co='0..1'; cd='0..*' },
  @{ o='TEMPORADA'; v='ENMARCA_PROMOCION'; d='PROMOCION'; co='0..1'; cd='0..*' },
  @{ o='TURNO_CAJA'; v='REGISTRA_DEVOLUCION'; d='DEVOLUCION'; co='1'; cd='0..*' },
  @{ o='TURNO_CAJA'; v='REGISTRA_VENTA'; d='VENTA'; co='0..1'; cd='0..*' },
  @{ o='USUARIO'; v='SE_AUDITA_EN'; d='BITACORA'; co='0..1'; cd='0..*' },
  @{ o='USUARIO'; v='ES'; d='CLIENTE'; co='1'; cd='0..1' },
  @{ o='USUARIO'; v='ES_EMPLEADO'; d='EMPLEADO'; co='1'; cd='0..1' },
  @{ o='USUARIO'; v='ORIGINA'; d='MOVIMIENTO_INVENTARIO'; co='0..1'; cd='0..*' },
  @{ o='USUARIO'; v='PUEDE_SER'; d='PROVEEDOR'; co='0..1'; cd='0..1' },
  @{ o='USUARIO'; v='INICIA_SESION_EN'; d='SESION_TOKEN'; co='1'; cd='0..*' },
  @{ o='USUARIO'; v='RECUPERA_CON'; d='TOKEN_RECUPERACION'; co='1'; cd='0..*' },
  @{ o='USUARIO'; v='ABRE'; d='TURNO_CAJA'; co='1'; cd='0..*' },
  @{ o='VARIANTE_PRODUCTO'; v='SE_REPONE_EN'; d='ABASTECIMIENTO'; co='1'; cd='0..*' },
  @{ o='VARIANTE_PRODUCTO'; v='SE_AGREGA_EN'; d='CARRITO_DETALLE'; co='1'; cd='0..*' },
  @{ o='VARIANTE_PRODUCTO'; v='SE_DEVUELVE_EN'; d='DETALLE_DEVOLUCION'; co='1'; cd='0..*' },
  @{ o='VARIANTE_PRODUCTO'; v='SE_VENDE_EN'; d='DETALLE_VENTA'; co='1'; cd='0..*' },
  @{ o='VARIANTE_PRODUCTO'; v='SE_ALMACENA_EN'; d='EXISTENCIA'; co='1'; cd='0..*' },
  @{ o='VARIANTE_PRODUCTO'; v='SE_MUESTRA_EN'; d='IMAGEN_PRODUCTO'; co='0..1'; cd='0..*' },
  @{ o='VARIANTE_PRODUCTO'; v='SE_APARTA_EN'; d='RESERVA_DETALLE'; co='1'; cd='0..*' },
  @{ o='VENTA'; v='SE_ACREDITA_CON'; d='COMPROBANTE'; co='1'; cd='0..1' },
  @{ o='VENTA'; v='SE_DETALLA_EN'; d='DETALLE_VENTA'; co='1'; cd='0..*' },
  @{ o='VENTA'; v='SE_REVIERTE_EN'; d='DEVOLUCION'; co='1'; cd='0..*' },
  @{ o='VENTA'; v='SE_SALDA_CON'; d='PAGO'; co='1'; cd='0..1' }
)
