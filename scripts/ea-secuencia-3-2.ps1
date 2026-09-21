# =========================================================================
# CAP. 3 - 3.2 Diagramas de Secuencia: uno por caso de uso.
#
# ---- DE DONDE SALE ESTE FORMATO ----
# Del ejemplo de catedra 'CICLO 3.eapx' (CU20 - Gestionar Platos del Menu):
#   - un solo diagrama por CU, que cubre el flujo basico y los alternos;
#   - las lineas de vida son las mismas clases del diagrama de comunicacion
#     2.2 del mismo CU, ni una mas;
#   - la numeracion decimal de los mensajes se hereda tal cual del 2.2, para
#     que el lector siga el mismo mensaje en los dos capitulos;
#   - los mensajes hacia la entidad llevan el SQL literal y los de vuelta, el
#     tipo del resultado;
#   - los flujos se separan con notas rotuladas;
#   - las alternativas van en un fragmento combinado 'alt' con los operandos
#     nombrados con la guarda en espanol.
#
# ---- DOS COSAS QUE EL EJEMPLO NO HACE Y AQUI SI ----
#   1. Cada linea de vida queda ENLAZADA a su clase de 2.3 por ClassifierID.
#      Por eso el elemento va sin nombre: EA lo dibuja como ': Usuario' y el
#      vinculo queda vivo, no es texto suelto.
#   2. Los mensajes de vuelta se marcan como Return (PDATA3), asi EA los
#      dibuja con linea punteada en vez de flecha solida.
#
# ---- POR QUE HAY UNA PASADA POR OLEDB AL FINAL ----
# La API COM de EA no expone ni la posicion vertical de los mensajes de
# secuencia, ni el tipo de mensaje (llamada/retorno), ni los operandos de un
# fragmento combinado. Eso vive en t_connector.SeqNo / PtStartY / PDATA3 y en
# la fila 'Partitions' de t_xref. La segunda mitad del script los escribe
# directo sobre el .eapx, con la misma forma exacta que tiene el archivo de
# catedra.
#
# ---- SOLO SE USA 'alt' ----
# El unico operador cuyo codigo interno esta verificado contra el archivo de
# catedra es 'alt' (t_object.NType = 0). Donde el codigo tiene un bucle, un
# opcional o una seccion critica, el mensaje lleva la guarda en el nombre y
# queda anotado en docs/diagramas/secuencia-y-codigo.md, que explica cual
# operador corresponde y como cambiarlo desde la interfaz de EA.
#
# ADITIVO: abre el modelo y solo agrega los diagramas que faltan.
# =========================================================================

param(
    # Borra el paquete 3.2 entero y lo vuelve a generar. Sin este modificador
    # el script es aditivo y respeta los diagramas que ya existen.
    [switch]$Rehacer
)

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

# =========================================================================
# CONSTANTES DE DIBUJO
#
# CUIDADO: EA REMAQUETA EL DIAGRAMA ENTERO CADA VEZ QUE LO ABRE.
# No respeta las alturas que uno escriba: reordena los mensajes por SeqNo y
# los reparte con SU paso, que son 35 px arrancando en -135, dejando un hueco
# extra en cada borde de fragmento. Lo que si conserva es la caja del
# fragmento combinado. O sea que si uno escribe los mensajes con otra escala,
# al abrir el diagrama los mensajes se comprimen, la caja se queda donde
# estaba y el 'alt' termina envolviendo mensajes que no son.
#
# Por eso estas constantes replican la escala de EA: asi la remaquetacion es
# practicamente la identidad y cada operando encierra lo que le toca.
# =========================================================================
$X0        = 190    # borde izquierdo de la primera linea de vida
$GAP       = 70     # separacion horizontal entre lineas de vida
$TOP_LV    = -50    # borde superior de las lineas de vida
$Y_PRIMERO = -135   # altura del primer mensaje (la que usa EA)
$PASO      = 35     # separacion vertical entre mensajes (la que usa EA)
$ALTO_NOTA = 55     # lo que consume una nota separadora de flujo
$ALTO_ALT  = 22     # lo que consume la cabecera de un fragmento
$ALTO_OP   = 20     # lo que consume la etiqueta de un operando
$NOTA_X    = 10
$NOTA_W    = 160

# =========================================================================
# GUION DE CADA CASO DE USO
#
# lineas : de izquierda a derecha. 'actor' reutiliza el elemento del CAP. 1;
#          'clase' enlaza con la clase de 2.3 del mismo nombre.
# guion  : se lee de arriba hacia abajo y es el orden vertical del diagrama.
#          t='nota' separador | t='msg' mensaje | t='alt' abre fragmento
#          t='op' operando con su guarda | t='fin' cierra el fragmento
#          ret=$true marca el mensaje como retorno (linea punteada)
# =========================================================================

$CASOS = @(

# ---------------------------------------------------------------- CU-01 --
@{
  nombre = '3.2 CU-01 Registrar cliente'
  lineas = @(
    @{ k = 'act'; actor = 'Cliente';            w = 110 },
    @{ k = 'frm'; clase = 'FormularioRegistro'; w = 190 },
    @{ k = 'gst'; clase = 'GestorRegistro';     w = 190 },
    @{ k = 'rol'; clase = 'Rol';                w = 140 },
    @{ k = 'usu'; clase = 'Usuario';            w = 150 },
    @{ k = 'cli'; clase = 'Cliente';            w = 150 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nRegistro exitoso" },
    @{ t='msg'; o='act'; d='frm'; n='1.1: enviarDatos(nombres, apellidos, correo, contrasena)' },
    @{ t='msg'; o='frm'; d='gst'; n='1.2: registrar_cliente(db, datos)' },
    @{ t='msg'; o='gst'; d='gst'; n='1.3: validarDatos(datos)' },
    @{ t='msg'; o='gst'; d='usu'; n='1.4: SELECT id FROM usuario WHERE correo = :correo' },
    @{ t='msg'; o='usu'; d='gst'; n='1.4.1: Usuario | None'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='datos válidos' },
    @{ t='msg'; o='gst'; d='gst'; n='1.5: hash_password(contrasena)' },
    @{ t='msg'; o='gst'; d='rol'; n="1.6: SELECT id FROM rol WHERE nombre = 'CLIENTE'" },
    @{ t='msg'; o='rol'; d='gst'; n='1.6.1: Rol'; ret=$true },
    @{ t='msg'; o='gst'; d='usu'; n='1.7: INSERT INTO usuario (correo, hash_contrasena, rol_id)' },
    @{ t='msg'; o='usu'; d='gst'; n='1.7.1: Usuario (id)'; ret=$true },
    @{ t='msg'; o='gst'; d='cli'; n='1.8: INSERT INTO cliente (usuario_id, documento, telefono)' },
    @{ t='msg'; o='cli'; d='gst'; n='1.8.1: Cliente (id)'; ret=$true },
    @{ t='msg'; o='gst'; d='frm'; n='1.8.2: ClienteRegistradoOut'; ret=$true },
    @{ t='msg'; o='frm'; d='act'; n='1.9: confirmarRegistro()' },
    @{ t='op'; g='correo o documento ya registrado' },
    @{ t='msg'; o='gst'; d='gst'; n='2.2: revertirTransaccion()' },
    @{ t='msg'; o='gst'; d='frm'; n='2.1: correoYaRegistrado()' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-02 --
@{
  nombre = '3.2 CU-02 Iniciar y cerrar sesión'
  lineas = @(
    @{ k = 'act'; actor = 'Cliente';             w = 110 },
    @{ k = 'frm'; clase = 'FormularioLogin';     w = 180 },
    @{ k = 'gau'; clase = 'GestorAutenticacion'; w = 210 },
    @{ k = 'usu'; clase = 'Usuario';             w = 150 },
    @{ k = 'rol'; clase = 'Rol';                 w = 140 },
    @{ k = 'ses'; clase = 'SesionToken';         w = 170 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nInicio de sesión" },
    @{ t='msg'; o='act'; d='frm'; n='1.1: enviarCredenciales(correo, contrasena)' },
    @{ t='msg'; o='frm'; d='gau'; n='1.2: autenticar(db, datos)' },
    @{ t='msg'; o='gau'; d='usu'; n='1.3: SELECT u.*, r.nombre FROM usuario u JOIN rol r WHERE u.correo = :correo' },
    @{ t='msg'; o='usu'; d='gau'; n='1.3.1: Usuario | None'; ret=$true },
    @{ t='msg'; o='gau'; d='gau'; n='1.5: verify_password(contrasena, hash_contrasena)' },
    @{ t='msg'; o='gau'; d='gau'; n='1.4: verificarActivo(usuario)' },
    @{ t='alt' },
    @{ t='op'; g='credenciales válidas y cuenta activa' },
    @{ t='msg'; o='gau'; d='rol'; n='1.6: SELECT nombre FROM rol WHERE id = :rol_id' },
    @{ t='msg'; o='rol'; d='gau'; n='1.6.1: Rol'; ret=$true },
    @{ t='msg'; o='gau'; d='gau'; n='1.7: crear_access_token(usuario_id, rol, sucursal_id)' },
    @{ t='msg'; o='gau'; d='ses'; n='1.8: INSERT INTO sesion_token (usuario_id, jti, expira_en)' },
    @{ t='msg'; o='ses'; d='gau'; n='1.8.1: SesionToken'; ret=$true },
    @{ t='msg'; o='gau'; d='frm'; n='1.9: TokenOut(access_token, expira_en, usuario)'; ret=$true },
    @{ t='msg'; o='frm'; d='act'; n='1.10: mostrarAreaDelRol()' },
    @{ t='op'; g='credenciales inválidas' },
    @{ t='msg'; o='gau'; d='frm'; n='3.1: credencialesInvalidas() -> 401' },
    @{ t='op'; g='cuenta desactivada' },
    @{ t='msg'; o='gau'; d='frm'; n='3.2: cuentaDesactivada() -> 403' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 2`nCierre de sesión" },
    @{ t='msg'; o='act'; d='frm'; n='2.1: solicitarCierre()' },
    @{ t='msg'; o='frm'; d='gau'; n='2.2: cerrar_sesion(db, jti)' },
    @{ t='msg'; o='gau'; d='ses'; n='2.3: UPDATE sesion_token SET revocado_en = now() WHERE jti = :jti' },
    @{ t='msg'; o='ses'; d='gau'; n='2.3.1: filas revocadas: int'; ret=$true }
  )
},

# ---------------------------------------------------------------- CU-03 --
@{
  nombre = '3.2 CU-03 Gestionar usuarios y roles'
  lineas = @(
    @{ k = 'act'; actor = 'Administrador';       w = 130 },
    @{ k = 'pus'; clase = 'PantallaUsuarios';    w = 190 },
    @{ k = 'gus'; clase = 'GestorUsuarios';      w = 190 },
    @{ k = 'gau'; clase = 'GestorAutenticacion'; w = 210 },
    @{ k = 'usu'; clase = 'Usuario';             w = 150 },
    @{ k = 'rol'; clase = 'Rol';                 w = 140 },
    @{ k = 'ses'; clase = 'SesionToken';         w = 170 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nAlta de usuario" },
    @{ t='msg'; o='act'; d='pus'; n='1.1: crearUsuario(datos)' },
    @{ t='msg'; o='pus'; d='gus'; n='1.2: crear_usuario(db, datos)' },
    @{ t='msg'; o='gus'; d='gau'; n='1.3: requiere_roles("ADMINISTRADOR")' },
    @{ t='msg'; o='gus'; d='gus'; n='1.4: validarDatos(datos)' },
    @{ t='msg'; o='gus'; d='usu'; n='1.5: SELECT id FROM usuario WHERE correo = :correo' },
    @{ t='msg'; o='usu'; d='gus'; n='1.5.1: Usuario | None'; ret=$true },
    @{ t='msg'; o='gus'; d='rol'; n='1.6: SELECT id FROM rol WHERE nombre = :rol' },
    @{ t='msg'; o='rol'; d='gus'; n='1.6.1: Rol | None'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='correo libre y rol existente' },
    @{ t='msg'; o='gus'; d='usu'; n='1.7: INSERT INTO usuario (correo, hash_contrasena, rol_id)' },
    @{ t='msg'; o='usu'; d='gus'; n='1.7.1: Usuario (id)'; ret=$true },
    @{ t='msg'; o='gus'; d='pus'; n='1.8: UsuarioResumenOut'; ret=$true },
    @{ t='op'; g='correo ya registrado' },
    @{ t='msg'; o='gus'; d='pus'; n='4.1: correoYaRegistrado() -> 409' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 2`nEdición de usuario" },
    @{ t='msg'; o='act'; d='pus'; n='2.1: editar(id, datos)' },
    @{ t='msg'; o='gus'; d='usu'; n='2.2: UPDATE usuario SET nombres, apellidos, rol_id WHERE id = :id' },
    @{ t='msg'; o='usu'; d='gus'; n='2.2.1: Usuario'; ret=$true },
    @{ t='nota'; txt = "FLUJO 3`nDesactivación" },
    @{ t='msg'; o='act'; d='pus'; n='3.1: desactivar(id)' },
    @{ t='alt' },
    @{ t='op'; g='no es su propia cuenta' },
    @{ t='msg'; o='gus'; d='usu'; n='3.1.1: UPDATE usuario SET activo = false WHERE id = :id' },
    @{ t='msg'; o='gus'; d='ses'; n='3.2: UPDATE sesion_token SET revocado_en = now() WHERE usuario_id = :id' },
    @{ t='msg'; o='ses'; d='gus'; n='3.2.1: sesiones revocadas: int'; ret=$true },
    @{ t='op'; g='intenta desactivarse a sí mismo' },
    @{ t='msg'; o='gus'; d='pus'; n='4.2: noPuedeAutodesactivarse() -> 409' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-04 --
@{
  nombre = '3.2 CU-04 Gestionar perfil del cliente'
  lineas = @(
    @{ k = 'act'; actor = 'Cliente';             w = 110 },
    @{ k = 'ppe'; clase = 'PantallaPerfil';      w = 180 },
    @{ k = 'gpe'; clase = 'GestorPerfil';        w = 180 },
    @{ k = 'gau'; clase = 'GestorAutenticacion'; w = 210 },
    @{ k = 'cli'; clase = 'Cliente';             w = 150 },
    @{ k = 'dir'; clase = 'DireccionCliente';    w = 200 },
    @{ k = 'usu'; clase = 'Usuario';             w = 150 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nConsulta y edición del perfil" },
    @{ t='msg'; o='act'; d='ppe'; n='1.1: solicitarPerfil()' },
    @{ t='msg'; o='ppe'; d='gpe'; n='1.2: obtener_perfil(db, usuario_id)' },
    @{ t='msg'; o='gpe'; d='gau'; n='1.3: get_usuario_actual(token)' },
    @{ t='msg'; o='gpe'; d='cli'; n='1.4: SELECT * FROM cliente WHERE usuario_id = :id' },
    @{ t='msg'; o='cli'; d='gpe'; n='1.4.1: Cliente'; ret=$true },
    @{ t='msg'; o='gpe'; d='dir'; n='1.4.2: SELECT * FROM direccion_cliente WHERE cliente_id = :id' },
    @{ t='msg'; o='dir'; d='gpe'; n='1.4.3: list[DireccionCliente]'; ret=$true },
    @{ t='msg'; o='gpe'; d='ppe'; n='1.4.4: PerfilOut'; ret=$true },
    @{ t='msg'; o='act'; d='ppe'; n='1.5: modificar(datos)' },
    @{ t='msg'; o='ppe'; d='gpe'; n='1.6: editar_perfil(db, usuario_id, datos)' },
    @{ t='msg'; o='gpe'; d='gpe'; n='1.7: validarDatos(datos)' },
    @{ t='msg'; o='gpe'; d='cli'; n='1.8: UPDATE cliente SET telefono, talla_superior, talla_inferior WHERE id = :id' },
    @{ t='msg'; o='cli'; d='gpe'; n='1.8.1: Cliente'; ret=$true },
    @{ t='nota'; txt = "FLUJO 2`nLibreta de direcciones" },
    @{ t='msg'; o='gpe'; d='dir'; n='2.1a: [si queda predeterminada] UPDATE direccion_cliente SET predeterminada = false WHERE cliente_id = :id' },
    @{ t='msg'; o='gpe'; d='dir'; n='2.1b: INSERT INTO direccion_cliente (cliente_id, ciudad_id, alias, direccion)' },
    @{ t='msg'; o='dir'; d='gpe'; n='2.1c: DireccionCliente'; ret=$true },
    @{ t='msg'; o='gpe'; d='dir'; n='2.2: DELETE FROM direccion_cliente WHERE id = :id AND cliente_id = :cliente' },
    @{ t='nota'; txt = "FLUJO 3`nCambio de contraseña" },
    @{ t='msg'; o='act'; d='ppe'; n='3.1: cambiarContrasena(actual, nueva)' },
    @{ t='msg'; o='ppe'; d='gpe'; n='3.1.1: cambiar_contrasena(db, usuario_id, datos)' },
    @{ t='msg'; o='gpe'; d='gpe'; n='3.1.2: verify_password(actual, hash_contrasena)' },
    @{ t='alt' },
    @{ t='op'; g='contraseña actual correcta' },
    @{ t='msg'; o='gpe'; d='usu'; n='3.1.3: UPDATE usuario SET hash_contrasena = :hash WHERE id = :id' },
    @{ t='msg'; o='usu'; d='gpe'; n='3.1.4: Usuario'; ret=$true },
    @{ t='op'; g='contraseña actual incorrecta' },
    @{ t='msg'; o='gpe'; d='ppe'; n='4.1: contrasenaActualIncorrecta() -> 400' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-05 --
@{
  nombre = '3.2 CU-05 Gestionar ciudades y sucursales'
  lineas = @(
    @{ k = 'act'; actor = 'Administrador';        w = 130 },
    @{ k = 'psu'; clase = 'PantallaSucursales';   w = 200 },
    @{ k = 'gor'; clase = 'GestorOrganizacion';   w = 210 },
    @{ k = 'gau'; clase = 'GestorAutenticacion';  w = 210 },
    @{ k = 'ciu'; clase = 'Ciudad';               w = 140 },
    @{ k = 'suc'; clase = 'Sucursal';             w = 150 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nAlta de sucursal" },
    @{ t='msg'; o='act'; d='psu'; n='1.1: registrarSucursal(datos)' },
    @{ t='msg'; o='psu'; d='gor'; n='1.2: crear_sucursal(db, datos)' },
    @{ t='msg'; o='gor'; d='gau'; n='1.3: requiere_roles("ADMINISTRADOR")' },
    @{ t='msg'; o='gor'; d='gor'; n='1.4: validarDatos(datos)' },
    @{ t='msg'; o='gor'; d='ciu'; n='1.5: SELECT id FROM ciudad WHERE id = :ciudad_id' },
    @{ t='msg'; o='ciu'; d='gor'; n='1.5.1: Ciudad | None'; ret=$true },
    @{ t='msg'; o='gor'; d='suc'; n='1.6: SELECT 1 FROM sucursal WHERE ciudad_id = :c AND nombre = :n' },
    @{ t='msg'; o='suc'; d='gor'; n='1.6.1: bool'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='nombre libre en la ciudad' },
    @{ t='msg'; o='gor'; d='suc'; n='1.7: INSERT INTO sucursal (ciudad_id, nombre, direccion, horarios, capacidad)' },
    @{ t='msg'; o='suc'; d='gor'; n='1.7.1: Sucursal (id)'; ret=$true },
    @{ t='msg'; o='gor'; d='psu'; n='1.8: SucursalOut'; ret=$true },
    @{ t='op'; g='nombre duplicado en la ciudad' },
    @{ t='msg'; o='gor'; d='psu'; n='4.1: nombreDuplicadoEnLaCiudad() -> 409' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 2`nAlta de ciudad" },
    @{ t='msg'; o='act'; d='psu'; n='2.1: gestionarCiudad(datos)' },
    @{ t='msg'; o='gor'; d='ciu'; n='2.2: INSERT INTO ciudad (nombre, departamento)' },
    @{ t='msg'; o='ciu'; d='gor'; n='2.2.1: Ciudad (id)'; ret=$true },
    @{ t='nota'; txt = "FLUJO 3`nBaja de sucursal y de ciudad" },
    @{ t='msg'; o='gor'; d='suc'; n='3.1: UPDATE sucursal SET activa = false WHERE id = :id' },
    @{ t='msg'; o='suc'; d='gor'; n='3.1.1: Sucursal'; ret=$true },
    @{ t='msg'; o='gor'; d='ciu'; n='3.1.2: SELECT count(*) FROM sucursal WHERE ciudad_id = :id' },
    @{ t='msg'; o='ciu'; d='gor'; n='3.1.3: (total, activas)'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='la ciudad no tiene sucursales' },
    @{ t='msg'; o='gor'; d='ciu'; n='3.2: DELETE FROM ciudad WHERE id = :id' },
    @{ t='op'; g='la ciudad tiene sucursales activas' },
    @{ t='msg'; o='gor'; d='psu'; n='4.2: ciudadConSucursalesActivas() -> 409' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-06 --
@{
  nombre = '3.2 CU-06 Gestionar empleados'
  lineas = @(
    @{ k = 'act'; actor = 'Administrador';       w = 130 },
    @{ k = 'pem'; clase = 'PantallaEmpleados';   w = 200 },
    @{ k = 'gem'; clase = 'GestorEmpleados';     w = 200 },
    @{ k = 'gau'; clase = 'GestorAutenticacion'; w = 210 },
    @{ k = 'emp'; clase = 'Empleado';            w = 150 },
    @{ k = 'suc'; clase = 'Sucursal';            w = 150 },
    @{ k = 'rol'; clase = 'Rol';                 w = 140 },
    @{ k = 'usu'; clase = 'Usuario';             w = 150 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nAlta de empleado" },
    @{ t='msg'; o='act'; d='pem'; n='1.1: registrarEmpleado(datos)' },
    @{ t='msg'; o='pem'; d='gem'; n='1.2: crear_empleado(db, datos)' },
    @{ t='msg'; o='gem'; d='gau'; n='1.3: requiere_roles("ADMINISTRADOR")' },
    @{ t='msg'; o='gem'; d='gem'; n='1.4: validarDatos(datos)' },
    @{ t='msg'; o='gem'; d='emp'; n='1.5: SELECT 1 FROM empleado WHERE documento = :documento' },
    @{ t='msg'; o='emp'; d='gem'; n='1.5.1: bool'; ret=$true },
    @{ t='msg'; o='gem'; d='suc'; n='1.6: SELECT id FROM sucursal WHERE id = :id AND activa = true' },
    @{ t='msg'; o='suc'; d='gem'; n='1.6.1: Sucursal | None'; ret=$true },
    @{ t='msg'; o='gem'; d='rol'; n='1.7: SELECT id FROM rol WHERE nombre = ROL_DE_CARGO[cargo]' },
    @{ t='msg'; o='rol'; d='gem'; n='1.7.1: Rol'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='vincula un usuario existente' },
    @{ t='msg'; o='gem'; d='usu'; n='1.8a: UPDATE usuario SET rol_id = :rol WHERE id = :usuario_id' },
    @{ t='op'; g='crea una cuenta nueva' },
    @{ t='msg'; o='gem'; d='usu'; n='1.8b: INSERT INTO usuario (correo, hash_contrasena, rol_id)' },
    @{ t='fin' },
    @{ t='msg'; o='usu'; d='gem'; n='1.8.1: Usuario (id)'; ret=$true },
    @{ t='msg'; o='gem'; d='emp'; n='1.9: INSERT INTO empleado (usuario_id, sucursal_id, documento, cargo)' },
    @{ t='msg'; o='emp'; d='gem'; n='1.9.1: Empleado (id)'; ret=$true },
    @{ t='msg'; o='gem'; d='pem'; n='1.10: EmpleadoOut'; ret=$true },
    @{ t='nota'; txt = "FLUJO 2`nBaja de empleado" },
    @{ t='msg'; o='act'; d='pem'; n='2.1: darDeBaja(id)' },
    @{ t='msg'; o='gem'; d='emp'; n='2.2: UPDATE empleado SET fecha_baja = :fecha WHERE id = :id' },
    @{ t='msg'; o='gem'; d='usu'; n='2.2.1: UPDATE usuario SET activo = false WHERE id = :usuario_id' },
    @{ t='nota'; txt = "FLUJO 3`nDocumento ya registrado" },
    @{ t='msg'; o='gem'; d='gem'; n='3.2: revertirTransaccion()' },
    @{ t='msg'; o='gem'; d='pem'; n='3.1: documentoYaRegistrado() -> 409' }
  )
},

# ---------------------------------------------------------------- CU-07 --
@{
  nombre = '3.2 CU-07 Gestionar proveedores'
  lineas = @(
    @{ k = 'act'; actor = 'Administrador';        w = 130 },
    @{ k = 'apr'; actor = 'Proveedor';            w = 120 },
    @{ k = 'ppr'; clase = 'PantallaProveedores';  w = 210 },
    @{ k = 'gpr'; clase = 'GestorProveedores';    w = 200 },
    @{ k = 'gau'; clase = 'GestorAutenticacion';  w = 210 },
    @{ k = 'pro'; clase = 'Proveedor';            w = 160 },
    @{ k = 'usu'; clase = 'Usuario';              w = 150 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nAlta de proveedor" },
    @{ t='msg'; o='act'; d='ppr'; n='1.1: registrarProveedor(datos)' },
    @{ t='msg'; o='ppr'; d='gpr'; n='1.2: crear(db, datos)' },
    @{ t='msg'; o='gpr'; d='gau'; n='1.3: requiere_roles("ADMINISTRADOR")' },
    @{ t='msg'; o='gpr'; d='gpr'; n='1.4: validarDatos(datos)' },
    @{ t='msg'; o='gpr'; d='pro'; n='1.5: SELECT 1 FROM proveedor WHERE identificacion_tributaria = :nit' },
    @{ t='msg'; o='pro'; d='gpr'; n='1.5.1: bool'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='identificación tributaria libre' },
    @{ t='msg'; o='gpr'; d='pro'; n='1.6: INSERT INTO proveedor (razon_social, identificacion_tributaria, contacto)' },
    @{ t='msg'; o='pro'; d='gpr'; n='1.6.1: Proveedor (id)'; ret=$true },
    @{ t='msg'; o='gpr'; d='ppr'; n='1.7: ProveedorOut'; ret=$true },
    @{ t='op'; g='identificación duplicada' },
    @{ t='msg'; o='gpr'; d='ppr'; n='4.1: identificacionDuplicada() -> 409' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 2`nBaja y habilitación de acceso" },
    @{ t='msg'; o='gpr'; d='pro'; n='2.1: UPDATE proveedor SET activo = false WHERE id = :id' },
    @{ t='msg'; o='gpr'; d='usu'; n="2.2: INSERT INTO usuario (correo, hash_contrasena, rol_id = 'PROVEEDOR')" },
    @{ t='msg'; o='usu'; d='gpr'; n='2.2.1: Usuario (id)'; ret=$true },
    @{ t='msg'; o='gpr'; d='pro'; n='2.2.2: UPDATE proveedor SET usuario_id = :id WHERE id = :proveedor' },
    @{ t='nota'; txt = "FLUJO 3`nEl proveedor consulta su ficha" },
    @{ t='msg'; o='apr'; d='ppr'; n='3.1: consultarSusDatos()' },
    @{ t='msg'; o='ppr'; d='gpr'; n='3.1.1: obtener_mi_ficha(db, usuario_id)' },
    @{ t='msg'; o='gpr'; d='pro'; n='3.1.2: SELECT * FROM proveedor WHERE usuario_id = :id' },
    @{ t='msg'; o='pro'; d='gpr'; n='3.1.3: Proveedor'; ret=$true },
    @{ t='msg'; o='gpr'; d='ppr'; n='3.1.4: ProveedorOut'; ret=$true }
  )
},

# ---------------------------------------------------------------- CU-08 --
@{
  nombre = '3.2 CU-08 Gestionar categorías, tallas y colores'
  lineas = @(
    @{ k = 'act'; actor = 'Administrador';              w = 130 },
    @{ k = 'pma'; clase = 'PantallaMaestrosCatalogo';   w = 240 },
    @{ k = 'gta'; clase = 'GestorTaxonomia';            w = 190 },
    @{ k = 'gau'; clase = 'GestorAutenticacion';        w = 210 },
    @{ k = 'cat'; clase = 'Categoria';                  w = 150 },
    @{ k = 'tal'; clase = 'Talla';                      w = 140 },
    @{ k = 'col'; clase = 'Color';                      w = 140 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nAlta de categoría" },
    @{ t='msg'; o='act'; d='pma'; n='1.1: registrarCategoria(datos)' },
    @{ t='msg'; o='pma'; d='gta'; n='1.2: crear_categoria(db, datos)' },
    @{ t='msg'; o='gta'; d='gau'; n='1.3: requiere_roles("ADMINISTRADOR")' },
    @{ t='msg'; o='gta'; d='gta'; n='1.4: validarDatos(datos)' },
    @{ t='msg'; o='gta'; d='cat'; n='1.5: SELECT 1 FROM categoria WHERE categoria_padre_id = :p AND nombre = :n' },
    @{ t='msg'; o='cat'; d='gta'; n='1.5.1: bool'; ret=$true },
    @{ t='msg'; o='gta'; d='cat'; n='1.6: WITH RECURSIVE descendientes AS (...) SELECT id' },
    @{ t='msg'; o='cat'; d='gta'; n='1.6.1: set[int]'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='nombre libre entre hermanas y sin ciclo' },
    @{ t='msg'; o='gta'; d='cat'; n='1.7: INSERT INTO categoria (categoria_padre_id, nombre, orden)' },
    @{ t='msg'; o='cat'; d='gta'; n='1.7.1: Categoria (id)'; ret=$true },
    @{ t='msg'; o='gta'; d='pma'; n='1.8: CategoriaOut'; ret=$true },
    @{ t='op'; g='el padre elegido es descendiente' },
    @{ t='msg'; o='gta'; d='pma'; n='4.1: cicloEnLaJerarquia() -> 409' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 2`nTallas" },
    @{ t='msg'; o='act'; d='pma'; n='2.1: gestionarTalla(datos)' },
    @{ t='msg'; o='gta'; d='tal'; n='2.2: INSERT INTO talla (tipo_prenda, codigo, orden)' },
    @{ t='msg'; o='tal'; d='gta'; n='2.2.1: Talla (id)'; ret=$true },
    @{ t='nota'; txt = "FLUJO 3`nColores" },
    @{ t='msg'; o='act'; d='pma'; n='3.1: gestionarColor(datos)' },
    @{ t='msg'; o='gta'; d='col'; n='3.2: INSERT INTO color (nombre, hexadecimal)' },
    @{ t='msg'; o='col'; d='gta'; n='3.2.1: Color (id)'; ret=$true },
    @{ t='nota'; txt = "FLUJO 4`nEliminación de categoría" },
    @{ t='msg'; o='gta'; d='cat'; n='4.2a: SELECT count(*) FROM categoria WHERE categoria_padre_id = :id' },
    @{ t='msg'; o='cat'; d='gta'; n='4.2b: int'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='sin subcategorías' },
    @{ t='msg'; o='gta'; d='cat'; n='4.2c: DELETE FROM categoria WHERE id = :id' },
    @{ t='op'; g='tiene subcategorías' },
    @{ t='msg'; o='gta'; d='pma'; n='4.2: tieneDependencias() -> 409' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-09 --
@{
  nombre = '3.2 CU-09 Gestionar temporadas y colecciones'
  lineas = @(
    @{ k = 'act'; actor = 'Administrador';       w = 130 },
    @{ k = 'pte'; clase = 'PantallaTemporadas';  w = 200 },
    @{ k = 'gte'; clase = 'GestorTemporadas';    w = 200 },
    @{ k = 'gau'; clase = 'GestorAutenticacion'; w = 210 },
    @{ k = 'tem'; clase = 'Temporada';           w = 160 },
    @{ k = 'cle'; clase = 'Coleccion';           w = 160 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nAlta de temporada" },
    @{ t='msg'; o='act'; d='pte'; n='1.1: registrarTemporada(datos)' },
    @{ t='msg'; o='pte'; d='gte'; n='1.2: crear_temporada(db, datos)' },
    @{ t='msg'; o='gte'; d='gau'; n='1.3: requiere_roles("ADMINISTRADOR")' },
    @{ t='msg'; o='gte'; d='gte'; n='1.4: verificarRangoDeFechas(inicio, fin)' },
    @{ t='msg'; o='gte'; d='tem'; n='1.5: SELECT id FROM temporada WHERE nombre = :nombre' },
    @{ t='msg'; o='tem'; d='gte'; n='1.5.1: Temporada | None'; ret=$true },
    @{ t='msg'; o='gte'; d='tem'; n='1.6: SELECT * FROM temporada WHERE activa AND fecha_inicio <= :fin AND fecha_fin >= :inicio' },
    @{ t='msg'; o='tem'; d='gte'; n='1.6.1: list[Temporada]'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='nombre libre y sin solapamiento' },
    @{ t='msg'; o='gte'; d='tem'; n='1.7: INSERT INTO temporada (nombre, fecha_inicio, fecha_fin, activa)' },
    @{ t='msg'; o='tem'; d='gte'; n='1.7.1: Temporada (id)'; ret=$true },
    @{ t='msg'; o='gte'; d='pte'; n='1.8: TemporadaOut'; ret=$true },
    @{ t='op'; g='fechas incoherentes' },
    @{ t='msg'; o='gte'; d='pte'; n='4.1: fechasIncoherentes() -> 422' },
    @{ t='op'; g='se cruza con otra temporada activa' },
    @{ t='msg'; o='gte'; d='pte'; n='4.2: solapamientoDeVigencias() -> 409' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 2`nAlta de colección" },
    @{ t='msg'; o='act'; d='pte'; n='2.1: registrarColeccion(datos)' },
    @{ t='msg'; o='gte'; d='cle'; n='2.2: INSERT INTO coleccion (temporada_id, nombre, descripcion)' },
    @{ t='msg'; o='cle'; d='gte'; n='2.2.1: Coleccion (id)'; ret=$true },
    @{ t='nota'; txt = "FLUJO 3`nCierre de temporada" },
    @{ t='msg'; o='gte'; d='tem'; n='3.1: UPDATE temporada SET activa = false WHERE id = :id' },
    @{ t='msg'; o='tem'; d='gte'; n='3.1.1: Temporada'; ret=$true }
  )
}

,

# =========================================================================
# CICLO 2 --- los trece casos de uso del nucleo del negocio.
#
# Las lineas de vida son las clases de 2.3 del mismo caso de uso, y la
# numeracion se hereda tal cual del diagrama de comunicacion 2.2, para que el
# mismo mensaje se siga en los dos capitulos. Los retornos, que el 2.2 no
# tiene, van como sub-nivel del mensaje que los provoca (1.7 -> 1.7.1) para no
# desplazar la numeracion original.
# =========================================================================

# ---------------------------------------------------------------- CU-10 --
@{
  nombre = '3.2 CU-10 Gestionar productos y variantes'
  lineas = @(
    @{ k = 'act'; actor = 'Administrador';       w = 130 },
    @{ k = 'pan'; clase = 'PantallaProductos';   w = 190 },
    @{ k = 'gst'; clase = 'GestorProductos';     w = 190 },
    @{ k = 'aut'; clase = 'GestorAutenticacion'; w = 190 },
    @{ k = 'pro'; clase = 'Producto';            w = 150 },
    @{ k = 'var'; clase = 'VarianteProducto';    w = 180 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nAlta de producto`ny sus variantes" },
    @{ t='msg'; o='act'; d='pan'; n='1.1: registrarProducto(datos)' },
    @{ t='msg'; o='pan'; d='gst'; n='1.2: crear_producto(db, datos)' },
    @{ t='msg'; o='gst'; d='aut'; n='1.3: autorizar("ADMINISTRADOR")' },
    @{ t='msg'; o='gst'; d='gst'; n='1.4: _validar_maestros(db, datos)' },
    @{ t='msg'; o='gst'; d='pro'; n='1.5: SELECT id FROM producto WHERE codigo = :codigo' },
    @{ t='msg'; o='pro'; d='gst'; n='1.5.1: bool'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='código libre y colección de la temporada' },
    @{ t='msg'; o='gst'; d='pro'; n='1.6: INSERT INTO producto (codigo, nombre, categoria_id, precio_base)' },
    @{ t='msg'; o='pro'; d='gst'; n='1.6.1: Producto (id)'; ret=$true },
    @{ t='msg'; o='act'; d='pan'; n='1.7: generarVariantes(tallas, colores)' },
    @{ t='msg'; o='pan'; d='gst'; n='1.8: generar_variantes(db, producto_id, tallas, colores)' },
    @{ t='msg'; o='gst'; d='var'; n='1.9: SELECT talla_id, color_id FROM variante_producto WHERE producto_id = :id' },
    @{ t='msg'; o='var'; d='gst'; n='1.9.1: list[tuple[int, int]]'; ret=$true },
    @{ t='msg'; o='gst'; d='gst'; n='1.10: armar_sku(producto, talla, color)' },
    @{ t='msg'; o='gst'; d='var'; n='1.11: INSERT INTO variante_producto (producto_id, talla_id, color_id, sku, precio)' },
    @{ t='msg'; o='var'; d='gst'; n='1.11.1: VarianteProducto (id)'; ret=$true },
    @{ t='msg'; o='gst'; d='pan'; n='1.11.2: ProductoOut'; ret=$true },
    @{ t='op'; g='código duplicado o colección ajena' },
    @{ t='msg'; o='gst'; d='pan'; n='4.1: codigoDuplicado() -> 409' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-11 --
@{
  nombre = '3.2 CU-11 Gestionar imágenes de producto'
  lineas = @(
    @{ k = 'act'; actor = 'Administrador';       w = 130 },
    @{ k = 'pan'; clase = 'PantallaImagenes';    w = 190 },
    @{ k = 'gst'; clase = 'GestorImagenes';      w = 190 },
    @{ k = 'aut'; clase = 'GestorAutenticacion'; w = 190 },
    @{ k = 'img'; clase = 'ImagenProducto';      w = 170 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nCarga de una imagen" },
    @{ t='msg'; o='act'; d='pan'; n='1.1: subirImagen(producto_id, archivo)' },
    @{ t='msg'; o='pan'; d='gst'; n='1.2: subir(db, producto_id, archivo)' },
    @{ t='msg'; o='gst'; d='aut'; n='1.3: autorizar("ADMINISTRADOR")' },
    @{ t='msg'; o='gst'; d='gst'; n='1.4: _asegurar_producto(db, producto_id)' },
    @{ t='alt' },
    @{ t='op'; g='formato e imagen válidos' },
    @{ t='msg'; o='gst'; d='img'; n='1.5: SELECT MAX(orden) FROM imagen_producto WHERE producto_id = :id' },
    @{ t='msg'; o='img'; d='gst'; n='1.5.1: int'; ret=$true },
    @{ t='msg'; o='gst'; d='img'; n='1.6: INSERT INTO imagen_producto (producto_id, ruta, es_principal, orden)' },
    @{ t='msg'; o='img'; d='gst'; n='1.6.1: ImagenProducto (id)'; ret=$true },
    @{ t='msg'; o='gst'; d='pan'; n='1.6.2: ImagenOut'; ret=$true },
    @{ t='nota'; txt = "FLUJO 3`nMarcado para`nel vestidor virtual" },
    @{ t='msg'; o='act'; d='pan'; n='3.1: marcarTransparente(imagen_id)' },
    @{ t='msg'; o='pan'; d='gst'; n='3.2: marcar_transparente(db, imagen_id)' },
    @{ t='msg'; o='gst'; d='gst'; n='3.3: _archivo_tiene_transparencia(ruta)' },
    @{ t='msg'; o='gst'; d='img'; n='3.4: UPDATE imagen_producto SET es_transparente = false WHERE variante_id = :v' },
    @{ t='msg'; o='gst'; d='img'; n='3.5: UPDATE imagen_producto SET es_transparente = true WHERE id = :id' },
    @{ t='op'; g='formato no admitido o PNG sin alfa' },
    @{ t='msg'; o='gst'; d='pan'; n='5.1: formatoNoAdmitido() -> 422' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-13 --
@{
  nombre = '3.2 CU-13 Registrar ingreso de mercadería'
  lineas = @(
    @{ k = 'act'; actor = 'Encargado de Sucursal'; w = 160 },
    @{ k = 'pan'; clase = 'PantallaInventario';    w = 190 },
    @{ k = 'gst'; clase = 'GestorInventario';      w = 190 },
    @{ k = 'aut'; clase = 'GestorAutenticacion';   w = 190 },
    @{ k = 'exi'; clase = 'Existencia';            w = 150 },
    @{ k = 'mov'; clase = 'MovimientoInventario';  w = 200 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nRemito completo,`nen una transacción" },
    @{ t='msg'; o='act'; d='pan'; n='1.1: registrarIngreso(remito)' },
    @{ t='msg'; o='pan'; d='gst'; n='1.2: registrar_ingreso(db, datos, usuario_id)' },
    @{ t='msg'; o='gst'; d='aut'; n='1.3: autorizar("ADMINISTRADOR", "ENCARGADO")' },
    @{ t='msg'; o='gst'; d='gst'; n='1.4: _sucursal_activa(db, sucursal_id)' },
    @{ t='msg'; o='gst'; d='gst'; n='1.5: _variantes_validas(db, lineas)' },
    @{ t='msg'; o='gst'; d='exi'; n='1.6: SELECT * FROM existencia WHERE variante_id = :v AND sucursal_id = :s' },
    @{ t='msg'; o='exi'; d='gst'; n='1.6.1: Existencia | None'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='remito válido' },
    @{ t='msg'; o='gst'; d='exi'; n='1.7: INSERT INTO existencia (variante_id, sucursal_id) -- si no existía' },
    @{ t='msg'; o='gst'; d='gst'; n='1.8: _aplicar_movimiento(existencia, INGRESO, cantidad)' },
    @{ t='msg'; o='gst'; d='exi'; n='1.9: UPDATE existencia SET cantidad_disponible = cantidad_disponible + :n' },
    @{ t='msg'; o='gst'; d='mov'; n='1.10: INSERT INTO movimiento_inventario (existencia_id, tipo, cantidad, referencia)' },
    @{ t='msg'; o='mov'; d='gst'; n='1.10.1: MovimientoInventario (id)'; ret=$true },
    @{ t='msg'; o='gst'; d='pan'; n='1.10.2: IngresoOut (saldos resultantes)'; ret=$true },
    @{ t='op'; g='sucursal inactiva o prenda desactivada' },
    @{ t='msg'; o='gst'; d='gst'; n='4.1: revertirTransaccion() -- ninguna línea queda escrita' },
    @{ t='msg'; o='gst'; d='pan'; n='4.2: sucursalInactiva() -> 422' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-14 --
@{
  nombre = '3.2 CU-14 Consultar inventario consolidado'
  lineas = @(
    @{ k = 'act'; actor = 'Administrador';        w = 130 },
    @{ k = 'pan'; clase = 'PantallaConsolidado';  w = 200 },
    @{ k = 'gst'; clase = 'GestorConsolidado';    w = 200 },
    @{ k = 'aut'; clase = 'GestorAutenticacion';  w = 190 },
    @{ k = 'exi'; clase = 'Existencia';           w = 150 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nConsulta consolidada`nde toda la red" },
    @{ t='msg'; o='act'; d='pan'; n='1.1: consultar(filtros)' },
    @{ t='msg'; o='pan'; d='gst'; n='1.2: consultar(db, pagina, tamano, filtros)' },
    @{ t='msg'; o='gst'; d='aut'; n='1.3: autorizar("ADMINISTRADOR")' },
    @{ t='msg'; o='gst'; d='exi'; n='1.4: SELECT ... FROM existencia JOIN variante_producto JOIN sucursal' },
    @{ t='msg'; o='exi'; d='gst'; n='1.4.1: list[Row]'; ret=$true },
    @{ t='msg'; o='gst'; d='gst'; n='1.5: _agrupar(filas) -- por variante, sobre TODO lo filtrado' },
    @{ t='msg'; o='gst'; d='gst'; n='1.6: _estado(disponible, stock_minimo)' },
    @{ t='alt' },
    @{ t='op'; g='hay resultados' },
    @{ t='msg'; o='gst'; d='gst'; n='1.7: _ordenar(items, orden)' },
    @{ t='msg'; o='gst'; d='pan'; n='1.7.1: PaginaInventarioConsolidado + ResumenInventarioOut'; ret=$true },
    @{ t='msg'; o='pan'; d='act'; n='1.8: mostrarConsolidado(resultado)' },
    @{ t='op'; g='sin resultados con esos filtros' },
    @{ t='msg'; o='gst'; d='pan'; n='3.1: sinResultados()' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-15 --
@{
  nombre = '3.2 CU-15 Registrar movimiento de inventario'
  lineas = @(
    @{ k = 'act'; actor = 'Administrador';        w = 130 },
    @{ k = 'pan'; clase = 'PantallaInventario';   w = 190 },
    @{ k = 'gst'; clase = 'GestorInventario';     w = 190 },
    @{ k = 'aut'; clase = 'GestorAutenticacion';  w = 190 },
    @{ k = 'exi'; clase = 'Existencia';           w = 150 },
    @{ k = 'mov'; clase = 'MovimientoInventario'; w = 200 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nAjuste por`nconteo físico" },
    @{ t='msg'; o='act'; d='pan'; n='1.1: registrarAjuste(datos)' },
    @{ t='msg'; o='pan'; d='gst'; n='1.2: registrar_ajuste(db, datos, usuario_id)' },
    @{ t='msg'; o='gst'; d='aut'; n='1.3: autorizar("ADMINISTRADOR", "ENCARGADO")' },
    @{ t='msg'; o='gst'; d='exi'; n='1.4: SELECT * FROM existencia WHERE id = :id FOR UPDATE' },
    @{ t='msg'; o='exi'; d='gst'; n='1.4.1: Existencia'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='el saldo contado no deja negativo' },
    @{ t='msg'; o='gst'; d='gst'; n='1.5: _aplicar_movimiento(existencia, AJUSTE, diferencia)' },
    @{ t='msg'; o='gst'; d='exi'; n='1.6: UPDATE existencia SET cantidad_disponible = :contada - cantidad_reservada' },
    @{ t='msg'; o='gst'; d='mov'; n='1.7: INSERT INTO movimiento_inventario (existencia_id, tipo, cantidad, motivo)' },
    @{ t='msg'; o='mov'; d='gst'; n='1.7.1: MovimientoInventario (id)'; ret=$true },
    @{ t='msg'; o='gst'; d='pan'; n='1.7.2: MovimientoOut (saldo resultante)'; ret=$true },
    @{ t='nota'; txt = "FLUJO 2`nTraslado: dos movimientos`nen una transacción" },
    @{ t='msg'; o='act'; d='pan'; n='2.1: registrarTransferencia(datos)' },
    @{ t='msg'; o='pan'; d='gst'; n='2.2: registrar_transferencia(db, datos, usuario_id)' },
    @{ t='msg'; o='gst'; d='mov'; n='2.3: INSERT INTO movimiento_inventario (tipo = TRASLADO_SALIDA, cantidad = -n)' },
    @{ t='msg'; o='gst'; d='mov'; n='2.4: INSERT INTO movimiento_inventario (tipo = TRASLADO_ENTRADA, cantidad = +n)' },
    @{ t='op'; g='el ajuste dejaría el saldo negativo' },
    @{ t='msg'; o='gst'; d='pan'; n='4.1: saldoNegativo() -> 409' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-16 --
@{
  nombre = '3.2 CU-16 Gestionar disponibilidad de la sucursal'
  lineas = @(
    @{ k = 'act'; actor = 'Encargado de Sucursal';   w = 160 },
    @{ k = 'pan'; clase = 'PantallaDisponibilidad';  w = 210 },
    @{ k = 'gst'; clase = 'GestorInventario';        w = 190 },
    @{ k = 'aut'; clase = 'GestorAutenticacion';     w = 190 },
    @{ k = 'exi'; clase = 'Existencia';              w = 150 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nFijar el punto`nde reposición" },
    @{ t='msg'; o='act'; d='pan'; n='1.1: fijarStockMinimo(existencia_id, umbral)' },
    @{ t='msg'; o='pan'; d='gst'; n='1.2: fijar_stock_minimo(db, existencia_id, minimo, usuario)' },
    @{ t='msg'; o='gst'; d='aut'; n='1.3: autorizar("ENCARGADO")' },
    @{ t='msg'; o='gst'; d='exi'; n='1.4: SELECT * FROM existencia WHERE id = :id' },
    @{ t='msg'; o='exi'; d='gst'; n='1.4.1: Existencia'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='la existencia es de su sucursal' },
    @{ t='msg'; o='gst'; d='exi'; n='1.5: UPDATE existencia SET stock_minimo = :minimo WHERE id = :id' },
    @{ t='msg'; o='exi'; d='gst'; n='1.5.1: Existencia'; ret=$true },
    @{ t='msg'; o='gst'; d='pan'; n='1.5.2: ExistenciaOut (bajo_minimo)'; ret=$true },
    @{ t='msg'; o='pan'; d='act'; n='1.6: confirmarConAviso(enAlerta)' },
    @{ t='nota'; txt = "FLUJO 2`nPanel de alertas`nde stock bajo" },
    @{ t='msg'; o='act'; d='pan'; n='2.1: listarAlertas()' },
    @{ t='msg'; o='pan'; d='gst'; n='2.2: alertas_de_stock(db, sucursal_id)' },
    @{ t='msg'; o='gst'; d='exi'; n='2.3: SELECT ... WHERE stock_minimo > 0 AND cantidad_disponible <= stock_minimo' },
    @{ t='msg'; o='exi'; d='gst'; n='2.3.1: list[Row]'; ret=$true },
    @{ t='op'; g='existencia de otra sucursal' },
    @{ t='msg'; o='gst'; d='pan'; n='4.1: existenciaDeOtraSucursal() -> 403' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-17 --
@{
  nombre = '3.2 CU-17 Consultar catálogo'
  lineas = @(
    @{ k = 'act'; actor = 'Cliente';            w = 110 },
    @{ k = 'pan'; clase = 'PantallaCatalogo';   w = 190 },
    @{ k = 'gst'; clase = 'GestorVitrina';      w = 190 },
    @{ k = 'pro'; clase = 'Producto';           w = 150 },
    @{ k = 'var'; clase = 'VarianteProducto';   w = 180 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nVitrina pública.`nNO pasa por autenticación" },
    @{ t='msg'; o='act'; d='pan'; n='1.1: abrirCatalogo()' },
    @{ t='msg'; o='pan'; d='gst'; n='1.2: listar_productos(db, consulta)' },
    @{ t='msg'; o='gst'; d='pro'; n='1.3: SELECT ... FROM producto WHERE activo = true' },
    @{ t='msg'; o='pro'; d='gst'; n='1.3.1: list[Row]'; ret=$true },
    @{ t='msg'; o='gst'; d='var'; n='1.4: SELECT MIN(precio), MAX(precio) FROM variante_producto WHERE producto_id IN (...)' },
    @{ t='msg'; o='var'; d='gst'; n='1.4.1: dict[int, tuple]'; ret=$true },
    @{ t='msg'; o='gst'; d='pan'; n='1.4.2: PaginaVitrinaOut'; ret=$true },
    @{ t='nota'; txt = "FLUJO 2`nBúsqueda, filtros y orden" },
    @{ t='msg'; o='act'; d='pan'; n='2.1: buscarYFiltrar(criterios)' },
    @{ t='msg'; o='pan'; d='gst'; n='2.2: listar_productos(db, consulta)' },
    @{ t='msg'; o='gst'; d='pro'; n='2.3: ids_de_categoria_y_descendientes(db, categoria_id)' },
    @{ t='msg'; o='pro'; d='gst'; n='2.3.1: list[int]'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='hay resultados' },
    @{ t='msg'; o='gst'; d='pro'; n='2.4: SELECT COUNT(*) FROM producto WHERE ... -- para el paginador' },
    @{ t='msg'; o='gst'; d='pan'; n='2.4.1: PaginaVitrinaOut'; ret=$true },
    @{ t='op'; g='la combinación de filtros no devuelve nada' },
    @{ t='msg'; o='gst'; d='pan'; n='3.1: sinResultadosConFiltros()' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-18 --
@{
  nombre = '3.2 CU-18 Consultar ficha de producto'
  lineas = @(
    @{ k = 'act'; actor = 'Cliente';                w = 110 },
    @{ k = 'pan'; clase = 'PantallaFichaProducto';  w = 210 },
    @{ k = 'gst'; clase = 'GestorVitrina';          w = 190 },
    @{ k = 'pro'; clase = 'Producto';               w = 150 },
    @{ k = 'var'; clase = 'VarianteProducto';       w = 180 },
    @{ k = 'img'; clase = 'ImagenProducto';         w = 170 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nApertura de la ficha" },
    @{ t='msg'; o='act'; d='pan'; n='1.1: abrirFicha(producto_id)' },
    @{ t='msg'; o='pan'; d='gst'; n='1.2: obtener_ficha(db, producto_id)' },
    @{ t='msg'; o='gst'; d='pro'; n='1.3: SELECT * FROM producto WHERE id = :id AND activo = true' },
    @{ t='msg'; o='pro'; d='gst'; n='1.3.1: Row | None'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='la prenda se sigue ofreciendo' },
    @{ t='msg'; o='gst'; d='img'; n='1.4: SELECT * FROM imagen_producto WHERE producto_id = :id ORDER BY orden' },
    @{ t='msg'; o='img'; d='gst'; n='1.4.1: list[Row]'; ret=$true },
    @{ t='msg'; o='gst'; d='var'; n='1.5: SELECT ... FROM variante_producto WHERE producto_id = :id AND activa = true' },
    @{ t='msg'; o='var'; d='gst'; n='1.5.1: list[Row]'; ret=$true },
    @{ t='msg'; o='gst'; d='gst'; n='1.6: _opciones(variantes) -- tallas y colores ofrecibles' },
    @{ t='msg'; o='gst'; d='pan'; n='1.6.1: FichaProductoOut'; ret=$true },
    @{ t='msg'; o='act'; d='pan'; n='2.1: elegirTalla(talla_id)' },
    @{ t='msg'; o='pan'; d='pan'; n='2.2: coloresDeTalla(talla_id) -- restringe en el cliente' },
    @{ t='msg'; o='act'; d='pan'; n='2.3: elegirColor(color_id)' },
    @{ t='msg'; o='pan'; d='pan'; n='2.4: varianteDe(talla_id, color_id)' },
    @{ t='op'; g='la prenda dejó de ofrecerse' },
    @{ t='msg'; o='gst'; d='pan'; n='4.1: prendaYaNoDisponible() -> 404' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-19 --
@{
  nombre = '3.2 CU-19 Consultar disponibilidad por sucursal'
  lineas = @(
    @{ k = 'act'; actor = 'Cliente';                w = 110 },
    @{ k = 'pan'; clase = 'PantallaFichaProducto';  w = 210 },
    @{ k = 'gst'; clase = 'GestorVitrina';          w = 190 },
    @{ k = 'inv'; clase = 'GestorInventario';       w = 190 },
    @{ k = 'var'; clase = 'VarianteProducto';       w = 180 },
    @{ k = 'exi'; clase = 'Existencia';             w = 150 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nCostura C1: P5 le PIDE`nel dato a P4" },
    @{ t='msg'; o='act'; d='pan'; n='1.1: verDisponibilidad(variante_id)' },
    @{ t='msg'; o='pan'; d='gst'; n='1.2: disponibilidad_de_variante(db, variante_id)' },
    @{ t='msg'; o='gst'; d='var'; n='1.3: SELECT ... FROM variante_producto WHERE id = :id AND activa = true' },
    @{ t='msg'; o='var'; d='gst'; n='1.3.1: Row | None'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='la variante se sigue ofreciendo' },
    @{ t='msg'; o='gst'; d='inv'; n='1.4: disponibilidad_por_sucursal(db, variante_id)' },
    @{ t='msg'; o='inv'; d='exi'; n='1.5: SELECT sucursal_id, cantidad_disponible FROM existencia WHERE variante_id = :v' },
    @{ t='msg'; o='exi'; d='inv'; n='1.5.1: list[Row]'; ret=$true },
    @{ t='msg'; o='inv'; d='gst'; n='1.5.2: list[DisponibilidadSucursal]'; ret=$true },
    @{ t='msg'; o='gst'; d='pan'; n='1.5.3: DisponibilidadOut (total + sucursales con saldo)'; ret=$true },
    @{ t='msg'; o='pan'; d='act'; n='1.6: mostrarSucursales(disponibilidad)' },
    @{ t='op'; g='sin unidades en ninguna sucursal' },
    @{ t='msg'; o='gst'; d='pan'; n='3.1: sinStockPorAhora() -- no es un error' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-22 --
@{
  nombre = '3.2 CU-22 Crear reserva de prendas'
  lineas = @(
    @{ k = 'act'; actor = 'Cliente';               w = 110 },
    @{ k = 'pan'; clase = 'PantallaReservas';      w = 190 },
    @{ k = 'gst'; clase = 'GestorReservas';        w = 190 },
    @{ k = 'inv'; clase = 'GestorInventario';      w = 190 },
    @{ k = 'res'; clase = 'Reserva';               w = 150 },
    @{ k = 'det'; clase = 'ReservaDetalle';        w = 170 },
    @{ k = 'exi'; clase = 'Existencia';            w = 150 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nPrimero lo que se rechaza`nSIN tocar filas; el apartado`nal final, que toma bloqueos" },
    @{ t='msg'; o='act'; d='pan'; n='1.1: confirmarReserva(datos)' },
    @{ t='msg'; o='pan'; d='gst'; n='1.2: crear_reserva(db, datos, usuario_id)' },
    @{ t='msg'; o='gst'; d='gst'; n='1.3: _validar_franja(sucursal, inicio, fin)' },
    @{ t='msg'; o='gst'; d='res'; n='1.4: SELECT COUNT(*) FROM reserva WHERE estado IN (...) AND franja se solapa' },
    @{ t='msg'; o='res'; d='gst'; n='1.4.1: int'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='franja válida y probador libre' },
    @{ t='msg'; o='gst'; d='inv'; n='1.5: apartar_para_reserva(db, variante_id, sucursal_id, cantidad)' },
    @{ t='msg'; o='inv'; d='exi'; n='1.6: SELECT * FROM existencia WHERE variante_id = :v AND sucursal_id = :s FOR UPDATE' },
    @{ t='msg'; o='exi'; d='inv'; n='1.6.1: Existencia'; ret=$true },
    @{ t='msg'; o='inv'; d='exi'; n='1.7: UPDATE existencia SET disponible = disponible - :n, reservada = reservada + :n' },
    @{ t='msg'; o='gst'; d='res'; n='1.8: INSERT INTO reserva (cliente_id, sucursal_id, franja_inicio, franja_fin, estado)' },
    @{ t='msg'; o='res'; d='gst'; n='1.8.1: Reserva (id)'; ret=$true },
    @{ t='msg'; o='gst'; d='det'; n='1.9: INSERT INTO reserva_detalle (reserva_id, variante_id, cantidad)' },
    @{ t='msg'; o='gst'; d='pan'; n='1.9.1: ReservaOut'; ret=$true },
    @{ t='op'; g='sin probadores libres o sin stock' },
    @{ t='msg'; o='gst'; d='gst'; n='3.1: revertirTransaccion() -- no queda apartada NINGUNA prenda' },
    @{ t='msg'; o='gst'; d='pan'; n='3.2: sinProbadoresLibres() -> 409' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-23 --
@{
  nombre = '3.2 CU-23 Consultar y cancelar reserva'
  lineas = @(
    @{ k = 'act'; actor = 'Cliente';               w = 110 },
    @{ k = 'pan'; clase = 'PantallaReservas';      w = 190 },
    @{ k = 'gst'; clase = 'GestorReservas';        w = 190 },
    @{ k = 'inv'; clase = 'GestorInventario';      w = 190 },
    @{ k = 'res'; clase = 'Reserva';               w = 150 },
    @{ k = 'det'; clase = 'ReservaDetalle';        w = 170 },
    @{ k = 'exi'; clase = 'Existencia';            w = 150 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nMis reservas" },
    @{ t='msg'; o='act'; d='pan'; n='1.1: abrirMisReservas()' },
    @{ t='msg'; o='pan'; d='gst'; n='1.2: listar_mis_reservas(db, usuario_id, filtros)' },
    @{ t='msg'; o='gst'; d='res'; n='1.3: SELECT ... FROM reserva WHERE cliente_id = :c ORDER BY franja_inicio DESC' },
    @{ t='msg'; o='res'; d='gst'; n='1.3.1: list[Row]'; ret=$true },
    @{ t='msg'; o='gst'; d='pan'; n='1.3.2: PaginaReservas'; ret=$true },
    @{ t='nota'; txt = "FLUJO 2`nCancelación. El estado se`ncomprueba DESPUÉS del bloqueo" },
    @{ t='msg'; o='act'; d='pan'; n='2.1: cancelarReserva(id, motivo)' },
    @{ t='msg'; o='pan'; d='gst'; n='2.2: cancelar_reserva(db, reserva_id, datos, usuario_id)' },
    @{ t='msg'; o='gst'; d='res'; n='2.3: SELECT * FROM reserva WHERE id = :id FOR UPDATE' },
    @{ t='msg'; o='res'; d='gst'; n='2.3.1: Reserva'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='la reserva sigue viva y es suya' },
    @{ t='msg'; o='gst'; d='det'; n='2.4: SELECT * FROM reserva_detalle WHERE reserva_id = :id' },
    @{ t='msg'; o='det'; d='gst'; n='2.4.1: list[ReservaDetalle]'; ret=$true },
    @{ t='msg'; o='gst'; d='inv'; n='2.5: liberar_de_reserva(db, variante_id, sucursal_id, cantidad)' },
    @{ t='msg'; o='inv'; d='exi'; n='2.6: UPDATE existencia SET disponible = disponible + :n, reservada = reservada - :n' },
    @{ t='msg'; o='gst'; d='res'; n="2.7: UPDATE reserva SET estado = 'CANCELADA', observacion = :motivo" },
    @{ t='msg'; o='gst'; d='pan'; n='2.7.1: ReservaOut'; ret=$true },
    @{ t='op'; g='ya fue atendida, cancelada o expiró' },
    @{ t='msg'; o='gst'; d='pan'; n='4.1: laReservaYaNoEstaViva(estado) -> 409' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-24 --
@{
  nombre = '3.2 CU-24 Atender reserva en sucursal'
  lineas = @(
    @{ k = 'act'; actor = 'Encargado de Sucursal';     w = 160 },
    @{ k = 'pan'; clase = 'PantallaReservasSucursal';  w = 220 },
    @{ k = 'gst'; clase = 'GestorReservas';            w = 190 },
    @{ k = 'inv'; clase = 'GestorInventario';          w = 190 },
    @{ k = 'res'; clase = 'Reserva';                   w = 150 },
    @{ k = 'det'; clase = 'ReservaDetalle';            w = 170 },
    @{ k = 'exi'; clase = 'Existencia';                w = 150 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nAgenda del local`ny preparación" },
    @{ t='msg'; o='act'; d='pan'; n='1.1: abrirPanelDeReservas()' },
    @{ t='msg'; o='pan'; d='gst'; n='1.2: listar_reservas_de_sucursal(db, sucursal_id, filtros)' },
    @{ t='msg'; o='gst'; d='res'; n='1.3: SELECT ... FROM reserva WHERE sucursal_id = :s ORDER BY franja_inicio' },
    @{ t='msg'; o='res'; d='gst'; n='1.3.1: list[Row]'; ret=$true },
    @{ t='msg'; o='act'; d='pan'; n='1.4: prepararReserva(id)' },
    @{ t='msg'; o='gst'; d='res'; n="1.5: UPDATE reserva SET estado = 'PREPARADA' WHERE id = :id" },
    @{ t='nota'; txt = "FLUJO 2`nCierre: DOS movimientos`npor cada prenda que se lleva" },
    @{ t='msg'; o='act'; d='pan'; n='2.1: atenderReserva(id, resultados)' },
    @{ t='msg'; o='pan'; d='gst'; n='2.2: atender_reserva(db, reserva_id, datos, usuario)' },
    @{ t='msg'; o='gst'; d='res'; n='2.3: SELECT * FROM reserva WHERE id = :id FOR UPDATE' },
    @{ t='msg'; o='res'; d='gst'; n='2.3.1: Reserva'; ret=$true },
    @{ t='msg'; o='gst'; d='det'; n='2.4: SELECT * FROM reserva_detalle WHERE reserva_id = :id' },
    @{ t='msg'; o='det'; d='gst'; n='2.4.1: list[ReservaDetalle]'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='el cliente se lleva la prenda' },
    @{ t='msg'; o='gst'; d='inv'; n='2.5a: liberar_de_reserva(...) -- LIBERACION +n, vuelve del apartado' },
    @{ t='msg'; o='gst'; d='inv'; n='2.6a: descontar_por_venta(...) -- VENTA -n' },
    @{ t='msg'; o='inv'; d='exi'; n='2.7a: UPDATE existencia SET disponible = disponible - :n, reservada = reservada - :n' },
    @{ t='op'; g='el cliente no se la lleva' },
    @{ t='msg'; o='gst'; d='inv'; n='2.5b: liberar_de_reserva(...) -- LIBERACION +n, y ahí termina' },
    @{ t='msg'; o='inv'; d='exi'; n='2.6b: UPDATE existencia SET disponible = disponible + :n, reservada = reservada - :n' },
    @{ t='fin' },
    @{ t='msg'; o='gst'; d='det'; n='2.8: UPDATE reserva_detalle SET resultado_prueba = :resultado' },
    @{ t='msg'; o='gst'; d='res'; n="2.9: UPDATE reserva SET estado = 'ATENDIDA', observacion = :nota" },
    @{ t='msg'; o='gst'; d='pan'; n='2.9.1: ReservaOut'; ret=$true }
  )
},

# ---------------------------------------------------------------- CU-25 --
@{
  nombre = '3.2 CU-25 Expirar reservas vencidas'
  lineas = @(
    @{ k = 'act'; actor = 'Sistema (procesos automaticos)'; w = 180 },
    @{ k = 'pla'; clase = 'PlanificadorTareas';             w = 200 },
    @{ k = 'gst'; clase = 'GestorReservas';                 w = 190 },
    @{ k = 'inv'; clase = 'GestorInventario';               w = 190 },
    @{ k = 'res'; clase = 'Reserva';                        w = 150 },
    @{ k = 'det'; clase = 'ReservaDetalle';                 w = 170 },
    @{ k = 'exi'; clase = 'Existencia';                     w = 150 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nCorrida de la tarea.`nNO hay autorización:`nno hay usuario" },
    @{ t='msg'; o='act'; d='pla'; n='1.1: dispararTarea()' },
    @{ t='msg'; o='pla'; d='gst'; n='1.2: expirar_reservas_vencidas(db, tope)' },
    @{ t='msg'; o='gst'; d='gst'; n='1.3: _ahora() - RESERVA_VIGENCIA_HORAS = corte' },
    @{ t='msg'; o='gst'; d='res'; n='1.4: SELECT * FROM reserva WHERE estado IN (...) AND franja_fin < :corte' },
    @{ t='msg'; o='res'; d='gst'; n='1.4.1: list[Reserva]'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='hay reservas vencidas' },
    @{ t='msg'; o='gst'; d='det'; n='1.5: SELECT * FROM reserva_detalle WHERE reserva_id = :id' },
    @{ t='msg'; o='det'; d='gst'; n='1.5.1: list[ReservaDetalle]'; ret=$true },
    @{ t='msg'; o='gst'; d='inv'; n='1.6: liberar_de_reserva(db, variante_id, sucursal_id, cantidad)' },
    @{ t='msg'; o='inv'; d='exi'; n='1.7: UPDATE existencia SET disponible = disponible + :n, reservada = reservada - :n' },
    @{ t='msg'; o='gst'; d='res'; n="1.8: UPDATE reserva SET estado = 'EXPIRADA' WHERE id = :id" },
    @{ t='msg'; o='gst'; d='pla'; n='1.8.1: ExpiracionOut (encontradas, expiradas, unidades)'; ret=$true },
    @{ t='op'; g='nada que expirar' },
    @{ t='msg'; o='gst'; d='pla'; n='3.1: informe(encontradas = 0) -- no escribe nada' },
    @{ t='fin' }
  )
}
,

# ================= CICLO 3 =================================
#
# Los seis del ciclo, sobre los mismos CU que llevan estado, tiempo y
# navegacion. Dependian del 2.3 del Ciclo 3, que entro el 20/09 con el PR
# de Karen: sin esas clases el generador no puede enlazar las lineas de
# vida y se planta con «Falta la clase de 2.3».

# ---------------------------------------------------------------- CU-21 --
@{
  nombre = '3.2 CU-21 Utilizar vestidor virtual (RA)'
  lineas = @(
    @{ k = 'act'; actor = 'Cliente';                w = 110 },
    @{ k = 'ves'; clase = 'PantallaVestidor';       w = 200 },
    @{ k = 'gve'; clase = 'GestorVestidor';         w = 190 },
    @{ k = 'med'; clase = 'MedidaCliente';          w = 180 },
    @{ k = 'img'; clase = 'ImagenProducto';         w = 180 },
    @{ k = 'var'; clase = 'VarianteProducto';       w = 190 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nProbarse una prenda" },
    @{ t='msg'; o='act'; d='ves'; n='1.1: abrirVestidor(producto_id)' },
    @{ t='msg'; o='ves'; d='gve'; n='1.2: GET /tienda/productos?solo_vestidor=true' },
    @{ t='msg'; o='gve'; d='img'; n='1.3: SELECT ruta FROM imagen_producto WHERE es_transparente' },
    @{ t='msg'; o='img'; d='gve'; n='1.3.1: list[ImagenProducto]'; ret=$true },
    @{ t='msg'; o='gve'; d='var'; n='1.4: SELECT id, talla_id, color_id FROM variante_producto WHERE activa' },
    @{ t='msg'; o='var'; d='gve'; n='1.4.1: list[VarianteProducto]'; ret=$true },
    @{ t='msg'; o='gve'; d='ves'; n='1.4.2: FichaVestidorOut'; ret=$true },
    @{ t='msg'; o='ves'; d='ves'; n='1.5: detectarPose(fotograma)  {en el telefono}' },
    @{ t='msg'; o='ves'; d='ves'; n='1.6: dibujarPrenda(hombros, cadera)' },
    @{ t='msg'; o='ves'; d='act'; n='1.7: mostrarPrendaSuperpuesta()' },
    @{ t='nota'; txt = "FLUJO 2`nSaber que talla le queda" },
    @{ t='msg'; o='act'; d='ves'; n='2.1: consultarAjuste()' },
    @{ t='msg'; o='ves'; d='gve'; n='2.2: GET /clientes/me/medidas' },
    @{ t='msg'; o='gve'; d='med'; n='2.3: SELECT busto_cm, cintura_cm, cadera_cm FROM medida_cliente' },
    @{ t='msg'; o='med'; d='gve'; n='2.3.1: MedidaCliente | None'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='tiene medidas cargadas' },
    @{ t='msg'; o='gve'; d='gve'; n='2.4a: compararConMedidaTalla(medidas)' },
    @{ t='msg'; o='gve'; d='ves'; n='2.4a.1: AjusteOut(talla, holgura)'; ret=$true },
    @{ t='op'; g='no las cargo todavia' },
    @{ t='msg'; o='gve'; d='ves'; n='2.4b: sinMedidas()' },
    @{ t='msg'; o='ves'; d='act'; n='2.5b: ofrecerCargarMedidas()' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 3`nCapturar y derivar" },
    @{ t='msg'; o='act'; d='ves'; n='3.1: capturar()' },
    @{ t='msg'; o='ves'; d='ves'; n='3.2: guardarEnElTelefono(imagen)  {no viaja al servidor}' },
    @{ t='msg'; o='act'; d='ves'; n='3.3: agregarAlCarrito(variante_id)' },
    @{ t='msg'; o='ves'; d='gve'; n='3.4: POST /tienda/carrito/items  {CU-26}' },
    @{ t='msg'; o='gve'; d='ves'; n='3.4.1: CarritoOut'; ret=$true }
  )
},

# ---------------------------------------------------------------- CU-27 --
@{
  nombre = '3.2 CU-27 Realizar pedido y pagar en línea'
  lineas = @(
    @{ k = 'act'; actor = 'Cliente';            w = 110 },
    @{ k = 'chk'; clase = 'PantallaCheckout';   w = 190 },
    @{ k = 'gpe'; clase = 'GestorPedidos';      w = 180 },
    @{ k = 'gin'; clase = 'GestorInventario';   w = 190 },
    @{ k = 'ven'; clase = 'Venta';              w = 140 },
    @{ k = 'det'; clase = 'DetalleVenta';       w = 170 },
    @{ k = 'exi'; clase = 'Existencia';         w = 160 },
    @{ k = 'pas'; actor = 'Pasarela de Pago';   w = 160 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nPaso 1: que puedo pedir" },
    @{ t='msg'; o='act'; d='chk'; n='1.1: abrirCheckout()' },
    @{ t='msg'; o='chk'; d='gpe'; n='1.2: GET /tienda/pedidos/opciones' },
    @{ t='msg'; o='gpe'; d='exi'; n='1.3: SELECT sucursal_id, SUM(cantidad_disponible) FROM existencia GROUP BY sucursal_id' },
    @{ t='msg'; o='exi'; d='gpe'; n='1.3.1: dict[sucursal, faltantes]'; ret=$true },
    @{ t='msg'; o='gpe'; d='chk'; n='1.3.2: OpcionesDePedidoOut'; ret=$true },
    @{ t='nota'; txt = "FLUJO 2`nPaso 2: confirmar y apartar" },
    @{ t='msg'; o='act'; d='chk'; n='2.1: confirmar(modalidad, sucursal, total_visto)' },
    @{ t='msg'; o='chk'; d='gpe'; n='2.2: POST /tienda/pedidos' },
    @{ t='msg'; o='gpe'; d='gpe'; n='2.3: bloquear_cliente(cliente_id)  {FOR UPDATE sobre cliente}' },
    @{ t='msg'; o='gpe'; d='ven'; n='2.4: SELECT id FROM venta WHERE cliente_id AND estado = ''PENDIENTE_PAGO''' },
    @{ t='msg'; o='ven'; d='gpe'; n='2.4.1: Venta | None'; ret=$true },
    @{ t='msg'; o='gpe'; d='gpe'; n='2.5: recalcularTotal(carrito)' },
    @{ t='alt' },
    @{ t='op'; g='sin pendiente y el total coincide' },
    @{ t='msg'; o='gpe'; d='gin'; n='2.6a: apartar_para_reserva(variantes, sucursal)' },
    @{ t='msg'; o='gin'; d='exi'; n='2.7a: SELECT ... FROM existencia WHERE variante_id FOR UPDATE' },
    @{ t='msg'; o='exi'; d='gin'; n='2.7a.1: Existencia'; ret=$true },
    @{ t='msg'; o='gin'; d='exi'; n='2.8a: UPDATE existencia SET disponible = disponible - :n, reservada = reservada + :n' },
    @{ t='msg'; o='gin'; d='gpe'; n='2.8a.1: confirmación'; ret=$true },
    @{ t='msg'; o='gpe'; d='ven'; n='2.9a: INSERT INTO venta (codigo, estado, sucursal_id, total)' },
    @{ t='msg'; o='ven'; d='gpe'; n='2.9a.1: Venta (id, codigo)'; ret=$true },
    @{ t='msg'; o='gpe'; d='det'; n='2.10a: INSERT INTO detalle_venta (precio_unitario CONGELADO)' },
    @{ t='msg'; o='gpe'; d='pas'; n='2.11a: crearSesionDeCobro(total, codigo)' },
    @{ t='msg'; o='pas'; d='gpe'; n='2.11a.1: url_de_pago'; ret=$true },
    @{ t='msg'; o='gpe'; d='chk'; n='2.12a: PedidoCreadoOut(codigo, url)'; ret=$true },
    @{ t='msg'; o='chk'; d='act'; n='2.13a: redirigirAPasarela(url)' },
    @{ t='op'; g='ya hay pendiente o el total cambio' },
    @{ t='msg'; o='gpe'; d='gpe'; n='2.6b: revertirTransaccion()' },
    @{ t='msg'; o='gpe'; d='chk'; n='2.7b: conflicto(409, carrito_actual)' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 3`nCancelar antes de pagar" },
    @{ t='msg'; o='act'; d='chk'; n='3.1: cancelarPedido(codigo)' },
    @{ t='msg'; o='chk'; d='gpe'; n='3.2: POST /tienda/pedidos/:codigo/cancelar' },
    @{ t='msg'; o='gpe'; d='gin'; n='3.3: liberar(variantes, sucursal)' },
    @{ t='msg'; o='gin'; d='exi'; n='3.4: UPDATE existencia SET reservada = reservada - :n, disponible = disponible + :n' },
    @{ t='msg'; o='gpe'; d='ven'; n='3.5: UPDATE venta SET estado = ''CANCELADA''' },
    @{ t='msg'; o='gpe'; d='chk'; n='3.5.1: confirmación'; ret=$true }
  )
},

# ---------------------------------------------------------------- CU-28 --
@{
  nombre = '3.2 CU-28 Confirmar pago del pedido'
  lineas = @(
    @{ k = 'pas'; actor = 'Pasarela de Pago';      w = 160 },
    @{ k = 'whk'; clase = 'WebhookPasarela';       w = 190 },
    @{ k = 'gpa'; clase = 'GestorPagos';           w = 170 },
    @{ k = 'trx'; clase = 'TransaccionPasarela';   w = 210 },
    @{ k = 'pag'; clase = 'Pago';                  w = 130 },
    @{ k = 'ven'; clase = 'Venta';                 w = 140 },
    @{ k = 'gin'; clase = 'GestorInventario';      w = 190 },
    @{ k = 'exi'; clase = 'Existencia';            w = 160 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nEl cobro entro" },
    @{ t='msg'; o='pas'; d='whk'; n='1.1: POST /pagos/webhook (evento_id, firma)' },
    @{ t='msg'; o='whk'; d='gpa'; n='1.2: confirmar_pago(cuerpo, firma)' },
    @{ t='msg'; o='gpa'; d='gpa'; n='1.3: verificarFirma(cuerpo, firma)  {ANTES de leer}' },
    @{ t='msg'; o='gpa'; d='trx'; n='1.4: SELECT id, procesado_en FROM transaccion_pasarela WHERE evento_id = :evento' },
    @{ t='msg'; o='trx'; d='gpa'; n='1.4.1: TransaccionPasarela | None'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='firma válida y aviso nuevo' },
    @{ t='msg'; o='gpa'; d='trx'; n='1.5a: INSERT INTO transaccion_pasarela (evento_id UNICO, carga_util)' },
    @{ t='msg'; o='gpa'; d='pag'; n='1.6a: UPDATE pago SET estado = ''APROBADO'', referencia_externa' },
    @{ t='msg'; o='gpa'; d='ven'; n='1.7a: UPDATE venta SET estado = ''PAGADA''' },
    @{ t='msg'; o='gpa'; d='gin'; n='1.8a: confirmar_salida(venta)' },
    @{ t='msg'; o='gin'; d='exi'; n='1.9a: UPDATE existencia SET reservada = reservada - :n' },
    @{ t='msg'; o='gin'; d='gin'; n='1.10a: registrarMovimiento(SALIDA, referencia)' },
    @{ t='msg'; o='gin'; d='gpa'; n='1.10a.1: confirmación'; ret=$true },
    @{ t='msg'; o='gpa'; d='gpa'; n='1.11a: emitirComprobante(venta)' },
    @{ t='msg'; o='gpa'; d='whk'; n='1.11a.1: db.commit() -> 200'; ret=$true },
    @{ t='op'; g='reintento: el aviso ya se aplico' },
    @{ t='msg'; o='gpa'; d='whk'; n='1.5b: 200 sin volver a aplicar  {idempotente}' },
    @{ t='op'; g='firma inválida' },
    @{ t='msg'; o='gpa'; d='trx'; n='1.5c: INSERT INTO transaccion_pasarela (firma_valida = false)' },
    @{ t='msg'; o='gpa'; d='whk'; n='1.6c: descartar(400)' },
    @{ t='fin' },
    @{ t='msg'; o='whk'; d='pas'; n='1.12: responder()  [para que deje de reintentar]' }
  )
},

# ---------------------------------------------------------------- CU-31 --
@{
  nombre = '3.2 CU-31 Registrar venta presencial'
  lineas = @(
    @{ k = 'act'; actor = 'Cajero';              w = 110 },
    @{ k = 'pnt'; clase = 'PantallaVenta';       w = 170 },
    @{ k = 'gmo'; clase = 'GestorMostrador';     w = 190 },
    @{ k = 'gca'; clase = 'GestorCaja';          w = 160 },
    @{ k = 'gpr'; clase = 'GestorPromociones';   w = 200 },
    @{ k = 'ven'; clase = 'Venta';               w = 140 },
    @{ k = 'gin'; clase = 'GestorInventario';    w = 190 },
    @{ k = 'exi'; clase = 'Existencia';          w = 160 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nCobrar en el mostrador" },
    @{ t='msg'; o='act'; d='pnt'; n='1.1: abrirMostrador()' },
    @{ t='msg'; o='pnt'; d='gca'; n='1.2: GET /caja/turnos/mio' },
    @{ t='msg'; o='gca'; d='pnt'; n='1.2.1: TurnoCaja | None'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='hay turno abierto' },
    @{ t='msg'; o='act'; d='pnt'; n='1.3a: buscarPrenda(texto)' },
    @{ t='msg'; o='pnt'; d='gmo'; n='1.4a: GET /pos/prendas?busqueda' },
    @{ t='msg'; o='gmo'; d='exi'; n='1.5a: SELECT v.* FROM existencia e JOIN variante_producto v WHERE e.sucursal_id = :suya' },
    @{ t='msg'; o='exi'; d='gmo'; n='1.5a.1: list[VarianteProducto]'; ret=$true },
    @{ t='msg'; o='act'; d='pnt'; n='1.6a: registrarVenta(detalle, medio_pago)' },
    @{ t='msg'; o='pnt'; d='gmo'; n='1.7a: POST /pos/ventas' },
    @{ t='msg'; o='gmo'; d='gpr'; n='1.8a: descuentos_por_variante(precios)' },
    @{ t='msg'; o='gpr'; d='gmo'; n='1.8a.1: dict[variante, Descuento]'; ret=$true },
    @{ t='msg'; o='gmo'; d='gin'; n='1.9a: descontar(variantes, sucursal)' },
    @{ t='msg'; o='gin'; d='exi'; n='1.10a: SELECT ... FROM existencia WHERE variante_id FOR UPDATE' },
    @{ t='msg'; o='gin'; d='exi'; n='1.11a: UPDATE existencia SET cantidad_disponible = disponible - :n' },
    @{ t='msg'; o='gin'; d='gmo'; n='1.11a.1: confirmación'; ret=$true },
    @{ t='msg'; o='gmo'; d='ven'; n='1.12a: INSERT INTO venta (canal = ''PRESENCIAL'', turno_caja_id)' },
    @{ t='msg'; o='ven'; d='gmo'; n='1.12a.1: Venta (codigo)'; ret=$true },
    @{ t='msg'; o='gmo'; d='gmo'; n='1.13a: emitirComprobante(venta)' },
    @{ t='msg'; o='gmo'; d='pnt'; n='1.13a.1: db.commit() -> VentaOut'; ret=$true },
    @{ t='op'; g='sin turno abierto' },
    @{ t='msg'; o='pnt'; d='act'; n='1.3b: llevarAAbrirCaja()  {CU-30}' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 2`nCobrar una reserva atendida" },
    @{ t='msg'; o='act'; d='pnt'; n='2.1: verReservasPorCobrar()' },
    @{ t='msg'; o='pnt'; d='gmo'; n='2.2: GET /pos/reservas' },
    @{ t='msg'; o='gmo'; d='pnt'; n='2.2.1: list[ReservaPorCobrar]'; ret=$true },
    @{ t='msg'; o='act'; d='pnt'; n='2.3: cargarReserva(reserva_id)' },
    @{ t='msg'; o='pnt'; d='gmo'; n='2.4: POST /pos/ventas (reserva_id)' },
    @{ t='msg'; o='gmo'; d='gin'; n='2.5: convertirReservaEnSalida(reserva)  [ya estaba apartado]' },
    @{ t='msg'; o='gmo'; d='ven'; n='2.6: INSERT INTO venta (reserva_id UNICO)' },
    @{ t='msg'; o='gmo'; d='pnt'; n='2.6.1: VentaOut'; ret=$true }
  )
},

# ---------------------------------------------------------------- CU-33 --
@{
  nombre = '3.2 CU-33 Recibir recomendaciones de prendas'
  lineas = @(
    @{ k = 'act'; actor = 'Cliente';                w = 110 },
    @{ k = 'pnt'; clase = 'PantallaParaVos';        w = 180 },
    @{ k = 'gre'; clase = 'GestorRecomendaciones';  w = 220 },
    @{ k = 'fav'; clase = 'Favorito';               w = 140 },
    @{ k = 'var'; clase = 'VarianteProducto';       w = 190 },
    @{ k = 'gin'; clase = 'GestorInventario';       w = 190 },
    @{ k = 'rec'; clase = 'Recomendacion';          w = 180 },
    @{ k = 'ia';  actor = 'Servicio de IA';         w = 150 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nSugerir prendas" },
    @{ t='msg'; o='act'; d='pnt'; n='1.1: abrirParaVos()' },
    @{ t='msg'; o='pnt'; d='gre'; n='1.2: GET /tienda/recomendaciones' },
    @{ t='msg'; o='gre'; d='fav'; n='1.3: SELECT producto_id FROM favorito WHERE cliente_id = :cliente' },
    @{ t='msg'; o='fav'; d='gre'; n='1.3.1: list[Favorito]'; ret=$true },
    @{ t='msg'; o='gre'; d='var'; n='1.4: SELECT p.id, p.nombre FROM producto p WHERE p.activo' },
    @{ t='msg'; o='var'; d='gre'; n='1.4.1: list[Producto]'; ret=$true },
    @{ t='msg'; o='gre'; d='gre'; n='1.5: armarContexto(senal, catalogo)  {id -> nombre}' },
    @{ t='msg'; o='gre'; d='ia';  n='1.6: generar(prompt)' },
    @{ t='msg'; o='ia';  d='gre'; n='1.6.1: sugerencias (3 a 25 s)'; ret=$true },
    @{ t='msg'; o='gre'; d='gin'; n='1.7: productos_con_stock(ids)  {costura C1}' },
    @{ t='msg'; o='gin'; d='gre'; n='1.7.1: set[producto_id]'; ret=$true },
    @{ t='msg'; o='gre'; d='gre'; n='1.8: validarContraCatalogo(sugerencias)' },
    @{ t='alt' },
    @{ t='op'; g='sobreviven al menos tres' },
    @{ t='msg'; o='gre'; d='rec'; n='1.9a: INSERT INTO recomendacion (motor, sugerencias JSONB)' },
    @{ t='msg'; o='rec'; d='gre'; n='1.9a.1: Recomendacion'; ret=$true },
    @{ t='msg'; o='gre'; d='pnt'; n='1.10a: RecomendacionesOut'; ret=$true },
    @{ t='msg'; o='pnt'; d='act'; n='1.11a: mostrarPrendasConMotivo()' },
    @{ t='op'; g='quedan menos de MINIMO_UTIL' },
    @{ t='msg'; o='gre'; d='ia';  n='1.9b: generar(prompt)  [se vuelve a pedir]' },
    @{ t='op'; g='no hay proveedor de IA' },
    @{ t='msg'; o='gre'; d='pnt'; n='1.9c: noDisponible()' },
    @{ t='msg'; o='pnt'; d='act'; n='1.10c: ofrecerElCatalogo()' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-34 --
@{
  nombre = '3.2 CU-34 Conversar con el asistente virtual'
  lineas = @(
    @{ k = 'act'; actor = 'Cliente';           w = 110 },
    @{ k = 'pnt'; clase = 'PantallaAsistente'; w = 190 },
    @{ k = 'gas'; clase = 'GestorAsistente';   w = 180 },
    @{ k = 'var'; clase = 'VarianteProducto';  w = 190 },
    @{ k = 'gpr'; clase = 'GestorPromociones'; w = 200 },
    @{ k = 'ven'; clase = 'Venta';             w = 140 },
    @{ k = 'med'; clase = 'MedidaCliente';     w = 180 },
    @{ k = 'ia';  actor = 'Servicio de IA';    w = 150 }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nPreguntar" },
    @{ t='msg'; o='act'; d='pnt'; n='1.1: abrirAsistente()' },
    @{ t='msg'; o='pnt'; d='gas'; n='1.2: GET /asistente/disponible' },
    @{ t='msg'; o='gas'; d='pnt'; n='1.2.1: EstadoOut(disponible, ejemplos)'; ret=$true },
    @{ t='msg'; o='act'; d='pnt'; n='1.3: preguntar(texto, historial)' },
    @{ t='msg'; o='pnt'; d='gas'; n='1.4: POST /asistente' },
    @{ t='msg'; o='gas'; d='var'; n='1.5: SELECT p.id, p.nombre, v.precio, t.codigo, c.nombre FROM producto p JOIN variante_producto v' },
    @{ t='msg'; o='var'; d='gas'; n='1.5.1: list[LineaDeCatalogo]'; ret=$true },
    @{ t='msg'; o='gas'; d='gpr'; n='1.6: descuentos_por_producto(precios)  {costura CU-12}' },
    @{ t='msg'; o='gpr'; d='gas'; n='1.6.1: dict[producto, Descuento]'; ret=$true },
    @{ t='msg'; o='gas'; d='ven'; n='1.7: SELECT codigo, estado, total FROM venta WHERE cliente_id = :cliente' },
    @{ t='msg'; o='ven'; d='gas'; n='1.7.1: list[Venta]  [SOLO las suyas]'; ret=$true },
    @{ t='msg'; o='gas'; d='med'; n='1.8: SELECT busto_cm, cintura_cm, cadera_cm FROM medida_cliente' },
    @{ t='msg'; o='med'; d='gas'; n='1.8.1: MedidaCliente | None'; ret=$true },
    @{ t='msg'; o='gas'; d='gas'; n='1.9: armarContexto(catalogo, ofertas, tallas, pedidos, medidas)' },
    @{ t='msg'; o='gas'; d='ia';  n='1.10: responder(pregunta, contexto, historial)  {UNA sola llamada}' },
    @{ t='msg'; o='ia';  d='gas'; n='1.10.1: texto con codigos [#12] (3 a 25 s)'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='el modelo contesto' },
    @{ t='msg'; o='gas'; d='gas'; n='1.11a: validarCodigos(texto, catalogo)  [descarta los inventados]' },
    @{ t='msg'; o='gas'; d='pnt'; n='1.11a.1: RespuestaOut(texto, productos)'; ret=$true },
    @{ t='msg'; o='pnt'; d='pnt'; n='1.12a: guardarTurnoEnMemoria()  {NO va a la base}' },
    @{ t='msg'; o='pnt'; d='act'; n='1.13a: mostrarRespuestaConEnlaces()' },
    @{ t='op'; g='el modelo se saturo' },
    @{ t='msg'; o='gas'; d='ia';  n='1.11b: responder(...)  [modelo de respaldo]' },
    @{ t='op'; g='no hay proveedor de IA' },
    @{ t='msg'; o='gas'; d='pnt'; n='1.11c: noDisponible()' },
    @{ t='fin' }
  )
}
)

# =========================================================================
# PARTE 1 - Enterprise Architect por COM
# =========================================================================

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

function Get-OCrearPaquete($padre, $nombre) {
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    $p = $padre.Packages.AddNew($nombre, 'Package'); [void]$p.Update()
    $padre.Packages.Refresh(); return $p
}
function BuscarPaquete($p, $n) {
    foreach ($s in $p.Packages) { if ($s.Name -eq $n) { return $s }; $r = BuscarPaquete $s $n; if ($r) { return $r } }
    return $null
}
function BuscarDiagrama($p, $n) {
    foreach ($d in $p.Diagrams) { if ($d.Name -eq $n) { return $d } }
    foreach ($s in $p.Packages) { $r = BuscarDiagrama $s $n; if ($r) { return $r } }
    return $null
}
function BuscarActor($p, $n) {
    foreach ($e in $p.Elements) { if ($e.Type -eq 'Actor' -and $e.Name -eq $n) { return $e } }
    foreach ($s in $p.Packages) { $r = BuscarActor $s $n; if ($r) { return $r } }
    return $null
}
function Poner($dia, $el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l + $ancho);t=$t;b=$($t - $alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
}

$root = $ea.Models.GetAt(0)

$p23 = BuscarPaquete $root '2.3 Analisis de Clases'
if (-not $p23) { throw 'No se encontro el paquete 2.3 Analisis de Clases' }
$clase = @{}
foreach ($e in $p23.Elements) { if ($e.Type -eq 'Class') { $clase[$e.Name] = $e } }

$pCap3 = BuscarPaquete $root 'CAP. 3 - Flujo de Trabajo: Diseno'
if (-not $pCap3) { throw 'No se encontro el paquete CAP. 3' }

if ($Rehacer) {
    for ($i = $pCap3.Packages.Count - 1; $i -ge 0; $i--) {
        if ($pCap3.Packages.GetAt($i).Name -eq '3.2 Diagramas de Secuencia') {
            $pCap3.Packages.DeleteAt($i, $false)
            Write-Output '  paquete 3.2 anterior eliminado (-Rehacer)'
        }
    }
    $pCap3.Packages.Refresh()
}

$p32 = Get-OCrearPaquete $pCap3 '3.2 Diagramas de Secuencia'

$pendientes = @()

foreach ($cu in $CASOS) {

    if (BuscarDiagrama $p32 $cu.nombre) {
        Write-Output "  $($cu.nombre) ya existe, no se toca"
        continue
    }

    # ---- Resolver las lineas de vida y calcular su posicion horizontal ----
    $lv = @{}
    $x = $X0
    $posX = @{}
    foreach ($def in $cu.lineas) {
        if ($def.ContainsKey('actor')) {
            $el = BuscarActor $root $def.actor
            if (-not $el) { throw "No se encontro el actor $($def.actor)" }
        } else {
            if (-not $clase.ContainsKey($def.clase)) { throw "Falta la clase de 2.3: $($def.clase)" }
            $el = $p32.Elements.AddNew('', 'Sequence')
            $el.Name = ''
            $el.ClassifierID = $clase[$def.clase].ElementID
            [void]$el.Update()
        }
        $lv[$def.k] = $el
        $posX[$def.k] = @{ l = $x; w = $def.w }
        $x += $def.w + $GAP
    }
    $p32.Elements.Refresh()
    $anchoTotal = $x - $GAP

    # ---- Recorrer el guion y asignar alturas ----
    $y = $Y_PRIMERO
    $msgs = @()
    $notas = @()
    $frames = @()
    $actual = $null

    foreach ($p in $cu.guion) {
        switch ($p.t) {
            'nota' {
                $notas += @{ txt = $p.txt; y = $y + 8 }
                $y -= $ALTO_NOTA
            }
            'msg' {
                $esRet = $false
                if ($p.ContainsKey('ret')) { $esRet = [bool]$p.ret }
                $msgs += @{ o = $p.o; d = $p.d; n = $p.n; ret = $esRet; y = $y }
                $y -= $PASO
            }
            'alt' {
                $actual = @{ top = $y + 24; cortes = @(); ops = @() }
                $y -= $ALTO_ALT
            }
            'op' {
                if ($actual.ops.Count -gt 0) { $actual.cortes += ($y + 22) }
                $actual.ops += $p.g
                $y -= $ALTO_OP
            }
            'fin' {
                $actual.bot = $y + 24
                $frames += $actual
                $actual = $null
                $y -= 18
            }
        }
    }
    $BOT = $y - 30

    # ---- Crear el diagrama y colocar todo ----
    $dia = $p32.Diagrams.AddNew($cu.nombre, 'Sequence')
    [void]$dia.Update(); $p32.Diagrams.Refresh()

    foreach ($def in $cu.lineas) {
        $pos = $posX[$def.k]
        Poner $dia $lv[$def.k] $pos.l $TOP_LV $pos.w ($TOP_LV - $BOT)
    }

    foreach ($n in $notas) {
        $nota = $p32.Elements.AddNew('', 'Note')
        $nota.Notes = $n.txt
        [void]$nota.Update()
        Poner $dia $nota $NOTA_X $n.y $NOTA_W 56
    }

    $fragsCreados = @()
    foreach ($f in $frames) {
        $frag = $p32.Elements.AddNew('', 'InteractionFragment')
        [void]$frag.Update()
        Poner $dia $frag ($X0 - 60) $f.top ($anchoTotal - $X0 + 100) ($f.top - $f.bot)

        # Los cortes entre operandos dan el alto de cada uno. La suma tiene que
        # ser exactamente el alto del fragmento o EA reparte mal las lineas.
        $limites = @($f.top) + $f.cortes + @($f.bot)
        $partes = @()
        for ($i = 0; $i -lt $f.ops.Count; $i++) {
            $tam = $limites[$i] - $limites[$i + 1]
            $g = '{' + [guid]::NewGuid().ToString().ToUpper() + '}'
            $partes += "@PAR;Name=$($f.ops[$i]);Size=$tam;GUID=$g;@ENDPAR;"
        }
        $fragsCreados += @{ g = $frag.ElementGUID; par = ($partes -join '') }
    }
    $p32.Elements.Refresh()

    # ---- Los mensajes ----
    $geo = @()
    $seq = 1
    foreach ($m in $msgs) {
        $src = $lv[$m.o]
        $dst = $lv[$m.d]
        $c = $src.Connectors.AddNew($m.n, 'Sequence')
        $c.SupplierID = $dst.ElementID
        $c.Direction = 'Source -> Destination'
        $c.DiagramID = $dia.DiagramID
        $c.SequenceNo = $seq
        [void]$c.Update()
        $geo += [pscustomobject]@{ g = $c.ConnectorGUID; seq = $seq; y = $m.y; ret = $m.ret }
        $src.Connectors.Refresh()
        $seq++
    }

    $dia.DiagramObjects.Refresh(); $dia.DiagramLinks.Refresh()
    $pendientes += [pscustomobject]@{ dia = $cu.nombre; geo = $geo; frags = $fragsCreados }
    Write-Output "  $($cu.nombre) : $($dia.DiagramObjects.Count) elementos, $($msgs.Count) mensajes, $($frames.Count) fragmento(s) alt"
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers()
Start-Sleep -Milliseconds 1500

if ($pendientes.Count -eq 0) { Write-Output 'Nada nuevo que escribir'; Write-Output 'OK'; exit 0 }

# =========================================================================
# PARTE 2 - Lo que la API COM no expone, escrito directo sobre el .eapx
# =========================================================================

$cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$modelo;")
$cn.Open()
function Exec($sql) { $c = $cn.CreateCommand(); $c.CommandText = $sql; return $c.ExecuteNonQuery() }
function Scalar($sql) { $c = $cn.CreateCommand(); $c.CommandText = $sql; return $c.ExecuteScalar() }

foreach ($pend in $pendientes) {

    # Centro horizontal de cada linea de vida de ESTE diagrama.
    $cx = @{}
    $nombreSql = $pend.dia -replace "'", "''"
    $c = $cn.CreateCommand()
    $c.CommandText = "SELECT Object_ID, (RectLeft + RectRight) / 2 FROM t_diagramobjects WHERE Diagram_ID = (SELECT Diagram_ID FROM t_diagram WHERE Name = '$nombreSql')"
    $r = $c.ExecuteReader()
    while ($r.Read()) { $cx[[int]$r[0]] = [int]$r[1] }
    $r.Close()

    foreach ($x in $pend.geo) {
        $sid = [int](Scalar "SELECT Start_Object_ID FROM t_connector WHERE ea_guid = '$($x.g)'")
        $eid = [int](Scalar "SELECT End_Object_ID FROM t_connector WHERE ea_guid = '$($x.g)'")
        $sx = $cx[$sid]
        $ex = $cx[$eid]
        $tipo = if ($x.ret) { 'Return' } else { 'Call' }
        $flags = if ($x.seq -eq 1) { 'Activation=0;Initiate=1;ForceActivation=0;ExtendActivationUp=0;' } else { 'Activation=0;' }
        [void](Exec "UPDATE t_connector SET SeqNo = $($x.seq), PtStartX = $sx, PtStartY = $($x.y), PtEndX = $ex, PtEndY = $($x.y), PDATA1 = 'Synchronous', PDATA2 = 'retval=void;', PDATA3 = '$tipo', StateFlags = '$flags' WHERE ea_guid = '$($x.g)'")
    }

    foreach ($f in $pend.frags) {
        # NType 0 = alt, PDATA1 = 6, igual que en el archivo de catedra.
        [void](Exec "UPDATE t_object SET NType = 0, PDATA1 = '6' WHERE ea_guid = '$($f.g)'")

        # Los acentos van por parametro, no interpolados en el SQL: por
        # concatenacion el proveedor ACE los manda en la codificacion ANSI del
        # sistema y llegan rotos.
        $ya = [int](Scalar "SELECT Count(*) FROM t_xref WHERE Client = '$($f.g)' AND Name = 'Partitions'")
        if ($ya -eq 0) {
            $gx = '{' + [guid]::NewGuid().ToString().ToUpper() + '}'
            $ins = $cn.CreateCommand()
            $ins.CommandText = "INSERT INTO t_xref (XrefID, Name, Type, Visibility, Client, Description) VALUES ('$gx', 'Partitions', 'element property', 'Public', '$($f.g)', ?)"
            [void]$ins.Parameters.AddWithValue('d', $f.par)
            [void]$ins.ExecuteNonQuery()
        } else {
            $upd = $cn.CreateCommand()
            $upd.CommandText = "UPDATE t_xref SET Description = ? WHERE Client = '$($f.g)' AND Name = 'Partitions'"
            [void]$upd.Parameters.AddWithValue('d', $f.par)
            [void]$upd.ExecuteNonQuery()
        }
    }

    Write-Output "  $($pend.dia) : geometria, retornos y operandos escritos"
}

$cn.Close()
Write-Output 'OK'
