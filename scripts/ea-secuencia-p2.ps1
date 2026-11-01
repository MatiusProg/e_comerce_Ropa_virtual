# =========================================================================
# 2DO PARCIAL - 3.3 Diagramas de Secuencia: uno por caso de uso (CU-01 a CU-20).
#
# ---- DE DONDE SALE ESTE FORMATO ----
# ICONIX: la secuencia sale de la robustez. Por eso:
#   - las lineas de vida son los mismos participantes del 3.2 del mismo CU
#     (paquete 'PARCIAL 2 - ICONIX > 3.2 Diagramas de Robustez'), ni uno mas;
#   - los mensajes son los que Mateo cargo en la robustez, con SU numeracion
#     de EA (1, 1.1, 1.2... 2, 2.1...), para seguir el mismo mensaje en los
#     dos diagramas;
#   - los retornos, que la robustez no tiene, van como sub-nivel del mensaje
#     que los provoca (1.3 -> 1.3.1) y se dibujan punteados.
#
# ---- LOS FRAGMENTOS COMBINADOS ----
# Cada uno sale de una estructura de control del codigo (ver
# docs/diagramas/secuencia-y-codigo.md, seccion 3):
#   alt      if / elif / else; raise excluyentes          (NType 0)
#   opt      if sin else                                    (NType 1)
#   break    raise temprano que abandona el resto           (NType 2)
#   loop     for, o el UPDATE que recorre varias filas      (NType 4)
#   critical try: ... commit / except: rollback             (NType 5)
# El guion los abre con t='alt'|'opt'|'break'|'loop'|'critical', los alt
# separan operandos con t='op', y todos cierran con t='fin'. Se anidan.
#
# ---- COMO SE MAQUETA ----
# Con la regla medida el 29/09 (scripts/ea-fragmentos-3-2.ps1): EA apila los
# mensajes por SeqNo de 35 en 35 desde -135 e ignora su altura guardada; solo
# baja un mensaje si caeria sobre la cabecera de una caja o la guarda de un
# operando. Las cajas y las notas quedan donde se guardan. Este script simula
# esa regla y pone cada caja alrededor de lo que le toca. NO SE ARRASTRA NADA
# A MANO EN EA: mover una caja corre todos los mensajes de abajo.
#
# Las lineas de vida van enlazadas por ClassifierID a las clases del 3.2; los
# actores se crean en el paquete 3.3 (regla 2 de la guia).
#
# ADITIVO: solo crea los diagramas que faltan. -Rehacer borra el paquete 3.3
# entero; -Solo 'CU-01','CU-05' limita a esos casos de uso.
#
# Se corre con el PowerShell de 64 bits (el proveedor ACE 16.0 solo esta ahi),
# con EA abierto SIN este archivo y su cuadro de inicio aceptado: el script
# usa ese EA, y la segunda pasada escribe directo en el .eapx. Primero sobre una copia (-Modelo copia.eapx) y mirar las imagenes.
# =========================================================================

param(
    [string]$Modelo = (Join-Path $PSScriptRoot '..\docs\diagramas\VioletBoutique.eapx'),
    [switch]$Rehacer,
    [string[]]$Solo,
    # Exporta un PNG por diagrama creado a esta carpeta, para revisarlos.
    [string]$Imagenes
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path $Modelo)) { throw "No existe $Modelo" }
$Modelo = (Resolve-Path $Modelo).Path

# ---- Constantes de dibujo (medidas sobre lo que dibuja EA) ----
$X0        = 190    # borde izquierdo de la primera linea de vida
$GAP       = 45     # separacion horizontal entre lineas de vida
$TOP_LV    = -50    # borde superior de las lineas de vida
$Y_PRIMERO = -135   # primer mensaje
$PASO      = 35     # separacion entre mensajes
$AUTO      = 15     # lo que baja la flecha de vuelta de un auto-mensaje
$NOTA_L = 5; $NOTA_R = 120; $NOTA_ALTO = 50
$NTYPE = @{ alt = 0; opt = 1; break = 2; loop = 4; critical = 5 }

# =========================================================================
# GUION DE CADA CASO DE USO
#
# lineas : de izquierda a derecha. 'actor' crea (o reusa) el actor en el
#          paquete 3.3; 'clase' enlaza con la clase del 3.2.
# guion  : de arriba hacia abajo. t='nota' separa flujos; t='msg' con o/d
#          (claves de linea), n (texto) y ret=$true si es retorno.
# =========================================================================

$CASOS = @(

# ---------------------------------------------------------------- CU-01 --
@{
  cu = 'CU-01'; nombre = '3.3 CU-01 Gestionar empresas'
  lineas = @(
    @{ k = 'act'; actor = 'Administrador de la plataforma' },
    @{ k = 'pan'; clase = 'PantallaEmpresas' },
    @{ k = 'gst'; clase = 'GestorEmpresas' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'emp'; clase = 'Empresa' },
    @{ k = 'pla'; clase = 'Plan' },
    @{ k = 'sus'; clase = 'Suscripcion' },
    @{ k = 'suc'; clase = 'Sucursal' },
    @{ k = 'usu'; clase = 'Usuario' },
    @{ k = 'cor'; clase = 'CanalDeCorreo' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nAlta de la empresa" },
    @{ t='msg'; o='act'; d='pan'; n='1: abrirListaEmpresas()' },
    @{ t='msg'; o='pan'; d='gst'; n='1.1: listarEmpresas()' },
    @{ t='msg'; o='gst'; d='aut'; n='1.2: autorizar("ADMIN_PLATAFORMA")' },
    @{ t='msg'; o='gst'; d='emp'; n='1.3: listar()' },
    @{ t='msg'; o='emp'; d='gst'; n='1.3.1: List<Empresa>'; ret=$true },
    @{ t='msg'; o='act'; d='pan'; n='1.4: registrarEmpresa(datos)' },
    @{ t='msg'; o='pan'; d='gst'; n='1.5: crearEmpresa(datos)' },
    @{ t='msg'; o='gst'; d='gst'; n='1.6: validarDatos(datos)' },
    @{ t='msg'; o='gst'; d='emp'; n='1.7: existeSlug(slug)' },
    @{ t='msg'; o='emp'; d='gst'; n='1.7.1: boolean'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='datos válidos y slug libre' },
    @{ t='msg'; o='gst'; d='pla'; n='1.8: obtenerPlan(idPlan)' },
    @{ t='msg'; o='pla'; d='gst'; n='1.8.1: Plan'; ret=$true },
    @{ t='critical'; g='' },
    @{ t='msg'; o='gst'; d='emp'; n='1.9: crear(empresa)' },
    @{ t='msg'; o='gst'; d='sus'; n='1.10: crear(empresa, plan, inicio, vencimiento)' },
    @{ t='msg'; o='gst'; d='suc'; n='1.11: crearPrincipal(empresa)' },
    @{ t='msg'; o='gst'; d='gst'; n='1.12: generarContrasenaTemporal()' },
    @{ t='msg'; o='gst'; d='usu'; n='1.13: crearAdministrador(empresa, datos)' },
    @{ t='fin' },
    @{ t='msg'; o='gst'; d='cor'; n='1.14: enviarAcceso(correo, slug, contrasena)' },
    @{ t='msg'; o='gst'; d='pan'; n='1.15: confirmar(empresa)' },
    @{ t='op'; g='datos inválidos' },
    @{ t='msg'; o='gst'; d='pan'; n='4: datosInvalidos(campos)' },
    @{ t='op'; g='slug ya registrado' },
    @{ t='msg'; o='gst'; d='pan'; n='4.1: slugRepetido()' },
    @{ t='op'; g='otra alta tomó el slug o el correo al confirmar' },
    @{ t='msg'; o='gst'; d='gst'; n='4.2: revertirTransaccion()' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 2`nEditar" },
    @{ t='msg'; o='act'; d='pan'; n='2: editarEmpresa(id, datos)' },
    @{ t='msg'; o='pan'; d='gst'; n='2.1: actualizarEmpresa(id, datos)' },
    @{ t='msg'; o='gst'; d='emp'; n='2.2: guardar(empresa)' },
    @{ t='nota'; txt = "FLUJO 3`nDar de baja" },
    @{ t='msg'; o='act'; d='pan'; n='3: darDeBaja(id)' },
    @{ t='msg'; o='pan'; d='gst'; n='3.1: darDeBajaEmpresa(id)' },
    @{ t='msg'; o='gst'; d='emp'; n='3.2: desactivar()' }
  )
},

# ---------------------------------------------------------------- CU-02 --
@{
  cu = 'CU-02'; nombre = '3.3 CU-02 Gestionar planes'
  lineas = @(
    @{ k = 'act'; actor = 'Administrador de la plataforma' },
    @{ k = 'pan'; clase = 'PantallaPlanes' },
    @{ k = 'gst'; clase = 'GestorPlanes' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'pla'; clase = 'Plan' },
    @{ k = 'sus'; clase = 'Suscripcion' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nCrear o editar un plan" },
    @{ t='msg'; o='act'; d='pan'; n='1: abrirListaPlanes()' },
    @{ t='msg'; o='pan'; d='gst'; n='1.1: listarPlanes()' },
    @{ t='msg'; o='gst'; d='aut'; n='1.2: autorizar("ADMIN_PLATAFORMA")' },
    @{ t='msg'; o='gst'; d='pla'; n='1.3: listar()' },
    @{ t='msg'; o='pla'; d='gst'; n='1.3.1: List<Plan>'; ret=$true },
    @{ t='msg'; o='gst'; d='sus'; n='1.4: contarEmpresasPorPlan()' },
    @{ t='msg'; o='sus'; d='gst'; n='1.4.1: Map<idPlan, int>'; ret=$true },
    @{ t='msg'; o='act'; d='pan'; n='1.5: guardarPlan(datos)' },
    @{ t='msg'; o='pan'; d='gst'; n='1.6: guardarPlan(datos)' },
    @{ t='msg'; o='gst'; d='gst'; n='1.7: validarDatos(datos)' },
    @{ t='msg'; o='gst'; d='pla'; n='1.8: existeNombre(nombre)' },
    @{ t='msg'; o='pla'; d='gst'; n='1.8.1: boolean'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='datos válidos y nombre libre' },
    @{ t='msg'; o='gst'; d='pla'; n='1.9: guardar(plan)' },
    @{ t='msg'; o='gst'; d='sus'; n='3: empresasPorEncimaDelLimite(plan)' },
    @{ t='opt'; g='hay empresas por encima del límite nuevo' },
    @{ t='msg'; o='gst'; d='pan'; n='3.1: avisarEmpresasPorEncima(lista)' },
    @{ t='fin' },
    @{ t='msg'; o='gst'; d='pan'; n='1.10: confirmar(plan)' },
    @{ t='op'; g='datos inválidos o nombre repetido' },
    @{ t='msg'; o='gst'; d='pan'; n='4: datosInvalidos(campos)' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 2`nDesactivar un plan" },
    @{ t='msg'; o='act'; d='pan'; n='2: desactivarPlan(id)' },
    @{ t='msg'; o='pan'; d='gst'; n='2.1: desactivarPlan(id)' },
    @{ t='msg'; o='gst'; d='pla'; n='2.2: desactivar()' }
  )
},

# ---------------------------------------------------------------- CU-03 --
@{
  cu = 'CU-03'; nombre = '3.3 CU-03 Gestionar suscripciones'
  lineas = @(
    @{ k = 'act'; actor = 'Administrador de la plataforma' },
    @{ k = 'sis'; actor = 'Sistema' },
    @{ k = 'pan'; clase = 'PantallaSuscripcion' },
    @{ k = 'tar'; clase = 'TareaProgramada' },
    @{ k = 'gst'; clase = 'GestorSuscripciones' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'emp'; clase = 'Empresa' },
    @{ k = 'pla'; clase = 'Plan' },
    @{ k = 'pag'; clase = 'PagoSimulado' },
    @{ k = 'sus'; clase = 'Suscripcion' },
    @{ k = 'suc'; clase = 'Sucursal' },
    @{ k = 'emd'; clase = 'Empleado' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nAsignar o cambiar el plan" },
    @{ t='msg'; o='act'; d='pan'; n='1: abrirFichaEmpresa(idEmpresa)' },
    @{ t='msg'; o='pan'; d='gst'; n='1.1: obtenerSuscripciones(idEmpresa)' },
    @{ t='msg'; o='gst'; d='aut'; n='1.2: autorizar("ADMIN_PLATAFORMA")' },
    @{ t='msg'; o='gst'; d='emp'; n='1.3: obtener(idEmpresa)' },
    @{ t='msg'; o='emp'; d='gst'; n='1.3.1: Empresa'; ret=$true },
    @{ t='msg'; o='gst'; d='sus'; n='1.4: historialDe(empresa)' },
    @{ t='msg'; o='sus'; d='gst'; n='1.4.1: List<Suscripcion>'; ret=$true },
    @{ t='msg'; o='act'; d='pan'; n='1.5: asignarPlan(idPlan, inicio)' },
    @{ t='msg'; o='pan'; d='gst'; n='1.6: asignarPlan(idEmpresa, idPlan, inicio)' },
    @{ t='msg'; o='gst'; d='pla'; n='1.7: obtenerPlan(idPlan)' },
    @{ t='msg'; o='pla'; d='gst'; n='1.7.1: Plan'; ret=$true },
    @{ t='critical'; g='' },
    @{ t='msg'; o='gst'; d='pag'; n='1.8: registrar(empresa, plan, monto)' },
    @{ t='msg'; o='gst'; d='sus'; n='1.9: cerrarVigente(empresa)' },
    @{ t='msg'; o='gst'; d='sus'; n='1.10: crear(empresa, plan, inicio, vencimiento)' },
    @{ t='fin' },
    @{ t='msg'; o='gst'; d='suc'; n='4: contarActivas(empresa)' },
    @{ t='msg'; o='gst'; d='emd'; n='4.1: contarActivos(empresa)' },
    @{ t='opt'; g='el plan nuevo queda por debajo de lo usado' },
    @{ t='msg'; o='gst'; d='pan'; n='4.2: avisarRecursosPorEncima(lista)' },
    @{ t='fin' },
    @{ t='msg'; o='gst'; d='pan'; n='1.11: mostrarEstado(suscripcion)' },
    @{ t='nota'; txt = "FLUJO 2`nRenovar" },
    @{ t='msg'; o='act'; d='pan'; n='2: renovar()' },
    @{ t='msg'; o='pan'; d='gst'; n='2.1: renovar(idEmpresa)' },
    @{ t='msg'; o='gst'; d='sus'; n='2.2: extenderVencimiento()' },
    @{ t='nota'; txt = "FLUJO 3`nSuspender o reactivar" },
    @{ t='msg'; o='act'; d='pan'; n='3: suspenderOReactivar()' },
    @{ t='msg'; o='pan'; d='gst'; n='3.1: cambiarEstado(idEmpresa, estado)' },
    @{ t='msg'; o='gst'; d='sus'; n='3.2: cambiarEstado(estado)' },
    @{ t='nota'; txt = "FLUJO 5`nVencimiento diario" },
    @{ t='msg'; o='sis'; d='tar'; n='5: ejecutarDiaria()' },
    @{ t='msg'; o='tar'; d='gst'; n='5.1: marcarVencidas(hoy)' },
    @{ t='msg'; o='gst'; d='sus'; n='5.2: vencidasAl(hoy)' },
    @{ t='msg'; o='sus'; d='gst'; n='5.2.1: List<Suscripcion>'; ret=$true },
    @{ t='loop'; g='por cada suscripción con la fecha pasada' },
    @{ t='msg'; o='gst'; d='sus'; n='5.3: marcarVencida()' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-04 --
@{
  cu = 'CU-04'; nombre = '3.3 CU-04 Consultar plan y consumo'
  lineas = @(
    @{ k = 'act'; actor = 'Administrador de la empresa' },
    @{ k = 'pan'; clase = 'PantallaMiPlan' },
    @{ k = 'gst'; clase = 'GestorConsumoPlan' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'sus'; clase = 'Suscripcion' },
    @{ k = 'pla'; clase = 'Plan' },
    @{ k = 'suc'; clase = 'Sucursal' },
    @{ k = 'emd'; clase = 'Empleado' },
    @{ k = 'cup'; clase = 'ConsumoCupo' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nVer el plan y el consumo" },
    @{ t='msg'; o='act'; d='pan'; n='1: abrirMiPlan()' },
    @{ t='msg'; o='pan'; d='gst'; n='1.1: consultarPlan()' },
    @{ t='msg'; o='gst'; d='aut'; n='1.2: autorizar("ADMINISTRADOR")' },
    @{ t='msg'; o='gst'; d='sus'; n='1.3: vigenteDe(empresa)' },
    @{ t='msg'; o='sus'; d='gst'; n='1.3.1: Suscripcion'; ret=$true },
    @{ t='msg'; o='gst'; d='pla'; n='1.4: obtenerLimitesYFunciones()' },
    @{ t='msg'; o='pla'; d='gst'; n='1.4.1: Plan'; ret=$true },
    @{ t='msg'; o='gst'; d='suc'; n='1.5: contarActivas(empresa)' },
    @{ t='msg'; o='suc'; d='gst'; n='1.5.1: int'; ret=$true },
    @{ t='msg'; o='gst'; d='emd'; n='1.6: contarActivos(empresa)' },
    @{ t='msg'; o='emd'; d='gst'; n='1.6.1: int'; ret=$true },
    @{ t='msg'; o='gst'; d='cup'; n='1.7: consumoDelMes(empresa)' },
    @{ t='msg'; o='cup'; d='gst'; n='1.7.1: List<ConsumoCupo>'; ret=$true },
    @{ t='msg'; o='gst'; d='pan'; n='1.8: mostrarPlanYConsumo(resumen)' },
    @{ t='opt'; g='suscripción vencida o suspendida' },
    @{ t='msg'; o='gst'; d='pan'; n='2: avisarModoSoloConsulta(estado)' },
    @{ t='fin' },
    @{ t='opt'; g='quiere comparar planes' },
    @{ t='msg'; o='act'; d='pan'; n='1.9: compararPlanes()' },
    @{ t='msg'; o='pan'; d='gst'; n='1.10: listarPlanes()' },
    @{ t='msg'; o='gst'; d='pla'; n='1.11: listarActivos()' },
    @{ t='msg'; o='pla'; d='gst'; n='1.11.1: List<Plan>'; ret=$true },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-05 --
@{
  cu = 'CU-05'; nombre = '3.3 CU-05 Verificar límites y funciones del plan'
  lineas = @(
    @{ k = 'act'; actor = 'Usuario' },
    @{ k = 'ope'; clase = 'OperacionControlada' },
    @{ k = 'ver'; clase = 'VerificadorPlan' },
    @{ k = 'sus'; clase = 'Suscripcion' },
    @{ k = 'pla'; clase = 'Plan' },
    @{ k = 'cup'; clase = 'ConsumoCupo' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nLa operación cumple el plan" },
    @{ t='msg'; o='act'; d='ope'; n='1: solicitarOperacion(datos)' },
    @{ t='msg'; o='ope'; d='ver'; n='1.1: verificar(empresa, funcion, recurso)' },
    @{ t='msg'; o='ver'; d='sus'; n='1.2: vigenteDe(empresa)' },
    @{ t='msg'; o='sus'; d='ver'; n='1.2.1: Suscripcion | None'; ret=$true },
    @{ t='break'; g='sin suscripción vigente' },
    @{ t='msg'; o='ver'; d='ope'; n='2: rechazarSinSuscripcion()' },
    @{ t='fin' },
    @{ t='msg'; o='ver'; d='pla'; n='1.3: incluyeFuncion(funcion)' },
    @{ t='msg'; o='pla'; d='ver'; n='1.3.1: boolean'; ret=$true },
    @{ t='msg'; o='ver'; d='cup'; n='1.4: usoActual(empresa, recurso)' },
    @{ t='msg'; o='cup'; d='ver'; n='1.4.1: int'; ret=$true },
    @{ t='msg'; o='ver'; d='pla'; n='1.5: limiteDe(recurso)' },
    @{ t='msg'; o='pla'; d='ver'; n='1.5.1: int | None'; ret=$true },
    @{ t='msg'; o='ver'; d='ver'; n='1.6: compararConLimite(uso, limite)' },
    @{ t='break'; g='función no incluida o límite alcanzado' },
    @{ t='msg'; o='ver'; d='ope'; n='3: rechazarPorPlan("plan_limit", limite, uso)' },
    @{ t='fin' },
    @{ t='msg'; o='ver'; d='ope'; n='1.7: permitir()' }
  )
},

# ---------------------------------------------------------------- CU-06 --
@{
  cu = 'CU-06'; nombre = '3.3 CU-06 Iniciar sesión en una empresa'
  lineas = @(
    @{ k = 'act'; actor = 'Usuario' },
    @{ k = 'pan'; clase = 'PantallaInicioSesion' },
    @{ k = 'men'; clase = 'MenuPrincipal' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'emp'; clase = 'Empresa' },
    @{ k = 'sus'; clase = 'Suscripcion' },
    @{ k = 'usu'; clase = 'Usuario' },
    @{ k = 'tok'; clase = 'SesionToken' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nInicio con el slug" },
    @{ t='msg'; o='act'; d='pan'; n='1: ingresarCredenciales(slug, correo, contrasena)' },
    @{ t='alt' },
    @{ t='op'; g='trae el slug de una empresa' },
    @{ t='msg'; o='pan'; d='aut'; n='1.1: iniciarSesion(slug, credenciales)' },
    @{ t='msg'; o='aut'; d='emp'; n='1.2: buscarPorSlug(slug)' },
    @{ t='msg'; o='emp'; d='aut'; n='1.2.1: Empresa | None'; ret=$true },
    @{ t='break'; g='empresa no encontrada o dada de baja' },
    @{ t='msg'; o='aut'; d='pan'; n='3: empresaNoEncontrada()' },
    @{ t='fin' },
    @{ t='msg'; o='aut'; d='sus'; n='1.3: vigenteDe(empresa)' },
    @{ t='msg'; o='sus'; d='aut'; n='1.3.1: Suscripcion | None'; ret=$true },
    @{ t='msg'; o='aut'; d='usu'; n='1.4: buscarPorCorreo(empresa, correo)' },
    @{ t='msg'; o='usu'; d='aut'; n='1.4.1: Usuario | None'; ret=$true },
    @{ t='op'; g='sin slug: administrador de la plataforma' },
    @{ t='msg'; o='pan'; d='aut'; n='2: iniciarSesionPlataforma(credenciales)' },
    @{ t='msg'; o='aut'; d='usu'; n='2.1: buscarAdministradorPlataforma(correo)' },
    @{ t='msg'; o='usu'; d='aut'; n='2.1.1: Usuario | None'; ret=$true },
    @{ t='fin' },
    @{ t='msg'; o='aut'; d='aut'; n='1.5: verificarContrasena(hash)' },
    @{ t='alt' },
    @{ t='op'; g='usuario activo y contraseña correcta' },
    @{ t='msg'; o='aut'; d='aut'; n='1.6: emitirToken(usuario, empresa, rol)' },
    @{ t='opt'; g='suscripción vencida' },
    @{ t='msg'; o='aut'; d='aut'; n='4: marcarSoloConsulta(token)' },
    @{ t='fin' },
    @{ t='msg'; o='aut'; d='tok'; n='1.7: registrarSesion(jti, expiraEn)' },
    @{ t='msg'; o='aut'; d='men'; n='1.8: mostrarMenuDelRol(rol, marca)' },
    @{ t='op'; g='usuario inexistente o contraseña incorrecta' },
    @{ t='msg'; o='aut'; d='pan'; n='3.1: credencialesInvalidas()' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 5`nCerrar sesión" },
    @{ t='msg'; o='act'; d='men'; n='5: cerrarSesion()' },
    @{ t='msg'; o='men'; d='aut'; n='5.1: cerrarSesion(jti)' },
    @{ t='msg'; o='aut'; d='tok'; n='5.2: revocar(jti)' }
  )
},

# ---------------------------------------------------------------- CU-07 --
@{
  cu = 'CU-07'; nombre = '3.3 CU-07 Registrar cliente con cuenta única'
  lineas = @(
    @{ k = 'act'; actor = 'Cliente' },
    @{ k = 'frm'; clase = 'FormularioRegistro' },
    @{ k = 'gst'; clase = 'GestorRegistro' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'usu'; clase = 'Usuario' },
    @{ k = 'cli'; clase = 'Cliente' },
    @{ k = 'emp'; clase = 'Empresa' },
    @{ k = 'cem'; clase = 'ClienteEmpresa' },
    @{ k = 'tok'; clase = 'SesionToken' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nCuenta nueva" },
    @{ t='msg'; o='act'; d='frm'; n='1: enviarDatos(nombres, apellidos, correo, contrasena)' },
    @{ t='msg'; o='frm'; d='gst'; n='1.1: registrarCliente(slug, datos)' },
    @{ t='msg'; o='gst'; d='gst'; n='1.2: validarDatos(datos)' },
    @{ t='msg'; o='gst'; d='usu'; n='1.3: existeCorreo(correo)' },
    @{ t='msg'; o='usu'; d='gst'; n='1.3.1: Usuario | None'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='datos válidos y correo libre' },
    @{ t='msg'; o='gst'; d='gst'; n='1.4: hashearContrasena(contrasena)' },
    @{ t='critical'; g='' },
    @{ t='msg'; o='gst'; d='usu'; n='1.5: crear(usuario)' },
    @{ t='msg'; o='gst'; d='cli'; n='1.6: crear(cliente)' },
    @{ t='msg'; o='gst'; d='emp'; n='1.7: buscarPorSlug(slug)' },
    @{ t='msg'; o='emp'; d='gst'; n='1.7.1: Empresa'; ret=$true },
    @{ t='msg'; o='gst'; d='cem'; n='1.8: asociar(cliente, empresa)' },
    @{ t='fin' },
    @{ t='msg'; o='gst'; d='aut'; n='1.9: iniciarSesion(usuario, empresa)' },
    @{ t='msg'; o='aut'; d='tok'; n='1.10: registrarSesion(jti, expiraEn)' },
    @{ t='msg'; o='aut'; d='gst'; n='1.10.1: TokenOut'; ret=$true },
    @{ t='msg'; o='gst'; d='frm'; n='1.11: confirmarRegistro(token)' },
    @{ t='op'; g='datos inválidos' },
    @{ t='msg'; o='gst'; d='frm'; n='2: datosInvalidos(campos)' },
    @{ t='op'; g='el correo ya tiene cuenta de cliente' },
    @{ t='msg'; o='gst'; d='frm'; n='3: ofrecerIniciarSesion(correo)' },
    @{ t='msg'; o='act'; d='frm'; n='3.1: iniciarSesionConSuCuenta(contrasena)' },
    @{ t='msg'; o='frm'; d='gst'; n='3.2: asociarCuentaExistente(slug, credenciales)' },
    @{ t='msg'; o='gst'; d='aut'; n='3.3: validarCredenciales(credenciales)' },
    @{ t='msg'; o='aut'; d='gst'; n='3.3.1: TokenOut'; ret=$true },
    @{ t='msg'; o='gst'; d='cem'; n='3.4: asociar(cliente, empresa)' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-08 --
@{
  cu = 'CU-08'; nombre = '3.3 CU-08 Gestionar usuarios de la empresa'
  lineas = @(
    @{ k = 'act'; actor = 'Administrador de la empresa' },
    @{ k = 'pan'; clase = 'PantallaUsuarios' },
    @{ k = 'gst'; clase = 'GestorUsuarios' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'ver'; clase = 'VerificadorPlan' },
    @{ k = 'usu'; clase = 'Usuario' },
    @{ k = 'rol'; clase = 'Rol' },
    @{ k = 'suc'; clase = 'Sucursal' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nAlta de usuario" },
    @{ t='msg'; o='act'; d='pan'; n='1: abrirListaUsuarios()' },
    @{ t='msg'; o='pan'; d='gst'; n='1.1: listarUsuarios()' },
    @{ t='msg'; o='gst'; d='aut'; n='1.2: autorizar("ADMINISTRADOR")' },
    @{ t='msg'; o='gst'; d='usu'; n='1.3: listarDeEmpresa(empresa)' },
    @{ t='msg'; o='usu'; d='gst'; n='1.3.1: List<Usuario>'; ret=$true },
    @{ t='msg'; o='act'; d='pan'; n='1.4: crearUsuario(datos)' },
    @{ t='msg'; o='pan'; d='gst'; n='1.5: registrar(datos)' },
    @{ t='msg'; o='gst'; d='ver'; n='1.6: verificar(empresa, "usuarios")' },
    @{ t='break'; g='límite alcanzado' },
    @{ t='msg'; o='gst'; d='pan'; n='3: limiteAlcanzado(limite, uso)' },
    @{ t='fin' },
    @{ t='msg'; o='gst'; d='gst'; n='1.7: validarDatos(datos)' },
    @{ t='msg'; o='gst'; d='rol'; n='1.8: obtenerRol(rol)' },
    @{ t='msg'; o='rol'; d='gst'; n='1.8.1: Rol'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='rol permitido para el personal' },
    @{ t='opt'; g='el rol trabaja en una sucursal' },
    @{ t='msg'; o='gst'; d='suc'; n='1.9: perteneceAEmpresa(idSucursal, empresa)' },
    @{ t='msg'; o='suc'; d='gst'; n='1.9.1: boolean'; ret=$true },
    @{ t='fin' },
    @{ t='msg'; o='gst'; d='usu'; n='1.10: crear(usuario, empresa)' },
    @{ t='msg'; o='gst'; d='pan'; n='1.11: confirmar()' },
    @{ t='op'; g='rol no permitido' },
    @{ t='msg'; o='gst'; d='pan'; n='4: rolNoPermitido()' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 2`nEditar o desactivar" },
    @{ t='msg'; o='act'; d='pan'; n='2: editarODesactivar(id, datos)' },
    @{ t='msg'; o='pan'; d='gst'; n='2.1: actualizar(id, datos)' },
    @{ t='msg'; o='gst'; d='usu'; n='2.2: guardar(usuario)' }
  )
},

# ---------------------------------------------------------------- CU-09 --
@{
  cu = 'CU-09'; nombre = '3.3 CU-09 Gestionar sucursales de la empresa'
  lineas = @(
    @{ k = 'act'; actor = 'Administrador de la empresa' },
    @{ k = 'pan'; clase = 'PantallaSucursales' },
    @{ k = 'gst'; clase = 'GestorOrganizacion' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'ver'; clase = 'VerificadorPlan' },
    @{ k = 'suc'; clase = 'Sucursal' },
    @{ k = 'ciu'; clase = 'Ciudad' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nAlta de sucursal" },
    @{ t='msg'; o='act'; d='pan'; n='1: abrirListaSucursales()' },
    @{ t='msg'; o='pan'; d='gst'; n='1.1: listarSucursales()' },
    @{ t='msg'; o='gst'; d='aut'; n='1.2: autorizar("ADMINISTRADOR")' },
    @{ t='msg'; o='gst'; d='suc'; n='1.3: listarDeEmpresa(empresa)' },
    @{ t='msg'; o='suc'; d='gst'; n='1.3.1: List<Sucursal>'; ret=$true },
    @{ t='msg'; o='act'; d='pan'; n='1.4: registrarSucursal(datos)' },
    @{ t='msg'; o='pan'; d='gst'; n='1.5: crearSucursal(datos)' },
    @{ t='msg'; o='gst'; d='ver'; n='1.6: verificar(empresa, "sucursales")' },
    @{ t='break'; g='límite de sucursales alcanzado' },
    @{ t='msg'; o='gst'; d='pan'; n='4: limiteAlcanzado(limite, uso)' },
    @{ t='fin' },
    @{ t='msg'; o='gst'; d='gst'; n='1.7: validarDatos(datos)' },
    @{ t='msg'; o='gst'; d='ciu'; n='1.8: obtenerCiudad(id)' },
    @{ t='msg'; o='ciu'; d='gst'; n='1.8.1: Ciudad'; ret=$true },
    @{ t='msg'; o='gst'; d='suc'; n='1.9: crear(sucursal, empresa)' },
    @{ t='msg'; o='gst'; d='pan'; n='1.10: confirmar()' },
    @{ t='nota'; txt = "FLUJO 2`nEditar" },
    @{ t='msg'; o='act'; d='pan'; n='2: editarSucursal(id, datos)' },
    @{ t='msg'; o='pan'; d='gst'; n='2.1: actualizarSucursal(id, datos)' },
    @{ t='msg'; o='gst'; d='suc'; n='2.2: guardar(sucursal)' },
    @{ t='nota'; txt = "FLUJO 3`nDesactivar" },
    @{ t='msg'; o='act'; d='pan'; n='3: desactivarSucursal(id)' },
    @{ t='msg'; o='pan'; d='gst'; n='3.1: desactivarSucursal(id)' },
    @{ t='msg'; o='gst'; d='suc'; n='3.2: desactivar()' }
  )
},

# ---------------------------------------------------------------- CU-10 --
@{
  cu = 'CU-10'; nombre = '3.3 CU-10 Gestionar empleados de la empresa'
  lineas = @(
    @{ k = 'act'; actor = 'Administrador de la empresa' },
    @{ k = 'pan'; clase = 'PantallaEmpleados' },
    @{ k = 'gst'; clase = 'GestorEmpleados' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'ver'; clase = 'VerificadorPlan' },
    @{ k = 'emd'; clase = 'Empleado' },
    @{ k = 'suc'; clase = 'Sucursal' },
    @{ k = 'rol'; clase = 'Rol' },
    @{ k = 'usu'; clase = 'Usuario' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nAlta de empleado" },
    @{ t='msg'; o='act'; d='pan'; n='1: abrirListaEmpleados()' },
    @{ t='msg'; o='pan'; d='gst'; n='1.1: listarEmpleados()' },
    @{ t='msg'; o='gst'; d='aut'; n='1.2: autorizar("ADMINISTRADOR")' },
    @{ t='msg'; o='gst'; d='emd'; n='1.3: listarDeEmpresa(empresa)' },
    @{ t='msg'; o='emd'; d='gst'; n='1.3.1: List<Empleado>'; ret=$true },
    @{ t='msg'; o='gst'; d='pan'; n='1.4: listarDeEmpresa(empresa)'; ret=$true },
    @{ t='msg'; o='pan'; d='gst'; n='1.5: crearEmpleado(datos)' },
    @{ t='msg'; o='gst'; d='ver'; n='1.6: verificar(empresa, "empleados")' },
    @{ t='break'; g='límite de empleados alcanzado' },
    @{ t='msg'; o='gst'; d='pan'; n='3: limiteAlcanzado(limite, uso)' },
    @{ t='fin' },
    @{ t='msg'; o='gst'; d='suc'; n='1.7: perteneceAEmpresa(idSucursal, empresa)' },
    @{ t='msg'; o='suc'; d='gst'; n='1.7.1: boolean'; ret=$true },
    @{ t='msg'; o='gst'; d='rol'; n='1.8: obtenerRol(cargo)' },
    @{ t='msg'; o='rol'; d='gst'; n='1.8.1: Rol'; ret=$true },
    @{ t='critical'; g='' },
    @{ t='msg'; o='gst'; d='usu'; n='1.9: crear(usuario, empresa)' },
    @{ t='msg'; o='usu'; d='gst'; n='1.9.1: Usuario'; ret=$true },
    @{ t='msg'; o='gst'; d='emd'; n='1.10: crear(empleado)' },
    @{ t='fin' },
    @{ t='msg'; o='gst'; d='pan'; n='1.11: confirmar()' },
    @{ t='nota'; txt = "FLUJO 2`nEditar o desactivar" },
    @{ t='msg'; o='act'; d='pan'; n='2: editarODesactivar(id, datos)' },
    @{ t='msg'; o='pan'; d='gst'; n='2.1: actualizar(id, datos)' },
    @{ t='msg'; o='gst'; d='emd'; n='2.2: guardar(empleado)' },
    @{ t='opt'; g='se da de baja al empleado' },
    @{ t='msg'; o='gst'; d='usu'; n='2.3: desactivarSiCorresponde()' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-11 --
@{
  cu = 'CU-11'; nombre = '3.3 CU-11 Contratar un plan desde la web'
  lineas = @(
    @{ k = 'act'; actor = 'Empresa interesada' },
    @{ k = 'pag'; clase = 'PaginaPlanes' },
    @{ k = 'frm'; clase = 'FormularioContratacion' },
    @{ k = 'gst'; clase = 'GestorContratacion' },
    @{ k = 'gem'; clase = 'GestorEmpresas' },
    @{ k = 'pla'; clase = 'Plan' },
    @{ k = 'emp'; clase = 'Empresa' },
    @{ k = 'pgs'; clase = 'PagoSimulado' },
    @{ k = 'sus'; clase = 'Suscripcion' },
    @{ k = 'suc'; clase = 'Sucursal' },
    @{ k = 'usu'; clase = 'Usuario' },
    @{ k = 'cor'; clase = 'CanalDeCorreo' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nElegir, pagar y dar de alta" },
    @{ t='msg'; o='act'; d='pag'; n='1: abrirPlanes()' },
    @{ t='msg'; o='pag'; d='gst'; n='1.1: listarPlanesOfrecidos()' },
    @{ t='msg'; o='gst'; d='pla'; n='1.2: listarActivos()' },
    @{ t='msg'; o='pla'; d='gst'; n='1.2.1: List<Plan>'; ret=$true },
    @{ t='msg'; o='act'; d='pag'; n='1.3: elegirPlan(idPlan)' },
    @{ t='msg'; o='pag'; d='gst'; n='1.4: iniciarContratacion(idPlan)' },
    @{ t='msg'; o='gst'; d='frm'; n='1.5: mostrarFormulario(plan)' },
    @{ t='msg'; o='act'; d='frm'; n='1.6: enviarDatos(empresa, slug, administrador)' },
    @{ t='msg'; o='frm'; d='gst'; n='1.7: contratar(datos, idPlan)' },
    @{ t='msg'; o='gst'; d='gst'; n='1.8: validarDatos(datos)' },
    @{ t='msg'; o='gst'; d='emp'; n='1.9: existeSlug(slug)' },
    @{ t='msg'; o='emp'; d='gst'; n='1.9.1: boolean'; ret=$true },
    @{ t='break'; g='slug ocupado' },
    @{ t='msg'; o='gst'; d='emp'; n='2: sugerirSlugsLibres(slug)' },
    @{ t='msg'; o='gst'; d='frm'; n='2.1: slugOcupado(sugerencias)' },
    @{ t='fin' },
    @{ t='msg'; o='gst'; d='pgs'; n='1.10: registrar(plan, monto)' },
    @{ t='break'; g='pago rechazado' },
    @{ t='msg'; o='gst'; d='frm'; n='3: pagoRechazado()' },
    @{ t='fin' },
    @{ t='msg'; o='gst'; d='gem'; n='1.11: crearEmpresaConSuscripcion(datos, plan)' },
    @{ t='critical'; g='' },
    @{ t='msg'; o='gem'; d='emp'; n='1.12: crear(empresa)' },
    @{ t='msg'; o='gem'; d='sus'; n='1.13: crear(empresa, plan, inicio, vencimiento)' },
    @{ t='msg'; o='gem'; d='suc'; n='1.14: crearPrincipal(empresa)' },
    @{ t='msg'; o='gem'; d='usu'; n='1.15: crearAdministrador(empresa, datos)' },
    @{ t='fin' },
    @{ t='msg'; o='gst'; d='cor'; n='1.16: enviarBienvenida(correo, slug)' },
    @{ t='msg'; o='gst'; d='frm'; n='1.17: mostrarComprobante(pago, slug)' }
  )
},

# ---------------------------------------------------------------- CU-12 --
@{
  cu = 'CU-12'; nombre = '3.3 CU-12 Personalizar la tienda de la empresa'
  lineas = @(
    @{ k = 'act'; actor = 'Administrador de la empresa' },
    @{ k = 'pan'; clase = 'PantallaMiTienda' },
    @{ k = 'tie'; clase = 'TiendaEnLinea' },
    @{ k = 'gst'; clase = 'GestorMarca' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'ver'; clase = 'VerificadorPlan' },
    @{ k = 'emp'; clase = 'Empresa' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nLogo y colores" },
    @{ t='msg'; o='act'; d='pan'; n='1: abrirMiTienda()' },
    @{ t='msg'; o='pan'; d='gst'; n='1.1: obtenerMarca()' },
    @{ t='msg'; o='gst'; d='aut'; n='1.2: autorizar("ADMINISTRADOR")' },
    @{ t='msg'; o='gst'; d='ver'; n='1.3: verificar(empresa, "marca_propia")' },
    @{ t='msg'; o='ver'; d='gst'; n='1.3.1: boolean'; ret=$true },
    @{ t='msg'; o='gst'; d='emp'; n='1.4: obtenerMarca()' },
    @{ t='msg'; o='emp'; d='gst'; n='1.4.1: Marca'; ret=$true },
    @{ t='msg'; o='gst'; d='pan'; n='1.5: mostrarVistaPrevia(marca)' },
    @{ t='msg'; o='act'; d='pan'; n='1.6: guardarMarca(logo, colorPrincipal, colorSecundario)' },
    @{ t='msg'; o='pan'; d='gst'; n='1.7: guardarMarca(logo, colores)' },
    @{ t='break'; g='el plan no incluye la marca propia' },
    @{ t='msg'; o='gst'; d='pan'; n='2: funcionNoIncluida()' },
    @{ t='fin' },
    @{ t='msg'; o='gst'; d='gst'; n='1.8: validarLogo(logo)' },
    @{ t='alt' },
    @{ t='op'; g='PNG, JPEG o WEBP válido' },
    @{ t='msg'; o='gst'; d='emp'; n='1.9: guardarMarca(logo, colores)' },
    @{ t='msg'; o='gst'; d='tie'; n='1.10: aplicarMarca(marca)' },
    @{ t='op'; g='no es una imagen válida' },
    @{ t='msg'; o='gst'; d='pan'; n='3: imagenInvalida()' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-13 --
# Fragmentos: alt de offline/service.py:120 (SinTurnoAbierto -> 409); el
# paquete del movil se guarda en una transaccion (base_local.dart:106) y las
# fotos se bajan una por una.
@{
  cu = 'CU-13'; nombre = '3.3 CU-13 Preparar el dispositivo para trabajar offline'
  lineas = @(
    @{ k = 'caj'; actor = 'Cajero' },
    @{ k = 'acl'; actor = 'Cliente' },
    @{ k = 'pan'; clase = 'PantallaSinConexion' },
    @{ k = 'ctl'; clase = 'ControlOffline' },
    @{ k = 'paq'; clase = 'PaqueteLocal' },
    @{ k = 'ope'; clase = 'OperacionLocal' },
    @{ k = 'fot'; clase = 'FotoLocal' },
    @{ k = 'gst'; clase = 'GestorOffline' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'tur'; clase = 'TurnoCaja' },
    @{ k = 'exi'; clase = 'Existencia' },
    @{ k = 'cli'; clase = 'Cliente' },
    @{ k = 'suc'; clase = 'Sucursal' },
    @{ k = 'img'; clase = 'ImagenProducto' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nEl cajero prepara la PWA" },
    @{ t='msg'; o='caj'; d='pan'; n='1: preparar()' },
    @{ t='msg'; o='pan'; d='ctl'; n='1.1: preparar()' },
    @{ t='msg'; o='ctl'; d='gst'; n='1.2: paqueteDeMostrador()' },
    @{ t='msg'; o='gst'; d='aut'; n='1.3: autorizar("CAJERO")' },
    @{ t='msg'; o='gst'; d='tur'; n='1.4: turnoAbiertoDe(usuario)' },
    @{ t='msg'; o='tur'; d='gst'; n='1.4.1: TurnoCaja | None'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='tiene un turno abierto' },
    @{ t='msg'; o='gst'; d='exi'; n='1.5: prendasDeSucursal(sucursal)' },
    @{ t='msg'; o='exi'; d='gst'; n='1.5.1: List<Existencia>'; ret=$true },
    @{ t='msg'; o='gst'; d='cli'; n='1.6: clientesDeLaEmpresa()' },
    @{ t='msg'; o='cli'; d='gst'; n='1.6.1: List<Cliente>'; ret=$true },
    @{ t='msg'; o='gst'; d='ctl'; n='1.7: paquete(prendas, clientes, turno, vigencia)'; ret=$true },
    @{ t='msg'; o='ctl'; d='paq'; n='1.8: guardar(paquete)' },
    @{ t='msg'; o='ctl'; d='pan'; n='1.9: mostrarResumen(fecha, prendas)' },
    @{ t='op'; g='no tiene turno abierto' },
    @{ t='msg'; o='gst'; d='ctl'; n='3: turnoNoAbierto() -> 409'; ret=$true },
    @{ t='msg'; o='ctl'; d='pan'; n='3.1: pedirAbrirTurno()' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 2`nEl cliente prepara el teléfono" },
    @{ t='msg'; o='acl'; d='pan'; n='2: prepararTelefono()' },
    @{ t='msg'; o='pan'; d='ctl'; n='2.1: preparar()' },
    @{ t='alt' },
    @{ t='op'; g='hay conexión' },
    @{ t='msg'; o='ctl'; d='gst'; n='2.2: paqueteDeCliente()' },
    @{ t='msg'; o='gst'; d='aut'; n='2.3: autorizar("CLIENTE")' },
    @{ t='msg'; o='gst'; d='suc'; n='2.4: sucursalesActivas()' },
    @{ t='msg'; o='suc'; d='gst'; n='2.4.1: List<Sucursal>'; ret=$true },
    @{ t='msg'; o='gst'; d='exi'; n='2.5: prendasEnSucursalesActivas()' },
    @{ t='msg'; o='exi'; d='gst'; n='2.5.1: List<Existencia>'; ret=$true },
    @{ t='msg'; o='gst'; d='img'; n='2.6: imagenPrincipal(productos)' },
    @{ t='msg'; o='img'; d='gst'; n='2.6.1: Map<producto, url>'; ret=$true },
    @{ t='msg'; o='gst'; d='ctl'; n='2.7: paquete(sucursales, prendas, vigencia)'; ret=$true },
    @{ t='critical'; g='' },
    @{ t='msg'; o='ctl'; d='paq'; n='2.8: guardarPaquete(paquete)' },
    @{ t='fin' },
    @{ t='msg'; o='ctl'; d='ope'; n='2.9: pendientes()' },
    @{ t='msg'; o='ope'; d='ctl'; n='2.9.1: List<OperacionLocal>'; ret=$true },
    @{ t='msg'; o='ctl'; d='paq'; n='2.10: descontar(sucursal, cantidades)' },
    @{ t='loop'; g='por cada foto del paquete' },
    @{ t='msg'; o='ctl'; d='fot'; n='2.11: guardarFotos(urls)' },
    @{ t='fin' },
    @{ t='msg'; o='ctl'; d='pan'; n='2.12: mostrarResumen(fecha, sucursales, prendas)' },
    @{ t='op'; g='sin conexión' },
    @{ t='msg'; o='ctl'; d='paq'; n='4: leerPaquete()' },
    @{ t='msg'; o='ctl'; d='pan'; n='4.1: avisarSinConexion()' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-14 --
# Todo pasa en el navegador: no hay llamada al servidor ni bitacora hasta
# que se sincroniza (CU-17). El alt de afuera es el metodo de pago; el de
# adentro, si IndexedDB pudo guardar la operacion.
@{
  cu = 'CU-14'; nombre = '3.3 CU-14 Registrar venta offline'
  lineas = @(
    @{ k = 'caj'; actor = 'Cajero' },
    @{ k = 'pan'; clase = 'PantallaVenta' },
    @{ k = 'ctl'; clase = 'ControlOffline' },
    @{ k = 'paq'; clase = 'PaqueteLocal' },
    @{ k = 'ope'; clase = 'OperacionLocal' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nVender sin conexión" },
    @{ t='msg'; o='caj'; d='pan'; n='1: buscarPrenda(texto)' },
    @{ t='msg'; o='pan'; d='ctl'; n='1.1: prendasGuardadas(texto)' },
    @{ t='msg'; o='ctl'; d='paq'; n='1.2: leerPrendas()' },
    @{ t='msg'; o='paq'; d='ctl'; n='1.2.1: List<PrendaOffline>'; ret=$true },
    @{ t='msg'; o='ctl'; d='pan'; n='1.3: mostrarPrendas(prendas)' },
    @{ t='msg'; o='caj'; d='pan'; n='1.4: agregar(prenda, cantidad)' },
    @{ t='msg'; o='caj'; d='pan'; n='1.5: cobrar(metodo, recibido)' },
    @{ t='alt' },
    @{ t='op'; g='efectivo o QR' },
    @{ t='msg'; o='pan'; d='ctl'; n='1.6: registrarVenta(lineas, pago)' },
    @{ t='msg'; o='ctl'; d='ctl'; n='1.7: generarUuid()' },
    @{ t='alt' },
    @{ t='op'; g='el navegador guardó la operación' },
    @{ t='msg'; o='ctl'; d='ope'; n='1.8: guardar(operacion, "guardada")' },
    @{ t='msg'; o='ctl'; d='paq'; n='1.9: descontar(cantidades)' },
    @{ t='msg'; o='ctl'; d='pan'; n='1.10: mostrarComprobanteProvisional(operacion)' },
    @{ t='op'; g='no se pudo guardar en el navegador' },
    @{ t='msg'; o='ctl'; d='pan'; n='3: noSePudoGuardar(error)' },
    @{ t='fin' },
    @{ t='op'; g='tarjeta' },
    @{ t='msg'; o='ctl'; d='pan'; n='2: metodosSinRed(EFECTIVO, QR)' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-15 --
# Movil. Los maximos y el horario se validan en el telefono antes de
# guardar; descontar() corre en una transaccion de SQLite (base_local.dart:208).
@{
  cu = 'CU-15'; nombre = '3.3 CU-15 Registrar reserva offline'
  lineas = @(
    @{ k = 'acl'; actor = 'Cliente' },
    @{ k = 'pan'; clase = 'PantallaReservaSinRed' },
    @{ k = 'ctl'; clase = 'ControlOffline' },
    @{ k = 'paq'; clase = 'PaqueteLocal' },
    @{ k = 'fot'; clase = 'FotoLocal' },
    @{ k = 'ope'; clase = 'OperacionLocal' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nReservar sin conexión" },
    @{ t='msg'; o='acl'; d='pan'; n='1: abrirNuevaReserva()' },
    @{ t='msg'; o='pan'; d='ctl'; n='1.1: paquete()' },
    @{ t='msg'; o='ctl'; d='paq'; n='1.2: leerPaquete()' },
    @{ t='msg'; o='paq'; d='ctl'; n='1.2.1: PaqueteCliente'; ret=$true },
    @{ t='msg'; o='ctl'; d='pan'; n='1.3: mostrarSucursales(sucursales)' },
    @{ t='msg'; o='acl'; d='pan'; n='1.4: elegirSucursal(sucursal)' },
    @{ t='msg'; o='acl'; d='pan'; n='1.5: elegirFranja(dia, hora, duracion)' },
    @{ t='msg'; o='pan'; d='ctl'; n='1.6: vitrina(sucursal, categoria, texto)' },
    @{ t='msg'; o='ctl'; d='paq'; n='1.7: prendasConSaldo(sucursal)' },
    @{ t='msg'; o='paq'; d='ctl'; n='1.7.1: List<PrendaCliente>'; ret=$true },
    @{ t='loop'; g='por cada producto de la vitrina' },
    @{ t='msg'; o='ctl'; d='fot'; n='1.8: foto(producto)' },
    @{ t='msg'; o='fot'; d='ctl'; n='1.8.1: File | null'; ret=$true },
    @{ t='fin' },
    @{ t='msg'; o='ctl'; d='pan'; n='1.9: mostrarVitrina(productos)' },
    @{ t='msg'; o='acl'; d='pan'; n='1.10: elegirVariante(talla, color, cantidad)' },
    @{ t='msg'; o='acl'; d='pan'; n='1.11: guardar()' },
    @{ t='msg'; o='pan'; d='ctl'; n='1.12: reservar(sucursal, prendas, inicio, fin)' },
    @{ t='alt' },
    @{ t='op'; g='dentro de los máximos y del horario' },
    @{ t='msg'; o='ctl'; d='ctl'; n='1.13: generarUuid()' },
    @{ t='msg'; o='ctl'; d='ope'; n='1.14: guardarOperacion(operacion)' },
    @{ t='critical'; g='' },
    @{ t='msg'; o='ctl'; d='paq'; n='1.15: descontar(sucursal, cantidades)' },
    @{ t='fin' },
    @{ t='msg'; o='ctl'; d='pan'; n='1.16: reservaGuardada(operacion)' },
    @{ t='op'; g='se alcanzó un máximo' },
    @{ t='msg'; o='ctl'; d='pan'; n='2: limiteAlcanzado()' },
    @{ t='op'; g='la hora ya pasó o cae fuera del horario' },
    @{ t='msg'; o='ctl'; d='pan'; n='3: fueraDeHorario(apertura, cierre)' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-16 --
@{
  cu = 'CU-16'; nombre = '3.3 CU-16 Registrar pago sin conexión'
  lineas = @(
    @{ k = 'caj'; actor = 'Cajero' },
    @{ k = 'pan'; clase = 'PantallaVenta' },
    @{ k = 'ctl'; clase = 'ControlOffline' },
    @{ k = 'ope'; clase = 'OperacionLocal' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nCobrar en efectivo" },
    @{ t='msg'; o='caj'; d='pan'; n='1: elegirMetodo("EFECTIVO")' },
    @{ t='msg'; o='pan'; d='ctl'; n='1.1: metodosSinRed()' },
    @{ t='msg'; o='ctl'; d='pan'; n='1.2: mostrarMetodos(EFECTIVO, QR)' },
    @{ t='msg'; o='caj'; d='pan'; n='1.3: ingresarRecibido(monto)' },
    @{ t='msg'; o='pan'; d='ctl'; n='1.4: calcularVuelto(total, recibido)' },
    @{ t='alt' },
    @{ t='op'; g='recibido >= total' },
    @{ t='msg'; o='ctl'; d='pan'; n='1.5: mostrarVuelto(vuelto)' },
    @{ t='msg'; o='pan'; d='ctl'; n='1.6: registrarPago(metodo, monto, referencia)' },
    @{ t='msg'; o='ctl'; d='ope'; n='1.7: guardarPago(operacion, pago)' },
    @{ t='op'; g='recibido < total' },
    @{ t='msg'; o='ctl'; d='pan'; n='3: recibidoInsuficiente()' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 2`nCobrar con QR" },
    @{ t='msg'; o='caj'; d='pan'; n='2: anotarReferencia(referencia)' },
    @{ t='msg'; o='pan'; d='ctl'; n='2.1: registrarPago("QR", monto, referencia)' },
    @{ t='opt'; g='falta la referencia' },
    @{ t='msg'; o='ctl'; d='pan'; n='2.2: pedirReferencia()' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-17 --
# offline/service.py: el for de sincronizar() (:212) es el loop del lote;
# el alt de :241 separa la operacion repetida (RNF05); el begin_nested de
# :262 (abrirPuntoDeGuardado) es el critical, con el if VENTA/else RESERVA adentro; y el except
# Rechazo de :275 da los dos rechazos. Sin red, la PWA deja la operacion en
# 'enviada' y reintenta al minuto (offline.service.ts:256).
@{
  cu = 'CU-17'; nombre = '3.3 CU-17 Sincronizar operaciones pendientes'
  lineas = @(
    @{ k = 'caj'; actor = 'Cajero' },
    @{ k = 'acl'; actor = 'Cliente' },
    @{ k = 'evt'; clase = 'EventoDeConexion' },
    @{ k = 'pan'; clase = 'PantallaSinConexion' },
    @{ k = 'ctl'; clase = 'ControlOffline' },
    @{ k = 'ope'; clase = 'OperacionLocal' },
    @{ k = 'gst'; clase = 'GestorOffline' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'inv'; clase = 'GestorInventario' },
    @{ k = 'grs'; clase = 'GestorReservas' },
    @{ k = 'bit'; clase = 'BitacoraMiddleware' },
    @{ k = 'oof'; clase = 'OperacionOffline' },
    @{ k = 'tur'; clase = 'TurnoCaja' },
    @{ k = 'exi'; clase = 'Existencia' },
    @{ k = 'ven'; clase = 'Venta' },
    @{ k = 'rsv'; clase = 'Reserva' },
    @{ k = 'asi'; clase = 'AsientoBitacora' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nEl servidor confirma" },
    @{ t='msg'; o='evt'; d='ctl'; n='1: conexionRecuperada()' },
    @{ t='msg'; o='caj'; d='pan'; n='1.1: sincronizarAhora()' },
    @{ t='msg'; o='acl'; d='pan'; n='1.2: sincronizarAhora()' },
    @{ t='msg'; o='pan'; d='ctl'; n='1.3: sincronizar()' },
    @{ t='msg'; o='ctl'; d='ope'; n='1.4: pendientes()' },
    @{ t='msg'; o='ope'; d='ctl'; n='1.4.1: List<OperacionGuardada>'; ret=$true },
    @{ t='loop'; g='por cada operación pendiente' },
    @{ t='msg'; o='ctl'; d='ope'; n='1.5: marcar(uuid, "enviada")' },
    @{ t='fin' },
    @{ t='alt' },
    @{ t='op'; g='el servidor responde' },
    @{ t='msg'; o='ctl'; d='gst'; n='1.6: sincronizar(lote)' },
    @{ t='msg'; o='gst'; d='aut'; n='1.7: autorizar(rol)' },
    @{ t='loop'; g='por cada operación del lote' },
    @{ t='msg'; o='gst'; d='oof'; n='1.8: operacionPorUuid(uuid)' },
    @{ t='msg'; o='oof'; d='gst'; n='1.8.1: OperacionOffline | None'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='la operación es nueva' },
    @{ t='msg'; o='gst'; d='gst'; n='1.8.2: abrirPuntoDeGuardado()' },
    @{ t='critical'; g='' },
    @{ t='alt' },
    @{ t='op'; g='es una venta' },
    @{ t='msg'; o='gst'; d='tur'; n='1.9: turnoPorId(turno)' },
    @{ t='msg'; o='tur'; d='gst'; n='1.9.1: TurnoCaja'; ret=$true },
    @{ t='msg'; o='gst'; d='inv'; n='1.10: descontar(sucursal, lineas)' },
    @{ t='msg'; o='inv'; d='exi'; n='1.11: bloquearYDescontar(variante, cantidad)' },
    @{ t='msg'; o='gst'; d='ven'; n='1.12: crear(venta)' },
    @{ t='op'; g='es una reserva' },
    @{ t='msg'; o='gst'; d='grs'; n='1.13: crear(reserva)' },
    @{ t='msg'; o='grs'; d='rsv'; n='1.14: crear(reserva)' },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='alt' },
    @{ t='op'; g='sin rechazo' },
    @{ t='msg'; o='gst'; d='oof'; n='1.15: guardar(operacion, "CONFIRMADA")' },
    @{ t='op'; g='ya no alcanza la existencia' },
    @{ t='msg'; o='inv'; d='gst'; n='4: existenciaInsuficiente()'; ret=$true },
    @{ t='msg'; o='gst'; d='gst'; n='4a: deshacerPuntoDeGuardado()' },
    @{ t='msg'; o='gst'; d='oof'; n='4.1: guardar(operacion, "RECHAZADA", motivo)' },
    @{ t='msg'; o='gst'; d='ctl'; n='4.2: rechazada(uuid, motivo, requiereDevolucion)'; ret=$true },
    @{ t='op'; g='turno ajeno o reserva fuera de horario' },
    @{ t='msg'; o='gst'; d='oof'; n='5: guardar(operacion, "RECHAZADA", motivo)' },
    @{ t='msg'; o='gst'; d='ctl'; n='5.1: rechazada(uuid, motivo)'; ret=$true },
    @{ t='fin' },
    @{ t='op'; g='ya estaba registrada' },
    @{ t='msg'; o='gst'; d='oof'; n='3: resultadoRegistrado(uuid)' },
    @{ t='msg'; o='gst'; d='ctl'; n='3.1: resultado(uuid, repetida)'; ret=$true },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='msg'; o='gst'; d='bit'; n='1.16: registrar(peticion)' },
    @{ t='msg'; o='bit'; d='asi'; n='1.17: agregar(accion, usuario, ip)' },
    @{ t='msg'; o='gst'; d='ctl'; n='1.18: resultados(lote)'; ret=$true },
    @{ t='msg'; o='ctl'; d='ope'; n='1.19: actualizar(uuid, estado, motivo)' },
    @{ t='msg'; o='ctl'; d='pan'; n='1.20: mostrarResultado(confirmadas, rechazadas)' },
    @{ t='op'; g='el servidor no responde' },
    @{ t='msg'; o='ctl'; d='ope'; n='2: marcar(uuid, "enviada")' },
    @{ t='msg'; o='ctl'; d='ctl'; n='2.1: reintentarEnUnMinuto()' },
    @{ t='fin' }
  )
},

# ---------------------------------------------------------------- CU-18 --
# Solo local: nadie llama a GET /operaciones/mias.
@{
  cu = 'CU-18'; nombre = '3.3 CU-18 Consultar operaciones pendientes'
  lineas = @(
    @{ k = 'caj'; actor = 'Cajero' },
    @{ k = 'acl'; actor = 'Cliente' },
    @{ k = 'pan'; clase = 'PantallaSinConexion' },
    @{ k = 'ctl'; clase = 'ControlOffline' },
    @{ k = 'ope'; clase = 'OperacionLocal' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nVer la cola" },
    @{ t='msg'; o='caj'; d='pan'; n='1: abrirSinConexion()' },
    @{ t='msg'; o='acl'; d='pan'; n='1.1: abrirSinConexion()' },
    @{ t='msg'; o='pan'; d='ctl'; n='1.2: operaciones()' },
    @{ t='msg'; o='ctl'; d='ope'; n='1.3: listar()' },
    @{ t='msg'; o='ope'; d='ctl'; n='1.3.1: List<OperacionGuardada>'; ret=$true },
    @{ t='msg'; o='ctl'; d='pan'; n='1.4: mostrarCola(operaciones, pendientes, enLinea)' },
    @{ t='nota'; txt = "FLUJO 2`nSincronizar ahora" },
    @{ t='msg'; o='caj'; d='pan'; n='2: sincronizarAhora()' },
    @{ t='msg'; o='pan'; d='ctl'; n='2.1: sincronizar()' },
    @{ t='nota'; txt = "FLUJO 3`nLimpiar el historial" },
    @{ t='msg'; o='caj'; d='pan'; n='3: limpiarHistorial()' },
    @{ t='msg'; o='pan'; d='ctl'; n='3.1: limpiarDecididas()' },
    @{ t='loop'; g='por cada operación confirmada o devuelta' },
    @{ t='msg'; o='ctl'; d='ope'; n='3.2: borrarDecididas()' },
    @{ t='fin' },
    @{ t='msg'; o='ctl'; d='pan'; n='3.3: mostrarCola(operaciones)' }
  )
},

# ---------------------------------------------------------------- CU-19 --
# offline/service.py:534 registrar_devolucion: la referencia del QR la pide
# el esquema (422) antes de leer; los raise de :552 a :559 son 'nada que
# devolver' (404/409). Un solo commit (:566).
@{
  cu = 'CU-19'; nombre = '3.3 CU-19 Atender operaciones rechazadas y devolver el dinero'
  lineas = @(
    @{ k = 'enc'; actor = 'Encargado de sucursal' },
    @{ k = 'pan'; clase = 'PantallaOperacionesSinConexion' },
    @{ k = 'gst'; clase = 'GestorOffline' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'bit'; clase = 'BitacoraMiddleware' },
    @{ k = 'oof'; clase = 'OperacionOffline' },
    @{ k = 'usu'; clase = 'Usuario' },
    @{ k = 'asi'; clase = 'AsientoBitacora' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nRegistrar la devolución" },
    @{ t='msg'; o='enc'; d='pan'; n='1: abrirOperaciones()' },
    @{ t='msg'; o='pan'; d='gst'; n='1.1: operacionesDeSucursal(porDevolver)' },
    @{ t='msg'; o='gst'; d='aut'; n='1.2: autorizar("ENCARGADO")' },
    @{ t='msg'; o='gst'; d='oof'; n='1.3: operaciones(sucursal, porDevolver)' },
    @{ t='msg'; o='oof'; d='gst'; n='1.3.1: List<OperacionOffline>'; ret=$true },
    @{ t='loop'; g='por cada operación' },
    @{ t='msg'; o='gst'; d='usu'; n='1.4: nombreDe(usuario)' },
    @{ t='fin' },
    @{ t='msg'; o='gst'; d='pan'; n='1.5: mostrarPorDevolver(operaciones)' },
    @{ t='msg'; o='enc'; d='pan'; n='1.6: registrarDevolucion(uuid, metodo, referencia, observacion)' },
    @{ t='msg'; o='pan'; d='gst'; n='1.7: registrarDevolucion(uuid, datos)' },
    @{ t='break'; g='devuelve por QR sin referencia' },
    @{ t='msg'; o='gst'; d='pan'; n='3: pedirReferencia() -> 422' },
    @{ t='fin' },
    @{ t='msg'; o='gst'; d='oof'; n='1.8: operacionPorUuid(uuid, bloquear)' },
    @{ t='msg'; o='oof'; d='gst'; n='1.8.1: OperacionOffline'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='rechazada, cobrada y sin devolver' },
    @{ t='msg'; o='gst'; d='oof'; n='1.9: marcarDevuelta(usuario, metodo, referencia)' },
    @{ t='msg'; o='gst'; d='bit'; n='1.10: registrar(peticion)' },
    @{ t='msg'; o='bit'; d='asi'; n='1.11: agregar(accion, usuario, entidad)' },
    @{ t='msg'; o='gst'; d='pan'; n='1.12: devolucionRegistrada(monto)' },
    @{ t='op'; g='confirmada, sin cobro o ya devuelta' },
    @{ t='msg'; o='gst'; d='pan'; n='4: nadaQueDevolver(motivo) -> 409' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 2`nVer todas" },
    @{ t='msg'; o='enc'; d='pan'; n='2: verTodas()' },
    @{ t='msg'; o='pan'; d='gst'; n='2.1: operacionesDeSucursal(porDevolver)' }
  )
},

# ---------------------------------------------------------------- CU-20 --
# caja/service.py:162 abrir: bloquea la caja y el alt de 'caja ocupada'.
# La web sincroniza antes de cerrar y no cierra si quedan ventas sin subir
# (features/caja/turno). caja/service.py:198 cerrar: el esperado suma las
# ventas offline y lo que falta devolver.
@{
  cu = 'CU-20'; nombre = '3.3 CU-20 Abrir y cerrar caja con ventas offline'
  lineas = @(
    @{ k = 'caj'; actor = 'Cajero' },
    @{ k = 'pan'; clase = 'PantallaTurno' },
    @{ k = 'ctl'; clase = 'ControlOffline' },
    @{ k = 'ope'; clase = 'OperacionLocal' },
    @{ k = 'gst'; clase = 'GestorCaja' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'bit'; clase = 'BitacoraMiddleware' },
    @{ k = 'cja'; clase = 'Caja' },
    @{ k = 'tur'; clase = 'TurnoCaja' },
    @{ k = 'ven'; clase = 'Venta' },
    @{ k = 'dev'; clase = 'Devolucion' },
    @{ k = 'oof'; clase = 'OperacionOffline' },
    @{ k = 'asi'; clase = 'AsientoBitacora' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1`nAbrir el turno" },
    @{ t='msg'; o='caj'; d='pan'; n='1: abrirTurno(caja, montoApertura)' },
    @{ t='msg'; o='pan'; d='gst'; n='1.1: abrir(caja, monto)' },
    @{ t='msg'; o='gst'; d='aut'; n='1.2: autorizar("CAJERO")' },
    @{ t='msg'; o='gst'; d='cja'; n='1.3: bloquearCaja(caja)' },
    @{ t='alt' },
    @{ t='op'; g='la caja está libre' },
    @{ t='msg'; o='gst'; d='tur'; n='1.4: abrir(caja, usuario, monto)' },
    @{ t='msg'; o='tur'; d='gst'; n='1.4.1: TurnoCaja'; ret=$true },
    @{ t='msg'; o='gst'; d='pan'; n='1.5: mostrarTurno(turno)' },
    @{ t='op'; g='todas las cajas están ocupadas' },
    @{ t='msg'; o='gst'; d='cja'; n='2: cajasDeSucursal(sucursal)' },
    @{ t='msg'; o='gst'; d='pan'; n='2.1: cajasOcupadas(cajas)' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 1`nCerrar el turno" },
    @{ t='msg'; o='caj'; d='pan'; n='1.6: cerrarTurno(montoContado)' },
    @{ t='msg'; o='pan'; d='ctl'; n='1.7: pendientesDelTurno(turno)' },
    @{ t='msg'; o='ctl'; d='ope'; n='1.8: pendientes()' },
    @{ t='msg'; o='ope'; d='ctl'; n='1.8.1: List<OperacionGuardada>'; ret=$true },
    @{ t='opt'; g='hay ventas sin conexión en la cola' },
    @{ t='msg'; o='ctl'; d='ctl'; n='3: sincronizar()' },
    @{ t='fin' },
    @{ t='break'; g='siguen quedando ventas sin subir' },
    @{ t='msg'; o='ctl'; d='pan'; n='3.1: quedanSinSubir(cantidad)' },
    @{ t='msg'; o='pan'; d='gst'; n='3.2: miTurno()' },
    @{ t='msg'; o='gst'; d='pan'; n='3.3: mostrarArqueo(esperado)' },
    @{ t='fin' },
    @{ t='msg'; o='pan'; d='gst'; n='1.9: cerrar(turno, montoContado)' },
    @{ t='msg'; o='gst'; d='ven'; n='1.10: efectivoCobrado(turno)' },
    @{ t='msg'; o='ven'; d='gst'; n='1.10.1: Decimal'; ret=$true },
    @{ t='msg'; o='gst'; d='dev'; n='1.11: devolucionesDelTurno(turno)' },
    @{ t='msg'; o='dev'; d='gst'; n='1.11.1: Decimal'; ret=$true },
    @{ t='msg'; o='gst'; d='dev'; n='1.12: diferenciasDeCambios(turno)' },
    @{ t='msg'; o='dev'; d='gst'; n='1.12.1: Decimal'; ret=$true },
    @{ t='msg'; o='gst'; d='oof'; n='1.13: efectivoPorDevolver(turno)' },
    @{ t='msg'; o='oof'; d='gst'; n='1.13.1: (cantidad, Decimal)'; ret=$true },
    @{ t='msg'; o='gst'; d='oof'; n='1.14: ventasOfflineDelTurno(turno)' },
    @{ t='msg'; o='oof'; d='gst'; n='1.14.1: (cantidad, Decimal)'; ret=$true },
    @{ t='msg'; o='gst'; d='tur'; n='1.15: guardarCierre(esperado, contado)' },
    @{ t='msg'; o='gst'; d='bit'; n='1.16: registrar(peticion)' },
    @{ t='msg'; o='bit'; d='asi'; n='1.17: agregar(accion, usuario, entidad)' },
    @{ t='msg'; o='gst'; d='pan'; n='1.18: mostrarArqueo(esperado, contado, diferencia)' },
    @{ t='opt'; g='lo contado no coincide con lo esperado' },
    @{ t='msg'; o='gst'; d='pan'; n='4: registrarDiferencia(diferencia)' },
    @{ t='fin' }
  )
}
)

# =========================================================================
# MAQUETADO: donde va a dibujar EA cada mensaje, y las cajas alrededor.
#
# Medido el 25/10 exportando estos diagramas: EA apila los mensajes por SeqNo
# de 35 en 35 desde -135 y NO baja ninguno, ni por la cabecera de una caja ni
# por la guarda de un operando ni por un borde. (La regla del 29/09, que si
# bajaba algunos, dejaba aca los operandos corridos.) Asi que los mensajes
# quedan fijos y cada borde ---el de arriba de una caja, una divisoria entre
# operandos o el de abajo--- se pone en el HUECO entre dos mensajes seguidos.
# Si en un hueco caen varios bordes, se reparten parejo en el orden del guion.
# $pos: clave de linea -> @{ l; r } (bordes horizontales).
# =========================================================================
function Maquetar($cu, $pos) {
    $y = @(); $esAuto = @(); $notas = @(); $pendienteNota = $null
    $pila = New-Object System.Collections.ArrayList
    $frames = @(); $eventos = @(); $k = 0
    foreach ($p in $cu.guion) {
        switch ($p.t) {
            'nota' { $pendienteNota = $p.txt }
            'msg' {
                $yy = $Y_PRIMERO - $PASO * $k
                $y += $yy; $esAuto += ($p.o -eq $p.d)
                if ($pendienteNota) { $notas += @{ y = $yy; txt = $pendienteNota }; $pendienteNota = $null }
                foreach ($f in $pila) { $f.lv[$p.o] = $true; $f.lv[$p.d] = $true }
                $k++
            }
            { $_ -in 'alt', 'opt', 'break', 'loop', 'critical' } {
                $ops = New-Object System.Collections.ArrayList
                if ($p.t -ne 'alt') { [void]$ops.Add([string]$p.g) }
                $f = @{ tipo = $NTYPE[$p.t]; hondo = $pila.Count; cortes = New-Object System.Collections.ArrayList; ops = $ops; lv = @{}; desde = $k }
                [void]$pila.Add($f)
                $eventos += @{ hueco = $k; f = $f; que = 'top' }
            }
            'op' {
                $f = $pila[$pila.Count - 1]
                if ($f.ops.Count -gt 0) { $eventos += @{ hueco = $k; f = $f; que = 'corte' } }
                [void]$f.ops.Add($p.g)
            }
            'fin' {
                $f = $pila[$pila.Count - 1]; $pila.RemoveAt($pila.Count - 1)
                if ($k -eq $f.desde) { throw "$($cu.nombre): fragmento vacio" }
                $eventos += @{ hueco = $k; f = $f; que = 'bot' }
                $frames += $f
            }
        }
    }
    $n = $k
    # Cada hueco va desde la flecha del mensaje anterior (la de vuelta, si es
    # un auto-mensaje) hasta un poco arriba de la flecha del siguiente.
    foreach ($grupo in ($eventos | Group-Object { $_.hueco })) {
        $h = [int]$grupo.Name
        $arriba = if ($h -eq 0) { $y[0] + 40 } else { $y[$h - 1] - $(if ($esAuto[$h - 1]) { $AUTO } else { 0 }) - 3 }
        $abajo  = if ($h -lt $n) { $y[$h] + 5 } else { $arriba - 8 * ($grupo.Count + 1) }
        $i = 0
        foreach ($e in $grupo.Group) {
            $i++
            $pos_y = [int]($arriba - $i * ($arriba - $abajo) / ($grupo.Count + 1))
            switch ($e.que) { 'top' { $e.f.top = $pos_y } 'corte' { [void]$e.f.cortes.Add($pos_y) } 'bot' { $e.f.bot = $pos_y } }
        }
    }
    if ($pila.Count) { throw "$($cu.nombre): falta un 'fin'" }

    $x0 = [int]::MaxValue; $derecha = 0
    foreach ($key in $pos.Keys) { $x0 = [math]::Min($x0, $pos[$key].l); $derecha = [math]::Max($derecha, $pos[$key].r) }
    foreach ($f in $frames) {
        if ($f.tipo -eq 0) {
            # El 'alt' cruza el diagrama entero.
            $f.l = $x0 - 60 + 8 * $f.hondo
            $f.r = $derecha + 40 - 8 * $f.hondo
        } else {
            # Los demas abarcan solo las lineas de vida que tocan sus mensajes.
            $izq = [int]::MaxValue; $der = 0
            foreach ($key in $f.lv.Keys) { $izq = [math]::Min($izq, $pos[$key].l); $der = [math]::Max($der, $pos[$key].r) }
            if ($f.lv.Count -eq 1) { $der += 60 }
            $f.l = $izq - 15; $f.r = $der + 15
        }
        if ($f.ops.Count -ne $f.cortes.Count + 1) { throw "$($cu.nombre): operandos y cortes no cuadran" }
        $limites = @($f.top) + $f.cortes + @($f.bot)
        # EA lee los operandos de ABAJO hacia ARRIBA: se escriben al reves.
        $txt = ''
        for ($j = $f.ops.Count - 1; $j -ge 0; $j--) {
            $g = '{' + [guid]::NewGuid().ToString().ToUpper() + '}'
            $txt += "@PAR;Name=$($f.ops[$j]);Size=$($limites[$j] - $limites[$j + 1]);GUID=$g;@ENDPAR;"
        }
        $f.par = $txt
    }
    $bajo = ($y | Measure-Object -Minimum).Minimum - 60
    foreach ($f in $frames) { $bajo = [math]::Min($bajo, $f.bot - 30) }
    return @{ y = $y; notas = $notas; frames = $frames; bajo = $bajo }
}

# =========================================================================
# PARTE 1 - Enterprise Architect por COM
# =========================================================================

function Get-Paquete($padre, $nombre) {
    $padre.Packages.Refresh()
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    return $null
}
function Poner($dia, $el, $l, $r, $t, $b) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$r;t=$t;b=$b;", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
}

# Con la version de prueba, un EA nuevo por COM falla (CO_E_SERVER_EXEC_FAILURE)
# hasta que se acepta su cuadro de inicio, y solo una vez. Si ya hay un EA
# abierto se usa ese: se le abre el modelo y al final se cierra el archivo,
# no EA.
function Abrir-EA {
    try { return @{ ea = [Runtime.InteropServices.Marshal]::GetActiveObject('EA.App').Repository; propio = $false } }
    catch { return @{ ea = (New-Object -ComObject EA.Repository); propio = $true } }
}
function Cerrar-EA($h) {
    $h.ea.CloseFile()
    if ($h.propio) { $h.ea.Exit() }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($h.ea) | Out-Null
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}

$h = Abrir-EA; $ea = $h.ea
if (-not $ea.OpenFile($Modelo)) { throw "No se pudo abrir $Modelo" }
try {
    $root  = $ea.Models.GetAt(0)
    $pRaiz = Get-Paquete $root 'Violet Boutique'
    if (-not $pRaiz) { throw "No se encontro el paquete 'Violet Boutique'" }
    $pP2 = Get-Paquete $pRaiz 'PARCIAL 2 - ICONIX'
    if (-not $pP2) { throw "No se encontro 'PARCIAL 2 - ICONIX'" }
    $p32 = Get-Paquete $pP2 '3.2 Diagramas de Robustez'
    if (-not $p32) { throw "No se encontro el 3.2 de robustez del 2do parcial" }

    # Las clases del 3.2, por nombre y SOLO las de tipo Class: 'Usuario' y
    # 'Cliente' son tambien actores en ese paquete (trampa 4).
    $clase = @{}
    foreach ($e in $p32.Elements) { if ($e.Type -eq 'Class') { $clase[$e.Name] = $e } }

    $N33 = '3.3 Diagramas de Secuencia'
    if ($Rehacer) {
        $pP2.Packages.Refresh()
        for ($i = $pP2.Packages.Count - 1; $i -ge 0; $i--) {
            if ($pP2.Packages.GetAt($i).Name -eq $N33) { $pP2.Packages.DeleteAt($i, $false); Write-Output "  [$N33] borrado (-Rehacer)" }
        }
        $pP2.Packages.Refresh()
    }
    $p33 = Get-Paquete $pP2 $N33
    if (-not $p33) { $p33 = $pP2.Packages.AddNew($N33, 'Package'); [void]$p33.Update(); $pP2.Packages.Refresh() }

    $actor = @{}
    foreach ($e in $p33.Elements) { if ($e.Type -eq 'Actor') { $actor[$e.Name] = $e } }

    $pendientes = @()
    foreach ($cu in $CASOS) {
        if ($Solo -and $Solo -notcontains $cu.cu) { continue }
        $ya = $null
        foreach ($d in $p33.Diagrams) { if ($d.Name -eq $cu.nombre) { $ya = $d } }
        if ($ya) { Write-Output "  $($cu.nombre) ya existe, no se toca"; continue }

        # ---- Lineas de vida y su posicion horizontal ----
        $lv = @{}; $pos = @{}; $x = $X0
        foreach ($def in $cu.lineas) {
            if ($def.ContainsKey('actor')) {
                if (-not $actor.ContainsKey($def.actor)) {
                    $a = $p33.Elements.AddNew($def.actor, 'Actor'); [void]$a.Update(); $p33.Elements.Refresh()
                    $actor[$def.actor] = $a
                }
                $el = $actor[$def.actor]; $ancho = 110
            } else {
                if (-not $clase.ContainsKey($def.clase)) { throw "$($cu.cu): falta la clase '$($def.clase)' en el 3.2" }
                $el = $p33.Elements.AddNew('', 'Sequence')
                $el.Name = ''
                $el.ClassifierID = $clase[$def.clase].ElementID
                [void]$el.Update()
                $ancho = [math]::Max(120, 8 * $def.clase.Length + 30)
            }
            $lv[$def.k] = $el
            $pos[$def.k] = @{ l = $x; r = $x + $ancho }
            $x += $ancho + $GAP
        }
        $p33.Elements.Refresh()

        $m = Maquetar $cu $pos

        $dia = $p33.Diagrams.AddNew($cu.nombre, 'Sequence'); [void]$dia.Update(); $p33.Diagrams.Refresh()
        foreach ($def in $cu.lineas) { Poner $dia $lv[$def.k] $pos[$def.k].l $pos[$def.k].r $TOP_LV $m.bajo }
        foreach ($n in $m.notas) {
            $nota = $p33.Elements.AddNew('', 'Note'); $nota.Notes = $n.txt; [void]$nota.Update()
            Poner $dia $nota $NOTA_L $NOTA_R ($n.y + 12) ($n.y + 12 - $NOTA_ALTO)
        }
        $frags = @()
        foreach ($f in $m.frames) {
            $fr = $p33.Elements.AddNew('', 'InteractionFragment'); [void]$fr.Update()
            Poner $dia $fr $f.l $f.r $f.top $f.bot
            $frags += @{ g = $fr.ElementGUID; tipo = $f.tipo; par = $f.par }
        }
        $p33.Elements.Refresh()

        # ---- Los mensajes ----
        $geo = @(); $seq = 1; $i = 0
        foreach ($p in $cu.guion) {
            if ($p.t -ne 'msg') { continue }
            $src = $lv[$p.o]; $dst = $lv[$p.d]
            $c = $src.Connectors.AddNew($p.n, 'Sequence')
            $c.SupplierID = $dst.ElementID
            $c.Direction = 'Source -> Destination'
            $c.DiagramID = $dia.DiagramID
            $c.SequenceNo = $seq
            [void]$c.Update(); $src.Connectors.Refresh()
            $ret = $p.ContainsKey('ret') -and $p.ret
            $ye = if ($p.o -eq $p.d) { $m.y[$i] - $AUTO } else { $m.y[$i] }
            $geo += @{ g = $c.ConnectorGUID; seq = $seq; y = $m.y[$i]; ye = $ye; ret = $ret }
            $seq++; $i++
        }
        $pendientes += @{ cu = $cu; diaId = $dia.DiagramID; guid = $dia.DiagramGUID; geo = $geo; frags = $frags }
        Write-Output ("  {0}: {1} lineas, {2} mensajes, {3} fragmentos" -f $cu.nombre, $cu.lineas.Count, $geo.Count, $frags.Count)
    }
} finally {
    Cerrar-EA $h
}
Start-Sleep -Milliseconds 1500
if ($pendientes.Count -eq 0) { Write-Output 'Nada nuevo'; Write-Output 'OK'; exit 0 }

# =========================================================================
# PARTE 2 - Lo que la API COM no expone, directo sobre el .eapx (EA cerrado)
# =========================================================================

$cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$Modelo;")
$cn.Open()
function Exec($sql, $params) {
    $c = $cn.CreateCommand(); $c.CommandText = $sql
    if ($params) { foreach ($v in $params) { [void]$c.Parameters.AddWithValue('p', $v) } }
    return $c.ExecuteNonQuery()
}
function Scalar($sql) { $c = $cn.CreateCommand(); $c.CommandText = $sql; return $c.ExecuteScalar() }

foreach ($pend in $pendientes) {
    $cx = @{}
    $c = $cn.CreateCommand()
    $c.CommandText = "SELECT Object_ID, (RectLeft + RectRight) / 2 FROM t_diagramobjects WHERE Diagram_ID = $($pend.diaId)"
    $r = $c.ExecuteReader(); while ($r.Read()) { $cx[[int]$r[0]] = [int]$r[1] }; $r.Close()

    foreach ($x in $pend.geo) {
        $donde = "ea_guid = '$($x.g)'"
        $sx = $cx[[int](Scalar "SELECT Start_Object_ID FROM t_connector WHERE $donde")]
        $ex = $cx[[int](Scalar "SELECT End_Object_ID FROM t_connector WHERE $donde")]
        $tipo = if ($x.ret) { 'Return' } else { 'Call' }
        $flags = if ($x.seq -eq 1) { 'Activation=0;Initiate=1;ForceActivation=0;ExtendActivationUp=0;' } else { 'Activation=0;' }
        [void](Exec "UPDATE t_connector SET SeqNo = $($x.seq), PtStartX = $sx, PtStartY = $($x.y), PtEndX = $ex, PtEndY = $($x.ye), PDATA1 = 'Synchronous', PDATA2 = 'retval=void;', PDATA3 = '$tipo', StateFlags = '$flags' WHERE $donde")
    }
    foreach ($f in $pend.frags) {
        [void](Exec "UPDATE t_object SET NType = $($f.tipo), PDATA1 = '6' WHERE ea_guid = '$($f.g)'")
        # Un 'critical' no lleva guarda: sin la fila, EA no dibuja '[]'.
        if ($f.par -match 'Name=;' -and $f.par -notmatch 'Name=[^;]') { continue }
        # Los acentos por parametro (regla 9).
        $gx = '{' + [guid]::NewGuid().ToString().ToUpper() + '}'
        [void](Exec "INSERT INTO t_xref (XrefID, Name, Type, Visibility, Client, Description) VALUES ('$gx', 'Partitions', 'element property', 'Public', '$($f.g)', ?)" @($f.par))
    }

    # El estilo de los 3.2 del 1er parcial: Times New Roman en negrita, los
    # controles en naranja y las entidades en marron; fronteras, actores y
    # notas con el color de EA.
    $c = $cn.CreateCommand()
    # Las cajas quedan con la letra de EA: en negrita grande, la guarda de una
    # caja de un solo mensaje se pisa con el borde de abajo.
    $c.CommandText = "SELECT do.Object_ID, c.Stereotype FROM (t_diagramobjects do INNER JOIN t_object o ON o.Object_ID = do.Object_ID) LEFT JOIN t_object c ON c.Object_ID = o.Classifier WHERE do.Diagram_ID = $($pend.diaId) AND o.Object_Type <> 'InteractionFragment'"
    $r = $c.ExecuteReader(); $estilos = @{}
    while ($r.Read()) { $estilos[[int]$r[0]] = if ($r.IsDBNull(1)) { '' } else { [string]$r[1] } }
    $r.Close()
    foreach ($id in $estilos.Keys) {
        $bcol = switch ($estilos[$id]) { 'control' { 'BCol=13495295;' } 'entity' { 'BCol=8894686;' } default { '' } }
        $duid = ([guid]::NewGuid().ToString('N').Substring(0, 8)).ToUpper()
        [void](Exec "UPDATE t_diagramobjects SET ObjectStyle = 'DUID=$duid;${bcol}font=Times New Roman;bold=1;black=0;italic=0;ul=0;charset=0;pitch=18;fontsz=100;' WHERE Diagram_ID = $($pend.diaId) AND Object_ID = $id")
    }
    Write-Output "  $($pend.cu.nombre): geometria, retornos y operandos escritos"
}
$cn.Close()

# ---- Imagenes para revisar (opcional) ----
if ($Imagenes) {
    New-Item -ItemType Directory -Force $Imagenes | Out-Null
    $h = Abrir-EA; $ea = $h.ea
    [void]$ea.OpenFile($Modelo)
    $pi = $ea.GetProjectInterface()
    foreach ($pend in $pendientes) {
        $png = Join-Path $Imagenes "$($pend.cu.cu).png"
        [void]$pi.PutDiagramImageToFile($pend.guid, $png, 1)
    }
    Cerrar-EA $h
    Write-Output "  imagenes en $Imagenes"
}
Write-Output 'OK'
