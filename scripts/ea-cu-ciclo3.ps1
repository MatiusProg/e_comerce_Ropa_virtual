param(
    # Borra el paquete 'Ciclo 3' del CAP. 1 y lo vuelve a generar.
    [switch]$Rehacer
)

# =========================================================================
# CAP. 1 - 1.5 Modelo de Casos de Uso Estructurado y 1.3.2 Disenar CU,
# un diagrama por caso de uso. CICLO 3: los VEINTE casos de uso del comercio,
# la experiencia y la inteligencia (CU-12, CU-20, CU-21, CU-26 a CU-42).
#
# DE DONDE SALEN ESTOS DATOS
# --------------------------
# De la tabla 1.3.1 del Ciclo 3, que es donde estan escritos el actor
# iniciador, el paquete y las relaciones de cada caso de uso. Este generador
# no decide nada: dibuja lo que esa tabla dice. Si los dos dejan de coincidir,
# manda la tabla.
#
# ADITIVO, como el del Ciclo 2. Abre el .eapx existente y solo le agrega el
# paquete 'Ciclo 3' con sus veintiun diagramas. Si el paquete ya esta, no lo
# toca; para rehacerlo, -Rehacer.
#
# POR QUE EL PAQUETE 'Ciclo 3' ES AUTOCONTENIDO
# ---------------------------------------------
# Los actores y 'Autenticar usuario' se crean de nuevo aca en vez de reutilizar
# los de los paquetes 'Ciclo 1' y 'Ciclo 2'. Son las reglas 2 y 3 del manual:
#
#   - Regla 2: si el diagrama y sus elementos viven en paquetes distintos, EA
#     rotula cada elemento con "(from Ciclo 1)" debajo del nombre y ensucia los
#     veinte dibujos.
#   - Regla 3: EA dibuja TODA relacion que exista entre los elementos que estan
#     en el lienzo. Compartiendo el actor Administrador, el diagrama de CU-12
#     dibujaria tambien sus lineas a CU-03, CU-05, CU-36, CU-37 y CU-42 ---
#     relaciones ajenas que habria que ocultar una por una en cada diagrama.
#
# Cada paquete de ciclo es una vista del modelo en un momento del proyecto.
#
# LO QUE ESTE CICLO TRAE Y LOS ANTERIORES NO
# -------------------------------------------
# Tres actores que hasta ahora no iniciaban nada:
#
#   - el CAJERO, que estrena CU-30, CU-31 y CU-32;
#   - el PROVEEDOR, que figuraba en el enunciado con tres responsabilidades y
#     no iniciaba ningun caso de uso hasta CU-38 y CU-39;
#   - la PASARELA DE PAGO, actor EXTERNO y el unico que inicia un caso de uso
#     sin ser una persona (CU-28).
#
# Y dos casos de uso SIN CONSTRUIR --- CU-34 y CU-40 ---, que se dibujan igual:
# el modelo del ciclo es el alcance acordado, no el codigo escrito. Quien mire
# el diagrama y despues el sistema tiene que poder ver la diferencia en la
# tabla, no descubrirla porque el diagrama los escondio.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
$dirPng = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\casos-de-uso\'

if (-not (Test-Path $modelo)) {
    throw "No existe $modelo. Este generador es aditivo: el modelo tiene que existir."
}

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

# ---------------------------------------------------------------- helpers --
# Los mismos que el generador del Ciclo 2. Se repiten en vez de importarse
# porque cada generador se corre solo y un archivo compartido de helpers
# obligaria a dot-sourcing relativo, que rompe segun desde donde se invoque.

function Get-Paquete($padre, $nombre) {
    $padre.Packages.Refresh()
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    return $null
}

function New-Paquete($padre, $nombre) {
    $p = $padre.Packages.AddNew($nombre, 'Package'); [void]$p.Update(); $padre.Packages.Refresh(); return $p
}

function New-Elemento($pkg, $nombre, $tipo, $notas) {
    $e = $pkg.Elements.AddNew($nombre, $tipo)
    if ($notas) { $e.Notes = $notas }
    [void]$e.Update(); return $e
}

function Add-AlDiagrama($dia, $el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l+$ancho);t=$t;b=$($t-$alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
}

# Regla 5: borrar un diagrama NO borra sus conectores. Se deduplica siempre,
# o una segunda corrida deja el modelo con las relaciones por duplicado.
function New-Conector($src, $dst, $tipo, $estereotipo) {
    $src.Connectors.Refresh()
    foreach ($c in $src.Connectors) {
        # `[string]` en los dos lados a proposito: para una Association el
        # estereotipo del conector es cadena vacia y el parametro llega como
        # $null, y en PowerShell `'' -eq $null` es FALSO. Sin el casteo, la
        # deduplicacion no reconoce el conector que ya existe y lo vuelve a
        # crear en cada corrida: asi aparecieron 30 duplicados el 13/09.
        if ($c.SupplierID -eq $dst.ElementID -and $c.Type -eq $tipo -and
            [string]$c.Stereotype -eq [string]$estereotipo) { return }
    }
    $c = $src.Connectors.AddNew('', $tipo)
    $c.SupplierID = $dst.ElementID
    if ($estereotipo) { $c.Stereotype = $estereotipo }
    [void]$c.Update(); $src.Connectors.Refresh()
}

function New-DiagramaDeCasoDeUso($paquete, $nombre, $puestos, $ocultar) {
    $d = $paquete.Diagrams.AddNew($nombre, 'UseCase')
    [void]$d.Update(); $paquete.Diagrams.Refresh()
    foreach ($x in $puestos) { Add-AlDiagrama $d $x.el $x.l $x.t $x.w $x.h }
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()

    # Regla 3: oculta las relaciones que existen entre elementos presentes en
    # el lienzo pero que no son objeto de ESTE diagrama.
    if ($ocultar) {
        foreach ($lnk in $d.DiagramLinks) {
            $con = $ea.GetConnectorByID($lnk.ConnectorID)
            foreach ($par in $ocultar) {
                if ($con.ClientID -eq $par[0].ElementID -and $con.SupplierID -eq $par[1].ElementID) {
                    $lnk.IsHidden = $true; [void]$lnk.Update()
                }
            }
        }
        $d.DiagramLinks.Refresh()
    }
    return $d
}

# ------------------------------------------------------------ ubicacion ----

$root  = $ea.Models.GetAt(0)
$pRaiz = Get-Paquete $root 'Violet Boutique'
if (-not $pRaiz) { throw "No se encontro el paquete 'Violet Boutique' en el modelo." }
$pCap1 = Get-Paquete $pRaiz 'CAP. 1 - Captura de Requisitos'
if (-not $pCap1) { throw "No se encontro 'CAP. 1 - Captura de Requisitos'." }

$pCiclo3 = Get-Paquete $pCap1 'Ciclo 3'
if ($pCiclo3 -and -not $Rehacer) {
    Write-Output "El paquete 'Ciclo 3' ya existe y este generador es aditivo: no se toca."
    Write-Output "Para rehacerlo desde cero, volve a correrlo con -Rehacer."
    $ea.CloseFile(); $ea.Exit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
    return
}
if ($pCiclo3 -and $Rehacer) {
    for ($i = 0; $i -lt $pCap1.Packages.Count; $i++) {
        if ($pCap1.Packages.GetAt($i).Name -eq 'Ciclo 3') { $pCap1.Packages.DeleteAt($i, $false); break }
    }
    $pCap1.Packages.Refresh()
    Write-Output "Paquete 'Ciclo 3' borrado (-Rehacer)."
}
$pCiclo3 = New-Paquete $pCap1 'Ciclo 3'

# =========================================================================
# 1.5  Modelo de Casos de Uso Estructurado - CICLO #3
# =========================================================================

$dia = $pCiclo3.Diagrams.AddNew('1.5 Modelo de Casos de Uso Estructurado - CICLO #3', 'UseCase')
[void]$dia.Update(); $pCiclo3.Diagrams.Refresh()

# ---------------- actores ----------------
# Siete: los cinco roles humanos que inician algo en este ciclo, el Sistema
# para los procesos automaticos, y los DOS EXTERNOS --- la Pasarela de Pago y
# el Servicio de IA ---, que no son personas y no tienen cuenta.
$A = @{}
$defA = @(
  @{k='cliente';   n='Cliente';                        t=-60;   h=80;  nt='Compra, reserva y se prueba prendas. En este ciclo estrena el carrito, el pedido en linea, el historial, los favoritos, el vestidor virtual y las recomendaciones.'},
  @{k='admin';     n='Administrador';                  t=-260;  h=80;  nt='Acceso completo. En este ciclo define las promociones, mira el tablero, genera los reportes --- tambien dictandolos --- y consulta la bitacora.'},
  @{k='encargado'; n='Encargado de Sucursal';          t=-460;  h=80;  nt='Responsable operativo de una sucursal. Atiende el mostrador en las sucursales chicas, asi que comparte con el Cajero la caja, la venta presencial y la devolucion.'},
  @{k='cajero';    n='Cajero';                         t=-660;  h=80;  nt='SE ESTRENA EN ESTE CICLO. Hasta el Ciclo 2 figuraba entre los actores del enunciado sin iniciar ningun caso de uso. Abre y cierra su caja, cobra en el mostrador y registra devoluciones.'},
  @{k='proveedor'; n='Proveedor';                      t=-860;  h=80;  nt='SE ESTRENA EN ESTE CICLO. Figuraba en el enunciado con tres responsabilidades y no iniciaba ningun caso de uso. Registra sus productos y anuncia que puede abastecer y en que plazo.'},
  @{k='sistema';   n='Sistema (procesos automáticos)'; t=-1060; h=80;  nt='A6. Procesos que el sistema ejecuta sin intervencion humana. En este ciclo, notificar los hechos que requieren atencion (CU-40) y escribir cada asiento de la bitacora (CU-42).'},
  @{k='pasarela';  n='Pasarela de Pago';               t=-1260; h=80;  nt='ACTOR EXTERNO. Es el unico que inicia un caso de uso sin ser una persona: manda la notificacion firmada que confirma el pago (CU-28). No tiene cuenta en el sistema --- la firma del webhook reemplaza a la sesion.'},
  @{k='ia';        n='Servicio de IA';                 t=-1460; h=80;  nt='ACTOR EXTERNO. Ordena las recomendaciones (CU-33), interpreta el dictado de un reporte (CU-35), responde al asistente (CU-34) y genera el probado asistido del vestidor (CU-21). Ninguno de los cuatro lo necesita para no romperse: todos degradan.'}
)
foreach ($def in $defA) {
    $e = New-Elemento $pCiclo3 $def.n 'Actor' $def.nt
    Add-AlDiagrama $dia $e 40 $def.t 170 $def.h
    $A[$def.k] = $e
}

# ---------------- casos de uso ----------------
# En una columna, agrupados por a quien sirven: primero los del Cliente,
# despues el mostrador, despues lo del Administrador, y al final lo del
# Proveedor y los procesos del sistema.
$U = @{}
$defU = @(
  @{k='cu26'; n='CU-26 Gestionar carrito de compras';          l=380; t=-40;   h=85;  nt='Permite al Cliente agregar variantes al carrito, cambiar cantidades y ver el total con las promociones aplicadas. NO aparta inventario: un carrito es una intencion.'},
  @{k='cu27'; n='CU-27 Realizar pedido y pagar en línea';      l=380; t=-150;  h=85;  nt='Permite al Cliente confirmar el carrito, elegir retiro o envio, generar el pedido e iniciar el pago. El pedido NO queda pagado aca: eso lo hace CU-28.'},
  @{k='cu29'; n='CU-29 Consultar historial de compras';        l=380; t=-260;  h=85;  nt='Permite al Cliente ver sus pedidos anteriores, su estado y descargar el comprobante. La primera descarga EMITE el comprobante si no existia.'},
  @{k='cu20'; n='CU-20 Gestionar favoritos';                   l=380; t=-370;  h=85;  nt='Permite al Cliente marcar prendas como favoritas y verlas juntas. No aparta inventario ni compromete una compra.'},
  @{k='cu21'; n='CU-21 Utilizar vestidor virtual (RA)';        l=380; t=-480;  h=85;  nt='Permite al Cliente verse una prenda encima con la camara del telefono. La superposicion directa no depende de ningun tercero; el probado asistido por IA es opcional.'},
  @{k='cu33'; n='CU-33 Recibir recomendaciones de prendas';    l=380; t=-590;  h=85;  nt='El sistema sugiere prendas segun el historial, la talla habitual, la temporada y la disponibilidad REAL. Sin el Servicio de IA recomienda por popularidad.'},
  @{k='cu34'; n='CU-34 Conversar con el asistente virtual';    l=380; t=-700;  h=85;  nt='SIN EMPEZAR. Permitiria al Cliente preguntar en lenguaje natural sobre el catalogo, sus pedidos y sus reservas, respondiendo con los datos reales del sistema.'},
  @{k='cu30'; n='CU-30 Abrir y cerrar caja';                   l=380; t=-830;  h=85;  nt='Permite al Cajero abrir su turno con un monto inicial y cerrarlo con el arqueo. Guarda LOS DOS numeros --- lo esperado y lo contado ---, porque un descuadre sin los dos no se puede auditar.'},
  @{k='cu31'; n='CU-31 Registrar venta presencial';            l=380; t=-940;  h=85;  nt='Permite al Cajero cobrar en el mostrador buscando las prendas o cargando una reserva ya atendida. La venta nace PAGADA: no pasa por la pasarela.'},
  @{k='cu32'; n='CU-32 Registrar devolución';                  l=380; t=-1050; h=85;  nt='Permite al Cajero recibir una prenda de vuelta y reingresarla al inventario. La plata sale del cajon SOLO si la venta se habia cobrado en efectivo.'},
  @{k='cu12'; n='CU-12 Gestionar promociones';                 l=380; t=-1180; h=85;  nt='Permite al Administrador definir descuentos con vigencia sobre un producto, una categoria o una temporada. Cuando dos alcanzan la misma prenda gana la mayor: nunca se suman.'},
  @{k='cu36'; n='CU-36 Consultar tablero de indicadores';      l=380; t=-1290; h=85;  nt='Permite al Administrador ver los KPIs del negocio en tiempo real: ventas del dia y del mes, ticket promedio, reservas, conversion, mas vendidos y stock critico.'},
  @{k='cu37'; n='CU-37 Generar reportes de gestión';           l=380; t=-1400; h=85;  nt='Permite generar y descargar en PDF y Excel los seis reportes de gestion. El Encargado los obtiene acotados a su sucursal.'},
  @{k='cu35'; n='CU-35 Generar reporte por comando de voz';    l=380; t=-1510; h=85;  nt='Permite al Administrador pedir un reporte dictandolo. El sistema interpreta el pedido, MUESTRA QUE ENTENDIO antes de generar, y delega la generacion en CU-37.'},
  @{k='cu42'; n='CU-42 Consultar la bitácora del sistema';     l=380; t=-1620; h=85;  nt='Permite al Administrador consultar el registro inmutable de toda operacion que modifico el estado del sistema, y de los intentos de acceso fallidos.'},
  @{k='cu38'; n='CU-38 Registrar productos del proveedor';     l=380; t=-1750; h=85;  nt='Permite al Proveedor registrar la informacion de los productos que abastece, con alcance limitado a los suyos. No se publican solos: el Administrador los revisa.'},
  @{k='cu39'; n='CU-39 Informar disponibilidad y plazo';       l=380; t=-1860; h=85;  nt='Permite al Proveedor anunciar que puede abastecer y en que plazo, alimentando el estado "proximo a ingresar". NO suma existencia: lo anunciado no es lo que hay.'},
  @{k='cu28'; n='CU-28 Confirmar pago del pedido';             l=380; t=-1990; h=85;  nt='El sistema recibe la notificacion firmada de la pasarela, la valida, marca el pedido como pagado y descuenta el inventario. Es el UNICO caso de uso que no inicia una persona.'},
  @{k='cu40'; n='CU-40 Notificar eventos a los usuarios';      l=380; t=-2100; h=85;  nt='SIN EMPEZAR. Avisaria a quien corresponda cuando ocurre un hecho que requiere su atencion. Es la diferencia entre notificar y consultar, que es lo que el RF11 exige de verdad.'},
  @{k='cu41'; n='CU-41 Recuperar contraseña';                  l=380; t=-2210; h=85;  nt='Permite a cualquier usuario recuperar el acceso con un enlace de un solo uso enviado a su correo. Se inicia SIN sesion, y esa es su razon de ser.'},
  @{k='auth'; n='Autenticar usuario';                          l=820; t=-1100; h=85;  nt='Caso de uso de inclusion, ya presente en el Ciclo 1. Verifica el token y el rol antes del primer paso de toda operacion que exige sesion. No es uno de los casos de uso numerados: no produce por si mismo un resultado de valor para un actor.'}
)
foreach ($def in $defU) {
    $e = New-Elemento $pCiclo3 $def.n 'UseCase' $def.nt
    Add-AlDiagrama $dia $e $def.l $def.t 300 $def.h
    $U[$def.k] = $e
}

if ($A.Count -ne 8 -or $U.Count -ne 21) { throw "Faltan elementos: actores=$($A.Count) casos=$($U.Count)" }

# ---------------- puntos de extension ----------------
$U['cu31'].ExtensionPoints = 'Al elegir cobrar una reserva atendida'; [void]$U['cu31'].Update()
$U['cu21'].ExtensionPoints = 'Al pedir el probado asistido';          [void]$U['cu21'].Update()

# ---------------- asociaciones actor - caso de uso ----------------
foreach ($p in @(
  # El Cliente: su compra, su vestidor y lo que el sistema le sugiere.
  @('cliente','cu26'), @('cliente','cu27'), @('cliente','cu29'),
  @('cliente','cu20'), @('cliente','cu21'), @('cliente','cu33'), @('cliente','cu34'),
  # El Cajero: el mostrador entero. Se estrena en este ciclo.
  @('cajero','cu30'), @('cajero','cu31'), @('cajero','cu32'),
  # El Encargado atiende el mostrador en las sucursales chicas, y ademas
  # consulta el tablero y los reportes acotados a su local.
  @('encargado','cu30'), @('encargado','cu31'), @('encargado','cu32'),
  @('encargado','cu36'), @('encargado','cu37'),
  # El Administrador: las promociones, lo que mira y lo que audita.
  @('admin','cu12'), @('admin','cu36'), @('admin','cu37'),
  @('admin','cu35'), @('admin','cu42'),
  # El Proveedor. Se estrena en este ciclo.
  @('proveedor','cu38'), @('proveedor','cu39'),
  # A6: los procesos sin persona detras.
  @('sistema','cu40'), @('sistema','cu42'),
  # Los dos externos.
  @('pasarela','cu28'), @('pasarela','cu27'),
  @('ia','cu33'), @('ia','cu34'), @('ia','cu35'), @('ia','cu21'),
  # CU-41 lo inicia cualquiera; se asocia al Cliente, que es el caso masivo.
  @('cliente','cu41'))) {
    New-Conector $A[$p[0]] $U[$p[1]] 'Association' $null
}

# ---------------- include ----------------
# Toda operacion con sesion incluye la autenticacion. Quedan afuera TRES, y
# cada una por un motivo distinto que el diagrama tiene que dejar ver:
#
#   CU-28  la inicia la pasarela, no una persona: lo que la autoriza es la
#          FIRMA del webhook, no un token. Ese es el punto de la decision D5.
#   CU-40  no hay nadie del otro lado: es el sistema avisando.
#   CU-41  se inicia SIN sesion --- si exigiera uno, no serviria para lo unico
#          que tiene que servir: entrar cuando no se puede entrar.
foreach ($k in @('cu12','cu20','cu21','cu26','cu27','cu29','cu30','cu31','cu32',
                 'cu33','cu34','cu35','cu36','cu37','cu38','cu39','cu42')) {
    New-Conector $U[$k] $U['auth'] 'Dependency' 'include'
}

# CU-35 incluye a CU-37: el reporte pedido por voz ES un reporte de gestion.
# CU-35 aporta la interpretacion del dictado y delega la generacion. Sin esta
# flecha, el diagrama haria pensar que hay dos generadores de reportes.
New-Conector $U['cu35'] $U['cu37'] 'Dependency' 'include'

# CU-27 incluye a CU-26: no hay pedido sin carrito. El flujo arranca leyendo
# lo que el carrito tiene, y si esta vacio el caso de uso no ocurre.
New-Conector $U['cu27'] $U['cu26'] 'Dependency' 'include'

# ---------------- extend ----------------
# CU-31 extiende con la reserva atendida: la venta presencial se completa sin
# cargar ninguna reserva, y cargarla es un camino alternativo. Es el puente de
# la decision D2 --- la reserva atendida y la venta presencial son el mismo
# acto comercial visto desde dos lados.
New-Conector $U['cu31'] $U['cu30'] 'Dependency' 'extend'

# CU-32 extiende CU-31: devolver es un hecho posterior y opcional. La venta
# esta completa sin el. Y la devolucion cuelga del turno, igual que la venta.
New-Conector $U['cu32'] $U['cu30'] 'Dependency' 'extend'

# CU-29 extiende CU-27: el pedido esta completo sin que nadie mire el historial
# despues. Mirarlo es lo que el cliente hace al otro dia.
New-Conector $U['cu29'] $U['cu27'] 'Dependency' 'extend'

# CU-28 extiende CU-27 y NO al reves: el pedido queda creado y a la espera aunque
# el pago nunca llegue --- de hecho ese es el caso que CU-25 barre. La flecha al
# reves diria que un pedido sin pagar no existe, y existe: existe PENDIENTE_PAGO.
New-Conector $U['cu28'] $U['cu27'] 'Dependency' 'extend'

$pCiclo3.Elements.Refresh(); $dia.DiagramObjects.Refresh(); $dia.DiagramLinks.Refresh()
Write-Output "1.5  -> elementos: $($pCiclo3.Elements.Count) | objetos: $($dia.DiagramObjects.Count) | conectores: $($dia.DiagramLinks.Count)"

# =========================================================================
# 1.3.2 Disenar Casos de Uso: un diagrama por caso de uso.
# En el MISMO paquete que los elementos (regla 2).
#
# El tercer parametro de New-DiagramaDeCasoDeUso son las relaciones a OCULTAR
# (regla 3): las que EA dibuja porque los dos extremos estan en el lienzo, pero
# que no son objeto de ESE diagrama.
# =========================================================================

# --- CU-12 ---
$dCu12 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-12 Gestionar promociones' @(
    @{ el=$A['admin']; l=40;  t=-80; w=170; h=80 },
    @{ el=$U['cu12'];  l=360; t=-70; w=300; h=85 },
    @{ el=$U['auth'];  l=800; t=-70; w=280; h=85 }
) $null

# --- CU-20 ---
$dCu20 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-20 Gestionar favoritos' @(
    @{ el=$A['cliente']; l=40;  t=-80; w=170; h=80 },
    @{ el=$U['cu20'];    l=360; t=-70; w=300; h=85 },
    @{ el=$U['auth'];    l=800; t=-70; w=280; h=85 }
) $null

# --- CU-21 --- el Servicio de IA entra solo por el probado asistido, que es
# el punto de extension. Por eso esta en el lienzo pero la prenda se ve igual
# sin el.
$dCu21 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-21 Utilizar vestidor virtual (RA)' @(
    @{ el=$A['cliente']; l=40;  t=-60;  w=170; h=80 },
    @{ el=$A['ia'];      l=40;  t=-220; w=170; h=80 },
    @{ el=$U['cu21'];    l=360; t=-110; w=300; h=85 },
    @{ el=$U['auth'];    l=800; t=-110; w=280; h=85 }
) $null

# --- CU-26 ---
$dCu26 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-26 Gestionar carrito de compras' @(
    @{ el=$A['cliente']; l=40;  t=-80; w=170; h=80 },
    @{ el=$U['cu26'];    l=360; t=-70; w=300; h=85 },
    @{ el=$U['auth'];    l=800; t=-70; w=280; h=85 }
) $null

# --- CU-27 --- lleva el carrito (include) y la pasarela, que es quien cobra.
# Se oculta la flecha de CU-28 a CU-27: CU-28 tiene su propio diagrama y aca
# solo enturbia --- el pedido se crea aunque el pago no llegue nunca.
$dCu27 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-27 Realizar pedido y pagar en línea' @(
    @{ el=$A['cliente'];  l=40;  t=-60;  w=170; h=80 },
    @{ el=$A['pasarela']; l=40;  t=-220; w=170; h=80 },
    @{ el=$U['cu27'];     l=360; t=-110; w=300; h=85 },
    @{ el=$U['cu26'];     l=360; t=-260; w=300; h=85 },
    @{ el=$U['auth'];     l=800; t=-110; w=280; h=85 }
) @(
    # CU-28 tiene su propio diagrama, y aca solo enturbia: el pedido se crea
    # aunque el pago no llegue nunca.
    @($U['cu28'], $U['cu27']),
    # Lo que es de CU-26 y no de este caso de uso.
    @($A['cliente'], $U['cu26']), @($U['cu26'], $U['auth'])
)

# --- CU-28 --- SIN 'Autenticar usuario' a proposito: lo que autoriza es la
# firma del webhook. Dibujar el include diria que la pasarela inicia sesion,
# que es exactamente lo que no pasa.
$dCu28 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-28 Confirmar pago del pedido' @(
    @{ el=$A['pasarela']; l=40;  t=-80;  w=170; h=80 },
    @{ el=$U['cu28'];     l=360; t=-70;  w=300; h=85 },
    @{ el=$U['cu27'];     l=800; t=-70;  w=300; h=85 }
) @( ,@($A['pasarela'], $U['cu27']) )

# --- CU-29 ---
$dCu29 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-29 Consultar historial de compras' @(
    @{ el=$A['cliente']; l=40;  t=-80; w=170; h=80 },
    @{ el=$U['cu29'];    l=360; t=-70; w=300; h=85 },
    @{ el=$U['auth'];    l=800; t=-70; w=280; h=85 }
) $null

# --- CU-30 --- dos iniciadores: el Cajero y el Encargado, que atiende el
# mostrador en las sucursales chicas. Se ocultan las extensiones de CU-31 y
# CU-32, que tienen su propio diagrama.
$dCu30 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-30 Abrir y cerrar caja' @(
    @{ el=$A['cajero'];    l=40;  t=-60;  w=170; h=80 },
    @{ el=$A['encargado']; l=40;  t=-220; w=170; h=80 },
    @{ el=$U['cu30'];      l=360; t=-110; w=300; h=85 },
    @{ el=$U['auth'];      l=800; t=-110; w=280; h=85 }
) $null

# --- CU-31 --- CU-30 esta en el lienzo porque sin turno abierto no se cobra:
# es la puerta del caso de uso.
$dCu31 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-31 Registrar venta presencial' @(
    @{ el=$A['cajero'];    l=40;  t=-60;  w=170; h=80 },
    @{ el=$A['encargado']; l=40;  t=-220; w=170; h=80 },
    @{ el=$U['cu31'];      l=360; t=-110; w=300; h=85 },
    @{ el=$U['cu30'];      l=360; t=-260; w=300; h=85 },
    @{ el=$U['auth'];      l=800; t=-110; w=280; h=85 }
) @(
    @($U['cu32'], $U['cu30']),
    # CU-30 esta en el lienzo para mostrar que es la PUERTA de este caso de
    # uso. Sus propias lineas --- quien la abre y que incluye --- son de su
    # diagrama, no de este.
    @($A['cajero'], $U['cu30']), @($A['encargado'], $U['cu30']),
    @($U['cu30'], $U['auth'])
)

# --- CU-32 ---
$dCu32 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-32 Registrar devolución' @(
    @{ el=$A['cajero'];    l=40;  t=-60;  w=170; h=80 },
    @{ el=$A['encargado']; l=40;  t=-220; w=170; h=80 },
    @{ el=$U['cu32'];      l=360; t=-110; w=300; h=85 },
    @{ el=$U['cu30'];      l=360; t=-260; w=300; h=85 },
    @{ el=$U['auth'];      l=800; t=-110; w=280; h=85 }
) @(
    @($U['cu31'], $U['cu30']),
    @($A['cajero'], $U['cu30']), @($A['encargado'], $U['cu30']),
    @($U['cu30'], $U['auth'])
)

# --- CU-33 ---
$dCu33 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-33 Recibir recomendaciones de prendas' @(
    @{ el=$A['cliente']; l=40;  t=-60;  w=170; h=80 },
    @{ el=$A['ia'];      l=40;  t=-220; w=170; h=80 },
    @{ el=$U['cu33'];    l=360; t=-110; w=300; h=85 },
    @{ el=$U['auth'];    l=800; t=-110; w=280; h=85 }
) $null

# --- CU-34 --- sin construir. Se dibuja igual: el modelo del ciclo es el
# alcance acordado, no el codigo escrito.
$dCu34 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-34 Conversar con el asistente virtual' @(
    @{ el=$A['cliente']; l=40;  t=-60;  w=170; h=80 },
    @{ el=$A['ia'];      l=40;  t=-220; w=170; h=80 },
    @{ el=$U['cu34'];    l=360; t=-110; w=300; h=85 },
    @{ el=$U['auth'];    l=800; t=-110; w=280; h=85 }
) $null

# --- CU-35 --- incluye a CU-37: el reporte dictado ES un reporte de gestion.
$dCu35 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-35 Generar reporte por comando de voz' @(
    @{ el=$A['admin']; l=40;  t=-60;  w=170; h=80 },
    @{ el=$A['ia'];    l=40;  t=-220; w=170; h=80 },
    @{ el=$U['cu35'];  l=360; t=-110; w=300; h=85 },
    @{ el=$U['cu37'];  l=360; t=-260; w=300; h=85 },
    @{ el=$U['auth'];  l=800; t=-110; w=280; h=85 }
) @(
    # CU-37 esta para mostrar que el reporte dictado ES un reporte de gestion.
    # Quien mas lo genera y que incluye son lineas de SU diagrama.
    @($A['admin'], $U['cu37']), @($A['encargado'], $U['cu37']),
    @($U['cu37'], $U['auth'])
)

# --- CU-36 ---
$dCu36 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-36 Consultar tablero de indicadores' @(
    @{ el=$A['admin'];     l=40;  t=-60;  w=170; h=80 },
    @{ el=$A['encargado']; l=40;  t=-220; w=170; h=80 },
    @{ el=$U['cu36'];      l=360; t=-110; w=300; h=85 },
    @{ el=$U['auth'];      l=800; t=-110; w=280; h=85 }
) $null

# --- CU-37 --- se oculta el include de CU-35, que tiene su propio diagrama.
$dCu37 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-37 Generar reportes de gestión' @(
    @{ el=$A['admin'];     l=40;  t=-60;  w=170; h=80 },
    @{ el=$A['encargado']; l=40;  t=-220; w=170; h=80 },
    @{ el=$U['cu37'];      l=360; t=-110; w=300; h=85 },
    @{ el=$U['auth'];      l=800; t=-110; w=280; h=85 }
) $null

# --- CU-38 ---
$dCu38 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-38 Registrar productos del proveedor' @(
    @{ el=$A['proveedor']; l=40;  t=-80; w=170; h=80 },
    @{ el=$U['cu38'];      l=360; t=-70; w=300; h=85 },
    @{ el=$U['auth'];      l=800; t=-70; w=280; h=85 }
) $null

# --- CU-39 ---
$dCu39 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-39 Informar disponibilidad y plazo' @(
    @{ el=$A['proveedor']; l=40;  t=-80; w=170; h=80 },
    @{ el=$U['cu39'];      l=360; t=-70; w=300; h=85 },
    @{ el=$U['auth'];      l=800; t=-70; w=280; h=85 }
) $null

# --- CU-40 --- sin construir, y SIN 'Autenticar usuario': no hay nadie del
# otro lado. Es el sistema avisando.
$dCu40 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-40 Notificar eventos a los usuarios' @(
    @{ el=$A['sistema']; l=40;  t=-80; w=170; h=80 },
    @{ el=$U['cu40'];    l=360; t=-70; w=300; h=85 }
) $null

# --- CU-41 --- SIN 'Autenticar usuario' a proposito: se inicia sin sesion, y
# esa es su razon de ser. Exigir un token aca lo volveria inutil justo para lo
# unico que tiene que servir.
$dCu41 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-41 Recuperar contraseña' @(
    @{ el=$A['cliente']; l=40;  t=-80; w=170; h=80 },
    @{ el=$U['cu41'];    l=360; t=-70; w=300; h=85 }
) $null

# --- CU-42 --- dos actores con papeles distintos: el Administrador consulta y
# el Sistema escribe cada asiento.
$dCu42 = New-DiagramaDeCasoDeUso $pCiclo3 'CU-42 Consultar la bitácora del sistema' @(
    @{ el=$A['admin'];   l=40;  t=-60;  w=170; h=80 },
    @{ el=$A['sistema']; l=40;  t=-220; w=170; h=80 },
    @{ el=$U['cu42'];    l=360; t=-110; w=300; h=85 },
    @{ el=$U['auth'];    l=800; t=-110; w=280; h=85 }
) $null

# --- exportacion -------------------------------------------------------------
$prj = $ea.GetProjectInterface()

$salidas = @(
    @{ d=$dia;   f='1.5-modelo-estructurado-ciclo-3.png';                      n='1.5  ' },
    @{ d=$dCu12; f='1.3.2-cu-12-gestionar-promociones.png';                    n='CU-12' },
    @{ d=$dCu20; f='1.3.2-cu-20-gestionar-favoritos.png';                      n='CU-20' },
    @{ d=$dCu21; f='1.3.2-cu-21-utilizar-vestidor-virtual.png';                n='CU-21' },
    @{ d=$dCu26; f='1.3.2-cu-26-gestionar-carrito-de-compras.png';             n='CU-26' },
    @{ d=$dCu27; f='1.3.2-cu-27-realizar-pedido-y-pagar.png';                  n='CU-27' },
    @{ d=$dCu28; f='1.3.2-cu-28-confirmar-pago-del-pedido.png';                n='CU-28' },
    @{ d=$dCu29; f='1.3.2-cu-29-consultar-historial-de-compras.png';           n='CU-29' },
    @{ d=$dCu30; f='1.3.2-cu-30-abrir-y-cerrar-caja.png';                      n='CU-30' },
    @{ d=$dCu31; f='1.3.2-cu-31-registrar-venta-presencial.png';               n='CU-31' },
    @{ d=$dCu32; f='1.3.2-cu-32-registrar-devolucion.png';                     n='CU-32' },
    @{ d=$dCu33; f='1.3.2-cu-33-recibir-recomendaciones.png';                  n='CU-33' },
    @{ d=$dCu34; f='1.3.2-cu-34-conversar-con-el-asistente.png';               n='CU-34' },
    @{ d=$dCu35; f='1.3.2-cu-35-generar-reporte-por-voz.png';                  n='CU-35' },
    @{ d=$dCu36; f='1.3.2-cu-36-consultar-tablero-de-indicadores.png';         n='CU-36' },
    @{ d=$dCu37; f='1.3.2-cu-37-generar-reportes-de-gestion.png';              n='CU-37' },
    @{ d=$dCu38; f='1.3.2-cu-38-registrar-productos-del-proveedor.png';        n='CU-38' },
    @{ d=$dCu39; f='1.3.2-cu-39-informar-disponibilidad-y-plazo.png';          n='CU-39' },
    @{ d=$dCu40; f='1.3.2-cu-40-notificar-eventos.png';                        n='CU-40' },
    @{ d=$dCu41; f='1.3.2-cu-41-recuperar-contrasena.png';                     n='CU-41' },
    @{ d=$dCu42; f='1.3.2-cu-42-consultar-bitacora.png';                       n='CU-42' }
)
foreach ($s in $salidas) {
    # `@(...)` a proposito: sin el, un `Where-Object` que devuelve UN solo
    # elemento no devuelve una coleccion, y `.Count` da vacio en vez de 1. Los
    # diagramas de CU-40 y CU-41 tienen una sola relacion y el informe decia
    # blanco --- que se lee como cero y hace dudar de un diagrama correcto.
    $visibles = @($s.d.DiagramLinks | Where-Object { -not $_.IsHidden }).Count
    $exp = $prj.PutDiagramImageToFile($s.d.DiagramGUID, $dirPng + $s.f, 1)
    Write-Output ("{0} -> objetos: {1,2} | relaciones visibles: {2,2} | export: {3}" -f $s.n, $s.d.DiagramObjects.Count, $visibles, $exp)
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
