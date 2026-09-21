param(
    # Borra el paquete de este capítulo y lo vuelve a generar.
    [switch]$Rehacer,
    # Genera solo este caso de uso (p. ej. -CU CU-03). Vacío = todos.
    [string]$CU = '',
    # Para probar sobre una copia sin tocar el modelo bueno.
    [string]$Modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
)

# =========================================================================
# CAP. 3 - 3.2 DIAGRAMA DE ESTADO  (uno POR CASO DE USO TRANSACCIONAL)
#
# ---- DE DÓNDE SALE ESTE FORMATO ----
#   Del ejemplo de cátedra, pág. 10 de «todos los diagramas.pdf», titulado
#   `CU1`. OJO: NO es el ciclo de vida de un objeto. Es el FLUJO DE UNA
#   TRANSACCIÓN, y va uno por caso de uso transaccional:
#
#       Inicio -> Autenticar -> Seleccionar operacion
#              -[listar|crear|modificar|eliminar]-> ... -> Transaccion
#              completada -> Fin
#
#   Los estados son ACTIVIDADES de la transacción (capturar, validar,
#   escribir), no valores de una columna. Las guardas son las condiciones
#   reales que evalúa el código, entre corchetes, y el estado sumidero
#   siempre es `Transaccion completada` seguido del estado final.
#
#   Corrección de la ingeniera del 15/09/2026: estado, tiempo y secuencia se
#   hacen SOLO de los casos de uso transaccionales, en los tres ciclos.
#   Quedan fuera las consultas puras (en el Ciclo 2: CU-14, CU-17, CU-18 y
#   CU-19).
#
# ---- DE DÓNDE SALE EL CONTENIDO ----
#   backend/app/modules/<módulo>/service.py -> cada `raise` es una guarda de
#     rechazo y cada `db.commit()` es la llegada a `Transaccion completada`.
#   backend/app/modules/<módulo>/router.py  -> el endpoint que dispara cada
#     rama del menú de operaciones.
#   backend/app/core/dependencies.py:110    -> `requiere_roles`, que es la
#     guarda del primer estado en todos los CU con sesión.
#
#   LAS RUTAS SE ESCRIBEN SIN EL PREFIJO `/api/v1`, que lo llevan todas
#   (core/config.py:19). Va dicho en la nota de cada diagrama.
#
# ---- EN QUÉ SE APARTA DEL EJEMPLO, Y POR QUÉ ----
#   1. Cada rótulo lleva su ancla al código entre llaves ({service.py:374},
#      {POST /usuarios}). El ejemplo no las tiene; acá sí, porque es lo que
#      hace defendible el diagrama: se puede abrir el archivo y mostrar la
#      línea.
#   2. El ejemplo repite `[correcto]`/`[incorrecto]` sin decir qué compara.
#      Acá la guarda es la condición literal del `if` que la produce.
#   3. Los rechazos van a UN sumidero (`Informar error`) y vuelven al menú
#      por UNA sola flecha. Si cada uno volviera por su cuenta al estado que
#      lo produjo, habría dos flechas entre las mismas dos cajas y EA
#      escribiría los dos rótulos en el mismo punto medio.
#
# ADITIVO: abre el modelo y solo agrega los diagramas que faltan.
# =========================================================================

$ErrorActionPreference = 'Stop'
if (-not (Test-Path $Modelo)) { throw "No existe $Modelo" }

$NOMBRE_PKG = '3.2 Diagramas de Estado'

# ---- Constantes de dibujo (todas juntas, arriba) ----
$W_EST   = 230; $H_EST  = 60       # caja de estado
$W_NODO  = 30;  $H_NODO = 30       # pseudoestado inicial / estado final
$SUB_INI = 100                     # StateNode.Subtype = pseudoestado inicial
$SUB_FIN = 101                     # StateNode.Subtype = estado final

# LAS POSICIONES NO SE ESCRIBEN A MANO. Cada estado declara su COLUMNA y su
# FILA, y el generador calcula l y t. Con dieciocho casos de uso, poner las
# coordenadas una por una era garantía de error.
#
# El hueco entre `menu` y `oper` tiene que ser el más ancho de todos: por ahí
# salen las cinco flechas del menú de operaciones y ahí se dibujan sus
# rótulos, que son los más largos del diagrama.
$COL = @{ auth = 120; menu = 520; oper = 1120; vali = 1620; fin = 2080 }
$Y0    = -40                       # fila 0
$PASO  = 180                       # alto de una fila

# =========================================================================
# LOS DATOS: un bloque por caso de uso transaccional.
#
#   estados      -> n (nombre), col, fila (admite medios: 1.5), nota
#   transiciones -> d (desde), h (hasta), e (rótulo: guarda + ancla al código)
#
#   '(inicial)', '(final)' y '(final-rechazo)' son los pseudoestados; se
#   crean solos y se colocan solos. El de rechazo solo si alguien lo usa.
# =========================================================================

# Atajo: casi todos los CU de gestión terminan igual.
# Misma razón que la del sumidero de errores, un piso más abajo: con el cierre
# en la fila 2, el conector `oper/3 -> fin` comparte punto medio con el
# `Validar -> Informar error`, que es vertical y cae en la misma x. El medio
# punto los separa.
$FIN_OK = @{ n = 'Transaccion completada'; col = 'fin'; fila = 2.5
             nota = 'Es el db.commit() del bloque try/except de cada rama.' }
# La fila 3.5 no es capricho. `Informar error` vuelve al menú, y ese conector
# tiene su punto medio a media altura entre los dos. Con el error en la fila 3
# ese punto medio cae EXACTAMENTE sobre el de la rama `menu -> oper/3`, y los
# dos rótulos se dibujan encimados. El medio punto los separa 45 px.
$ERR    = @{ n = 'Informar error'; col = 'vali'; fila = 3.5
             nota = 'Sumidero de los rechazos. Es el _traducir() del router, que convierte cada error de gestion en su HTTPException.' }

$CASOS = @(

    # ================= CICLO 1 =================================

    @{
        cu = 'CU-01'; ciclo = '#1'; titulo = 'Registrar cliente'
        nota = 'Flujo transaccional de CU-01. Unico caso de uso del Ciclo 1 SIN autenticacion previa: la vitrina es publica. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Abrir formulario de registro'; col = 'auth'; fila = 1
               nota = 'features/auth/registro/registro.ts. No exige sesion.' },
            @{ n = 'Capturar datos de registro'; col = 'oper'; fila = 0
               nota = 'Correo, documento, nombres y contrasena.' },
            @{ n = 'Validar datos'; col = 'vali'; fila = 0.5
               nota = 'seguridad/service.py:92, :97 y :101.' },
            @{ n = 'Crear usuario y ficha de cliente'; col = 'oper'; fila = 2
               nota = 'Las dos filas en la MISMA transaccion. service.py:120.' },
            @{ n = 'Informar error'; col = 'vali'; fila = 2
               nota = 'Sumidero de los rechazos. _traducir(), seguridad/router.py:160.' },
            @{ n = 'Transaccion completada'; col = 'fin'; fila = 1
               nota = 'db.commit() de service.py:120. El cliente ya puede iniciar sesion.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Abrir formulario de registro'; e = '' },
            @{ d = 'Abrir formulario de registro'; h = 'Capturar datos de registro'
               e = '[el visitante elige crear cuenta]' },
            @{ d = 'Capturar datos de registro'; h = 'Validar datos'
               e = '[llenar datos]  {POST /auth/registro}' },
            @{ d = 'Validar datos'; h = 'Crear usuario y ficha de cliente'
               e = '[correo y documento libres]  {service.py:92 y :97}' },
            @{ d = 'Validar datos'; h = 'Informar error'
               e = '[correo o documento ya registrado]  {409 service.py:92 y :97}' },
            @{ d = 'Crear usuario y ficha de cliente'; h = 'Transaccion completada'
               e = '{service.py:120}' },
            @{ d = 'Informar error'; h = 'Capturar datos de registro'; e = 'reintentar()' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-02'; ciclo = '#1'; titulo = 'Iniciar y cerrar sesion'
        nota = 'Flujo transaccional de CU-02. Las dos ramas escriben: iniciar emite un sesion_token, cerrar lo revoca. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Seleccionar operacion'; col = 'menu'; fila = 1
               nota = 'features/auth/login/login.ts, o el boton de salir del layout.' },
            @{ n = 'Capturar credenciales'; col = 'oper'; fila = 0
               nota = 'Correo y contrasena.' },
            @{ n = 'Verificar credenciales'; col = 'oper'; fila = 1
               nota = 'verify_password y el estado de la cuenta. service.py:195 y :198.' },
            @{ n = 'Revocar token'; col = 'oper'; fila = 3
               nota = 'cerrar_sesion, service.py:251. Marca revocado el jti del token.' },
            @{ n = 'Emitir token'; col = 'vali'; fila = 0.5
               nota = 'Crea la fila de sesion_token con su jti y su expiracion. service.py:211.' },
            @{ n = 'Informar error'; col = 'vali'; fila = 3
               nota = 'Sumidero de los rechazos. _traducir(), seguridad/router.py:160.' },
            @{ n = 'Transaccion completada'; col = 'fin'; fila = 1
               nota = 'db.commit(). El token ya es aceptado, o ya dejo de serlo.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Seleccionar operacion'; e = '' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar credenciales'
               e = '[iniciar sesion]  {POST /auth/sesion}' },
            @{ d = 'Seleccionar operacion'; h = 'Revocar token'
               e = '[cerrar sesion]  {DELETE /auth/sesion}' },
            @{ d = 'Capturar credenciales'; h = 'Verificar credenciales'; e = '[enviar]' },
            @{ d = 'Verificar credenciales'; h = 'Emitir token'
               e = '[credenciales validas y cuenta activa]  {service.py:195}' },
            @{ d = 'Verificar credenciales'; h = 'Informar error'
               e = '[invalidas o cuenta desactivada]  {401 service.py:195 y :198}' },
            @{ d = 'Emitir token'; h = 'Transaccion completada'; e = '{service.py:211}' },
            @{ d = 'Revocar token'; h = 'Transaccion completada'; e = '{service.py:251}' },
            @{ d = 'Informar error'; h = 'Capturar credenciales'; e = 'reintentar()' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-03'; ciclo = '#1'; titulo = 'Gestionar usuarios y roles'
        nota = 'Flujo transaccional de CU-03. Las guardas son las condiciones reales de backend/app/modules/seguridad/service.py. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Autenticar Administrador'; col = 'auth'; fila = 2
               nota = 'requiere_roles("ADMINISTRADOR") en core/dependencies.py:110. Sin rol, 403.' },
            @{ n = 'Seleccionar operacion'; col = 'menu'; fila = 2
               nota = 'Pantalla /admin/usuarios. Cada rama es un endpoint distinto.' },
            @{ n = 'Desplegar lista de usuarios'; col = 'oper'; fila = 0
               nota = 'Unica rama de solo lectura del CU. listar_usuarios, service.py:326.' },
            @{ n = 'Capturar datos del usuario'; col = 'oper'; fila = 1
               nota = 'Formulario de alta. usuario-formulario.ts.' },
            @{ n = 'Capturar cambios'; col = 'oper'; fila = 2
               nota = 'Mismo formulario, en modo edicion. editar_usuario, service.py:419.' },
            @{ n = 'Confirmar cambio de estado'; col = 'oper'; fila = 3
               nota = 'Activar o desactivar. cambiar_estado, service.py:477.' },
            @{ n = 'Identificar usuario a eliminar'; col = 'oper'; fila = 4
               nota = 'eliminar_usuario, service.py:507.' },
            @{ n = 'Validar datos'; col = 'vali'; fila = 1.5
               nota = 'Correo libre y rol existente. service.py:374 y :378.' },
            @{ n = 'Eliminar Usuario'; col = 'vali'; fila = 4
               nota = 'Solo si no tiene operaciones asociadas. service.py:523.' },
            $ERR, $FIN_OK
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Autenticar Administrador'; e = '' },
            @{ d = 'Autenticar Administrador'; h = 'Seleccionar operacion'
               e = '[rol ADMINISTRADOR]  {dependencies.py:110}' },
            @{ d = 'Autenticar Administrador'; h = '(final-rechazo)'
               e = '[rol distinto]  {403 dependencies.py:119}' },
            @{ d = 'Seleccionar operacion'; h = 'Desplegar lista de usuarios'
               e = '[listar]  {GET /usuarios}' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar datos del usuario'
               e = '[crear]  {POST /usuarios}' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar cambios'
               e = '[modificar]  {PATCH /usuarios/:id}' },
            @{ d = 'Seleccionar operacion'; h = 'Confirmar cambio de estado'
               e = '[activar o desactivar]  {PATCH /usuarios/:id/estado}' },
            @{ d = 'Seleccionar operacion'; h = 'Identificar usuario a eliminar'
               e = '[eliminar]  {DELETE /usuarios/:id}' },
            @{ d = 'Desplegar lista de usuarios'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Capturar datos del usuario'; h = 'Validar datos'; e = '[llenar datos]' },
            @{ d = 'Capturar cambios';           h = 'Validar datos'; e = '[llenar datos]' },
            @{ d = 'Validar datos'; h = 'Transaccion completada'
               e = '[correo libre y rol existente]  {service.py:374}' },
            @{ d = 'Validar datos'; h = 'Informar error'
               e = '[correo ya registrado]  {409 service.py:374}' },
            @{ d = 'Confirmar cambio de estado'; h = 'Transaccion completada'
               e = '[no es su propia cuenta]  {service.py:493}' },
            @{ d = 'Confirmar cambio de estado'; h = 'Informar error'
               e = '[intenta desactivarse a si mismo]  {409 service.py:493}' },
            @{ d = 'Identificar usuario a eliminar'; h = 'Eliminar Usuario'
               e = '[sin operaciones asociadas]  {service.py:523}' },
            @{ d = 'Identificar usuario a eliminar'; h = 'Informar error'
               e = '[tiene operaciones asociadas]  {409 service.py:523}' },
            @{ d = 'Eliminar Usuario'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Informar error'; h = 'Seleccionar operacion'
               e = 'reintentar()  {_traducir(), router.py:160}' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-04'; ciclo = '#1'; titulo = 'Gestionar perfil del cliente'
        nota = 'Flujo transaccional de CU-04. Todo el perfil cuelga de un router propio que exige rol CLIENTE. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Autenticar Cliente'; col = 'auth'; fila = 2
               nota = 'perfil_router exige requiere_roles("CLIENTE"). seguridad/router.py:302.' },
            @{ n = 'Seleccionar operacion'; col = 'menu'; fila = 2
               nota = 'Pantalla /mi-cuenta.' },
            @{ n = 'Desplegar perfil'; col = 'oper'; fila = 0
               nota = 'Unica rama de solo lectura. obtener_perfil, service.py:615.' },
            @{ n = 'Capturar cambios del perfil'; col = 'oper'; fila = 1
               nota = 'editar_perfil, service.py:663.' },
            @{ n = 'Capturar direccion'; col = 'oper'; fila = 2
               nota = 'agregar_direccion, service.py:729. Un cliente puede tener varias.' },
            @{ n = 'Capturar contrasena'; col = 'oper'; fila = 3
               nota = 'cambiar_contrasena, service.py:812.' },
            @{ n = 'Elegir categorias preferidas'; col = 'oper'; fila = 4
               nota = 'guardar_preferencias, service.py:635. Alimenta las recomendaciones del Ciclo 3.' },
            @{ n = 'Validar datos'; col = 'vali'; fila = 1.5
               nota = 'service.py:678 (correo), :741 (ciudad), :824 (contrasena actual), :656 (categoria).' },
            $ERR, $FIN_OK
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Autenticar Cliente'; e = '' },
            @{ d = 'Autenticar Cliente'; h = 'Seleccionar operacion'
               e = '[rol CLIENTE]  {dependencies.py:110}' },
            @{ d = 'Autenticar Cliente'; h = '(final-rechazo)'
               e = '[rol distinto]  {403 dependencies.py:119}' },
            @{ d = 'Seleccionar operacion'; h = 'Desplegar perfil'
               e = '[ver perfil]  {GET /perfil}' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar cambios del perfil'
               e = '[editar datos]  {PATCH /perfil}' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar direccion'
               e = '[agregar direccion]  {POST /perfil/direcciones}' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar contrasena'
               e = '[cambiar contrasena]  {POST /perfil/contrasena}' },
            @{ d = 'Seleccionar operacion'; h = 'Elegir categorias preferidas'
               e = '[guardar preferencias]  {PUT /perfil/preferencias}' },
            @{ d = 'Desplegar perfil'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Capturar cambios del perfil'; h = 'Validar datos'; e = '[llenar datos]' },
            @{ d = 'Capturar direccion';          h = 'Validar datos'; e = '[llenar datos]' },
            @{ d = 'Capturar contrasena';         h = 'Validar datos'; e = '[llenar datos]' },
            @{ d = 'Elegir categorias preferidas'; h = 'Validar datos'; e = '[elegir]' },
            @{ d = 'Validar datos'; h = 'Transaccion completada'
               e = '[datos coherentes]  {service.py:678, :741 y :824}' },
            @{ d = 'Validar datos'; h = 'Informar error'
               e = '[correo duplicado, ciudad inexistente o contrasena incorrecta]  {409/404/400 service.py:678, :741 y :824}' },
            @{ d = 'Informar error'; h = 'Seleccionar operacion'
               e = 'reintentar()  {_traducir_perfil(), router.py:313}' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-05'; ciclo = '#1'; titulo = 'Gestionar ciudades y sucursales'
        nota = 'Flujo transaccional de CU-05. Las dos entidades las atiende el mismo modulo: organizacion/service.py. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Autenticar Administrador'; col = 'auth'; fila = 2
               nota = 'requiere_roles("ADMINISTRADOR"). core/dependencies.py:110.' },
            @{ n = 'Seleccionar operacion'; col = 'menu'; fila = 2
               nota = 'Pantallas /admin/ciudades y /admin/sucursales.' },
            @{ n = 'Desplegar ciudades y sucursales'; col = 'oper'; fila = 0
               nota = 'listar_ciudades service.py:91 y listar_sucursales service.py:198.' },
            @{ n = 'Capturar ciudad'; col = 'oper'; fila = 1
               nota = 'crear_ciudad service.py:103 y editar_ciudad service.py:127.' },
            @{ n = 'Capturar sucursal'; col = 'oper'; fila = 2
               nota = 'crear_sucursal service.py:221 y editar_sucursal service.py:263. Valida el horario.' },
            @{ n = 'Confirmar cambio de estado'; col = 'oper'; fila = 3
               nota = 'cambiar_estado_sucursal, service.py:321.' },
            @{ n = 'Identificar ciudad a eliminar'; col = 'oper'; fila = 4
               nota = 'eliminar_ciudad, service.py:156.' },
            @{ n = 'Validar datos'; col = 'vali'; fila = 1.5
               nota = 'Nombre libre en la ciudad y horario coherente. service.py:106, :234 y :254.' },
            @{ n = 'Eliminar ciudad'; col = 'vali'; fila = 4
               nota = 'Solo si no tiene sucursales activas ni historial. service.py:169 y :171.' },
            $ERR, $FIN_OK
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Autenticar Administrador'; e = '' },
            @{ d = 'Autenticar Administrador'; h = 'Seleccionar operacion'
               e = '[rol ADMINISTRADOR]  {dependencies.py:110}' },
            @{ d = 'Autenticar Administrador'; h = '(final-rechazo)'
               e = '[rol distinto]  {403 dependencies.py:119}' },
            @{ d = 'Seleccionar operacion'; h = 'Desplegar ciudades y sucursales'
               e = '[listar]  {GET /organizacion/ciudades}' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar ciudad'
               e = '[crear o modificar ciudad]  {POST /organizacion/ciudades}' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar sucursal'
               e = '[crear o modificar sucursal]  {POST /organizacion/sucursales}' },
            @{ d = 'Seleccionar operacion'; h = 'Confirmar cambio de estado'
               e = '[activar o desactivar sucursal]  {PATCH /organizacion/sucursales/:id/estado}' },
            @{ d = 'Seleccionar operacion'; h = 'Identificar ciudad a eliminar'
               e = '[eliminar ciudad]  {DELETE /organizacion/ciudades/:id}' },
            @{ d = 'Desplegar ciudades y sucursales'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Capturar ciudad';   h = 'Validar datos'; e = '[llenar datos]' },
            @{ d = 'Capturar sucursal'; h = 'Validar datos'; e = '[llenar datos]' },
            @{ d = 'Validar datos'; h = 'Transaccion completada'
               e = '[nombre libre en la ciudad y horario valido]  {service.py:234 y :254}' },
            @{ d = 'Validar datos'; h = 'Informar error'
               e = '[nombre duplicado u horario invalido]  {409/400 service.py:106, :234 y :254}' },
            @{ d = 'Confirmar cambio de estado'; h = 'Transaccion completada'
               e = '[la sucursal existe]  {service.py:332}' },
            @{ d = 'Identificar ciudad a eliminar'; h = 'Eliminar ciudad'
               e = '[sin sucursales activas ni historial]  {service.py:169 y :171}' },
            @{ d = 'Identificar ciudad a eliminar'; h = 'Informar error'
               e = '[tiene sucursales activas o historial]  {409 service.py:169 y :171}' },
            @{ d = 'Eliminar ciudad'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Informar error'; h = 'Seleccionar operacion'
               e = 'reintentar()  {_traducir(), organizacion/router.py:59}' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-06'; ciclo = '#1'; titulo = 'Gestionar empleados'
        nota = 'Flujo transaccional de CU-06. Dar de alta un empleado crea tambien su usuario, en la MISMA transaccion. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Autenticar Administrador'; col = 'auth'; fila = 1.5
               nota = 'requiere_roles("ADMINISTRADOR"). core/dependencies.py:110.' },
            @{ n = 'Seleccionar operacion'; col = 'menu'; fila = 1.5
               nota = 'Pantalla /admin/empleados.' },
            @{ n = 'Desplegar empleados'; col = 'oper'; fila = 0
               nota = 'listar_empleados, empleados/service.py:114.' },
            @{ n = 'Capturar datos del empleado'; col = 'oper'; fila = 1
               nota = 'crear_empleado, empleados/service.py:161. Vincula un usuario existente o crea uno.' },
            @{ n = 'Capturar cambios'; col = 'oper'; fila = 2
               nota = 'editar_empleado, empleados/service.py:238. Permite reasignar sucursal.' },
            @{ n = 'Confirmar baja'; col = 'oper'; fila = 3
               nota = 'dar_de_baja, empleados/service.py:317. Revoca sus sesiones vigentes.' },
            @{ n = 'Validar datos'; col = 'vali'; fila = 1.5
               nota = 'Documento libre, sucursal activa y usuario vinculable. empleados/service.py:173, :157 y :186.' },
            $ERR, $FIN_OK
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Autenticar Administrador'; e = '' },
            @{ d = 'Autenticar Administrador'; h = 'Seleccionar operacion'
               e = '[rol ADMINISTRADOR]  {dependencies.py:110}' },
            @{ d = 'Autenticar Administrador'; h = '(final-rechazo)'
               e = '[rol distinto]  {403 dependencies.py:119}' },
            @{ d = 'Seleccionar operacion'; h = 'Desplegar empleados'
               e = '[listar]  {GET /organizacion/empleados}' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar datos del empleado'
               e = '[crear]  {POST /organizacion/empleados}' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar cambios'
               e = '[modificar o reasignar]  {PATCH /organizacion/empleados/:id}' },
            @{ d = 'Seleccionar operacion'; h = 'Confirmar baja'
               e = '[dar de baja]  {POST /organizacion/empleados/:id/baja}' },
            @{ d = 'Desplegar empleados'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Capturar datos del empleado'; h = 'Validar datos'; e = '[llenar datos]' },
            @{ d = 'Capturar cambios';            h = 'Validar datos'; e = '[llenar datos]' },
            @{ d = 'Validar datos'; h = 'Transaccion completada'
               e = '[documento libre y sucursal activa]  {empleados/service.py:173 y :157}' },
            @{ d = 'Validar datos'; h = 'Informar error'
               e = '[documento duplicado, sucursal inactiva o usuario no vinculable]  {409 empleados/service.py:173, :158 y :186}' },
            @{ d = 'Confirmar baja'; h = 'Transaccion completada'
               e = '[no estaba dado de baja y la fecha es valida]  {empleados/service.py:328 y :332}' },
            @{ d = 'Confirmar baja'; h = 'Informar error'
               e = '[ya dado de baja o fecha invalida]  {409 empleados/service.py:328 y :332}' },
            @{ d = 'Informar error'; h = 'Seleccionar operacion'
               e = 'reintentar()  {_traducir(), empleados/router.py:40}' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-07'; ciclo = '#1'; titulo = 'Gestionar proveedores'
        nota = 'Flujo transaccional de CU-07. Habilitar el acceso le crea al proveedor un usuario con rol PROVEEDOR. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Autenticar Administrador'; col = 'auth'; fila = 2
               nota = 'requiere_roles("ADMINISTRADOR"). core/dependencies.py:110.' },
            @{ n = 'Seleccionar operacion'; col = 'menu'; fila = 2
               nota = 'Pantalla /admin/proveedores.' },
            @{ n = 'Desplegar proveedores'; col = 'oper'; fila = 0
               nota = 'listar, proveedores_service.py:95.' },
            @{ n = 'Capturar datos del proveedor'; col = 'oper'; fila = 1
               nota = 'crear, proveedores_service.py:127.' },
            @{ n = 'Capturar cambios'; col = 'oper'; fila = 2
               nota = 'editar, proveedores_service.py:163.' },
            @{ n = 'Confirmar cambio de estado'; col = 'oper'; fila = 3
               nota = 'cambiar_estado, proveedores_service.py:206.' },
            @{ n = 'Habilitar acceso'; col = 'oper'; fila = 4
               nota = 'habilitar_acceso, proveedores_service.py:230. Le crea el usuario con rol PROVEEDOR.' },
            @{ n = 'Validar datos'; col = 'vali'; fila = 1.5
               nota = 'Identificacion tributaria libre. proveedores_service.py:134.' },
            $ERR, $FIN_OK
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Autenticar Administrador'; e = '' },
            @{ d = 'Autenticar Administrador'; h = 'Seleccionar operacion'
               e = '[rol ADMINISTRADOR]  {dependencies.py:110}' },
            @{ d = 'Autenticar Administrador'; h = '(final-rechazo)'
               e = '[rol distinto]  {403 dependencies.py:119}' },
            @{ d = 'Seleccionar operacion'; h = 'Desplegar proveedores'
               e = '[listar]  {GET /organizacion/proveedores}' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar datos del proveedor'
               e = '[crear]  {POST /organizacion/proveedores}' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar cambios'
               e = '[modificar]  {PATCH /organizacion/proveedores/:id}' },
            @{ d = 'Seleccionar operacion'; h = 'Confirmar cambio de estado'
               e = '[activar o desactivar]  {PATCH /organizacion/proveedores/:id/estado}' },
            @{ d = 'Seleccionar operacion'; h = 'Habilitar acceso'
               e = '[dar acceso al portal]  {POST /organizacion/proveedores/:id/acceso}' },
            @{ d = 'Desplegar proveedores'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Capturar datos del proveedor'; h = 'Validar datos'; e = '[llenar datos]' },
            @{ d = 'Capturar cambios';             h = 'Validar datos'; e = '[llenar datos]' },
            @{ d = 'Validar datos'; h = 'Transaccion completada'
               e = '[identificacion tributaria libre]  {proveedores_service.py:134}' },
            @{ d = 'Validar datos'; h = 'Informar error'
               e = '[identificacion duplicada]  {409 proveedores_service.py:134}' },
            @{ d = 'Confirmar cambio de estado'; h = 'Transaccion completada'
               e = '[el proveedor existe]  {proveedores_service.py:216}' },
            @{ d = 'Habilitar acceso'; h = 'Transaccion completada'
               e = '[no tenia acceso y el correo esta libre]  {proveedores_service.py:244 y :247}' },
            @{ d = 'Habilitar acceso'; h = 'Informar error'
               e = '[acceso ya habilitado o correo ya registrado]  {409 proveedores_service.py:244 y :247}' },
            @{ d = 'Informar error'; h = 'Seleccionar operacion'
               e = 'reintentar()  {_traducir(), proveedores_router.py:52}' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-08'; ciclo = '#1'; titulo = 'Gestionar categorias, tallas y colores'
        nota = 'Flujo transaccional de CU-08. Los tres maestros comparten modulo y forma; la categoria ademas es jerarquica. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Autenticar Administrador'; col = 'auth'; fila = 2
               nota = 'requiere_roles("ADMINISTRADOR"). core/dependencies.py:110.' },
            @{ n = 'Seleccionar operacion'; col = 'menu'; fila = 2
               nota = 'Pantalla /admin/maestros, con una pestana por maestro.' },
            @{ n = 'Desplegar maestros'; col = 'oper'; fila = 0
               nota = 'listar_categorias :108, listar_tallas :260 y listar_colores :361. El arbol lo arma _armar_arbol, :82.' },
            @{ n = 'Capturar categoria'; col = 'oper'; fila = 1
               nota = 'crear_categoria :129 y editar_categoria :160. Comprueba ciclos en la jerarquia.' },
            @{ n = 'Capturar talla o color'; col = 'oper'; fila = 2
               nota = 'crear_talla :273, crear_color :368 y sus ediciones.' },
            @{ n = 'Confirmar cambio de estado'; col = 'oper'; fila = 3
               nota = 'cambiar_estado_categoria :212, _talla :327 y _color :418.' },
            @{ n = 'Identificar elemento a eliminar'; col = 'oper'; fila = 4
               nota = 'eliminar_categoria :235, _talla :343 y _color :433.' },
            @{ n = 'Validar datos'; col = 'vali'; fila = 1.5
               nota = 'Nombre libre entre hermanas y sin ciclo. maestros/service.py:137 y :179.' },
            @{ n = 'Eliminar elemento'; col = 'vali'; fila = 4
               nota = 'Solo si nada lo referencia. maestros/service.py:242.' },
            $ERR, $FIN_OK
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Autenticar Administrador'; e = '' },
            @{ d = 'Autenticar Administrador'; h = 'Seleccionar operacion'
               e = '[rol ADMINISTRADOR]  {dependencies.py:110}' },
            @{ d = 'Autenticar Administrador'; h = '(final-rechazo)'
               e = '[rol distinto]  {403 dependencies.py:119}' },
            @{ d = 'Seleccionar operacion'; h = 'Desplegar maestros'
               e = '[listar]  {GET /catalogo/categorias}' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar categoria'
               e = '[crear o modificar categoria]  {POST /catalogo/categorias}' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar talla o color'
               e = '[crear o modificar talla o color]  {POST /catalogo/tallas}' },
            @{ d = 'Seleccionar operacion'; h = 'Confirmar cambio de estado'
               e = '[activar o desactivar]  {PATCH /catalogo/categorias/:id/estado}' },
            @{ d = 'Seleccionar operacion'; h = 'Identificar elemento a eliminar'
               e = '[eliminar]  {DELETE /catalogo/categorias/:id}' },
            @{ d = 'Desplegar maestros'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Capturar categoria';     h = 'Validar datos'; e = '[llenar datos]' },
            @{ d = 'Capturar talla o color'; h = 'Validar datos'; e = '[llenar datos]' },
            @{ d = 'Validar datos'; h = 'Transaccion completada'
               e = '[nombre libre y sin ciclo en la jerarquia]  {service.py:137 y :179}' },
            @{ d = 'Validar datos'; h = 'Informar error'
               e = '[nombre duplicado o el padre es descendiente]  {409 service.py:137 y :179}' },
            @{ d = 'Confirmar cambio de estado'; h = 'Transaccion completada'
               e = '[el elemento existe]  {service.py:223}' },
            @{ d = 'Identificar elemento a eliminar'; h = 'Eliminar elemento'
               e = '[sin dependencias]  {service.py:242}' },
            @{ d = 'Identificar elemento a eliminar'; h = 'Informar error'
               e = '[tiene dependencias]  {409 service.py:242}' },
            @{ d = 'Eliminar elemento'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Informar error'; h = 'Seleccionar operacion'
               e = 'reintentar()  {_traducir(), maestros/router.py:43}' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-09'; ciclo = '#1'; titulo = 'Gestionar temporadas y colecciones'
        nota = 'Flujo transaccional de CU-09. Dos temporadas activas no pueden solaparse en el calendario. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Autenticar Administrador'; col = 'auth'; fila = 2
               nota = 'requiere_roles("ADMINISTRADOR"). core/dependencies.py:110.' },
            @{ n = 'Seleccionar operacion'; col = 'menu'; fila = 2
               nota = 'Pantalla /admin/temporadas.' },
            @{ n = 'Desplegar temporadas'; col = 'oper'; fila = 0
               nota = 'listar_temporadas :97 y listar_colecciones :309.' },
            @{ n = 'Capturar temporada'; col = 'oper'; fila = 1
               nota = 'crear_temporada :137 y editar_temporada :181.' },
            @{ n = 'Capturar coleccion'; col = 'oper'; fila = 2
               nota = 'crear_coleccion :331 y editar_coleccion :362.' },
            @{ n = 'Confirmar cambio de estado'; col = 'oper'; fila = 3
               nota = 'cambiar_estado_temporada :241 y _coleccion :406.' },
            @{ n = 'Identificar temporada a eliminar'; col = 'oper'; fila = 4
               nota = 'eliminar_temporada, temporadas_service.py:273.' },
            @{ n = 'Validar datos'; col = 'vali'; fila = 1.5
               nota = 'Nombre libre, rango coherente y sin solapamiento. temporadas_service.py:144, :172 y :134.' },
            @{ n = 'Eliminar temporada'; col = 'vali'; fila = 4
               nota = 'Solo si no tiene colecciones. temporadas_service.py:286.' },
            $ERR, $FIN_OK
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Autenticar Administrador'; e = '' },
            @{ d = 'Autenticar Administrador'; h = 'Seleccionar operacion'
               e = '[rol ADMINISTRADOR]  {dependencies.py:110}' },
            @{ d = 'Autenticar Administrador'; h = '(final-rechazo)'
               e = '[rol distinto]  {403 dependencies.py:119}' },
            @{ d = 'Seleccionar operacion'; h = 'Desplegar temporadas'
               e = '[listar]  {GET /catalogo/temporadas}' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar temporada'
               e = '[crear o modificar temporada]  {POST /catalogo/temporadas}' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar coleccion'
               e = '[crear o modificar coleccion]  {POST /catalogo/colecciones}' },
            @{ d = 'Seleccionar operacion'; h = 'Confirmar cambio de estado'
               e = '[activar o desactivar]  {PATCH /catalogo/temporadas/:id/estado}' },
            @{ d = 'Seleccionar operacion'; h = 'Identificar temporada a eliminar'
               e = '[eliminar]  {DELETE /catalogo/temporadas/:id}' },
            @{ d = 'Desplegar temporadas'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Capturar temporada'; h = 'Validar datos'; e = '[llenar datos]' },
            @{ d = 'Capturar coleccion'; h = 'Validar datos'; e = '[llenar datos]' },
            @{ d = 'Validar datos'; h = 'Transaccion completada'
               e = '[nombre libre, rango valido y sin solapamiento]  {service.py:144, :172 y :134}' },
            @{ d = 'Validar datos'; h = 'Informar error'
               e = '[nombre duplicado, rango invalido o se cruza con otra activa]  {409/400 service.py:144, :172 y :134}' },
            @{ d = 'Confirmar cambio de estado'; h = 'Transaccion completada'
               e = '[la temporada existe]  {service.py:252}' },
            @{ d = 'Identificar temporada a eliminar'; h = 'Eliminar temporada'
               e = '[sin colecciones]  {service.py:286}' },
            @{ d = 'Identificar temporada a eliminar'; h = 'Informar error'
               e = '[tiene colecciones]  {409 service.py:286}' },
            @{ d = 'Eliminar temporada'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Informar error'; h = 'Seleccionar operacion'
               e = 'reintentar()  {_traducir(), temporadas_router.py:48}' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    # ================= CICLO 2 =================================

    @{
        cu = 'CU-10'; ciclo = '#2'; titulo = 'Gestionar productos y variantes'
        nota = 'Flujo transaccional de CU-10. El SKU de cada variante se arma solo, con armar_sku (catalogo/service.py:115). Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Autenticar Administrador'; col = 'auth'; fila = 2
               nota = 'requiere_roles("ADMINISTRADOR"). core/dependencies.py:110.' },
            @{ n = 'Seleccionar operacion'; col = 'menu'; fila = 2
               nota = 'Pantalla /admin/productos.' },
            @{ n = 'Desplegar productos'; col = 'oper'; fila = 0
               nota = 'listar_productos, catalogo/service.py:216.' },
            @{ n = 'Capturar producto'; col = 'oper'; fila = 1
               nota = 'crear_producto :265 y editar_producto :307.' },
            @{ n = 'Generar variantes'; col = 'oper'; fila = 2
               nota = 'generar_variantes :424, el producto cartesiano de tallas por colores.' },
            @{ n = 'Confirmar cambio de estado'; col = 'oper'; fila = 3
               nota = 'cambiar_estado_producto, catalogo/service.py:363.' },
            @{ n = 'Identificar producto a eliminar'; col = 'oper'; fila = 4
               nota = 'eliminar_producto :389 y eliminar_variante :549.' },
            @{ n = 'Validar datos y armar SKU'; col = 'vali'; fila = 1.5
               nota = 'Codigo libre, maestros existentes y SKU que entre. service.py:279, :180 y :133.' },
            @{ n = 'Eliminar producto'; col = 'vali'; fila = 4
               nota = 'Solo si no tiene existencias ni movimientos. service.py:407.' },
            $ERR, $FIN_OK
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Autenticar Administrador'; e = '' },
            @{ d = 'Autenticar Administrador'; h = 'Seleccionar operacion'
               e = '[rol ADMINISTRADOR]  {dependencies.py:110}' },
            @{ d = 'Autenticar Administrador'; h = '(final-rechazo)'
               e = '[rol distinto]  {403 dependencies.py:119}' },
            @{ d = 'Seleccionar operacion'; h = 'Desplegar productos'
               e = '[listar]  {GET /catalogo/productos}' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar producto'
               e = '[crear o modificar]  {POST /catalogo/productos}' },
            @{ d = 'Seleccionar operacion'; h = 'Generar variantes'
               e = '[generar variantes]  {POST /catalogo/productos/:id/variantes/generar}' },
            @{ d = 'Seleccionar operacion'; h = 'Confirmar cambio de estado'
               e = '[activar o desactivar]  {PATCH /catalogo/productos/:id/estado}' },
            @{ d = 'Seleccionar operacion'; h = 'Identificar producto a eliminar'
               e = '[eliminar]  {DELETE /catalogo/productos/:id}' },
            @{ d = 'Desplegar productos'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Capturar producto';  h = 'Validar datos y armar SKU'; e = '[llenar datos]' },
            @{ d = 'Generar variantes';  h = 'Validar datos y armar SKU'; e = '[elegir tallas y colores]' },
            @{ d = 'Validar datos y armar SKU'; h = 'Transaccion completada'
               e = '[codigo libre y maestros existentes]  {service.py:279 y :180}' },
            @{ d = 'Validar datos y armar SKU'; h = 'Informar error'
               e = '[codigo duplicado, maestro inexistente o SKU demasiado largo]  {409/400 service.py:279, :180 y :133}' },
            @{ d = 'Confirmar cambio de estado'; h = 'Transaccion completada'
               e = '[el producto existe]  {service.py:374}' },
            @{ d = 'Identificar producto a eliminar'; h = 'Eliminar producto'
               e = '[sin dependencias]  {service.py:407}' },
            @{ d = 'Identificar producto a eliminar'; h = 'Informar error'
               e = '[tiene existencias o movimientos]  {409 service.py:407}' },
            @{ d = 'Eliminar producto'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Informar error'; h = 'Seleccionar operacion'
               e = 'reintentar()  {_traducir(), catalogo/router.py}' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-11'; ciclo = '#2'; titulo = 'Gestionar imagenes de producto'
        nota = 'Flujo transaccional de CU-11. El archivo va al almacen de objetos y la fila a la base; la imagen del vestidor exige canal alfa. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Autenticar Administrador'; col = 'auth'; fila = 2.5
               nota = 'requiere_roles("ADMINISTRADOR"). core/dependencies.py:110.' },
            @{ n = 'Seleccionar operacion'; col = 'menu'; fila = 2.5
               nota = 'Pantalla /admin/productos, panel de imagenes.' },
            @{ n = 'Desplegar imagenes'; col = 'oper'; fila = 0
               nota = 'listar, imagenes_service.py:129.' },
            @{ n = 'Subir archivo'; col = 'oper'; fila = 1
               nota = 'subir, imagenes_service.py:144. Escribe en el almacen y en la base.' },
            @{ n = 'Marcar principal'; col = 'oper'; fila = 2
               nota = 'marcar_principal, imagenes_service.py:229. Desmarca la anterior.' },
            @{ n = 'Marcar transparente'; col = 'oper'; fila = 3
               nota = 'marcar_transparente, imagenes_service.py:265. Es la del vestidor virtual.' },
            @{ n = 'Reordenar'; col = 'oper'; fila = 4
               nota = 'reordenar, imagenes_service.py:321.' },
            @{ n = 'Identificar imagen a eliminar'; col = 'oper'; fila = 5
               nota = 'eliminar, imagenes_service.py:349. Borra la fila y el objeto.' },
            @{ n = 'Validar imagen'; col = 'vali'; fila = 2
               nota = 'Canal alfa comprobado con _archivo_tiene_transparencia :304, y que la variante sea del producto :124.' },
            @{ n = 'Eliminar imagen'; col = 'vali'; fila = 5
               nota = 'imagenes_service.py:358.' },
            # Fila 4 y no 3.5: la vuelta al menu sale de aqui, y su punto medio
            # tiene que caer en el HUECO entre dos operaciones, no encima de
            # una. Con 3.5 el rotulo aterrizaba sobre `Marcar transparente`.
            @{ n = 'Informar error'; col = 'vali'; fila = 4
               nota = 'Sumidero de los rechazos. _traducir_error_de_archivo, imagenes_service.py:98.' },
            @{ n = 'Transaccion completada'; col = 'fin'; fila = 2.5
               nota = 'db.commit(). El archivo ya esta en el almacen y la fila en la base.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Autenticar Administrador'; e = '' },
            @{ d = 'Autenticar Administrador'; h = 'Seleccionar operacion'
               e = '[rol ADMINISTRADOR]  {dependencies.py:110}' },
            @{ d = 'Autenticar Administrador'; h = '(final-rechazo)'
               e = '[rol distinto]  {403 dependencies.py:119}' },
            @{ d = 'Seleccionar operacion'; h = 'Desplegar imagenes'
               e = '[listar]  {GET /catalogo/productos/:id/imagenes}' },
            @{ d = 'Seleccionar operacion'; h = 'Subir archivo'
               e = '[subir]  {POST /catalogo/productos/:id/imagenes}' },
            @{ d = 'Seleccionar operacion'; h = 'Marcar principal'
               e = '[marcar principal]  {PATCH /catalogo/imagenes/:id/principal}' },
            @{ d = 'Seleccionar operacion'; h = 'Marcar transparente'
               e = '[marcar para el vestidor]  {PATCH /catalogo/imagenes/:id/transparente}' },
            @{ d = 'Seleccionar operacion'; h = 'Reordenar'
               e = '[reordenar]  {PUT /catalogo/productos/:id/imagenes/orden}' },
            @{ d = 'Seleccionar operacion'; h = 'Identificar imagen a eliminar'
               e = '[eliminar]  {DELETE /catalogo/imagenes/:id}' },
            @{ d = 'Desplegar imagenes'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Subir archivo';        h = 'Validar imagen'; e = '[elegir archivo]' },
            @{ d = 'Marcar transparente';  h = 'Validar imagen'; e = '[elegir variante]' },
            @{ d = 'Validar imagen'; h = 'Transaccion completada'
               e = '[tiene canal alfa y la variante es del producto]  {service.py:304 y :124}' },
            @{ d = 'Validar imagen'; h = 'Informar error'
               e = '[sin transparencia o variante ajena]  {400 service.py:284 y :124}' },
            @{ d = 'Marcar principal'; h = 'Transaccion completada'
               e = '[la imagen existe]  {service.py:242}' },
            @{ d = 'Reordenar'; h = 'Transaccion completada'
               e = '[todas las imagenes son del producto]  {service.py:329}' },
            @{ d = 'Identificar imagen a eliminar'; h = 'Eliminar imagen'
               e = '[la imagen existe]  {service.py:358}' },
            @{ d = 'Identificar imagen a eliminar'; h = 'Informar error'
               e = '[imagen inexistente]  {404 service.py:358}' },
            @{ d = 'Eliminar imagen'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Informar error'; h = 'Seleccionar operacion'
               e = 'reintentar()  {imagenes_router.py}' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-13'; ciclo = '#2'; titulo = 'Registrar ingreso de mercaderia'
        nota = 'Flujo transaccional de CU-13. Cada linea del ingreso genera un movimiento INGRESO y sube la existencia de la sucursal. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Autenticar Encargado'; col = 'auth'; fila = 1.5
               nota = 'requiere_roles("ENCARGADO", "ADMINISTRADOR"). core/dependencies.py:110.' },
            @{ n = 'Seleccionar operacion'; col = 'menu'; fila = 1.5
               nota = 'Pantalla /sucursal/inventario.' },
            @{ n = 'Desplegar ingresos'; col = 'oper'; fila = 0
               nota = 'listar_ingresos, inventario/service.py:391.' },
            @{ n = 'Elegir proveedor y sucursal'; col = 'oper'; fila = 1
               nota = 'registrar_ingreso, inventario/service.py:309.' },
            @{ n = 'Capturar lineas del ingreso'; col = 'oper'; fila = 2
               nota = 'Una linea por variante, con su cantidad y su costo.' },
            @{ n = 'Aplicar movimientos de INGRESO'; col = 'oper'; fila = 3
               nota = '_aplicar_movimiento, inventario/service.py:147. Bloquea la fila de existencia (RNF11).' },
            @{ n = 'Validar proveedor y variantes'; col = 'vali'; fila = 1.5
               nota = 'Proveedor activo :322 y :324, variantes validas :274 y :278.' },
            @{ n = 'Informar error'; col = 'vali'; fila = 3.5
               nota = 'Sumidero de los rechazos. _traducir(), inventario/router.py.' },
            @{ n = 'Transaccion completada'; col = 'fin'; fila = 1.5
               nota = 'db.commit(). El stock ya subio y los movimientos quedaron registrados (RNF10).' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Autenticar Encargado'; e = '' },
            @{ d = 'Autenticar Encargado'; h = 'Seleccionar operacion'
               e = '[rol ENCARGADO o ADMINISTRADOR]  {dependencies.py:110}' },
            @{ d = 'Autenticar Encargado'; h = '(final-rechazo)'
               e = '[rol distinto]  {403 dependencies.py:119}' },
            @{ d = 'Seleccionar operacion'; h = 'Desplegar ingresos'
               e = '[listar]  {GET /inventario/ingresos}' },
            @{ d = 'Seleccionar operacion'; h = 'Elegir proveedor y sucursal'
               e = '[registrar ingreso]  {POST /inventario/ingresos}' },
            @{ d = 'Elegir proveedor y sucursal'; h = 'Capturar lineas del ingreso'
               e = '[proveedor elegido]' },
            @{ d = 'Capturar lineas del ingreso'; h = 'Validar proveedor y variantes'
               e = '[llenar lineas]' },
            @{ d = 'Validar proveedor y variantes'; h = 'Aplicar movimientos de INGRESO'
               e = '[proveedor activo y variantes validas]  {service.py:322 y :274}' },
            @{ d = 'Validar proveedor y variantes'; h = 'Informar error'
               e = '[proveedor inactivo o variante inexistente]  {409 service.py:324 y :274}' },
            @{ d = 'Aplicar movimientos de INGRESO'; h = 'Transaccion completada'
               e = '{_aplicar_movimiento, service.py:147}' },
            @{ d = 'Desplegar ingresos'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Informar error'; h = 'Seleccionar operacion'; e = 'reintentar()' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-15'; ciclo = '#2'; titulo = 'Registrar movimiento de inventario'
        nota = 'Flujo transaccional de CU-15. Todo movimiento es inmutable y queda con tipo, motivo, usuario y fecha (RNF10). Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Autenticar Encargado'; col = 'auth'; fila = 1.5
               nota = 'requiere_roles("ENCARGADO", "ADMINISTRADOR"). core/dependencies.py:110.' },
            @{ n = 'Seleccionar operacion'; col = 'menu'; fila = 1.5
               nota = 'Pantalla /sucursal/inventario.' },
            @{ n = 'Desplegar movimientos'; col = 'oper'; fila = 0
               nota = 'listar_movimientos, inventario/service.py:597.' },
            @{ n = 'Capturar ajuste'; col = 'oper'; fila = 1
               nota = 'registrar_ajuste, inventario/service.py:455. Es un conteo fisico.' },
            @{ n = 'Capturar transferencia'; col = 'oper'; fila = 2
               nota = 'registrar_transferencia, inventario/service.py:513. Dos movimientos, una transaccion.' },
            @{ n = 'Fijar stock minimo'; col = 'oper'; fila = 3
               nota = 'fijar_stock_minimo, inventario/service.py:651.' },
            @{ n = 'Validar existencias'; col = 'vali'; fila = 1.5
               nota = 'Conteo mayor que lo reservado :483, con diferencia :492, y stock suficiente :542.' },
            $ERR, $FIN_OK
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Autenticar Encargado'; e = '' },
            @{ d = 'Autenticar Encargado'; h = 'Seleccionar operacion'
               e = '[rol ENCARGADO o ADMINISTRADOR]  {dependencies.py:110}' },
            @{ d = 'Autenticar Encargado'; h = '(final-rechazo)'
               e = '[rol distinto]  {403 dependencies.py:119}' },
            @{ d = 'Seleccionar operacion'; h = 'Desplegar movimientos'
               e = '[listar]  {GET /inventario/movimientos}' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar ajuste'
               e = '[registrar ajuste]  {POST /inventario/movimientos/ajuste}' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar transferencia'
               e = '[registrar transferencia]  {POST /inventario/movimientos/transferencia}' },
            @{ d = 'Seleccionar operacion'; h = 'Fijar stock minimo'
               e = '[fijar stock minimo]  {PATCH /inventario/existencias/:id/stock-minimo}' },
            @{ d = 'Desplegar movimientos'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Capturar ajuste';         h = 'Validar existencias'; e = '[llenar el conteo]' },
            @{ d = 'Capturar transferencia';  h = 'Validar existencias'; e = '[elegir origen y destino]' },
            @{ d = 'Validar existencias'; h = 'Transaccion completada'
               e = '[hay stock y el conteo difiere de lo reservado]  {service.py:483 y :542}' },
            @{ d = 'Validar existencias'; h = 'Informar error'
               e = '[conteo menor que lo reservado, sin diferencia o stock insuficiente]  {409 service.py:483, :492 y :542}' },
            @{ d = 'Fijar stock minimo'; h = 'Transaccion completada'
               e = '[la existencia existe]  {service.py:664}' },
            @{ d = 'Informar error'; h = 'Seleccionar operacion'; e = 'reintentar()' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-16'; ciclo = '#2'; titulo = 'Gestionar disponibilidad de la sucursal'
        nota = 'Flujo transaccional de CU-16. El Encargado solo ve y toca su propia sucursal: el ambito sale del token. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Autenticar Encargado'; col = 'auth'; fila = 1
               nota = 'requiere_roles("ENCARGADO"). El sucursal_id sale del token, no del pedido.' },
            @{ n = 'Seleccionar operacion'; col = 'menu'; fila = 1
               nota = 'Pantalla /sucursal/disponibilidad.' },
            @{ n = 'Desplegar disponibilidad'; col = 'oper'; fila = 0
               nota = 'listar_existencias, inventario/service.py:854. Paginado.' },
            @{ n = 'Capturar stock minimo'; col = 'oper'; fila = 1
               nota = 'fijar_stock_minimo, inventario/service.py:651.' },
            @{ n = 'Revisar alertas de stock'; col = 'oper'; fila = 2
               nota = 'alertas_de_stock, inventario/service.py:674. Compara contra el minimo fijado.' },
            @{ n = 'Validar existencia'; col = 'vali'; fila = 1
               nota = 'inventario/service.py:664.' },
            @{ n = 'Informar error'; col = 'vali'; fila = 2
               nota = 'Sumidero de los rechazos. _traducir(), inventario/router.py.' },
            @{ n = 'Transaccion completada'; col = 'fin'; fila = 1
               nota = 'db.commit(). El minimo ya rige para las alertas.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Autenticar Encargado'; e = '' },
            @{ d = 'Autenticar Encargado'; h = 'Seleccionar operacion'
               e = '[rol ENCARGADO]  {dependencies.py:110}' },
            @{ d = 'Autenticar Encargado'; h = '(final-rechazo)'
               e = '[rol distinto]  {403 dependencies.py:119}' },
            @{ d = 'Seleccionar operacion'; h = 'Desplegar disponibilidad'
               e = '[listar]  {GET /inventario/existencias}' },
            @{ d = 'Seleccionar operacion'; h = 'Capturar stock minimo'
               e = '[fijar minimo]  {PATCH /inventario/existencias/:id/stock-minimo}' },
            @{ d = 'Seleccionar operacion'; h = 'Revisar alertas de stock'
               e = '[ver alertas]  {GET /inventario/alertas}' },
            @{ d = 'Desplegar disponibilidad'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Revisar alertas de stock'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Capturar stock minimo'; h = 'Validar existencia'; e = '[llenar el minimo]' },
            @{ d = 'Validar existencia'; h = 'Transaccion completada'
               e = '[la existencia es de su sucursal]  {service.py:664}' },
            @{ d = 'Validar existencia'; h = 'Informar error'
               e = '[existencia inexistente o ajena]  {404 service.py:664}' },
            @{ d = 'Informar error'; h = 'Seleccionar operacion'; e = 'reintentar()' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-22'; ciclo = '#2'; titulo = 'Crear reserva de prendas'
        nota = 'Flujo transaccional de CU-22. Apartar las unidades y crear la reserva ocurren en la misma transaccion, con la fila de existencia bloqueada (RNF11). Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Autenticar Cliente'; col = 'auth'; fila = 1.5
               nota = 'requiere_roles("CLIENTE"). El cliente_id sale del token.' },
            @{ n = 'Elegir sucursal y franja'; col = 'menu'; fila = 1.5
               nota = 'crear_reserva, reservas/service.py:282.' },
            @{ n = 'Elegir prendas'; col = 'oper'; fila = 0
               nota = 'Una linea por variante. Se comprueba que esten activas :315 y :318.' },
            @{ n = 'Apartar unidades'; col = 'oper'; fila = 2
               nota = 'apartar_para_reserva, inventario/service.py:697. Sube cantidad_reservada.' },
            @{ n = 'Validar franja y stock'; col = 'vali'; fila = 0.5
               nota = 'Franja no pasada :210, no lejana :215, duracion valida :224, dentro de horario :237, vestidor libre :333.' },
            @{ n = 'Informar error'; col = 'vali'; fila = 3.5
               nota = 'Sumidero de los rechazos. _traducir(), reservas/router.py.' },
            @{ n = 'Transaccion completada'; col = 'fin'; fila = 1.5
               nota = 'db.commit(). La reserva queda PENDIENTE y el stock apartado.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Autenticar Cliente'; e = '' },
            @{ d = 'Autenticar Cliente'; h = 'Elegir sucursal y franja'
               e = '[rol CLIENTE]  {dependencies.py:110}' },
            @{ d = 'Autenticar Cliente'; h = '(final-rechazo)'
               e = '[rol distinto]  {403 dependencies.py:119}' },
            @{ d = 'Elegir sucursal y franja'; h = 'Elegir prendas'
               e = '[sucursal activa]  {service.py:302 y :304}' },
            @{ d = 'Elegir prendas'; h = 'Validar franja y stock'
               e = '[confirmar]  {POST /reservas}' },
            @{ d = 'Validar franja y stock'; h = 'Apartar unidades'
               e = '[franja valida, dentro de horario y con vestidor libre]  {service.py:210, :237 y :333}' },
            @{ d = 'Validar franja y stock'; h = 'Informar error'
               e = '[franja en el pasado, fuera de horario o sin vestidores]  {400/409 service.py:210, :237 y :333}' },
            @{ d = 'Apartar unidades'; h = 'Transaccion completada'
               e = '[hay stock disponible]  {inventario/service.py:732}' },
            @{ d = 'Apartar unidades'; h = 'Informar error'
               e = '[stock insuficiente]  {409 inventario/service.py:732}' },
            @{ d = 'Informar error'; h = 'Elegir sucursal y franja'; e = 'reintentar()' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-23'; ciclo = '#2'; titulo = 'Consultar y cancelar reserva'
        nota = 'Flujo transaccional de CU-23. Cancelar devuelve el stock con un movimiento LIBERACION. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Autenticar Cliente'; col = 'auth'; fila = 1
               nota = 'requiere_roles("CLIENTE"). El cliente_id sale del token.' },
            @{ n = 'Seleccionar operacion'; col = 'menu'; fila = 1
               nota = 'Pantalla /mi-cuenta/reservas.' },
            @{ n = 'Desplegar mis reservas'; col = 'oper'; fila = 0
               nota = 'listar_mis_reservas, reservas/service.py:738.' },
            @{ n = 'Elegir reserva a cancelar'; col = 'oper'; fila = 1
               nota = 'cancelar_reserva, reservas/service.py:384.' },
            @{ n = 'Liberar unidades'; col = 'oper'; fila = 2
               nota = 'liberar_de_reserva, inventario/service.py:746. Genera el movimiento LIBERACION.' },
            @{ n = 'Validar propiedad y estado'; col = 'vali'; fila = 1
               nota = 'Que sea suya :413 y que siga viva :419.' },
            @{ n = 'Informar error'; col = 'vali'; fila = 2.5
               nota = 'Sumidero de los rechazos. _traducir(), reservas/router.py.' },
            @{ n = 'Transaccion completada'; col = 'fin'; fila = 1
               nota = 'db.commit(). La reserva queda CANCELADA y el stock devuelto.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Autenticar Cliente'; e = '' },
            @{ d = 'Autenticar Cliente'; h = 'Seleccionar operacion'
               e = '[rol CLIENTE]  {dependencies.py:110}' },
            @{ d = 'Autenticar Cliente'; h = '(final-rechazo)'
               e = '[rol distinto]  {403 dependencies.py:119}' },
            @{ d = 'Seleccionar operacion'; h = 'Desplegar mis reservas'
               e = '[listar]  {GET /reservas}' },
            @{ d = 'Seleccionar operacion'; h = 'Elegir reserva a cancelar'
               e = '[cancelar]  {POST /reservas/:id/cancelacion}' },
            @{ d = 'Desplegar mis reservas'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Elegir reserva a cancelar'; h = 'Validar propiedad y estado'
               e = '[confirmar]' },
            @{ d = 'Validar propiedad y estado'; h = 'Liberar unidades'
               e = '[es su reserva y sigue viva]  {service.py:413 y :419}' },
            @{ d = 'Validar propiedad y estado'; h = 'Informar error'
               e = '[reserva ajena o no cancelable]  {403/409 service.py:413 y :419}' },
            @{ d = 'Liberar unidades'; h = 'Transaccion completada'
               e = '{inventario/service.py:746}' },
            @{ d = 'Informar error'; h = 'Seleccionar operacion'; e = 'reintentar()' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-24'; ciclo = '#2'; titulo = 'Atender reserva en sucursal'
        nota = 'Flujo transaccional de CU-24. Preparar es OPCIONAL: atender_reserva admite cualquier estado vivo. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Autenticar Encargado'; col = 'auth'; fila = 1.5
               nota = 'requiere_roles("ADMINISTRADOR", "ENCARGADO"). La sucursal sale del token.' },
            @{ n = 'Seleccionar operacion'; col = 'menu'; fila = 1.5
               nota = 'Pantalla /sucursal/reservas.' },
            @{ n = 'Desplegar reservas de la sucursal'; col = 'oper'; fila = 0
               nota = 'listar_reservas_de_sucursal, reservas/service.py:585.' },
            @{ n = 'Preparar reserva'; col = 'oper'; fila = 1
               nota = 'preparar_reserva, reservas/service.py:467. Paso OPCIONAL.' },
            @{ n = 'Registrar resultado por prenda'; col = 'oper'; fila = 2
               nota = 'atender_reserva, reservas/service.py:489. Una marca por cada prenda.' },
            @{ n = 'Validar estado y resultados'; col = 'vali'; fila = 1.5
               nota = 'Reserva viva :533, todas las prendas marcadas :545, y de su sucursal :463.' },
            @{ n = 'Informar error'; col = 'vali'; fila = 3.5
               nota = 'Sumidero de los rechazos. _traducir(), reservas/router.py.' },
            @{ n = 'Transaccion completada'; col = 'fin'; fila = 1.5
               nota = 'db.commit(). La reserva queda ATENDIDA con el resultado de cada prenda.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Autenticar Encargado'; e = '' },
            @{ d = 'Autenticar Encargado'; h = 'Seleccionar operacion'
               e = '[rol ADMINISTRADOR o ENCARGADO]  {dependencies.py:110}' },
            @{ d = 'Autenticar Encargado'; h = '(final-rechazo)'
               e = '[rol distinto]  {403 dependencies.py:119}' },
            @{ d = 'Seleccionar operacion'; h = 'Desplegar reservas de la sucursal'
               e = '[listar]  {GET /sucursal/reservas}' },
            @{ d = 'Seleccionar operacion'; h = 'Preparar reserva'
               e = '[preparar]  {POST /sucursal/reservas/:id/preparacion}' },
            @{ d = 'Seleccionar operacion'; h = 'Registrar resultado por prenda'
               e = '[atender]  {POST /sucursal/reservas/:id/atencion}' },
            @{ d = 'Desplegar reservas de la sucursal'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Preparar reserva'; h = 'Transaccion completada'
               e = '[la reserva esta viva]  {service.py:482}' },
            @{ d = 'Registrar resultado por prenda'; h = 'Validar estado y resultados'
               e = '[marcar cada prenda]' },
            @{ d = 'Validar estado y resultados'; h = 'Transaccion completada'
               e = '[reserva viva y todas las prendas marcadas]  {service.py:533 y :545}' },
            @{ d = 'Validar estado y resultados'; h = 'Informar error'
               e = '[no atendible, resultados incompletos o de otra sucursal]  {409/403 service.py:533, :545 y :463}' },
            @{ d = 'Informar error'; h = 'Seleccionar operacion'; e = 'reintentar()' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-25'; ciclo = '#2'; titulo = 'Expirar reservas vencidas'
        nota = 'Flujo transaccional de CU-25. UNICO caso de uso sin actor humano: lo dispara el planificador de tareas. No tiene menu de operaciones, es un solo camino. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Disparar tarea programada'; col = 'auth'; fila = 1
               nota = 'PlanificadorTareas. Endpoint de mantenimiento, reservas/router.py.' },
            @{ n = 'Buscar reservas vencidas'; col = 'menu'; fila = 1
               nota = 'expirar_reservas_vencidas, reservas/service.py:643. El corte es franja_fin + RESERVA_VIGENCIA_HORAS.' },
            @{ n = 'Liberar unidades'; col = 'oper'; fila = 0.5
               nota = 'liberar_de_reserva por cada linea, inventario/service.py:746. Genera el movimiento LIBERACION.' },
            @{ n = 'Marcar EXPIRADA'; col = 'vali'; fila = 0.5
               nota = 'reserva.estado = EXPIRADA. La fila sigue viva y el cliente la sigue viendo.' },
            @{ n = 'Transaccion completada'; col = 'fin'; fila = 1
               nota = 'db.commit(). El stock volvio a estar disponible.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Disparar tarea programada'; e = '' },
            @{ d = 'Disparar tarea programada'; h = 'Buscar reservas vencidas'
               e = '[se cumple el intervalo]  {POST /mantenimiento/reservas/expiracion}' },
            @{ d = 'Buscar reservas vencidas'; h = 'Liberar unidades'
               e = '[franja_fin + RESERVA_VIGENCIA_HORAS < ahora]  {service.py:643}' },
            @{ d = 'Buscar reservas vencidas'; h = 'Transaccion completada'
               e = '[no hay vencidas]' },
            @{ d = 'Liberar unidades'; h = 'Marcar EXPIRADA'
               e = '{inventario/service.py:746}' },
            @{ d = 'Marcar EXPIRADA'; h = 'Transaccion completada'; e = '' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    # ================= CICLO 3 =================================
    #
    # PILOTO DEL 20/09. Un solo caso de uso, para revisar que el patron sirve
    # tal cual antes de escribir los demas del ciclo.
    #
    # Se eligio CU-27 porque tiene la maquina de estados mas rica del ciclo
    # ---y porque cubre de una vez tres de los seis procesos que el auxiliar
    # nombra: venta, compra y pagos---. A diferencia de los CU de gestion del
    # Ciclo 1, aca la transaccion NO termina en el commit: el pedido queda
    # PENDIENTE_PAGO y su estado final lo decide otro actor ---la pasarela,
    # en CU-28--- o el paso del tiempo.

    @{
        cu = 'CU-27'; ciclo = '#3'; titulo = 'Realizar pedido y pagar en linea'
        nota = 'Flujo transaccional de CU-27. OJO: el commit NO es el final. El pedido nace PENDIENTE_PAGO y se resuelve por CU-28 (pago confirmado), por cancelacion del cliente o por la barrida de vencidos. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Revisar el carrito'; col = 'auth'; fila = 1
               nota = 'features/tienda/checkout. Exige sesion de CLIENTE.' },
            @{ n = 'Elegir entrega y sucursal'; col = 'menu'; fila = 1
               nota = 'GET /tienda/pedidos/opciones dice que sucursal puede abastecerlo completo.' },
            @{ n = 'Validar total y pendiente'; col = 'vali'; fila = 0.5
               nota = 'Bloquea la fila del CLIENTE antes de mirar: una consulta sin filas no bloquea nada.' },
            @{ n = 'Apartar stock'; col = 'oper'; fila = 1.5
               nota = 'Reusa apartar_para_reserva de P4, con FOR UPDATE por variante.' },
            @{ n = 'Crear venta PENDIENTE_PAGO'; col = 'oper'; fila = 2.5
               nota = 'Congela los precios en detalle_venta y vacia el carrito.' },
            @{ n = 'Esperando el pago'; col = 'fin'; fila = 1.5
               nota = 'Aca termina CU-27. El estado siguiente no lo decide el cliente.' },
            @{ n = 'Informar error'; col = 'vali'; fila = 3.5
               nota = 'Sumidero de los rechazos: 409 total desactualizado, 409 ya hay pendiente, 409 ninguna sucursal completa.' },
            @{ n = 'Liberar stock apartado'; col = 'oper'; fila = 4
               nota = 'Cancelacion del cliente o barrida de vencidos. Sin esto, apartar seria un defecto.' },
            @{ n = 'Transaccion completada'; col = 'fin'; fila = 3.5
               nota = 'El pedido queda resuelto: pagado por CU-28, cancelado o expirado.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Revisar el carrito'; e = '' },
            @{ d = 'Revisar el carrito'; h = 'Elegir entrega y sucursal'
               e = '[el cliente decide comprar]  {GET /tienda/pedidos/opciones}' },
            @{ d = 'Elegir entrega y sucursal'; h = 'Validar total y pendiente'
               e = '[confirmar]  {POST /tienda/pedidos}' },
            @{ d = 'Validar total y pendiente'; h = 'Apartar stock'
               e = '[total coincide y no hay otro pendiente]' },
            @{ d = 'Validar total y pendiente'; h = 'Informar error'
               e = '[total desactualizado / ya hay pendiente / ninguna completa]  {409}' },
            @{ d = 'Apartar stock'; h = 'Crear venta PENDIENTE_PAGO'
               e = '[hay existencia en la sucursal elegida]  {FOR UPDATE por variante}' },
            @{ d = 'Apartar stock'; h = 'Informar error'
               e = '[existencia insuficiente]  {409}' },
            @{ d = 'Crear venta PENDIENTE_PAGO'; h = 'Esperando el pago'
               e = '{db.commit() -> 201 y URL de la pasarela}' },
            @{ d = 'Esperando el pago'; h = 'Transaccion completada'
               e = '[la pasarela confirma]  {CU-28: POST /pagos/webhook}' },
            @{ d = 'Esperando el pago'; h = 'Liberar stock apartado'
               e = '[el cliente cancela]  {POST /tienda/pedidos/:codigo/cancelar}' },
            @{ d = 'Esperando el pago'; h = 'Liberar stock apartado'
               e = '[vence el plazo sin pago]  {POST /pedidos/expirar-vencidos}' },
            @{ d = 'Liberar stock apartado'; h = 'Transaccion completada'
               e = '{el stock vuelve a disponible}' },
            @{ d = 'Informar error'; h = 'Revisar el carrito'; e = 'reintentar()' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-21'; ciclo = '#3'; titulo = 'Utilizar vestidor virtual (RA)'
        nota = 'Flujo de CU-21. El unico del ciclo que NO escribe en la base: todo ocurre en el telefono, y lo unico que persiste es lo que se derive al carrito o a la reserva. Por eso no hay estado de commit.'
        estados = @(
            @{ n = 'Abrir el vestidor'; col = 'auth'; fila = 1
               nota = 'mobile/lib/features/vestidor/pantalla_vestidor.dart. Desde la ficha o desde el menu.' },
            @{ n = 'Pedir permiso de camara'; col = 'menu'; fila = 0.5
               nota = 'permission_handler. La camara FRONTAL: es la que sirve para probarse solo.' },
            @{ n = 'Detectar la pose'; col = 'oper'; fila = 0
               nota = 'google_mlkit_pose_detection sobre los fotogramas. Corre EN EL TELEFONO.' },
            @{ n = 'Superponer la prenda'; col = 'oper'; fila = 1.5
               nota = 'pintor_prenda.dart: escala por hombros, ubica y rota siguiendo hombros y cadera.' },
            @{ n = 'Capturar la imagen'; col = 'oper'; fila = 3
               nota = 'Se guarda en el telefono. Nada viaja al servidor.' },
            @{ n = 'Derivar al carrito o la reserva'; col = 'fin'; fila = 2.5
               nota = 'Lo unico que persiste de todo el caso de uso.' },
            @{ n = 'Informar que no se puede probar'; col = 'vali'; fila = 3.5
               nota = 'Sin permiso, sin PNG transparente o sin cuerpo detectado.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Abrir el vestidor'; e = '' },
            @{ d = 'Abrir el vestidor'; h = 'Pedir permiso de camara'; e = '[el cliente elige probarse]' },
            @{ d = 'Pedir permiso de camara'; h = 'Detectar la pose'; e = '[permiso concedido]' },
            @{ d = 'Pedir permiso de camara'; h = 'Informar que no se puede probar'
               e = '[permiso denegado]  {no se insiste}' },
            @{ d = 'Detectar la pose'; h = 'Superponer la prenda'
               e = '[hay un cuerpo en el cuadro]  {hombros y cadera}' },
            @{ d = 'Detectar la pose'; h = 'Informar que no se puede probar'
               e = '[no se detecta un cuerpo]' },
            @{ d = 'Superponer la prenda'; h = 'Superponer la prenda'
               e = 'cambiarTallaOColor()  [en vivo, sin consultar al servidor]' },
            @{ d = 'Superponer la prenda'; h = 'Informar que no se puede probar'
               e = '[la variante no tiene PNG transparente]' },
            @{ d = 'Superponer la prenda'; h = 'Capturar la imagen'; e = 'capturar()' },
            @{ d = 'Capturar la imagen'; h = 'Derivar al carrito o la reserva'
               e = '[el cliente decide llevarla]  {CU-26 o CU-22}' },
            @{ d = 'Informar que no se puede probar'; h = 'Abrir el vestidor'; e = 'probar otra prenda()' },
            @{ d = 'Derivar al carrito o la reserva'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-28'; ciclo = '#3'; titulo = 'Confirmar pago del pedido'
        nota = 'Flujo transaccional de CU-28. Lo INICIA UNA MAQUINA, no una persona: la pasarela llama al webhook. Por eso la guarda de entrada no es un token sino la firma, y por eso este caso de uso no deja asiento en la bitacora. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Recibir la notificacion'; col = 'auth'; fila = 1
               nota = 'POST /pagos/webhook. Sin sesion: el que llama es el cobrador.' },
            @{ n = 'Validar la firma'; col = 'vali'; fila = 0
               nota = 'Antes de LEER el contenido. Un webhook sin verificar deja a cualquiera marcar pedidos como pagados.' },
            @{ n = 'Buscar la transaccion y la venta'; col = 'menu'; fila = 1.5
               nota = 'transaccion_pasarela -> venta.' },
            @{ n = 'Comprobar si ya se aplico'; col = 'vali'; fila = 1.5
               nota = 'Las pasarelas reintentan. Sin esto se descuenta el inventario dos veces.' },
            @{ n = 'Marcar la venta PAGADA'; col = 'oper'; fila = 1.5
               nota = 'Es el unico lugar del sistema que mueve una venta a PAGADA.' },
            @{ n = 'Descontar inventario y emitir comprobante'; col = 'oper'; fila = 2.5
               nota = 'El apartado se vuelve salida definitiva, con su movimiento inmutable.' },
            @{ n = 'Descartar la notificacion'; col = 'vali'; fila = 3.5
               nota = 'Firma invalida o venta inexistente. No se crea nada a partir de un aviso.' },
            @{ n = 'Transaccion completada'; col = 'fin'; fila = 2
               nota = 'Se responde para que la pasarela deje de reintentar.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Recibir la notificacion'; e = '' },
            @{ d = 'Recibir la notificacion'; h = 'Validar la firma'; e = '{POST /pagos/webhook}' },
            @{ d = 'Validar la firma'; h = 'Buscar la transaccion y la venta'; e = '[firma valida]' },
            @{ d = 'Validar la firma'; h = 'Descartar la notificacion'; e = '[firma invalida]  {400}' },
            @{ d = 'Buscar la transaccion y la venta'; h = 'Comprobar si ya se aplico'
               e = '[la venta existe]' },
            @{ d = 'Buscar la transaccion y la venta'; h = 'Descartar la notificacion'
               e = '[no hay venta para ese aviso]' },
            @{ d = 'Comprobar si ya se aplico'; h = 'Marcar la venta PAGADA'; e = '[es la primera vez]' },
            @{ d = 'Comprobar si ya se aplico'; h = 'Transaccion completada'
               e = '[reintento de la pasarela]  {idempotente}' },
            @{ d = 'Marcar la venta PAGADA'; h = 'Descontar inventario y emitir comprobante'
               e = '[pago aprobado]' },
            @{ d = 'Marcar la venta PAGADA'; h = 'Transaccion completada'
               e = '[pago rechazado]  {la venta sigue pendiente}' },
            @{ d = 'Descontar inventario y emitir comprobante'; h = 'Transaccion completada'
               e = '{db.commit()}' },
            @{ d = 'Descartar la notificacion'; h = '(final-rechazo)'; e = '' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-31'; ciclo = '#3'; titulo = 'Registrar venta presencial'
        nota = 'Flujo transaccional de CU-31. La guarda de entrada NO es el rol sino el TURNO DE CAJA ABIERTO: sin turno el dinero cobrado no es atribuible. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Abrir el mostrador'; col = 'auth'; fila = 1
               nota = 'Exige rol CAJERO y sucursal asignada.' },
            @{ n = 'Verificar turno abierto'; col = 'vali'; fila = 0
               nota = 'GET /caja/turnos/mio. Sin turno no se cobra.' },
            @{ n = 'Buscar prendas del mostrador'; col = 'menu'; fila = 1.5
               nota = 'GET /pos/prendas: solo las que tienen existencia en SU sucursal.' },
            @{ n = 'Armar el detalle y el total'; col = 'oper'; fila = 0.5
               nota = 'El total aplica las promociones vigentes de CU-12.' },
            @{ n = 'Descontar inventario y registrar la venta'; col = 'oper'; fila = 2
               nota = 'FOR UPDATE sobre la existencia: dos cajeros no venden la misma ultima unidad.' },
            @{ n = 'Emitir el comprobante'; col = 'oper'; fila = 3
               nota = 'GET /pos/ventas/:codigo/comprobante. Se puede volver a descargar.' },
            @{ n = 'Informar error'; col = 'vali'; fila = 3.5
               nota = 'Sin turno, existencia insuficiente o prenda de otra sucursal.' },
            @{ n = 'Transaccion completada'; col = 'fin'; fila = 2.5
               nota = 'La venta queda asociada al turno, que es lo que permite cuadrar la caja.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Abrir el mostrador'; e = '' },
            @{ d = 'Abrir el mostrador'; h = 'Verificar turno abierto'; e = '{GET /caja/turnos/mio}' },
            @{ d = 'Verificar turno abierto'; h = 'Buscar prendas del mostrador'; e = '[hay turno abierto]' },
            @{ d = 'Verificar turno abierto'; h = 'Informar error'
               e = '[sin turno]  {lleva a abrir caja, CU-30}' },
            @{ d = 'Buscar prendas del mostrador'; h = 'Armar el detalle y el total'
               e = '[elegir prendas y cantidades]' },
            @{ d = 'Buscar prendas del mostrador'; h = 'Armar el detalle y el total'
               e = 'cargarReservaAtendida()  {GET /pos/reservas}' },
            @{ d = 'Armar el detalle y el total'; h = 'Descontar inventario y registrar la venta'
               e = '[efectivo o tarjeta]  {POST /pos/ventas}' },
            @{ d = 'Descontar inventario y registrar la venta'; h = 'Informar error'
               e = '[existencia insuficiente]  {409, la venta no entra parcial}' },
            @{ d = 'Descontar inventario y registrar la venta'; h = 'Emitir el comprobante'
               e = '[descuento aplicado]  {movimiento de salida}' },
            @{ d = 'Emitir el comprobante'; h = 'Transaccion completada'; e = '{db.commit() -> 201}' },
            @{ d = 'Informar error'; h = 'Buscar prendas del mostrador'; e = 'reintentar()' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-33'; ciclo = '#3'; titulo = 'Recibir recomendaciones de prendas'
        nota = 'Flujo de CU-33. NO ESCRIBE EN LA BASE: es una consulta asistida. Lo que lo distingue es `Validar contra el catalogo`, que descarta lo que el modelo invente, y el reintento cuando sobreviven menos de tres. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Abrir Para vos'; col = 'auth'; fila = 1
               nota = 'Exige rol CLIENTE. Web y movil.' },
            @{ n = 'Reunir la senal del cliente'; col = 'menu'; fila = 1
               nota = 'Favoritos, compras, reservas, talla habitual y temporada vigente.' },
            @{ n = 'Armar el contexto'; col = 'oper'; fila = 0
               nota = 'Catalogo ya filtrado, con el par id -> nombre. Se arma en CADA pedido, sin cache.' },
            @{ n = 'Consultar al modelo'; col = 'oper'; fila = 1.5
               nota = 'El modelo elige y ordena; no consulta la base.' },
            @{ n = 'Validar contra el catalogo'; col = 'vali'; fila = 1.5
               nota = 'Descarta lo inventado, lo desactivado y lo agotado. La existencia entra por la costura C1.' },
            @{ n = 'Mostrar las prendas sugeridas'; col = 'fin'; fila = 1.5
               nota = 'Cada una con su motivo.' },
            @{ n = 'Informar que no esta disponible'; col = 'vali'; fila = 3.5
               nota = 'Sin proveedor de IA no se dibuja una version degradada.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Abrir Para vos'; e = '' },
            @{ d = 'Abrir Para vos'; h = 'Reunir la senal del cliente'
               e = '{GET /tienda/recomendaciones}' },
            @{ d = 'Reunir la senal del cliente'; h = 'Armar el contexto'; e = '' },
            @{ d = 'Armar el contexto'; h = 'Consultar al modelo'; e = '[hay proveedor de IA]' },
            @{ d = 'Armar el contexto'; h = 'Informar que no esta disponible'; e = '[sin proveedor de IA]' },
            @{ d = 'Consultar al modelo'; h = 'Validar contra el catalogo'; e = '[el modelo contesta]' },
            @{ d = 'Consultar al modelo'; h = 'Consultar al modelo'
               e = '[saturado o agotado el tiempo]  {modelo de respaldo}' },
            @{ d = 'Consultar al modelo'; h = 'Informar que no esta disponible'
               e = '[tampoco contesta el de respaldo]' },
            @{ d = 'Validar contra el catalogo'; h = 'Consultar al modelo'
               e = '[sobreviven menos de MINIMO_UTIL]  {se vuelve a pedir}' },
            @{ d = 'Validar contra el catalogo'; h = 'Mostrar las prendas sugeridas'
               e = '[quedan suficientes prendas reales]' },
            @{ d = 'Informar que no esta disponible'; h = '(final-rechazo)'; e = '' },
            @{ d = 'Mostrar las prendas sugeridas'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-34'; ciclo = '#3'; titulo = 'Conversar con el asistente virtual'
        nota = 'Flujo de CU-34. NO ESCRIBE EN LA BASE, ni siquiera la conversacion: los turnos viven en la pantalla y se pierden al recargar, a proposito. El bucle sobre `Esperando la pregunta` es lo que lo hace conversacional. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Abrir el asistente'; col = 'auth'; fila = 1
               nota = 'Exige rol CLIENTE. GET /asistente/disponible.' },
            @{ n = 'Esperando la pregunta'; col = 'menu'; fila = 1
               nota = 'Ofrece seis preguntas de ejemplo y el campo libre.' },
            @{ n = 'Armar el contexto'; col = 'oper'; fila = 0
               nota = 'Catalogo, promociones vigentes, tallas en cm, y SUS pedidos, reservas y medidas. Entero, en cada pregunta.' },
            @{ n = 'Consultar al modelo'; col = 'oper'; fila = 1.5
               nota = 'Una sola llamada, con los ultimos turnos. Tarda entre 3 y 25 segundos.' },
            @{ n = 'Validar los codigos citados'; col = 'vali'; fila = 1.5
               nota = 'Un codigo inventado no llega a la pantalla.' },
            @{ n = 'Mostrar la respuesta'; col = 'fin'; fila = 1.5
               nota = 'Con las prendas mencionadas como enlaces. El turno se guarda EN MEMORIA.' },
            @{ n = 'Informar que no esta disponible'; col = 'vali'; fila = 3.5
               nota = 'Sin proveedor de IA no se contesta una version degradada.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Abrir el asistente'; e = '' },
            @{ d = 'Abrir el asistente'; h = 'Esperando la pregunta'
               e = '[hay proveedor de IA]  {GET /asistente/disponible}' },
            @{ d = 'Abrir el asistente'; h = 'Informar que no esta disponible'
               e = '[sin proveedor de IA]' },
            @{ d = 'Esperando la pregunta'; h = 'Armar el contexto'
               e = '[pregunta de 1 a 500 caracteres]  {POST /asistente}' },
            @{ d = 'Esperando la pregunta'; h = 'Esperando la pregunta'
               e = '[vacia o muy larga]  {422, sin gastar una llamada al modelo}' },
            @{ d = 'Armar el contexto'; h = 'Consultar al modelo'; e = '{contexto y los ultimos turnos}' },
            @{ d = 'Consultar al modelo'; h = 'Validar los codigos citados'; e = '[el modelo contesta]' },
            @{ d = 'Consultar al modelo'; h = 'Consultar al modelo'
               e = '[saturado o agotado el tiempo]  {modelo de respaldo}' },
            @{ d = 'Consultar al modelo'; h = 'Informar que no esta disponible'
               e = '[tampoco contesta el de respaldo]' },
            @{ d = 'Validar los codigos citados'; h = 'Mostrar la respuesta'
               e = '[solo los codigos que existen]' },
            @{ d = 'Mostrar la respuesta'; h = 'Esperando la pregunta'
               e = 'repreguntar()  [el historial viaja con la siguiente]' },
            @{ d = 'Informar que no esta disponible'; h = '(final-rechazo)'; e = '' },
            @{ d = 'Mostrar la respuesta'; h = '(final)'; e = 'cerrar  [la conversacion se pierde]' }
        )
    }
)

# =========================================================================
# PARTE 1 - Enterprise Architect por COM
# =========================================================================

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($Modelo)) { throw "No se pudo abrir $Modelo" }

function Get-OCrearPaquete($padre, $nombre) {
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    $p = $padre.Packages.AddNew($nombre, 'Package'); [void]$p.Update()
    $padre.Packages.Refresh(); return $p
}
function BuscarDiagrama($p, $n) {
    foreach ($d in $p.Diagrams) { if ($d.Name -eq $n) { return $d } }
    foreach ($s in $p.Packages) { $r = BuscarDiagrama $s $n; if ($r) { return $r } }
    return $null
}
function Poner($dia, $elid, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l + $ancho);t=$t;b=$($t - $alto);", '')
    $do.ElementID = $elid
    [void]$do.Update()
    return $do
}
# La fila se admite con medios (1.5) para intercalar un estado entre otros dos.
function CoordY($fila) { return [int]($Y0 - ($fila * $PASO)) }

$root  = $ea.Models.GetAt(0)
$pRaiz = Get-OCrearPaquete $root 'Violet Boutique'
$pCap  = Get-OCrearPaquete $pRaiz 'CAP. 3 - Flujo de Trabajo: Diseno'

if ($Rehacer) {
    for ($i = $pCap.Packages.Count - 1; $i -ge 0; $i--) {
        if ($pCap.Packages.GetAt($i).Name -eq $NOMBRE_PKG) {
            $pCap.Packages.DeleteAt($i, $false)
            Write-Output '  paquete anterior eliminado (-Rehacer)'
        }
    }
    $pCap.Packages.Refresh()
}

$pkg = Get-OCrearPaquete $pCap $NOMBRE_PKG
$hechos = 0

foreach ($caso in $CASOS) {
    if ($CU -and $caso.cu -ne $CU) { continue }

    $NOMBRE_DIA = "3.2 Diagrama de Estado - $($caso.cu) $($caso.titulo) - CICLO $($caso.ciclo)"
    if (BuscarDiagrama $pkg $NOMBRE_DIA) {
        Write-Output "  $NOMBRE_DIA ya existe, no se toca"
        continue
    }

    $dia = $pkg.Diagrams.AddNew($NOMBRE_DIA, 'Statechart')
    $dia.Notes = $caso.nota
    [void]$dia.Update(); $pkg.Diagrams.Refresh()

    # ---- Los elementos. Se guarda el ID, NUNCA la referencia COM: la regla
    #      del catálogo de errores dice que Elements.Refresh() la invalida y
    #      los DiagramObject quedan con Object_ID = 0, sin dar ningún error.
    #
    #      El Alias lleva el CU porque `Validar datos` y `Seleccionar
    #      operacion` se repiten en casi todos los casos de uso: sin el alias
    #      no hay forma de saber, mirando el explorador, de qué CU es cada
    #      estado.
    $id = @{}
    foreach ($e in $caso.estados) {
        $el = $pkg.Elements.AddNew($e.n, 'State')
        $el.Alias = $caso.cu
        $el.Notes = $e.nota
        [void]$el.Update()
        $id[$e.n] = $el.ElementID
    }
    $el = $pkg.Elements.AddNew('', 'StateNode'); $el.Subtype = $SUB_INI; [void]$el.Update()
    $id['(inicial)'] = $el.ElementID
    $el = $pkg.Elements.AddNew('', 'StateNode'); $el.Subtype = $SUB_FIN; [void]$el.Update()
    $id['(final)'] = $el.ElementID

    # Segundo estado final, para el rechazo de autorizacion. UML 2.5 admite
    # varios: la peticion sin rol muere ahi mismo, no llega a haber
    # transaccion. Dibujarlo al lado de la autenticacion evita una flecha que
    # cruce el lienzo entero. Solo se crea si alguna transicion lo usa: CU-01
    # y CU-25 no tienen autorizacion que rechazar.
    $usaRechazo = @($caso.transiciones | Where-Object { $_.h -eq '(final-rechazo)' }).Count -gt 0
    if ($usaRechazo) {
        $el = $pkg.Elements.AddNew('', 'StateNode'); $el.Subtype = $SUB_FIN; [void]$el.Update()
        $id['(final-rechazo)'] = $el.ElementID
    }
    $pkg.Elements.Refresh()

    # ---- al lienzo. Las coordenadas salen de la columna y la fila.
    foreach ($e in $caso.estados) {
        [void](Poner $dia $id[$e.n] $COL[$e.col] (CoordY $e.fila) $W_EST $H_EST)
    }

    # Los pseudoestados se cuelgan del primer estado y del de cierre.
    $primero = $caso.estados | Where-Object { $_.col -eq 'auth' } | Select-Object -First 1
    if (-not $primero) { $primero = $caso.estados | Select-Object -First 1 }
    $ultimo  = $caso.estados | Where-Object { $_.col -eq 'fin' }  | Select-Object -First 1
    if (-not $ultimo)  { $ultimo  = $caso.estados | Select-Object -Last 1 }

    $yIni = (CoordY $primero.fila) - 15
    $yFin = (CoordY $ultimo.fila)  - 15
    [void](Poner $dia $id['(inicial)'] ($COL[$primero.col] - 80)  $yIni $W_NODO $H_NODO)
    [void](Poner $dia $id['(final)']   ($COL[$ultimo.col] + 290)  $yFin $W_NODO $H_NODO)
    if ($usaRechazo) {
        [void](Poner $dia $id['(final-rechazo)'] ($COL[$primero.col] + 100) ($yIni - 225) $W_NODO $H_NODO)
    }

    # ---- transiciones: conector StateFlow
    foreach ($t in $caso.transiciones) {
        if (-not $id.ContainsKey($t.d)) { throw "$($caso.cu): no existe el estado origen '$($t.d)'" }
        if (-not $id.ContainsKey($t.h)) { throw "$($caso.cu): no existe el estado destino '$($t.h)'" }
        $src = $ea.GetElementByID($id[$t.d])
        $c = $src.Connectors.AddNew($t.e, 'StateFlow')
        $c.SupplierID = $id[$t.h]
        $c.Direction  = 'Source -> Destination'
        [void]$c.Update()
        $src.Connectors.Refresh()
    }

    $pkg.Elements.Refresh()
    $dia.DiagramObjects.Refresh()
    $huerfanos = $ea.SQLQuery("SELECT COUNT(*) AS n FROM t_diagramobjects WHERE Diagram_ID=$($dia.DiagramID) AND Object_ID=0")
    Write-Output "  $($caso.cu) : $($dia.DiagramObjects.Count) estados, $($caso.transiciones.Count) transiciones"
    if ($huerfanos -match '<n>([1-9]\d*)</n>') { Write-Output "  AVISO: $($Matches[1]) objetos con Object_ID=0" }
    $hechos++
}

Write-Output "  $hechos diagrama(s) generado(s)"
$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers()
Write-Output 'OK'
