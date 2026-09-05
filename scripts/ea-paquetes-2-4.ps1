# =========================================================================
# CAP. 2 - 2.4 Analisis de Paquetes: un diagrama por ciclo de desarrollo.
#
# El diagrama responde a las dos preguntas del capitulo:
#
#   COHESION      que hay DENTRO de cada paquete. Las clases se dibujan
#                 contenidas en su paquete: se ve de un vistazo que las cinco
#                 de P1 hablan de identidad, las cuatro de P2 de la estructura
#                 de la empresa y las cinco de P3 de la taxonomia del catalogo.
#
#   ACOPLAMIENTO  las lineas ENTRE paquetes. Son conectores Usage («use»), en
#                 un solo sentido: P2 -> P1 y P3 -> P1. P1 no conoce a ninguno
#                 de los otros dos, y P2 y P3 no se conocen entre si.
#
# La regla del 04/09/2026 --- toda union entre clases es una Association ---
# es para los diagramas de CLASES. Aqui no se une clase con clase: las clases
# solo se muestran dentro de su paquete, y lo unico que se conecta son los
# paquetes, con Usage, que es lo que expresa una dependencia de paquete.
#
# ---- POR QUE SE DUPLICAN LOS ELEMENTOS ----
# Los once paquetes de 2.1 y las clases de 2.2 ya existen en el modelo, pero
# aqui se crean elementos propios, por dos razones:
#
#   1. EA dibuja TODA relacion que exista entre los elementos presentes en el
#      lienzo. Las clases de 2.2 llevan encima los conectores Collaboration de
#      los nueve diagramas de comunicacion; reusarlas inundaria este diagrama
#      de mensajes que no vienen al caso.
#   2. Al reves, colgar las dependencias P2 -> P1 y P3 -> P1 de los paquetes de
#      2.1 las haria aparecer en 2.1.1 y 2.1.2, que ya estan acomodados a mano.
#
# Ademas, un diagrama y los elementos que muestra deben vivir en el mismo
# paquete, o EA rotula cada uno con "(from OtroPaquete)" y ensucia el dibujo.
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
    return $do
}
# El paquete es un rectangulo relleno y EA deja la secuencia Z sin definir
# (999999), asi que tapa las clases que contiene. Numero mas bajo = mas al
# frente: los paquetes al fondo, las clases y las notas adelante.
function Ordenar-Z($dia) {
    $i = 1
    foreach ($o in $dia.DiagramObjects) {
        $el = $ea.GetElementByID($o.ElementID)
        if ($el.Type -eq 'Package') { $o.Sequence = 100 } else { $o.Sequence = $i; $i++ }
        [void]$o.Update()
    }
}

$root     = $ea.Models.GetAt(0)
$pRaiz = Get-OCrearPaqueteModelo $root 'Violet Boutique'
$pCap2    = Get-OCrearPaqueteModelo $pRaiz 'CAP. 2 - Flujo de Trabajo: Analisis'
$p24      = Get-OCrearPaqueteModelo $pCap2 '2.4 Analisis de Paquetes'

# El indice de lo que ya hay en el paquete, leido por SQL y no por la API.
#
# OJO: la coleccion Package.Elements NO incluye a los elementos de tipo
# Package --- la API los esconde. Un Get-O-Crear que recorra Elements nunca
# encuentra un paquete ya creado y lo vuelve a crear en cada pasada. Asi es
# como en 2.1 los once paquetes terminaron TRIPLICADOS: el generador se corrio
# tres veces y cada diagrama apunta a una copia distinta.
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

function Get-OCrearElemento24($nombre, $tipo, $estereotipo, $notas) {
    $clave = "$tipo|$nombre"
    if ($yaEstan.ContainsKey($clave)) { return $ea.GetElementByID($yaEstan[$clave]) }
    $e = $p24.Elements.AddNew($nombre, $tipo)
    if ($estereotipo) { $e.Stereotype = $estereotipo; $e.StereotypeEx = $estereotipo }
    if ($notas) { $e.Notes = $notas }
    [void]$e.Update(); $p24.Elements.Refresh()
    $yaEstan[$clave] = $e.ElementID
    return $e
}

function New-Dependencia($src, $dst) {
    foreach ($c in $src.Connectors) {
        if ($c.SupplierID -eq $dst.ElementID -and $c.Type -eq 'Usage') { return }
    }
    $c = $src.Connectors.AddNew('', 'Usage')
    $c.SupplierID = $dst.ElementID
    $c.Direction  = 'Source -> Destination'
    [void]$c.Update(); $src.Connectors.Refresh()
}

# =========================================================================
# Los ciclos.
#
# Solo esta el Ciclo 1, que es el que tiene sus clases analizadas. Los ciclos
# 2 y 3 se agregan aqui cuando se desarrollen --- el reparto de paquetes por
# ciclo esta en docs/04-analisis-arquitectura.md, seccion 4.1.4.
#
# 'usa' son las claves de los paquetes de los que depende, dentro del mismo
# ciclo. El contenido de cada paquete sale de la tabla de 2.4 en
# docs/entregas/ciclo-1/cap-2-3-analisis-y-diseno.md.
# =========================================================================
$ciclos = @(
  @{
    ciclo = 1
    paquetes = @(
      @{ k='p1'; n='P1 · Seguridad y Usuarios'
         nt='Identidad y acceso. Realiza CU-01, CU-02, CU-03 y CU-04. No depende de ningun otro paquete: es el mas transversal del sistema y los ocho restantes lo usaran para autorizar.'
         clases=@('Usuario','Rol','Permiso','Cliente','SesionToken')
         usa=@() },
      @{ k='p2'; n='P2 · Organización'
         nt='Estructura de la empresa. Realiza CU-05, CU-06 y CU-07. Depende de P1 porque un Empleado es un Usuario con rol.'
         clases=@('Ciudad','Sucursal','Empleado','Proveedor')
         usa=@('p1') },
      @{ k='p3'; n='P3 · Catálogo (maestros)'
         nt='Taxonomia del catalogo. Realiza CU-08 y CU-09. Depende de P1 solo para autorizar quien administra los maestros; no conoce a P2.'
         clases=@('Categoria','Talla','Color','Temporada','Coleccion')
         usa=@('p1') }
    )
    cohesion   = "COHESION --- que agrupa a cada paquete.`n`nP1 reune todo lo que responde «quien sos y que podes hacer»; P2, la estructura fisica y comercial de la empresa; P3, las listas que definen una prenda. Ninguna clase encaja en dos paquetes a la vez, y sacar cualquiera de ellas deja a su paquete incompleto: eso es alta cohesion."
    acoplamiento = "ACOPLAMIENTO --- que sabe cada paquete del otro.`n`nLas dependencias «use» van en un solo sentido: P2 -> P1 y P3 -> P1. P1 no conoce a ninguno de los otros dos, y P2 y P3 no se conocen entre si. Dos flechas para tres paquetes es el minimo posible sin dejarlos aislados: eso es bajo acoplamiento.`n`nEs lo que permite construir el Ciclo 1 sin que existan todavia los paquetes de los Ciclos 2 y 3."
  }
)

foreach ($c in $ciclos) {
    $nombre = "2.4 Analisis de Paquetes - CICLO #$($c.ciclo)"
    if (BuscarDiagrama $p24 $nombre) { Write-Output "  $nombre ya existe, no se toca"; continue }

    # ---- elementos ----
    $P = @{}
    # Ojo con el nombre. PowerShell no distingue mayusculas de minusculas en
    # los nombres de variable, asi que este mapa no puede llamarse ni como el
    # ciclo que se recorre afuera ni como la clase del bucle de adentro: los
    # tres serian la misma variable y el mapa terminaria siendo una cadena.
    $mapaClases = @{}
    foreach ($def in $c.paquetes) {
        $P[$def.k] = Get-OCrearElemento24 $def.n 'Package' $null $def.nt
        foreach ($cl in $def.clases) {
            if (-not $mapaClases.ContainsKey($cl)) {
                $mapaClases[$cl] = Get-OCrearElemento24 $cl 'Class' 'entidad' $null
            }
        }
    }
    foreach ($def in $c.paquetes) {
        foreach ($k in $def.usa) { New-Dependencia $P[$def.k] $P[$k] }
    }

    # ---- lienzo ----
    # El paquete del que dependen los demas va arriba y solo; los que dependen
    # de el, debajo. Asi las flechas «use» apuntan siempre hacia arriba y la
    # jerarquia se lee sin seguir las puntas.
    $d = $p24.Diagrams.AddNew($nombre, 'Package')
    $d.Notes = "Paquetes del Ciclo $($c.ciclo), su contenido (cohesion) y sus dependencias (acoplamiento)."
    [void]$d.Update(); $p24.Diagrams.Refresh()

    $anchoPaq = 320; $anchoCls = 240; $altoCls = 70; $paso = 90
    $sepH = 120; $sepV = 120; $margen = 40

    $filas = @()
    $filas += ,@($c.paquetes | Where-Object { $_.usa.Count -eq 0 })   # arriba: los que no dependen de nadie
    $filas += ,@($c.paquetes | Where-Object { $_.usa.Count -gt 0 })   # abajo:  los que dependen

    # Cada fila se centra contra la mas ancha, para que la raiz quede sobre el
    # medio de sus dependientes y las flechas no salgan en diagonal larga.
    $anchoMax = 0
    foreach ($fila in $filas) {
        $w = $fila.Count * $anchoPaq + ($fila.Count - 1) * $sepH
        if ($w -gt $anchoMax) { $anchoMax = $w }
    }

    $t = -$margen
    foreach ($fila in $filas) {
        $altoFila = 0
        $w = $fila.Count * $anchoPaq + ($fila.Count - 1) * $sepH
        $l = $margen + [int](($anchoMax - $w) / 2)
        foreach ($def in $fila) {
            $altoPaq = 100 + $def.clases.Count * $paso
            if ($altoPaq -gt $altoFila) { $altoFila = $altoPaq }
            Poner $d $P[$def.k] $l $t $anchoPaq $altoPaq | Out-Null
            $tc = $t - 70
            foreach ($cl in $def.clases) {
                Poner $d $mapaClases[$cl] ($l + 40) $tc $anchoCls $altoCls | Out-Null
                $tc -= $paso
            }
            $l += ($anchoPaq + $sepH)
        }
        $t -= ($altoFila + $sepV)
    }

    # ---- las dos notas de lectura ----
    # Van como Note en el lienzo y no solo en las notas del diagrama: al
    # exportar el PNG, las notas del elemento no se ven. Se reparten el ancho
    # del dibujo para que el pie quede alineado con los paquetes.
    $anchoNota = [int](($anchoMax - 20) / 2)
    $nc = $p24.Elements.AddNew('', 'Note'); $nc.Notes = $c.cohesion;     [void]$nc.Update()
    $na = $p24.Elements.AddNew('', 'Note'); $na.Notes = $c.acoplamiento; [void]$na.Update()
    Poner $d $nc $margen $t $anchoNota 280 | Out-Null
    Poner $d $na ($margen + $anchoNota + 20) $t $anchoNota 280 | Out-Null

    # Ordenar-Z recorre $d.DiagramObjects, que sigue con la copia que tenia al
    # crearse el diagrama --- vacia. Sin este Refresh no encuentra nada que
    # ordenar, no da error, y los paquetes quedan tapando a sus clases.
    $d.DiagramObjects.Refresh()
    Ordenar-Z $d
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    Write-Output "  $nombre : $($d.DiagramObjects.Count) objetos, $($d.DiagramLinks.Count) dependencias"
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
