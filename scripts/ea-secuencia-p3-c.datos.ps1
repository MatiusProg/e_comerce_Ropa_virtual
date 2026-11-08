# Guiones del 3.3, CU-31 a CU-35 (grupo c). Los dibuja scripts/ea-secuencia-p3.ps1.
# Robustez: scripts/p3_datos_c.py (ROBUSTEZ). Código: backend/app/modules/catalogo/ofertas_*.py,
# catalogo/promociones_service.py, core/tareas.py, traspasos/*.py y notificaciones/service.py.
$CASOS_P3 = @(
# ---- CU-31 ---- catalogo/ofertas_service.py: editar_mayorista (:145) cambia la cantidad y el
# precio solo si vienen (:152, :160) -> opt; crear_mayorista (:125) rechaza con dos raise
# excluyentes: escalón repetido (:129, 409) y precio que no es menor (_validar_precio :117, 422) -> alt.
@{
  cu = 'CU-31'; nombre = '3.3 CU-31 Gestionar ofertas y precios mayoristas'
  lineas = @(
    @{ k = 'adm'; actor = 'Administrador de la empresa' },
    @{ k = 'pof'; clase = 'PantallaOfertas' },
    @{ k = 'ppr'; clase = 'PantallaPromociones' },
    @{ k = 'gof'; clase = 'GestorOfertas' },
    @{ k = 'gpr'; clase = 'GestorPromociones' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'bit'; clase = 'BitacoraMiddleware' },
    @{ k = 'pma'; clase = 'PrecioMayorista' },
    @{ k = 'pro'; clase = 'Producto' },
    @{ k = 'var'; clase = 'VarianteProducto' },
    @{ k = 'prm'; clase = 'Promocion' },
    @{ k = 'asi'; clase = 'AsientoBitacora' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1" },
    @{ t='msg'; o='adm'; d='pof'; n='1: abrirOfertas()' },
    @{ t='msg'; o='pof'; d='gof'; n='1.1: listarMayoristas(busqueda, pagina, tamano)' },
    @{ t='msg'; o='gof'; d='aut'; n='1.2: autorizar("ADMINISTRADOR")' },
    @{ t='msg'; o='gof'; d='pma'; n='1.3: listarMayoristas(busqueda, pagina, tamano)' },
    @{ t='msg'; o='pma'; d='gof'; n='1.3.1: tuple[int, list[Row]]'; ret=$true },
    @{ t='msg'; o='gof'; d='pof'; n='1.4: mostrarMayoristas(escalones)' },
    @{ t='msg'; o='adm'; d='pof'; n='1.5: elegirProducto(producto)' },
    @{ t='msg'; o='adm'; d='pof'; n='1.6: guardar(cantidadMinima, precioUnitario)' },
    @{ t='msg'; o='pof'; d='gof'; n='1.7: crearMayorista(datos)' },
    @{ t='msg'; o='gof'; d='pro'; n='1.8: producto(idProducto)' },
    @{ t='msg'; o='pro'; d='gof'; n='1.8.1: Producto | None'; ret=$true },
    @{ t='msg'; o='gof'; d='pma'; n='1.9: existeEscalon(idProducto, cantidadMinima)' },
    @{ t='msg'; o='pma'; d='gof'; n='1.9.1: bool'; ret=$true },
    @{ t='msg'; o='gof'; d='var'; n='1.10: precioMinimoDelProducto(idProducto)' },
    @{ t='msg'; o='var'; d='gof'; n='1.10.1: Decimal | None'; ret=$true },
    @{ t='msg'; o='gof'; d='pma'; n='1.11: agregar(escalon)' },
    @{ t='msg'; o='gof'; d='bit'; n='1.12: registrar(peticion)' },
    @{ t='msg'; o='bit'; d='asi'; n='1.13: agregar(accion, usuario, entidad)' },
    @{ t='msg'; o='gof'; d='pof'; n='1.14: confirmar(escalon) -> 201' },
    @{ t='nota'; txt = "FLUJO 2" },
    @{ t='msg'; o='adm'; d='pof'; n='2: editar(escalon)' },
    @{ t='msg'; o='pof'; d='gof'; n='2.1: editarMayorista(id, datos)' },
    # ofertas_service.py:152 y :160
    @{ t='opt'; g='vienen una cantidad mínima o un precio nuevos' },
    @{ t='msg'; o='gof'; d='pma'; n='2.2: guardar(cantidadMinima, precioUnitario)' },
    @{ t='fin' },
    @{ t='msg'; o='adm'; d='pof'; n='2.3: cambiarEstado(escalon, activo)' },
    @{ t='msg'; o='pof'; d='gof'; n='2.4: cambiarEstadoMayorista(id, activo)' },
    @{ t='msg'; o='gof'; d='pma'; n='2.5: cambiarEstado(activo)' },
    @{ t='nota'; txt = "FLUJO 3" },
    # ofertas_service.py:129 (409) y :117 (422)
    @{ t='alt' },
    @{ t='op'; g='ya hay un escalón desde esa cantidad' },
    @{ t='msg'; o='gof'; d='pof'; n='3: escalonRepetido(cantidadMinima) -> 409' },
    @{ t='op'; g='el precio no es menor que la prenda más barata' },
    @{ t='msg'; o='gof'; d='pof'; n='3.1: precioNoEsMenor(precioMinimo) -> 422' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 4" },
    @{ t='msg'; o='adm'; d='ppr'; n='4: nueva(nombre, alcance, objetivo, porcentaje, desde, hasta)' },
    @{ t='msg'; o='ppr'; d='gpr'; n='4.1: crear(datos)' },
    @{ t='msg'; o='gpr'; d='aut'; n='4.2: autorizar("ADMINISTRADOR")' },
    @{ t='msg'; o='gpr'; d='prm'; n='4.3: existeNombre(nombre)' },
    @{ t='msg'; o='prm'; d='gpr'; n='4.3.1: bool'; ret=$true },
    @{ t='msg'; o='gpr'; d='prm'; n='4.4: agregar(promocion)' },
    @{ t='msg'; o='gpr'; d='bit'; n='4.5: registrar(peticion)' },
    @{ t='msg'; o='gpr'; d='ppr'; n='4.6: confirmar(promocion) -> 201' }
  )
},

# ---- CU-32 ---- core/tareas.py:235 recorre las empresas activas (loop) y llama a
# ofertas_service.aplicar (:273). Dentro: el for de _candidatas (:241) mira cada producto
# candidato (loop); if regla.activa (:285) crea las nuevas (opt). La situación de la promoción
# anterior (_candidatas :245-250, aplicar :292) separa la que apagó el administrador de la que
# cerró la regla (alt).
@{
  cu = 'CU-32'; nombre = '3.3 CU-32 Aplicar ofertas de fuera de temporada'
  lineas = @(
    @{ k = 'sis'; actor = 'Sistema' },
    @{ k = 'adm'; actor = 'Administrador de la empresa' },
    @{ k = 'tar'; clase = 'TareaProgramada' },
    @{ k = 'pof'; clase = 'PantallaOfertas' },
    @{ k = 'gof'; clase = 'GestorOfertas' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'bit'; clase = 'BitacoraMiddleware' },
    @{ k = 'reg'; clase = 'ReglaFueraDeTemporada' },
    @{ k = 'pro'; clase = 'Producto' },
    @{ k = 'tem'; clase = 'Temporada' },
    @{ k = 'exi'; clase = 'Existencia' },
    @{ k = 'prm'; clase = 'Promocion' },
    @{ k = 'asi'; clase = 'AsientoBitacora' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1" },
    @{ t='msg'; o='sis'; d='tar'; n='1: correrVuelta()' },
    # tareas.py:235
    @{ t='loop'; g='por cada empresa activa' },
    @{ t='msg'; o='tar'; d='gof'; n='1.1: aplicar(empresa)' },
    @{ t='msg'; o='gof'; d='reg'; n='1.2: regla()' },
    @{ t='msg'; o='reg'; d='gof'; n='1.2.1: ReglaFueraDeTemporada | None'; ret=$true },
    @{ t='msg'; o='gof'; d='gof'; n='1.3: calcularHastaFin(hoy, diasDesdeFin)' },
    @{ t='msg'; o='gof'; d='pro'; n='1.4: candidatasFueraDeTemporada(hastaFin, existenciaMinima)' },
    @{ t='msg'; o='pro'; d='gof'; n='1.4.1: list[Row]'; ret=$true },
    # ofertas_service.py:241
    @{ t='loop'; g='por cada producto candidato' },
    @{ t='msg'; o='gof'; d='tem'; n='1.5: fechaFin(producto)' },
    @{ t='msg'; o='gof'; d='exi'; n='1.6: disponibleEnSucursalesActivas(producto)' },
    @{ t='msg'; o='gof'; d='prm'; n='1.7: automaticaDe(producto)' },
    @{ t='msg'; o='prm'; d='gof'; n='1.7.1: Promocion | None'; ret=$true },
    @{ t='fin' },
    # ofertas_service.py:285-287
    @{ t='opt'; g='la regla está activa y la candidata es nueva' },
    @{ t='msg'; o='gof'; d='prm'; n='1.8: agregar("AUTOMATICA", producto, porcentaje, hoy)' },
    @{ t='fin' },
    @{ t='msg'; o='gof'; d='prm'; n='1.9: automaticasVigentes()' },
    @{ t='msg'; o='prm'; d='gof'; n='1.9.1: list[Promocion]'; ret=$true },
    @{ t='msg'; o='gof'; d='prm'; n='1.10: cerrar(ayer, cerradaPorRegla)' },
    @{ t='msg'; o='gof'; d='tar'; n='1.11: resultado(creadas, cerradas)' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 2" },
    @{ t='msg'; o='gof'; d='gof'; n='2: omitirCreacion()' },
    @{ t='msg'; o='gof'; d='prm'; n='2.1: automaticasVigentes()' },
    @{ t='msg'; o='prm'; d='gof'; n='2.1.1: list[Promocion]'; ret=$true },
    @{ t='msg'; o='gof'; d='prm'; n='2.2: cerrar(ayer, cerradaPorRegla)' },
    @{ t='nota'; txt = "FLUJO 3" },
    @{ t='msg'; o='gof'; d='prm'; n='3: promocion(idPromocion)' },
    # ofertas_service.py:245-250 y :292-297
    @{ t='alt' },
    @{ t='op'; g='la apagó o la cerró el administrador' },
    @{ t='msg'; o='gof'; d='gof'; n='3.1: respetarSiLaApagoElAdministrador()' },
    @{ t='op'; g='la cerró la regla y el producto vuelve a sobrar' },
    @{ t='msg'; o='gof'; d='prm'; n='3.2: reabrir(hoy, porcentaje)' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 4" },
    @{ t='msg'; o='adm'; d='pof'; n='4: guardarRegla(activa, diasDesdeFin, existenciaMinima, porcentaje)' },
    @{ t='msg'; o='pof'; d='gof'; n='4.1: guardarRegla(datos)' },
    @{ t='msg'; o='gof'; d='aut'; n='4.2: autorizar("ADMINISTRADOR")' },
    @{ t='msg'; o='gof'; d='reg'; n='4.3: guardar(regla)' },
    @{ t='msg'; o='adm'; d='pof'; n='4.4: aplicar()' },
    @{ t='msg'; o='pof'; d='gof'; n='4.5: aplicar()' },
    @{ t='msg'; o='gof'; d='bit'; n='4.6: registrar(peticion)' },
    @{ t='msg'; o='bit'; d='asi'; n='4.7: agregar(accion, usuario, ruta)' },
    @{ t='msg'; o='gof'; d='pof'; n='4.8: mostrarAplicacion(creadas, cerradas, candidatas)' }
  )
},

# ---- CU-33 ---- traspasos/service.py:272 solicitar. El aviso a los encargados del origen es el
# for de notificaciones/service.py:333 (loop). La validación de las sucursales y la prenda va en
# try/except y corta con raise (:289-294, break). No alcanza (:299-302) y ya hay uno abierto
# (:303-310) son raise excluyentes, 409 (alt).
@{
  cu = 'CU-33'; nombre = '3.3 CU-33 Solicitar traspaso entre sucursales'
  lineas = @(
    @{ k = 'enc'; actor = 'Encargado de sucursal' },
    @{ k = 'adm'; actor = 'Administrador de la empresa' },
    @{ k = 'pan'; clase = 'PantallaTraspasos' },
    @{ k = 'gtr'; clase = 'GestorTraspasos' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'inv'; clase = 'GestorInventario' },
    @{ k = 'ntf'; clase = 'GestorNotificaciones' },
    @{ k = 'bit'; clase = 'BitacoraMiddleware' },
    @{ k = 'exi'; clase = 'Existencia' },
    @{ k = 'var'; clase = 'VarianteProducto' },
    @{ k = 'suc'; clase = 'Sucursal' },
    @{ k = 'tra'; clase = 'Traspaso' },
    @{ k = 'usu'; clase = 'Usuario' },
    @{ k = 'ntc'; clase = 'Notificacion' },
    @{ k = 'asi'; clase = 'AsientoBitacora' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1" },
    @{ t='msg'; o='enc'; d='pan'; n='1: buscarPrenda(texto)' },
    @{ t='msg'; o='pan'; d='gtr'; n='1.1: prendasPedibles(busqueda)' },
    @{ t='msg'; o='gtr'; d='aut'; n='1.2: autorizar("ENCARGADO")' },
    @{ t='msg'; o='gtr'; d='exi'; n='1.3: prendasEnOtras(busqueda, excluir)' },
    @{ t='msg'; o='exi'; d='gtr'; n='1.3.1: list[Row]'; ret=$true },
    @{ t='msg'; o='gtr'; d='pan'; n='1.4: mostrarPrendas(prendas)' },
    @{ t='msg'; o='enc'; d='pan'; n='1.5: elegirPrenda(prenda)' },
    @{ t='msg'; o='pan'; d='gtr'; n='1.6: origenesPosibles(idVariante)' },
    @{ t='msg'; o='gtr'; d='exi'; n='1.7: origenesPosibles(idVariante, excluir)' },
    @{ t='msg'; o='exi'; d='gtr'; n='1.7.1: list[Row]'; ret=$true },
    @{ t='msg'; o='gtr'; d='pan'; n='1.8: mostrarOrigenes(origenes)' },
    @{ t='msg'; o='enc'; d='pan'; n='1.9: pedir(origen, cantidad, motivo)' },
    @{ t='msg'; o='pan'; d='gtr'; n='1.10: solicitar(datos)' },
    @{ t='msg'; o='gtr'; d='inv'; n='1.11: sucursalActiva(idOrigen, idDestino)' },
    @{ t='msg'; o='inv'; d='suc'; n='1.12: obtenerSucursal(id)' },
    @{ t='msg'; o='suc'; d='inv'; n='1.12.1: Sucursal | None'; ret=$true },
    @{ t='msg'; o='gtr'; d='inv'; n='1.13: variantesValidas([idVariante])' },
    @{ t='msg'; o='inv'; d='var'; n='1.14: obtenerVariantes(ids)' },
    @{ t='msg'; o='var'; d='inv'; n='1.14.1: list[VarianteProducto]'; ret=$true },
    @{ t='msg'; o='gtr'; d='exi'; n='1.15: disponible(idVariante, idOrigen)' },
    @{ t='msg'; o='exi'; d='gtr'; n='1.15.1: int | None'; ret=$true },
    @{ t='msg'; o='gtr'; d='tra'; n='1.16: hayAbierto(idVariante, idOrigen, idDestino)' },
    @{ t='msg'; o='tra'; d='gtr'; n='1.16.1: bool'; ret=$true },
    @{ t='msg'; o='gtr'; d='tra'; n='1.17: agregar("PEDIDO", "SOLICITADO", datos)' },
    @{ t='msg'; o='tra'; d='gtr'; n='1.17.1: Traspaso'; ret=$true },
    @{ t='msg'; o='gtr'; d='ntf'; n='1.18: avisarTraspaso(traspaso, idOrigen, titulo, cuerpo)' },
    @{ t='msg'; o='ntf'; d='usu'; n='1.19: encargadosDe(idOrigen)' },
    @{ t='msg'; o='usu'; d='ntf'; n='1.19.1: list[Usuario]'; ret=$true },
    # notificaciones/service.py:333
    @{ t='loop'; g='por cada encargado del origen' },
    @{ t='msg'; o='ntf'; d='ntc'; n='1.20: crear(destinatario, "TRASPASO", titulo, cuerpo)' },
    @{ t='fin' },
    @{ t='msg'; o='gtr'; d='bit'; n='1.21: registrar(peticion)' },
    @{ t='msg'; o='bit'; d='asi'; n='1.22: agregar(accion, usuario, entidad)' },
    @{ t='msg'; o='gtr'; d='pan'; n='1.23: confirmar(traspaso) -> 201' },
    @{ t='nota'; txt = "FLUJO 2" },
    @{ t='msg'; o='adm'; d='pan'; n='2: ordenar(origen, destino, cantidad, motivo)' },
    @{ t='msg'; o='pan'; d='gtr'; n='2.1: solicitar(datos)' },
    @{ t='msg'; o='gtr'; d='aut'; n='2.2: autorizar("ADMINISTRADOR")' },
    @{ t='msg'; o='gtr'; d='tra'; n='2.3: agregar("ORDEN", "APROBADO", aprobadoPor)' },
    @{ t='msg'; o='tra'; d='gtr'; n='2.3.1: Traspaso'; ret=$true },
    @{ t='msg'; o='gtr'; d='ntf'; n='2.4: avisarTraspaso(traspaso, idOrigen, titulo, cuerpo)' },
    @{ t='nota'; txt = "FLUJO 3" },
    # traspasos/service.py:289-294
    @{ t='break'; g='la sucursal o la prenda está dada de baja' },
    @{ t='msg'; o='inv'; d='gtr'; n='3: sucursalOPrendaInactiva()' },
    @{ t='msg'; o='gtr'; d='pan'; n='3.1: rechazarPedido(motivo) -> 422' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 4" },
    # traspasos/service.py:299-302 y :303-310
    @{ t='alt' },
    @{ t='op'; g='el origen no tiene lo pedido' },
    @{ t='msg'; o='gtr'; d='pan'; n='4: existenciaInsuficiente(disponible, pedido) -> 409' },
    @{ t='op'; g='ya hay un traspaso de esa prenda sin despachar' },
    @{ t='msg'; o='gtr'; d='pan'; n='4.1: traspasoAbierto(origen, destino) -> 409' },
    @{ t='fin' }
  )
},

# ---- CU-34 ---- traspasos/service.py. listar arma cada fila con sus acciones (:236, loop); el
# aviso al destino es el for de notificaciones/service.py:333 (loop). enviar (:422-434) aplica el
# movimiento en try/except con db.rollback (critical). _bloquear (:350-356) llama a _exigir
# (:125-154), que corta con raise y rollback si el paso no le toca o el estado cambió (break).
@{
  cu = 'CU-34'; nombre = '3.3 CU-34 Atender traspaso'
  lineas = @(
    @{ k = 'enc'; actor = 'Encargado de sucursal' },
    @{ k = 'pan'; clase = 'PantallaTraspasos' },
    @{ k = 'gtr'; clase = 'GestorTraspasos' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'inv'; clase = 'GestorInventario' },
    @{ k = 'ntf'; clase = 'GestorNotificaciones' },
    @{ k = 'bit'; clase = 'BitacoraMiddleware' },
    @{ k = 'tra'; clase = 'Traspaso' },
    @{ k = 'exi'; clase = 'Existencia' },
    @{ k = 'mov'; clase = 'MovimientoInventario' },
    @{ k = 'suc'; clase = 'Sucursal' },
    @{ k = 'usu'; clase = 'Usuario' },
    @{ k = 'ntc'; clase = 'Notificacion' },
    @{ k = 'asi'; clase = 'AsientoBitacora' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1" },
    @{ t='msg'; o='enc'; d='pan'; n='1: abrirSeguimiento(bandeja, abiertos)' },
    @{ t='msg'; o='pan'; d='gtr'; n='1.1: listar(bandeja, estado, abiertos, pagina)' },
    @{ t='msg'; o='gtr'; d='aut'; n='1.2: autorizar("ENCARGADO")' },
    @{ t='msg'; o='gtr'; d='tra'; n='1.3: listar(sucursal, bandeja, abiertos)' },
    @{ t='msg'; o='tra'; d='gtr'; n='1.3.1: tuple[int, list[Row]]'; ret=$true },
    # traspasos/service.py:236
    @{ t='loop'; g='por cada traspaso de la página' },
    @{ t='msg'; o='gtr'; d='gtr'; n='1.4: acciones(traspaso, quien)' },
    @{ t='fin' },
    @{ t='msg'; o='gtr'; d='pan'; n='1.5: mostrarTraspasos(traspasos)' },
    @{ t='msg'; o='enc'; d='pan'; n='1.6: aprobar(traspaso, cantidad)' },
    @{ t='msg'; o='pan'; d='gtr'; n='1.7: aprobar(id, cantidad)' },
    @{ t='msg'; o='gtr'; d='tra'; n='1.8: obtener(id, bloquear)' },
    @{ t='msg'; o='tra'; d='gtr'; n='1.8.1: Traspaso | None'; ret=$true },
    @{ t='msg'; o='gtr'; d='exi'; n='1.9: disponible(idVariante, idOrigen)' },
    @{ t='msg'; o='exi'; d='gtr'; n='1.9.1: int | None'; ret=$true },
    @{ t='msg'; o='gtr'; d='tra'; n='1.10: marcarAprobado(cantidad, usuario)' },
    @{ t='msg'; o='enc'; d='pan'; n='1.11: enviar(traspaso)' },
    @{ t='msg'; o='pan'; d='gtr'; n='1.12: enviar(id)' },
    @{ t='msg'; o='gtr'; d='suc'; n='1.13: obtenerSucursal(idOrigen, idDestino)' },
    @{ t='msg'; o='suc'; d='gtr'; n='1.13.1: Sucursal'; ret=$true },
    @{ t='msg'; o='gtr'; d='exi'; n='1.14: obtenerExistencia(idVariante, idOrigen, bloquear)' },
    @{ t='msg'; o='exi'; d='gtr'; n='1.14.1: Existencia | None'; ret=$true },
    @{ t='msg'; o='gtr'; d='inv'; n='1.15: aplicarMovimiento(existencia, "TRANSFERENCIA", -cantidad)' },
    @{ t='msg'; o='inv'; d='exi'; n='1.16: descontar(cantidad)' },
    @{ t='msg'; o='inv'; d='mov'; n='1.17: agregar("TRANSFERENCIA", -cantidad, referencia)' },
    @{ t='msg'; o='gtr'; d='tra'; n='1.18: marcarEnviado(usuario, movimientoSalida)' },
    @{ t='msg'; o='gtr'; d='ntf'; n='1.19: avisarTraspaso(traspaso, idDestino, titulo, cuerpo)' },
    @{ t='msg'; o='ntf'; d='usu'; n='1.20: encargadosDe(sucursal)' },
    @{ t='msg'; o='usu'; d='ntf'; n='1.20.1: list[Usuario]'; ret=$true },
    # notificaciones/service.py:333
    @{ t='loop'; g='por cada encargado del destino' },
    @{ t='msg'; o='ntf'; d='ntc'; n='1.21: crear(destinatario, "TRASPASO", titulo, cuerpo)' },
    @{ t='fin' },
    @{ t='msg'; o='enc'; d='pan'; n='1.22: recibir(traspaso)' },
    @{ t='msg'; o='pan'; d='gtr'; n='1.23: recibir(id)' },
    @{ t='msg'; o='gtr'; d='inv'; n='1.24: existenciaOCrearla(idVariante, idDestino)' },
    @{ t='msg'; o='inv'; d='gtr'; n='1.24.1: Existencia'; ret=$true },
    @{ t='msg'; o='gtr'; d='inv'; n='1.25: aplicarMovimiento(existencia, "TRANSFERENCIA", cantidad)' },
    @{ t='msg'; o='inv'; d='exi'; n='1.26: sumar(cantidad)' },
    @{ t='msg'; o='inv'; d='mov'; n='1.27: agregar("TRANSFERENCIA", cantidad, referencia)' },
    @{ t='msg'; o='gtr'; d='tra'; n='1.28: marcarRecibido(usuario, movimientoEntrada)' },
    @{ t='msg'; o='gtr'; d='bit'; n='1.29: registrar(peticion)' },
    @{ t='msg'; o='bit'; d='asi'; n='1.30: agregar(accion, usuario, entidad)' },
    @{ t='msg'; o='gtr'; d='pan'; n='1.31: confirmar(traspaso)' },
    @{ t='nota'; txt = "FLUJO 2" },
    @{ t='msg'; o='enc'; d='pan'; n='2: rechazar(traspaso, motivo)' },
    @{ t='msg'; o='pan'; d='gtr'; n='2.1: rechazar(id, motivo)' },
    @{ t='msg'; o='gtr'; d='tra'; n='2.2: marcarRechazado(usuario, motivo)' },
    @{ t='msg'; o='gtr'; d='ntf'; n='2.3: avisarTraspaso(traspaso, otraSucursal, titulo, motivo)' },
    @{ t='nota'; txt = "FLUJO 3" },
    # traspasos/service.py:422-434
    @{ t='critical'; g='' },
    @{ t='msg'; o='inv'; d='gtr'; n='3: stockInsuficiente(disponible, solicitado)' },
    @{ t='msg'; o='gtr'; d='gtr'; n='3.1: revertirTransaccion()' },
    @{ t='msg'; o='gtr'; d='pan'; n='3.2: existenciaInsuficiente(disponible, cantidad) -> 409' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 4" },
    # traspasos/service.py:125-154 (_exigir) y :354-356 (rollback)
    @{ t='break'; g='el paso no le toca o el estado ya cambió' },
    @{ t='msg'; o='gtr'; d='pan'; n='4: pasoNoPermitido(estado) -> 403 o 409' },
    @{ t='fin' },
    @{ t='msg'; o='pan'; d='gtr'; n='4.1: listar(bandeja, estado, abiertos, pagina)' },
    @{ t='nota'; txt = "FLUJO 5" },
    @{ t='msg'; o='enc'; d='pan'; n='5: recibirDeVuelta(traspaso)' },
    @{ t='msg'; o='pan'; d='gtr'; n='5.1: devolver(id)' },
    @{ t='msg'; o='gtr'; d='inv'; n='5.2: aplicarMovimiento(existenciaOrigen, "TRANSFERENCIA", cantidad)' },
    @{ t='msg'; o='gtr'; d='tra'; n='5.3: marcarRecibido(usuario, movimientoEntrada)' }
  )
},

# ---- CU-35 ---- traspasos/router.py:58-66 exige requiere_funcion("traspasos_sugeridos"), que
# corta con RechazoDelPlan (plataforma/verificador.py:212, 403 en main.py:166; break).
# traspasos/service.py:523 sugeridos: if variante_ids (:545, opt) y el for por prenda (:565, loop).
@{
  cu = 'CU-35'; nombre = '3.3 CU-35 Consultar traspasos sugeridos'
  lineas = @(
    @{ k = 'adm'; actor = 'Administrador de la empresa' },
    @{ k = 'pan'; clase = 'PantallaTraspasos' },
    @{ k = 'gtr'; clase = 'GestorTraspasos' },
    @{ k = 'aut'; clase = 'GestorAutenticacion' },
    @{ k = 'ver'; clase = 'VerificadorPlan' },
    @{ k = 'bit'; clase = 'BitacoraMiddleware' },
    @{ k = 'pla'; clase = 'Plan' },
    @{ k = 'ven'; clase = 'Venta' },
    @{ k = 'suc'; clase = 'Sucursal' },
    @{ k = 'exi'; clase = 'Existencia' },
    @{ k = 'tra'; clase = 'Traspaso' },
    @{ k = 'var'; clase = 'VarianteProducto' },
    @{ k = 'asi'; clase = 'AsientoBitacora' }
  )
  guion = @(
    @{ t='nota'; txt = "FLUJO 1" },
    @{ t='msg'; o='adm'; d='pan'; n='1: abrirSugeridos()' },
    @{ t='msg'; o='pan'; d='gtr'; n='1.1: sugeridos(dias)' },
    @{ t='msg'; o='gtr'; d='aut'; n='1.2: autorizar("ADMINISTRADOR")' },
    @{ t='msg'; o='gtr'; d='ver'; n='1.3: verificarFuncion(empresa, "traspasos_sugeridos")' },
    @{ t='msg'; o='ver'; d='pla'; n='1.4: incluyeFuncion("traspasos_sugeridos")' },
    @{ t='msg'; o='pla'; d='ver'; n='1.4.1: bool'; ret=$true },
    @{ t='msg'; o='gtr'; d='ven'; n='1.5: vendidasPorSucursal(desde)' },
    @{ t='msg'; o='ven'; d='gtr'; n='1.5.1: list[Row]'; ret=$true },
    # traspasos/service.py:545
    @{ t='opt'; g='alguna prenda se vendió en el período' },
    @{ t='msg'; o='gtr'; d='suc'; n='1.6: sucursalesActivas()' },
    @{ t='msg'; o='suc'; d='gtr'; n='1.6.1: dict[int, str]'; ret=$true },
    @{ t='msg'; o='gtr'; d='exi'; n='1.7: existenciasDe(variantes)' },
    @{ t='msg'; o='exi'; d='gtr'; n='1.7.1: list[Row]'; ret=$true },
    @{ t='msg'; o='gtr'; d='tra'; n='1.8: enTraspaso(variantes)' },
    @{ t='msg'; o='tra'; d='gtr'; n='1.8.1: tuple[dict, dict]'; ret=$true },
    @{ t='msg'; o='gtr'; d='var'; n='1.9: variantes(ids)' },
    @{ t='msg'; o='var'; d='gtr'; n='1.9.1: dict[int, Row]'; ret=$true },
    # traspasos/service.py:565
    @{ t='loop'; g='por cada prenda vendida' },
    @{ t='msg'; o='gtr'; d='gtr'; n='1.10: calcularFaltaYSobra(vendidas, disponible, stockMinimo)' },
    @{ t='msg'; o='gtr'; d='gtr'; n='1.11: repartir(destinos, origenes)' },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='msg'; o='gtr'; d='pan'; n='1.12: mostrarSugerencias(sugerencias)' },
    @{ t='nota'; txt = "FLUJO 2" },
    # plataforma/verificador.py:212
    @{ t='break'; g='el plan no incluye traspasos sugeridos' },
    @{ t='msg'; o='ver'; d='gtr'; n='2: rechazarPorPlan("traspasos_sugeridos")' },
    @{ t='msg'; o='gtr'; d='pan'; n='2.1: funcionNoIncluida(mensaje) -> 403' },
    @{ t='fin' },
    @{ t='nota'; txt = "FLUJO 3" },
    @{ t='msg'; o='adm'; d='pan'; n='3: cambiarDias(dias)' },
    @{ t='msg'; o='pan'; d='gtr'; n='3.1: sugeridos(dias)' },
    @{ t='nota'; txt = "FLUJO 4" },
    @{ t='msg'; o='adm'; d='pan'; n='4: ordenarSugerido(sugerencia)' },
    @{ t='msg'; o='pan'; d='gtr'; n='4.1: solicitar(datos, desdeSugerencia)' },
    @{ t='msg'; o='gtr'; d='tra'; n='4.2: agregar("SUGERIDO", "APROBADO", razon)' },
    @{ t='msg'; o='tra'; d='gtr'; n='4.2.1: Traspaso'; ret=$true },
    @{ t='msg'; o='gtr'; d='bit'; n='4.3: registrar(peticion)' },
    @{ t='msg'; o='bit'; d='asi'; n='4.4: agregar(accion, usuario, entidad)' },
    @{ t='msg'; o='gtr'; d='pan'; n='4.5: confirmar(traspaso) -> 201' }
  )
}
)
