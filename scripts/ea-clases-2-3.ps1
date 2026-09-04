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
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\FashionStore.eapx'
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
$pFashion = Get-OCrearPaqueteModelo $root 'FashionStore'
$pCap2    = Get-OCrearPaqueteModelo $pFashion 'CAP. 2 - Flujo de Trabajo: Analisis'
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

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
