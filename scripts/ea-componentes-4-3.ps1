param(
    # Borra el paquete 4.3 entero y lo vuelve a generar.
    [switch]$Rehacer
)

# =========================================================================
# CAP. 4 - 4.3 Diagramas de Componentes por Subsistema.
#
# ---- DE DONDE SALE ESTE FORMATO ----
# De los ejemplos de catedra 'CICLO 4.eapx' y 'CICLO 4 PROY_GRUP.eapx'. Uno
# por paquete, con el nombre codificando la trazabilidad: Subsistema N es el
# paquete PN del analisis 2.1. Tres bandas horizontales, todas de elementos
# Component, diferenciadas solo por el estereotipo:
#
#     «FORM»   pantallas del frontend
#        |     Assembly  (el conector de ensamblado de UML 2.x)
#     «CLASS»  endpoints del backend
#        |     Dependency
#     «TABLA»  tablas de la base
#
# ---- TRES COSAS EN LAS QUE ESTE DIAGRAMA SE APARTA DEL EJEMPLO ----
#
# 1. LOS ESTEREOTIPOS SON DE VERDAD. En el archivo grupal de catedra estan
#    tecleados a mano como texto --- '<CLASS>', y '< FORM>' con un espacio de
#    sobra ---, no como estereotipos. Aqui se asignan por Stereotype y
#    StereotypeEx, asi que EA los dibuja entre guillemets.
#
# 2. LA BANDA «CLASS» VA EN DOS FILAS, alternando. Con 27 endpoints en una
#    sola fila el diagrama pasaria de los 4000 px y el texto no se leeria al
#    exportarlo. Alternando, cada grupo ocupa la mitad de columnas y el ancho
#    queda en el orden del ejemplo de catedra.
#
# 3. CADA «CLASS» QUEDA DEBAJO DE SU «FORM». Los endpoints se agrupan por la
#    pantalla que los llama, y la pantalla se centra sobre su grupo. Asi las
#    lineas de Assembly son cortas y verticales, y no se cruzan.
#
# El color sigue la convencion del 4.2: verde, implementado; azul, tabla que
# pertenece a otro subsistema.
#
# ADITIVO: abre el modelo y solo agrega lo que falta.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

# ---- Constantes de dibujo ----
$COL_W    = 160
$COL_STEP = 180
$Y_FORM   = -60;  $H_FORM  = 62
$Y_CLS_A  = -240; $Y_CLS_B = -345; $H_CLS = 62
$Y_TABLA  = -520; $H_TABLA = 56
$TAB_W    = 170;  $TAB_STEP = 200

$VERDE = 14086358   # RGB 214,240,214 - implementado
$AZUL  = 16443094   # RGB 214,230,250 - tabla de otro subsistema

# =========================================================================
# LOS SUBSISTEMAS. Solo los tres que estan implementados: P1, P2 y P3 son los
# unicos con router montado en main.py al 05/09/2026.
#
# grupos : cada pantalla «FORM» con los endpoints «CLASS» que llama.
#          Los endpoints van en el orden en que se leen en router.py.
# tablas : la banda de abajo. propia=$false marca la que es de otro paquete.
# =========================================================================

$SUBSISTEMAS = @(

# ------------------------------------------------------------------ P1 --
@{
  nombre = '4.3 Subsistema 1 — Seguridad y Usuarios'
  nota   = "SUBSISTEMA 1 = PAQUETE P1 del análisis 2.1`n`nCU-01 Registrar cliente, CU-02 Iniciar y cerrar sesión,`nCU-03 Gestionar usuarios y roles, CU-04 Perfil del cliente.`n`nBackend: backend/app/modules/seguridad`nFrontend: features/auth, features/cliente/perfil,`n          features/admin/usuarios`n`nVerde: implementado. Azul: tabla de otro subsistema.`n`nLas tablas permiso y rol_permiso existen en el esquema`npero todavía ningún componente las usa: solo las declara`nseguridad/models.py."
  grupos = @(
    @{ form = 'Registro'; nf = 'frontend-web/src/app/features/auth/registro'; clases = @(
        @{ n = 'registrar_cliente'; nc = 'POST /api/v1/auth/registro'; tablas = @('usuario','cliente','rol') }
      )},
    @{ form = 'Login'; nf = 'frontend-web/src/app/features/auth/login, con AuthService'; clases = @(
        @{ n = 'iniciar_sesion';      nc = 'POST /api/v1/auth/login';  tablas = @('usuario','sesion_token') },
        @{ n = 'cerrar_sesion';       nc = 'POST /api/v1/auth/logout'; tablas = @('sesion_token') },
        @{ n = 'usuario_autenticado'; nc = 'GET /api/v1/auth/yo';      tablas = @('usuario') }
      )},
    @{ form = 'Usuarios'; nf = 'frontend-web/src/app/features/admin/usuarios/usuarios.ts'; clases = @(
        @{ n = 'listar_usuarios'; nc = 'GET /api/v1/usuarios';                       tablas = @('usuario') },
        @{ n = 'obtener_usuario'; nc = 'GET /api/v1/usuarios/{id}';                  tablas = @('usuario') },
        @{ n = 'cambiar_estado';  nc = 'PATCH /api/v1/usuarios/{id}/estado';         tablas = @('usuario','sesion_token') },
        @{ n = 'eliminar_usuario';nc = 'DELETE /api/v1/usuarios/{id}';               tablas = @('usuario') },
        @{ n = 'listar_roles';    nc = 'GET /api/v1/auth/roles';                     tablas = @('rol') }
      )},
    @{ form = 'UsuarioFormulario'; nf = 'frontend-web/src/app/features/admin/usuarios/usuario-formulario.ts'; clases = @(
        @{ n = 'crear_usuario';  nc = 'POST /api/v1/usuarios. Si el rol exige sucursal crea también la ficha de empleado, en la misma transacción.'; tablas = @('usuario','empleado') },
        @{ n = 'editar_usuario'; nc = 'PATCH /api/v1/usuarios/{id}. Al cambiar el rol revoca las sesiones vigentes.'; tablas = @('usuario','sesion_token') }
      )},
    @{ form = 'Perfil'; nf = 'frontend-web/src/app/features/cliente/perfil/perfil.ts'; clases = @(
        @{ n = 'obtener_perfil';        nc = 'GET /api/v1/perfil';                                        tablas = @('cliente','direccion_cliente') },
        @{ n = 'editar_perfil';         nc = 'PATCH /api/v1/perfil';                                      tablas = @('cliente') },
        @{ n = 'marcar_predeterminada'; nc = 'PATCH /api/v1/perfil/direcciones/{id}/predeterminada';      tablas = @('direccion_cliente') },
        @{ n = 'eliminar_direccion';    nc = 'DELETE /api/v1/perfil/direcciones/{id}';                    tablas = @('direccion_cliente') }
      )},
    @{ form = 'DireccionFormulario'; nf = 'frontend-web/src/app/features/cliente/perfil/direccion-formulario.ts'; clases = @(
        @{ n = 'agregar_direccion'; nc = 'POST /api/v1/perfil/direcciones'; tablas = @('direccion_cliente','ciudad') }
      )},
    @{ form = 'CambioContrasena'; nf = 'frontend-web/src/app/features/cliente/perfil/cambio-contrasena.ts'; clases = @(
        @{ n = 'cambiar_contrasena'; nc = 'PUT /api/v1/perfil/contrasena. Revoca las sesiones abiertas.'; tablas = @('usuario','sesion_token') }
      )},
    @{ form = $null; clases = @(
        @{ n = 'seed.py'; nc = 'backend/app/db/seed.py. No es un endpoint: siembra los roles y el administrador inicial al arrancar.'; tablas = @('rol','usuario') }
      )}
  )
  tablas = @(
    @{ n = 'usuario';           propia = $true  },
    @{ n = 'rol';               propia = $true  },
    @{ n = 'cliente';           propia = $true  },
    @{ n = 'direccion_cliente'; propia = $true  },
    @{ n = 'sesion_token';      propia = $true  },
    @{ n = 'empleado';          propia = $false },
    @{ n = 'ciudad';            propia = $false }
  )
},

# ------------------------------------------------------------------ P2 --
@{
  nombre = '4.3 Subsistema 2 — Organización'
  nota   = "SUBSISTEMA 2 = PAQUETE P2 del análisis 2.1`n`nCU-05 Gestionar ciudades y sucursales,`nCU-06 Gestionar empleados, CU-07 Gestionar proveedores.`n`nBackend: backend/app/modules/organizacion`nFrontend: features/admin/ciudades, sucursales,`n          empleados, proveedores`n`nVerde: implementado. Azul: tabla de otro subsistema.`n`nGET /organizacion/empleados/cargos no aparece: devuelve`nuna constante de schemas.py, no consulta ninguna tabla."
  grupos = @(
    @{ form = 'Ciudades'; nf = 'features/admin/ciudades/ciudades.ts'; clases = @(
        @{ n = 'listar_ciudades';  nc = 'GET /api/v1/organizacion/ciudades';         tablas = @('ciudad') },
        @{ n = 'obtener_ciudad';   nc = 'GET /api/v1/organizacion/ciudades/{id}';    tablas = @('ciudad') },
        @{ n = 'eliminar_ciudad';  nc = 'DELETE /api/v1/organizacion/ciudades/{id}. No deja borrar si la ciudad tiene sucursales.'; tablas = @('ciudad','sucursal') }
      )},
    @{ form = 'CiudadFormulario'; nf = 'features/admin/ciudades/ciudad-formulario.ts'; clases = @(
        @{ n = 'crear_ciudad';  nc = 'POST /api/v1/organizacion/ciudades';        tablas = @('ciudad') },
        @{ n = 'editar_ciudad'; nc = 'PATCH /api/v1/organizacion/ciudades/{id}';  tablas = @('ciudad') }
      )},
    @{ form = 'Sucursales'; nf = 'features/admin/sucursales/sucursales.ts'; clases = @(
        @{ n = 'listar_sucursales';       nc = 'GET /api/v1/organizacion/sucursales';               tablas = @('sucursal','ciudad') },
        @{ n = 'obtener_sucursal';        nc = 'GET /api/v1/organizacion/sucursales/{id}';          tablas = @('sucursal') },
        @{ n = 'cambiar_estado_sucursal'; nc = 'PATCH /api/v1/organizacion/sucursales/{id}/estado. La sucursal no se borra, se desactiva.'; tablas = @('sucursal') }
      )},
    @{ form = 'SucursalFormulario'; nf = 'features/admin/sucursales/sucursal-formulario.ts'; clases = @(
        @{ n = 'crear_sucursal';  nc = 'POST /api/v1/organizacion/sucursales';       tablas = @('sucursal') },
        @{ n = 'editar_sucursal'; nc = 'PATCH /api/v1/organizacion/sucursales/{id}'; tablas = @('sucursal') }
      )},
    @{ form = 'Empleados'; nf = 'features/admin/empleados/empleados.ts'; clases = @(
        @{ n = 'listar_empleados'; nc = 'GET /api/v1/organizacion/empleados';                tablas = @('empleado','sucursal') },
        @{ n = 'obtener_empleado'; nc = 'GET /api/v1/organizacion/empleados/{id}';           tablas = @('empleado') },
        @{ n = 'dar_de_baja';      nc = 'PATCH /api/v1/organizacion/empleados/{id}/baja. Baja lógica: llena fecha_baja y desactiva la cuenta.'; tablas = @('empleado','usuario') }
      )},
    @{ form = 'EmpleadoFormulario'; nf = 'features/admin/empleados/empleado-formulario.ts'; clases = @(
        @{ n = 'crear_empleado';              nc = 'POST /api/v1/organizacion/empleados. Vincula un usuario existente o crea uno nuevo, en la misma transacción.'; tablas = @('empleado','usuario','sucursal','rol') },
        @{ n = 'editar_empleado';             nc = 'PATCH /api/v1/organizacion/empleados/{id}';                   tablas = @('empleado','usuario') },
        @{ n = 'listar_usuarios_vinculables'; nc = 'GET /api/v1/organizacion/empleados/usuarios-vinculables';     tablas = @('usuario') }
      )},
    @{ form = 'Proveedores'; nf = 'features/admin/proveedores/proveedores.ts'; clases = @(
        @{ n = 'listar_proveedores';       nc = 'GET /api/v1/organizacion/proveedores';                tablas = @('proveedor') },
        @{ n = 'obtener_proveedor';        nc = 'GET /api/v1/organizacion/proveedores/{id}';           tablas = @('proveedor') },
        @{ n = 'cambiar_estado_proveedor'; nc = 'PATCH /api/v1/organizacion/proveedores/{id}/estado';  tablas = @('proveedor') }
      )},
    @{ form = 'ProveedorFormulario'; nf = 'features/admin/proveedores/proveedor-formulario.ts'; clases = @(
        @{ n = 'crear_proveedor';  nc = 'POST /api/v1/organizacion/proveedores';        tablas = @('proveedor') },
        @{ n = 'editar_proveedor'; nc = 'PATCH /api/v1/organizacion/proveedores/{id}';  tablas = @('proveedor') }
      )},
    @{ form = 'AccesoFormulario'; nf = 'features/admin/proveedores/acceso-formulario.ts'; clases = @(
        @{ n = 'habilitar_acceso'; nc = 'POST /api/v1/organizacion/proveedores/{id}/acceso. Le crea una cuenta con rol PROVEEDOR.'; tablas = @('proveedor','usuario','rol') }
      )},
    @{ form = $null; clases = @(
        @{ n = 'mi_ficha'; nc = 'GET /api/v1/organizacion/mi-ficha. Es el endpoint del rol PROVEEDOR; su pantalla todavía no existe en el frontend.'; tablas = @('proveedor') }
      )}
  )
  tablas = @(
    @{ n = 'ciudad';    propia = $true  },
    @{ n = 'sucursal';  propia = $true  },
    @{ n = 'empleado';  propia = $true  },
    @{ n = 'proveedor'; propia = $true  },
    @{ n = 'usuario';   propia = $false },
    @{ n = 'rol';       propia = $false }
  )
},

# ------------------------------------------------------------------ P3 --
@{
  nombre = '4.3 Subsistema 3 — Catálogo'
  nota   = "SUBSISTEMA 3 = PAQUETE P3 del análisis 2.1`n`nCU-08 Gestionar categorías, tallas y colores,`nCU-09 Gestionar temporadas y colecciones.`n`nBackend: backend/app/modules/catalogo`nFrontend: features/admin/maestros, features/admin/temporadas`n`nVerde: implementado.`n`nMaestros es una sola pantalla con tres pestañas, por eso`nconcentra diez endpoints. Es el subsistema más cerrado:`nninguna de sus cinco tablas es de otro paquete."
  grupos = @(
    @{ form = 'Maestros'; nf = 'features/admin/maestros/maestros.ts. Una pantalla con tres pestañas: categorías, tallas y colores.'; clases = @(
        @{ n = 'listar_categorias';        nc = 'GET /api/v1/catalogo/categorias. Devuelve el árbol ya armado.'; tablas = @('categoria') },
        @{ n = 'cambiar_estado_categoria'; nc = 'PATCH /api/v1/catalogo/categorias/{id}/estado';                 tablas = @('categoria') },
        @{ n = 'eliminar_categoria';       nc = 'DELETE /api/v1/catalogo/categorias/{id}. No deja borrar si tiene subcategorías.'; tablas = @('categoria') },
        @{ n = 'listar_tallas';            nc = 'GET /api/v1/catalogo/tallas';        tablas = @('talla') },
        @{ n = 'listar_tipos_de_prenda';   nc = 'GET /api/v1/catalogo/tallas/tipos';  tablas = @('talla') },
        @{ n = 'cambiar_estado_talla';     nc = 'PATCH /api/v1/catalogo/tallas/{id}/estado';   tablas = @('talla') },
        @{ n = 'eliminar_talla';           nc = 'DELETE /api/v1/catalogo/tallas/{id}';         tablas = @('talla') },
        @{ n = 'listar_colores';           nc = 'GET /api/v1/catalogo/colores';                tablas = @('color') },
        @{ n = 'cambiar_estado_color';     nc = 'PATCH /api/v1/catalogo/colores/{id}/estado';  tablas = @('color') },
        @{ n = 'eliminar_color';           nc = 'DELETE /api/v1/catalogo/colores/{id}';        tablas = @('color') }
      )},
    @{ form = 'CategoriaFormulario'; nf = 'features/admin/maestros/categoria-formulario.ts'; clases = @(
        @{ n = 'crear_categoria';  nc = 'POST /api/v1/catalogo/categorias';        tablas = @('categoria') },
        @{ n = 'editar_categoria'; nc = 'PATCH /api/v1/catalogo/categorias/{id}. Comprueba con una consulta recursiva que el padre nuevo no sea un descendiente.'; tablas = @('categoria') }
      )},
    @{ form = 'TallaFormulario'; nf = 'features/admin/maestros/talla-formulario.ts'; clases = @(
        @{ n = 'crear_talla';  nc = 'POST /api/v1/catalogo/tallas';       tablas = @('talla') },
        @{ n = 'editar_talla'; nc = 'PATCH /api/v1/catalogo/tallas/{id}'; tablas = @('talla') }
      )},
    @{ form = 'ColorFormulario'; nf = 'features/admin/maestros/color-formulario.ts'; clases = @(
        @{ n = 'crear_color';  nc = 'POST /api/v1/catalogo/colores';       tablas = @('color') },
        @{ n = 'editar_color'; nc = 'PATCH /api/v1/catalogo/colores/{id}'; tablas = @('color') }
      )},
    @{ form = 'Temporadas'; nf = 'features/admin/temporadas/temporadas.ts'; clases = @(
        @{ n = 'listar_temporadas';         nc = 'GET /api/v1/catalogo/temporadas';                    tablas = @('temporada') },
        @{ n = 'obtener_temporada';         nc = 'GET /api/v1/catalogo/temporadas/{id}';               tablas = @('temporada') },
        @{ n = 'cambiar_estado_temporada';  nc = 'PATCH /api/v1/catalogo/temporadas/{id}/estado';      tablas = @('temporada') },
        @{ n = 'eliminar_temporada';        nc = 'DELETE /api/v1/catalogo/temporadas/{id}. No deja borrar si ya tiene colecciones.'; tablas = @('temporada','coleccion') },
        @{ n = 'listar_colecciones';        nc = 'GET /api/v1/catalogo/colecciones';                   tablas = @('coleccion') },
        @{ n = 'obtener_coleccion';         nc = 'GET /api/v1/catalogo/colecciones/{id}';              tablas = @('coleccion') },
        @{ n = 'cambiar_estado_coleccion';  nc = 'PATCH /api/v1/catalogo/colecciones/{id}/estado';     tablas = @('coleccion') }
      )},
    @{ form = 'TemporadaFormulario'; nf = 'features/admin/temporadas/temporada-formulario.ts'; clases = @(
        @{ n = 'crear_temporada';  nc = 'POST /api/v1/catalogo/temporadas. Avisa si las fechas se cruzan con otra temporada activa.'; tablas = @('temporada') },
        @{ n = 'editar_temporada'; nc = 'PATCH /api/v1/catalogo/temporadas/{id}'; tablas = @('temporada') }
      )},
    @{ form = 'ColeccionFormulario'; nf = 'features/admin/temporadas/coleccion-formulario.ts'; clases = @(
        @{ n = 'crear_coleccion';  nc = 'POST /api/v1/catalogo/colecciones. El nombre es único dentro de su temporada.'; tablas = @('coleccion','temporada') },
        @{ n = 'editar_coleccion'; nc = 'PATCH /api/v1/catalogo/colecciones/{id}'; tablas = @('coleccion') }
      )}
  )
  tablas = @(
    @{ n = 'categoria'; propia = $true },
    @{ n = 'talla';     propia = $true },
    @{ n = 'color';     propia = $true },
    @{ n = 'temporada'; propia = $true },
    @{ n = 'coleccion'; propia = $true }
  )
}
,

# ------------------------------------------------------------------ P4 --
@{
  nombre = '4.3 Subsistema 4 — Inventario'
  nota   = "SUBSISTEMA 4 = PAQUETE P4 del análisis 2.1`n`nCU-13 Registrar ingreso de mercadería,`nCU-14 Consultar inventario consolidado,`nCU-15 Registrar movimiento de inventario,`nCU-16 Gestionar disponibilidad de la sucursal.`n`nBackend: backend/app/modules/inventario`nFrontend: features/admin/inventario, features/admin/consolidado,`n          features/sucursal/disponibilidad`n`nVerde: implementado. Azul: tabla de otro subsistema.`n`nEs el subsistema que concentra la regla más crítica del`nsistema: ninguna cantidad se modifica sin generar su`nmovimiento. Por eso TODO endpoint que toca existencia`ntoca también movimiento_inventario.`n`nsolo dos de sus siete tablas son propias: P4 dice cuánto`nhay y dónde, pero la prenda y la sucursal son de otros."
  grupos = @(
    @{ form = 'Inventario'; nf = 'features/admin/inventario/inventario.ts. Tres pestañas: existencias, ingresos y movimientos.'; clases = @(
        @{ n = 'listar_existencias';     nc = 'GET /api/v1/inventario/existencias. Paginado desde el 13/09: devolvía la lista entera y con el dataset cargado el navegador no la podía dibujar.'; tablas = @('existencia','variante_producto','sucursal') },
        @{ n = 'listar_ingresos';        nc = 'GET /api/v1/inventario/ingresos. Agrupa los movimientos de INGRESO por referencia de remito.'; tablas = @('movimiento_inventario') },
        @{ n = 'detalle_de_ingreso';     nc = 'GET /api/v1/inventario/ingresos/detalle';   tablas = @('movimiento_inventario','existencia') },
        @{ n = 'listar_movimientos';     nc = 'GET /api/v1/inventario/movimientos. La trazabilidad que pide el RF22.'; tablas = @('movimiento_inventario','existencia') },
        @{ n = 'listar_tipos_manuales';  nc = 'GET /api/v1/inventario/tipos-movimiento. Devuelve una constante: no consulta ninguna tabla.'; tablas = @() }
      )},
    @{ form = 'IngresoFormulario'; nf = 'features/admin/inventario/ingreso-formulario.ts. El remito, con sus líneas.'; clases = @(
        @{ n = 'registrar_ingreso'; nc = 'POST /api/v1/inventario/ingresos. Todo el remito en una sola transacción: si una línea falla, no entra ninguna.'; tablas = @('existencia','movimiento_inventario','variante_producto','sucursal','proveedor') }
      )},
    @{ form = 'AjusteFormulario'; nf = 'features/admin/inventario/ajuste-formulario.ts'; clases = @(
        @{ n = 'registrar_ajuste'; nc = 'POST /api/v1/inventario/movimientos/ajuste. Se cuenta el total FÍSICO, no el disponible: una prenda apartada sigue en la percha.'; tablas = @('existencia','movimiento_inventario') }
      )},
    @{ form = 'TransferenciaFormulario'; nf = 'features/admin/inventario/transferencia-formulario.ts'; clases = @(
        @{ n = 'registrar_transferencia'; nc = 'POST /api/v1/inventario/movimientos/transferencia. Dos movimientos en una transacción: TRASLADO_SALIDA y TRASLADO_ENTRADA.'; tablas = @('existencia','movimiento_inventario','sucursal') }
      )},
    @{ form = 'Consolidado'; nf = 'features/admin/consolidado/consolidado.ts'; clases = @(
        @{ n = 'consultar_consolidado'; nc = 'GET /api/v1/inventario/consolidado. Agrupa por variante y calcula el resumen sobre TODO lo filtrado antes de paginar.'; tablas = @('existencia','variante_producto','producto','sucursal') }
      )},
    @{ form = 'Disponibilidad'; nf = 'features/sucursal/disponibilidad/disponibilidad.ts. El panel del Encargado, acotado a su sucursal.'; clases = @(
        @{ n = 'listar_alertas'; nc = 'GET /api/v1/inventario/alertas. Solo las que tienen umbral: cero significa «sin alerta».'; tablas = @('existencia','variante_producto') }
      )},
    @{ form = 'MinimoFormulario'; nf = 'features/admin/inventario/minimo-formulario.ts'; clases = @(
        @{ n = 'fijar_stock_minimo'; nc = 'PATCH /api/v1/inventario/existencias/{id}/stock-minimo'; tablas = @('existencia') }
      )},
    @{ form = $null; clases = @(
        @{ n = 'apartar_para_reserva'; nc = 'inventario/service.py. NO es un endpoint: lo llama P6 al crear una reserva. Toma el SELECT ... FOR UPDATE que mitiga el riesgo R5.'; tablas = @('existencia','movimiento_inventario') },
        @{ n = 'liberar_de_reserva';   nc = 'inventario/service.py. Lo llaman CU-23, CU-24 y CU-25 para devolver el stock apartado.'; tablas = @('existencia','movimiento_inventario') },
        @{ n = 'descontar_por_venta';  nc = 'inventario/service.py. Lo llama CU-24 cuando el cliente se lleva la prenda.'; tablas = @('existencia','movimiento_inventario') },
        @{ n = 'disponibilidad_por_sucursal'; nc = 'inventario/service.py. La COSTURA C1: P5 le pide este dato en vez de consultar existencia, que es ajena.'; tablas = @('existencia','sucursal') }
      )}
  )
  tablas = @(
    @{ n = 'existencia';            propia = $true  },
    @{ n = 'movimiento_inventario'; propia = $true  },
    @{ n = 'variante_producto';     propia = $false },
    @{ n = 'producto';              propia = $false },
    @{ n = 'sucursal';              propia = $false },
    @{ n = 'proveedor';             propia = $false }
  )
},

# ------------------------------------------------------------------ P5 --
@{
  nombre = '4.3 Subsistema 5 — Catálogo Público y Disponibilidad'
  nota   = "SUBSISTEMA 5 = PAQUETE P5 del análisis 2.1`n`nCU-17 Consultar catálogo, CU-18 Consultar ficha de producto,`nCU-19 Consultar disponibilidad por sucursal.`n`nBackend: backend/app/modules/catalogo_publico`nFrontend: features/tienda/catalogo, features/tienda/ficha`nMóvil: mobile/lib/features/catalogo`n`nAzul: TODAS las tablas son de otro subsistema.`n`nEs el único subsistema SIN TABLAS PROPIAS en este ciclo,`ny no es un descuido: P5 es una fachada de solo lectura`nsobre P3 y P4. Esa es su razón de ser --- separa las`nnecesidades de consulta del cliente de las operaciones`nde mantenimiento del Administrador.`n`nTampoco pasa por autenticación: su router no declara`nrequiere_roles. La vitrina es pública.`n`ndisponibilidad_de_variante no consulta existencia por su`ncuenta: llama a la función de P4 (costura C1)."
  grupos = @(
    @{ form = 'Catalogo'; nf = 'features/tienda/catalogo/catalogo.ts. La vitrina, con búsqueda, filtros, orden y paginación.'; clases = @(
        @{ n = 'listar_productos'; nc = 'GET /api/v1/tienda/productos. Solo lo ofrecible: producto activo con al menos una variante activa.'; tablas = @('producto','variante_producto','imagen_producto','categoria') },
        @{ n = 'obtener_filtros';  nc = 'GET /api/v1/tienda/filtros. Solo las opciones que el catálogo realmente ofrece.'; tablas = @('categoria','talla','color','temporada') }
      )},
    @{ form = 'Ficha'; nf = 'features/tienda/ficha/ficha.ts. El detalle, con la selección de talla y color.'; clases = @(
        @{ n = 'obtener_ficha';              nc = 'GET /api/v1/tienda/productos/{id}. El 404 es el mismo si no existe o si dejó de ofrecerse: recorrer identificadores no delata los productos ocultos.'; tablas = @('producto','variante_producto','imagen_producto') },
        @{ n = 'disponibilidad_de_variante'; nc = 'GET /api/v1/tienda/variantes/{id}/disponibilidad. COSTURA C1: le pide el dato a P4.'; tablas = @('variante_producto','existencia') }
      )}
  )
  tablas = @(
    @{ n = 'producto';          propia = $false },
    @{ n = 'variante_producto'; propia = $false },
    @{ n = 'imagen_producto';   propia = $false },
    @{ n = 'categoria';         propia = $false },
    @{ n = 'talla';             propia = $false },
    @{ n = 'color';             propia = $false },
    @{ n = 'temporada';         propia = $false },
    @{ n = 'existencia';        propia = $false }
  )
},

# ------------------------------------------------------------------ P6 --
@{
  nombre = '4.3 Subsistema 6 — Reservas'
  nota   = "SUBSISTEMA 6 = PAQUETE P6 del análisis 2.1`n`nCU-22 Crear reserva de prendas,`nCU-23 Consultar y cancelar reserva,`nCU-24 Atender reserva en sucursal,`nCU-25 Expirar reservas vencidas.`n`nBackend: backend/app/modules/reservas`nFrontend: features/cliente/reservas, features/sucursal/reservas`nMóvil: mobile/lib/features/reservas`n`nVerde: implementado. Azul: tabla de otro subsistema.`n`nDOS ROUTERS, PORQUE SON DOS ÁMBITOS: /reservas es del`nCliente --- las suyas --- y /sucursal/reservas es del`nEncargado --- las de su local ---. Casi nunca coinciden.`n`nP6 NO ESCRIBE existencia ni movimiento_inventario por su`ncuenta: llama a las funciones de P4. La regla «ninguna`ncantidad cambia sin movimiento» es de P4 y no puede estar`nen dos lugares. Lo que P6 sí controla es la transacción.`n`nexpirar_reservas_vencidas no tiene pantalla: lo dispara`nel planificador. El endpoint de mantenimiento existe para`npoder demostrarlo en la defensa."
  grupos = @(
    @{ form = 'Reservas'; nf = 'features/cliente/reservas/reservas.ts. Mis reservas: las vivas en tarjetas y las cerradas en lista.'; clases = @(
        @{ n = 'listar_mis_reservas'; nc = 'GET /api/v1/reservas. Filtro `vivas` además del de estado: la pregunta de la pantalla es «¿qué tengo pendiente?», y eso son dos estados.'; tablas = @('reserva','reserva_detalle') },
        @{ n = 'obtener_reserva';     nc = 'GET /api/v1/reservas/{id}. Una reserva ajena devuelve 404 y no 403: un 403 confirmaría que existe.'; tablas = @('reserva','reserva_detalle','variante_producto') },
        @{ n = 'cancelar_reserva';    nc = 'PATCH /api/v1/reservas/{id}/cancelacion. PATCH sobre un sub-recurso y no DELETE: cancelar no borra la reserva.'; tablas = @('reserva','reserva_detalle','existencia','movimiento_inventario') }
      )},
    @{ form = 'ReservaFormulario'; nf = 'features/cliente/reservas/reserva-formulario.ts. Pide primero las prendas y después la sucursal, al revés que el servidor.'; clases = @(
        @{ n = 'crear_reserva'; nc = 'POST /api/v1/reservas. Primero todo lo que se rechaza sin tocar filas --- sucursal, franja, prendas, capacidad --- y recién al final el apartado, que es lo único que toma bloqueos.'; tablas = @('reserva','reserva_detalle','existencia','movimiento_inventario','sucursal','variante_producto') }
      )},
    @{ form = 'ReservasSucursal'; nf = 'features/sucursal/reservas/reservas-sucursal.ts. La agenda del local, la franja más próxima arriba.'; clases = @(
        @{ n = 'listar_reservas_de_sucursal'; nc = 'GET /api/v1/sucursal/reservas. Ordena al revés que las del Cliente: el Encargado mira una agenda, no un historial.'; tablas = @('reserva','cliente') },
        @{ n = 'obtener_reserva_de_sucursal'; nc = 'GET /api/v1/sucursal/reservas/{id}. Las prendas que hay que ir a buscar a la percha.'; tablas = @('reserva','reserva_detalle','variante_producto') },
        @{ n = 'preparar_reserva';            nc = 'PATCH /api/v1/sucursal/reservas/{id}/preparacion. No mueve stock: ya estaba apartado.'; tablas = @('reserva') }
      )},
    @{ form = 'AtencionFormulario'; nf = 'features/sucursal/reservas/atencion-formulario.ts. El resultado de cada prenda.'; clases = @(
        @{ n = 'atender_reserva'; nc = 'PATCH /api/v1/sucursal/reservas/{id}/atencion. Por cada prenda que el cliente se lleva escribe DOS movimientos: una LIBERACION y una VENTA. El neto sobre el disponible es cero y el invariante D4 se sostiene.'; tablas = @('reserva','reserva_detalle','existencia','movimiento_inventario') }
      )},
    @{ form = $null; clases = @(
        @{ n = 'expirar_reservas_vencidas'; nc = 'POST /api/v1/mantenimiento/reservas/expiracion. Lo dispara el planificador; el endpoint existe para demostrarlo. El movimiento de LIBERACION queda SIN usuario, y eso es lo que distingue una expiración de una cancelación en el historial.'; tablas = @('reserva','reserva_detalle','existencia','movimiento_inventario') }
      )}
  )
  tablas = @(
    @{ n = 'reserva';               propia = $true  },
    @{ n = 'reserva_detalle';       propia = $true  },
    @{ n = 'existencia';            propia = $false },
    @{ n = 'movimiento_inventario'; propia = $false },
    @{ n = 'variante_producto';     propia = $false },
    @{ n = 'sucursal';              propia = $false },
    @{ n = 'cliente';               propia = $false }
  )
}

)

# =========================================================================
# PARTE 1 - Enterprise Architect por COM
# =========================================================================

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

function Get-OCrearPaquete($padre, $nombre) {
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    $p = $padre.Packages.AddNew($nombre, 'Package'); [void]$p.Update()
    $padre.Packages.Refresh(); return $p
}
function BuscarPaquete($p, $n) {
    foreach ($s in $p.Packages) { if ($s.Name -eq $n) { return $s }; $r = BuscarPaquete $s $n; if ($r) { return $r } }
    return $null
}
function BuscarDiagrama($p, $n) {
    foreach ($d in $p.Diagrams) { if ($d.Name -eq $n) { return $d } }
    foreach ($s in $p.Packages) { $r = BuscarDiagrama $s $n; if ($r) { return $r } }
    return $null
}

$root = $ea.Models.GetAt(0)
$pRaiz = BuscarPaquete $root 'Violet Boutique'
if (-not $pRaiz) { throw 'No se encontro el paquete Violet Boutique' }
$pCap4 = Get-OCrearPaquete $pRaiz 'CAP. 4 - Flujo de Trabajo: Implementacion'

if ($Rehacer) {
    for ($i = $pCap4.Packages.Count - 1; $i -ge 0; $i--) {
        if ($pCap4.Packages.GetAt($i).Name -eq '4.3 Componentes de Subsistemas') {
            $pCap4.Packages.DeleteAt($i, $false)
            Write-Output '  paquete 4.3 anterior eliminado (-Rehacer)'
        }
    }
    $pCap4.Packages.Refresh()
}

$p43 = Get-OCrearPaquete $pCap4 '4.3 Componentes de Subsistemas'
$estilos = @()

foreach ($sub in $SUBSISTEMAS) {

    if (BuscarDiagrama $p43 $sub.nombre) {
        Write-Output "  $($sub.nombre) ya existe, no se toca"
        continue
    }

    $dia = $p43.Diagrams.AddNew($sub.nombre, 'Component')
    [void]$dia.Update(); $p43.Diagrams.Refresh()

    function New-Comp($nombre, $estereotipo, $nota) {
        $e = $p43.Elements.AddNew($nombre, 'Component')
        if ($estereotipo) { $e.Stereotype = $estereotipo; $e.StereotypeEx = $estereotipo }
        if ($nota) { $e.Notes = $nota }
        [void]$e.Update()
        return $e
    }
    function Poner($d, $el, $l, $t, $ancho, $alto, $color) {
        $do = $d.DiagramObjects.AddNew("l=$l;r=$($l + $ancho);t=$t;b=$($t - $alto);", '')
        $do.ElementID = $el.ElementID
        [void]$do.Update()
        if ($color) { $script:estilos += [pscustomobject]@{ dia = $d.DiagramID; id = $el.ElementID; col = $color } }
    }
    function New-Conector($src, $dst, $tipo) {
        $c = $src.Connectors.AddNew('', $tipo)
        $c.SupplierID = $dst.ElementID
        $c.Direction = 'Source -> Destination'
        [void]$c.Update()
        $src.Connectors.Refresh()
    }

    # ---- Bandas «FORM» y «CLASS» ----
    # Cada grupo ocupa ceil(n/2) columnas: los endpoints se alternan entre la
    # fila de arriba y la de abajo. La pantalla se centra sobre su grupo.
    $col = 0
    $elClase = @{}
    $nForm = 0; $nClase = 0
    foreach ($g in $sub.grupos) {
        $n = $g.clases.Count
        $cols = [math]::Ceiling($n / 2)
        $x0 = $col * $COL_STEP

        for ($i = 0; $i -lt $n; $i++) {
            $c = $g.clases[$i]
            $cx = $x0 + ([math]::Floor($i / 2) * $COL_STEP)
            $cy = if ($i % 2 -eq 0) { $Y_CLS_A } else { $Y_CLS_B }
            $e = New-Comp $c.n 'CLASS' $c.nc
            Poner $dia $e $cx $cy $COL_W $H_CLS $VERDE
            $elClase[$c.n] = @{ el = $e; tablas = $c.tablas }
            $nClase++
        }

        if ($g.form) {
            $anchoF = ($cols * $COL_STEP) - ($COL_STEP - $COL_W)
            $ef = New-Comp $g.form 'FORM' $g.nf
            Poner $dia $ef $x0 $Y_FORM $anchoF $H_FORM $VERDE
            foreach ($c in $g.clases) { New-Conector $ef $elClase[$c.n].el 'Assembly' }
            $nForm++
        }

        $col += $cols
    }
    $anchoTotal = $col * $COL_STEP

    # ---- Banda «TABLA», repartida a lo ancho ----
    $elTabla = @{}
    $nt = $sub.tablas.Count
    $usado = $nt * $TAB_STEP
    $tx0 = [math]::Max(0, [int](($anchoTotal - $usado) / 2))
    for ($i = 0; $i -lt $nt; $i++) {
        $t = $sub.tablas[$i]
        $e = New-Comp $t.n 'TABLA' "Tabla $($t.n) del esquema de 3.3.1."
        Poner $dia $e ($tx0 + $i * $TAB_STEP) $Y_TABLA $TAB_W $H_TABLA $(if ($t.propia) { $VERDE } else { $AZUL })
        $elTabla[$t.n] = $e
    }

    # ---- Dependencias «CLASS» -> «TABLA» ----
    $nDep = 0
    foreach ($k in $elClase.Keys) {
        foreach ($t in $elClase[$k].tablas) {
            if (-not $elTabla.ContainsKey($t)) { throw "En '$($sub.nombre)' el endpoint $k apunta a la tabla $t, que no esta en la banda" }
            New-Conector $elClase[$k].el $elTabla[$t] 'Dependency'
            $nDep++
        }
    }

    # ---- Leyenda ----
    $nota = $p43.Elements.AddNew('', 'Note')
    $nota.Notes = $sub.nota
    [void]$nota.Update()
    Poner $dia $nota ($anchoTotal + 60) $Y_FORM 420 400 $null

    $p43.Elements.Refresh()
    $dia.DiagramObjects.Refresh(); $dia.DiagramLinks.Refresh()
    Write-Output "  $($sub.nombre) : $nForm «FORM», $nClase «CLASS», $nt «TABLA», $nDep dependencias"
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers()
Start-Sleep -Milliseconds 1500

if ($estilos.Count -eq 0) { Write-Output 'Nada nuevo que pintar'; Write-Output 'OK'; exit 0 }

# =========================================================================
# PARTE 2 - El color de fondo, concatenado en t_diagramobjects.ObjectStyle.
# =========================================================================

$cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$modelo;")
$cn.Open()
foreach ($g in $estilos) {
    $q = $cn.CreateCommand()
    $q.CommandText = "SELECT ObjectStyle FROM t_diagramobjects WHERE Diagram_ID = $($g.dia) AND Object_ID = $($g.id)"
    $st = "$($q.ExecuteScalar())"
    if ($st -notmatch 'BCol=') {
        $u = $cn.CreateCommand()
        $u.CommandText = "UPDATE t_diagramobjects SET ObjectStyle = ? WHERE Diagram_ID = $($g.dia) AND Object_ID = $($g.id)"
        [void]$u.Parameters.AddWithValue('s', ($st + "BCol=$($g.col);"))
        [void]$u.ExecuteNonQuery()
    }
}
# ---- El estereotipo «FORM» ----
# EA trae un estereotipo propio llamado 'form' y, al asignarlo por la API,
# lo empareja sin distinguir mayusculas: guarda 'form' en minuscula y ademas
# le cuelga la aplicacion del perfil en una fila 'Stereotypes' de t_xref.
# CLASS y TABLA no chocan con nada y quedan bien.
#
# En el archivo de catedra pasa exactamente lo mismo: hay un LoginForm
# huerfano con «form» --- su primer intento --- y los definitivos llevan
# «FORM» con los guillemets tecleados a mano para escapar del emparejamiento.
# Aqui se resuelve limpio: se borra la aplicacion del perfil y se deja el
# texto en mayusculas.
$pk = "(SELECT Package_ID FROM t_package WHERE Name = '4.3 Componentes de Subsistemas')"

$dx = $cn.CreateCommand()
$dx.CommandText = "DELETE FROM t_xref WHERE Name = 'Stereotypes' AND Client IN (SELECT ea_guid FROM t_object WHERE Stereotype = 'form' AND Package_ID = $pk)"
$borradas = $dx.ExecuteNonQuery()

$ux = $cn.CreateCommand()
# Ojo: StereotypeEx NO es una columna de t_object --- es justamente la fila
# de t_xref que se acaba de borrar. Aqui solo se toca Stereotype.
$ux.CommandText = "UPDATE t_object SET Stereotype = 'FORM' WHERE Stereotype = 'form' AND Package_ID = $pk"
$corregidas = $ux.ExecuteNonQuery()

$cn.Close()
Write-Output "  color de fondo aplicado a $($estilos.Count) componentes"
Write-Output "  «FORM»: $corregidas estereotipos pasados a mayusculas, $borradas perfiles desligados"
Write-Output 'OK'
