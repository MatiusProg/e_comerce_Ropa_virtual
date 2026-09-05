# =========================================================================
# CAP. 2 - 2.3 Analisis de Clases: un diagrama de clases por caso de uso.
#
# ---- POR QUE ESTAS CLASES SON ELEMENTOS APARTE (decision del 04/09/2026) ----
#
# EA dibuja el icono redondo de robustez SOLO para los estereotipos que se
# llaman exactamente 'boundary', 'control' y 'entity'. Con cualquier otro nombre
# --- 'frontera', 'controlador', 'entidad' --- dibuja la clase como tabla, con
# sus atributos y operaciones. No hay forma de desactivar el icono por diagrama:
# se probaron StereoIcon, UseStereoIcon, ShowIcon, UCRect, SPT, NoIcon,
# ShapeScript e IsIcon en DiagramObject.Style, y ninguna surte efecto.
#
# Como 2.2 necesita el formato redondo y 2.3 el de tabla, y un mismo elemento no
# puede verse de las dos maneras, las clases de 2.3 son ELEMENTOS DISTINTOS de
# las de 2.2, con el mismo nombre. Viven en su propio paquete y usan los
# estereotipos en espanol.
#
# Cuidado si se cambia un estereotipo a mano: EA guarda ademas la aplicacion del
# perfil, y el elemento queda con StereotypeEx = "entidad,entity" --- el viejo
# sigue activo por debajo y el icono no desaparece. Hay que asignar tambien
# StereotypeEx.
#
# ---- NIVEL DE DETALLE ----
# Tomado del modelo de dominio de referencia: atributos privados con su tipo de
# la base de datos, y asociaciones con NOMBRE DE ROL en mayusculas y
# CARDINALIDAD en los dos extremos. De estas clases sale el diseno de datos
# logico de 3.3.1, asi que los tipos son los del esquema real.
#
# Los nombres de las operaciones son los REALES del codigo:
#   «frontera»    -> el componente Angular y el endpoint de router.py
#   «controlador» -> las funciones de service.py y de core/security.py
#   «entidad»     -> los atributos son las columnas de models.py; las
#                    operaciones, las funciones de repository.py que acceden a
#                    esa tabla.
#
# ADITIVO: abre el modelo y solo agrega lo que falta.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

function Get-OCrearPaqueteModelo($padre, $nombre) {
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

$root     = $ea.Models.GetAt(0)
$pRaiz = Get-OCrearPaqueteModelo $root 'Violet Boutique'
$pCap2    = Get-OCrearPaqueteModelo $pRaiz 'CAP. 2 - Flujo de Trabajo: Analisis'
$p23      = Get-OCrearPaqueteModelo $pCap2 '2.3 Analisis de Clases'

# =========================================================================
# PASO 1 - Devolver a 2.2 sus estereotipos en ingles.
# Si una pasada anterior los dejo en espanol, los diagramas de comunicacion
# perdieron el icono redondo. Aqui se restauran.
# =========================================================================
$aIngles = @{ 'frontera'='boundary'; 'controlador'='control'; 'entidad'='entity' }
$p22Clases = BuscarPaquete $root 'Clases de Analisis'
if ($p22Clases) {
    foreach ($e in $p22Clases.Elements) {
        if ($aIngles.ContainsKey($e.Stereotype)) {
            $e.Stereotype   = $aIngles[$e.Stereotype]
            $e.StereotypeEx = $e.Stereotype    # borra la aplicacion del perfil viejo
            [void]$e.Update()
            Write-Output "  2.2 restaurado: $($e.Name) -> «$($e.Stereotype)»"
        }
    }
}

# =========================================================================
# PASO 2 - Las clases de 2.3, elementos propios en su propio paquete.
# =========================================================================
function Get-OCrearClase23($nombre, $estereotipo, $notas) {
    foreach ($e in $p23.Elements) {
        if ($e.Type -eq 'Class' -and $e.Name -eq $nombre) { return $e }
    }
    $e = $p23.Elements.AddNew($nombre, 'Class')
    $e.Stereotype   = $estereotipo
    $e.StereotypeEx = $estereotipo
    if ($notas) { $e.Notes = $notas }
    [void]$e.Update(); $p23.Elements.Refresh()
    return $e
}

function Set-Atributos($el, $lista) {
    $ya = @{}
    foreach ($a in $el.Attributes) { $ya[$a.Name] = $a }
    $i = 0
    foreach ($def in $lista) {
        if ($ya.ContainsKey($def.n)) { $at = $ya[$def.n] }
        else { $at = $el.Attributes.AddNew($def.n, $def.t) }
        $at.Type = $def.t
        $at.Visibility = 'Private'
        $at.Pos = $i
        [void]$at.Update()
        $i++
    }
    $el.Attributes.Refresh()
}

function Set-Operaciones($el, $lista) {
    $ya = @{}
    foreach ($m in $el.Methods) { $ya[$m.Name] = $true }
    $i = 0
    foreach ($op in $lista) {
        if (-not $ya.ContainsKey($op.n)) {
            $m = $el.Methods.AddNew($op.n, $op.r)
            $m.Visibility = if ($op.n.StartsWith('_')) { 'Private' } else { 'Public' }
            $m.Pos = $i
            [void]$m.Update()
            $j = 0
            foreach ($par in $op.p) {
                $pa = $m.Parameters.AddNew($par.n, $par.t); $pa.Position = $j; $j++
                [void]$pa.Update()
            }
            $m.Parameters.Refresh()
        }
        $i++
    }
    $el.Methods.Refresh()
}

# Decision del 04/09/2026: la union entre dos clases es SIEMPRE una
# Association, con rol en mayusculas y cardinalidad en los dos extremos.
# Nada de Dependency, Usage, Aggregation ni Composition entre clases: con un
# solo tipo de linea el lector compara los diagramas del capitulo entre si sin
# interpretar la semantica de cada estilo. Vale para los casos de uso que
# faltan; CU-01 y CU-02 quedan como estan.
function New-Asociacion($src, $dst, $rol, $cardOrigen, $cardDestino) {
    foreach ($c in $src.Connectors) {
        if ($c.SupplierID -eq $dst.ElementID -and $c.Type -eq 'Association' -and $c.Name -eq $rol) { return }
    }
    $c = $src.Connectors.AddNew($rol, 'Association')
    $c.SupplierID = $dst.ElementID
    $c.Direction = 'Source -> Destination'
    [void]$c.Update()
    $c.ClientEnd.Cardinality = $cardOrigen; $c.SupplierEnd.Cardinality = $cardDestino
    [void]$c.ClientEnd.Update(); [void]$c.SupplierEnd.Update(); [void]$c.Update()
    $src.Connectors.Refresh()
}

function Poner($dia, $el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l+$ancho);t=$t;b=$($t-$alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
}

# ---- CU-01 Registrar cliente ----

$frm = Get-OCrearClase23 'FormularioRegistro' 'frontera' 'Frontera del caso de uso en sus dos extremos: la pantalla de registro (frontend-web/src/app/features/auth/registro) y el endpoint POST /api/v1/auth/registro de app/modules/seguridad/router.py.'
$gst = Get-OCrearClase23 'GestorRegistro' 'controlador' 'app/modules/seguridad/service.py. Coordina el caso de uso y delimita la transaccion.'
$seg = Get-OCrearClase23 'Seguridad' 'controlador' 'app/core/security.py. No conoce la base de datos ni HTTP: solo transforma datos.'
$usu = Get-OCrearClase23 'Usuario' 'entidad' 'Tabla usuario. Atributos = sus columnas; operaciones = las funciones de repository.py que la consultan.'
$rol = Get-OCrearClase23 'Rol' 'entidad' 'Tabla rol.'
$cli = Get-OCrearClase23 'Cliente' 'entidad' 'Tabla cliente.'

Set-Operaciones $frm @(
  @{n='enviar';            r='void'; p=@()},
  @{n='irALogin';          r='void'; p=@()},
  @{n='registrar';         r='Observable<ClienteRegistradoOut>'; p=@(@{n='datos';t='ClienteRegistroIn'})},
  @{n='registrar_cliente'; r='ClienteRegistradoOut'; p=@(@{n='datos';t='ClienteRegistroIn'}, @{n='db';t='Session'})}
)
Set-Operaciones $gst @(
  @{n='registrar_cliente'; r='ClienteRegistradoOut'; p=@(@{n='db';t='Session'}, @{n='datos';t='ClienteRegistroIn'})},
  @{n='_viola';            r='bool'; p=@(@{n='exc';t='IntegrityError'}, @{n='tabla';t='str'}, @{n='columna';t='str'})}
)
Set-Operaciones $seg @(
  @{n='hash_password';   r='str';  p=@(@{n='password';t='str'})},
  @{n='verify_password'; r='bool'; p=@(@{n='password';t='str'}, @{n='hashed';t='str'})}
)

Set-Atributos $usu @(
  @{n='id';t='BIGSERIAL'}, @{n='correo';t='VARCHAR(120)'}, @{n='hash_contrasena';t='VARCHAR(255)'},
  @{n='nombres';t='VARCHAR(80)'}, @{n='apellidos';t='VARCHAR(80)'}, @{n='rol_id';t='SMALLINT'},
  @{n='activo';t='BOOLEAN'}, @{n='creado_en';t='TIMESTAMPTZ'}, @{n='actualizado_en';t='TIMESTAMPTZ'}
)
Set-Operaciones $usu @(
  @{n='obtener_usuario_por_correo'; r='Usuario'; p=@(@{n='db';t='Session'}, @{n='correo';t='str'})},
  @{n='agregar_usuario';            r='Usuario'; p=@(@{n='db';t='Session'}, @{n='datos';t='ClienteRegistroIn'}, @{n='rol_id';t='int'})}
)

Set-Atributos $rol @(
  @{n='id';t='SMALLSERIAL'}, @{n='nombre';t='VARCHAR(30)'}, @{n='descripcion';t='VARCHAR(150)'}
)
Set-Operaciones $rol @(
  @{n='obtener_rol_por_nombre'; r='Rol'; p=@(@{n='db';t='Session'}, @{n='nombre';t='str'})}
)

Set-Atributos $cli @(
  @{n='id';t='BIGSERIAL'}, @{n='usuario_id';t='BIGINT'}, @{n='documento';t='VARCHAR(20)'},
  @{n='telefono';t='VARCHAR(20)'}, @{n='talla_superior';t='VARCHAR(10)'},
  @{n='talla_inferior';t='VARCHAR(10)'}, @{n='talla_calzado';t='VARCHAR(10)'},
  @{n='creado_en';t='TIMESTAMPTZ'}, @{n='actualizado_en';t='TIMESTAMPTZ'}
)
Set-Operaciones $cli @(
  @{n='agregar_cliente';              r='Cliente'; p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'}, @{n='datos';t='ClienteRegistroIn'})},
  @{n='existe_cliente_con_documento'; r='bool';    p=@(@{n='db';t='Session'}, @{n='documento';t='str'})}
)

New-Asociacion $frm $gst 'DELEGA_EN'   '1'    '1'
New-Asociacion $gst $seg 'USA'         '1'    '1'
New-Asociacion $gst $rol 'CONSULTA'    '1'    '1'
New-Asociacion $gst $usu 'CREA'        '1'    '0..*'
New-Asociacion $gst $cli 'CREA'        '1'    '0..*'
New-Asociacion $usu $rol 'TIENE'       '0..*' '1'
New-Asociacion $cli $usu 'PERTENECE_A' '1'    '1'

$nombre = '2.3 CU-01 Registrar cliente'
if (BuscarDiagrama $p23 $nombre) {
    Write-Output "  $nombre ya existe, no se toca"
} else {
    $d = $p23.Diagrams.AddNew($nombre, 'Logical')
    [void]$d.Update(); $p23.Diagrams.Refresh()
    Poner $d $frm   40 -120 300 200
    Poner $d $gst  440 -120 340 200
    Poner $d $seg  440 -420 320 160
    Poner $d $rol  900  -40 300 200
    Poner $d $usu  900 -300 320 300
    Poner $d $cli  900 -660 340 320
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    Write-Output "  $nombre : $($d.DiagramObjects.Count) clases, $($d.DiagramLinks.Count) asociaciones"
}

# ---- CU-02 Iniciar y cerrar sesion ----
#
# Reaparecen Seguridad, Usuario y Rol, que ya creó CU-01: son las mismas
# clases y se les AGREGAN las operaciones de este caso de uso. Por eso las
# listas de abajo repiten las de CU-01 --- Set-Operaciones solo da de alta lo
# que falta, y asi las nuevas quedan despues de las viejas.
#
# La sucursal que viaja en el token la resuelve repository.obtener_sucursal_de_
# usuario() contra la tabla empleado. No se dibuja Empleado porque el 2.2 de
# este caso de uso no la tiene y es una lectura auxiliar, no una colaboracion.

$flg = Get-OCrearClase23 'FormularioLogin' 'frontera' 'Frontera del caso de uso en sus dos extremos: la pantalla de acceso (frontend-web/src/app/features/auth/login) con AuthService, y los endpoints POST /api/v1/auth/login, POST /api/v1/auth/logout y GET /api/v1/auth/yo de app/modules/seguridad/router.py.'
$gau = Get-OCrearClase23 'GestorAutenticacion' 'controlador' 'app/modules/seguridad/service.py, seccion CU-02. Verifica credenciales, emite el token y registra o revoca la sesion; delimita la transaccion.'
$ses = Get-OCrearClase23 'SesionToken' 'entidad' 'Tabla sesion_token. Es la fila que permite revocar un token antes de que expire: sin ella, cerrar sesion o desactivar una cuenta no tendrian efecto inmediato. Su ciclo de vida es el diagrama de estado de 3.2.'

Set-Operaciones $flg @(
  @{n='enviar';              r='void'; p=@()},
  @{n='iniciarSesion';       r='Observable<UsuarioAutenticado>';       p=@(@{n='datos';t='LoginIn'})},
  @{n='cerrarSesion';        r='void';                                 p=@()},
  @{n='restaurarSesion';     r='Observable<UsuarioAutenticado|null>';  p=@()},
  @{n='iniciar_sesion';      r='TokenOut';                p=@(@{n='datos';t='LoginIn'}, @{n='db';t='Session'})},
  @{n='cerrar_sesion';       r='None';                    p=@(@{n='usuario';t='Usuario'}, @{n='db';t='Session'})},
  @{n='usuario_autenticado'; r='UsuarioAutenticadoOut';   p=@(@{n='usuario';t='Usuario'}, @{n='db';t='Session'})}
)
Set-Operaciones $gau @(
  @{n='autenticar';                  r='TokenOut';               p=@(@{n='db';t='Session'}, @{n='datos';t='LoginIn'})},
  @{n='cerrar_sesion';               r='None';                   p=@(@{n='db';t='Session'}, @{n='jti';t='UUID'})},
  @{n='obtener_usuario_autenticado'; r='UsuarioAutenticadoOut';  p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'})}
)

# Las dos primeras ya existen desde CU-01; se listan para conservar el orden.
Set-Operaciones $seg @(
  @{n='hash_password';       r='str';           p=@(@{n='password';t='str'})},
  @{n='verify_password';     r='bool';          p=@(@{n='password';t='str'}, @{n='hashed';t='str'})},
  @{n='crear_access_token';  r='TokenEmitido';  p=@(@{n='usuario_id';t='int'}, @{n='rol';t='str'}, @{n='sucursal_id';t='int'}, @{n='vigencia';t='timedelta'})},
  @{n='decodificar_token';   r='dict';          p=@(@{n='token';t='str'})}
)
Set-Operaciones $usu @(
  @{n='obtener_usuario_por_correo'; r='Usuario'; p=@(@{n='db';t='Session'}, @{n='correo';t='str'})},
  @{n='agregar_usuario';            r='Usuario'; p=@(@{n='db';t='Session'}, @{n='datos';t='ClienteRegistroIn'}, @{n='rol_id';t='int'})},
  @{n='obtener_usuario_con_rol';    r='Usuario'; p=@(@{n='db';t='Session'}, @{n='correo';t='str'})},
  @{n='obtener_usuario_con_id';     r='Usuario'; p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'})}
)

Set-Atributos $ses @(
  @{n='id';t='BIGSERIAL'}, @{n='usuario_id';t='BIGINT'}, @{n='jti';t='UUID'},
  @{n='emitido_en';t='TIMESTAMPTZ'}, @{n='expira_en';t='TIMESTAMPTZ'},
  @{n='revocado_en';t='TIMESTAMPTZ'}
)
Set-Operaciones $ses @(
  @{n='agregar_sesion';              r='SesionToken'; p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'}, @{n='jti';t='UUID'}, @{n='expira_en';t='datetime'})},
  @{n='obtener_sesion_por_jti';      r='SesionToken'; p=@(@{n='db';t='Session'}, @{n='jti';t='UUID'})},
  @{n='revocar_sesion';              r='int';         p=@(@{n='db';t='Session'}, @{n='jti';t='UUID'})},
  @{n='revocar_sesiones_de_usuario'; r='int';         p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'})}
)

New-Asociacion $flg $gau 'DELEGA_EN'   '1'    '1'
New-Asociacion $gau $seg 'USA'         '1'    '1'
New-Asociacion $gau $usu 'AUTENTICA'   '1'    '0..*'
New-Asociacion $gau $ses 'REGISTRA'    '1'    '0..*'
New-Asociacion $ses $usu 'PERTENECE_A' '0..*' '1'
# Usuario --TIENE--> Rol ya la creo CU-01; EA la dibuja igual en este diagrama.

$nombre = '2.3 CU-02 Iniciar y cerrar sesión'
if (BuscarDiagrama $p23 $nombre) {
    Write-Output "  $nombre ya existe, no se toca"
} else {
    $d = $p23.Diagrams.AddNew($nombre, 'Logical')
    [void]$d.Update(); $p23.Diagrams.Refresh()
    Poner $d $flg   40 -120 320 280
    Poner $d $gau  460 -120 360 200
    Poner $d $seg  460 -460 360 220
    Poner $d $rol  920  -40 300 200
    Poner $d $usu  920 -300 340 340
    Poner $d $ses  920 -700 360 300
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    Write-Output "  $nombre : $($d.DiagramObjects.Count) clases, $($d.DiagramLinks.Count) asociaciones"
}


# =========================================================================
# CU-03 a CU-09. Mismas convenciones que CU-01 y CU-02:
#   - clases propias de 2.3, con los estereotipos en espanol;
#   - atributos = columnas reales de models.py, con el tipo de PostgreSQL;
#   - operaciones = nombres reales del codigo (el servicio Angular y el
#     router.py en la frontera, service.py en el controlador, repository.py
#     en la entidad);
#   - toda union clase-clase es Association con rol y cardinalidad.
#
# GestorAutenticacion reaparece en los siete: es el guardian de
# app/core/dependencies.py que resuelve el token y exige el rol antes de que
# la pantalla llame a su gestor. Aqui se le agregan esas tres operaciones.
# =========================================================================

Set-Operaciones $gau @(
  @{n='autenticar';                  r='TokenOut';               p=@(@{n='db';t='Session'}, @{n='datos';t='LoginIn'})},
  @{n='cerrar_sesion';               r='None';                   p=@(@{n='db';t='Session'}, @{n='jti';t='UUID'})},
  @{n='obtener_usuario_autenticado'; r='UsuarioAutenticadoOut';  p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'})},
  @{n='get_usuario_actual';          r='UsuarioActual';          p=@(@{n='token';t='str'}, @{n='db';t='Session'})},
  @{n='requiere_roles';              r='Callable';               p=@(@{n='roles';t='str'})},
  @{n='verificar_ambito_sucursal';   r='None';                   p=@(@{n='usuario';t='UsuarioActual'}, @{n='sucursal_id';t='int'})}
)

# ---- CU-03 Gestionar usuarios y roles ----

$pus = Get-OCrearClase23 'PantallaUsuarios' 'frontera' 'Frontera del caso de uso en sus dos extremos: la pantalla de administracion (frontend-web/src/app/features/admin/usuarios) con UsuariosService, y los endpoints de /api/v1/usuarios de app/modules/seguridad/router.py.'
$gus = Get-OCrearClase23 'GestorUsuarios' 'controlador' 'app/modules/seguridad/service.py, seccion CU-03. Da de alta, edita, activa y elimina usuarios; al desactivar o borrar uno revoca sus sesiones vigentes.'

Set-Operaciones $pus @(
  @{n='roles';         r='Observable<RolAsignable[]>'; p=@()},
  @{n='listar';        r='Observable<PaginaUsuarios>'; p=@(@{n='filtros';t='FiltrosUsuarios'})},
  @{n='crear';         r='Observable<UsuarioResumen>'; p=@(@{n='datos';t='UsuarioCrear'})},
  @{n='editar';        r='Observable<UsuarioResumen>'; p=@(@{n='id';t='number'}, @{n='datos';t='UsuarioEditar'})},
  @{n='cambiarEstado'; r='Observable<UsuarioResumen>'; p=@(@{n='id';t='number'}, @{n='activo';t='boolean'})},
  @{n='eliminar';      r='Observable<void>';           p=@(@{n='id';t='number'})},
  @{n='listar_roles';     r='list[RolOut]';      p=@(@{n='db';t='Session'})},
  @{n='listar_usuarios';  r='PaginaUsuarios';    p=@(@{n='db';t='Session'}, @{n='filtros';t='FiltrosUsuarios'})},
  @{n='crear_usuario';    r='UsuarioResumenOut'; p=@(@{n='datos';t='UsuarioCrearIn'}, @{n='db';t='Session'})},
  @{n='obtener_usuario';  r='UsuarioResumenOut'; p=@(@{n='usuario_id';t='int'}, @{n='db';t='Session'})},
  @{n='editar_usuario';   r='UsuarioResumenOut'; p=@(@{n='usuario_id';t='int'}, @{n='datos';t='UsuarioEditarIn'}, @{n='db';t='Session'})},
  @{n='cambiar_estado';   r='UsuarioResumenOut'; p=@(@{n='usuario_id';t='int'}, @{n='activo';t='bool'}, @{n='db';t='Session'})},
  @{n='eliminar_usuario'; r='None';              p=@(@{n='usuario_id';t='int'}, @{n='db';t='Session'}, @{n='usuario';t='UsuarioActual'})}
)
Set-Operaciones $gus @(
  @{n='listar_roles';     r='list[RolOut]';      p=@(@{n='db';t='Session'})},
  @{n='listar_usuarios';  r='PaginaUsuarios';    p=@(@{n='db';t='Session'}, @{n='busqueda';t='str'}, @{n='rol_id';t='int'}, @{n='pagina';t='int'})},
  @{n='obtener_usuario';  r='UsuarioResumenOut'; p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'})},
  @{n='crear_usuario';    r='UsuarioResumenOut'; p=@(@{n='db';t='Session'}, @{n='datos';t='UsuarioCrearIn'})},
  @{n='editar_usuario';   r='UsuarioResumenOut'; p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'}, @{n='datos';t='UsuarioEditarIn'})},
  @{n='cambiar_estado';   r='UsuarioResumenOut'; p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'}, @{n='activo';t='bool'})},
  @{n='eliminar_usuario'; r='None';              p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'}, @{n='solicitante_id';t='int'})},
  @{n='_validar_ambito';  r='None';              p=@(@{n='db';t='Session'}, @{n='datos';t='UsuarioCrearIn'})},
  @{n='_fila_a_resumen';  r='UsuarioResumenOut'; p=@(@{n='fila';t='Row'})}
)
Set-Operaciones $usu @(
  @{n='obtener_usuario_por_correo';  r='Usuario'; p=@(@{n='db';t='Session'}, @{n='correo';t='str'})},
  @{n='agregar_usuario';             r='Usuario'; p=@(@{n='db';t='Session'}, @{n='datos';t='ClienteRegistroIn'}, @{n='rol_id';t='int'})},
  @{n='obtener_usuario_con_rol';     r='Usuario'; p=@(@{n='db';t='Session'}, @{n='correo';t='str'})},
  @{n='obtener_usuario_con_id';      r='Usuario'; p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'})},
  @{n='contar_y_listar_usuarios';    r='tuple[int, list[Row]]'; p=@(@{n='db';t='Session'}, @{n='busqueda';t='str'}, @{n='rol_id';t='int'})},
  @{n='obtener_detalle_usuario';     r='Row';  p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'})},
  @{n='tiene_operaciones_asociadas'; r='bool'; p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'})},
  @{n='eliminar_usuario';            r='None'; p=@(@{n='db';t='Session'}, @{n='usuario';t='Usuario'})}
)
Set-Operaciones $rol @(
  @{n='obtener_rol_por_nombre'; r='Rol';       p=@(@{n='db';t='Session'}, @{n='nombre';t='str'})},
  @{n='listar_roles';           r='list[Rol]'; p=@(@{n='db';t='Session'})}
)

New-Asociacion $pus $gus 'DELEGA_EN'    '1' '1'
New-Asociacion $pus $gau 'VERIFICA_CON' '1' '1'
New-Asociacion $gus $usu 'ADMINISTRA'   '1' '0..*'
New-Asociacion $gus $rol 'ASIGNA'       '1' '0..*'
New-Asociacion $gus $ses 'REVOCA'       '1' '0..*'

$nombre = '2.3 CU-03 Gestionar usuarios y roles'
if (BuscarDiagrama $p23 $nombre) {
    Write-Output "  $nombre ya existe, no se toca"
} else {
    $d = $p23.Diagrams.AddNew($nombre, 'Logical')
    [void]$d.Update(); $p23.Diagrams.Refresh()
    Poner $d $pus   40 -120 380 480
    Poner $d $gus  500 -120 400 360
    Poner $d $gau  500 -560 400 260
    Poner $d $rol  980  -40 320 200
    Poner $d $usu  980 -300 400 440
    Poner $d $ses  980 -800 380 300
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    Write-Output "  $nombre : $($d.DiagramObjects.Count) clases, $($d.DiagramLinks.Count) asociaciones"
}

# ---- CU-04 Gestionar perfil del cliente ----

$ppe = Get-OCrearClase23 'PantallaPerfil' 'frontera' 'Frontera del caso de uso en sus dos extremos: la pantalla del cliente (frontend-web/src/app/features/cliente/perfil) con PerfilService, y los endpoints de /api/v1/perfil de app/modules/seguridad/router.py.'
$gpe = Get-OCrearClase23 'GestorPerfil' 'controlador' 'app/modules/seguridad/service.py, seccion CU-04. Edita los datos del cliente, administra su libreta de direcciones y cambia la contrasena.'
$dir = Get-OCrearClase23 'DireccionCliente' 'entidad' 'Tabla direccion_cliente. Solo una fila por cliente puede tener predeterminada = true; el gestor desmarca las demas antes de marcar la nueva.'

Set-Operaciones $ppe @(
  @{n='obtener';              r='Observable<Perfil>';      p=@()},
  @{n='editar';               r='Observable<Perfil>';      p=@(@{n='datos';t='PerfilEditar'})},
  @{n='agregarDireccion';     r='Observable<Direccion[]>'; p=@(@{n='datos';t='DireccionCrear'})},
  @{n='marcarPredeterminada'; r='Observable<Direccion[]>'; p=@(@{n='id';t='number'})},
  @{n='eliminarDireccion';    r='Observable<Direccion[]>'; p=@(@{n='id';t='number'})},
  @{n='cambiarContrasena';    r='Observable<void>';        p=@(@{n='datos';t='CambioContrasena'})},
  @{n='obtener_perfil';        r='PerfilOut';          p=@(@{n='db';t='Session'}, @{n='usuario';t='UsuarioActual'})},
  @{n='editar_perfil';         r='PerfilOut';          p=@(@{n='datos';t='PerfilEditarIn'}, @{n='db';t='Session'}, @{n='usuario';t='UsuarioActual'})},
  @{n='agregar_direccion';     r='list[DireccionOut]'; p=@(@{n='datos';t='DireccionCrearIn'}, @{n='db';t='Session'}, @{n='usuario';t='UsuarioActual'})},
  @{n='marcar_predeterminada'; r='list[DireccionOut]'; p=@(@{n='direccion_id';t='int'}, @{n='db';t='Session'}, @{n='usuario';t='UsuarioActual'})},
  @{n='eliminar_direccion';    r='list[DireccionOut]'; p=@(@{n='direccion_id';t='int'}, @{n='db';t='Session'}, @{n='usuario';t='UsuarioActual'})},
  @{n='cambiar_contrasena';    r='None';               p=@(@{n='datos';t='CambioContrasenaIn'}, @{n='db';t='Session'}, @{n='usuario';t='UsuarioActual'})}
)
Set-Operaciones $gpe @(
  @{n='obtener_perfil';                  r='PerfilOut';          p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'})},
  @{n='editar_perfil';                   r='PerfilOut';          p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'}, @{n='datos';t='PerfilEditarIn'})},
  @{n='agregar_direccion';               r='list[DireccionOut]'; p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'}, @{n='datos';t='DireccionCrearIn'})},
  @{n='marcar_direccion_predeterminada'; r='list[DireccionOut]'; p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'}, @{n='direccion_id';t='int'})},
  @{n='eliminar_direccion';              r='list[DireccionOut]'; p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'}, @{n='direccion_id';t='int'})},
  @{n='cambiar_contrasena';              r='None';               p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'}, @{n='datos';t='CambioContrasenaIn'})},
  @{n='_cliente_del_usuario';            r='Cliente';            p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'})},
  @{n='_direcciones';                    r='list[DireccionOut]'; p=@(@{n='db';t='Session'}, @{n='cliente_id';t='int'})}
)
Set-Operaciones $cli @(
  @{n='agregar_cliente';              r='Cliente'; p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'}, @{n='datos';t='ClienteRegistroIn'})},
  @{n='existe_cliente_con_documento'; r='bool';    p=@(@{n='db';t='Session'}, @{n='documento';t='str'})},
  @{n='obtener_cliente_de_usuario';   r='Cliente'; p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'})}
)

Set-Atributos $dir @(
  @{n='id';t='BIGSERIAL'}, @{n='cliente_id';t='BIGINT'}, @{n='ciudad_id';t='INTEGER'},
  @{n='alias';t='VARCHAR(40)'}, @{n='direccion';t='VARCHAR(200)'},
  @{n='referencia';t='VARCHAR(200)'}, @{n='predeterminada';t='BOOLEAN'},
  @{n='creado_en';t='TIMESTAMPTZ'}, @{n='actualizado_en';t='TIMESTAMPTZ'}
)
Set-Operaciones $dir @(
  @{n='listar_direcciones';        r='list[Row]';        p=@(@{n='db';t='Session'}, @{n='cliente_id';t='int'})},
  @{n='obtener_direccion';         r='DireccionCliente'; p=@(@{n='db';t='Session'}, @{n='direccion_id';t='int'}, @{n='cliente_id';t='int'})},
  @{n='agregar_direccion';         r='DireccionCliente'; p=@(@{n='db';t='Session'}, @{n='cliente_id';t='int'}, @{n='datos';t='DireccionCrearIn'})},
  @{n='desmarcar_predeterminadas'; r='None';             p=@(@{n='db';t='Session'}, @{n='cliente_id';t='int'})},
  @{n='eliminar_direccion';        r='None';             p=@(@{n='db';t='Session'}, @{n='direccion';t='DireccionCliente'})}
)

New-Asociacion $ppe $gpe 'DELEGA_EN'    '1'    '1'
New-Asociacion $ppe $gau 'VERIFICA_CON' '1'    '1'
New-Asociacion $gpe $cli 'ADMINISTRA'   '1'    '1'
New-Asociacion $gpe $dir 'ADMINISTRA'   '1'    '0..*'
New-Asociacion $gpe $usu 'ACTUALIZA'    '1'    '1'
New-Asociacion $dir $cli 'PERTENECE_A'  '0..*' '1'

$nombre = '2.3 CU-04 Gestionar perfil del cliente'
if (BuscarDiagrama $p23 $nombre) {
    Write-Output "  $nombre ya existe, no se toca"
} else {
    $d = $p23.Diagrams.AddNew($nombre, 'Logical')
    [void]$d.Update(); $p23.Diagrams.Refresh()
    Poner $d $ppe   40 -120 380 460
    Poner $d $gpe  500 -120 420 340
    Poner $d $gau  500 -540 400 260
    Poner $d $usu 1000  -40 400 440
    Poner $d $cli 1000 -540 380 340
    Poner $d $dir 1000 -940 380 360
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    Write-Output "  $nombre : $($d.DiagramObjects.Count) clases, $($d.DiagramLinks.Count) asociaciones"
}

# ---- CU-05 Gestionar ciudades y sucursales ----

$psu = Get-OCrearClase23 'PantallaSucursales' 'frontera' 'Frontera del caso de uso en sus dos extremos: las pantallas de administracion (frontend-web/src/app/features/admin/ciudades y .../sucursales) con OrganizacionService, y los endpoints de /api/v1/organizacion de app/modules/organizacion/router.py.'
$gor = Get-OCrearClase23 'GestorOrganizacion' 'controlador' 'app/modules/organizacion/service.py. Administra el catalogo geografico: la ciudad no se puede borrar si tiene sucursales, y la sucursal no se borra nunca, solo se desactiva.'
$ciu = Get-OCrearClase23 'Ciudad' 'entidad' 'Tabla ciudad.'
$suc = Get-OCrearClase23 'Sucursal' 'entidad' 'Tabla sucursal. Su horario y su capacidad de vestidores son los que consumen las reservas del Ciclo 2.'

Set-Operaciones $psu @(
  @{n='listarCiudades';         r='Observable<Ciudad[]>';    p=@(@{n='busqueda';t='string'})},
  @{n='crearCiudad';            r='Observable<Ciudad>';      p=@(@{n='datos';t='CiudadCrear'})},
  @{n='editarCiudad';           r='Observable<Ciudad>';      p=@(@{n='id';t='number'}, @{n='datos';t='CiudadEditar'})},
  @{n='eliminarCiudad';         r='Observable<void>';        p=@(@{n='id';t='number'})},
  @{n='listarSucursales';       r='Observable<Sucursal[]>';  p=@(@{n='filtros';t='FiltrosSucursales'})},
  @{n='crearSucursal';          r='Observable<Sucursal>';    p=@(@{n='datos';t='SucursalCrear'})},
  @{n='editarSucursal';         r='Observable<Sucursal>';    p=@(@{n='id';t='number'}, @{n='datos';t='SucursalEditar'})},
  @{n='cambiarEstadoSucursal';  r='Observable<Sucursal>';    p=@(@{n='id';t='number'}, @{n='activa';t='boolean'})},
  @{n='listar_ciudades';        r='list[CiudadOut]';   p=@(@{n='busqueda';t='str'}, @{n='db';t='Session'})},
  @{n='crear_ciudad';           r='CiudadOut';         p=@(@{n='datos';t='CiudadCrearIn'}, @{n='db';t='Session'})},
  @{n='obtener_ciudad';         r='CiudadOut';         p=@(@{n='ciudad_id';t='int'}, @{n='db';t='Session'})},
  @{n='editar_ciudad';          r='CiudadOut';         p=@(@{n='ciudad_id';t='int'}, @{n='datos';t='CiudadEditarIn'}, @{n='db';t='Session'})},
  @{n='eliminar_ciudad';        r='None';              p=@(@{n='ciudad_id';t='int'}, @{n='db';t='Session'})},
  @{n='listar_sucursales';      r='list[SucursalOut]'; p=@(@{n='filtros';t='FiltrosSucursales'}, @{n='db';t='Session'})},
  @{n='crear_sucursal';         r='SucursalOut';       p=@(@{n='datos';t='SucursalCrearIn'}, @{n='db';t='Session'})},
  @{n='obtener_sucursal';       r='SucursalOut';       p=@(@{n='sucursal_id';t='int'}, @{n='db';t='Session'})},
  @{n='editar_sucursal';        r='SucursalOut';       p=@(@{n='sucursal_id';t='int'}, @{n='datos';t='SucursalEditarIn'}, @{n='db';t='Session'})},
  @{n='cambiar_estado';         r='SucursalOut';       p=@(@{n='sucursal_id';t='int'}, @{n='activa';t='bool'}, @{n='db';t='Session'})}
)
Set-Operaciones $gor @(
  @{n='listar_ciudades';         r='list[CiudadOut]';   p=@(@{n='db';t='Session'}, @{n='busqueda';t='str'})},
  @{n='obtener_ciudad';          r='CiudadOut';         p=@(@{n='db';t='Session'}, @{n='ciudad_id';t='int'})},
  @{n='crear_ciudad';            r='CiudadOut';         p=@(@{n='db';t='Session'}, @{n='datos';t='CiudadCrearIn'})},
  @{n='editar_ciudad';           r='CiudadOut';         p=@(@{n='db';t='Session'}, @{n='ciudad_id';t='int'}, @{n='datos';t='CiudadEditarIn'})},
  @{n='eliminar_ciudad';         r='None';              p=@(@{n='db';t='Session'}, @{n='ciudad_id';t='int'})},
  @{n='listar_sucursales';       r='list[SucursalOut]'; p=@(@{n='db';t='Session'}, @{n='ciudad_id';t='int'}, @{n='activa';t='bool'})},
  @{n='obtener_sucursal';        r='SucursalOut';       p=@(@{n='db';t='Session'}, @{n='sucursal_id';t='int'})},
  @{n='crear_sucursal';          r='SucursalOut';       p=@(@{n='db';t='Session'}, @{n='datos';t='SucursalCrearIn'})},
  @{n='editar_sucursal';         r='SucursalOut';       p=@(@{n='db';t='Session'}, @{n='sucursal_id';t='int'}, @{n='datos';t='SucursalEditarIn'})},
  @{n='cambiar_estado_sucursal'; r='SucursalOut';       p=@(@{n='db';t='Session'}, @{n='sucursal_id';t='int'}, @{n='activa';t='bool'})},
  @{n='_fila_a_ciudad';          r='CiudadOut';         p=@(@{n='fila';t='Row'})},
  @{n='_fila_a_sucursal';        r='SucursalOut';       p=@(@{n='fila';t='Row'})},
  @{n='_viola';                  r='bool';              p=@(@{n='exc';t='IntegrityError'}, @{n='restriccion';t='str'})}
)

Set-Atributos $ciu @(
  @{n='id';t='SERIAL'}, @{n='nombre';t='VARCHAR(60)'}, @{n='departamento';t='VARCHAR(60)'},
  @{n='creado_en';t='TIMESTAMPTZ'}, @{n='actualizado_en';t='TIMESTAMPTZ'}
)
Set-Operaciones $ciu @(
  @{n='listar_ciudades';              r='list[Row]';        p=@(@{n='db';t='Session'}, @{n='busqueda';t='str'})},
  @{n='obtener_ciudad_con_recuento';  r='Row';              p=@(@{n='db';t='Session'}, @{n='ciudad_id';t='int'})},
  @{n='obtener_ciudad';               r='Ciudad';           p=@(@{n='db';t='Session'}, @{n='ciudad_id';t='int'})},
  @{n='obtener_ciudad_por_nombre';    r='Ciudad';           p=@(@{n='db';t='Session'}, @{n='nombre';t='str'})},
  @{n='agregar_ciudad';               r='Ciudad';           p=@(@{n='db';t='Session'}, @{n='nombre';t='str'}, @{n='departamento';t='str'})},
  @{n='contar_sucursales_de_ciudad';  r='tuple[int, int]';  p=@(@{n='db';t='Session'}, @{n='ciudad_id';t='int'})},
  @{n='eliminar_ciudad';              r='None';             p=@(@{n='db';t='Session'}, @{n='ciudad';t='Ciudad'})},
  @{n='existe_ciudad';                r='bool';             p=@(@{n='db';t='Session'}, @{n='ciudad_id';t='int'})}
)

Set-Atributos $suc @(
  @{n='id';t='SERIAL'}, @{n='ciudad_id';t='INTEGER'}, @{n='nombre';t='VARCHAR(80)'},
  @{n='direccion';t='VARCHAR(200)'}, @{n='telefono';t='VARCHAR(20)'},
  @{n='horario_apertura';t='TIME'}, @{n='horario_cierre';t='TIME'},
  @{n='capacidad_vestidores';t='SMALLINT'}, @{n='activa';t='BOOLEAN'},
  @{n='creado_en';t='TIMESTAMPTZ'}, @{n='actualizado_en';t='TIMESTAMPTZ'}
)
Set-Operaciones $suc @(
  @{n='listar_sucursales';           r='list[Row]'; p=@(@{n='db';t='Session'}, @{n='ciudad_id';t='int'}, @{n='activa';t='bool'})},
  @{n='obtener_sucursal_con_ciudad'; r='Row';       p=@(@{n='db';t='Session'}, @{n='sucursal_id';t='int'})},
  @{n='obtener_sucursal';            r='Sucursal';  p=@(@{n='db';t='Session'}, @{n='sucursal_id';t='int'})},
  @{n='existe_sucursal_con_nombre';  r='bool';      p=@(@{n='db';t='Session'}, @{n='ciudad_id';t='int'}, @{n='nombre';t='str'})},
  @{n='agregar_sucursal';            r='Sucursal';  p=@(@{n='db';t='Session'}, @{n='datos';t='SucursalCrearIn'})}
)

New-Asociacion $psu $gor 'DELEGA_EN'    '1'    '1'
New-Asociacion $psu $gau 'VERIFICA_CON' '1'    '1'
New-Asociacion $gor $ciu 'ADMINISTRA'   '1'    '0..*'
New-Asociacion $gor $suc 'ADMINISTRA'   '1'    '0..*'
New-Asociacion $suc $ciu 'UBICADA_EN'   '0..*' '1'

$nombre = '2.3 CU-05 Gestionar ciudades y sucursales'
if (BuscarDiagrama $p23 $nombre) {
    Write-Output "  $nombre ya existe, no se toca"
} else {
    $d = $p23.Diagrams.AddNew($nombre, 'Logical')
    [void]$d.Update(); $p23.Diagrams.Refresh()
    Poner $d $psu   40 -120 400 620
    Poner $d $gor  560 -120 420 480
    Poner $d $gau  560 -680 400 260
    Poner $d $ciu 1060  -40 400 380
    Poner $d $suc 1060 -480 400 560
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    Write-Output "  $nombre : $($d.DiagramObjects.Count) clases, $($d.DiagramLinks.Count) asociaciones"
}

# ---- CU-06 Gestionar empleados ----
#
# Sucursal reaparece aqui con dos lecturas mas (obtener_sucursal_activa y
# existe_sucursal): un empleado solo se puede asignar a una sucursal activa.
# Usuario suma las dos consultas de vinculacion.

$pem = Get-OCrearClase23 'PantallaEmpleados' 'frontera' 'Frontera del caso de uso en sus dos extremos: la pantalla de administracion (frontend-web/src/app/features/admin/empleados) con EmpleadosService, y los endpoints de /api/v1/organizacion/empleados de app/modules/organizacion/empleados/router.py.'
$gem = Get-OCrearClase23 'GestorEmpleados' 'controlador' 'app/modules/organizacion/empleados/service.py. Da de alta el empleado sobre un usuario existente o creando uno nuevo, y lo da de baja con fecha en vez de borrarlo.'
$emp = Get-OCrearClase23 'Empleado' 'entidad' 'Tabla empleado. La baja es logica: se llena fecha_baja y la fila se conserva por trazabilidad de ventas e inventario.'

Set-Operaciones $pem @(
  @{n='listar';               r='Observable<Empleado[]>';           p=@(@{n='filtros';t='FiltrosEmpleados'})},
  @{n='usuariosVinculables';  r='Observable<UsuarioVinculable[]>';  p=@()},
  @{n='crear';                r='Observable<Empleado>';             p=@(@{n='datos';t='EmpleadoCrear'})},
  @{n='editar';               r='Observable<Empleado>';             p=@(@{n='id';t='number'}, @{n='datos';t='EmpleadoEditar'})},
  @{n='darDeBaja';            r='Observable<Empleado>';             p=@(@{n='id';t='number'}, @{n='fecha_baja';t='string'})},
  @{n='listar_empleados';           r='list[EmpleadoOut]';          p=@(@{n='filtros';t='FiltrosEmpleados'}, @{n='db';t='Session'})},
  @{n='listar_usuarios_vinculables'; r='list[UsuarioVinculableOut]'; p=@(@{n='db';t='Session'})},
  @{n='crear_empleado';             r='EmpleadoOut';                p=@(@{n='datos';t='EmpleadoCrearIn'}, @{n='db';t='Session'})},
  @{n='obtener_empleado';           r='EmpleadoOut';                p=@(@{n='empleado_id';t='int'}, @{n='db';t='Session'})},
  @{n='editar_empleado';            r='EmpleadoOut';                p=@(@{n='empleado_id';t='int'}, @{n='datos';t='EmpleadoEditarIn'}, @{n='db';t='Session'})},
  @{n='dar_de_baja';                r='EmpleadoOut';                p=@(@{n='empleado_id';t='int'}, @{n='datos';t='BajaEmpleadoIn'}, @{n='db';t='Session'})}
)
Set-Operaciones $gem @(
  @{n='listar_empleados';            r='list[EmpleadoOut]';          p=@(@{n='db';t='Session'}, @{n='sucursal_id';t='int'}, @{n='activo';t='bool'})},
  @{n='obtener_empleado';            r='EmpleadoOut';                p=@(@{n='db';t='Session'}, @{n='empleado_id';t='int'})},
  @{n='listar_usuarios_vinculables'; r='list[UsuarioVinculableOut]'; p=@(@{n='db';t='Session'})},
  @{n='crear_empleado';              r='EmpleadoOut';                p=@(@{n='db';t='Session'}, @{n='datos';t='EmpleadoCrearIn'})},
  @{n='editar_empleado';             r='EmpleadoOut';                p=@(@{n='db';t='Session'}, @{n='empleado_id';t='int'}, @{n='datos';t='EmpleadoEditarIn'})},
  @{n='dar_de_baja';                 r='EmpleadoOut';                p=@(@{n='db';t='Session'}, @{n='empleado_id';t='int'}, @{n='datos';t='BajaEmpleadoIn'})},
  @{n='_validar_sucursal';           r='None';                       p=@(@{n='db';t='Session'}, @{n='sucursal_id';t='int'})},
  @{n='_fila_a_empleado';            r='EmpleadoOut';                p=@(@{n='fila';t='Row'})},
  @{n='_viola';                      r='bool';                       p=@(@{n='exc';t='IntegrityError'}, @{n='restriccion';t='str'})}
)

Set-Atributos $emp @(
  @{n='id';t='BIGSERIAL'}, @{n='usuario_id';t='BIGINT'}, @{n='sucursal_id';t='INTEGER'},
  @{n='documento';t='VARCHAR(20)'}, @{n='telefono';t='VARCHAR(20)'},
  @{n='cargo';t='VARCHAR(30)'}, @{n='fecha_ingreso';t='DATE'}, @{n='fecha_baja';t='DATE'},
  @{n='creado_en';t='TIMESTAMPTZ'}, @{n='actualizado_en';t='TIMESTAMPTZ'}
)
Set-Operaciones $emp @(
  @{n='listar_empleados';           r='list[Row]'; p=@(@{n='db';t='Session'}, @{n='sucursal_id';t='int'}, @{n='activo';t='bool'})},
  @{n='obtener_empleado_con_detalle'; r='Row';     p=@(@{n='db';t='Session'}, @{n='empleado_id';t='int'})},
  @{n='obtener_empleado';           r='Empleado';  p=@(@{n='db';t='Session'}, @{n='empleado_id';t='int'})},
  @{n='existe_documento';           r='bool';      p=@(@{n='db';t='Session'}, @{n='documento';t='str'}, @{n='excluir_id';t='int'})},
  @{n='agregar_empleado';           r='Empleado';  p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'}, @{n='datos';t='EmpleadoCrearIn'})}
)
Set-Operaciones $suc @(
  @{n='listar_sucursales';           r='list[Row]'; p=@(@{n='db';t='Session'}, @{n='ciudad_id';t='int'}, @{n='activa';t='bool'})},
  @{n='obtener_sucursal_con_ciudad'; r='Row';       p=@(@{n='db';t='Session'}, @{n='sucursal_id';t='int'})},
  @{n='obtener_sucursal';            r='Sucursal';  p=@(@{n='db';t='Session'}, @{n='sucursal_id';t='int'})},
  @{n='existe_sucursal_con_nombre';  r='bool';      p=@(@{n='db';t='Session'}, @{n='ciudad_id';t='int'}, @{n='nombre';t='str'})},
  @{n='agregar_sucursal';            r='Sucursal';  p=@(@{n='db';t='Session'}, @{n='datos';t='SucursalCrearIn'})},
  @{n='obtener_sucursal_activa';     r='Sucursal';  p=@(@{n='db';t='Session'}, @{n='sucursal_id';t='int'})},
  @{n='existe_sucursal';             r='bool';      p=@(@{n='db';t='Session'}, @{n='sucursal_id';t='int'})}
)
Set-Operaciones $usu @(
  @{n='obtener_usuario_por_correo';   r='Usuario'; p=@(@{n='db';t='Session'}, @{n='correo';t='str'})},
  @{n='agregar_usuario';              r='Usuario'; p=@(@{n='db';t='Session'}, @{n='datos';t='ClienteRegistroIn'}, @{n='rol_id';t='int'})},
  @{n='obtener_usuario_con_rol';      r='Usuario'; p=@(@{n='db';t='Session'}, @{n='correo';t='str'})},
  @{n='obtener_usuario_con_id';       r='Usuario'; p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'})},
  @{n='contar_y_listar_usuarios';     r='tuple[int, list[Row]]'; p=@(@{n='db';t='Session'}, @{n='busqueda';t='str'}, @{n='rol_id';t='int'})},
  @{n='obtener_detalle_usuario';      r='Row';  p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'})},
  @{n='tiene_operaciones_asociadas';  r='bool'; p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'})},
  @{n='eliminar_usuario';             r='None'; p=@(@{n='db';t='Session'}, @{n='usuario';t='Usuario'})},
  @{n='listar_usuarios_vinculables';  r='list[Row]'; p=@(@{n='db';t='Session'})},
  @{n='obtener_usuario_vinculable';   r='Usuario';   p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'})}
)

New-Asociacion $pem $gem 'DELEGA_EN'    '1'    '1'
New-Asociacion $pem $gau 'VERIFICA_CON' '1'    '1'
New-Asociacion $gem $emp 'ADMINISTRA'   '1'    '0..*'
New-Asociacion $gem $suc 'VALIDA'       '1'    '0..*'
New-Asociacion $gem $usu 'VINCULA'      '1'    '0..*'
New-Asociacion $gem $rol 'ASIGNA'       '1'    '0..*'
New-Asociacion $emp $usu 'ES_UN'        '1'    '1'
New-Asociacion $emp $suc 'ASIGNADO_A'   '0..*' '1'

$nombre = '2.3 CU-06 Gestionar empleados'
if (BuscarDiagrama $p23 $nombre) {
    Write-Output "  $nombre ya existe, no se toca"
} else {
    $d = $p23.Diagrams.AddNew($nombre, 'Logical')
    [void]$d.Update(); $p23.Diagrams.Refresh()
    Poner $d $pem   40 -120 400 440
    Poner $d $gem  500 -120 420 360
    Poner $d $gau  500 -560 400 260
    Poner $d $rol 1000  -40 320 200
    Poner $d $emp 1000 -300 400 460
    Poner $d $suc 1000 -820 400 640
    Poner $d $usu 1460 -300 400 520
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    Write-Output "  $nombre : $($d.DiagramObjects.Count) clases, $($d.DiagramLinks.Count) asociaciones"
}

# ---- CU-07 Gestionar proveedores ----

$ppr = Get-OCrearClase23 'PantallaProveedores' 'frontera' 'Frontera del caso de uso en sus dos extremos: la pantalla de administracion (frontend-web/src/app/features/admin/proveedores) con ProveedoresService, y los endpoints de /api/v1/organizacion/proveedores y /api/v1/organizacion/mi-ficha de app/modules/organizacion/proveedores_router.py.'
$gpr = Get-OCrearClase23 'GestorProveedores' 'controlador' 'app/modules/organizacion/proveedores_service.py. El proveedor se desactiva, nunca se borra; habilitar_acceso le crea un usuario con rol proveedor para que consulte su propia ficha.'
$pro = Get-OCrearClase23 'Proveedor' 'entidad' 'Tabla proveedor. usuario_id es opcional: solo se llena cuando el administrador le habilita acceso al sistema.'

Set-Operaciones $ppr @(
  @{n='listar';          r='Observable<Proveedor[]>'; p=@(@{n='filtros';t='FiltrosProveedores'})},
  @{n='crear';           r='Observable<Proveedor>';   p=@(@{n='datos';t='ProveedorCrear'})},
  @{n='editar';          r='Observable<Proveedor>';   p=@(@{n='id';t='number'}, @{n='datos';t='ProveedorEditar'})},
  @{n='cambiarEstado';   r='Observable<Proveedor>';   p=@(@{n='id';t='number'}, @{n='activo';t='boolean'})},
  @{n='habilitarAcceso'; r='Observable<Proveedor>';   p=@(@{n='id';t='number'}, @{n='datos';t='AccesoProveedor'})},
  @{n='miFicha';         r='Observable<Proveedor>';   p=@()},
  @{n='listar_proveedores';  r='list[ProveedorOut]'; p=@(@{n='filtros';t='FiltrosProveedores'}, @{n='db';t='Session'})},
  @{n='crear_proveedor';     r='ProveedorOut';       p=@(@{n='datos';t='ProveedorCrearIn'}, @{n='db';t='Session'})},
  @{n='obtener_proveedor';   r='ProveedorOut';       p=@(@{n='proveedor_id';t='int'}, @{n='db';t='Session'})},
  @{n='editar_proveedor';    r='ProveedorOut';       p=@(@{n='proveedor_id';t='int'}, @{n='datos';t='ProveedorEditarIn'}, @{n='db';t='Session'})},
  @{n='cambiar_estado';      r='ProveedorOut';       p=@(@{n='proveedor_id';t='int'}, @{n='activo';t='bool'}, @{n='db';t='Session'})},
  @{n='habilitar_acceso';    r='ProveedorOut';       p=@(@{n='proveedor_id';t='int'}, @{n='datos';t='AccesoProveedorIn'}, @{n='db';t='Session'})},
  @{n='obtener_mi_ficha';    r='ProveedorOut';       p=@(@{n='db';t='Session'}, @{n='usuario';t='UsuarioActual'})}
)
Set-Operaciones $gpr @(
  @{n='listar';            r='list[ProveedorOut]'; p=@(@{n='db';t='Session'}, @{n='busqueda';t='str'}, @{n='activo';t='bool'})},
  @{n='obtener';           r='ProveedorOut';       p=@(@{n='db';t='Session'}, @{n='proveedor_id';t='int'})},
  @{n='obtener_mi_ficha';  r='ProveedorOut';       p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'})},
  @{n='crear';             r='ProveedorOut';       p=@(@{n='db';t='Session'}, @{n='datos';t='ProveedorCrearIn'})},
  @{n='editar';            r='ProveedorOut';       p=@(@{n='db';t='Session'}, @{n='proveedor_id';t='int'}, @{n='datos';t='ProveedorEditarIn'})},
  @{n='cambiar_estado';    r='ProveedorOut';       p=@(@{n='db';t='Session'}, @{n='proveedor_id';t='int'}, @{n='activo';t='bool'})},
  @{n='habilitar_acceso';  r='ProveedorOut';       p=@(@{n='db';t='Session'}, @{n='proveedor_id';t='int'}, @{n='datos';t='AccesoProveedorIn'})},
  @{n='_fila_a_salida';    r='ProveedorOut';       p=@(@{n='fila';t='Row'})},
  @{n='_viola';            r='bool';               p=@(@{n='exc';t='IntegrityError'}, @{n='restriccion';t='str'})}
)

Set-Atributos $pro @(
  @{n='id';t='BIGSERIAL'}, @{n='usuario_id';t='BIGINT'}, @{n='razon_social';t='VARCHAR(120)'},
  @{n='identificacion_tributaria';t='VARCHAR(30)'}, @{n='contacto';t='VARCHAR(80)'},
  @{n='telefono';t='VARCHAR(20)'}, @{n='correo';t='VARCHAR(120)'},
  @{n='direccion';t='VARCHAR(200)'}, @{n='activo';t='BOOLEAN'},
  @{n='creado_en';t='TIMESTAMPTZ'}, @{n='actualizado_en';t='TIMESTAMPTZ'}
)
Set-Operaciones $pro @(
  @{n='listar';                     r='list[Row]';  p=@(@{n='db';t='Session'}, @{n='busqueda';t='str'}, @{n='activo';t='bool'})},
  @{n='obtener_detalle';            r='Row';        p=@(@{n='db';t='Session'}, @{n='proveedor_id';t='int'})},
  @{n='obtener_detalle_por_usuario'; r='Row';       p=@(@{n='db';t='Session'}, @{n='usuario_id';t='int'})},
  @{n='obtener';                    r='Proveedor';  p=@(@{n='db';t='Session'}, @{n='proveedor_id';t='int'})},
  @{n='existe_identificacion';      r='bool';       p=@(@{n='db';t='Session'}, @{n='identificacion';t='str'}, @{n='excluir_id';t='int'})},
  @{n='agregar';                    r='Proveedor';  p=@(@{n='db';t='Session'}, @{n='datos';t='ProveedorCrearIn'})}
)

New-Asociacion $ppr $gpr 'DELEGA_EN'    '1'    '1'
New-Asociacion $ppr $gau 'VERIFICA_CON' '1'    '1'
New-Asociacion $gpr $pro 'ADMINISTRA'   '1'    '0..*'
New-Asociacion $gpr $usu 'HABILITA'     '1'    '0..*'
New-Asociacion $pro $usu 'ACCEDE_CON'   '0..*' '0..1'

$nombre = '2.3 CU-07 Gestionar proveedores'
if (BuscarDiagrama $p23 $nombre) {
    Write-Output "  $nombre ya existe, no se toca"
} else {
    $d = $p23.Diagrams.AddNew($nombre, 'Logical')
    [void]$d.Update(); $p23.Diagrams.Refresh()
    Poner $d $ppr   40 -120 400 480
    Poner $d $gpr  500 -120 420 360
    Poner $d $gau  500 -560 400 260
    Poner $d $pro 1000  -40 400 620
    Poner $d $usu 1000 -720 400 520
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    Write-Output "  $nombre : $($d.DiagramObjects.Count) clases, $($d.DiagramLinks.Count) asociaciones"
}

# ---- CU-08 Gestionar categorias, tallas y colores ----
#
# La frontera es una sola pantalla con tres pestanas, y por eso concentra las
# dieciseis operaciones de MaestrosService. Los endpoints de maestros/router.py
# llevan el mismo nombre en snake_case (listar_categorias, crear_talla, ...),
# asi que no se repiten aqui: la clase quedaria ilegible.

$pma = Get-OCrearClase23 'PantallaMaestrosCatalogo' 'frontera' 'Frontera del caso de uso en sus dos extremos: la pantalla de tres pestanas (frontend-web/src/app/features/admin/maestros, con categoria-formulario, talla-formulario y color-formulario) usando MaestrosService, y los endpoints de /api/v1/catalogo/categorias, /tallas y /colores de app/modules/catalogo/maestros/router.py, que llevan los mismos nombres en snake_case.'
$gta = Get-OCrearClase23 'GestorTaxonomia' 'controlador' 'app/modules/catalogo/maestros/service.py. Arma el arbol de categorias, impide ciclos al reasignar el padre y solo deja borrar lo que no tiene hijos ni uso.'
$cat = Get-OCrearClase23 'Categoria' 'entidad' 'Tabla categoria. Es jerarquica: categoria_padre_id apunta a otra fila de la misma tabla.'
$tal = Get-OCrearClase23 'Talla' 'entidad' 'Tabla talla. La combinacion tipo_prenda + codigo es unica; orden fija la secuencia de presentacion.'
$col = Get-OCrearClase23 'Color' 'entidad' 'Tabla color. hexadecimal es CHAR(7) con el formato #RRGGBB.'

Set-Operaciones $pma @(
  @{n='categorias';              r='Observable<Categoria[]>'; p=@()},
  @{n='crearCategoria';          r='Observable<Categoria>';   p=@(@{n='datos';t='CategoriaCrear'})},
  @{n='editarCategoria';         r='Observable<Categoria>';   p=@(@{n='id';t='number'}, @{n='datos';t='CategoriaEditar'})},
  @{n='cambiarEstadoCategoria';  r='Observable<Categoria>';   p=@(@{n='id';t='number'}, @{n='activo';t='boolean'})},
  @{n='eliminarCategoria';       r='Observable<void>';        p=@(@{n='id';t='number'})},
  @{n='tallas';                  r='Observable<Talla[]>';     p=@(@{n='tipo_prenda';t='string'})},
  @{n='tiposDePrenda';           r='Observable<string[]>';    p=@()},
  @{n='crearTalla';              r='Observable<Talla>';       p=@(@{n='datos';t='TallaCrear'})},
  @{n='editarTalla';             r='Observable<Talla>';       p=@(@{n='id';t='number'}, @{n='datos';t='TallaEditar'})},
  @{n='cambiarEstadoTalla';      r='Observable<Talla>';       p=@(@{n='id';t='number'}, @{n='activo';t='boolean'})},
  @{n='eliminarTalla';           r='Observable<void>';        p=@(@{n='id';t='number'})},
  @{n='colores';                 r='Observable<Color[]>';     p=@()},
  @{n='crearColor';              r='Observable<Color>';       p=@(@{n='datos';t='ColorCrear'})},
  @{n='editarColor';             r='Observable<Color>';       p=@(@{n='id';t='number'}, @{n='datos';t='ColorEditar'})},
  @{n='cambiarEstadoColor';      r='Observable<Color>';       p=@(@{n='id';t='number'}, @{n='activo';t='boolean'})},
  @{n='eliminarColor';           r='Observable<void>';        p=@(@{n='id';t='number'})}
)
Set-Operaciones $gta @(
  @{n='listar_categorias';        r='list[CategoriaOut]'; p=@(@{n='db';t='Session'})},
  @{n='obtener_categoria';        r='CategoriaOut';       p=@(@{n='db';t='Session'}, @{n='categoria_id';t='int'})},
  @{n='crear_categoria';          r='CategoriaOut';       p=@(@{n='db';t='Session'}, @{n='datos';t='CategoriaCrearIn'})},
  @{n='editar_categoria';         r='CategoriaOut';       p=@(@{n='db';t='Session'}, @{n='categoria_id';t='int'}, @{n='datos';t='CategoriaEditarIn'})},
  @{n='cambiar_estado_categoria'; r='CategoriaOut';       p=@(@{n='db';t='Session'}, @{n='categoria_id';t='int'}, @{n='activa';t='bool'})},
  @{n='eliminar_categoria';       r='None';               p=@(@{n='db';t='Session'}, @{n='categoria_id';t='int'})},
  @{n='listar_tallas';            r='list[TallaOut]';     p=@(@{n='db';t='Session'}, @{n='tipo_prenda';t='str'})},
  @{n='listar_tipos_de_prenda';   r='list[str]';          p=@(@{n='db';t='Session'})},
  @{n='crear_talla';              r='TallaOut';           p=@(@{n='db';t='Session'}, @{n='datos';t='TallaCrearIn'})},
  @{n='editar_talla';             r='TallaOut';           p=@(@{n='db';t='Session'}, @{n='talla_id';t='int'}, @{n='datos';t='TallaEditarIn'})},
  @{n='cambiar_estado_talla';     r='TallaOut';           p=@(@{n='db';t='Session'}, @{n='talla_id';t='int'}, @{n='activa';t='bool'})},
  @{n='eliminar_talla';           r='None';               p=@(@{n='db';t='Session'}, @{n='talla_id';t='int'})},
  @{n='listar_colores';           r='list[ColorOut]';     p=@(@{n='db';t='Session'}, @{n='activo';t='bool'})},
  @{n='crear_color';              r='ColorOut';           p=@(@{n='db';t='Session'}, @{n='datos';t='ColorCrearIn'})},
  @{n='editar_color';             r='ColorOut';           p=@(@{n='db';t='Session'}, @{n='color_id';t='int'}, @{n='datos';t='ColorEditarIn'})},
  @{n='cambiar_estado_color';     r='ColorOut';           p=@(@{n='db';t='Session'}, @{n='color_id';t='int'}, @{n='activo';t='bool'})},
  @{n='eliminar_color';           r='None';               p=@(@{n='db';t='Session'}, @{n='color_id';t='int'})},
  @{n='_armar_arbol';             r='list[CategoriaOut]'; p=@(@{n='categorias';t='list[Categoria]'})},
  @{n='_validar_padre';           r='None';               p=@(@{n='db';t='Session'}, @{n='categoria_padre_id';t='int'})},
  @{n='_viola';                   r='bool';               p=@(@{n='exc';t='IntegrityError'}, @{n='restriccion';t='str'})}
)

Set-Atributos $cat @(
  @{n='id';t='SERIAL'}, @{n='categoria_padre_id';t='INTEGER'}, @{n='nombre';t='VARCHAR(60)'},
  @{n='orden';t='SMALLINT'}, @{n='activa';t='BOOLEAN'},
  @{n='creado_en';t='TIMESTAMPTZ'}, @{n='actualizado_en';t='TIMESTAMPTZ'}
)
Set-Operaciones $cat @(
  @{n='listar_categorias';        r='list[Categoria]'; p=@(@{n='db';t='Session'})},
  @{n='obtener_categoria';        r='Categoria';       p=@(@{n='db';t='Session'}, @{n='categoria_id';t='int'})},
  @{n='existe_hermana_con_nombre'; r='bool';           p=@(@{n='db';t='Session'}, @{n='categoria_padre_id';t='int'}, @{n='nombre';t='str'})},
  @{n='ids_de_descendientes';     r='set[int]';        p=@(@{n='db';t='Session'}, @{n='categoria_id';t='int'})},
  @{n='contar_subcategorias';     r='int';             p=@(@{n='db';t='Session'}, @{n='categoria_id';t='int'})},
  @{n='agregar_categoria';        r='Categoria';       p=@(@{n='db';t='Session'}, @{n='datos';t='CategoriaCrearIn'})},
  @{n='eliminar_categoria';       r='None';            p=@(@{n='db';t='Session'}, @{n='categoria';t='Categoria'})}
)

Set-Atributos $tal @(
  @{n='id';t='SERIAL'}, @{n='tipo_prenda';t='VARCHAR(30)'}, @{n='codigo';t='VARCHAR(10)'},
  @{n='orden';t='SMALLINT'}, @{n='activa';t='BOOLEAN'},
  @{n='creado_en';t='TIMESTAMPTZ'}, @{n='actualizado_en';t='TIMESTAMPTZ'}
)
Set-Operaciones $tal @(
  @{n='listar_tallas';          r='list[Talla]'; p=@(@{n='db';t='Session'}, @{n='tipo_prenda';t='str'})},
  @{n='listar_tipos_de_prenda'; r='list[str]';   p=@(@{n='db';t='Session'})},
  @{n='obtener_talla';          r='Talla';       p=@(@{n='db';t='Session'}, @{n='talla_id';t='int'})},
  @{n='existe_talla';           r='bool';        p=@(@{n='db';t='Session'}, @{n='tipo_prenda';t='str'}, @{n='codigo';t='str'})},
  @{n='agregar_talla';          r='Talla';       p=@(@{n='db';t='Session'}, @{n='datos';t='TallaCrearIn'})},
  @{n='eliminar_talla';         r='None';        p=@(@{n='db';t='Session'}, @{n='talla';t='Talla'})}
)

Set-Atributos $col @(
  @{n='id';t='SERIAL'}, @{n='nombre';t='VARCHAR(40)'}, @{n='hexadecimal';t='CHAR(7)'},
  @{n='activo';t='BOOLEAN'}, @{n='creado_en';t='TIMESTAMPTZ'}, @{n='actualizado_en';t='TIMESTAMPTZ'}
)
Set-Operaciones $col @(
  @{n='listar_colores';           r='list[Color]'; p=@(@{n='db';t='Session'}, @{n='activo';t='bool'})},
  @{n='obtener_color';            r='Color';       p=@(@{n='db';t='Session'}, @{n='color_id';t='int'})},
  @{n='existe_color_con_nombre';  r='bool';        p=@(@{n='db';t='Session'}, @{n='nombre';t='str'}, @{n='excluir_id';t='int'})},
  @{n='agregar_color';            r='Color';       p=@(@{n='db';t='Session'}, @{n='nombre';t='str'}, @{n='hexadecimal';t='str'}, @{n='activo';t='bool'})},
  @{n='eliminar_color';           r='None';        p=@(@{n='db';t='Session'}, @{n='color';t='Color'})}
)

New-Asociacion $pma $gta 'DELEGA_EN'       '1'    '1'
New-Asociacion $pma $gau 'VERIFICA_CON'    '1'    '1'
New-Asociacion $gta $cat 'ADMINISTRA'      '1'    '0..*'
New-Asociacion $gta $tal 'ADMINISTRA'      '1'    '0..*'
New-Asociacion $gta $col 'ADMINISTRA'      '1'    '0..*'
New-Asociacion $cat $cat 'SUBCATEGORIA_DE' '0..*' '0..1'

$nombre = '2.3 CU-08 Gestionar categorías, tallas y colores'
if (BuscarDiagrama $p23 $nombre) {
    Write-Output "  $nombre ya existe, no se toca"
} else {
    $d = $p23.Diagrams.AddNew($nombre, 'Logical')
    [void]$d.Update(); $p23.Diagrams.Refresh()
    Poner $d $pma   40 -120 400 560
    Poner $d $gta  500 -120 440 700
    Poner $d $gau  500 -900 400 260
    Poner $d $cat 1020  -40 420 460
    Poner $d $tal 1020 -560 420 420
    Poner $d $col 1020 -1040 420 380
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    Write-Output "  $nombre : $($d.DiagramObjects.Count) clases, $($d.DiagramLinks.Count) asociaciones"
}

# ---- CU-09 Gestionar temporadas y colecciones ----

$pte = Get-OCrearClase23 'PantallaTemporadas' 'frontera' 'Frontera del caso de uso en sus dos extremos: la pantalla de administracion (frontend-web/src/app/features/admin/temporadas) con TemporadasService, y los endpoints de /api/v1/catalogo/temporadas y /colecciones de app/modules/catalogo/temporadas_router.py.'
$gte = Get-OCrearClase23 'GestorTemporadas' 'controlador' 'app/modules/catalogo/temporadas_service.py. Comprueba que dos temporadas activas no se solapen en fechas y no deja borrar una temporada que ya tiene colecciones.'
$tem = Get-OCrearClase23 'Temporada' 'entidad' 'Tabla temporada. fecha_inicio y fecha_fin delimitan su vigencia; el gestor las usa para detectar solapamientos.'
$cle = Get-OCrearClase23 'Coleccion' 'entidad' 'Tabla coleccion. El nombre es unico dentro de su temporada, no en toda la tabla.'

Set-Operaciones $pte @(
  @{n='listarTemporadas';        r='Observable<Temporada[]>';  p=@(@{n='filtros';t='FiltrosTemporadas'})},
  @{n='crearTemporada';          r='Observable<Temporada>';    p=@(@{n='datos';t='TemporadaCrear'})},
  @{n='editarTemporada';         r='Observable<Temporada>';    p=@(@{n='id';t='number'}, @{n='datos';t='TemporadaEditar'})},
  @{n='eliminarTemporada';       r='Observable<void>';         p=@(@{n='id';t='number'})},
  @{n='listarColecciones';       r='Observable<Coleccion[]>';  p=@(@{n='filtros';t='FiltrosColecciones'})},
  @{n='crearColeccion';          r='Observable<Coleccion>';    p=@(@{n='datos';t='ColeccionCrear'})},
  @{n='editarColeccion';         r='Observable<Coleccion>';    p=@(@{n='id';t='number'}, @{n='datos';t='ColeccionEditar'})},
  @{n='cambiarEstadoColeccion';  r='Observable<Coleccion>';    p=@(@{n='id';t='number'}, @{n='activa';t='boolean'})},
  @{n='listar_temporadas';        r='list[TemporadaOut]'; p=@(@{n='filtros';t='FiltrosTemporadas'}, @{n='db';t='Session'})},
  @{n='crear_temporada';          r='TemporadaOut';       p=@(@{n='datos';t='TemporadaCrearIn'}, @{n='db';t='Session'})},
  @{n='obtener_temporada';        r='TemporadaOut';       p=@(@{n='temporada_id';t='int'}, @{n='db';t='Session'})},
  @{n='editar_temporada';         r='TemporadaOut';       p=@(@{n='temporada_id';t='int'}, @{n='datos';t='TemporadaEditarIn'}, @{n='db';t='Session'})},
  @{n='cambiar_estado_temporada'; r='TemporadaOut';       p=@(@{n='temporada_id';t='int'}, @{n='activa';t='bool'}, @{n='db';t='Session'})},
  @{n='eliminar_temporada';       r='None';               p=@(@{n='temporada_id';t='int'}, @{n='db';t='Session'})},
  @{n='listar_colecciones';       r='list[ColeccionOut]'; p=@(@{n='filtros';t='FiltrosColecciones'}, @{n='db';t='Session'})},
  @{n='crear_coleccion';          r='ColeccionOut';       p=@(@{n='datos';t='ColeccionCrearIn'}, @{n='db';t='Session'})},
  @{n='obtener_coleccion';        r='ColeccionOut';       p=@(@{n='coleccion_id';t='int'}, @{n='db';t='Session'})},
  @{n='editar_coleccion';         r='ColeccionOut';       p=@(@{n='coleccion_id';t='int'}, @{n='datos';t='ColeccionEditarIn'}, @{n='db';t='Session'})},
  @{n='cambiar_estado_coleccion'; r='ColeccionOut';       p=@(@{n='coleccion_id';t='int'}, @{n='activa';t='bool'}, @{n='db';t='Session'})}
)
Set-Operaciones $gte @(
  @{n='listar_temporadas';        r='list[TemporadaOut]'; p=@(@{n='db';t='Session'}, @{n='activa';t='bool'})},
  @{n='obtener_temporada';        r='TemporadaOut';       p=@(@{n='db';t='Session'}, @{n='temporada_id';t='int'})},
  @{n='crear_temporada';          r='TemporadaOut';       p=@(@{n='db';t='Session'}, @{n='datos';t='TemporadaCrearIn'})},
  @{n='editar_temporada';         r='TemporadaOut';       p=@(@{n='db';t='Session'}, @{n='temporada_id';t='int'}, @{n='datos';t='TemporadaEditarIn'})},
  @{n='cambiar_estado_temporada'; r='TemporadaOut';       p=@(@{n='db';t='Session'}, @{n='temporada_id';t='int'}, @{n='activa';t='bool'})},
  @{n='eliminar_temporada';       r='None';               p=@(@{n='db';t='Session'}, @{n='temporada_id';t='int'})},
  @{n='listar_colecciones';       r='list[ColeccionOut]'; p=@(@{n='db';t='Session'}, @{n='temporada_id';t='int'}, @{n='activa';t='bool'})},
  @{n='obtener_coleccion';        r='ColeccionOut';       p=@(@{n='db';t='Session'}, @{n='coleccion_id';t='int'})},
  @{n='crear_coleccion';          r='ColeccionOut';       p=@(@{n='db';t='Session'}, @{n='datos';t='ColeccionCrearIn'})},
  @{n='editar_coleccion';         r='ColeccionOut';       p=@(@{n='db';t='Session'}, @{n='coleccion_id';t='int'}, @{n='datos';t='ColeccionEditarIn'})},
  @{n='cambiar_estado_coleccion'; r='ColeccionOut';       p=@(@{n='db';t='Session'}, @{n='coleccion_id';t='int'}, @{n='activa';t='bool'})},
  @{n='_comprobar_solapamiento';  r='None';               p=@(@{n='db';t='Session'}, @{n='fecha_inicio';t='date'}, @{n='fecha_fin';t='date'}, @{n='excluir_id';t='int'})},
  @{n='_fila_a_temporada';        r='TemporadaOut';       p=@(@{n='fila';t='Row'}, @{n='hoy';t='date'})},
  @{n='_fila_a_coleccion';        r='ColeccionOut';       p=@(@{n='fila';t='Row'})},
  @{n='_viola';                   r='bool';               p=@(@{n='exc';t='IntegrityError'}, @{n='restriccion';t='str'})}
)

Set-Atributos $tem @(
  @{n='id';t='SERIAL'}, @{n='nombre';t='VARCHAR(60)'}, @{n='descripcion';t='VARCHAR(200)'},
  @{n='fecha_inicio';t='DATE'}, @{n='fecha_fin';t='DATE'}, @{n='activa';t='BOOLEAN'},
  @{n='creado_en';t='TIMESTAMPTZ'}, @{n='actualizado_en';t='TIMESTAMPTZ'}
)
Set-Operaciones $tem @(
  @{n='listar_temporadas';               r='list[Row]';       p=@(@{n='db';t='Session'}, @{n='activa';t='bool'})},
  @{n='obtener_temporada_detalle';       r='Row';             p=@(@{n='db';t='Session'}, @{n='temporada_id';t='int'})},
  @{n='obtener_temporada';               r='Temporada';       p=@(@{n='db';t='Session'}, @{n='temporada_id';t='int'})},
  @{n='obtener_temporada_por_nombre';    r='Temporada';       p=@(@{n='db';t='Session'}, @{n='nombre';t='str'})},
  @{n='temporadas_que_se_cruzan';        r='list[Temporada]'; p=@(@{n='db';t='Session'}, @{n='fecha_inicio';t='date'}, @{n='fecha_fin';t='date'}, @{n='excluir_id';t='int'})},
  @{n='agregar_temporada';               r='Temporada';       p=@(@{n='db';t='Session'}, @{n='datos';t='TemporadaCrearIn'})},
  @{n='contar_colecciones_de_temporada'; r='tuple[int, int]'; p=@(@{n='db';t='Session'}, @{n='temporada_id';t='int'})},
  @{n='eliminar_temporada';              r='None';            p=@(@{n='db';t='Session'}, @{n='temporada';t='Temporada'})}
)

Set-Atributos $cle @(
  @{n='id';t='SERIAL'}, @{n='temporada_id';t='INTEGER'}, @{n='nombre';t='VARCHAR(60)'},
  @{n='descripcion';t='VARCHAR(200)'}, @{n='activa';t='BOOLEAN'},
  @{n='creado_en';t='TIMESTAMPTZ'}, @{n='actualizado_en';t='TIMESTAMPTZ'}
)
Set-Operaciones $cle @(
  @{n='listar_colecciones';          r='list[Row]'; p=@(@{n='db';t='Session'}, @{n='temporada_id';t='int'}, @{n='activa';t='bool'})},
  @{n='obtener_coleccion_detalle';   r='Row';       p=@(@{n='db';t='Session'}, @{n='coleccion_id';t='int'})},
  @{n='obtener_coleccion';           r='Coleccion'; p=@(@{n='db';t='Session'}, @{n='coleccion_id';t='int'})},
  @{n='existe_coleccion_con_nombre'; r='bool';      p=@(@{n='db';t='Session'}, @{n='temporada_id';t='int'}, @{n='nombre';t='str'})},
  @{n='agregar_coleccion';           r='Coleccion'; p=@(@{n='db';t='Session'}, @{n='datos';t='ColeccionCrearIn'})}
)

New-Asociacion $pte $gte 'DELEGA_EN'    '1'    '1'
New-Asociacion $pte $gau 'VERIFICA_CON' '1'    '1'
New-Asociacion $gte $tem 'ADMINISTRA'   '1'    '0..*'
New-Asociacion $gte $cle 'ADMINISTRA'   '1'    '0..*'
New-Asociacion $cle $tem 'PERTENECE_A'  '0..*' '1'

$nombre = '2.3 CU-09 Gestionar temporadas y colecciones'
if (BuscarDiagrama $p23 $nombre) {
    Write-Output "  $nombre ya existe, no se toca"
} else {
    $d = $p23.Diagrams.AddNew($nombre, 'Logical')
    [void]$d.Update(); $p23.Diagrams.Refresh()
    Poner $d $pte   40 -120 420 640
    Poner $d $gte  520 -120 440 560
    Poner $d $gau  520 -760 400 260
    Poner $d $tem 1040  -40 440 500
    Poner $d $cle 1040 -600 440 420
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    Write-Output "  $nombre : $($d.DiagramObjects.Count) clases, $($d.DiagramLinks.Count) asociaciones"
}
$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
