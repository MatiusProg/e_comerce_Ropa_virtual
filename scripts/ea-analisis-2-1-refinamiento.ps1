# =========================================================================
# CAP. 2 - 2.1.2 y 2.1.3: incorporar CU-38 a CU-41, el refinamiento del
# Ciclo 2.
#
# NO REGENERA NADA. Los dos diagramas estan acomodados a mano --- las
# posiciones son irregulares y los marcos de 2.1.3 se ajustaron uno por uno ---
# asi que este script AGREGA los cuatro casos de uso al dibujo que ya existe:
#
#   2.1.2  inserta cada CU en el bloque de SU paquete y empuja hacia abajo lo
#          que queda debajo, que es una columna vertical y se desplaza sin
#          romper nada. Despues recentra la caja del paquete sobre su grupo.
#
#   2.1.3  agranda el marco del paquete y pone el CU en el espacio nuevo. Si
#          el actor que lo inicia no estaba en ese diagrama, lo agrega.
#
# Es idempotente: si los elementos ya existen, no los duplica ni vuelve a
# desplazar el lienzo.
#
# NO EXPORTA IMAGENES.
#
# ---- A QUE PAQUETE VA CADA UNO ----
# Lo manda la columna "Paquete" de la tabla de priorizacion (§1.2 de
# docs/03-captura-requisitos.md), que es lo que va al .docx. El diagrama y el
# documento tienen que decir lo mismo.
#
#   CU-38 Registrar productos del proveedor       -> P2 Organizacion
#   CU-39 Informar disponibilidad y plazo         -> P4 Inventario
#   CU-40 Notificar eventos a los usuarios        -> P6 Reservas Y P7 Ventas
#   CU-41 Recuperar contrasena                    -> P1 Seguridad
#
# CU-40 traza a DOS paquetes y aparece UNA sola vez en el 2.1.2, igual que
# CU-27, que ya traza a P7 y P8.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

function Get-Paquete($padre, $nombre) {
    $padre.Packages.Refresh()
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    throw "No se encontro el paquete '$nombre'"
}

$root  = $ea.Models.GetAt(0)
$pRaiz = Get-Paquete $root 'Violet Boutique'
$pCap1 = Get-Paquete $pRaiz 'CAP. 1 - Captura de Requisitos'
$pMcu  = Get-Paquete $pCap1 'Modelo de Casos de Uso'   # el hogar canonico de los 37

# ---------------- los cuatro casos de uso ----------------
# Se crean en 'Modelo de Casos de Uso', que es donde viven CU-10 a CU-37 y de
# donde los toman el 2.1.2 y el 2.1.3. NO en el paquete del Ciclo 2 del CAP. 1,
# que es otro juego de elementos para otros diagramas.

$nuevos = @(
  @{ k='cu38'; n='CU-38 Registrar productos del proveedor'
     nt='Permite al Proveedor registrar o enviar la informacion de los productos que abastece y asociarlos a una temporada y una coleccion, con alcance limitado a los suyos. Realiza el RF37. Refinamiento del Ciclo 2.'
     actores=@('Proveedor') },
  @{ k='cu39'; n='CU-39 Informar disponibilidad y plazo de abastecimiento'
     nt='Permite al Proveedor informar que productos puede abastecer y en que plazo, alimentando el estado «proximo a ingresar» del inventario consolidado. Realiza el RF38. Refinamiento del Ciclo 2.'
     actores=@('Proveedor') },
  @{ k='cu40'; n='CU-40 Notificar eventos a los usuarios'
     nt='El Sistema avisa a quien corresponda cuando ocurre un hecho que requiere su atencion: una reserva dirigida a su sucursal, una reserva preparada para el cliente, un pedido pagado y una alerta de stock bajo. Es el que REALIZA el RF11: lo que habia antes era consulta, no notificacion. Refinamiento del Ciclo 2.'
     actores=@('Sistema (procesos automaticos)') },
  @{ k='cu41'; n='CU-41 Recuperar contraseña'
     nt='Permite a cualquier usuario recuperar el acceso a su cuenta mediante un enlace de un solo uso enviado a su correo, sin intervencion del Administrador. Realiza el RF39. Refinamiento del Ciclo 2.'
     # Los mismos seis que CU-02: es literalmente «cualquier usuario».
     actores=@('Cliente','Usuario interno','Administrador','Encargado de Sucursal','Cajero','Proveedor') }
)

# Indice de lo que ya existe, por nombre, en todo el modelo.
$porNombre = @{}
function Indexar($pkg) {
    foreach ($e in $pkg.Elements) { $porNombre["$($e.Type)|$($e.Name)"] = $e }
    foreach ($sp in $pkg.Packages) { Indexar $sp }
}
Indexar $pRaiz

$U = @{}
$creados = 0
foreach ($def in $nuevos) {
    $clave = "UseCase|$($def.n)"
    if ($porNombre.ContainsKey($clave)) {
        $U[$def.k] = $porNombre[$clave]
    } else {
        $e = $pMcu.Elements.AddNew($def.n, 'UseCase')
        $e.Notes = $def.nt
        [void]$e.Update(); $pMcu.Elements.Refresh()
        $U[$def.k] = $e; $creados++
    }
}
Write-Output "Casos de uso nuevos: $creados creados, $(4 - $creados) ya estaban"

# ---------------- asociaciones actor - caso de uso ----------------
function New-Asociacion($src, $dst) {
    $src.Connectors.Refresh()
    foreach ($c in $src.Connectors) {
        if ($c.SupplierID -eq $dst.ElementID -and $c.Type -eq 'Association') { return $false }
    }
    $c = $src.Connectors.AddNew('', 'Association')
    $c.SupplierID = $dst.ElementID
    [void]$c.Update(); $src.Connectors.Refresh()
    return $true
}

$nAsoc = 0
foreach ($def in $nuevos) {
    foreach ($nom in $def.actores) {
        $act = $porNombre["Actor|$nom"]
        if (-not $act) { throw "No se encontro el actor '$nom'" }
        if (New-Asociacion $act $U[$def.k]) { $nAsoc++ }
    }
}
Write-Output "Asociaciones actor - caso de uso: $nAsoc nuevas"

# ---------------- trazas paquete -> caso de uso ----------------
# La traza va del PAQUETE al CASO DE USO --- Source = paquete --- y es un
# Abstraction con estereotipo «trace». Cada CU lleva DOS: una desde la copia
# del paquete que usa el 2.1.2 y otra desde la que usa el 2.1.3.
#
# Los once paquetes estan TRIPLICADOS en el modelo (ids 59-69, 81-91 y 92-102):
# quedo asi de una corrida vieja del generador de 2.1 --- Package.Elements no
# devuelve los elementos de tipo Package, asi que el buscar-o-crear no los
# encontraba y los recreaba. No se arregla aca: cada diagrama apunta a su copia
# y arreglarlo ahora significaria rehacer los trece dibujos a mano.
$COPIA_212 = @{ p1=81; p2=82; p3=83; p4=84; p5=85; p6=86; p7=87; p8=88; p9=89; p10=90; p11=91 }
$COPIA_213 = @{ p1=92; p2=93; p3=94; p4=95; p5=96; p6=97; p7=98; p8=99; p9=100; p10=101; p11=102 }

$traza = @(
  @{ cu='cu38'; paqs=@('p2') },
  @{ cu='cu39'; paqs=@('p4') },
  @{ cu='cu40'; paqs=@('p6','p7') },
  @{ cu='cu41'; paqs=@('p1') }
)

function New-Traza($idPaquete, $cu) {
    $paq = $ea.GetElementByID($idPaquete)
    $paq.Connectors.Refresh()
    foreach ($c in $paq.Connectors) {
        if ($c.SupplierID -eq $cu.ElementID -and $c.Type -eq 'Abstraction') { return $false }
    }
    $c = $paq.Connectors.AddNew('', 'Abstraction')
    $c.SupplierID = $cu.ElementID
    $c.Stereotype = 'trace'
    $c.Direction  = 'Source -> Destination'
    [void]$c.Update(); $paq.Connectors.Refresh()
    return $true
}

$nTrazas = 0
foreach ($t in $traza) {
    foreach ($p in $t.paqs) {
        if (New-Traza $COPIA_212[$p] $U[$t.cu]) { $nTrazas++ }
        if (New-Traza $COPIA_213[$p] $U[$t.cu]) { $nTrazas++ }
    }
}
Write-Output "Trazas «trace» paquete -> caso de uso: $nTrazas nuevas"

# =========================================================================
# 2.1.2 --- insertar en la columna y empujar lo de abajo
# =========================================================================

function Get-Diagrama($id) { return $ea.GetDiagramByID($id) }

function Esta-EnDiagrama($dia, $el) {
    $dia.DiagramObjects.Refresh()
    foreach ($o in $dia.DiagramObjects) { if ($o.ElementID -eq $el.ElementID) { return $true } }
    return $false
}

function Poner($dia, $el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l+$ancho);t=$t;b=$($t-$alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
}

# Empuja hacia abajo todo lo que este por debajo del umbral.
function Empujar($dia, $umbral, $cuanto) {
    $dia.DiagramObjects.Refresh()
    foreach ($o in $dia.DiagramObjects) {
        if ($o.Top -le $umbral) {
            $o.Top = $o.Top - $cuanto
            $o.Bottom = $o.Bottom - $cuanto
            [void]$o.Update()
        }
    }
}

$d212 = Get-Diagrama 14
$PASO = 90   # el mismo espaciado que ya tienen los CU dentro de un bloque

# De ABAJO hacia ARRIBA, para que cada desplazamiento no mueva el punto de
# insercion de los que faltan.
$inserciones = @(
  @{ cu='cu40'; umbral=-2400; t=-2400 },   # bloque P6, despues de CU-25
  @{ cu='cu39'; umbral=-1600; t=-1600 },   # bloque P4, despues de CU-16
  @{ cu='cu38'; umbral=-710;  t=-710  },   # bloque P2, despues de CU-07
  @{ cu='cu41'; umbral=-420;  t=-419  }    # bloque P1, despues de CU-04
)

foreach ($ins in $inserciones) {
    if (Esta-EnDiagrama $d212 $U[$ins.cu]) {
        Write-Output "  2.1.2: $($U[$ins.cu].Name) ya estaba, no se toca"
        continue
    }
    Empujar $d212 $ins.umbral $PASO
    Poner $d212 $U[$ins.cu] 420 $ins.t 105 70
    Write-Output "  2.1.2: insertado $($U[$ins.cu].Name)"
}
$d212.DiagramObjects.Refresh(); $d212.DiagramLinks.Refresh()
Write-Output "2.1.2 -> $($d212.DiagramObjects.Count) objetos, $($d212.DiagramLinks.Count) relaciones"

# =========================================================================
# 2.1.3 --- agrandar el marco y poner el CU en el espacio nuevo
# =========================================================================
#
# Aqui el Package SI es un marco contenedor: los actores y los casos de uso se
# dibujan dentro de sus limites. Hay que bajar el borde inferior antes de
# meter nada, o el CU nuevo queda fuera de la caja.

$vistas = @(
  @{ dia=25; paq=92;  cu='cu41'; frameBottom=-680; cuL=159; cuT=-560; actores=@() },
  @{ dia=26; paq=93;  cu='cu38'; frameBottom=-500; cuL=490; cuT=-400; actores=@() },
  @{ dia=28; paq=95;  cu='cu39'; frameBottom=-540; cuL=463; cuT=-420;
     actores=@(@{ n='Proveedor'; l=620; t=-109 }) },
  @{ dia=30; paq=97;  cu='cu40'; frameBottom=-560; cuL=324; cuT=-420; actores=@() },
  @{ dia=31; paq=98;  cu='cu40'; frameBottom=-560; cuL=465; cuT=-420;
     actores=@(@{ n='Sistema (procesos automaticos)'; l=180; t=-113 }) }
)

foreach ($v in $vistas) {
    $d = Get-Diagrama $v.dia
    if (Esta-EnDiagrama $d $U[$v.cu]) {
        Write-Output "  2.1.3 ($($d.Name)): $($U[$v.cu].Name) ya estaba, no se toca"
        continue
    }

    # 1. bajar el borde inferior del marco
    $d.DiagramObjects.Refresh()
    foreach ($o in $d.DiagramObjects) {
        if ($o.ElementID -eq $v.paq) { $o.Bottom = $v.frameBottom; [void]$o.Update() }
    }

    # 2. el actor iniciador, si no estaba en esta vista
    foreach ($a in $v.actores) {
        $act = $porNombre["Actor|$($a.n)"]
        if (-not (Esta-EnDiagrama $d $act)) {
            Poner $d $act $a.l $a.t 45 90
            Write-Output "    + actor $($a.n)"
        }
    }

    # 3. el caso de uso
    Poner $d $U[$v.cu] $v.cuL $v.cuT 105 70
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    Write-Output ("  2.1.3 ({0}): + {1}  [{2} objetos]" -f $d.Name, $U[$v.cu].Name, $d.DiagramObjects.Count)
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
