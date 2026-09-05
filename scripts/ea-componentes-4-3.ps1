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
