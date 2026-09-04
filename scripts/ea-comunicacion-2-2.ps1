# =========================================================================
# CAP. 2 - 2.2 Analizar Casos de Uso: diagramas de comunicacion.
#
# Un diagrama por caso de uso del Ciclo 1, con sus clases de analisis y los
# mensajes numerados entre ellas.
#
# NUMERACION DE LOS FLUJOS. El flujo principal va 1, 2, 3... Los flujos
# alternativos y las excepciones conservan la etiqueta que usa la tabla de
# detalle de cap-1-captura-requisitos.md: "3a.1" es el primer mensaje del flujo
# alternativo 3a, y "E1" el de la primera excepcion. Asi el diagrama se lee
# contra la tabla sin tener que traducir nada.
#
# COMO SE ARMA UN MENSAJE EN EA, que costo averiguarlo:
#   - El ENLACE entre dos objetos es un conector 'Association'. Es lo que dibuja
#     la linea, y va uno solo por par aunque intercambien varios mensajes.
#   - Cada MENSAJE es un conector 'Collaboration' cuyo nombre es el texto
#     numerado. Aporta la etiqueta, no la linea.
#   - Un conector 'Sequence' --- el de los diagramas de secuencia --- se crea sin
#     error y no dibuja nada en un diagrama de comunicacion.
#   - Los estereotipos boundary/control/entity se dibujan como un circulo
#     inscrito en la caja, asi que la caja tiene que ser CUADRADA.
#
# LIMITACION CONOCIDA: los mensajes que comparten enlace apilan sus etiquetas en
# el punto medio. Se intento separarlas por DiagramLink.Geometry y EA lo
# recalcula. Se arreglan arrastrandolas una vez en EA.
#
# ADITIVO: abre el modelo y solo agrega los diagramas que faltan.
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

function Get-Actor($nombre) {
    $clave = "Actor||$nombre"
    if ($indice.ContainsKey($clave)) { return $indice[$clave] }
    throw "No se encontro el actor '$nombre'"
}

function Get-Diagrama($pkg, $nombre) {
    foreach ($d in $pkg.Diagrams) { if ($d.Name -eq $nombre) { return $d } }
    return $null
}

function Poner($dia, $el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l+$ancho);t=$t;b=$($t-$alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
}

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
}

# ---------------- estructura ----------------

$root     = $ea.Models.GetAt(0)
$pFashion = Get-OCrearPaqueteModelo $root 'FashionStore'
Registrar-Elementos $pFashion

$pCap2 = Get-OCrearPaqueteModelo $pFashion 'CAP. 2 - Flujo de Trabajo: Analisis'
$p22   = Get-OCrearPaqueteModelo $pCap2    '2.2 Analizar Casos de Uso'
$pClas = Get-OCrearPaqueteModelo $p22      'Clases de Analisis'

# ---------------- descripcion de las clases de analisis ----------------

$desc = @{
    'FormularioRegistro'       = 'Pantalla de registro, en la web y en la app movil.'
    'FormularioLogin'          = 'Pantalla de inicio de sesion, comun a los cinco actores humanos.'
    'PantallaUsuarios'         = 'Listado y formulario de usuarios y roles, area del Administrador.'
    'PantallaPerfil'           = 'Perfil del cliente: datos, tallas habituales y direcciones.'
    'PantallaSucursales'       = 'Arbol de ciudades y sucursales, con su formulario.'
    'PantallaEmpleados'        = 'Listado y formulario de empleados, con filtro por sucursal y cargo.'
    'PantallaProveedores'      = 'Listado y formulario de proveedores.'
    'PantallaMaestrosCatalogo' = 'Categorias en arbol, tallas y colores.'
    'PantallaTemporadas'       = 'Temporadas y sus colecciones.'
    'GestorRegistro'      = 'Coordina CU-01: valida, verifica el correo, calcula el hash y crea usuario y cliente en una transaccion.'
    'GestorAutenticacion' = 'Coordina CU-02 y resuelve la autorizacion del resto: verifica credenciales, emite y revoca el token.'
    'GestorUsuarios'      = 'Coordina CU-03: alta, edicion, activacion y baja de cuentas, con revocacion de sesiones.'
    'GestorPerfil'        = 'Coordina CU-04: datos del cliente, direcciones y cambio de contrasena.'
    'GestorOrganizacion'  = 'Coordina CU-05: ciudades y sucursales, con su regla de nombre unico por ciudad.'
    'GestorEmpleados'     = 'Coordina CU-06: crea el empleado y su usuario en una unica transaccion.'
    'GestorProveedores'   = 'Coordina CU-07: proveedores y su acceso opcional al sistema.'
    'GestorTaxonomia'     = 'Coordina CU-08: categorias jerarquicas, tallas y colores.'
    'GestorTemporadas'    = 'Coordina CU-09: temporadas con vigencia y sus colecciones.'
    'Usuario'          = 'Identidad y credencial de quien accede al sistema.'
    'Rol'              = 'Conjunto de permisos de un tipo de usuario.'
    'Cliente'          = 'Datos comerciales del usuario con rol Cliente.'
    'SesionToken'      = 'Sesion emitida, con su vigencia y su revocacion.'
    'DireccionCliente' = 'Direccion de entrega de un cliente.'
    'Ciudad'           = 'Agrupa las sucursales de una misma plaza.'
    'Sucursal'         = 'Tienda fisica; eje de particion del inventario.'
    'Empleado'         = 'Persona que trabaja en una sucursal, con su cargo.'
    'Proveedor'        = 'Empresa que abastece prendas.'
    'Categoria'        = 'Clasificacion jerarquica de las prendas.'
    'Talla'            = 'Medida de una prenda.'
    'Color'            = 'Color de una prenda.'
    'Temporada'        = 'Ventana comercial de los productos.'
    'Coleccion'        = 'Conjunto de productos de una temporada.'
}

# ---------------- definicion de los nueve diagramas ----------------

$casos = @(
  @{ n='2.2 CU-01 Registrar cliente'
     actores=@('Cliente'); boundary='FormularioRegistro'; controles=@('GestorRegistro')
     entidades=@('Rol','Usuario','Cliente'); nota=$null
     msj=@(
       @{d='A:Cliente';a='FormularioRegistro';m='1: enviarDatos(nombres, apellidos, correo, contrasena)'},
       @{d='FormularioRegistro';a='GestorRegistro';m='2: registrarCliente(datos)'},
       @{d='GestorRegistro';a='GestorRegistro';m='3: validarDatos(datos)'},
       @{d='GestorRegistro';a='Usuario';m='4: existeCorreo(correo)'},
       @{d='GestorRegistro';a='GestorRegistro';m='5: hashearContrasena(contrasena)'},
       @{d='GestorRegistro';a='Rol';m='6: obtenerRol("CLIENTE")'},
       @{d='GestorRegistro';a='Usuario';m='7: crear(usuario)'},
       @{d='GestorRegistro';a='Cliente';m='8: crear(cliente)'},
       @{d='FormularioRegistro';a='A:Cliente';m='9: confirmarRegistro()'},
       @{d='GestorRegistro';a='FormularioRegistro';m='E1: correoYaRegistrado()'},
       @{d='GestorRegistro';a='GestorRegistro';m='E2: revertirTransaccion()'}
     )},

  @{ n='2.2 CU-02 Iniciar y cerrar sesión'
     actores=@('Cliente'); boundary='FormularioLogin'; controles=@('GestorAutenticacion')
     entidades=@('Rol','Usuario','SesionToken')
     nota='Cualquiera de los cinco actores humanos inicia este caso de uso y la colaboracion es la misma; se dibuja Cliente como representante. Que actores participan se ve en el diagrama 1.3.2 de CU-02. Los mensajes C1 a C3 son el flujo de cierre de sesion.'
     msj=@(
       @{d='A:Cliente';a='FormularioLogin';m='1: enviarCredenciales(correo, contrasena)'},
       @{d='FormularioLogin';a='GestorAutenticacion';m='2: autenticar(credenciales)'},
       @{d='GestorAutenticacion';a='Usuario';m='3: buscarPorCorreo(correo)'},
       @{d='GestorAutenticacion';a='Usuario';m='4: verificarActivo()'},
       @{d='GestorAutenticacion';a='GestorAutenticacion';m='5: verificarContrasena(hash)'},
       @{d='GestorAutenticacion';a='Rol';m='6: obtenerRol()'},
       @{d='GestorAutenticacion';a='GestorAutenticacion';m='7: emitirToken(usuario, rol, sucursal)'},
       @{d='GestorAutenticacion';a='SesionToken';m='8: registrarSesion(jti, expiraEn)'},
       @{d='GestorAutenticacion';a='FormularioLogin';m='9: devolverToken(token)'},
       @{d='FormularioLogin';a='A:Cliente';m='10: mostrarAreaDelRol()'},
       @{d='A:Cliente';a='FormularioLogin';m='C1: solicitarCierre()'},
       @{d='FormularioLogin';a='GestorAutenticacion';m='C2: cerrarSesion(jti)'},
       @{d='GestorAutenticacion';a='SesionToken';m='C3: revocar(jti)'},
       @{d='GestorAutenticacion';a='FormularioLogin';m='E1: credencialesInvalidas()'},
       @{d='GestorAutenticacion';a='FormularioLogin';m='E2: cuentaDesactivada()'}
     )},

  @{ n='2.2 CU-03 Gestionar usuarios y roles'
     actores=@('Administrador'); boundary='PantallaUsuarios'
     controles=@('GestorUsuarios','GestorAutenticacion')
     entidades=@('Rol','Usuario','SesionToken'); nota=$null
     msj=@(
       @{d='A:Administrador';a='PantallaUsuarios';m='1: crearUsuario(datos)'},
       @{d='PantallaUsuarios';a='GestorUsuarios';m='2: registrar(datos)'},
       @{d='GestorUsuarios';a='GestorAutenticacion';m='3: autorizar("ADMINISTRADOR")'},
       @{d='GestorUsuarios';a='GestorUsuarios';m='4: validarDatos(datos)'},
       @{d='GestorUsuarios';a='Usuario';m='5: existeCorreo(correo)'},
       @{d='GestorUsuarios';a='Rol';m='6: obtenerRol(rol)'},
       @{d='GestorUsuarios';a='Usuario';m='7: crear(usuario)'},
       @{d='GestorUsuarios';a='PantallaUsuarios';m='8: confirmar()'},
       @{d='A:Administrador';a='PantallaUsuarios';m='3a.1: editar(id, datos)'},
       @{d='A:Administrador';a='PantallaUsuarios';m='3b.1: desactivar(id)'},
       @{d='GestorUsuarios';a='SesionToken';m='3b.2: revocarSesionesDe(usuario)'},
       @{d='GestorUsuarios';a='PantallaUsuarios';m='E1: correoYaRegistrado()'},
       @{d='GestorUsuarios';a='PantallaUsuarios';m='E3: noPuedeAutodesactivarse()'}
     )},

  @{ n='2.2 CU-04 Gestionar perfil del cliente'
     actores=@('Cliente'); boundary='PantallaPerfil'
     controles=@('GestorPerfil','GestorAutenticacion')
     entidades=@('Usuario','Cliente','DireccionCliente'); nota=$null
     msj=@(
       @{d='A:Cliente';a='PantallaPerfil';m='1: solicitarPerfil()'},
       @{d='PantallaPerfil';a='GestorPerfil';m='2: obtenerPerfil()'},
       @{d='GestorPerfil';a='GestorAutenticacion';m='3: autorizarPropietario()'},
       @{d='GestorPerfil';a='Cliente';m='4: buscarPorUsuario(idUsuario)'},
       @{d='A:Cliente';a='PantallaPerfil';m='5: modificar(datos)'},
       @{d='PantallaPerfil';a='GestorPerfil';m='6: actualizar(datos)'},
       @{d='GestorPerfil';a='GestorPerfil';m='7: validarDatos(datos)'},
       @{d='GestorPerfil';a='Cliente';m='8: guardar(cliente)'},
       @{d='GestorPerfil';a='DireccionCliente';m='3a.1: agregarDireccion(datos)'},
       @{d='GestorPerfil';a='DireccionCliente';m='3b.1: eliminarDireccion(id)'},
       @{d='GestorPerfil';a='Usuario';m='3c.1: cambiarContrasena(actual, nueva)'},
       @{d='GestorPerfil';a='PantallaPerfil';m='E1: contrasenaActualIncorrecta()'}
     )},

  @{ n='2.2 CU-05 Gestionar ciudades y sucursales'
     actores=@('Administrador'); boundary='PantallaSucursales'
     controles=@('GestorOrganizacion','GestorAutenticacion')
     entidades=@('Ciudad','Sucursal'); nota=$null
     msj=@(
       @{d='A:Administrador';a='PantallaSucursales';m='1: registrarSucursal(datos)'},
       @{d='PantallaSucursales';a='GestorOrganizacion';m='2: crearSucursal(datos)'},
       @{d='GestorOrganizacion';a='GestorAutenticacion';m='3: autorizar("ADMINISTRADOR")'},
       @{d='GestorOrganizacion';a='GestorOrganizacion';m='4: validarDatos(datos)'},
       @{d='GestorOrganizacion';a='Ciudad';m='5: obtenerCiudad(id)'},
       @{d='GestorOrganizacion';a='Sucursal';m='6: existeNombreEnCiudad(ciudad, nombre)'},
       @{d='GestorOrganizacion';a='Sucursal';m='7: crear(sucursal)'},
       @{d='GestorOrganizacion';a='PantallaSucursales';m='8: confirmar()'},
       @{d='A:Administrador';a='PantallaSucursales';m='3a.1: gestionarCiudad(datos)'},
       @{d='GestorOrganizacion';a='Ciudad';m='3a.2: crear(ciudad)'},
       @{d='GestorOrganizacion';a='Sucursal';m='3c.1: darDeBaja(sucursal)'},
       @{d='GestorOrganizacion';a='PantallaSucursales';m='E1: nombreDuplicadoEnLaCiudad()'},
       @{d='GestorOrganizacion';a='PantallaSucursales';m='E2: ciudadConSucursalesActivas()'}
     )},

  @{ n='2.2 CU-06 Gestionar empleados'
     actores=@('Administrador'); boundary='PantallaEmpleados'
     controles=@('GestorEmpleados','GestorAutenticacion')
     entidades=@('Rol','Usuario','Sucursal','Empleado')
     nota='CU-06 incluye a CU-03: registrar un empleado crea siempre su usuario con el rol del cargo. Los mensajes 7, 8 y 9 ocurren dentro de una unica transaccion; si falla cualquiera, se revierte todo (E3).'
     msj=@(
       @{d='A:Administrador';a='PantallaEmpleados';m='1: registrarEmpleado(datos)'},
       @{d='PantallaEmpleados';a='GestorEmpleados';m='2: crearEmpleado(datos)'},
       @{d='GestorEmpleados';a='GestorAutenticacion';m='3: autorizar("ADMINISTRADOR")'},
       @{d='GestorEmpleados';a='GestorEmpleados';m='4: validarDatos(datos)'},
       @{d='GestorEmpleados';a='Empleado';m='5: existeDocumento(documento)'},
       @{d='GestorEmpleados';a='Sucursal';m='6: verificarActiva(sucursal)'},
       @{d='GestorEmpleados';a='Rol';m='7: obtenerRol(cargo)'},
       @{d='GestorEmpleados';a='Usuario';m='8: crear(usuario)'},
       @{d='GestorEmpleados';a='Empleado';m='9: crear(empleado)'},
       @{d='GestorEmpleados';a='PantallaEmpleados';m='10: confirmar()'},
       @{d='A:Administrador';a='PantallaEmpleados';m='3b.1: darDeBaja(id)'},
       @{d='GestorEmpleados';a='Usuario';m='3b.2: desactivarUsuario()'},
       @{d='GestorEmpleados';a='PantallaEmpleados';m='E1: documentoYaRegistrado()'},
       @{d='GestorEmpleados';a='GestorEmpleados';m='E3: revertirTransaccion()'}
     )},

  @{ n='2.2 CU-07 Gestionar proveedores'
     actores=@('Administrador','Proveedor'); boundary='PantallaProveedores'
     controles=@('GestorProveedores','GestorAutenticacion')
     entidades=@('Usuario','Proveedor')
     nota='El actor Proveedor solo consulta sus propios datos (P1); el alta, la edicion y la baja son del Administrador.'
     msj=@(
       @{d='A:Administrador';a='PantallaProveedores';m='1: registrarProveedor(datos)'},
       @{d='PantallaProveedores';a='GestorProveedores';m='2: crearProveedor(datos)'},
       @{d='GestorProveedores';a='GestorAutenticacion';m='3: autorizar("ADMINISTRADOR")'},
       @{d='GestorProveedores';a='GestorProveedores';m='4: validarDatos(datos)'},
       @{d='GestorProveedores';a='Proveedor';m='5: existeIdentificacion(nit)'},
       @{d='GestorProveedores';a='Proveedor';m='6: crear(proveedor)'},
       @{d='GestorProveedores';a='PantallaProveedores';m='7: confirmar()'},
       @{d='GestorProveedores';a='Proveedor';m='3b.1: darDeBaja(proveedor)'},
       @{d='GestorProveedores';a='Usuario';m='3c.1: habilitarAcceso(proveedor)'},
       @{d='A:Proveedor';a='PantallaProveedores';m='P1: consultarSusDatos()'},
       @{d='GestorProveedores';a='PantallaProveedores';m='E1: identificacionDuplicada()'}
     )},

  @{ n='2.2 CU-08 Gestionar categorías, tallas y colores'
     actores=@('Administrador'); boundary='PantallaMaestrosCatalogo'
     controles=@('GestorTaxonomia','GestorAutenticacion')
     entidades=@('Categoria','Talla','Color')
     nota='El flujo principal 1-8 es el de categorias. Los flujos 1a y 1b son los de tallas y colores, que son mas simples: no tienen jerarquia que validar.'
     msj=@(
       @{d='A:Administrador';a='PantallaMaestrosCatalogo';m='1: registrarCategoria(datos)'},
       @{d='PantallaMaestrosCatalogo';a='GestorTaxonomia';m='2: crearCategoria(datos)'},
       @{d='GestorTaxonomia';a='GestorAutenticacion';m='3: autorizar("ADMINISTRADOR")'},
       @{d='GestorTaxonomia';a='GestorTaxonomia';m='4: validarDatos(datos)'},
       @{d='GestorTaxonomia';a='Categoria';m='5: existeEntreHermanas(padre, nombre)'},
       @{d='GestorTaxonomia';a='Categoria';m='6: verificarSinCiclo(padre)'},
       @{d='GestorTaxonomia';a='Categoria';m='7: crear(categoria)'},
       @{d='GestorTaxonomia';a='PantallaMaestrosCatalogo';m='8: confirmar()'},
       @{d='A:Administrador';a='PantallaMaestrosCatalogo';m='1a.1: gestionarTalla(datos)'},
       @{d='GestorTaxonomia';a='Talla';m='1a.2: crear(talla)'},
       @{d='A:Administrador';a='PantallaMaestrosCatalogo';m='1b.1: gestionarColor(datos)'},
       @{d='GestorTaxonomia';a='Color';m='1b.2: crear(color)'},
       @{d='GestorTaxonomia';a='PantallaMaestrosCatalogo';m='E2: cicloEnLaJerarquia()'},
       @{d='GestorTaxonomia';a='PantallaMaestrosCatalogo';m='E3: tieneDependencias()'}
     )},

  @{ n='2.2 CU-09 Gestionar temporadas y colecciones'
     actores=@('Administrador'); boundary='PantallaTemporadas'
     controles=@('GestorTemporadas','GestorAutenticacion')
     entidades=@('Temporada','Coleccion')
     nota='El flujo principal 1-8 es el de temporadas. El flujo 1a es el de colecciones, que dependen de una temporada existente.'
     msj=@(
       @{d='A:Administrador';a='PantallaTemporadas';m='1: registrarTemporada(datos)'},
       @{d='PantallaTemporadas';a='GestorTemporadas';m='2: crearTemporada(datos)'},
       @{d='GestorTemporadas';a='GestorAutenticacion';m='3: autorizar("ADMINISTRADOR")'},
       @{d='GestorTemporadas';a='GestorTemporadas';m='4: verificarRangoDeFechas(inicio, fin)'},
       @{d='GestorTemporadas';a='Temporada';m='5: existeNombre(nombre)'},
       @{d='GestorTemporadas';a='Temporada';m='6: buscarSolapamiento(inicio, fin)'},
       @{d='GestorTemporadas';a='Temporada';m='7: crear(temporada)'},
       @{d='GestorTemporadas';a='PantallaTemporadas';m='8: confirmar()'},
       @{d='A:Administrador';a='PantallaTemporadas';m='1a.1: registrarColeccion(datos)'},
       @{d='GestorTemporadas';a='Coleccion';m='1a.2: crear(coleccion)'},
       @{d='GestorTemporadas';a='Temporada';m='3b.1: cerrarTemporada(id)'},
       @{d='GestorTemporadas';a='PantallaTemporadas';m='E1: fechasIncoherentes()'},
       @{d='GestorTemporadas';a='PantallaTemporadas';m='E2: solapamientoDeVigencias()'}
     )}
)

# ---------------- generacion ----------------

foreach ($caso in $casos) {
    if (Get-Diagrama $p22 $caso.n) { Write-Output "  $($caso.n) ya existe, no se toca"; continue }

    # Participantes: actor(es) | boundary | control(es) | entidades.
    $part = @{}
    # Prefijo "A:" en los actores: el actor Cliente y la entidad Cliente son
    # elementos distintos y comparten nombre; sin prefijo, uno pisaba al otro en
    # la tabla de participantes y el diagrama salia con un objeto de menos.
    foreach ($nom in $caso.actores)   { $part["A:$nom"] = Get-Actor $nom }
    $part[$caso.boundary]             = Get-OCrearClase $pClas $caso.boundary 'boundary' $desc[$caso.boundary]
    foreach ($nom in $caso.controles) { $part[$nom] = Get-OCrearClase $pClas $nom 'control' $desc[$nom] }
    foreach ($nom in $caso.entidades) { $part[$nom] = Get-OCrearClase $pClas $nom 'entity'  $desc[$nom] }

    $d = $p22.Diagrams.AddNew($caso.n, 'Communication')
    [void]$d.Update(); $p22.Diagrams.Refresh()

    # Cuatro columnas: actor | boundary | control | entidades. Cada columna se
    # centra sobre el mismo eje horizontal.
    $columnas = @(
        @{ lista=@($caso.actores | ForEach-Object { "A:$_" }); x=40; ancho=100; alto=90 },
        @{ lista=@($caso.boundary);    x=320; ancho=100; alto=100 },
        @{ lista=$caso.controles;      x=640; ancho=100; alto=100 },
        @{ lista=$caso.entidades;      x=960; ancho=100; alto=100 }
    )
    foreach ($col in $columnas) {
        # EA dibuja el circulo del estereotipo algo mas grande que la caja, asi
        # que la separacion tiene que ser mayor que el alto o se encabalgan.
        $paso   = $col.alto + 130
        $inicio = -200 + [int]((($col.lista.Count - 1) * $paso) / 2)
        for ($i = 0; $i -lt $col.lista.Count; $i++) {
            Poner $d $part[$col.lista[$i]] $col.x ($inicio - $i * $paso) $col.ancho $col.alto
        }
    }

    # Un enlace por par de participantes que se comunican, sin repetir.
    $pares = @{}
    foreach ($m in $caso.msj) {
        if ($m.d -eq $m.a) { continue }
        $c1 = $part[$m.d]; $c2 = $part[$m.a]
        $k1 = "$($c1.ElementID)-$($c2.ElementID)"; $k2 = "$($c2.ElementID)-$($c1.ElementID)"
        if ($pares.ContainsKey($k1) -or $pares.ContainsKey($k2)) { continue }
        New-Enlace $c1 $c2
        $pares[$k1] = $true
    }
    foreach ($m in $caso.msj) { New-Mensaje $part[$m.d] $part[$m.a] $m.m }

    if ($caso.nota) {
        $nota = $pClas.Elements.AddNew('', 'Note')
        $nota.Notes = $caso.nota
        [void]$nota.Update()
        Poner $d $nota 320 -640 740 120
    }

    # Las clases de analisis se comparten entre casos de uso --- GestorAutenticacion,
    # Usuario y Rol aparecen en casi todos --- y EA dibuja TODA relacion existente
    # entre los elementos presentes en el lienzo. Sin esto, el diagrama de CU-06
    # mostraba tambien los mensajes de CU-02. Se oculta en este diagrama todo lo
    # que no se creo para el; en el modelo no se toca nada.
    $mios = @{}
    foreach ($m in $caso.msj) { $mios[$m.m] = $true }
    $d.DiagramLinks.Refresh()
    $ajenos = 0
    foreach ($lnk in $d.DiagramLinks) {
        $con = $ea.GetConnectorByID($lnk.ConnectorID)
        $propio = $false
        if ($con.Type -eq 'Collaboration') {
            $propio = $mios.ContainsKey($con.Name)
        } elseif ($con.Type -eq 'Association') {
            $k1 = "$($con.ClientID)-$($con.SupplierID)"; $k2 = "$($con.SupplierID)-$($con.ClientID)"
            $propio = ($pares.ContainsKey($k1) -or $pares.ContainsKey($k2))
        }
        if (-not $propio) { $lnk.IsHidden = $true; [void]$lnk.Update(); $ajenos++ }
    }
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    Write-Output ("  {0,-46} {1,2} objetos, {2,2} mensajes, {3,2} ajenos ocultos" -f $caso.n, $d.DiagramObjects.Count, $caso.msj.Count, $ajenos)
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
