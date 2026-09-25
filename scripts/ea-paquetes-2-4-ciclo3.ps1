param(
    # Borra el diagrama del Ciclo 3 con sus elementos y conectores, y lo
    # vuelve a generar de cero. Es lo que hubo que correr el 21/09 para
    # arreglar los tres defectos de la primera pasada.
    [switch]$Rehacer
)

# =========================================================================
# CAP. 2 - 2.4 Analisis de Paquetes. CICLO 3.
#
# Sigue la receta del Ciclo 2 --- ea-paquetes-2-4-ciclo2.ps1 --- sin
# cambiarla: paquetes solos sin las clases adentro, `Dependency` en vez de
# `Usage`, disposicion en piramide con la base abajo, y las dos notas de
# cohesion y acoplamiento al pie.
#
# Lo unico que cambia respecto del Ciclo 2 es el contenido: SON ONCE
# PAQUETES Y OCHO CAPAS, no seis y cinco. El sistema completo se dibuja
# porque los cinco paquetes nuevos se apoyan en todos los anteriores: sin
# P1 a P6 en el lienzo, las flechas de P7 y P11 apuntarian a la nada.
#
# ---- LOS TRES DEFECTOS DE LA PRIMERA PASADA (20/09), Y POR QUE ----
#
# 1. LOS NOMBRES SALIERON CON CARACTERES ROTOS --- `OrganizaciA3n`, `A7`.
#    El archivo se habia guardado SIN BOM, y PowerShell 5.1 lee un .ps1 sin
#    BOM como ANSI (Windows-1252), no como UTF-8. Cada acento entraba al
#    modelo como los dos bytes de su UTF-8 leidos por separado. No da
#    ningun error: el script corre y escribe basura.
#    ESTE ARCHIVO TIENE QUE QUEDAR GUARDADO EN UTF-8 CON BOM.
#
# 2. SE DIBUJABAN TRES ACTORES ---la pasarela, el modelo de IA y el
#    servicio de RA--- y en un diagrama de paquetes no van: la seccion 2.4
#    habla de la descomposicion INTERNA del sistema, y un actor ahi dentro
#    mezcla dos modelos. Los servicios externos ya estan donde les
#    corresponde: en los diagramas de casos de uso y en el 3.1.2 de
#    despliegue. Lo que justifica que P8 y P10 existan se dice con
#    palabras, en la nota de acoplamiento, que es donde se lee.
#
# 3. LAS DOS NOTAS NO LLEGARON A CREARSE. El diagrama quedo con once
#    objetos y ninguno era una Note: la corrida murio al colocar el primer
#    actor, que es justo el paso anterior. Como el guardia de mas abajo es
#    «si el diagrama ya existe, no se toca», una segunda corrida no las
#    agregaba nunca. Por eso este script ahora acepta -Rehacer.
#
# Los diagramas de los Ciclos 1 y 2 NO se rehacen: quedan como estan.
# NO EXPORTA IMAGENES. Las exporta Mateo a mano desde EA.
#
# ADITIVO: abre el modelo y solo agrega lo que falta, salvo con -Rehacer.
#
# OJO AL CORRER VARIOS GENERADORES SEGUIDOS: cada uno deja un proceso EA
# vivo. El 20/09 se acumularon 24 y el siguiente fallo con «failed to
# create empty document», que no es un error del modelo sino agotamiento de
# recursos. Entre corrida y corrida:
#     Get-Process EA -ErrorAction SilentlyContinue | Stop-Process -Force
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

$NOMBRE_DIAGRAMA = '2.4 Analisis de Paquetes - CICLO #3'

# =========================================================================
# PARTE 0 - La limpieza de -Rehacer, por OLEDB y con EA cerrado.
#
# Va por SQL y no por la API COM por la regla 6: `Package.Elements` NO
# devuelve los elementos de tipo Package, que aca son los once. Por COM
# habria que borrarlos de a uno buscandolos por ID, y los conectores
# quedarian huerfanos (regla 5). En SQL se borra el paquete entero.
#
# El subpaquete «Ciclo 3» es exclusivo de este diagrama --- por eso existe
# ---, asi que vaciarlo no toca nada de nadie.
# =========================================================================
if ($Rehacer) {
    $cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$modelo;")
    $cn.Open()
    function Escalar($sql) { $c = $cn.CreateCommand(); $c.CommandText = $sql; return $c.ExecuteScalar() }
    function Ejecutar($sql) { $c = $cn.CreateCommand(); $c.CommandText = $sql; return $c.ExecuteNonQuery() }

    $idPadre = Escalar "SELECT Package_ID FROM t_package WHERE Name = '2.4 Analisis de Paquetes'"
    if (-not $idPadre) { throw 'No existe el paquete 2.4 Analisis de Paquetes' }
    $idPkg = Escalar "SELECT Package_ID FROM t_package WHERE Parent_ID = $idPadre AND Name = 'Ciclo 3'"

    if (-not $idPkg) {
        Write-Output '  -Rehacer: todavia no hay nada del Ciclo 3 que borrar'
    } else {
        $enPkg = "(SELECT Object_ID FROM t_object WHERE Package_ID = $idPkg)"
        # Ojo con el orden: los conectores y los objetos de diagrama antes que
        # los elementos, o las subconsultas ya no encuentran a quien borrar.
        $nDia = Ejecutar "DELETE FROM t_diagramobjects WHERE Diagram_ID IN (SELECT Diagram_ID FROM t_diagram WHERE Package_ID = $idPkg)"
        # t_diagramlinks lleva DiagramID SIN guion bajo, al reves que todas las
        # demas tablas. Escribirlo `Diagram_ID` no da «columna inexistente»:
        # ACE lo toma por un parametro y falla con «faltan valores para algunos
        # de los parametros requeridos», que no se parece en nada a la causa.
        $nLnk = Ejecutar "DELETE FROM t_diagramlinks WHERE DiagramID IN (SELECT Diagram_ID FROM t_diagram WHERE Package_ID = $idPkg)"
        $nCon = Ejecutar "DELETE FROM t_connector WHERE Start_Object_ID IN $enPkg OR End_Object_ID IN $enPkg"
        $nXrf = Ejecutar "DELETE FROM t_xref WHERE Client IN (SELECT ea_guid FROM t_object WHERE Package_ID = $idPkg)"
        $nObj = Ejecutar "DELETE FROM t_object WHERE Package_ID = $idPkg"
        $nDgm = Ejecutar "DELETE FROM t_diagram WHERE Package_ID = $idPkg"
        Write-Output "  -Rehacer: $nObj elementos, $nCon conectores, $nDgm diagramas, $nDia objetos de lienzo, $nLnk enlaces, $nXrf filas de t_xref"
    }
    $cn.Close()
}

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

# Subpaquete propio del ciclo, por la misma razon que en el Ciclo 2: si se
# reutilizaran los elementos del otro diagrama, las dependencias nuevas
# quedarian colgadas de ellos y apareceria una flecha de mas sobre un dibujo
# ya acomodado a mano. No da error y no se ve hasta que alguien lo abre.
$p24 = Get-OCrearPaqueteModelo $p24p 'Ciclo 3'

# Regla 6: `Package.Elements` NO devuelve los elementos de tipo Package. La
# lectura que no miente es SQL.
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
Write-Output "  ya habia $($yaEstan.Count) elementos en 2.4 / Ciclo 3"

function Get-OCrearElemento24($nombre, $tipo, $notas) {
    $clave = "$tipo|$nombre"
    if ($yaEstan.ContainsKey($clave)) { return $ea.GetElementByID($yaEstan[$clave]) }
    $e = $p24.Elements.AddNew($nombre, $tipo)
    if ($notas) { $e.Notes = $notas }
    [void]$e.Update(); $p24.Elements.Refresh()
    $yaEstan[$clave] = $e.ElementID
    return $e
}

# Regla 5: se deduplica, porque borrar un diagrama no borra sus conectores.
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
# Los once paquetes. Las dependencias son las de
# docs/04-analisis-arquitectura.md, seccion 4.1, literales:
#
#   P1 -> nadie      P2 -> P1            P3 -> P1, P2
#   P4 -> P2, P3     P5 -> P3, P4        P6 -> P1, P2, P3, P4
#   P7 -> P1, P2, P3, P4, P6             P8 -> P7
#   P9 -> P3, y se comunica con P5, P6 y P7
#   P10 -> consume de los demas y NADIE lo consulta
#   P11 -> P4, P6, P7, P8, en solo lectura
# =========================================================================
$paquetes = @(
  @{ k='p1'; n='P1 · Seguridad y Usuarios'
     nt='Identidad y acceso. Sigue siendo el paquete más transversal y el único que no depende de ninguno. En este ciclo se le suman CU-41 (recuperar contraseña) y CU-42 (bitácora).'
     usa=@() },
  @{ k='p2'; n='P2 · Organización'
     nt='Estructura de la empresa. Provee la noción de SUCURSAL, que en este ciclo además particiona las cajas y los turnos. Depende de P1.'
     usa=@('p1') },
  @{ k='p3'; n='P3 · Catálogo (productos)'
     nt='Define QUÉ SE VENDE. En este ciclo se le suma CU-12 (promociones), que es lo que hace que el precio cobrado no sea siempre el de lista. Depende de P1 y P2.'
     usa=@('p1','p2') },
  @{ k='p4'; n='P4 · Inventario'
     nt='Define CUÁNTO HAY Y DÓNDE. Ninguna cantidad se modifica sin generar un movimiento, y en este ciclo esa regla la invocan también P7 y P8. Depende de P2 y P3.'
     usa=@('p2','p3') },
  @{ k='p5'; n='P5 · Catálogo Público y Disponibilidad'
     nt='La vista de solo lectura del cliente. En este ciclo se le suma CU-20 (favoritos), que es la señal que alimenta al recomendador de P10. Depende de P3 y P4.'
     usa=@('p3','p4') },
  @{ k='p6'; n='P6 · Reservas'
     nt='El ciclo de vida de la reserva. En este ciclo aparece su salida natural: una reserva atendida se convierte en venta de P7. Depende de P1, P2, P3 y P4.'
     usa=@('p1','p2','p3','p4') },
  @{ k='p7'; n='P7 · Ventas y Punto de Venta'
     nt='Unifica los DOS CANALES sobre una misma entidad: el carrito y el pedido digital, y la venta presencial en caja con su turno, su comprobante y sus devoluciones. Es el paquete que hace que el inventario sea uno solo. Depende de P1, P2, P3, P4 y P6.'
     usa=@('p1','p2','p3','p4','p6') },
  @{ k='p8'; n='P8 · Pagos'
     nt='Aísla la integración con la pasarela de pago: inicia el cobro, recibe su notificación firmada y confirma el pedido. Existe como paquete propio para que cambiar de pasarela no toque P7. Depende de P7.'
     usa=@('p7') },
  @{ k='p9'; n='P9 · Vestidor Virtual (RA)'
     nt='Vive en la aplicación móvil. Toma la cámara, detecta la pose y superpone el PNG de la variante. Depende de P3 por la imagen y la variante, y deriva a P5, P6 y P7 cuando el cliente decide llevarse la prenda.'
     usa=@('p3','p5','p6','p7') },
  @{ k='p10'; n='P10 · Inteligencia Artificial'
     nt='Recomendador, asistente conversacional y reportes por voz. CONSUME de los demás y NINGUNO lo consulta: es la propiedad que permite apagarlo sin afectar la operación. El razonamiento lo delega en un modelo externo.'
     usa=@('p3','p4','p6','p7','p11') },
  @{ k='p11'; n='P11 · Reportes y Tablero'
     nt='Consolida para decidir: los KPIs del tablero y los reportes exportables. Depende de los paquetes transaccionales en SOLO LECTURA, y esa unidireccionalidad es la que permite agregar reportes sin tocar la lógica de venta.'
     usa=@('p4','p6','p7','p8') }
)

# Las capas, de abajo hacia arriba. La base es la que no depende de nadie.
# Ocho, porque el Ciclo 3 apila sobre todo lo anterior.
$capas = @(
  @('p1'),
  @('p2'),
  @('p3'),
  @('p4'),
  @('p5','p6'),
  @('p7'),
  @('p8','p11'),
  @('p9','p10')
)

$cohesion = @"
COHESIÓN — qué agrupa a cada paquete nuevo.

P7 reúne todo lo que es una venta, en sus dos canales: carrito, pedido, venta presencial, caja y turno, comprobante y devolución. Están juntos porque comparten la entidad venta y el mismo descuento de inventario; separar el canal digital del presencial habría duplicado esa lógica.

P8 reúne el pago y la transacción de la pasarela. Es poco, y es a propósito: lo que lo hace un paquete no es su tamaño sino que concentra TODO el acoplamiento con un servicio externo.

P9 reúne la sesión de prueba virtual y la medida corporal del cliente. Vive casi entero en el teléfono.

P10 reúne los tres casos de IA. Ninguno escribe en la base salvo la recomendación, y ninguno es consultado por otro paquete.

P11 reúne el tablero y los reportes exportables. Es de solo lectura: no tiene ninguna tabla propia.

Ninguna clase encaja en dos paquetes a la vez, y sacar cualquiera deja a su paquete incompleto: eso es alta cohesión.
"@

$acoplamiento = @"
ACOPLAMIENTO — qué sabe cada paquete del otro.

Las dependencias van en un solo sentido y siempre hacia abajo: no hay ningún ciclo en los once paquetes.

Las cuatro que importan en este ciclo:

· P8 → P7 y nada más. La pasarela de pago solo la conoce P8, y por eso cambiarla no toca la venta. Es el motivo de que P8 exista como paquete y no como una carpeta de P7.

· P7 → P4 es la costura C1 otra vez. P7 controla la transacción —apartar el pedido es todo o nada— pero el movimiento de stock lo escribe P4, porque la regla «ninguna cantidad cambia sin movimiento» no puede estar en dos lugares.

· P10 no tiene ninguna flecha entrante. Es un consumidor puro, y esa propiedad es la que permite apagar la IA sin que deje de funcionar nada: si el modelo externo no responde, las pantallas de P10 dicen que no está disponible y el resto del sistema no se entera.

· P11 depende de cuatro paquetes pero solo los LEE. Nunca escribe, y por eso agregar un reporte no puede romper una venta.

Los servicios de terceros —la pasarela, el modelo de lenguaje y la detección de pose— no se dibujan acá: este diagrama es la descomposición interna del sistema. Están donde les corresponde, en los casos de uso y en el despliegue 3.1.2. Que P8 y P10 existan precisamente para aislarlos es lo que dicen los dos puntos de arriba.
"@

# ---------------- generacion ----------------

if (BuscarDiagrama $p24 $NOMBRE_DIAGRAMA) {
    Write-Output "  $NOMBRE_DIAGRAMA ya existe, no se toca. Para rehacerlo: -Rehacer"
} else {
    $P = @{}
    foreach ($def in $paquetes) { $P[$def.k] = Get-OCrearElemento24 $def.n 'Package' $def.nt }
    foreach ($def in $paquetes) {
        foreach ($k in $def.usa) { New-Dependencia $P[$def.k] $P[$k] }
    }

    $d = $p24.Diagrams.AddNew($NOMBRE_DIAGRAMA, 'Package')
    $d.Notes = 'Los once paquetes del sistema completo con sus dependencias. Ciclo 3.'
    [void]$d.Update(); $p24.Diagrams.Refresh()

    # La misma grilla del Ciclo 2: caja de 280 x 80, paso de fila 150 y cada
    # fila centrada sobre el mismo eje.
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

    # Las dos notas de lectura, al pie. Van como Note EN EL LIENZO y no solo
    # en las notas del elemento: al exportar el PNG, esas no se ven (regla 8).
    # Mas altas que las del Ciclo 2 --- 460 contra 300 --- porque el texto es
    # el doble de largo y EA recorta lo que no entra en la caja, sin avisar.
    $nc = $p24.Elements.AddNew('', 'Note'); $nc.Notes = $cohesion;     [void]$nc.Update()
    $na = $p24.Elements.AddNew('', 'Note'); $na.Notes = $acoplamiento; [void]$na.Update()
    $p24.Elements.Refresh()
    $t -= 40
    Poner $d $nc 20  $t 540 460
    Poner $d $na 600 $t 540 460

    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    Write-Output "  $NOMBRE_DIAGRAMA : $($d.DiagramObjects.Count) objetos, $($d.DiagramLinks.Count) dependencias"
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
