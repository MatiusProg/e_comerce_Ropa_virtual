# =========================================================================
# CAP. 3 - 3.3.1 Diseno de Datos Logico: el modelo de dominio del ciclo.
#
# Sigue las convenciones del modelo de referencia que paso Mateo
# (MODELO DE DOMINIO.qea):
#
#   - una clase por tabla, con el NOMBRE DE LA TABLA EN MAYUSCULAS
#   - sin operaciones: es un modelo de datos, no de comportamiento
#   - atributos privados, la clave primaria primero
#   - las relaciones son conectores Association con un VERBO EN MAYUSCULAS
#     por nombre y cardinalidad en los dos extremos
#
# Dos cosas se agregan sobre la referencia, porque el proyecto ya las tiene:
#
#   1. el TIPO de cada columna, tomado del esquema real de SQLAlchemy. La
#      referencia solo tipa la clave primaria. Aqui interesa que 3.3.1 y el
#      3.3.2 fisico digan lo mismo.
#   2. el estereotipo «PK» / «FK» en cada columna que lo sea. Sin eso hay que
#      adivinar cual columna cierra cada relacion.
#
# Los nombres de columna van en minusculas, como en el codigo y como en el
# esquema de 3.3.2. Solo el nombre de la entidad va en mayusculas.
#
# El contenido sale de dos fuentes que coinciden:
#   docs/entregas/ciclo-1/cap-2-3-analisis-y-diseno.md  seccion 3.3.1
#   backend/app/modules/{seguridad,organizacion,catalogo}/models.py
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

$root     = $ea.Models.GetAt(0)
$pRaiz = Get-OCrearPaqueteModelo $root 'Violet Boutique'
$pCap3    = Get-OCrearPaqueteModelo $pRaiz 'CAP. 3 - Flujo de Trabajo: Diseno'
$p331     = Get-OCrearPaqueteModelo $pCap3 '3.3.1 Diseno de Datos Logico'

# Indice por SQL y no por la coleccion Elements de la API: Package.Elements no
# devuelve los elementos de tipo Package, y un Get-O-Crear que la recorra los
# recrea en cada pasada. Aqui son todos Class, pero se hace igual por
# uniformidad --- y porque es la unica lectura que no miente.
$yaEstan = @{}
$xml = $ea.SQLQuery("SELECT o.Object_ID AS id, o.Name AS nombre FROM t_object o WHERE o.Package_ID=$($p331.PackageID) AND o.Object_Type='Class'")
if ($xml) {
    $doc = New-Object System.Xml.XmlDocument
    $doc.LoadXml($xml)
    foreach ($fila in $doc.SelectNodes('//Row')) { $yaEstan["$($fila.nombre)"] = [int]$fila.id }
}
Write-Output "  ya habia $($yaEstan.Count) entidades en 3.3.1"

function Get-OCrearEntidad($nombre, $notas) {
    if ($yaEstan.ContainsKey($nombre)) { return $ea.GetElementByID($yaEstan[$nombre]) }
    $e = $p331.Elements.AddNew($nombre, 'Class')
    if ($notas) { $e.Notes = $notas }
    [void]$e.Update(); $p331.Elements.Refresh()
    $yaEstan[$nombre] = $e.ElementID
    return $e
}

# Cada columna es @{n=nombre; t=tipo; k='PK'|'FK'|'PK,FK'|$null}
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

# Regla del 04/09/2026: la union entre dos clases es siempre una Association.
# Aqui ademas coincide con la referencia, que usa Association para todas las
# relaciones del modelo de dominio.
function New-Relacion($src, $dst, $verbo, $cardOrigen, $cardDestino) {
    foreach ($c in $src.Connectors) {
        if ($c.SupplierID -eq $dst.ElementID -and $c.Type -eq 'Association' -and $c.Name -eq $verbo) { return }
    }
    $c = $src.Connectors.AddNew($verbo, 'Association')
    $c.SupplierID = $dst.ElementID
    [void]$c.Update()
    $c.ClientEnd.Cardinality = $cardOrigen; $c.SupplierEnd.Cardinality = $cardDestino
    [void]$c.ClientEnd.Update(); [void]$c.SupplierEnd.Update(); [void]$c.Update()
    $src.Connectors.Refresh()
}

# =========================================================================
# Las dieciseis entidades del Ciclo 1.
#
# Catorce vienen de las clases de analisis de 2.3; las otras dos las agrega el
# diseno y es lo que conviene senalar en la defensa:
#   direccion_cliente  CU-04 admite varias direcciones por cliente, y un
#                      uno-a-muchos no se representa como atributo.
#   rol_permiso        resuelve el muchos-a-muchos entre rol y permiso.
#
# El orden de las columnas es el del codigo, para que 3.3.1 y 3.3.2 se lean
# igual. Los tipos son los que compila el dialecto PostgreSQL de SQLAlchemy;
# TIMESTAMP WITH TIME ZONE se abrevia TIMESTAMPTZ, que es como aparece en el
# esquema fisico.
# =========================================================================
$AUD = @(
  @{n='creado_en';      t='TIMESTAMPTZ'},
  @{n='actualizado_en'; t='TIMESTAMPTZ'}
)

$entidades = @(
  @{ n='ROL'; nt='Tabla rol. Los nombres van en mayusculas (CLIENTE, ADMINISTRADOR, ...) porque asi los compara app/core/dependencies.py.'
     cols=@(
       @{n='id';          t='SMALLSERIAL';   k='PK'},
       @{n='nombre';      t='VARCHAR(30)'},
       @{n='descripcion'; t='VARCHAR(150)'}
     )},
  @{ n='PERMISO'; nt='Tabla permiso.'
     cols=@(
       @{n='id';          t='SMALLSERIAL';   k='PK'},
       @{n='codigo';      t='VARCHAR(60)'},
       @{n='descripcion'; t='VARCHAR(150)'}
     )},
  @{ n='ROL_PERMISO'; nt='Tabla rol_permiso. Entidad que el diseno agrega: resuelve el muchos-a-muchos entre rol y permiso. Su clave primaria es el par completo.'
     cols=@(
       @{n='rol_id';     t='SMALLINT'; k='PK,FK'},
       @{n='permiso_id'; t='SMALLINT'; k='PK,FK'}
     )},
  @{ n='USUARIO'; nt='Tabla usuario. La contrasena se guarda solo como hash bcrypt (RNF01).'
     cols=@(
       @{n='id';              t='BIGSERIAL';    k='PK'},
       @{n='correo';          t='VARCHAR(120)'},
       @{n='hash_contrasena'; t='VARCHAR(255)'},
       @{n='nombres';         t='VARCHAR(80)'},
       @{n='apellidos';       t='VARCHAR(80)'},
       @{n='rol_id';          t='SMALLINT';     k='FK'},
       @{n='activo';          t='BOOLEAN'}
     ) + $AUD },
  @{ n='CLIENTE'; nt='Tabla cliente. usuario_id es unico: un usuario es cliente a lo sumo una vez.'
     cols=@(
       @{n='id';             t='BIGSERIAL';   k='PK'},
       @{n='usuario_id';     t='BIGINT';      k='FK'},
       @{n='documento';      t='VARCHAR(20)'},
       @{n='telefono';       t='VARCHAR(20)'},
       @{n='talla_superior'; t='VARCHAR(10)'},
       @{n='talla_inferior'; t='VARCHAR(10)'},
       @{n='talla_calzado';  t='VARCHAR(10)'}
     ) + $AUD },
  @{ n='DIRECCION_CLIENTE'; nt='Tabla direccion_cliente. Entidad que el diseno agrega: CU-04 permite varias direcciones de entrega por cliente, y una relacion uno-a-muchos no se puede representar como atributo de Cliente.'
     cols=@(
       @{n='id';             t='BIGSERIAL';    k='PK'},
       @{n='cliente_id';     t='BIGINT';       k='FK'},
       @{n='ciudad_id';      t='INTEGER';      k='FK'},
       @{n='alias';          t='VARCHAR(40)'},
       @{n='direccion';      t='VARCHAR(200)'},
       @{n='referencia';     t='VARCHAR(200)'},
       @{n='predeterminada'; t='BOOLEAN'}
     ) + $AUD },
  @{ n='SESION_TOKEN'; nt='Tabla sesion_token. Es la fila que permite revocar un token antes de que expire. No usa el mixin de auditoria: sus fechas son las de su propio ciclo de vida, que es el diagrama de estado de 3.2.'
     cols=@(
       @{n='id';          t='BIGSERIAL';   k='PK'},
       @{n='usuario_id';  t='BIGINT';      k='FK'},
       @{n='jti';         t='UUID'},
       @{n='emitido_en';  t='TIMESTAMPTZ'},
       @{n='expira_en';   t='TIMESTAMPTZ'},
       @{n='revocado_en'; t='TIMESTAMPTZ'}
     )},
  @{ n='CIUDAD'; nt='Tabla ciudad.'
     cols=@(
       @{n='id';           t='SERIAL';       k='PK'},
       @{n='nombre';       t='VARCHAR(60)'},
       @{n='departamento'; t='VARCHAR(60)'}
     ) + $AUD },
  @{ n='SUCURSAL'; nt='Tabla sucursal. Es el eje sobre el que se particiona el inventario en el Ciclo 2.'
     cols=@(
       @{n='id';                   t='SERIAL';       k='PK'},
       @{n='ciudad_id';            t='INTEGER';      k='FK'},
       @{n='nombre';               t='VARCHAR(80)'},
       @{n='direccion';            t='VARCHAR(200)'},
       @{n='telefono';             t='VARCHAR(20)'},
       @{n='horario_apertura';     t='TIME'},
       @{n='horario_cierre';       t='TIME'},
       @{n='capacidad_vestidores'; t='SMALLINT'},
       @{n='activa';               t='BOOLEAN'}
     ) + $AUD },
  @{ n='EMPLEADO'; nt='Tabla empleado. sucursal_id es lo que da el ambito del token de un Encargado y le impide operar sobre otra sucursal.'
     cols=@(
       @{n='id';            t='BIGSERIAL';   k='PK'},
       @{n='usuario_id';    t='BIGINT';      k='FK'},
       @{n='sucursal_id';   t='INTEGER';     k='FK'},
       @{n='documento';     t='VARCHAR(20)'},
       @{n='telefono';      t='VARCHAR(20)'},
       @{n='cargo';         t='VARCHAR(30)'},
       @{n='fecha_ingreso'; t='DATE'},
       @{n='fecha_baja';    t='DATE'}
     ) + $AUD },
  @{ n='PROVEEDOR'; nt='Tabla proveedor. usuario_id es opcional: un proveedor puede existir sin cuenta de acceso al sistema.'
     cols=@(
       @{n='id';                        t='BIGSERIAL';    k='PK'},
       @{n='usuario_id';                t='BIGINT';       k='FK'},
       @{n='razon_social';              t='VARCHAR(120)'},
       @{n='identificacion_tributaria'; t='VARCHAR(30)'},
       @{n='contacto';                  t='VARCHAR(80)'},
       @{n='telefono';                  t='VARCHAR(20)'},
       @{n='correo';                    t='VARCHAR(120)'},
       @{n='direccion';                 t='VARCHAR(200)'},
       @{n='activo';                    t='BOOLEAN'}
     ) + $AUD },
  @{ n='CATEGORIA'; nt='Tabla categoria. Jerarquia por autorreferencia: categoria_padre_id nulo significa categoria raiz.'
     cols=@(
       @{n='id';                 t='SERIAL';      k='PK'},
       @{n='categoria_padre_id'; t='INTEGER';     k='FK'},
       @{n='nombre';             t='VARCHAR(60)'},
       @{n='orden';              t='SMALLINT'},
       @{n='activa';             t='BOOLEAN'}
     ) + $AUD },
  @{ n='TALLA'; nt='Tabla talla. La unicidad es del par (tipo_prenda, codigo): la M de una remera no es la M de un pantalon.'
     cols=@(
       @{n='id';          t='SERIAL';      k='PK'},
       @{n='tipo_prenda'; t='VARCHAR(30)'},
       @{n='codigo';      t='VARCHAR(10)'},
       @{n='orden';       t='SMALLINT'},
       @{n='activa';      t='BOOLEAN'}
     ) + $AUD },
  @{ n='COLOR'; nt='Tabla color.'
     cols=@(
       @{n='id';          t='SERIAL';      k='PK'},
       @{n='nombre';      t='VARCHAR(40)'},
       @{n='hexadecimal'; t='CHAR(7)'},
       @{n='activo';      t='BOOLEAN'}
     ) + $AUD },
  @{ n='TEMPORADA'; nt='Tabla temporada.'
     cols=@(
       @{n='id';           t='SERIAL';       k='PK'},
       @{n='nombre';       t='VARCHAR(60)'},
       @{n='descripcion';  t='VARCHAR(200)'},
       @{n='fecha_inicio'; t='DATE'},
       @{n='fecha_fin';    t='DATE'},
       @{n='activa';       t='BOOLEAN'}
     ) + $AUD },
  @{ n='COLECCION'; nt='Tabla coleccion.'
     cols=@(
       @{n='id';           t='SERIAL';       k='PK'},
       @{n='temporada_id'; t='INTEGER';      k='FK'},
       @{n='nombre';       t='VARCHAR(60)'},
       @{n='descripcion';  t='VARCHAR(200)'},
       @{n='activa';       t='BOOLEAN'}
     ) + $AUD }
)

# =========================================================================
# Las relaciones.
#
# Cardinalidades tomadas de lo que la base realmente obliga, no de la prosa:
# cliente.usuario_id y empleado.usuario_id son UNIQUE y NOT NULL, asi que un
# usuario tiene 0 o 1 ficha de cada tipo --- nunca "exactamente 1", porque un
# Administrador no es ni cliente ni empleado.
# =========================================================================
$relaciones = @(
  @{ o='ROL';       v='TIENE';         d='USUARIO';           co='1'; cd='0..*' },
  @{ o='ROL';       v='SE_ASIGNA_EN';  d='ROL_PERMISO';       co='1'; cd='0..*' },
  @{ o='PERMISO';   v='SE_OTORGA_EN';  d='ROL_PERMISO';       co='1'; cd='0..*' },
  @{ o='USUARIO';   v='ES';            d='CLIENTE';           co='1'; cd='0..1' },
  @{ o='USUARIO';   v='ES';            d='EMPLEADO';          co='1'; cd='0..1' },
  @{ o='USUARIO';   v='PUEDE_SER';     d='PROVEEDOR';         co='1'; cd='0..1' },
  @{ o='USUARIO';   v='ABRE';          d='SESION_TOKEN';      co='1'; cd='0..*' },
  @{ o='CLIENTE';   v='REGISTRA';      d='DIRECCION_CLIENTE'; co='1'; cd='0..*' },
  @{ o='CIUDAD';    v='UBICA';         d='DIRECCION_CLIENTE'; co='1'; cd='0..*' },
  @{ o='CIUDAD';    v='ALBERGA';       d='SUCURSAL';          co='1'; cd='0..*' },
  @{ o='SUCURSAL';  v='EMPLEA';        d='EMPLEADO';          co='1'; cd='0..*' },
  @{ o='CATEGORIA'; v='AGRUPA_A';      d='CATEGORIA';         co='0..1'; cd='0..*' },
  @{ o='TEMPORADA'; v='CONTIENE';      d='COLECCION';         co='1'; cd='0..*' }
)

# ---- crear todo ----
$E = @{}
foreach ($def in $entidades) {
    $E[$def.n] = Get-OCrearEntidad $def.n $def.nt
    Set-Columnas $E[$def.n] $def.cols
}
foreach ($r in $relaciones) { New-Relacion $E[$r.o] $E[$r.d] $r.v $r.co $r.cd }

# ---- el diagrama ----
$nombre = '3.3.1 Modelo de Dominio - CICLO #1'
if (BuscarDiagrama $p331 $nombre) {
    Write-Output "  $nombre ya existe, no se toca"
} else {
    $d = $p331.Diagrams.AddNew($nombre, 'Logical')
    $d.Notes = 'Modelo entidad-relacion de las dieciseis entidades del Ciclo 1. Catorce vienen del analisis de 2.3; direccion_cliente y rol_permiso las agrega el diseno.'
    [void]$d.Update(); $p331.Diagrams.Refresh()

    # Columnas agrupadas por paquete de analisis, de izquierda a derecha:
    # las raices de identidad, despues lo que cuelga de usuario, despues la
    # organizacion, y por ultimo los maestros del catalogo. Las
    # autorreferencias --- CATEGORIA --- necesitan aire a la derecha.
    $columnas = @(
      @('ROL','PERMISO','ROL_PERMISO'),
      @('USUARIO','SESION_TOKEN'),
      @('CLIENTE','DIRECCION_CLIENTE','CIUDAD'),
      @('EMPLEADO','SUCURSAL','PROVEEDOR'),
      @('CATEGORIA','TALLA','COLOR','TEMPORADA','COLECCION')
    )
    $ancho = 320; $sepH = 120; $sepV = 60; $margen = 40
    $altoDe = @{}
    foreach ($def in $entidades) { $altoDe[$def.n] = 60 + $def.cols.Count * 18 }

    $l = $margen
    $fondo = 0                      # la columna que baja mas, para el pie
    foreach ($col in $columnas) {
        $t = -$margen
        foreach ($n in $col) {
            Poner $d $E[$n] $l $t $ancho $altoDe[$n]
            $t -= ($altoDe[$n] + $sepV)
        }
        if ($t -lt $fondo) { $fondo = $t }
        $l += ($ancho + $sepH)
    }

    # Nota de lectura al pie. Va como Note en el lienzo porque al exportar el
    # PNG las notas del elemento no se ven.
    $nota = $p331.Elements.AddNew('', 'Note')
    $nota.Notes = "Las dieciseis entidades del Ciclo 1.`n`nCatorce salen de las clases de analisis de 2.3. Las otras dos las agrega el diseno, y es lo que aporta este flujo de trabajo:`n`n  DIRECCION_CLIENTE --- CU-04 admite varias direcciones de entrega por cliente. Un uno-a-muchos exige entidad propia; como atributo de CLIENTE seria irrepresentable.`n`n  ROL_PERMISO --- resuelve el muchos-a-muchos entre ROL y PERMISO.`n`nUn USUARIO tiene 0 o 1 ficha de CLIENTE y 0 o 1 de EMPLEADO, no exactamente una de cada: un Administrador no es ninguna de las dos."
    [void]$nota.Update()
    Poner $d $nota $margen ($fondo - 60) 760 300

    $d.DiagramObjects.Refresh()
    $d.DiagramLinks.Refresh()
    Write-Output "  $nombre : $($d.DiagramObjects.Count) objetos, $($d.DiagramLinks.Count) relaciones"
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
