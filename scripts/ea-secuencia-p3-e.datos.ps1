# Guiones del 3.3, CU-42 a CU-45 (grupo e). Los dibuja scripts/ea-secuencia-p3.ps1.
# Salen de la robustez de scripts/p3_datos_e.py (mismos participantes, mismos mensajes, mismo orden).
$CASOS_P3 = @(
# ---------------------------------------------------------------- CU-42 --
# frontend-web core/services/push-web.service.ts:98 'if (!clave) return' (opt de la clave VAPID);
# notificaciones/push_service.py:214 el while del despacho (loop, tope de 100) y :169 el for por
# cada dispositivo (loop anidado); push_service.py:84-86 el raise DispositivoAjeno -> 409 en el
# router.py:167 (break). El borrado del dispositivo inválido es el except ErrorDePush de :178-181.
@{
  cu = 'CU-42'; nombre = '3.3 CU-42 Enviar avisos push de las operaciones sin conexión'
  lineas = @(
    @{ k = 'sis'; actor = 'Sistema' },
    @{ k = 'usr'; actor = 'Usuario' },
    @{ k = 'pav'; clase = 'PantallaAvisos' },
    @{ k = 'pin'; clase = 'PantallaInicioSesion' },
    @{ k = 'tar'; clase = 'TareaProgramada' },
    @{ k = 'evt'; clase = 'EventoDeConexion' },
    @{ k = 'can'; clase = 'CanalPush' },
    @{ k = 'gpu'; clase = 'GestorPush' },
    @{ k = 'cpu'; clase = 'ControlPush' },
    @{ k = 'gno'; clase = 'GestorNotificaciones' },
    @{ k = 'gof'; clase = 'GestorOffline' },
    @{ k = 'cof'; clase = 'ControlOffline' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'bit'; clase = 'BitacoraMiddleware' },
    @{ k = 'sus'; clase = 'SuscripcionPush' },
    @{ k = 'not'; clase = 'Notificacion' },
    @{ k = 'asi'; clase = 'AsientoBitacora' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1" },
    @{ t='msg'; o='usr'; d='pav'; n='1: abrirCampanita()' },
    @{ t='msg'; o='pav'; d='cpu'; n='1.1: iniciar()' },
    @{ t='msg'; o='cpu'; d='gpu'; n='1.2: configuracion()' },
    @{ t='msg'; o='gpu'; d='aut'; n='1.3: autorizar(usuario)' },
    @{ t='msg'; o='gpu'; d='cpu'; n='1.4: clavePublicaVapid(clave)' },
    @{ t='msg'; o='usr'; d='pav'; n='1.5: recibirAvisosEnEsteDispositivo()' },
    @{ t='msg'; o='pav'; d='cpu'; n='1.6: activar()' },
    # push-web.service.ts:98
    @{ t='opt'; g='hay clave pública VAPID' },
    @{ t='msg'; o='cpu'; d='cpu'; n='1.7: pedirSuscripcion(clavePublica)' },
    @{ t='msg'; o='cpu'; d='gpu'; n='1.8: registrar("WEBPUSH", direccion, p256dh, auth, dispositivo)' },
    @{ t='msg'; o='gpu'; d='sus'; n='1.9: porDireccion(direccion, bloquear)' },
    @{ t='msg'; o='sus'; d='gpu'; n='1.9.1: SuscripcionPush | None'; ret=$true },
    @{ t='msg'; o='gpu'; d='sus'; n='1.10: guardar(usuario, canal, claves, dispositivo)' },
    @{ t='msg'; o='gpu'; d='bit'; n='1.11: registrar(peticion)' },
    @{ t='msg'; o='bit'; d='asi'; n='1.12: agregar(accion, usuario, entidad)' },
    @{ t='msg'; o='gpu'; d='cpu'; n='1.13: dispositivoRegistrado(suscripcion)' },
    @{ t='msg'; o='cpu'; d='pav'; n='1.14: mostrarAvisosActivos()' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 2" },
    @{ t='msg'; o='gno'; d='gpu'; n='2: tieneDispositivos(destinatario)' },
    @{ t='msg'; o='gpu'; d='sus'; n='2.1: existeDe(usuario)' },
    @{ t='msg'; o='sus'; d='gpu'; n='2.1.1: bool'; ret=$true },
    @{ t='msg'; o='gno'; d='not'; n='2.2: crear(aviso, push="PENDIENTE")' },
    @{ t='msg'; o='sis'; d='tar'; n='2.3: ejecutarVuelta()' },
    @{ t='msg'; o='tar'; d='gpu'; n='2.4: despachar()' },
    # push_service.py:214
    @{ t='loop'; g='mientras haya avisos pendientes (hasta 100)' },
    @{ t='msg'; o='gpu'; d='not'; n='2.5: tomarPendientePush()' },
    @{ t='msg'; o='not'; d='gpu'; n='2.5.1: Notificacion | None'; ret=$true },
    @{ t='msg'; o='gpu'; d='sus'; n='2.6: dispositivosDe(destinatario)' },
    @{ t='msg'; o='sus'; d='gpu'; n='2.6.1: list[SuscripcionPush]'; ret=$true },
    # push_service.py:169
    @{ t='loop'; g='por cada dispositivo del destinatario' },
    @{ t='msg'; o='gpu'; d='can'; n='2.7: enviar(destino, aviso)' },
    @{ t='msg'; o='gpu'; d='sus'; n='2.8: marcarUsada(ahora)' },
    @{ t='fin' },
    @{ t='msg'; o='gpu'; d='not'; n='2.9: marcarPush("ENVIADO", ahora)' },
    @{ t='fin' },
    @{ t='msg'; o='gpu'; d='tar'; n='2.10: resumen(intentadas, enviadas, fallidas)' },
    @{ t='nota'; txt = "FLUJO 3" },
    @{ t='msg'; o='sis'; d='evt'; n='3: conexionRecuperada()' },
    @{ t='msg'; o='evt'; d='cof'; n='3.1: sincronizar()' },
    @{ t='msg'; o='cof'; d='gof'; n='3.2: sincronizar(lote)' },
    @{ t='msg'; o='gof'; d='gno'; n='3.3: avisarA(destinatarios, "OPERACION_OFFLINE")' },
    @{ t='msg'; o='gno'; d='gof'; n='3.3.1: list[Notificacion]'; ret=$true },
    @{ t='msg'; o='gof'; d='gpu'; n='3.4: despacharSinFallar(idsDelLote)' },
    @{ t='msg'; o='gpu'; d='can'; n='3.5: enviar(destino, aviso)' },
    @{ t='nota'; txt = "FLUJO 4" },
    @{ t='msg'; o='usr'; d='pin'; n='4: iniciarSesion(slug, correo, contrasena)' },
    @{ t='msg'; o='pin'; d='cpu'; n='4.1: registrar(dio)' },
    @{ t='msg'; o='cpu'; d='cpu'; n='4.2: obtenerTokenFcm()' },
    @{ t='msg'; o='cpu'; d='gpu'; n='4.3: registrar("FCM", token, "App Android")' },
    @{ t='msg'; o='gpu'; d='sus'; n='4.4: guardar(usuario, canal, token)' },
    @{ t='nota'; txt = "FLUJO 5" },
    # push_service.py:84
    @{ t='break'; g='el dispositivo es de otra cuenta y no trae sus claves' },
    @{ t='msg'; o='gpu'; d='cpu'; n='5: dispositivoAjeno() -> 409' },
    @{ t='fin' },
    @{ t='msg'; o='can'; d='gpu'; n='5.1: errorDePush(invalida)' },
    @{ t='msg'; o='gpu'; d='sus'; n='5.2: borrar()' },
    @{ t='msg'; o='gpu'; d='not'; n='5.3: marcarPush("FALLIDO", motivo)' }
  )
},

# ---------------------------------------------------------------- CU-43 --
# offline/service.py:251 el for del lote (loop); :314 el begin_nested con el punto.rollback() del
# except Rechazo de :344 (critical); :362 'if fila.monto_cobrado is not None' + :721 'if metodo_pago
# != "QR": return' (opt del reintegro por QR); :811 'if cliente is not None' (opt del aviso al
# cliente en el efectivo).
@{
  cu = 'CU-43'; nombre = '3.3 CU-43 Devolver automáticamente el pago de una operación rechazada'
  lineas = @(
    @{ k = 'sis'; actor = 'Sistema' },
    @{ k = 'evt'; clase = 'EventoDeConexion' },
    @{ k = 'can'; clase = 'CanalPush' },
    @{ k = 'gof'; clase = 'GestorOffline' },
    @{ k = 'cof'; clase = 'ControlOffline' },
    @{ k = 'inv'; clase = 'GestorInventario' },
    @{ k = 'gno'; clase = 'GestorNotificaciones' },
    @{ k = 'gpu'; clase = 'GestorPush' },
    @{ k = 'bit'; clase = 'BitacoraMiddleware' },
    @{ k = 'oof'; clase = 'OperacionOffline' },
    @{ k = 'ope'; clase = 'OperacionLocal' },
    @{ k = 'cli'; clase = 'Cliente' },
    @{ k = 'usu'; clase = 'Usuario' },
    @{ k = 'suc'; clase = 'Sucursal' },
    @{ k = 'not'; clase = 'Notificacion' },
    @{ k = 'asi'; clase = 'AsientoBitacora' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1" },
    @{ t='msg'; o='sis'; d='evt'; n='1: conexionRecuperada()' },
    @{ t='msg'; o='evt'; d='cof'; n='1.1: sincronizar()' },
    @{ t='msg'; o='cof'; d='ope'; n='1.2: pendientes()' },
    @{ t='msg'; o='ope'; d='cof'; n='1.2.1: List<OperacionGuardada>'; ret=$true },
    @{ t='msg'; o='cof'; d='gof'; n='1.3: sincronizar(lote)' },
    # offline/service.py:251
    @{ t='loop'; g='por cada operación del lote' },
    @{ t='msg'; o='gof'; d='oof'; n='1.4: operacionPorUuid(uuid)' },
    @{ t='msg'; o='oof'; d='gof'; n='1.4.1: OperacionOffline | None'; ret=$true },
    # offline/service.py:314 y :344
    @{ t='critical'; g='punto de guardado: se deshace al rechazar' },
    @{ t='msg'; o='gof'; d='inv'; n='1.5: descontar(sucursal, lineas)' },
    @{ t='msg'; o='inv'; d='gof'; n='1.6: existenciaInsuficiente()' },
    @{ t='fin' },
    @{ t='msg'; o='gof'; d='gof'; n='1.7: limitarAlTotal(montoCobrado, total)' },
    # offline/service.py:362 y :721
    @{ t='opt'; g='se había cobrado por QR' },
    @{ t='msg'; o='gof'; d='gof'; n='1.8: reintegrarQr(operacion)' },
    @{ t='fin' },
    @{ t='msg'; o='gof'; d='oof'; n='1.9: guardar(operacion, "RECHAZADA", motivo, devolucionAutomatica, referencia)' },
    @{ t='msg'; o='gof'; d='gno'; n='1.10: usuarioDelCliente(cliente)' },
    @{ t='msg'; o='gno'; d='cli'; n='1.11: obtener(cliente)' },
    @{ t='msg'; o='cli'; d='gno'; n='1.11.1: Cliente | None'; ret=$true },
    @{ t='msg'; o='gno'; d='usu'; n='1.12: activo(usuario)' },
    @{ t='msg'; o='usu'; d='gno'; n='1.12.1: Usuario | None'; ret=$true },
    @{ t='msg'; o='gof'; d='gno'; n='1.13: avisarA([cliente], "DEVOLUCION_PAGO")' },
    @{ t='msg'; o='gno'; d='not'; n='1.14: crear(aviso)' },
    @{ t='msg'; o='not'; d='gno'; n='1.14.1: Notificacion'; ret=$true },
    @{ t='fin' },
    @{ t='msg'; o='gof'; d='bit'; n='1.15: registrar(peticion)' },
    @{ t='msg'; o='bit'; d='asi'; n='1.16: agregar(accion, usuario, entidad)' },
    @{ t='msg'; o='gof'; d='gpu'; n='1.17: despacharSinFallar(ids)' },
    @{ t='msg'; o='gpu'; d='not'; n='1.18: tomarPendientePush()' },
    @{ t='msg'; o='not'; d='gpu'; n='1.18.1: Notificacion | None'; ret=$true },
    @{ t='msg'; o='gpu'; d='can'; n='1.19: enviar(destino, aviso)' },
    @{ t='msg'; o='gof'; d='cof'; n='1.20: resultados(lote)' },
    @{ t='msg'; o='cof'; d='ope'; n='1.21: actualizar(uuid, "rechazada", reintegroQr)' },
    @{ t='nota'; txt = "FLUJO 2" },
    @{ t='msg'; o='gof'; d='oof'; n='2: guardar(operacion, "RECHAZADA", motivo)' },
    @{ t='msg'; o='gof'; d='gno'; n='2.1: avisarA([cliente], "OPERACION_OFFLINE")' },
    @{ t='nota'; txt = "FLUJO 3" },
    @{ t='msg'; o='gof'; d='suc'; n='3: sucursal(id)' },
    @{ t='msg'; o='gof'; d='gno'; n='3.1: encargadosDe(sucursal)' },
    @{ t='msg'; o='gno'; d='usu'; n='3.2: encargadosActivos(sucursal)' },
    @{ t='msg'; o='usu'; d='gno'; n='3.2.1: list[Usuario]'; ret=$true },
    @{ t='msg'; o='gof'; d='gno'; n='3.3: avisarA(encargados, "DEVOLUCION_PAGO")' },
    # offline/service.py:811
    @{ t='opt'; g='el cliente tiene cuenta' },
    @{ t='msg'; o='gof'; d='gno'; n='3.4: avisarA([cliente], "DEVOLUCION_PAGO")' },
    @{ t='fin' },
    @{ t='msg'; o='gof'; d='cof'; n='3.5: rechazada(uuid, motivo, requiereDevolucion)' },
    @{ t='nota'; txt = "FLUJO 4" },
    @{ t='msg'; o='gof'; d='gno'; n='4: avisarA([cajero], resumenDelLote)' },
    @{ t='msg'; o='gno'; d='not'; n='4.1: crear(aviso)' },
    @{ t='msg'; o='not'; d='gno'; n='4.1.1: Notificacion'; ret=$true }
  )
},

# ---------------------------------------------------------------- CU-44 --
# avisos_talla/service.py:169 'if existente is None' (opt del flujo 1) y su raise YaHayUnidades de
# :170-171 frente al aviso ya existente (alt del flujo 3); inventario/service.py:308 'if cantidad >
# 0' llama al gancho (opt) y avisos_talla/service.py:358 el for de los pendientes (loop anidado).
@{
  cu = 'CU-44'; nombre = '3.3 CU-44 Pedir aviso de talla disponible'
  lineas = @(
    @{ k = 'cl';  actor = 'Cliente' },
    @{ k = 'enc'; actor = 'Encargado de sucursal' },
    @{ k = 'adm'; actor = 'Administrador de la empresa' },
    @{ k = 'sis'; actor = 'Sistema' },
    @{ k = 'pfi'; clase = 'PantallaFicha' },
    @{ k = 'pma'; clase = 'PantallaMisAvisos' },
    @{ k = 'pte'; clase = 'PantallaTallasEsperadas' },
    @{ k = 'pin'; clase = 'PantallaInventario' },
    @{ k = 'tar'; clase = 'TareaProgramada' },
    @{ k = 'can'; clase = 'CanalPush' },
    @{ k = 'gat'; clase = 'GestorAvisosTalla' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'inv'; clase = 'GestorInventario' },
    @{ k = 'gno'; clase = 'GestorNotificaciones' },
    @{ k = 'gpu'; clase = 'GestorPush' },
    @{ k = 'bit'; clase = 'BitacoraMiddleware' },
    @{ k = 'avt'; clase = 'AvisoTalla' },
    @{ k = 'var'; clase = 'VarianteProducto' },
    @{ k = 'exi'; clase = 'Existencia' },
    @{ k = 'suc'; clase = 'Sucursal' },
    @{ k = 'cli'; clase = 'Cliente' },
    @{ k = 'not'; clase = 'Notificacion' },
    @{ k = 'asi'; clase = 'AsientoBitacora' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1" },
    @{ t='msg'; o='cl';  d='pfi'; n='1: elegirTalla(talla)' },
    @{ t='msg'; o='cl';  d='pfi'; n='1.1: elegirColor(color)' },
    @{ t='msg'; o='cl';  d='pfi'; n='1.2: pedirAviso()' },
    @{ t='msg'; o='pfi'; d='gat'; n='1.3: suscribir(variante)' },
    @{ t='msg'; o='gat'; d='aut'; n='1.4: autorizar("CLIENTE")' },
    @{ t='msg'; o='gat'; d='cli'; n='1.5: clienteDeUsuario(usuario)' },
    @{ t='msg'; o='cli'; d='gat'; n='1.5.1: int'; ret=$true },
    @{ t='msg'; o='gat'; d='var'; n='1.6: varianteOfrecible(variante)' },
    @{ t='msg'; o='var'; d='gat'; n='1.6.1: VarianteProducto | None'; ret=$true },
    @{ t='msg'; o='gat'; d='avt'; n='1.7: pendienteDe(cliente, variante)' },
    @{ t='msg'; o='avt'; d='gat'; n='1.7.1: AvisoTalla | None'; ret=$true },
    # avisos_talla/service.py:169
    @{ t='opt'; g='no lo había pedido antes' },
    @{ t='msg'; o='gat'; d='exi'; n='1.8: totalDisponible(variante)' },
    @{ t='msg'; o='exi'; d='gat'; n='1.8.1: int'; ret=$true },
    @{ t='msg'; o='gat'; d='avt'; n='1.9: crear(cliente, variante)' },
    @{ t='fin' },
    @{ t='msg'; o='gat'; d='bit'; n='1.10: registrar(peticion)' },
    @{ t='msg'; o='bit'; d='asi'; n='1.11: agregar(accion, usuario, entidad)' },
    @{ t='msg'; o='gat'; d='pfi'; n='1.12: avisoRegistrado(aviso)' },
    @{ t='nota'; txt = "FLUJO 2" },
    @{ t='msg'; o='enc'; d='pin'; n='2: registrarIngreso(datos)' },
    @{ t='msg'; o='pin'; d='inv'; n='2.1: registrarIngreso(datos)' },
    @{ t='msg'; o='inv'; d='exi'; n='2.2: sumarDisponible(cantidad)' },
    # inventario/service.py:308
    @{ t='opt'; g='entraron unidades' },
    @{ t='msg'; o='inv'; d='gat'; n='2.3: avisarSiVolvio(existencia, cantidad)' },
    @{ t='msg'; o='gat'; d='avt'; n='2.4: hayPendientes(variante)' },
    @{ t='msg'; o='avt'; d='gat'; n='2.4.1: int | None'; ret=$true },
    @{ t='msg'; o='gat'; d='suc'; n='2.5: estaActiva(sucursal)' },
    @{ t='msg'; o='suc'; d='gat'; n='2.5.1: bool'; ret=$true },
    @{ t='msg'; o='gat'; d='exi'; n='2.6: totalDisponible(variante)' },
    @{ t='msg'; o='exi'; d='gat'; n='2.6.1: int'; ret=$true },
    @{ t='msg'; o='gat'; d='avt'; n='2.7: pendientesParaActualizar(variante)' },
    @{ t='msg'; o='avt'; d='gat'; n='2.7.1: list[AvisoTalla]'; ret=$true },
    # avisos_talla/service.py:358
    @{ t='loop'; g='por cada aviso pendiente' },
    @{ t='msg'; o='gat'; d='gno'; n='2.8: notificar(cliente, "STOCK_DISPONIBLE")' },
    @{ t='msg'; o='gno'; d='not'; n='2.9: crear(aviso)' },
    @{ t='msg'; o='not'; d='gno'; n='2.9.1: Notificacion'; ret=$true },
    @{ t='msg'; o='gat'; d='avt'; n='2.10: marcarNotificado(ahora, notificacion)' },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='msg'; o='sis'; d='tar'; n='2.11: ejecutarVuelta()' },
    @{ t='msg'; o='tar'; d='gpu'; n='2.12: despachar()' },
    @{ t='msg'; o='gpu'; d='not'; n='2.13: tomarPendientePush()' },
    @{ t='msg'; o='not'; d='gpu'; n='2.13.1: Notificacion | None'; ret=$true },
    @{ t='msg'; o='gpu'; d='can'; n='2.14: enviar(destino, aviso)' },
    @{ t='nota'; txt = "FLUJO 3" },
    # avisos_talla/service.py:169-171
    @{ t='alt' },
    @{ t='op'; g='ya tenía un aviso pendiente' },
    @{ t='msg'; o='gat'; d='pfi'; n='3: avisoRegistrado(avisoExistente)' },
    @{ t='op'; g='la talla ya tiene unidades' },
    @{ t='msg'; o='gat'; d='pfi'; n='3.1: yaHayUnidades() -> 409' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 4" },
    @{ t='msg'; o='cl';  d='pma'; n='4: cancelar(aviso)' },
    @{ t='msg'; o='pma'; d='gat'; n='4.1: cancelar(aviso)' },
    @{ t='msg'; o='gat'; d='avt'; n='4.2: pendientePropio(aviso, cliente)' },
    @{ t='msg'; o='avt'; d='gat'; n='4.2.1: AvisoTalla | None'; ret=$true },
    @{ t='msg'; o='gat'; d='avt'; n='4.3: borrar()' },
    @{ t='msg'; o='gat'; d='pma'; n='4.4: avisoCancelado()' },
    @{ t='nota'; txt = "FLUJO 5" },
    @{ t='msg'; o='enc'; d='pte'; n='5: abrirTallasEsperadas()' },
    @{ t='msg'; o='adm'; d='pte'; n='5.1: abrirTallasEsperadas()' },
    @{ t='msg'; o='pte'; d='gat'; n='5.2: demanda()' },
    @{ t='msg'; o='gat'; d='aut'; n='5.3: autorizar("ENCARGADO", "ADMINISTRADOR")' },
    @{ t='msg'; o='gat'; d='avt'; n='5.4: pendientesPorVariante()' },
    @{ t='msg'; o='avt'; d='gat'; n='5.4.1: list[Row]'; ret=$true },
    @{ t='msg'; o='gat'; d='var'; n='5.5: detalleDeVariantes(ids)' },
    @{ t='msg'; o='var'; d='gat'; n='5.5.1: dict[int, dict]'; ret=$true },
    @{ t='msg'; o='gat'; d='pte'; n='5.6: mostrarDemanda(filas)' }
  )
},

# ---------------------------------------------------------------- CU-45 --
# analitica/anomalias.py:142 la lista por comprensión que explica cada fila marcada (loop);
# analitica/service.py:332 'if len(devs) >= MIN_DEVOLUCIONES' (opt); analitica/router.py:38
# requiere_funcion("analitica_ml") -> 403 plan_limit (break); service.py:321 el raise de menos de
# 20 turnos -> 409 (break). El flujo 5 es el else de :339 (no corta: solo deja el mensaje).
@{
  cu = 'CU-45'; nombre = '3.3 CU-45 Detectar anomalías en caja y devoluciones'
  lineas = @(
    @{ k = 'adm'; actor = 'Administrador de la empresa' },
    @{ k = 'pan'; clase = 'PantallaAnomalias' },
    @{ k = 'gan'; clase = 'GestorAnalitica' },
    @{ k = 'det'; clase = 'DetectorAnomalias' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'vpl'; clase = 'VerificadorPlan' },
    @{ k = 'bit'; clase = 'BitacoraMiddleware' },
    @{ k = 'tur'; clase = 'TurnoCaja' },
    @{ k = 'ven'; clase = 'Venta' },
    @{ k = 'dev'; clase = 'Devolucion' },
    @{ k = 'usu'; clase = 'Usuario' },
    @{ k = 'mod'; clase = 'ModeloAnalitica' },
    @{ k = 'asi'; clase = 'AsientoBitacora' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1" },
    @{ t='msg'; o='adm'; d='pan'; n='1: buscarAnomalias()' },
    @{ t='msg'; o='pan'; d='gan'; n='1.1: entrenarAnomalias(semilla)' },
    @{ t='msg'; o='gan'; d='aut'; n='1.2: autorizar("ADMINISTRADOR")' },
    @{ t='msg'; o='gan'; d='vpl'; n='1.3: verificar(empresa, "analitica_ml")' },
    @{ t='msg'; o='gan'; d='tur'; n='1.4: turnosCerrados(desde)' },
    @{ t='msg'; o='tur'; d='gan'; n='1.4.1: list[Row]'; ret=$true },
    @{ t='msg'; o='gan'; d='mod'; n='1.5: ultimo("ANOMALIAS")' },
    @{ t='msg'; o='mod'; d='gan'; n='1.5.1: ModeloAnalitica | None'; ret=$true },
    @{ t='msg'; o='gan'; d='det'; n='1.6: detectar(matrizTurnos, variablesTurno, semilla)' },
    # analitica/anomalias.py:142
    @{ t='loop'; g='por cada turno marcado como anómalo' },
    @{ t='msg'; o='det'; d='det'; n='1.7: explicar(fila, matriz, variables)' },
    @{ t='fin' },
    @{ t='msg'; o='gan'; d='dev'; n='1.8: devolucionesRecientes(desde)' },
    @{ t='msg'; o='dev'; d='gan'; n='1.8.1: list[Row]'; ret=$true },
    # analitica/service.py:332
    @{ t='opt'; g='hay al menos 15 devoluciones' },
    @{ t='msg'; o='gan'; d='ven'; n='1.9: ventasPorCajero(desde)' },
    @{ t='msg'; o='ven'; d='gan'; n='1.9.1: dict[int, int]'; ret=$true },
    @{ t='msg'; o='gan'; d='det'; n='1.10: detectar(matrizDevoluciones, variablesDevolucion, semilla)' },
    @{ t='msg'; o='det'; d='gan'; n='1.10.1: Detectado'; ret=$true },
    @{ t='fin' },
    @{ t='msg'; o='gan'; d='mod'; n='1.11: guardar(modelo, "ANOMALIAS")' },
    @{ t='msg'; o='gan'; d='bit'; n='1.12: registrar(peticion)' },
    @{ t='msg'; o='bit'; d='asi'; n='1.13: agregar(accion, usuario, entidad)' },
    @{ t='msg'; o='gan'; d='pan'; n='1.14: mostrarAnomalias(turnos, devoluciones)' },
    @{ t='nota'; txt = "FLUJO 2" },
    @{ t='msg'; o='adm'; d='pan'; n='2: marcarRevisada(grupo, anomalia)' },
    @{ t='msg'; o='pan'; d='gan'; n='2.1: marcarRevisada(grupo, id)' },
    @{ t='msg'; o='gan'; d='mod'; n='2.2: ultimo("ANOMALIAS")' },
    @{ t='msg'; o='mod'; d='gan'; n='2.2.1: ModeloAnalitica | None'; ret=$true },
    @{ t='msg'; o='gan'; d='usu'; n='2.3: nombreDe(usuario)' },
    @{ t='msg'; o='usu'; d='gan'; n='2.3.1: Usuario | None'; ret=$true },
    @{ t='msg'; o='gan'; d='mod'; n='2.4: actualizarResultado(revision)' },
    @{ t='msg'; o='gan'; d='bit'; n='2.5: registrar(peticion)' },
    @{ t='msg'; o='gan'; d='pan'; n='2.6: mostrarAnomalias(turnos, devoluciones)' },
    @{ t='nota'; txt = "FLUJO 3" },
    # analitica/router.py:38
    @{ t='break'; g='el plan no incluye analitica_ml' },
    @{ t='msg'; o='vpl'; d='gan'; n='3: rechazarPorPlan("plan_limit") -> 403' },
    @{ t='msg'; o='gan'; d='pan'; n='3.1: mostrarCandado()' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 4" },
    # analitica/service.py:321
    @{ t='break'; g='hay menos de 20 turnos cerrados' },
    @{ t='msg'; o='gan'; d='pan'; n='4: faltanTurnos(minimo, hay) -> 409' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 5" },
    @{ t='msg'; o='gan'; d='pan'; n='5: faltanDevoluciones(minimo, hay)' }
  )
}
)
