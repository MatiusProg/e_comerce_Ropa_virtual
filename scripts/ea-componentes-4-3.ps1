param(
    # Borra el paquete 4.3 entero y lo vuelve a generar.
    [switch]$Rehacer,

    # Rehace SOLO los subsistemas cuyo nombre contenga este texto, sin tocar
    # los demas. Es lo que hay que usar casi siempre: -Rehacer borra los once
    # y se lleva por delante el acomodo que EA le haya dado a los viejos.
    #     .\ea-componentes-4-3.ps1 -Solo 'Subsistema 7'
    #     .\ea-componentes-4-3.ps1 -Solo 'Subsistema 1'
    [string]$Solo
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
# El color sigue la convencion del 4.2: verde, implementado; azul, lo que
# pertenece a OTRO subsistema --- una tabla, o desde el Ciclo 3 tambien un
# endpoint: las pantallas de P8 y P9 llaman a uno que no es suyo, y pintarlo
# verde diria que el subsistema lo implementa.
#
# ---- LO QUE AGREGO EL CICLO 3 (21/09/2026) ----
#
# Los cinco subsistemas que faltaban: P7 Ventas y Punto de Venta, P8 Pagos,
# P9 Vestidor Virtual, P10 Inteligencia Artificial y P11 Reportes y Tablero.
# Con ellos quedan los once del analisis 2.1.
#
# Y dos ajustes de maquetacion que esos cinco obligaron a resolver:
#
# 4. LA BANDA «TABLA» TAMBIEN VA EN DOS FILAS cuando pasa de doce, por la
#    misma razon que la de «CLASS»: P7 tiene dieciocho tablas y P10
#    diecisiete, y en una sola fila el diagrama pasaba de los 3600 px. Los
#    seis subsistemas del Ciclo 2 tienen ocho o menos, asi que no cambian.
#
# 5. LA LEYENDA SE COLOCA A LA DERECHA DE LO MAS ANCHO de las tres bandas y
#    no solo de la de «CLASS». En P8 la banda de tablas es el triple de ancha
#    que la de endpoints ---cuatro componentes, ocho tablas--- y con el
#    calculo viejo la nota caia justo encima de ella.
#
# OJO: los seis diagramas del Ciclo 2 ya estan generados y este script es
# aditivo, asi que no se tocan. Les falta el alcance del Ciclo 3 --- CU-41 y
# CU-42 en S1, CU-12 y CU-38 en S3, CU-39 en S4, CU-20 en S5 ---; para
# ponerlos al dia hay que agregar esos endpoints a su bloque y correr con
# -Rehacer, que borra el paquete 4.3 ENTERO y regenera los once.
#
# ADITIVO: abre el modelo y solo agrega lo que falta.
#
# OJO AL CORRER VARIOS GENERADORES SEGUIDOS: cada uno deja un proceso EA
# vivo, y al acumularse el siguiente falla con «failed to create empty
# document», que no es un error del modelo sino agotamiento de recursos.
# Entre corrida y corrida:
#     Get-Process EA -ErrorAction SilentlyContinue | Stop-Process -Force
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

# =========================================================================
# PARTE 0 - El borrado de -Solo, por OLEDB y con EA cerrado.
#
# Los once diagramas comparten el paquete 4.3, asi que no alcanza con vaciar
# un paquete como en el 2.4: hay que borrar los elementos DE ESE DIAGRAMA.
# Se puede porque los elementos NO se comparten --- cada diagrama crea los
# suyos con AddNew, y por eso `usuario` o `venta` aparecen repetidos en
# varios subsistemas. Borrar los de uno no deja tuerto a ningun otro.
#
# El orden importa: conectores y objetos de lienzo ANTES que los elementos,
# o las subconsultas ya no encuentran a quien borrar (regla 5: borrar un
# diagrama no borra sus conectores).
# =========================================================================
if ($Solo) {
    $cn0 = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$modelo;")
    $cn0.Open()
    function Filas($sql) {
        $c = $cn0.CreateCommand(); $c.CommandText = $sql
        $a = New-Object System.Data.OleDb.OleDbDataAdapter $c
        $t = New-Object System.Data.DataTable; [void]$a.Fill($t); return ,$t
    }
    function Correr($sql) { $c = $cn0.CreateCommand(); $c.CommandText = $sql; return $c.ExecuteNonQuery() }

    $patron = $Solo.Replace("'", "''")
    $encontrados = Filas "SELECT d.Diagram_ID AS id, d.Name AS nom FROM t_diagram d INNER JOIN t_package p ON p.Package_ID = d.Package_ID WHERE p.Name = '4.3 Componentes de Subsistemas' AND d.Name LIKE '%$patron%'"
    if ($encontrados.Rows.Count -eq 0) {
        Write-Output "  -Solo '$Solo': no coincide con ningun diagrama del 4.3; no se borra nada"
    }
    foreach ($fila in $encontrados.Rows) {
        $id = [int]$fila.id
        $enDia = "(SELECT Object_ID FROM t_diagramobjects WHERE Diagram_ID = $id)"
        $nCon = Correr "DELETE FROM t_connector WHERE Start_Object_ID IN $enDia OR End_Object_ID IN $enDia"
        $nXrf = Correr "DELETE FROM t_xref WHERE Client IN (SELECT ea_guid FROM t_object WHERE Object_ID IN $enDia)"
        $nObj = Correr "DELETE FROM t_object WHERE Object_ID IN $enDia"
        # t_diagramlinks lleva DiagramID SIN guion bajo, al reves que todas
        # las demas tablas. Escribirlo `Diagram_ID` no da «columna
        # inexistente»: ACE lo toma por un parametro y falla con «faltan
        # valores para algunos de los parametros requeridos».
        $nLnk = Correr "DELETE FROM t_diagramlinks WHERE DiagramID = $id"
        $nDo  = Correr "DELETE FROM t_diagramobjects WHERE Diagram_ID = $id"
        [void](Correr "DELETE FROM t_diagram WHERE Diagram_ID = $id")
        Write-Output "  -Solo: borrado '$($fila.nom)' --- $nObj elementos, $nCon conectores, $nDo objetos de lienzo, $nLnk enlaces, $nXrf filas de t_xref"
    }
    $cn0.Close()
}

# ---- Constantes de dibujo ----
# EL MARGEN IZQUIERDO NO ES DECORACION. Si un objeto se coloca con `l=0`, EA
# DESCARTA el rectangulo entero y lo deja en (0,0): la primera columna de
# cada banda ---la pantalla, sus endpoints y las primeras tablas--- termina
# apilada en el origen, una encima de la otra. No da ningun error. Los seis
# diagramas del Ciclo 2 no lo mostraban porque EA los remaqueto al abrirlos,
# que tapa el sintoma y no la causa.
#
# Y NO SE LLAMA COMO LA VARIABLE DEL BUCLE, aunque seria el nombre obvio:
# adentro hay un $x0 ---la izquierda del grupo que se esta dibujando--- y
# PowerShell NO DISTINGUE MAYUSCULAS EN LOS NOMBRES DE VARIABLE (regla 7).
# Serian la misma: la constante se iba acumulando en cada grupo y el
# Subsistema 7 salio de 11660 px de ancho en vez de 2840. Tampoco da error.
$MARGEN_X = 20
$COL_W    = 160
$COL_STEP = 180
$Y_FORM   = -60;  $H_FORM  = 62
$Y_CLS_A  = -240; $Y_CLS_B = -345; $H_CLS = 62
$Y_TABLA  = -520; $H_TABLA = 56
$Y_TABLA_B = -615                  # la segunda fila de tablas, si hace falta
$TAB_W    = 170;  $TAB_STEP = 200
$TAB_2_FILAS_DESDE = 12            # con mas tablas que esto, la banda va en dos filas

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

,

# ------------------------------------------------------------------ P7 --
@{
  nombre = '4.3 Subsistema 7 — Ventas y Punto de Venta'
  nota   = "SUBSISTEMA 7 = PAQUETE P7 del análisis 2.1`n`nCU-26 Carrito de compras, CU-27 Confirmar pedido,`nCU-29 Historial de compras y comprobante,`nCU-30 Abrir y cerrar caja, CU-31 Venta presencial,`nCU-32 Registrar devolución.`n`nBackend: modules/ventas, modules/caja, modules/pos`nFrontend: features/tienda/carrito, checkout,`n          features/cliente/compras, features/caja`nMóvil: mobile/lib/features/compra`n`nVerde: implementado. Azul: tabla de otro subsistema.`n`nES EL SUBSISTEMA MÁS GRANDE, y esa es su razón de ser:`nel canal digital y el presencial terminan en la MISMA`ntabla venta, con el mismo descuento de inventario.`nSepararlos habría duplicado esa lógica.`n`nTRES REGLAS QUE NO SE VEN EN EL DIBUJO:`n· El carrito NO congela el precio --- no tiene ninguna`n  columna de dinero ---; detalle_venta sí.`n· crear_pedido APARTA el stock, no espera al pago. Por`n  eso existe expirar_pedidos_vencidos: sin esa barrida,`n  apartar sería un defecto.`n· P7 nunca escribe existencia por su cuenta: llama a las`n  funciones de P4, porque la regla «ninguna cantidad`n  cambia sin movimiento» no puede estar en dos lugares.`n`nLa banda de tablas va en DOS FILAS: son dieciocho."
  grupos = @(
    @{ form = 'Carrito'; nf = 'features/tienda/carrito/carrito.ts, sobre CarritoService. El botón de agregar no vive acá sino en la Ficha y el Catálogo de P5.'; clases = @(
        @{ n = 'ver_carrito';       nc = 'GET /api/v1/tienda/carrito. El precio se lee EN VIVO y no congelado: si la boutique baja un precio, el carrito lo refleja.'; tablas = @('carrito','carrito_detalle','variante_producto','existencia') },
        @{ n = 'agregar_al_carrito';nc = 'POST /api/v1/tienda/carrito/items. SUMA a lo que ya hubiera de esa variante; no la reemplaza.'; tablas = @('carrito','carrito_detalle','variante_producto') },
        @{ n = 'cambiar_cantidad';  nc = 'PATCH /api/v1/tienda/carrito/items/{variante_id}. FIJA la cantidad, al revés que agregar.'; tablas = @('carrito_detalle','existencia') },
        @{ n = 'quitar_del_carrito';nc = 'DELETE /api/v1/tienda/carrito/items/{variante_id}'; tablas = @('carrito_detalle') },
        @{ n = 'vaciar_carrito';    nc = 'DELETE /api/v1/tienda/carrito. Lo usa también P8 al confirmar el pago.'; tablas = @('carrito_detalle') }
      )},
    @{ form = 'Checkout'; nf = 'features/tienda/checkout/checkout.ts. Dirección de envío o retiro en sucursal, y el total ya con los descuentos de CU-12.'; clases = @(
        @{ n = 'opciones_de_pedido'; nc = 'GET /api/v1/tienda/pedidos/opciones. Paso 1: qué sucursal puede cubrir el carrito ENTERO, y qué prenda le falta a cada una de las que no.'; tablas = @('carrito','carrito_detalle','existencia','sucursal','direccion_cliente','variante_producto') },
        @{ n = 'crear_pedido';       nc = 'POST /api/v1/tienda/pedidos. Nace PENDIENTE_PAGO y APARTA el stock. El cliente manda el total que vio: si no coincide es 409 con el carrito entero. Un pedido se despacha desde UNA sucursal, la de la ciudad del destino si puede.'; tablas = @('venta','detalle_venta','carrito_detalle','existencia','movimiento_inventario','cliente','sucursal','direccion_cliente','variante_producto','pago') }
      )},
    @{ form = 'MiPedido'; nf = 'mobile/lib/features/compra/pantalla_pedido.dart. En la web el estado se mira desde la pantalla de retorno de P8.'; clases = @(
        @{ n = 'ver_pedido';      nc = 'GET /api/v1/tienda/pedidos/{codigo}'; tablas = @('venta','detalle_venta','pago','sucursal','variante_producto') },
        @{ n = 'cancelar_pedido'; nc = 'POST /api/v1/tienda/pedidos/{codigo}/cancelar. Devuelve al stock lo apartado.'; tablas = @('venta','detalle_venta','existencia','movimiento_inventario') }
      )},
    @{ form = 'Compras'; nf = 'features/cliente/compras/compras.ts y mobile/lib/features/compra/pantalla_mis_compras.dart'; clases = @(
        @{ n = 'listar_compras';        nc = 'GET /api/v1/tienda/compras. Lo que quedó después de comprar; el pedido es el flujo, la compra es el resultado.'; tablas = @('venta','detalle_venta') },
        @{ n = 'descargar_comprobante'; nc = 'GET /api/v1/tienda/compras/{codigo}/comprobante. El PDF; se fabrica una sola vez y queda guardado.'; tablas = @('comprobante','venta') }
      )},
    @{ form = 'Turno'; nf = 'features/caja/turno/turno.ts. La cáscara propia de /caja, que hasta CU-30 no existía.'; clases = @(
        @{ n = 'cajas_de_mi_sucursal'; nc = 'GET /api/v1/caja/cajas. Acotado a la sucursal del Cajero.'; tablas = @('caja','sucursal') },
        @{ n = 'mi_turno_abierto';     nc = 'GET /api/v1/caja/turnos/mio. Devuelve null si no hay ninguno, y eso no es un error.'; tablas = @('turno_caja') },
        @{ n = 'abrir_turno';          nc = 'POST /api/v1/caja/turnos. Toma FOR UPDATE sobre la caja: dos cajeros no pueden abrir la misma.'; tablas = @('turno_caja','caja') },
        @{ n = 'cerrar_turno';         nc = 'POST /api/v1/caja/turnos/{turno_id}/cierre. El arqueo: suma el efectivo cobrado y resta las devoluciones del turno.'; tablas = @('turno_caja','venta','devolucion') }
      )},
    @{ form = 'VentaPresencial'; nf = 'features/caja/venta/venta.ts. El mostrador: prendas sueltas o una reserva que vino a cobrarse.'; clases = @(
        @{ n = 'prendas_del_mostrador'; nc = 'GET /api/v1/pos/prendas. Solo lo que HAY en la sucursal del turno.'; tablas = @('variante_producto','existencia') },
        @{ n = 'reservas_por_cobrar';   nc = 'GET /api/v1/pos/reservas. La salida natural de P6: una reserva atendida se convierte en venta.'; tablas = @('reserva','reserva_detalle','cliente') },
        @{ n = 'ver_reserva_a_cobrar';  nc = 'GET /api/v1/pos/reservas/{reserva_id}'; tablas = @('reserva','reserva_detalle','cliente') },
        @{ n = 'registrar_venta';       nc = 'POST /api/v1/pos/ventas. Exige un turno abierto. Aplica las promociones de CU-12, descuenta por P4 y emite el comprobante, todo en una transacción.'; tablas = @('venta','detalle_venta','turno_caja','existencia','movimiento_inventario','reserva','variante_producto','comprobante') },
        @{ n = 'ver_venta';             nc = 'GET /api/v1/pos/ventas/{codigo}'; tablas = @('venta','detalle_venta','sucursal','cliente') },
        @{ n = 'comprobante_de_venta';  nc = 'GET /api/v1/pos/ventas/{codigo}/comprobante'; tablas = @('comprobante','venta') }
      )},
    @{ form = 'Devolucion'; nf = 'features/caja/devolucion/devolucion.ts'; clases = @(
        @{ n = 'venta_a_devolver';     nc = 'GET /api/v1/pos/devoluciones/ventas/{codigo}. Descuenta lo YA devuelto: no se puede devolver dos veces la misma prenda.'; tablas = @('venta','detalle_venta','devolucion','detalle_devolucion') },
        @{ n = 'registrar_devolucion'; nc = 'POST /api/v1/pos/devoluciones. Toma FOR UPDATE sobre la venta y devuelve la prenda al stock por P4.'; tablas = @('devolucion','detalle_devolucion','venta','existencia','movimiento_inventario','turno_caja') }
      )},
    @{ form = $null; clases = @(
        @{ n = 'expirar_pedidos_vencidos'; nc = 'POST /api/v1/pedidos/expirar-vencidos. Lo dispara el planificador; el endpoint existe para poder demostrarlo. Sin esta barrida, apartar el stock antes de cobrar sería un defecto y no una decisión.'; tablas = @('venta','detalle_venta','existencia','movimiento_inventario') }
      )}
  )
  tablas = @(
    @{ n = 'carrito';              propia = $true  },
    @{ n = 'carrito_detalle';      propia = $true  },
    @{ n = 'venta';                propia = $true  },
    @{ n = 'detalle_venta';        propia = $true  },
    @{ n = 'comprobante';          propia = $true  },
    @{ n = 'devolucion';           propia = $true  },
    @{ n = 'detalle_devolucion';   propia = $true  },
    @{ n = 'caja';                 propia = $true  },
    @{ n = 'turno_caja';           propia = $true  },
    @{ n = 'pago';                 propia = $false },
    @{ n = 'existencia';           propia = $false },
    @{ n = 'movimiento_inventario';propia = $false },
    @{ n = 'variante_producto';    propia = $false },
    @{ n = 'reserva';              propia = $false },
    @{ n = 'reserva_detalle';      propia = $false },
    @{ n = 'cliente';              propia = $false },
    @{ n = 'direccion_cliente';    propia = $false },
    @{ n = 'sucursal';             propia = $false }
  )
},

# ------------------------------------------------------------------ P8 --
@{
  nombre = '4.3 Subsistema 8 — Pagos'
  nota   = "SUBSISTEMA 8 = PAQUETE P8 del análisis 2.1`n`nCU-27 (parcial: iniciar el cobro), CU-28 Confirmar el pago.`n`nBackend: backend/app/modules/pagos`n         backend/app/integrations/pasarela_pago`nFrontend: features/tienda/pago`n`nVerde: implementado.`nAzul: componente o tabla de otro subsistema.`n`nES EL SUBSISTEMA MÁS CHICO, y es a propósito: lo que lo`nhace un paquete no es su tamaño sino que concentra TODO`nel acoplamiento con un servicio externo. Cambiar de`npasarela no toca P7.`n`nCASI NO TIENE PANTALLAS. Dos de sus cuatro componentes`nno los llama ninguna persona: a recibir_webhook lo llama`nla pasarela, y a iniciar_cobro lo llama crear_pedido de`nP7. Por eso la banda «FORM» está casi vacía.`n`nLA IDEMPOTENCIA ES UNA SOLA RESTRICCIÓN: el UNIQUE sobre`ntransaccion_pasarela.evento_id. La transacción se escribe`nANTES de mover nada, así una notificación repetida choca`ncontra la base en vez de descontar el inventario dos`nveces. Las pasarelas reintentan de verdad.`n`nEl proveedor por omisión es «simulada» y NO cobra nada:`nel flujo se demuestra sin claves de Stripe."
  grupos = @(
    @{ form = 'PagoRetorno'; nf = 'features/tienda/pago/pago-retorno.ts. La pantalla a la que la pasarela devuelve al cliente, en /pago/exito y /pago/cancelado.'; clases = @(
        @{ n = 'ver_pedido'; ajena = $true; nc = 'GET /api/v1/tienda/pedidos/{codigo}. ES DE P7, por eso va en azul. La pantalla de retorno NO le cree a la URL de la pasarela --- esa la puede escribir cualquiera a mano --- sino que le pregunta a la BASE si la venta quedó PAGADA. Es la decisión D5.'; tablas = @('venta','pago') }
      )},
    @{ form = $null; clases = @(
        @{ n = 'iniciar_cobro';        nc = 'pagos/service.py. NO es un endpoint: lo llama crear_pedido de P7 y devuelve la URL de la pasarela. Se pide ANTES de tomar los bloqueos de inventario, para no sostenerlos mientras se espera a un tercero.'; tablas = @('pago','transaccion_pasarela','venta') },
        @{ n = 'recibir_webhook';      nc = 'POST /api/v1/pagos/webhook. Lo llama la pasarela, no una persona. Verifica la firma, registra el evento, marca la venta PAGADA, convierte el apartado en venta por P4, emite el comprobante y vacía el carrito. Responde 200 a casi todo: un error le dice a la pasarela «reintentá», y un evento repetido no mejora reintentando. La firma inválida es la excepción y responde 400.'; tablas = @('pago','transaccion_pasarela','venta','detalle_venta','existencia','movimiento_inventario','comprobante','carrito_detalle') },
        @{ n = 'simular_notificacion'; nc = 'POST /api/v1/pagos/simulacion. Dispara a mano la notificación del proveedor simulado. Existe para poder demostrar CU-28 en la defensa sin una pasarela real.'; tablas = @('pago','transaccion_pasarela','venta') },
        @{ n = 'configuracion';        nc = 'GET /api/v1/pagos/configuracion. Dice si el cobro es real o simulado, sin revelar ningún secreto. No consulta ninguna tabla.'; tablas = @() }
      )}
  )
  tablas = @(
    @{ n = 'pago';                 propia = $true  },
    @{ n = 'transaccion_pasarela'; propia = $true  },
    @{ n = 'venta';                propia = $false },
    @{ n = 'detalle_venta';        propia = $false },
    @{ n = 'comprobante';          propia = $false },
    @{ n = 'carrito_detalle';      propia = $false },
    @{ n = 'existencia';           propia = $false },
    @{ n = 'movimiento_inventario';propia = $false }
  )
},

# ------------------------------------------------------------------ P9 --
@{
  nombre = '4.3 Subsistema 9 — Vestidor Virtual (RA)'
  nota   = "SUBSISTEMA 9 = PAQUETE P9 del análisis 2.1`n`nCU-21 Probarse una prenda en el vestidor virtual.`n`nBackend: modules/vestidor_virtual, modules/medidas`nMóvil: mobile/lib/features/vestidor`n`nVerde: implementado.`nAzul: componente o tabla de otro subsistema.`n`nES EL ÚNICO SUBSISTEMA QUE VIVE EN EL TELÉFONO. Sus dos`n«FORM» son pantallas de Flutter, no de Angular: la RA`nnecesita la cámara y la detección de pose corre EN EL`nDISPOSITIVO. Del servidor apenas necesita la imagen de la`nprenda y las medidas.`n`nDOS COSAS QUE EL DIBUJO NO DEBE PROMETER:`n· NO hay ayuda por foto. Las medidas son cuatro campos`n  que el cliente ESCRIBE. La detección de pose sirve para`n  COLOCAR la prenda, no para medir a nadie.`n· El probado por IA está en «no_disponible» y su botón`n  está escondido: es opcional y no puede correr en el`n  teléfono porque necesita un modelo grande y una clave.`n`nNO EXISTE LA TABLA sesion_vestidor_virtual, y no es un`ndescuido: registraría la sesión, no la habilitaría.`nSe dejó sin escribir para no abrir una migración de más.`nPor eso P9 solo tiene dos tablas propias, las de medidas."
  grupos = @(
    @{ form = 'PantallaVestidor'; nf = 'mobile/lib/features/vestidor/pantalla_vestidor.dart. Cámara, pose y la prenda encima, escalada y rotada siguiendo hombros y cadera; el dibujo lo hace pintor_prenda.dart.'; clases = @(
        @{ n = 'listar_prendas_probables'; ajena = $true; nc = 'GET /api/v1/tienda/productos?solo_vestidor=true. ES DE P5, por eso va en azul. El filtro es opt-in: si recortara por omisión vaciaría la vitrina entera. Sin él la pantalla pedía la primera página de 48 y filtraba en el teléfono, así que de 32 prendas probables veía 22.'; tablas = @('variante_producto','producto','imagen_producto') },
        @{ n = 'estado_del_probador';      nc = 'GET /api/v1/vestidor/probador. Dice si el probado por IA está disponible. Hoy responde que no, y el botón queda escondido. No consulta ninguna tabla.'; tablas = @() },
        @{ n = 'probar';                   nc = 'POST /api/v1/vestidor/probar. El probado por IA, OPCIONAL. Toma el PNG de la variante y la foto, y delega en un modelo externo.'; tablas = @('variante_producto','producto','imagen_producto') }
      )},
    @{ form = 'PantallaMedidas'; nf = 'mobile/lib/features/vestidor/pantalla_medidas.dart. Cuatro campos escritos a mano: busto, cintura, cadera y altura.'; clases = @(
        @{ n = 'ver_mis_medidas';     nc = 'GET /api/v1/clientes/me/medidas. Devuelve null si el cliente todavía no las cargó, y eso no es un error.'; tablas = @('medida_cliente','cliente') },
        @{ n = 'guardar_mis_medidas'; nc = 'PUT /api/v1/clientes/me/medidas. PUT y no POST: hay una sola ficha de medidas por cliente.'; tablas = @('medida_cliente','cliente') },
        @{ n = 'ajuste_del_producto'; nc = 'GET /api/v1/tienda/productos/{producto_id}/ajuste. Cómo le queda cada talla a quien pregunta. NUNCA falla por falta de datos: si no hay medidas o no hay tabla de tallas, lo dice en la respuesta en vez de devolver un error.'; tablas = @('medida_cliente','medida_talla','talla') }
      )}
  )
  tablas = @(
    @{ n = 'medida_cliente';    propia = $true  },
    @{ n = 'medida_talla';      propia = $true  },
    @{ n = 'cliente';           propia = $false },
    @{ n = 'variante_producto'; propia = $false },
    @{ n = 'producto';          propia = $false },
    @{ n = 'imagen_producto';   propia = $false },
    @{ n = 'talla';             propia = $false }
  )
},

# ------------------------------------------------------------------ P10 --
@{
  nombre = '4.3 Subsistema 10 — Inteligencia Artificial'
  nota   = "SUBSISTEMA 10 = PAQUETE P10 del análisis 2.1`n`nCU-33 Recomendador de prendas,`nCU-34 Asistente conversacional,`nCU-35 Pedir un reporte por voz.`n`nBackend: modules/ia, y CU-35 en modules/reportes`n         backend/app/integrations/{recomendador,`n         asistente,interprete}`nFrontend: features/tienda/para-vos, tienda/asistente,`n          features/reportes/exportar`nMóvil: pantalla_para_vos, pantalla_asistente,`n       pantalla_reporte_por_voz`n`nVerde: implementado. Azul: tabla de otro subsistema.`n`nMIRAR LA FORMA DEL DIBUJO: tres pantallas, cinco`nendpoints... y DIECISIETE tablas, de las que una sola es`npropia. Eso no es un defecto, es la propiedad que define`na P10: CONSUME de todos y ninguno lo consulta. No tiene`nninguna flecha entrante, y por eso se lo puede apagar sin`nque deje de funcionar nada: si el modelo externo no`nresponde, las tres pantallas dicen que no está disponible`ny el resto del sistema no se entera.`n`nLO QUE SE LE PASA AL MODELO SE RESUELVE EN CADA PEDIDO,`nno se guarda: solo filas ACTIVAS, y siempre el par`nid → nombre, para que la respuesta pueda referirse a algo`nque existe de verdad.`n`nLa conversación de CU-34 vive en el cliente: sobrevive a`nla navegación SIN tocar la base. La única tabla propia es`nrecomendacion, que es una caché para no volver a pagarle`nal modelo por la misma respuesta."
  grupos = @(
    @{ form = 'ParaVos'; nf = 'features/tienda/para-vos/para-vos.ts y mobile/lib/features/catalogo/pantalla_para_vos.dart'; clases = @(
        @{ n = 'mis_recomendaciones'; nc = 'GET /api/v1/tienda/recomendaciones. Arma el perfil con lo que el cliente compró y marcó como favorito, propone candidatas ofrecibles de la temporada vigente y las guarda. El parámetro `forzar` vuelve a generar aunque la guardada siga vigente: es para la demostración.'; tablas = @('recomendacion','cliente','favorito','venta','detalle_venta','producto','variante_producto','categoria','talla','temporada','existencia') }
      )},
    @{ form = 'Asistente'; nf = 'features/tienda/asistente/asistente.ts y mobile/lib/features/asistente/pantalla_asistente.dart. La conversación vive en el cliente: no hay tabla que la guarde.'; clases = @(
        @{ n = 'hay_asistente'; nc = 'GET /api/v1/asistente/disponible. Lo primero que pregunta la pantalla. No consulta ninguna tabla.'; tablas = @() },
        @{ n = 'preguntar';     nc = 'POST /api/v1/asistente. Arma el contexto del momento --- catálogo ofrecible, colores y tallas de cada prenda, la tabla de tallas en centímetros, promociones vigentes, sucursales, y los pedidos y reservas de quien pregunta --- y se lo pasa al modelo.'; tablas = @('producto','variante_producto','categoria','color','talla','medida_talla','venta','reserva','sucursal','promocion','existencia') }
      )},
    @{ form = 'Exportar'; nf = 'features/reportes/exportar/exportar.ts y mobile/lib/features/reportes/pantalla_reporte_por_voz.dart. Es la MISMA pantalla que usa P11: el dictado es una entrada más del exportador, no una pantalla aparte.'; clases = @(
        @{ n = 'hay_pedido_por_voz'; nc = 'GET /api/v1/reportes/voz/disponible. Sin esto el botón del micrófono aparecería y no haría nada.'; tablas = @() },
        @{ n = 'pedir_por_voz';      nc = 'POST /api/v1/reportes/voz. NO devuelve el archivo: devuelve QUÉ ENTENDIÓ y la URL para bajarlo, así se puede leer «entendí: ventas de septiembre, en Excel» antes de descargar. Si no entiende NO adivina: entregar lo más parecido es como se termina mandando el reporte equivocado. El «hoy» va en hora boliviana.'; tablas = @('sucursal','proveedor','temporada') }
      )}
  )
  tablas = @(
    @{ n = 'recomendacion';     propia = $true  },
    @{ n = 'cliente';           propia = $false },
    @{ n = 'favorito';          propia = $false },
    @{ n = 'venta';             propia = $false },
    @{ n = 'detalle_venta';     propia = $false },
    @{ n = 'producto';          propia = $false },
    @{ n = 'variante_producto'; propia = $false },
    @{ n = 'categoria';         propia = $false },
    @{ n = 'color';             propia = $false },
    @{ n = 'talla';             propia = $false },
    @{ n = 'temporada';         propia = $false },
    @{ n = 'medida_talla';      propia = $false },
    @{ n = 'promocion';         propia = $false },
    @{ n = 'existencia';        propia = $false },
    @{ n = 'reserva';           propia = $false },
    @{ n = 'sucursal';          propia = $false },
    @{ n = 'proveedor';         propia = $false }
  )
},

# ------------------------------------------------------------------ P11 --
@{
  nombre = '4.3 Subsistema 11 — Reportes y Tablero'
  nota   = "SUBSISTEMA 11 = PAQUETE P11 del análisis 2.1`n`nCU-36 Tablero de indicadores,`nCU-37 Generar reportes exportables.`n`nBackend: backend/app/modules/reportes`n         reportes/exportador.py (PDF y Excel)`nFrontend: features/reportes/tablero, reportes/exportar`nMóvil: pantalla_tablero, pantalla_reportes`n`nAzul: TODAS las tablas son de otro subsistema.`n`nNO TIENE NINGUNA TABLA PROPIA, y eso es lo que dice el`ndiagrama: P11 es de SOLO LECTURA. Nunca escribe, y por`neso agregar un reporte no puede romper una venta. Es la`nmisma propiedad que P5, un ciclo más arriba.`n`nTRES COSAS QUE VALE LA PENA MIRAR:`n· El catálogo de reportes se PIDE, no está escrito a mano`n  en la pantalla: si se agrega un reporte, aparece solo.`n  Sin eso, agregar el sexto obliga a tocar el backend y`n  la web, y alguien se olvida de la segunda mitad.`n· La extensión va en la RUTA (/ventas.pdf) y no en un`n  parámetro, así el navegador sabe qué es sin mirar las`n  cabeceras y el archivo ya se guarda con su nombre.`n· El ENCARGADO no elige sucursal: se le impone la suya,`n  y por eso tampoco se le ofrece ese filtro.`n`nLos cortes de día van en HORA BOLIVIANA, por`napp/core/tiempo.py: con UTC, una venta de las 21:00 del`n15 contaría en el 16.`n`nLa banda de tablas va en DOS FILAS: son dieciséis."
  grupos = @(
    @{ form = 'Tablero'; nf = 'features/reportes/tablero/tablero.ts y mobile/lib/features/gestion/pantalla_tablero.dart'; clases = @(
        @{ n = 'consultar_tablero'; nc = 'GET /api/v1/reportes/tablero. Los indicadores del período: ventas y monto, reservas por estado, prendas probadas, salud del inventario y los más vendidos y más reservados. Un indicador que todavía no se puede calcular viaja con disponible=false y su motivo, en vez de mentir con un cero.'; tablas = @('venta','detalle_venta','reserva','reserva_detalle','existencia','variante_producto','producto','talla','color','sucursal') }
      )},
    @{ form = 'Exportar'; nf = 'features/reportes/exportar/exportar.ts y mobile/lib/features/gestion/pantalla_reportes.dart. La misma pantalla desde la que P10 escucha el dictado.'; clases = @(
        @{ n = 'catalogo_de_reportes'; nc = 'GET /api/v1/reportes/catalogo. Qué reportes hay, qué columnas trae cada uno y qué filtros acepta, con sus opciones YA resueltas desde la base: pedirlas por separado serían tres consultas más y tres formas de quedar desincronizada con lo que el reporte de verdad acepta.'; tablas = @('sucursal','proveedor','temporada') },
        @{ n = 'descargar';            nc = 'GET /api/v1/reportes/{tipo}.{formato}. Los cinco reportes --- ventas, inventario, movimientos, reservas, rendimiento por temporada y compras a proveedores --- en PDF o Excel, por el mismo exportador.'; tablas = @('venta','detalle_venta','existencia','movimiento_inventario','reserva','cliente','usuario','sucursal','proveedor','temporada','coleccion','producto','variante_producto','talla','color') }
      )}
  )
  tablas = @(
    @{ n = 'venta';                propia = $false },
    @{ n = 'detalle_venta';        propia = $false },
    @{ n = 'reserva';              propia = $false },
    @{ n = 'reserva_detalle';      propia = $false },
    @{ n = 'existencia';           propia = $false },
    @{ n = 'movimiento_inventario';propia = $false },
    @{ n = 'variante_producto';    propia = $false },
    @{ n = 'producto';             propia = $false },
    @{ n = 'talla';                propia = $false },
    @{ n = 'color';                propia = $false },
    @{ n = 'coleccion';            propia = $false },
    @{ n = 'temporada';            propia = $false },
    @{ n = 'sucursal';             propia = $false },
    @{ n = 'proveedor';            propia = $false },
    @{ n = 'cliente';              propia = $false },
    @{ n = 'usuario';              propia = $false }
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
        $x0 = $MARGEN_X + ($col * $COL_STEP)

        for ($i = 0; $i -lt $n; $i++) {
            $c = $g.clases[$i]
            $cx = $x0 + ([math]::Floor($i / 2) * $COL_STEP)
            $cy = if ($i % 2 -eq 0) { $Y_CLS_A } else { $Y_CLS_B }
            $e = New-Comp $c.n 'CLASS' $c.nc
            # Azul tambien para un «CLASS» que es de OTRO subsistema, con el
            # mismo criterio que ya tenian las tablas. Pasa en P8 y en P9: sus
            # pantallas llaman a un endpoint que no es suyo, y pintarlo verde
            # diria que el subsistema lo implementa.
            Poner $dia $e $cx $cy $COL_W $H_CLS $(if ($c.ajena) { $AZUL } else { $VERDE })
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
    # Con mas de $TAB_2_FILAS_DESDE tablas la banda se reparte en DOS FILAS,
    # por la misma razon que la banda «CLASS»: P7 tiene dieciocho tablas y en
    # una sola fila el diagrama pasaria de los 3600 px, con lo que el texto no
    # se lee al exportarlo. Los seis subsistemas del Ciclo 2 tienen ocho o
    # menos, asi que ninguno de ellos cambia.
    $elTabla = @{}
    $nt = $sub.tablas.Count
    $dosFilas = $nt -gt $TAB_2_FILAS_DESDE
    $colsTabla = if ($dosFilas) { [math]::Ceiling($nt / 2) } else { $nt }
    $anchoTablas = $colsTabla * $TAB_STEP
    $tx0 = $MARGEN_X + [math]::Max(0, [int](($anchoTotal - $anchoTablas) / 2))
    for ($i = 0; $i -lt $nt; $i++) {
        $t = $sub.tablas[$i]
        $e = New-Comp $t.n 'TABLA' "Tabla $($t.n) del esquema de 3.3.1."
        $tcx = if ($dosFilas) { $tx0 + ([math]::Floor($i / 2) * $TAB_STEP) } else { $tx0 + ($i * $TAB_STEP) }
        $tcy = if ($dosFilas -and ($i % 2 -ne 0)) { $Y_TABLA_B } else { $Y_TABLA }
        Poner $dia $e $tcx $tcy $TAB_W $H_TABLA $(if ($t.propia) { $VERDE } else { $AZUL })
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
    # A la derecha de lo MAS ANCHO de las tres bandas, no solo de «CLASS»: en
    # P8 la banda de tablas es el triple de ancha que la de endpoints, y con el
    # calculo viejo la nota caia encima de ella.
    Poner $dia $nota ($MARGEN_X + [math]::Max($anchoTotal, $anchoTablas) + 60) $Y_FORM 420 400 $null

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
