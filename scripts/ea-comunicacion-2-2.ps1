# =========================================================================
# CAP. 2 - 2.2 Analizar Casos de Uso: diagramas de comunicacion.
#
# Un diagrama por caso de uso del Ciclo 1: sus clases de analisis y los mensajes
# que intercambian, agrupados por flujo.
#
# ---- COMO SE ARMA UN MENSAJE EN EA -------------------------------------
#
#   1. El ENLACE entre dos objetos es un conector 'Association'. Es lo que
#      dibuja la linea, y va UNO SOLO por par de objetos, aunque intercambien
#      varios mensajes.
#   2. Cada MENSAJE es un conector 'Collaboration'. Su nombre es SOLO la
#      operacion: nada de numerarlo a mano.
#   3. El numero lo pone EA, y sale del campo PDATA4 del conector, con el
#      formato "<grupo>.<orden>". Ese campo es el "Start New Group" de la
#      interfaz: al cambiar de grupo, EA reinicia la numeracion y dibuja el
#      grupo nuevo en otro color.
#
#   PDATA4 es de SOLO LECTURA por la API (MiscData(3)), asi que se escribe con
#   Repository.Execute contra t_connector. Es la unica forma de fijar los grupos
#   por automatizacion.
#
#   Numerar a mano dentro del nombre del mensaje --- "1: enviarDatos()" --- se
#   ve parecido pero es peor: EA no sabe que son grupos, no los colorea y
#   amontona todas las etiquetas en el punto medio del enlace. Con PDATA4 las
#   apila ordenadas.
#
#   Un conector 'Sequence' --- el de los diagramas de secuencia --- se crea sin
#   error y no dibuja nada en un diagrama de comunicacion.
#
#   Los estereotipos boundary/control/entity se dibujan como un circulo inscrito
#   en la caja del elemento, asi que la caja tiene que ser CUADRADA y la
#   separacion entre elementos, mayor que su alto.
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

# Devuelve el ConnectorID para poder fijarle el numero de grupo despues.
function New-Mensaje($src, $dst, $nombre) {
    foreach ($c in $src.Connectors) {
        if ($c.SupplierID -eq $dst.ElementID -and $c.Type -eq 'Collaboration' -and $c.Name -eq $nombre) {
            return $c.ConnectorID   # ya existe: no duplicar
        }
    }
    $c = $src.Connectors.AddNew($nombre, 'Collaboration')
    $c.SupplierID = $dst.ElementID
    [void]$c.Update(); $src.Connectors.Refresh()
    return $c.ConnectorID
}

# ---------------- estructura ----------------

$root     = $ea.Models.GetAt(0)
$pFashion = Get-OCrearPaqueteModelo $root 'FashionStore'
Registrar-Elementos $pFashion

$pCap2 = Get-OCrearPaqueteModelo $pFashion 'CAP. 2 - Flujo de Trabajo: Analisis'
$p22   = Get-OCrearPaqueteModelo $pCap2    '2.2 Analizar Casos de Uso'
$pClas = Get-OCrearPaqueteModelo $p22      'Clases de Analisis'

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

# ---------------- los nueve diagramas ----------------
#
# 'g' es el grupo del mensaje. El orden dentro del grupo lo da el orden de
# declaracion. Los actores se referencian con prefijo "A:" porque el actor
# Cliente y la entidad Cliente son elementos distintos con el mismo nombre.

$casos = @(
  @{ n='2.2 CU-01 Registrar cliente'
     actores=@('Cliente'); boundary='FormularioRegistro'; controles=@('GestorRegistro')
     entidades=@('Rol','Usuario','Cliente')
     grupos='Grupo 1: flujo principal.   Grupo 2: excepciones E1 (correo ya registrado) y E2 (fallo al persistir).'
     msj=@(
       @{g=1;d='A:Cliente';a='FormularioRegistro';m='enviarDatos(nombres, apellidos, correo, contrasena)'},
       @{g=1;d='FormularioRegistro';a='GestorRegistro';m='registrarCliente(datos)'},
       @{g=1;d='GestorRegistro';a='GestorRegistro';m='validarDatos(datos)'},
       @{g=1;d='GestorRegistro';a='Usuario';m='existeCorreo(correo)'},
       @{g=1;d='GestorRegistro';a='GestorRegistro';m='hashearContrasena(contrasena)'},
       @{g=1;d='GestorRegistro';a='Rol';m='obtenerRol("CLIENTE")'},
       @{g=1;d='GestorRegistro';a='Usuario';m='crear(usuario)'},
       @{g=1;d='GestorRegistro';a='Cliente';m='crear(cliente)'},
       @{g=1;d='FormularioRegistro';a='A:Cliente';m='confirmarRegistro()'},
       @{g=2;d='GestorRegistro';a='FormularioRegistro';m='correoYaRegistrado()'},
       @{g=2;d='GestorRegistro';a='GestorRegistro';m='revertirTransaccion()'}
     )},

  @{ n='2.2 CU-02 Iniciar y cerrar sesión'
     actores=@('Cliente'); boundary='FormularioLogin'; controles=@('GestorAutenticacion')
     entidades=@('Rol','Usuario','SesionToken')
     grupos='Grupo 1: inicio de sesion.   Grupo 2: cierre de sesion.   Grupo 3: excepciones E1 (credenciales invalidas) y E2 (cuenta desactivada). Cualquiera de los cinco actores humanos inicia este caso de uso y la colaboracion es la misma; se dibuja Cliente como representante.'
     msj=@(
       @{g=1;d='A:Cliente';a='FormularioLogin';m='enviarCredenciales(correo, contrasena)'},
       @{g=1;d='FormularioLogin';a='GestorAutenticacion';m='autenticar(credenciales)'},
       @{g=1;d='GestorAutenticacion';a='Usuario';m='buscarPorCorreo(correo)'},
       @{g=1;d='GestorAutenticacion';a='Usuario';m='verificarActivo()'},
       @{g=1;d='GestorAutenticacion';a='GestorAutenticacion';m='verificarContrasena(hash)'},
       @{g=1;d='GestorAutenticacion';a='Rol';m='obtenerRol()'},
       @{g=1;d='GestorAutenticacion';a='GestorAutenticacion';m='emitirToken(usuario, rol, sucursal)'},
       @{g=1;d='GestorAutenticacion';a='SesionToken';m='registrarSesion(jti, expiraEn)'},
       @{g=1;d='GestorAutenticacion';a='FormularioLogin';m='devolverToken(token)'},
       @{g=1;d='FormularioLogin';a='A:Cliente';m='mostrarAreaDelRol()'},
       @{g=2;d='A:Cliente';a='FormularioLogin';m='solicitarCierre()'},
       @{g=2;d='FormularioLogin';a='GestorAutenticacion';m='cerrarSesion(jti)'},
       @{g=2;d='GestorAutenticacion';a='SesionToken';m='revocar(jti)'},
       @{g=3;d='GestorAutenticacion';a='FormularioLogin';m='credencialesInvalidas()'},
       @{g=3;d='GestorAutenticacion';a='FormularioLogin';m='cuentaDesactivada()'}
     )},

  @{ n='2.2 CU-03 Gestionar usuarios y roles'
     actores=@('Administrador'); boundary='PantallaUsuarios'
     controles=@('GestorUsuarios','GestorAutenticacion')
     entidades=@('Rol','Usuario','SesionToken')
     grupos='Grupo 1: alta de usuario.   Grupo 2: flujo alternativo 3a, edicion.   Grupo 3: flujo alternativo 3b, activar o desactivar --- desactivar revoca las sesiones vigentes.   Grupo 4: excepciones E1 y E3.'
     msj=@(
       @{g=1;d='A:Administrador';a='PantallaUsuarios';m='crearUsuario(datos)'},
       @{g=1;d='PantallaUsuarios';a='GestorUsuarios';m='registrar(datos)'},
       @{g=1;d='GestorUsuarios';a='GestorAutenticacion';m='autorizar("ADMINISTRADOR")'},
       @{g=1;d='GestorUsuarios';a='GestorUsuarios';m='validarDatos(datos)'},
       @{g=1;d='GestorUsuarios';a='Usuario';m='existeCorreo(correo)'},
       @{g=1;d='GestorUsuarios';a='Rol';m='obtenerRol(rol)'},
       @{g=1;d='GestorUsuarios';a='Usuario';m='crear(usuario)'},
       @{g=1;d='GestorUsuarios';a='PantallaUsuarios';m='confirmar()'},
       @{g=2;d='A:Administrador';a='PantallaUsuarios';m='editar(id, datos)'},
       @{g=2;d='GestorUsuarios';a='Usuario';m='guardar(usuario)'},
       @{g=3;d='A:Administrador';a='PantallaUsuarios';m='desactivar(id)'},
       @{g=3;d='GestorUsuarios';a='SesionToken';m='revocarSesionesDe(usuario)'},
       @{g=4;d='GestorUsuarios';a='PantallaUsuarios';m='correoYaRegistrado()'},
       @{g=4;d='GestorUsuarios';a='PantallaUsuarios';m='noPuedeAutodesactivarse()'}
     )},

  @{ n='2.2 CU-04 Gestionar perfil del cliente'
     actores=@('Cliente'); boundary='PantallaPerfil'
     controles=@('GestorPerfil','GestorAutenticacion')
     entidades=@('Usuario','Cliente','DireccionCliente')
     grupos='Grupo 1: consulta y edicion del perfil.   Grupo 2: flujos alternativos 3a y 3b, direcciones de entrega.   Grupo 3: flujo alternativo 3c, cambio de contrasena --- es el unico que escribe en Usuario.   Grupo 4: excepcion E1.'
     msj=@(
       @{g=1;d='A:Cliente';a='PantallaPerfil';m='solicitarPerfil()'},
       @{g=1;d='PantallaPerfil';a='GestorPerfil';m='obtenerPerfil()'},
       @{g=1;d='GestorPerfil';a='GestorAutenticacion';m='autorizarPropietario()'},
       @{g=1;d='GestorPerfil';a='Cliente';m='buscarPorUsuario(idUsuario)'},
       @{g=1;d='A:Cliente';a='PantallaPerfil';m='modificar(datos)'},
       @{g=1;d='PantallaPerfil';a='GestorPerfil';m='actualizar(datos)'},
       @{g=1;d='GestorPerfil';a='GestorPerfil';m='validarDatos(datos)'},
       @{g=1;d='GestorPerfil';a='Cliente';m='guardar(cliente)'},
       @{g=2;d='GestorPerfil';a='DireccionCliente';m='agregarDireccion(datos)'},
       @{g=2;d='GestorPerfil';a='DireccionCliente';m='eliminarDireccion(id)'},
       @{g=3;d='GestorPerfil';a='Usuario';m='cambiarContrasena(actual, nueva)'},
       @{g=4;d='GestorPerfil';a='PantallaPerfil';m='contrasenaActualIncorrecta()'}
     )},

  @{ n='2.2 CU-05 Gestionar ciudades y sucursales'
     actores=@('Administrador'); boundary='PantallaSucursales'
     controles=@('GestorOrganizacion','GestorAutenticacion')
     entidades=@('Ciudad','Sucursal')
     grupos='Grupo 1: alta de sucursal.   Grupo 2: flujo alternativo 3a, gestion de ciudades.   Grupo 3: flujo alternativo 3c, baja de sucursal.   Grupo 4: excepciones E1 y E2.'
     msj=@(
       @{g=1;d='A:Administrador';a='PantallaSucursales';m='registrarSucursal(datos)'},
       @{g=1;d='PantallaSucursales';a='GestorOrganizacion';m='crearSucursal(datos)'},
       @{g=1;d='GestorOrganizacion';a='GestorAutenticacion';m='autorizar("ADMINISTRADOR")'},
       @{g=1;d='GestorOrganizacion';a='GestorOrganizacion';m='validarDatos(datos)'},
       @{g=1;d='GestorOrganizacion';a='Ciudad';m='obtenerCiudad(id)'},
       @{g=1;d='GestorOrganizacion';a='Sucursal';m='existeNombreEnCiudad(ciudad, nombre)'},
       @{g=1;d='GestorOrganizacion';a='Sucursal';m='crear(sucursal)'},
       @{g=1;d='GestorOrganizacion';a='PantallaSucursales';m='confirmar()'},
       @{g=2;d='A:Administrador';a='PantallaSucursales';m='gestionarCiudad(datos)'},
       @{g=2;d='GestorOrganizacion';a='Ciudad';m='crear(ciudad)'},
       @{g=3;d='GestorOrganizacion';a='Sucursal';m='darDeBaja(sucursal)'},
       @{g=4;d='GestorOrganizacion';a='PantallaSucursales';m='nombreDuplicadoEnLaCiudad()'},
       @{g=4;d='GestorOrganizacion';a='PantallaSucursales';m='ciudadConSucursalesActivas()'}
     )},

  @{ n='2.2 CU-06 Gestionar empleados'
     actores=@('Administrador'); boundary='PantallaEmpleados'
     controles=@('GestorEmpleados','GestorAutenticacion')
     entidades=@('Rol','Usuario','Sucursal','Empleado')
     grupos='Grupo 1: alta de empleado. CU-06 incluye a CU-03: los mensajes 1.7 a 1.9 crean el usuario y el empleado dentro de una unica transaccion.   Grupo 2: flujo alternativo 3b, baja --- desactiva tambien su usuario.   Grupo 3: excepciones E1 y E3.'
     msj=@(
       @{g=1;d='A:Administrador';a='PantallaEmpleados';m='registrarEmpleado(datos)'},
       @{g=1;d='PantallaEmpleados';a='GestorEmpleados';m='crearEmpleado(datos)'},
       @{g=1;d='GestorEmpleados';a='GestorAutenticacion';m='autorizar("ADMINISTRADOR")'},
       @{g=1;d='GestorEmpleados';a='GestorEmpleados';m='validarDatos(datos)'},
       @{g=1;d='GestorEmpleados';a='Empleado';m='existeDocumento(documento)'},
       @{g=1;d='GestorEmpleados';a='Sucursal';m='verificarActiva(sucursal)'},
       @{g=1;d='GestorEmpleados';a='Rol';m='obtenerRol(cargo)'},
       @{g=1;d='GestorEmpleados';a='Usuario';m='crear(usuario)'},
       @{g=1;d='GestorEmpleados';a='Empleado';m='crear(empleado)'},
       @{g=1;d='GestorEmpleados';a='PantallaEmpleados';m='confirmar()'},
       @{g=2;d='A:Administrador';a='PantallaEmpleados';m='darDeBaja(id)'},
       @{g=2;d='GestorEmpleados';a='Usuario';m='desactivarUsuario()'},
       @{g=3;d='GestorEmpleados';a='PantallaEmpleados';m='documentoYaRegistrado()'},
       @{g=3;d='GestorEmpleados';a='GestorEmpleados';m='revertirTransaccion()'}
     )},

  @{ n='2.2 CU-07 Gestionar proveedores'
     actores=@('Administrador','Proveedor'); boundary='PantallaProveedores'
     controles=@('GestorProveedores','GestorAutenticacion')
     entidades=@('Usuario','Proveedor')
     grupos='Grupo 1: alta de proveedor.   Grupo 2: flujos alternativos 3b y 3c, baja y habilitacion de acceso.   Grupo 3: consulta del propio Proveedor, que es su unica intervencion.   Grupo 4: excepcion E1.'
     msj=@(
       @{g=1;d='A:Administrador';a='PantallaProveedores';m='registrarProveedor(datos)'},
       @{g=1;d='PantallaProveedores';a='GestorProveedores';m='crearProveedor(datos)'},
       @{g=1;d='GestorProveedores';a='GestorAutenticacion';m='autorizar("ADMINISTRADOR")'},
       @{g=1;d='GestorProveedores';a='GestorProveedores';m='validarDatos(datos)'},
       @{g=1;d='GestorProveedores';a='Proveedor';m='existeIdentificacion(nit)'},
       @{g=1;d='GestorProveedores';a='Proveedor';m='crear(proveedor)'},
       @{g=1;d='GestorProveedores';a='PantallaProveedores';m='confirmar()'},
       @{g=2;d='GestorProveedores';a='Proveedor';m='darDeBaja(proveedor)'},
       @{g=2;d='GestorProveedores';a='Usuario';m='habilitarAcceso(proveedor)'},
       @{g=3;d='A:Proveedor';a='PantallaProveedores';m='consultarSusDatos()'},
       @{g=4;d='GestorProveedores';a='PantallaProveedores';m='identificacionDuplicada()'}
     )},

  @{ n='2.2 CU-08 Gestionar categorías, tallas y colores'
     actores=@('Administrador'); boundary='PantallaMaestrosCatalogo'
     controles=@('GestorTaxonomia','GestorAutenticacion')
     entidades=@('Categoria','Talla','Color')
     grupos='Grupo 1: categorias, el unico con jerarquia que validar.   Grupo 2: flujo alternativo 1a, tallas.   Grupo 3: flujo alternativo 1b, colores.   Grupo 4: excepciones E2 y E3.'
     msj=@(
       @{g=1;d='A:Administrador';a='PantallaMaestrosCatalogo';m='registrarCategoria(datos)'},
       @{g=1;d='PantallaMaestrosCatalogo';a='GestorTaxonomia';m='crearCategoria(datos)'},
       @{g=1;d='GestorTaxonomia';a='GestorAutenticacion';m='autorizar("ADMINISTRADOR")'},
       @{g=1;d='GestorTaxonomia';a='GestorTaxonomia';m='validarDatos(datos)'},
       @{g=1;d='GestorTaxonomia';a='Categoria';m='existeEntreHermanas(padre, nombre)'},
       @{g=1;d='GestorTaxonomia';a='Categoria';m='verificarSinCiclo(padre)'},
       @{g=1;d='GestorTaxonomia';a='Categoria';m='crear(categoria)'},
       @{g=1;d='GestorTaxonomia';a='PantallaMaestrosCatalogo';m='confirmar()'},
       @{g=2;d='A:Administrador';a='PantallaMaestrosCatalogo';m='gestionarTalla(datos)'},
       @{g=2;d='GestorTaxonomia';a='Talla';m='crear(talla)'},
       @{g=3;d='A:Administrador';a='PantallaMaestrosCatalogo';m='gestionarColor(datos)'},
       @{g=3;d='GestorTaxonomia';a='Color';m='crear(color)'},
       @{g=4;d='GestorTaxonomia';a='PantallaMaestrosCatalogo';m='cicloEnLaJerarquia()'},
       @{g=4;d='GestorTaxonomia';a='PantallaMaestrosCatalogo';m='tieneDependencias()'}
     )},

  @{ n='2.2 CU-09 Gestionar temporadas y colecciones'
     actores=@('Administrador'); boundary='PantallaTemporadas'
     controles=@('GestorTemporadas','GestorAutenticacion')
     entidades=@('Temporada','Coleccion')
     grupos='Grupo 1: alta de temporada.   Grupo 2: flujo alternativo 1a, colecciones, que dependen de una temporada existente.   Grupo 3: flujo alternativo 3b, cierre de temporada.   Grupo 4: excepciones E1 y E2.'
     msj=@(
       @{g=1;d='A:Administrador';a='PantallaTemporadas';m='registrarTemporada(datos)'},
       @{g=1;d='PantallaTemporadas';a='GestorTemporadas';m='crearTemporada(datos)'},
       @{g=1;d='GestorTemporadas';a='GestorAutenticacion';m='autorizar("ADMINISTRADOR")'},
       @{g=1;d='GestorTemporadas';a='GestorTemporadas';m='verificarRangoDeFechas(inicio, fin)'},
       @{g=1;d='GestorTemporadas';a='Temporada';m='existeNombre(nombre)'},
       @{g=1;d='GestorTemporadas';a='Temporada';m='buscarSolapamiento(inicio, fin)'},
       @{g=1;d='GestorTemporadas';a='Temporada';m='crear(temporada)'},
       @{g=1;d='GestorTemporadas';a='PantallaTemporadas';m='confirmar()'},
       @{g=2;d='A:Administrador';a='PantallaTemporadas';m='registrarColeccion(datos)'},
       @{g=2;d='GestorTemporadas';a='Coleccion';m='crear(coleccion)'},
       @{g=3;d='GestorTemporadas';a='Temporada';m='cerrarTemporada(id)'},
       @{g=4;d='GestorTemporadas';a='PantallaTemporadas';m='fechasIncoherentes()'},
       @{g=4;d='GestorTemporadas';a='PantallaTemporadas';m='solapamientoDeVigencias()'}
     )}
)

# ---------------- generacion ----------------

foreach ($caso in $casos) {
    if (Get-Diagrama $p22 $caso.n) { Write-Output "  $($caso.n) ya existe, no se toca"; continue }

    $part = @{}
    foreach ($nom in $caso.actores)   { $part["A:$nom"] = Get-Actor $nom }
    $part[$caso.boundary]             = Get-OCrearClase $pClas $caso.boundary 'boundary' $desc[$caso.boundary]
    foreach ($nom in $caso.controles) { $part[$nom] = Get-OCrearClase $pClas $nom 'control' $desc[$nom] }
    foreach ($nom in $caso.entidades) { $part[$nom] = Get-OCrearClase $pClas $nom 'entity'  $desc[$nom] }

    $d = $p22.Diagrams.AddNew($caso.n, 'Communication')
    [void]$d.Update(); $p22.Diagrams.Refresh()

    $columnas = @(
        @{ lista=@($caso.actores | ForEach-Object { "A:$_" }); x=40; ancho=100; alto=90 },
        @{ lista=@($caso.boundary); x=340; ancho=100; alto=100 },
        @{ lista=$caso.controles;   x=680; ancho=100; alto=100 },
        @{ lista=$caso.entidades;   x=1020; ancho=100; alto=100 }
    )
    foreach ($col in $columnas) {
        $paso   = $col.alto + 130
        $inicio = -220 + [int]((($col.lista.Count - 1) * $paso) / 2)
        for ($i = 0; $i -lt $col.lista.Count; $i++) {
            Poner $d $part[$col.lista[$i]] $col.x ($inicio - $i * $paso) $col.ancho $col.alto
        }
    }

    # Un enlace por par de participantes que se comunican.
    $pares = @{}
    foreach ($m in $caso.msj) {
        if ($m.d -eq $m.a) { continue }
        $c1 = $part[$m.d]; $c2 = $part[$m.a]
        $k1 = "$($c1.ElementID)-$($c2.ElementID)"; $k2 = "$($c2.ElementID)-$($c1.ElementID)"
        if ($pares.ContainsKey($k1) -or $pares.ContainsKey($k2)) { continue }
        New-Enlace $c1 $c2
        $pares[$k1] = $true
    }

    # Mensajes, con su numero de grupo y orden. El nombre no lleva numero: lo
    # pone EA a partir de PDATA4.
    $orden = @{}
    $mios  = @{}
    foreach ($m in $caso.msj) {
        $g = $m.g
        if (-not $orden.ContainsKey($g)) { $orden[$g] = 0 }
        $orden[$g] = $orden[$g] + 1
        $id = New-Mensaje $part[$m.d] $part[$m.a] $m.m
        $ea.Execute("UPDATE t_connector SET PDATA4='$g.$($orden[$g])' WHERE Connector_ID=$id")
        $mios[$id] = $true
    }

    # Nota con la leyenda de los grupos.
    $nota = $pClas.Elements.AddNew('', 'Note')
    $nota.Notes = $caso.grupos
    [void]$nota.Update()
    Poner $d $nota 340 -700 800 130

    # Las clases de analisis se comparten entre casos de uso y EA dibuja TODA
    # relacion existente entre los elementos del lienzo. Sin esto, el diagrama de
    # CU-06 mostraria tambien los mensajes de CU-02.
    $d.DiagramLinks.Refresh()
    $ajenos = 0
    foreach ($lnk in $d.DiagramLinks) {
        $con = $ea.GetConnectorByID($lnk.ConnectorID)
        $propio = $false
        if ($con.Type -eq 'Collaboration') {
            $propio = $mios.ContainsKey($con.ConnectorID)
        } elseif ($con.Type -eq 'Association') {
            $k1 = "$($con.ClientID)-$($con.SupplierID)"; $k2 = "$($con.SupplierID)-$($con.ClientID)"
            $propio = ($pares.ContainsKey($k1) -or $pares.ContainsKey($k2))
        }
        if (-not $propio) { $lnk.IsHidden = $true; [void]$lnk.Update(); $ajenos++ }
    }
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    $ng = ($caso.msj | ForEach-Object { $_.g } | Sort-Object -Unique).Count
    Write-Output ("  {0,-46} {1,2} objetos, {2,2} mensajes en {3} grupos, {4,2} ajenos ocultos" -f $caso.n, $d.DiagramObjects.Count, $caso.msj.Count, $ng, $ajenos)
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
