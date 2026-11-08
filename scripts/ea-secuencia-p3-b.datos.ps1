# Guiones del 3.3, CU-26 a CU-30 (grupo b). Los dibuja scripts/ea-secuencia-p3.ps1.
# Salen de la robustez de scripts/p3_datos_b.py (mismos participantes, mismos mensajes, mismo orden)
# y del código de origin/main al 08/11. Los flujos alternativos van después del principal, con su nota.
$CASOS_P3 = @(
# ---- CU-26 ---- notificaciones/service.py:207 for de los encargados (loop);
# core/tareas.py:229 'if not _toca_vuelta' -> return temprano (break, alternativo 4a);
# core/tareas.py:235 for de las empresas activas (loop) y, adentro,
# notificaciones/service.py:512 el while del despacho, de a una con SKIP LOCKED (loop anidado).
# El 3a sale del if/elif de notificar() (service.py:158-163) y el 7a del except ErrorDeEnvio (:527).
@{
  cu = 'CU-26'; nombre = '3.3 CU-26 Notificar eventos por correo según el plan'
  lineas = @(
    @{ k = 'sis'; actor = 'Sistema' },
    @{ k = 'tpr'; clase = 'TareaProgramada' },
    @{ k = 'cor'; clase = 'CanalDeCorreo' },
    @{ k = 'gno'; clase = 'GestorNotificaciones' },
    @{ k = 'gta'; clase = 'GestorTareas' },
    @{ k = 'ver'; clase = 'VerificadorPlan' },
    @{ k = 'grs'; clase = 'GestorReservas' },
    @{ k = 'ntf'; clase = 'Notificacion' },
    @{ k = 'usu'; clase = 'Usuario' },
    @{ k = 'sus'; clase = 'Suscripcion' },
    @{ k = 'pla'; clase = 'Plan' },
    @{ k = 'tar'; clase = 'TareaAutomatica' },
    @{ k = 'emp'; clase = 'Empresa' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1" },
    @{ t='msg'; o='grs'; d='gno'; n='1: avisarReservaEnSucursal(reserva)' },
    @{ t='msg'; o='gno'; d='usu'; n='1.1: encargadosDe(sucursal)' },
    @{ t='msg'; o='usu'; d='gno'; n='1.1.1: list[Usuario]'; ret=$true },
    @{ t='loop'; g='por cada encargado activo de la sucursal' },
    @{ t='msg'; o='gno'; d='ver'; n='1.2: incluye("correo")' },
    @{ t='msg'; o='ver'; d='sus'; n='1.3: vigenteDe(empresa)' },
    @{ t='msg'; o='sus'; d='ver'; n='1.3.1: Suscripcion | None'; ret=$true },
    @{ t='msg'; o='ver'; d='pla'; n='1.4: incluyeFuncion("correo")' },
    @{ t='msg'; o='pla'; d='ver'; n='1.4.1: bool'; ret=$true },
    @{ t='msg'; o='gno'; d='ntf'; n='1.5: crear(destinatario, tipo, titulo, cuerpo, "PENDIENTE")' },
    @{ t='fin' },
    @{ t='msg'; o='sis'; d='tpr'; n='1.6: despertarCada15Minutos()' },
    @{ t='msg'; o='tpr'; d='gta'; n='1.7: correrVuelta()' },
    @{ t='msg'; o='gta'; d='gta'; n='1.8: tomarBloqueoAdvisory()' },
    @{ t='msg'; o='gta'; d='tar'; n='1.9: tocaVuelta(minimo)' },
    @{ t='msg'; o='tar'; d='gta'; n='1.9.1: bool'; ret=$true },
    @{ t='msg'; o='gta'; d='emp'; n='1.10: empresasActivas()' },
    @{ t='msg'; o='emp'; d='gta'; n='1.10.1: list[int]'; ret=$true },
    @{ t='loop'; g='por cada empresa activa' },
    @{ t='msg'; o='gta'; d='gno'; n='1.11: despacharPendientes(empresa)' },
    @{ t='loop'; g='mientras quede una pendiente y no se llegue al tope' },
    @{ t='msg'; o='gno'; d='ntf'; n='1.12: tomarPendienteDeCorreo()' },
    @{ t='msg'; o='ntf'; d='gno'; n='1.12.1: Notificacion | None'; ret=$true },
    @{ t='msg'; o='gno'; d='usu'; n='1.13: obtener(destinatario)' },
    @{ t='msg'; o='usu'; d='gno'; n='1.13.1: Usuario | None'; ret=$true },
    @{ t='msg'; o='gno'; d='gno'; n='1.14: armarMensaje(notificacion, enlace)' },
    @{ t='msg'; o='gno'; d='cor'; n='1.15: enviar(mensaje)' },
    @{ t='msg'; o='gno'; d='ntf'; n='1.16: marcar("ENVIADO", enviadoEn)' },
    @{ t='fin' },
    @{ t='msg'; o='gno'; d='gta'; n='1.11.1: DespachoOut'; ret=$true },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 2" },
    @{ t='msg'; o='ver'; d='gno'; n='2: noIncluye()' },
    @{ t='msg'; o='gno'; d='ntf'; n='2.1: crear(destinatario, tipo, titulo, cuerpo, "OMITIDO", motivo)' },
    @{ t='nota'; txt = "FLUJO 3" },
    @{ t='msg'; o='gta'; d='tar'; n='3: ultimaVuelta()' },
    @{ t='break'; g='la última vuelta fue hace menos de 15 minutos' },
    @{ t='msg'; o='gta'; d='gta'; n='3.1: saltearVuelta()' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 4" },
    @{ t='msg'; o='cor'; d='gno'; n='4: errorDeEnvio(motivo)' },
    @{ t='msg'; o='gno'; d='ntf'; n='4.1: marcar("FALLIDO", motivo)' },
    @{ t='msg'; o='gno'; d='gno'; n='4.2: seguirConLaSiguiente()' }
  )
},

# ---- CU-27 ---- reportes/dinamico.py:433 _valor_de_medida (y el _HECHOS de :509): una sola consulta
# según la medida, el alt de las cuatro; core/dependencies.py:253 requiere_funcion + requiere_cupo ->
# verificador.py:209/:251 raise RechazoDelPlan (break, 3a); dinamico_router.py:129 except
# ErrorDelInterprete -> intérprete por reglas (opt, 5a); dinamico_router.py:135/:140/:148 vuelve con
# _no_entendido antes de ejecutar (break, 6a). El cupo se gasta recién en :152, antes del commit de :153.
@{
  cu = 'CU-27'; nombre = '3.3 CU-27 Generar reporte con IA por texto o voz'
  lineas = @(
    @{ k = 'adm'; actor = 'Administrador de la empresa' },
    @{ k = 'enc'; actor = 'Encargado de sucursal' },
    @{ k = 'pan'; clase = 'PantallaReportesIA' },
    @{ k = 'pia'; clase = 'ProveedorIA' },
    @{ k = 'gri'; clase = 'GestorReportesIA' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'ver'; clase = 'VerificadorPlan' },
    @{ k = 'bit'; clase = 'BitacoraMiddleware' },
    @{ k = 'pla'; clase = 'Plan' },
    @{ k = 'cup'; clase = 'ConsumoCupo' },
    @{ k = 'suc'; clase = 'Sucursal' },
    @{ k = 'ven'; clase = 'Venta' },
    @{ k = 'dev'; clase = 'Devolucion' },
    @{ k = 'exi'; clase = 'Existencia' },
    @{ k = 'rsv'; clase = 'Reserva' },
    @{ k = 'asi'; clase = 'AsientoBitacora' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1" },
    @{ t='msg'; o='adm'; d='pan'; n='1: escribirODictar(pedido)' },
    @{ t='msg'; o='enc'; d='pan'; n='1.1: escribirODictar(pedido)' },
    @{ t='msg'; o='pan'; d='gri'; n='1.2: consultar(texto)' },
    @{ t='msg'; o='gri'; d='aut'; n='1.3: autorizar("ADMINISTRADOR", "ENCARGADO")' },
    @{ t='msg'; o='gri'; d='ver'; n='1.4: verificar("reportes_ia", cupo)' },
    @{ t='msg'; o='ver'; d='pla'; n='1.5: incluyeFuncion("reportes_ia")' },
    @{ t='msg'; o='pla'; d='ver'; n='1.5.1: bool'; ret=$true },
    @{ t='msg'; o='ver'; d='cup'; n='1.6: usoDelMes("reportes_ia")' },
    @{ t='msg'; o='cup'; d='ver'; n='1.6.1: int'; ret=$true },
    @{ t='msg'; o='gri'; d='suc'; n='1.7: paresIdNombre(sucursalForzada)' },
    @{ t='msg'; o='suc'; d='gri'; n='1.7.1: dict[str, str]'; ret=$true },
    @{ t='msg'; o='gri'; d='pia'; n='1.8: interpretarConsulta(texto, vocabulario, hoy)' },
    @{ t='msg'; o='pia'; d='gri'; n='1.9: especificacion(json)' },
    @{ t='msg'; o='gri'; d='gri'; n='1.10: validar(especificacion)' },
    @{ t='alt' },
    @{ t='op'; g='la medida es de ventas' },
    @{ t='msg'; o='gri'; d='ven'; n='1.11: sumarPor(dimensiones, filtros, periodo)' },
    @{ t='msg'; o='ven'; d='gri'; n='1.11.1: list[Row]'; ret=$true },
    @{ t='op'; g='la medida es de devoluciones' },
    @{ t='msg'; o='gri'; d='dev'; n='1.12: sumarPor(dimensiones, filtros, periodo)' },
    @{ t='msg'; o='dev'; d='gri'; n='1.12.1: list[Row]'; ret=$true },
    @{ t='op'; g='la medida es de existencias' },
    @{ t='msg'; o='gri'; d='exi'; n='1.13: sumarPor(dimensiones, filtros)' },
    @{ t='msg'; o='exi'; d='gri'; n='1.13.1: list[Row]'; ret=$true },
    @{ t='op'; g='la medida es de reservas' },
    @{ t='msg'; o='gri'; d='rsv'; n='1.14: contarPor(dimensiones, filtros, periodo)' },
    @{ t='msg'; o='rsv'; d='gri'; n='1.14.1: list[Row]'; ret=$true },
    @{ t='fin' },
    @{ t='msg'; o='gri'; d='gri'; n='1.15: armarGraficoYLectura(filas)' },
    @{ t='msg'; o='gri'; d='ver'; n='1.16: consumirCupo("reportes_ia")' },
    @{ t='msg'; o='ver'; d='cup'; n='1.17: sumarUno(recurso, periodo)' },
    @{ t='msg'; o='cup'; d='ver'; n='1.17.1: int'; ret=$true },
    @{ t='msg'; o='gri'; d='bit'; n='1.18: registrar(peticion)' },
    @{ t='msg'; o='bit'; d='asi'; n='1.19: agregar(accion, usuario, ip)' },
    @{ t='msg'; o='gri'; d='pan'; n='1.20: mostrarReporte(entendido, tabla, grafico, lectura)' },
    @{ t='nota'; txt = "FLUJO 2" },
    @{ t='break'; g='el plan no incluye reportes_ia o ya se usó el cupo del mes' },
    @{ t='msg'; o='ver'; d='gri'; n='2: rechazarPorPlan("plan_limit", limite, uso)' },
    @{ t='msg'; o='gri'; d='pan'; n='2.1: avisarPlan(mensaje)' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 3" },
    @{ t='opt'; g='el modelo no está configurado o no contesta' },
    @{ t='msg'; o='pia'; d='gri'; n='3: errorDelInterprete()' },
    @{ t='msg'; o='gri'; d='gri'; n='3.1: interpretarPorReglas(texto, vocabulario, hoy)' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 4" },
    @{ t='break'; g='no se entendió, es ambiguo o no pasa la lista blanca' },
    @{ t='msg'; o='gri'; d='pan'; n='4: noEntendido(motivo, ejemplos)' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 5" },
    @{ t='msg'; o='adm'; d='pan'; n='5: exportar(formato)' },
    @{ t='msg'; o='pan'; d='gri'; n='5.1: exportar(especificacion, formato)' },
    @{ t='msg'; o='gri'; d='gri'; n='5.2: validarYEjecutar(especificacion)' },
    @{ t='msg'; o='gri'; d='pan'; n='5.3: entregarArchivo(pdfOXlsx)' }
  )
},

# ---- CU-28 ---- reportes/reportes_router.py:209 el catálogo recorre los reportes y resuelve las
# opciones de cada filtro (loop); reportes_router.py:145 'if pedido is None' -> solo con el pedido
# entendido se muestra lo entendido (opt, 3a); reportes_router.py:238 'if usuario.rol != ADMINISTRADOR'
# (opt, 5a) con el raise 409 de :239 si no tiene sucursal (break anidado).
@{
  cu = 'CU-28'; nombre = '3.3 CU-28 Generar reportes de gestión con devoluciones'
  lineas = @(
    @{ k = 'adm'; actor = 'Administrador de la empresa' },
    @{ k = 'enc'; actor = 'Encargado de sucursal' },
    @{ k = 'pan'; clase = 'PantallaReportes' },
    @{ k = 'pia'; clase = 'ProveedorIA' },
    @{ k = 'gre'; clase = 'GestorReportes' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'ver'; clase = 'VerificadorPlan' },
    @{ k = 'bit'; clase = 'BitacoraMiddleware' },
    @{ k = 'dev'; clase = 'Devolucion' },
    @{ k = 'ddv'; clase = 'DetalleDevolucion' },
    @{ k = 'dvt'; clase = 'DetalleVenta' },
    @{ k = 'suc'; clase = 'Sucursal' },
    @{ k = 'asi'; clase = 'AsientoBitacora' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1" },
    @{ t='msg'; o='adm'; d='pan'; n='1: abrirReportes()' },
    @{ t='msg'; o='enc'; d='pan'; n='1.1: abrirReportes()' },
    @{ t='msg'; o='pan'; d='gre'; n='1.2: catalogo()' },
    @{ t='msg'; o='gre'; d='aut'; n='1.3: autorizar("ADMINISTRADOR", "ENCARGADO")' },
    @{ t='loop'; g='por cada reporte y cada filtro que declara' },
    @{ t='msg'; o='gre'; d='suc'; n='1.4: opcionesDeSucursal()' },
    @{ t='msg'; o='suc'; d='gre'; n='1.4.1: list[tuple[str, str]]'; ret=$true },
    @{ t='fin' },
    @{ t='msg'; o='gre'; d='pan'; n='1.5: mostrarCatalogo(reportes, filtros)' },
    @{ t='msg'; o='adm'; d='pan'; n='1.6: descargar("devoluciones", formato, periodo, filtros)' },
    @{ t='msg'; o='enc'; d='pan'; n='1.7: descargar("devoluciones", formato, periodo, filtros)' },
    @{ t='msg'; o='pan'; d='gre'; n='1.8: descargar(tipo, formato, desde, hasta, filtros)' },
    @{ t='msg'; o='gre'; d='dev'; n='1.9: devoluciones(desde, hasta, sucursal, tipo)' },
    @{ t='msg'; o='dev'; d='gre'; n='1.9.1: list[tuple]'; ret=$true },
    @{ t='msg'; o='gre'; d='ddv'; n='1.10: lineasDevueltas(devolucion)' },
    @{ t='msg'; o='gre'; d='dvt'; n='1.11: precioCongelado(venta, variante)' },
    @{ t='msg'; o='gre'; d='gre'; n='1.12: totales(cantidad, valor)' },
    @{ t='msg'; o='gre'; d='gre'; n='1.13: aPdfOExcel(tabla)' },
    @{ t='msg'; o='gre'; d='bit'; n='1.14: registrar(peticion)' },
    @{ t='msg'; o='bit'; d='asi'; n='1.15: agregar("EXPORTAR", usuario, ip)' },
    @{ t='msg'; o='gre'; d='pan'; n='1.16: entregarArchivo(nombre)' },
    @{ t='nota'; txt = "FLUJO 2" },
    @{ t='msg'; o='adm'; d='pan'; n='2: hablar()' },
    @{ t='msg'; o='pan'; d='gre'; n='2.1: interpretarVoz(texto)' },
    @{ t='msg'; o='gre'; d='ver'; n='2.2: verificar("reportes_ia", cupo)' },
    @{ t='msg'; o='gre'; d='pia'; n='2.3: interpretar(texto, reportes, hoy)' },
    @{ t='msg'; o='pia'; d='gre'; n='2.3.1: Pedido | None'; ret=$true },
    @{ t='opt'; g='el modelo entendió qué reporte se pidió' },
    @{ t='msg'; o='gre'; d='pan'; n='2.4: mostrarLoEntendido(resumen, url)' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 3" },
    @{ t='opt'; g='quien descarga es el encargado' },
    @{ t='msg'; o='gre'; d='gre'; n='3: forzarSucursal(usuario.sucursal)' },
    @{ t='break'; g='no tiene sucursal asignada' },
    @{ t='msg'; o='gre'; d='pan'; n='3.1: sinSucursalAsignada()' },
    @{ t='fin' },
    @{ t='fin' }
  )
},

# ---- CU-29 ---- analitica/modelos.py:125 for de los productos que arma las filas con rezago y corte
# temporal (loop); modelos.py:291 for de k en K_CANDIDATOS, se queda con la mejor silueta (loop);
# core/dependencies.py:253 requiere_funcion -> verificador.py:211 raise RechazoDelPlan (break, 2a).
# Un solo commit al final (analitica/service.py:115).
@{
  cu = 'CU-29'; nombre = '3.3 CU-29 Entrenar los modelos de analítica'
  lineas = @(
    @{ k = 'adm'; actor = 'Administrador de la empresa' },
    @{ k = 'pan'; clase = 'PantallaAnalitica' },
    @{ k = 'gan'; clase = 'GestorAnalitica' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'ver'; clase = 'VerificadorPlan' },
    @{ k = 'bit'; clase = 'BitacoraMiddleware' },
    @{ k = 'pla'; clase = 'Plan' },
    @{ k = 'pro'; clase = 'Producto' },
    @{ k = 'ven'; clase = 'Venta' },
    @{ k = 'mod'; clase = 'ModeloAnalitica' },
    @{ k = 'asi'; clase = 'AsientoBitacora' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1" },
    @{ t='msg'; o='adm'; d='pan'; n='1: entrenar()' },
    @{ t='msg'; o='pan'; d='gan'; n='1.1: entrenar(semilla)' },
    @{ t='msg'; o='gan'; d='aut'; n='1.2: autorizar("ADMINISTRADOR")' },
    @{ t='msg'; o='gan'; d='ver'; n='1.3: verificarFuncion("analitica_ml")' },
    @{ t='msg'; o='ver'; d='pla'; n='1.4: incluyeFuncion("analitica_ml")' },
    @{ t='msg'; o='pla'; d='ver'; n='1.4.1: bool'; ret=$true },
    @{ t='msg'; o='gan'; d='pro'; n='1.5: productosActivos()' },
    @{ t='msg'; o='pro'; d='gan'; n='1.5.1: list[Row]'; ret=$true },
    @{ t='msg'; o='gan'; d='ven'; n='1.6: ventasSemanales(desde)' },
    @{ t='msg'; o='ven'; d='gan'; n='1.6.1: list[Row]'; ret=$true },
    @{ t='msg'; o='gan'; d='gan'; n='1.7: demandaSintetica(productos, semanas, semilla)' },
    @{ t='loop'; g='por cada producto y cada semana con rezago' },
    @{ t='msg'; o='gan'; d='gan'; n='1.8: entrenarDemanda(GradientBoosting, corteTemporal)' },
    @{ t='fin' },
    @{ t='msg'; o='gan'; d='ven'; n='1.9: rfmDeClientes()' },
    @{ t='msg'; o='ven'; d='gan'; n='1.9.1: list[Row]'; ret=$true },
    @{ t='loop'; g='por cada k de 2 a 6' },
    @{ t='msg'; o='gan'; d='gan'; n='1.10: entrenarSegmentos(KMeans, k 2 a 6, silueta)' },
    @{ t='fin' },
    @{ t='msg'; o='gan'; d='mod'; n='1.11: guardar(entrenamiento)' },
    @{ t='msg'; o='mod'; d='gan'; n='1.11.1: ModeloAnalitica'; ret=$true },
    @{ t='msg'; o='gan'; d='mod'; n='1.12: borrarViejos(tipo, conservar 5)' },
    @{ t='msg'; o='gan'; d='bit'; n='1.13: registrar(peticion)' },
    @{ t='msg'; o='bit'; d='asi'; n='1.14: agregar(accion, usuario, ip)' },
    @{ t='msg'; o='gan'; d='pan'; n='1.15: mostrarDashboard(resumen)' },
    @{ t='nota'; txt = "FLUJO 2" },
    @{ t='break'; g='el plan no incluye analitica_ml' },
    @{ t='msg'; o='ver'; d='gan'; n='2: rechazarPorPlan("plan_limit")' },
    @{ t='msg'; o='gan'; d='pan'; n='2.1: mostrarCandado(mensaje)' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 3" },
    @{ t='msg'; o='gan'; d='gan'; n='3: completarConSinteticos(filasReales)' }
  )
},

# ---- CU-30 ---- core/dependencies.py:253 requiere_funcion -> verificador.py:211 raise RechazoDelPlan
# (break, 2a); analitica/service.py:158 'if modelo is None' -> raise ErrorDeAnalitica 409 (y :180 en el
# reporte): todavía no se entrenó (break, 3a). El reporte en PDF o Excel sale de router.py:120/:128.
@{
  cu = 'CU-30'; nombre = '3.3 CU-30 Consultar el dashboard analítico'
  lineas = @(
    @{ k = 'adm'; actor = 'Administrador de la empresa' },
    @{ k = 'pan'; clase = 'PantallaAnalitica' },
    @{ k = 'gan'; clase = 'GestorAnalitica' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'ver'; clase = 'VerificadorPlan' },
    @{ k = 'pla'; clase = 'Plan' },
    @{ k = 'mod'; clase = 'ModeloAnalitica' },
    @{ k = 'ven'; clase = 'Venta' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1" },
    @{ t='msg'; o='adm'; d='pan'; n='1: abrirAnalitica()' },
    @{ t='msg'; o='pan'; d='gan'; n='1.1: resumen()' },
    @{ t='msg'; o='gan'; d='aut'; n='1.2: autorizar("ADMINISTRADOR")' },
    @{ t='msg'; o='gan'; d='ver'; n='1.3: verificarFuncion("analitica_ml")' },
    @{ t='msg'; o='ver'; d='pla'; n='1.4: incluyeFuncion("analitica_ml")' },
    @{ t='msg'; o='pla'; d='ver'; n='1.4.1: bool'; ret=$true },
    @{ t='msg'; o='gan'; d='mod'; n='1.5: ultimo("DEMANDA")' },
    @{ t='msg'; o='mod'; d='gan'; n='1.5.1: ModeloAnalitica | None'; ret=$true },
    @{ t='msg'; o='gan'; d='mod'; n='1.6: ultimo("SEGMENTOS")' },
    @{ t='msg'; o='mod'; d='gan'; n='1.6.1: ModeloAnalitica | None'; ret=$true },
    @{ t='msg'; o='gan'; d='pan'; n='1.7: mostrarMetricasPrediccionesYSegmentos(resumen)' },
    @{ t='msg'; o='pan'; d='gan'; n='1.8: clientesPorSegmento()' },
    @{ t='msg'; o='gan'; d='ven'; n='1.9: rfmDeClientes()' },
    @{ t='msg'; o='ven'; d='gan'; n='1.9.1: list[Row]'; ret=$true },
    @{ t='msg'; o='gan'; d='gan'; n='1.10: clasificar(modeloGuardado, rfm)' },
    @{ t='msg'; o='gan'; d='pan'; n='1.11: mostrarClientes(segmentos)' },
    @{ t='nota'; txt = "FLUJO 2" },
    @{ t='break'; g='el plan no incluye analitica_ml' },
    @{ t='msg'; o='ver'; d='gan'; n='2: rechazarPorPlan("plan_limit")' },
    @{ t='msg'; o='gan'; d='pan'; n='2.1: mostrarCandado(mensaje)' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 3" },
    @{ t='break'; g='no hay un modelo de segmentos guardado' },
    @{ t='msg'; o='gan'; d='pan'; n='3: invitarAEntrenar()' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 4" },
    @{ t='msg'; o='adm'; d='pan'; n='4: descargar(formato)' },
    @{ t='msg'; o='pan'; d='gan'; n='4.1: reporte(formato)' },
    @{ t='msg'; o='gan'; d='gan'; n='4.2: aPdfOExcel(tabla)' },
    @{ t='msg'; o='gan'; d='pan'; n='4.3: entregarArchivo(nombre)' }
  )
}
)
