param(
    # Borra el subpaquete 'Ciclo 3' de 3.3.1 y lo vuelve a generar.
    [switch]$Rehacer
)

# =========================================================================
# CAP. 3 - 3.3.1 Diseno de Datos Logico. CICLO 3: EL SISTEMA ENTERO.
#
# A diferencia del Ciclo 2 ---que dibujaba sus ocho tablas nuevas mas las de
# apoyo a las que apuntaban--- este lleva LAS 43 TABLAS. Es el modelo de datos
# completo al cerrar el proyecto, que es lo que pidio Karen.
#
# EL CONTENIDO NO SE TRANSCRIBE A MANO. Las columnas, sus tipos y los
# estereotipos PK/FK salen de `information_schema` de la base de pruebas, que
# `alembic upgrade head` deja al dia; los genera gen-dominio-3-3-1-ciclo3.py
# en el archivo de datos que este script carga.
#
# LAS CARDINALIDADES SALEN DE LO QUE LA BASE OBLIGA, NO DE LA PROSA
# ------------------------------------------------------------------
# Un extremo es `1` cuando la columna es NOT NULL y `0..1` cuando admite nulo;
# el otro es `0..1` cuando la columna es UNIQUE y `0..*` cuando no. Si
# `cliente.usuario_id` es UNIQUE NOT NULL, un usuario tiene 0 o 1 ficha de
# cliente --- nunca «exactamente 1», porque un administrador no es cliente.
#
# POR QUE UN SUBPAQUETE PROPIO
# ----------------------------
# Las entidades de los Ciclos 1 y 2 ya existen en 3.3.1 con sus relaciones.
# Reusarlas tendria dos efectos, los dos malos (reglas 2 y 3):
#   - las relaciones NUEVAS quedarian colgadas de esos elementos y apareceria
#     una linea de mas en los diagramas de aquellos ciclos, que ya estan
#     acomodados;
#   - EA dibujaria ademas las relaciones VIEJAS entre ellas.
# Es la misma decision que se tomo en 2.4 y en el 3.3.1 del Ciclo 2.
#
# NO EXPORTA IMAGENES. Las exporta Mateo a mano desde EA (pedido del 13/09).
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\SI2\Primer_Parcial\docs\diagramas\VioletBoutique.eapx'
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

. (Join-Path $PSScriptRoot 'ea-datos-3-3-1-ciclo3.datos.ps1')

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
$pCap3 = Get-OCrearPaqueteModelo $pRaiz 'CAP. 3 - Flujo de Trabajo: Diseno'
$p331p = Get-OCrearPaqueteModelo $pCap3 '3.3.1 Diseno de Datos Logico'

if ($Rehacer) {
    # De atras para adelante: borrar corre los indices que faltan visitar.
    $p331p.Packages.Refresh()
    for ($i = $p331p.Packages.Count - 1; $i -ge 0; $i--) {
        if ($p331p.Packages.GetAt($i).Name -eq 'Ciclo 3') {
            $p331p.Packages.DeleteAt($i, $false)
            Write-Output '  subpaquete Ciclo 3 anterior eliminado (-Rehacer)'
        }
    }
    $p331p.Packages.Refresh()
}
$p331 = Get-OCrearPaqueteModelo $p331p 'Ciclo 3'

# Regla 6: `Package.Elements` no devuelve los elementos de tipo Package, y la
# lectura que no miente es SQL.
$yaEstan = @{}
$xml = $ea.SQLQuery("SELECT o.Object_ID AS id, o.Name AS nombre FROM t_object o WHERE o.Package_ID=$($p331.PackageID) AND o.Object_Type='Class'")
if ($xml) {
    $doc = New-Object System.Xml.XmlDocument
    $doc.LoadXml($xml)
    foreach ($fila in $doc.SelectNodes('//Row')) { $yaEstan["$($fila.nombre)"] = [int]$fila.id }
}
Write-Output "  ya habia $($yaEstan.Count) entidades en 3.3.1 / Ciclo 3"

function Get-OCrearEntidad($nombre) {
    if ($yaEstan.ContainsKey($nombre)) { return $ea.GetElementByID($yaEstan[$nombre]) }
    $e = $p331.Elements.AddNew($nombre, 'Class')
    [void]$e.Update(); $p331.Elements.Refresh()
    $yaEstan[$nombre] = $e.ElementID
    return $e
}

# Cada columna es @{n=nombre; t=tipo; k='PK'|'FK'|'PK,FK'|$null}. Sin
# operaciones: es un modelo de datos, no de comportamiento.
function Set-Columnas($el, $lista) {
    $ya = @{}
    foreach ($a in $el.Attributes) { $ya[$a.Name] = $a }
    $i = 0
    foreach ($col in $lista) {
        if ($ya.ContainsKey($col.n)) { $at = $ya[$col.n] } else { $at = $el.Attributes.AddNew($col.n, $col.t) }
        $at.Type       = $col.t
        $at.Visibility = 'Private'
        $at.Pos        = $i
        if ($col.k) { $at.Stereotype = $col.k }
        [void]$at.Update()
        $i++
    }
    $el.Attributes.Refresh()
}

# Regla 5: borrar un diagrama no borra sus conectores; se deduplica siempre.
function New-Relacion($src, $dst, $verbo, $cardOrigen, $cardDestino) {
    $src.Connectors.Refresh()
    foreach ($c in $src.Connectors) {
        if ($c.SupplierID -eq $dst.ElementID -and $c.Type -eq 'Association' -and $c.Name -eq $verbo) { return }
    }
    $c = $src.Connectors.AddNew($verbo, 'Association')
    $c.SupplierID = $dst.ElementID
    [void]$c.Update()                          # PRIMERO el conector...
    $c.ClientEnd.Cardinality   = $cardOrigen   # ...y despues los extremos, o
    $c.SupplierEnd.Cardinality = $cardDestino  # EA no guarda la cardinalidad
    [void]$c.ClientEnd.Update(); [void]$c.SupplierEnd.Update(); [void]$c.Update()
    $src.Connectors.Refresh()
}

# --- las entidades --------------------------------------------------------
$E = @{}
foreach ($t in $TABLAS_C3) {
    $el = Get-OCrearEntidad $t.n
    Set-Columnas $el $t.cols
    $E[$t.n] = $el
}
Write-Output "  $($TABLAS_C3.Count) entidades con sus columnas"

foreach ($r in $RELACIONES_C3) {
    if (-not $E.ContainsKey($r.o)) { throw "Relacion con origen inexistente: $($r.o)" }
    if (-not $E.ContainsKey($r.d)) { throw "Relacion con destino inexistente: $($r.d)" }
    New-Relacion $E[$r.o] $E[$r.d] $r.v $r.co $r.cd
}
Write-Output "  $($RELACIONES_C3.Count) relaciones"

# --- el diagrama ----------------------------------------------------------
$nombre = '3.3.1 Modelo de Dominio - CICLO #3'
if ((BuscarDiagrama $p331 $nombre) -and -not $Rehacer) {
    Write-Output "  $nombre ya existe, no se toca"
} else {
    $p331.Diagrams.Refresh()
    for ($i = $p331.Diagrams.Count - 1; $i -ge 0; $i--) {
        if ($p331.Diagrams.GetAt($i).Name -eq $nombre) { $p331.Diagrams.DeleteAt($i, $false) }
    }
    $p331.Diagrams.Refresh()

    $d = $p331.Diagrams.AddNew($nombre, 'Logical')
    $d.Notes = 'Modelo de dominio al cerrar el Ciclo 3: las 43 tablas del sistema, con sus tipos, sus claves y las cardinalidades que la base obliga.'
    [void]$d.Update(); $p331.Diagrams.Refresh()

    # Columnas agrupadas por paquete de analisis, de izquierda a derecha, en el
    # orden en que las tablas se apuntan: primero a las que apuntan las demas.
    # CATEGORIA se subdivide en si misma, asi que necesita aire a la derecha ---
    # por eso no va pegada al borde de su columna.
    $COLUMNAS = @(
        @{ x=40;   tablas=@('ROL','PERMISO','ROL_PERMISO','USUARIO','SESION_TOKEN','TOKEN_RECUPERACION') },
        @{ x=400;  tablas=@('CLIENTE','DIRECCION_CLIENTE','CLIENTE_CATEGORIA','MEDIDA_CLIENTE','EMPLEADO','CIUDAD','SUCURSAL','PROVEEDOR') },
        @{ x=760;  tablas=@('CATEGORIA','TALLA','COLOR','TEMPORADA','COLECCION','MEDIDA_TALLA') },
        @{ x=1120; tablas=@('PRODUCTO','VARIANTE_PRODUCTO','IMAGEN_PRODUCTO','PROMOCION','FAVORITO') },
        @{ x=1480; tablas=@('EXISTENCIA','MOVIMIENTO_INVENTARIO','ABASTECIMIENTO') },
        @{ x=1840; tablas=@('RESERVA','RESERVA_DETALLE','RECOMENDACION') },
        @{ x=2200; tablas=@('CARRITO','CARRITO_DETALLE','VENTA','DETALLE_VENTA','PAGO','TRANSACCION_PASARELA','COMPROBANTE') },
        @{ x=2560; tablas=@('CAJA','TURNO_CAJA','DEVOLUCION','DETALLE_DEVOLUCION') },
        @{ x=2920; tablas=@('BITACORA') }
    )
    $ANCHO = 300

    $porNombre = @{}
    foreach ($t in $TABLAS_C3) { $porNombre[$t.n] = $t }

    # Nadie puede quedar afuera del reparto por un descuido al escribir las
    # columnas: si falta o sobra una tabla, se corta aca y no en la defensa.
    $puestas = @{}
    foreach ($col in $COLUMNAS) { foreach ($n in $col.tablas) { $puestas[$n] = $true } }
    $olvidadas = @()
    foreach ($t in $TABLAS_C3) { if (-not $puestas.ContainsKey($t.n)) { $olvidadas += $t.n } }
    if ($olvidadas.Count) { throw "Tablas sin columna asignada: $($olvidadas -join ', ')" }
    foreach ($n in $puestas.Keys) { if (-not $porNombre.ContainsKey($n)) { throw "En el reparto hay una tabla que no existe: $n" } }

    $fondo = 0
    foreach ($col in $COLUMNAS) {
        $t = -40
        foreach ($n in $col.tablas) {
            # Alto por contenido: si queda corta, EA recorta la lista sin avisar.
            $alto = 60 + ($porNombre[$n].cols.Count * 18)
            Poner $d $E[$n] $col.x $t $ANCHO $alto
            $t = $t - $alto - 50
        }
        if ($t -lt $fondo) { $fondo = $t }
    }

    $nota = $p331.Elements.AddNew('', 'Note')
    $nota.Notes = @"
MODELO DE DOMINIO — CICLO 3 · EL SISTEMA COMPLETO

Las 43 tablas del esquema, agrupadas por paquete de análisis de izquierda a derecha. El tipo de cada columna y los estereotipos «PK» y «FK» salen de information_schema, no de una transcripción.

Las cardinalidades son las que la base OBLIGA, no las de la prosa: un extremo es 1 cuando la columna es NOT NULL y 0..1 cuando admite nulo; el otro es 0..1 cuando la columna es UNIQUE y 0..* cuando no.

Cuatro que conviene mirar en la defensa:
· La VARIANTE_PRODUCTO es la unidad de negocio: es lo único que tiene EXISTENCIA, RESERVA_DETALLE, DETALLE_VENTA y DETALLE_DEVOLUCION (decisión D1). El PRODUCTO es el concepto comercial.
· Hay UNA sola VENTA para los dos canales, en línea y mostrador; la columna canal los distingue (decisión D2). Por eso TURNO_CAJA se le cuelga con 0..1: la venta en línea no pasa por caja.
· EXISTENCIA lleva disponible y reservada POR SEPARADO. Reservar traslada unidades entre las dos y el total físico no cambia (decisión D3), y MOVIMIENTO_INVENTARIO es el historial inmutable que lo explica (invariante D4).
· El estado de PAGO solo lo mueve TRANSACCION_PASARELA, que guarda el identificador del evento firmado (decisión D5). Es lo que hace que una notificación repetida no descuente el inventario dos veces.

No figura ninguna tabla de notificaciones: CU-40 no está construido.
"@
    [void]$nota.Update()
    Poner $d $nota 40 ($fondo - 60) 1200 320

    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    Write-Output "  $nombre : $($d.DiagramObjects.Count) objetos, $($d.DiagramLinks.Count) relaciones"
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
