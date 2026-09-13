# =========================================================================
# CAP. 2 - 2.4 Analisis de Paquetes. CICLO 2.
#
# ESTA RECETA CAMBIO EL 13/09/2026
# --------------------------------
# La version que produjo el diagrama del Ciclo 1 --- ea-paquetes-2-4.ps1 ---
# dibujaba las clases CONTENIDAS dentro de cada paquete y unia los paquetes
# con Usage. Se reemplazo por la forma del diagrama 3.10a de otro proyecto
# (PROYECTO_MEDICOS/docs/diagramas/PlataformaMedica.eapx), que esta mejor
# resuelto. Tres cambios:
#
#   1. LOS PAQUETES VAN SOLOS, sin las clases adentro. Con tres paquetes y
#      catorce clases el dibujo del Ciclo 1 todavia se leia; con los seis
#      paquetes y la veintena de clases del Ciclo 2 se vuelve ilegible. El
#      diagrama tiene que contestar «quien depende de quien».
#
#   2. Dependency EN VEZ DE Usage. Es la flecha que UML asocia a la
#      dependencia entre paquetes; Usage es un refinamiento que promete mas de
#      lo que el diagrama afirma.
#
#   3. LA DISPOSICION ES UNA PIRAMIDE, no dos filas. La base --- el paquete
#      del que todos dependen --- abajo y centrada, y cada capa encima depende
#      hacia abajo. Con dos filas, seis paquetes dejan una fila de cinco y no
#      se entiende que depende de que.
#
# La cohesion no se pierde: baja a las notas del pie, y la de cohesion NOMBRA
# las clases de cada paquete. Es la misma informacion, en un espacio que no
# compite con las flechas.
#
# El diagrama del Ciclo 1 NO se rehace: queda como esta.
# NO EXPORTA IMAGENES. Las exporta Mateo a mano desde EA.
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
function BuscarDiagrama($p, $n) {
    foreach ($d in $p.Diagrams) { if ($d.Name -eq $n) { return $d } }
    return $null
}
function Poner($dia, $el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l+$ancho);t=$t;b=$($t-$alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
}

$root  = $ea.Models.GetAt(0)
$pRaiz = Get-OCrearPaqueteModelo $root 'Violet Boutique'
$pCap2 = Get-OCrearPaqueteModelo $pRaiz 'CAP. 2 - Flujo de Trabajo: Analisis'
$p24p  = Get-OCrearPaqueteModelo $pCap2 '2.4 Analisis de Paquetes'

# SUBPAQUETE PROPIO DEL CICLO, Y NO EL DE 2.4 A SECAS.
#
# Los paquetes del Ciclo 1 --- 'P1 · Seguridad y Usuarios' y 'P2 ·
# Organizacion' --- ya viven en 2.4, con los conectores Usage de SU diagrama.
# Un buscar-o-crear por nombre sobre 2.4 los encuentra y los reutiliza, y
# entonces las dependencias nuevas quedan colgadas de ESOS elementos: al abrir
# el diagrama del Ciclo 1 en EA, la regla 3 hace que aparezca una flecha
# Dependency al lado de cada Usage, sobre un dibujo que ya estaba acomodado a
# mano. No da error y no se ve hasta que alguien lo abre.
#
# Con un subpaquete por ciclo, cada uno tiene sus propios elementos y el
# indice no puede alcanzar a los del otro. El diagrama vive aqui tambien, para
# no arrastrar el rotulo "(from ...)" (regla 2).
$p24 = Get-OCrearPaqueteModelo $p24p 'Ciclo 2'

# Regla 6: Package.Elements NO devuelve los elementos de tipo Package --- la
# API los esconde ---, asi que un buscar-o-crear que recorra Elements nunca
# encuentra un paquete ya creado y lo duplica en cada pasada. La lectura que
# no miente es SQL.
$yaEstan = @{}
$xml = $ea.SQLQuery(
  "SELECT o.Object_ID AS id, o.Name AS nombre, o.Object_Type AS tipo " +
  "FROM t_object o WHERE o.Package_ID=$($p24.PackageID)")
if ($xml) {
    $doc = New-Object System.Xml.XmlDocument
    $doc.LoadXml($xml)
    foreach ($fila in $doc.SelectNodes('//Row')) {
        $yaEstan["$($fila.tipo)|$($fila.nombre)"] = [int]$fila.id
    }
}
Write-Output "  ya habia $($yaEstan.Count) elementos en 2.4"

function Get-OCrearElemento24($nombre, $tipo, $notas) {
    $clave = "$tipo|$nombre"
    if ($yaEstan.ContainsKey($clave)) { return $ea.GetElementByID($yaEstan[$clave]) }
    $e = $p24.Elements.AddNew($nombre, $tipo)
    if ($notas) { $e.Notes = $notas }
    [void]$e.Update(); $p24.Elements.Refresh()
    $yaEstan[$clave] = $e.ElementID
    return $e
}

# Dependency pelado, sin estereotipo, como el 3.10a. Regla 5: se deduplica,
# porque borrar un diagrama no borra sus conectores.
function New-Dependencia($src, $dst) {
    $src.Connectors.Refresh()
    foreach ($c in $src.Connectors) {
        if ($c.SupplierID -eq $dst.ElementID -and $c.Type -eq 'Dependency') { return }
    }
    $c = $src.Connectors.AddNew('', 'Dependency')
    $c.SupplierID = $dst.ElementID
    $c.Direction  = 'Source -> Destination'
    [void]$c.Update(); $src.Connectors.Refresh()
}

# =========================================================================
# Los paquetes del Ciclo 2 y los del Ciclo 1 sobre los que se apoyan.
#
# P1 y P2 no se desarrollan en este ciclo, pero se dibujan: sin ellos, las
# dependencias de P4 y P6 apuntarian a la nada y el diagrama diria que el
# inventario no necesita saber en que sucursal esta.
#
# Las dependencias son las de docs/04-analisis-arquitectura.md, seccion 4.1:
#   P1 no depende de nadie     P2 -> P1            P3 -> P1, P2
#   P4 -> P2, P3               P5 -> P3, P4        P6 -> P1, P2, P3, P4
# =========================================================================
$paquetes = @(
  @{ k='p1'; n='P1 · Seguridad y Usuarios'
     nt='Identidad y acceso. En el Ciclo 2 no se desarrolla: se dibuja porque P6 lo usa para autorizar al Cliente y al Encargado. Es el paquete mas transversal del sistema y no depende de ninguno.'
     usa=@() },
  @{ k='p2'; n='P2 · Organización'
     nt='Estructura de la empresa. Provee la nocion de SUCURSAL, que es el eje sobre el que se particionan el inventario y las reservas. Depende de P1.'
     usa=@('p1') },
  @{ k='p3'; n='P3 · Catálogo (productos)'
     nt='Define QUE SE VENDE: productos, sus imagenes y sus variantes (SKU = producto x talla x color). En el Ciclo 2 se le agregan CU-10 y CU-11 sobre los maestros del Ciclo 1. Depende de P1 y P2.'
     usa=@('p1','p2') },
  @{ k='p4'; n='P4 · Inventario'
     nt='Define CUANTO HAY Y DONDE. Concentra la regla mas critica del sistema: ninguna cantidad se modifica sin generar un movimiento. Depende de P2 (sucursal) y P3 (variante).'
     usa=@('p2','p3') },
  @{ k='p5'; n='P5 · Catálogo Público y Disponibilidad'
     nt='La vista de solo lectura del cliente: busqueda, filtros, ficha y disponibilidad por sucursal. Separa la lectura del cliente de las operaciones del Administrador. Depende de P3 y P4.'
     usa=@('p3','p4') },
  @{ k='p6'; n='P6 · Reservas'
     nt='El ciclo de vida completo de la reserva. Cada transicion de estado produce un movimiento en P4: P6 NO escribe existencia por su cuenta. Depende de P1, P2, P3 y P4.'
     usa=@('p1','p2','p3','p4') }
)

# Las capas, de abajo hacia arriba. La base es la que no depende de nadie.
$capas = @(
  @('p1'),
  @('p2'),
  @('p3'),
  @('p4'),
  @('p5','p6')
)

$cohesion = @"
COHESIÓN — qué agrupa a cada paquete.

P3 reúne todo lo que define una prenda: producto, variante (SKU), imagen, y los maestros del Ciclo 1 —categoría, talla, color, temporada, colección—.
P4 reúne lo que dice cuánto hay y dónde: existencia y movimiento de inventario.
P5 no tiene tabla propia en este ciclo: es una fachada de lectura sobre P3 y P4, y esa es su razón de ser.
P6 reúne la reserva y su detalle, con los cinco estados de su ciclo de vida.

Ninguna clase encaja en dos paquetes a la vez, y sacar cualquiera deja a su paquete incompleto: eso es alta cohesión.
"@

$acoplamiento = @"
ACOPLAMIENTO — qué sabe cada paquete del otro.

Las dependencias van en un solo sentido y siempre hacia abajo: nunca hay un ciclo. P1 no conoce a ninguno; P5 y P6, que están arriba, no se conocen entre sí.

Las dos que importan en este ciclo:
· P5 → P4 es la costura C1. CU-19 le PIDE la disponibilidad a P4 en vez de consultar la tabla existencia, que es ajena.
· P6 → P4 es la mitigación del riesgo R5. P6 controla la transacción —apartar tres prendas es todo o nada— pero el movimiento de stock lo escribe P4, porque la regla «ninguna cantidad cambia sin movimiento» es de P4 y no puede estar en dos lugares.
"@

# ---------------- generacion ----------------

$nombre = '2.4 Analisis de Paquetes - CICLO #2'
if (BuscarDiagrama $p24 $nombre) {
    Write-Output "  $nombre ya existe, no se toca"
} else {
    $P = @{}
    foreach ($def in $paquetes) { $P[$def.k] = Get-OCrearElemento24 $def.n 'Package' $def.nt }
    foreach ($def in $paquetes) {
        foreach ($k in $def.usa) { New-Dependencia $P[$def.k] $P[$k] }
    }

    $d = $p24.Diagrams.AddNew($nombre, 'Package')
    $d.Notes = 'Paquetes del Ciclo 2 y los del Ciclo 1 sobre los que se apoyan, con sus dependencias.'
    [void]$d.Update(); $p24.Diagrams.Refresh()

    # La grilla del 3.10a: caja de 280 x 80, paso de fila 150, columnas cada
    # 320 y cada fila centrada sobre el mismo eje.
    $ANCHO = 280; $ALTO = 80; $PASO_FILA = 150
    $COLUMNAS = @{ 1 = @(360); 2 = @(200, 520); 3 = @(40, 360, 680) }

    $t = -60
    foreach ($fila in $capas) {
        $xs = $COLUMNAS[$fila.Count]
        for ($i = 0; $i -lt $fila.Count; $i++) {
            Poner $d $P[$fila[$i]] $xs[$i] $t $ANCHO $ALTO
        }
        $t -= $PASO_FILA
    }

    # Las dos notas de lectura, al pie. Van como Note en el lienzo y no solo en
    # las notas del diagrama: al exportar el PNG, las notas del elemento no se
    # ven.
    $nc = $p24.Elements.AddNew('', 'Note'); $nc.Notes = $cohesion;     [void]$nc.Update()
    $na = $p24.Elements.AddNew('', 'Note'); $na.Notes = $acoplamiento; [void]$na.Update()
    $t -= 40
    Poner $d $nc 40  $t 440 300
    Poner $d $na 520 $t 440 300

    # Sin clases contenidas no hay rectangulo que tape a nadie, asi que el
    # orden Z se puede dejar como viene. Es la ventaja de la receta nueva.
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    Write-Output "  $nombre : $($d.DiagramObjects.Count) objetos, $($d.DiagramLinks.Count) dependencias"
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
