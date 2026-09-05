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
