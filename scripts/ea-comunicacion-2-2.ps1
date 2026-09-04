# =========================================================================
# CAP. 2 - 2.2 Analizar Casos de Uso: diagramas de comunicacion.
#
# Un diagrama por caso de uso, con sus clases de analisis y los mensajes
# numerados entre ellas. Los participantes y la secuencia de mensajes salen de
# docs/entregas/ciclo-1/cap-2-3-analisis-y-diseno.md seccion 2.2.
#
# ADITIVO: abre el modelo y solo agrega lo que falta. No recrea nada ni toca
# los diagramas ya acomodados a mano.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\FashionStore.eapx'
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

# ---------------- utilidades ----------------

function Get-OCrearPaqueteModelo($padre, $nombre) {
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    $p = $padre.Packages.AddNew($nombre, 'Package'); [void]$p.Update()
    $padre.Packages.Refresh(); return $p
}

$indice = @{}
function Registrar-Elementos($pkg) {
    foreach ($e in $pkg.Elements) { $indice["$($e.Type)|$($e.Stereotype)|$($e.Name)"] = $e }
    foreach ($sp in $pkg.Packages) { Registrar-Elementos $sp }
}

function Get-OCrearClase($pkg, $nombre, $estereotipo, $notas) {
    $clave = "Class|$estereotipo|$nombre"
    if ($indice.ContainsKey($clave)) { return $indice[$clave] }
    $e = $pkg.Elements.AddNew($nombre, 'Class')
    $e.Stereotype = $estereotipo
    if ($notas) { $e.Notes = $notas }
    [void]$e.Update(); $pkg.Elements.Refresh()
    $indice[$clave] = $e
    return $e
}

function Buscar-Elemento($tipo, $estereotipo, $nombre) {
    $clave = "$tipo|$estereotipo|$nombre"
    if ($indice.ContainsKey($clave)) { return $indice[$clave] }
    throw "No se encontro el elemento $clave"
}

function Get-Diagrama($pkg, $nombre) {
    foreach ($d in $pkg.Diagrams) { if ($d.Name -eq $nombre) { return $d } }
    return $null
}

function Poner($dia, $el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l+$ancho);t=$t;b=$($t-$alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
    return $do
}

# Como se arma un mensaje de comunicacion en EA, que costo averiguarlo:
#
#   - El ENLACE entre dos objetos es un conector 'Association'. Es lo que dibuja
#     la linea. Va uno solo por par de objetos, aunque intercambien varios
#     mensajes.
#   - Cada MENSAJE es un conector 'Collaboration' cuyo nombre es el texto
#     numerado ("4: existeCorreo(correo)"). Aporta la etiqueta, no la linea.
#
# Un conector 'Sequence' --- que es el de los diagramas de secuencia --- se crea
# sin error pero no dibuja nada en un diagrama de comunicacion.

function New-Enlace($src, $dst) {
    foreach ($c in $src.Connectors) {
        if ($c.SupplierID -eq $dst.ElementID -and $c.Type -eq 'Association') { return }
    }
    $c = $src.Connectors.AddNew('', 'Association')
    $c.SupplierID = $dst.ElementID
    [void]$c.Update(); $src.Connectors.Refresh()
}

function New-Mensaje($src, $dst, $nombre) {
    $c = $src.Connectors.AddNew($nombre, 'Collaboration')
    $c.SupplierID = $dst.ElementID
    [void]$c.Update(); $src.Connectors.Refresh()
    return $c
}

# ---------------- estructura ----------------

$root     = $ea.Models.GetAt(0)
$pFashion = Get-OCrearPaqueteModelo $root 'FashionStore'
Registrar-Elementos $pFashion

$pCap2 = Get-OCrearPaqueteModelo $pFashion 'CAP. 2 - Flujo de Trabajo: Analisis'
$p22   = Get-OCrearPaqueteModelo $pCap2    '2.2 Analizar Casos de Uso'
$pClas = Get-OCrearPaqueteModelo $p22      'Clases de Analisis'

# ---------------- clases de analisis de CU-01 ----------------

$fmReg = Get-OCrearClase $pClas 'FormularioRegistro' 'boundary' `
    'Pantalla de registro en la web y en la app movil. Recoge los datos, los valida en el formulario y muestra el resultado.'
$gsReg = Get-OCrearClase $pClas 'GestorRegistro' 'control' `
    'Coordina CU-01: valida, verifica que el correo este libre, calcula el hash y crea usuario y cliente en una sola transaccion.'
$enUsu = Get-OCrearClase $pClas 'Usuario' 'entity' `
    'Identidad y credencial de quien accede al sistema.'
$enRol = Get-OCrearClase $pClas 'Rol' 'entity' `
    'Conjunto de permisos de un tipo de usuario.'
$enCli = Get-OCrearClase $pClas 'Cliente' 'entity' `
    'Datos comerciales del usuario con rol Cliente.'

$acCli = Buscar-Elemento 'Actor' '' 'Cliente'

# ---------------- el diagrama ----------------

$nombre = '2.2 CU-01 Registrar cliente'
if (Get-Diagrama $p22 $nombre) {
    Write-Output "$nombre ya existe, no se toca"
} else {
    $d = $p22.Diagrams.AddNew($nombre, 'Communication')
    [void]$d.Update(); $p22.Diagrams.Refresh()
    Write-Output "diagrama creado, tipo real: $($d.Type)"

    # Cuadrados: con los estereotipos boundary/control/entity, EA dibuja el
    # icono redondo inscrito en la caja. Si la caja es ancha y baja, el circulo
    # se desborda y se come a los vecinos.
    Poner $d $acCli  60 -190 100  90 | Out-Null
    Poner $d $fmReg 320 -180 100 100 | Out-Null
    Poner $d $gsReg 640 -180 100 100 | Out-Null
    Poner $d $enRol 980  -30 100 100 | Out-Null
    Poner $d $enUsu 980 -180 100 100 | Out-Null
    Poner $d $enCli 980 -330 100 100 | Out-Null

    # Un enlace por par de objetos que se comunican.
    New-Enlace $acCli $fmReg
    New-Enlace $fmReg $gsReg
    New-Enlace $gsReg $enUsu
    New-Enlace $gsReg $enRol
    New-Enlace $gsReg $enCli

    # Mensajes numerados. El numero va en el nombre, que es como se lee un
    # diagrama de comunicacion: la secuencia la da la numeracion, no la posicion.
    $mensajes = @(
        @{ de=$acCli; a=$fmReg; m='1: enviarDatos(nombres, apellidos, correo, contrasena)' },
        @{ de=$fmReg; a=$gsReg; m='2: registrarCliente(datos)' },
        @{ de=$gsReg; a=$gsReg; m='3: validarDatos(datos)' },
        @{ de=$gsReg; a=$enUsu; m='4: existeCorreo(correo)' },
        @{ de=$gsReg; a=$gsReg; m='5: hashearContrasena(contrasena)' },
        @{ de=$gsReg; a=$enRol; m='6: obtenerRol("CLIENTE")' },
        @{ de=$gsReg; a=$enUsu; m='7: crear(usuario)' },
        @{ de=$gsReg; a=$enCli; m='8: crear(cliente)' },
        @{ de=$fmReg; a=$acCli; m='9: confirmarRegistro()' }
    )
    foreach ($x in $mensajes) { New-Mensaje $x.de $x.a $x.m | Out-Null }

    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    Write-Output "objetos: $($d.DiagramObjects.Count) | mensajes dibujados: $($d.DiagramLinks.Count)"

    $prj = $ea.GetProjectInterface()
    $png = 'C:\Users\luism\AppData\Local\Temp\claude\D--UNI-Si2-PRIMER-PARCIAL\3e277b4a-7ab7-43f9-aacc-df4565e09a6f\scratchpad\v22-cu01.png'
    Write-Output "export -> $($prj.PutDiagramImageToFile($d.DiagramGUID, $png, 1))"
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
