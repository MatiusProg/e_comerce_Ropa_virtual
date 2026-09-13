# GENERADO por scripts/gen-dominio-3-3-1.py --- NO editar a mano.
# Las columnas, sus tipos y los estereotipos PK/FK salen de information_schema
# de la base construida con las migraciones. Las cardinalidades salen de lo
# que la base OBLIGA --- NOT NULL y UNIQUE ---, no de la prosa.

$TABLAS_C2 = @(
  @{ n='PRODUCTO'; nuevo=$true
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
  @{ n='VARIANTE_PRODUCTO'; nuevo=$true
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
  @{ n='IMAGEN_PRODUCTO'; nuevo=$true
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='producto_id'; t='BIGINT'; k='FK'},
       @{n='variante_id'; t='BIGINT'; k='FK'},
       @{n='ruta'; t='VARCHAR(255)'},
       @{n='es_principal'; t='BOOLEAN'},
       @{n='es_transparente'; t='BOOLEAN'},
       @{n='orden'; t='SMALLINT'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='EXISTENCIA'; nuevo=$true
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='variante_id'; t='BIGINT'; k='FK'},
       @{n='sucursal_id'; t='INTEGER'; k='FK'},
       @{n='cantidad_disponible'; t='INTEGER'},
       @{n='cantidad_reservada'; t='INTEGER'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'},
       @{n='stock_minimo'; t='INTEGER'}
     ) },
  @{ n='MOVIMIENTO_INVENTARIO'; nuevo=$true
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
  @{ n='RESERVA'; nuevo=$true
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
  @{ n='RESERVA_DETALLE'; nuevo=$true
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='reserva_id'; t='BIGINT'; k='FK'},
       @{n='variante_id'; t='BIGINT'; k='FK'},
       @{n='cantidad'; t='INTEGER'},
       @{n='resultado_prueba'; t='VARCHAR(10)'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='CLIENTE_CATEGORIA'; nuevo=$true
     cols=@(
       @{n='cliente_id'; t='BIGINT'; k='PK,FK'},
       @{n='categoria_id'; t='INTEGER'; k='PK,FK'}
     ) },
  @{ n='CATEGORIA'; nuevo=$false
     cols=@(
       @{n='id'; t='SERIAL'; k='PK'},
       @{n='categoria_padre_id'; t='INTEGER'; k='FK'},
       @{n='nombre'; t='VARCHAR(60)'},
       @{n='orden'; t='SMALLINT'},
       @{n='activa'; t='BOOLEAN'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='PROVEEDOR'; nuevo=$false
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
  @{ n='TEMPORADA'; nuevo=$false
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
  @{ n='COLECCION'; nuevo=$false
     cols=@(
       @{n='id'; t='SERIAL'; k='PK'},
       @{n='temporada_id'; t='INTEGER'; k='FK'},
       @{n='nombre'; t='VARCHAR(60)'},
       @{n='descripcion'; t='VARCHAR(200)'},
       @{n='activa'; t='BOOLEAN'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='TALLA'; nuevo=$false
     cols=@(
       @{n='id'; t='SERIAL'; k='PK'},
       @{n='tipo_prenda'; t='VARCHAR(30)'},
       @{n='codigo'; t='VARCHAR(10)'},
       @{n='orden'; t='SMALLINT'},
       @{n='activa'; t='BOOLEAN'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='COLOR'; nuevo=$false
     cols=@(
       @{n='id'; t='SERIAL'; k='PK'},
       @{n='nombre'; t='VARCHAR(40)'},
       @{n='hexadecimal'; t='CHARACTER'},
       @{n='activo'; t='BOOLEAN'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='SUCURSAL'; nuevo=$false
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
  @{ n='CLIENTE'; nuevo=$false
     cols=@(
       @{n='id'; t='BIGSERIAL'; k='PK'},
       @{n='usuario_id'; t='BIGINT'; k='FK'},
       @{n='documento'; t='VARCHAR(20)'},
       @{n='telefono'; t='VARCHAR(20)'},
       @{n='talla_superior'; t='VARCHAR(10)'},
       @{n='talla_inferior'; t='VARCHAR(10)'},
       @{n='talla_calzado'; t='VARCHAR(10)'},
       @{n='creado_en'; t='TIMESTAMPTZ'},
       @{n='actualizado_en'; t='TIMESTAMPTZ'}
     ) },
  @{ n='USUARIO'; nuevo=$false
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
     ) }
)

$RELACIONES_C2 = @(
  @{ o='CATEGORIA'; v='SE_SUBDIVIDE_EN'; d='CATEGORIA'; co='0..1'; cd='0..*' },
  @{ o='USUARIO'; v='ES'; d='CLIENTE'; co='1'; cd='0..1' },
  @{ o='CATEGORIA'; v='SE_PREFIERE_EN'; d='CLIENTE_CATEGORIA'; co='1'; cd='0..*' },
  @{ o='CLIENTE'; v='PREFIERE_EN'; d='CLIENTE_CATEGORIA'; co='1'; cd='0..*' },
  @{ o='TEMPORADA'; v='CONTIENE'; d='COLECCION'; co='1'; cd='0..*' },
  @{ o='SUCURSAL'; v='ALBERGA'; d='EXISTENCIA'; co='1'; cd='0..*' },
  @{ o='VARIANTE_PRODUCTO'; v='SE_ALMACENA_EN'; d='EXISTENCIA'; co='1'; cd='0..*' },
  @{ o='PRODUCTO'; v='SE_ILUSTRA_CON'; d='IMAGEN_PRODUCTO'; co='1'; cd='0..*' },
  @{ o='VARIANTE_PRODUCTO'; v='SE_MUESTRA_EN'; d='IMAGEN_PRODUCTO'; co='0..1'; cd='0..*' },
  @{ o='EXISTENCIA'; v='SE_EXPLICA_POR'; d='MOVIMIENTO_INVENTARIO'; co='1'; cd='0..*' },
  @{ o='PROVEEDOR'; v='ABASTECE_EN'; d='MOVIMIENTO_INVENTARIO'; co='0..1'; cd='0..*' },
  @{ o='USUARIO'; v='ORIGINA'; d='MOVIMIENTO_INVENTARIO'; co='0..1'; cd='0..*' },
  @{ o='CATEGORIA'; v='CLASIFICA'; d='PRODUCTO'; co='1'; cd='0..*' },
  @{ o='COLECCION'; v='AGRUPA'; d='PRODUCTO'; co='0..1'; cd='0..*' },
  @{ o='PROVEEDOR'; v='ABASTECE'; d='PRODUCTO'; co='0..1'; cd='0..*' },
  @{ o='TEMPORADA'; v='ENMARCA'; d='PRODUCTO'; co='0..1'; cd='0..*' },
  @{ o='USUARIO'; v='PUEDE_SER'; d='PROVEEDOR'; co='0..1'; cd='0..1' },
  @{ o='CLIENTE'; v='REALIZA'; d='RESERVA'; co='1'; cd='0..*' },
  @{ o='SUCURSAL'; v='ATIENDE'; d='RESERVA'; co='1'; cd='0..*' },
  @{ o='RESERVA'; v='SE_DETALLA_EN'; d='RESERVA_DETALLE'; co='1'; cd='0..*' },
  @{ o='VARIANTE_PRODUCTO'; v='SE_APARTA_EN'; d='RESERVA_DETALLE'; co='1'; cd='0..*' },
  @{ o='COLOR'; v='TINE'; d='VARIANTE_PRODUCTO'; co='1'; cd='0..*' },
  @{ o='PRODUCTO'; v='SE_OFRECE_COMO'; d='VARIANTE_PRODUCTO'; co='1'; cd='0..*' },
  @{ o='TALLA'; v='DIMENSIONA'; d='VARIANTE_PRODUCTO'; co='1'; cd='0..*' }
)
