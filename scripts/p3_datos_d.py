# Datos de la 3ra presentación, grupo d: CU-36 a CU-41, sacados del código (08/11).
#   CASOS (2.5), ROBUSTEZ y DESCRIPCION (3.2), CLASES y CUS (3.4) y ESPEC (fichas del 2.6).
# Mismos formatos que scripts/p2_datos.py y scripts/p2_clases_datos.py. Módulo autónomo.
#
# Lo verificado en el código:
#   - CU-36: features/admin/probador/probador-admin.ts -> /catalogo/probador/... (vestidor_virtual/probador_*).
#   - CU-37 y CU-38: están en la WEB (features/tienda/probador/probador.ts, ruta /tienda/producto/:id/probador,
#     guardas sesionGuard + rolGuard('CLIENTE')). El 2.5 dice «Móvil», pero el móvil NO llama a /vestidor/sesiones
#     ni a /vestidor/productos/{id}/prueba: solo usa el vestidor RA del 1er parcial (/vestidor/probador y
#     /vestidor/probar, data/repositorios/repositorio_vestidor.dart). La pantalla móvil con ML Kit quedó pendiente
#     (docs/entregas/Presentacion-3/cu-36-38-probador.md, sección «Pendiente»).
#   - CU-39 y CU-40: features/admin/datos/datos.ts («Datos y copias» en el menú) -> datos/router.py.
#   - CU-41: features/admin/roles/roles.ts -> roles/router.py + app/core/permisos.py.
#
# Uso: python -X utf8 scripts/p3_datos_d.py   (solo valida; no escribe nada)

# ------------------------------------------------------------------ 2.5 ---
CASOS = [
    # (id, nombre, actores, incluye, notas[, extiende])
    # Sin el «(propio)» de la tabla del 2.5, como el CU-11 y el CU-12 de p2_datos.py: va en las notas.
    ('CU-36', 'Preparar prenda para el probador', ['Administrador de la empresa'], [],
     'Aporte propio. Reemplaza al CU-11 del primer parcial en lo del vestidor. Marca hombros y ruedo sobre el PNG '
     'sin fondo y carga busto, cintura, cadera y largo por talla. RF-43.'),
    ('CU-37', 'Probarse una prenda con su talla real', ['Cliente'], [],
     'Aporte propio. Evoluciona el CU-21 del primer parcial. En la web: la prenda se dibuja con los cm de la talla '
     'sobre la foto del cliente, que no sale del navegador; el servidor calcula el ajuste. RF-44.'),
    ('CU-38', 'Generar foto realista de la prueba', ['Cliente'], ['CU-05'],
     'Aporte propio. Foto con IA a partir de la composición del CU-37; función foto_ia y cupo mensual de la tienda, '
     'que se descuenta solo si la foto salió. RF-45, RN-11.',
     ['CU-37']),
    ('CU-39', 'Exportar los datos de la empresa', ['Administrador de la empresa'], ['CU-05'],
     'Aporte propio. Excel con una hoja por tabla o ZIP con un CSV por tabla; función exportar_datos del plan. '
     'RF-48.'),
    ('CU-40', 'Gestionar copias de seguridad de la empresa', ['Administrador de la empresa', 'Sistema'], ['CU-05'],
     'Aporte propio. Copia manual firmada que se descarga, automática cifrada con retención, restauración en una '
     'transacción e historial. RF-60 a RF-63, RN-18, RN-19.'),
    ('CU-41', 'Gestionar roles y permisos de la empresa', ['Administrador de la empresa'], ['CU-05'],
     'Pedido en clase. Roles propios que parten de un rol base y solo le quitan permisos; los que dependen del plan '
     'piden su función. RF-64, RN-22.'),
]

# ------------------------------------------------------------------ 3.2 ---
AE, CL, SI = 'A:Administrador de la empresa', 'A:Cliente', 'A:Sistema'
BM, AB = 'BitacoraMiddleware', 'AsientoBitacora'
F3 = 'agregar(accion, usuario, entidad)'

ROBUSTEZ = [
    dict(cu='CU-36', n='Preparar prenda para el probador', a=['Administrador de la empresa'],
         f=['PantallaPrepararPrenda'], c=['GestorProbador', 'GestorAutenticacion', BM],
         e=['Producto', 'ImagenProducto', 'PuntoPrenda', 'Talla', 'MedidaTalla', AB],
         grupos=['flujo principal: marcar los puntos y cargar las medidas',
                 'alternativo 5a: la imagen no es de vestidor', 'alternativo 5b: puntos incoherentes',
                 'alternativo 7a: medidas inválidas'],
         m=[(1, AE, 'PantallaPrepararPrenda', 'abrirProbador()'),
            (1, 'PantallaPrepararPrenda', 'GestorProbador', 'productos()'),
            (1, 'GestorProbador', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR")'),
            (1, 'GestorProbador', 'Producto', 'productosConVestidor()'),
            (1, 'GestorProbador', 'GestorProbador', 'calcularAvance(imagenes, tallas)'),
            (1, 'GestorProbador', 'PantallaPrepararPrenda', 'mostrarAvance(productos)'),
            (1, AE, 'PantallaPrepararPrenda', 'elegirProducto(id)'),
            (1, 'PantallaPrepararPrenda', 'GestorProbador', 'preparacion(idProducto)'),
            (1, 'GestorProbador', 'ImagenProducto', 'imagenesDeVestidor(producto)'),
            (1, 'GestorProbador', 'PuntoPrenda', 'puntosDe(imagen)'),
            (1, 'GestorProbador', 'Talla', 'tallasDelProducto(producto)'),
            (1, 'GestorProbador', 'MedidaTalla', 'medidasDe(producto)'),
            (1, 'GestorProbador', 'PantallaPrepararPrenda', 'mostrarPrenda(imagenes, tallas, faltan)'),
            (1, AE, 'PantallaPrepararPrenda', 'marcar(hombroIzq, hombroDer, ruedo)'),
            (1, AE, 'PantallaPrepararPrenda', 'guardarPuntos()'),
            (1, 'PantallaPrepararPrenda', 'GestorProbador', 'guardarPuntos(idImagen, puntos)'),
            (1, 'GestorProbador', 'ImagenProducto', 'imagen(idImagen)'),
            (1, 'GestorProbador', 'GestorProbador', 'validarPuntos(puntos)'),
            (1, 'GestorProbador', 'PuntoPrenda', 'guardar(imagen, puntos)'),
            (1, 'GestorProbador', BM, 'registrar(peticion)'),
            (1, BM, AB, F3),
            (1, AE, 'PantallaPrepararPrenda', 'guardarMedidas(tallas)'),
            (1, 'PantallaPrepararPrenda', 'GestorProbador', 'guardarMedidas(idProducto, tallas)'),
            (1, 'GestorProbador', 'Talla', 'tallasDelProducto(producto)'),
            (1, 'GestorProbador', 'GestorProbador', 'validarSerieDeBusto(tallas)'),
            (1, 'GestorProbador', 'MedidaTalla', 'guardar(producto, talla, medidas)'),
            (1, 'GestorProbador', 'PantallaPrepararPrenda', 'mostrarPrenda(lista, faltan)'),
            (2, 'GestorProbador', 'PantallaPrepararPrenda', 'noEsImagenDeVestidor()'),
            (3, 'GestorProbador', 'PantallaPrepararPrenda', 'puntosInvalidos(motivo)'),
            (4, 'GestorProbador', 'PantallaPrepararPrenda', 'medidasInvalidas(motivo)')]),

    dict(cu='CU-37', n='Probarse una prenda con su talla real', a=['Cliente'],
         # ControlComposicion: la lógica del navegador (pose y dibujo a escala). La foto no viaja (RNF14).
         f=['PantallaProbador'], c=['GestorProbador', 'ControlComposicion', 'GestorMedidas', 'GestorAutenticacion', BM],
         e=['Producto', 'ImagenProducto', 'PuntoPrenda', 'VarianteProducto', 'Cliente', 'MedidaCliente',
            'MedidaTalla', 'SesionVestidorVirtual', AB],
         grupos=['flujo principal: probarse la prenda y guardar la prueba',
                 'alternativo 2a: faltan las medidas del cliente', 'alternativo 4a: no se detecta la pose',
                 'alternativo 8a: borrar una prueba'],
         m=[(1, CL, 'PantallaProbador', 'probarmela(idProducto)'),
            (1, 'PantallaProbador', 'GestorProbador', 'prueba(idProducto)'),
            (1, 'GestorProbador', 'GestorAutenticacion', 'autorizar("CLIENTE")'),
            (1, 'GestorProbador', 'Producto', 'producto(id)'),
            (1, 'GestorProbador', 'ImagenProducto', 'imagenesDeVestidor(producto, soloActivas)'),
            (1, 'GestorProbador', 'PuntoPrenda', 'puntosDe(imagen)'),
            (1, 'GestorProbador', 'Cliente', 'clienteDeUsuario(usuario)'),
            (1, 'GestorProbador', 'MedidaCliente', 'medidasDe(cliente)'),
            (1, 'GestorProbador', 'GestorMedidas', 'ajusteDeProducto(producto, usuario)'),
            (1, 'GestorMedidas', 'MedidaTalla', 'tablaDeProducto(producto)'),
            (1, 'GestorProbador', 'PantallaProbador', 'mostrarPrueba(prendas, ajuste, medidas, fotoIa)'),
            (1, CL, 'PantallaProbador', 'elegirFoto(foto)'),
            (1, 'PantallaProbador', 'ControlComposicion', 'detectarHombros(foto)'),
            (1, CL, 'PantallaProbador', 'elegirTalla(talla)'),
            (1, 'PantallaProbador', 'ControlComposicion', 'dibujar(foto, hombros, prenda, medidas)'),
            (1, 'ControlComposicion', 'ControlComposicion', 'escalarPorCm(bustoCliente, bustoTalla, largoTalla)'),
            (1, 'ControlComposicion', 'PantallaProbador', 'mostrarComposicion(lienzo, comoLeQueda)'),
            (1, CL, 'PantallaProbador', 'guardarPrueba()'),
            (1, 'PantallaProbador', 'GestorProbador', 'registrarSesion(variante, metodo)'),
            (1, 'GestorProbador', 'VarianteProducto', 'variantePreparada(variante)'),
            (1, 'GestorProbador', 'GestorMedidas', 'ajusteDeProducto(producto, usuario)'),
            (1, 'GestorProbador', 'SesionVestidorVirtual', 'crear(cliente, variante, metodo, ajuste, tallaRecomendada)'),
            (1, 'GestorProbador', BM, 'registrar(peticion)'),
            (1, BM, AB, F3),
            (1, 'GestorProbador', 'PantallaProbador', 'pruebaGuardada(sesion)'),
            (2, CL, 'PantallaProbador', 'guardarMedidas(busto, cintura, cadera, altura)'),
            (2, 'PantallaProbador', 'GestorMedidas', 'guardarMisMedidas(medidas)'),
            (2, 'GestorMedidas', 'MedidaCliente', 'guardarMedidas(cliente, medidas)'),
            (2, 'GestorMedidas', BM, 'registrar(peticion)'),
            (2, 'PantallaProbador', 'GestorProbador', 'prueba(idProducto)'),
            (3, 'ControlComposicion', 'PantallaProbador', 'poseNoDetectada()'),
            (3, CL, 'PantallaProbador', 'marcarHombro(punto)'),
            (3, 'PantallaProbador', 'ControlComposicion', 'dibujar(foto, hombros, prenda, medidas)'),
            (4, CL, 'PantallaProbador', 'borrar(sesion)'),
            (4, 'PantallaProbador', 'GestorProbador', 'borrarSesion(idSesion)'),
            (4, 'GestorProbador', 'SesionVestidorVirtual', 'sesion(id)'),
            (4, 'GestorProbador', 'SesionVestidorVirtual', 'borrar()'),
            (4, 'GestorProbador', BM, 'registrar(peticion)'),
            (4, 'GestorProbador', 'PantallaProbador', 'pruebaBorrada()')]),

    dict(cu='CU-38', n='Generar foto realista de la prueba', a=['Cliente'],
         f=['PantallaProbador', 'ProveedorIA'],
         c=['GestorProbador', 'ControlComposicion', 'VerificadorPlan', 'GestorAutenticacion', BM],
         e=['SesionVestidorVirtual', 'ImagenProducto', 'Plan', 'ConsumoCupo', AB],
         grupos=['flujo principal: generar la foto y descontar el cupo',
                 'alternativo 4a: el plan no la incluye o no queda cupo', 'alternativo 5a: la prueba ya tiene foto',
                 'alternativo 6a: falla el proveedor de IA'],
         m=[(1, CL, 'PantallaProbador', 'generarFotoRealista()'),
            (1, 'PantallaProbador', 'GestorProbador', 'registrarSesion(variante, metodo)'),
            (1, 'PantallaProbador', 'ControlComposicion', 'exportarComposicion()'),
            (1, 'ControlComposicion', 'PantallaProbador', 'composicion(png)'),
            (1, 'PantallaProbador', 'GestorProbador', 'generarFoto(idSesion, composicion)'),
            (1, 'GestorProbador', 'GestorAutenticacion', 'autorizar("CLIENTE")'),
            (1, 'GestorProbador', 'VerificadorPlan', 'verificarFuncion("foto_ia")'),
            (1, 'GestorProbador', 'VerificadorPlan', 'verificarCupo("fotos_ia")'),
            (1, 'VerificadorPlan', 'Plan', 'funcionesYCupo()'),
            (1, 'VerificadorPlan', 'ConsumoCupo', 'usoDelMes("fotos_ia")'),
            (1, 'GestorProbador', 'SesionVestidorVirtual', 'sesion(id)'),
            (1, 'GestorProbador', 'ImagenProducto', 'prendaDeVariante(variante)'),
            (1, 'GestorProbador', 'ProveedorIA', 'probar(composicion, prenda, descripcion)'),
            (1, 'ProveedorIA', 'GestorProbador', 'resultado(imagen, generadaPor)'),
            (1, 'GestorProbador', 'GestorProbador', 'guardarFoto(imagen)'),
            (1, 'GestorProbador', 'VerificadorPlan', 'consumirCupo("fotos_ia")'),
            (1, 'VerificadorPlan', 'ConsumoCupo', 'sumarUno(recurso, periodo)'),
            (1, 'GestorProbador', 'SesionVestidorVirtual', 'guardarFoto(ruta, generadaPor)'),
            (1, 'GestorProbador', BM, 'registrar(peticion)'),
            (1, BM, AB, F3),
            (1, 'GestorProbador', 'PantallaProbador', 'mostrarFoto(sesion)'),
            (2, 'VerificadorPlan', 'GestorProbador', 'rechazarPorPlan("plan_limit", limite, uso)'),
            (2, 'GestorProbador', 'PantallaProbador', 'fotoNoDisponible(motivo)'),
            (3, 'GestorProbador', 'PantallaProbador', 'yaTieneFoto()'),
            (4, 'ProveedorIA', 'GestorProbador', 'resultado(imagen, "simulado (falló gemini)")'),
            (4, 'GestorProbador', 'PantallaProbador', 'mostrarFoto(sesion, vistaSimulada)')]),

    dict(cu='CU-39', n='Exportar los datos de la empresa', a=['Administrador de la empresa'],
         # GET: el middleware solo anota las exportaciones de /reportes/*.pdf|xlsx y /comprobante,
         # así que esta descarga no deja asiento (no hay bitácora).
         f=['PantallaDatos'], c=['GestorExportacion', 'GestorAutenticacion', 'VerificadorPlan'],
         e=['Usuario', 'Rol', 'TablaDeEmpresa', 'Plan'],
         grupos=['flujo principal: exportar a Excel', 'alternativo 3a: exportar a CSV',
                 'alternativo 4a: el plan no incluye la exportación'],
         m=[(1, AE, 'PantallaDatos', 'abrirDatos()'),
            (1, 'PantallaDatos', 'VerificadorPlan', 'incluye("exportar_datos")'),
            (1, 'VerificadorPlan', 'Plan', 'funciones()'),
            (1, AE, 'PantallaDatos', 'exportar("xlsx")'),
            (1, 'PantallaDatos', 'GestorExportacion', 'exportarExcel()'),
            (1, 'GestorExportacion', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR")'),
            (1, 'GestorExportacion', 'VerificadorPlan', 'verificarFuncion("exportar_datos")'),
            (1, 'GestorExportacion', 'Usuario', 'personal(empresa)'),
            (1, 'GestorExportacion', 'Rol', 'nombreDe(rol)'),
            (1, 'GestorExportacion', 'TablaDeEmpresa', 'filasDe(tabla)'),
            (1, 'GestorExportacion', 'GestorExportacion', 'escaparFormulas(celdas)'),
            (1, 'GestorExportacion', 'GestorExportacion', 'armarLibro(hojas, resumen)'),
            (1, 'GestorExportacion', 'PantallaDatos', 'descargar(archivo)'),
            (2, AE, 'PantallaDatos', 'exportar("zip")'),
            (2, 'PantallaDatos', 'GestorExportacion', 'exportarCsv()'),
            (2, 'GestorExportacion', 'GestorExportacion', 'armarZip(csvPorTabla)'),
            (2, 'GestorExportacion', 'PantallaDatos', 'descargar(archivo)'),
            (3, 'VerificadorPlan', 'GestorExportacion', 'rechazarPorPlan("plan_limit")'),
            (3, 'GestorExportacion', 'PantallaDatos', 'exportacionBloqueada(motivo)')]),

    dict(cu='CU-40', n='Gestionar copias de seguridad de la empresa', a=['Administrador de la empresa', 'Sistema'],
         f=['PantallaDatos', 'TareaProgramada'],
         c=['GestorRespaldos', 'GestorAutenticacion', 'VerificadorPlan', BM],
         e=['Respaldo', 'Restauracion', 'TablaDeEmpresa', 'Usuario', 'Empresa', 'Plan', AB],
         grupos=['flujo principal: generar y descargar una copia manual',
                 'alternativo 3a: restaurar desde un archivo o una copia automática',
                 'alternativo 4a: todavía no toca la copia manual',
                 'alternativo 3c: copia alterada, de otra empresa o que no entra',
                 'alternativo 1a: copia automática del Sistema'],
         m=[(1, AE, 'PantallaDatos', 'abrirDatos()'),
            (1, 'PantallaDatos', 'GestorRespaldos', 'historial()'),
            (1, 'GestorRespaldos', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR")'),
            (1, 'GestorRespaldos', 'Respaldo', 'listar()'),
            (1, 'GestorRespaldos', 'Restauracion', 'listar()'),
            (1, 'GestorRespaldos', 'Usuario', 'nombres()'),
            (1, 'GestorRespaldos', 'VerificadorPlan', 'planVigente()'),
            (1, 'VerificadorPlan', 'Plan', 'funciones()'),
            (1, 'GestorRespaldos', 'PantallaDatos', 'mostrarHistorial(copias, restauraciones, proximaManual)'),
            (1, AE, 'PantallaDatos', 'copiaManual()'),
            (1, 'PantallaDatos', 'GestorRespaldos', 'manual()'),
            (1, 'GestorRespaldos', 'Respaldo', 'ultima("MANUAL")'),
            (1, 'GestorRespaldos', 'GestorRespaldos', 'abrirFotoRepeatableRead()'),
            (1, 'GestorRespaldos', 'TablaDeEmpresa', 'filasDe(tabla)'),
            (1, 'GestorRespaldos', 'Usuario', 'rolesDelPersonal(empresa)'),
            (1, 'GestorRespaldos', 'Empresa', 'slug()'),
            (1, 'GestorRespaldos', 'GestorRespaldos', 'firmar(cuerpo)'),
            (1, 'GestorRespaldos', 'Respaldo', 'crear("MANUAL", archivo, sha256, filas)'),
            (1, 'GestorRespaldos', BM, 'registrar(peticion)'),
            (1, BM, AB, F3),
            (1, 'GestorRespaldos', 'PantallaDatos', 'descargar(archivo)'),
            (2, AE, 'PantallaDatos', 'restaurar(archivoOCopia, "RESTAURAR")'),
            (2, 'PantallaDatos', 'GestorRespaldos', 'restaurar(archivo)'),
            (2, 'GestorRespaldos', 'Respaldo', 'contenidoDe(idCopia)'),
            (2, 'GestorRespaldos', 'GestorRespaldos', 'leerYVerificarFirma(archivo, empresa)'),
            (2, 'GestorRespaldos', 'TablaDeEmpresa', 'borrarDeEmpresa(empresa)'),
            (2, 'GestorRespaldos', 'TablaDeEmpresa', 'insertar(filas)'),
            (2, 'GestorRespaldos', 'Usuario', 'ponerRolEmpresa(usuario, rol)'),
            (2, 'GestorRespaldos', 'Restauracion', 'crear(origen, archivo, sha256, filas)'),
            (2, 'GestorRespaldos', BM, 'registrar(peticion)'),
            (2, 'GestorRespaldos', 'PantallaDatos', 'restaurado(filas)'),
            (3, 'GestorRespaldos', 'PantallaDatos', 'todaviaNoToca(proximaManual)'),
            (4, 'GestorRespaldos', 'GestorRespaldos', 'deshacerTransaccion()'),
            (4, 'GestorRespaldos', 'PantallaDatos', 'copiaInvalida(motivo)'),
            (5, SI, 'TareaProgramada', 'correrVuelta()'),
            (5, 'TareaProgramada', 'GestorRespaldos', 'automatica(empresa)'),
            (5, 'GestorRespaldos', 'Respaldo', 'ultima("AUTOMATICA")'),
            (5, 'GestorRespaldos', 'TablaDeEmpresa', 'filasDe(tabla)'),
            (5, 'GestorRespaldos', 'Respaldo', 'crear("AUTOMATICA", contenidoCifrado)'),
            (5, 'GestorRespaldos', 'Respaldo', 'borrarSobrantes(retencion)')]),

    dict(cu='CU-41', n='Gestionar roles y permisos de la empresa', a=['Administrador de la empresa'],
         f=['PantallaRoles'], c=['GestorRoles', 'GestorAutenticacion', 'VerificadorPlan', BM],
         e=['RolEmpresa', 'RolEmpresaPermiso', 'Permiso', 'Usuario', 'Rol', 'Sucursal', 'Plan', AB],
         grupos=['flujo principal: crear un rol y asignarlo', 'alternativo 3a: editar un rol',
                 'alternativo 3b: activar o desactivar un rol', 'alternativo 4a: permiso fuera del plan o del rol base',
                 'alternativo 7a: asignación inválida'],
         m=[(1, AE, 'PantallaRoles', 'abrirRoles()'),
            (1, 'PantallaRoles', 'GestorRoles', 'permisos()'),
            (1, 'GestorRoles', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR")'),
            (1, 'GestorRoles', 'Permiso', 'asignables()'),
            (1, 'GestorRoles', 'VerificadorPlan', 'incluye(funcion)'),
            (1, 'VerificadorPlan', 'Plan', 'funciones()'),
            (1, 'PantallaRoles', 'GestorRoles', 'listar()'),
            (1, 'GestorRoles', 'RolEmpresa', 'listar()'),
            (1, 'GestorRoles', 'Usuario', 'personasPorRol()'),
            (1, 'PantallaRoles', 'GestorRoles', 'personal()'),
            (1, 'GestorRoles', 'Usuario', 'personal(empresa)'),
            (1, 'GestorRoles', 'Rol', 'nombreDe(rol)'),
            (1, 'GestorRoles', 'Sucursal', 'sucursalDe(empleado)'),
            (1, 'GestorRoles', 'PantallaRoles', 'mostrar(catalogo, roles, personal)'),
            (1, AE, 'PantallaRoles', 'guardar(nombre, descripcion, rolBase, permisos)'),
            (1, 'PantallaRoles', 'GestorRoles', 'crear(datos)'),
            (1, 'GestorRoles', 'RolEmpresa', 'nombreLibre(nombre)'),
            (1, 'GestorRoles', 'Permiso', 'porCodigo(codigo)'),
            (1, 'GestorRoles', 'VerificadorPlan', 'verificarFuncion(funcion)'),
            (1, 'GestorRoles', 'RolEmpresa', 'crear(rol)'),
            (1, 'GestorRoles', 'RolEmpresaPermiso', 'agregar(rol, permiso)'),
            (1, 'GestorRoles', BM, 'registrar(peticion)'),
            (1, BM, AB, F3),
            (1, 'GestorRoles', 'PantallaRoles', 'rolGuardado(rol)'),
            (1, AE, 'PantallaRoles', 'asignar(persona, rol)'),
            (1, 'PantallaRoles', 'GestorRoles', 'asignar(usuario, rolEmpresa)'),
            (1, 'GestorRoles', 'RolEmpresa', 'obtener(id)'),
            (1, 'GestorRoles', 'Usuario', 'ponerRolEmpresa(rolEmpresa)'),
            (1, 'GestorRoles', 'PantallaRoles', 'asignado(persona)'),
            (2, AE, 'PantallaRoles', 'editar(rol, datos)'),
            (2, 'PantallaRoles', 'GestorRoles', 'editar(id, datos)'),
            (2, 'GestorRoles', 'RolEmpresaPermiso', 'reemplazar(permisos)'),
            (3, AE, 'PantallaRoles', 'cambiarEstado(rol, activo)'),
            (3, 'PantallaRoles', 'GestorRoles', 'cambiarEstado(id, activo)'),
            (3, 'GestorRoles', 'Usuario', 'personasPorRol()'),
            (3, 'GestorRoles', 'RolEmpresa', 'cambiarEstado(activo)'),
            (3, 'GestorRoles', 'PantallaRoles', 'tienePersonasAsignadas(cantidad)'),
            (4, 'VerificadorPlan', 'GestorRoles', 'rechazarPorPlan("plan_limit")'),
            (4, 'GestorRoles', 'PantallaRoles', 'permisoNoPermitido(motivo)'),
            (5, 'GestorRoles', 'PantallaRoles', 'asignacionInvalida(motivo)')]),
]

# Solo los nombres nuevos de la robustez.
DESCRIPCION = {
    'PantallaPrepararPrenda': 'Pantalla «Probador» del administrador (probador-admin.ts): marca los puntos y carga las medidas por talla.',
    'PantallaProbador': 'Probador de la tienda en línea (probador.ts, web): la prenda a escala real sobre la foto del cliente.',
    'PantallaDatos': 'Pantalla «Datos de la empresa» (datos.ts): exportación, copias de seguridad, restauración e historial.',
    'PantallaRoles': 'Pantalla «Roles y permisos» (roles.ts): roles propios, sus permisos y la asignación al personal.',
    'ProveedorIA': 'Frontera de salida: el proveedor de la foto realista (Gemini o la vista simulada con Pillow).',
    'GestorProbador': 'Coordina CU-36 a CU-38: puntos, medidas por talla, pruebas y foto realista (vestidor_virtual/probador_service.py).',
    'ControlComposicion': 'Control del navegador: detecta los hombros con MediaPipe Pose y dibuja la prenda con sus cm; la foto no sale del dispositivo.',
    'GestorMedidas': 'Medidas del cliente y ajuste por talla con la talla recomendada (medidas/service.py y medidas/router.py).',
    'GestorExportacion': 'Coordina CU-39: arma el Excel o el ZIP de CSV con todas las tablas de la empresa (datos/exportacion.py).',
    'GestorRespaldos': 'Coordina CU-40: copia manual firmada, automática cifrada, restauración e historial (datos/respaldos.py).',
    'GestorRoles': 'Coordina CU-41: roles propios, sus permisos y su asignación al personal (roles/service.py).',
    'Producto': 'Prenda del catálogo de la empresa, con sus variantes e imágenes.',
    'VarianteProducto': 'Combinación de talla y color de un producto, con su SKU y su precio.',
    'Talla': 'Talla del catálogo de la empresa, con su orden para comparar series.',
    'PuntoPrenda': 'Calibración de una imagen de vestidor: hombros y ruedo en coordenadas relativas (0 a 1).',
    'MedidaTalla': 'Centímetros de la prenda en una talla: busto, cintura, cadera y largo.',
    'MedidaCliente': 'Medidas del cuerpo del cliente: busto, cintura, cadera y estatura.',
    'SesionVestidorVirtual': 'Una prueba del cliente: variante, método de los hombros, ajuste, talla recomendada y foto realista.',
    'TablaDeEmpresa': 'Cualquier tabla con empresa_id (TABLAS_DE_EMPRESA), leída o repuesta de forma genérica con RLS.',
    'Respaldo': 'Copia de seguridad generada: tipo, archivo, SHA-256, filas por tabla y, si es automática, el contenido cifrado.',
    'Restauracion': 'Cada reemplazo de los datos desde una copia: origen, archivo, de cuándo eran los datos y quién lo hizo.',
    'RolEmpresa': 'Rol propio de una empresa, que parte de un rol base del personal (RN-22).',
    'RolEmpresaPermiso': 'Permiso del catálogo que conserva un rol propio.',
    'Permiso': 'Catálogo de permisos del sistema, definido en código (app/core/permisos.py), con sus rutas y su función del plan.',
}

# ------------------------------------------------------------------ 3.4 ---
B = "backend/app/modules/"
W = "frontend-web/src/app/"
OMIT_AUD = "Omitidas las heredadas de Auditoria: creado_en TIMESTAMPTZ, actualizado_en TIMESTAMPTZ."

CLASES = {
  # ---------------- INTERFACES ----------------
  "ProbadorAdmin": {"tipo": "interfaz", "origen": W+"features/admin/probador/probador-admin.ts",
    "nota": "Ruta /admin/probador, menú «Probador». cargarProductos(), mostrar() y refrescar() son privados.",
    "atributos": [], "operaciones": ["ngOnInit(): void", "elegirProducto(id: number): void",
      "elegirImagen(imagen: ImagenParaPreparar | null): void", "marcar(evento: MouseEvent): void",
      "elegirPaso(paso: Paso): void", "guardarPuntos(): void", "guardarMedidas(): void",
      "pct(valor: number | undefined): string"]},
  "Probador": {"tipo": "interfaz", "origen": W+"features/tienda/probador/probador.ts",
    "nota": "Ruta /tienda/producto/:id/probador (sesionGuard + rolGuard('CLIENTE')), WEB. La pose (MediaPipe) y el dibujo a escala corren aca; cargar(), cargarMisPruebas(), imagenDe() y superponer() son privados.",
    "atributos": [], "operaciones": ["ngOnInit(): void", "guardarMedidas(): void", "elegirTalla(tallaId: number): void",
      "cambiarPrenda(prenda: PrendaDelProbador | null): void", "elegirFoto(evento: Event): void",
      "detectarPose(): Promise<void>", "marcarHombro(evento: MouseEvent): void", "dibujar(): Promise<void>",
      "guardarPrueba(): void", "generarFoto(): void", "borrar(s: SesionProbador): void",
      "generadaPor(s: SesionProbador): string"]},
  "Datos": {"tipo": "interfaz", "origen": W+"features/admin/datos/datos.ts",
    "nota": "Ruta /admin/datos, menú «Datos y copias». guardar(d) (descarga el Blob), mostrar() y mensajeDeBlob() son privados.",
    "atributos": [], "operaciones": ["ngOnInit(): void", "cargar(): void", "textoIntervalo(horas: number | null): string",
      "totalFilas(filas: Record<string, number>): number", "exportar(formato: 'xlsx' | 'zip'): void",
      "copiaManual(): void", "copiaAutomatica(): void", "descargar(copia: Copia): void",
      "elegirArchivo(evento: Event): void", "prepararRestauracion(copia: Copia): void",
      "cancelarRestauracion(): void", "restaurar(): void"]},
  "Roles": {"tipo": "interfaz", "origen": W+"features/admin/roles/roles.ts",
    "nota": "Ruta /admin/roles, menú «Roles y permisos» (solo con roles.gestionar). cargar() y mostrar() son privados.",
    "atributos": [], "operaciones": ["ngOnInit(): void", "nuevo(): void", "editar(rol: RolEmpresa): void",
      "cambiarBase(base: RolBase): void", "alternar(codigo: string, marcado: boolean): void", "guardar(): void",
      "cambiarEstado(rol: RolEmpresa, activo: boolean, control?: { checked: boolean }): void",
      "rolesPara(persona: Persona): RolEmpresa[]",
      "asignar(persona: Persona, rolId: number | null, control?: { value: unknown }): void"]},

  # ---------------- CONTROLES (web) ----------------
  "ProbadorService": {"tipo": "control", "origen": W+"core/services/probador.service.ts",
    "atributos": ["admin: string", "vestidor: string"],
    "operaciones": ["productos(): Observable<ProductoDelProbador[]>", "preparacion(productoId: number): Observable<PrendaParaPreparar>",
      "guardarPuntos(imagenId: number, puntos: PuntosDePrenda): Observable<PuntosDePrenda>",
      "guardarMedidas(productoId: number, tallas: MedidaDeTalla[]): Observable<PrendaParaPreparar>",
      "prueba(productoId: number): Observable<PruebaDeProducto>", "guardarMisMedidas(medidas: MedidasDelCliente): Observable<unknown>",
      "registrar(varianteId: number, metodo: 'POSE' | 'MANUAL'): Observable<SesionProbador>",
      "misPruebas(): Observable<SesionProbador[]>", "borrar(sesionId: number): Observable<void>",
      "generarFoto(sesionId: number, composicion: Blob): Observable<SesionProbador>"]},
  "DatosService": {"tipo": "control", "origen": W+"core/services/datos.service.ts",
    "atributos": ["api: string"],
    "operaciones": ["exportar(formato: 'xlsx' | 'zip'): Observable<Descarga>", "historial(): Observable<HistorialDeCopias>",
      "copiaManual(): Observable<Descarga>", "descargarCopia(id: number): Observable<Descarga>",
      "copiaAutomatica(): Observable<{ creada: boolean; motivo: string | null; borradas: number }>",
      "restaurarArchivo(archivo: File): Observable<Restaurado>", "restaurarCopia(id: number): Observable<Restaurado>"]},
  "RolesService": {"tipo": "control", "origen": W+"core/services/roles.service.ts",
    "atributos": ["base: string"],
    "operaciones": ["permisos(): Observable<PermisoDelCatalogo[]>", "listar(): Observable<RolEmpresa[]>",
      "crear(datos: GuardarRol): Observable<RolEmpresa>", "editar(id: number, datos: Omit<GuardarRol, 'rol_base'>): Observable<RolEmpresa>",
      "estado(id: number, activo: boolean): Observable<RolEmpresa>", "personal(): Observable<Persona[]>",
      "asignar(usuarioId: number, rolId: number | null): Observable<Persona>"]},

  # ---------------- CONTROLES (backend) ----------------
  "probador_service": {"tipo": "control", "origen": B+"vestidor_virtual/probador_service.py",
    "nota": "Modulo de funciones. Rutas en vestidor_virtual/probador_router.py: admin_router /catalogo/probador (ADMINISTRADOR; GET /productos, GET /productos/{id}, PUT /imagenes/{id}/puntos, PUT /productos/{id}/medidas) y cliente_router /vestidor (CLIENTE; GET /productos/{id}/prueba, POST y GET /sesiones, DELETE /sesiones/{id}, POST /sesiones/{id}/foto con requiere_funcion('foto_ia') y requiere_cupo('fotos_ia')). prueba() tambien llama a vestidor_virtual/service.py estado(db) para saber si ofrecer la foto.",
    "atributos": ["SEPARACION_MINIMA_HOMBROS: float = 0.10", "DESNIVEL_MAXIMO_HOMBROS: float = 0.15", "LARGO_MINIMO: float = 0.10"],
    "operaciones": ["productos(db): list[ProductoDelProbador]", "preparacion(db, producto_id): PrendaParaPreparar",
      "validar_puntos(puntos: PuntosDePrenda): None", "guardar_puntos(db, imagen_id, puntos): PuntosDePrenda",
      "guardar_medidas(db, producto_id, tallas: list[MedidaDeTalla]): PrendaParaPreparar",
      "prueba(db, producto_id, usuario_id): PruebaDeProducto", "registrar_sesion(db, usuario_id, variante_id, metodo): SesionSalida",
      "mis_sesiones(db, usuario_id): list[SesionSalida]", "borrar_sesion(db, usuario_id, sesion_id): None",
      "_sesion_propia(db, usuario_id, sesion_id): SesionVestidorVirtual", "_guardar_foto(contenido: bytes): str",
      "generar_foto(db, usuario_id, sesion_id, composicion: bytes, tipo_mime: str | None): SesionSalida",
      "_producto_o_404(db, producto_id)", "_cliente_o_404(db, usuario_id): int"]},
  "medidas_service": {"tipo": "control", "origen": B+"medidas/service.py",
    "nota": "El ajuste por talla y la talla recomendada (clasificacion de medidas/tallaje.py: A_TU_MEDIDA, HOLGADA, ...). Las medidas del cliente se guardan por PUT /clientes/me/medidas (medidas/router.py guardar_mis_medidas -> repository.guardar_medidas).",
    "atributos": [], "operaciones": ["ajuste_de_producto(db, producto_id, usuario_id): AjusteDeProducto",
      "_sin_ajuste(producto_id, hay_medidas, hay_tabla): AjusteDeProducto"]},
  "verificador": {"tipo": "control", "origen": B+"plataforma/verificador.py",
    "nota": "CU-05. Lo piden las dependencias requiere_funcion / requiere_cupo de app/core/dependencies.py. Rechaza con RechazoDelPlan (403 plan_limit) o SinSuscripcionVigente.",
    "atributos": ["FUNCIONES: dict[str, str]", "CUPOS: dict[str, tuple[str, str]]"],
    "operaciones": ["suscripcion_vigente(db): Suscripcion | None", "plan_vigente(db): Plan", "incluye(db, funcion): bool",
      "verificar_funcion(db, funcion): None", "verificar_cupo(db, cupo): None", "uso_del_mes(db, cupo): int",
      "consumir_cupo(db, cupo): int"]},
  "probador_ia": {"tipo": "control", "origen": "backend/app/integrations/probador_ia/__init__.py",
    "nota": "Integracion con el proveedor (ProbadorGemini, ProbadorSimulado con Pillow, ProbadorNoDisponible). Si Gemini falla devuelve la vista simulada con generada_por = 'simulado (fallo gemini)'; ProbadorNoConfigurado -> 503.",
    "atributos": [], "operaciones": ["obtener_proveedor(): ProveedorProbador", "esta_disponible(): bool",
      "probar(solicitud: SolicitudDeProbado): ResultadoDeProbado"]},
  "exportacion": {"tipo": "control", "origen": B+"datos/exportacion.py",
    "nota": "Rutas en datos/router.py: GET /exportacion/datos.xlsx y GET /exportacion/datos.zip, con requiere_roles('ADMINISTRADOR') y requiere_funcion('exportar_datos'). Del personal nunca sale el hash de la contrasena.",
    "atributos": ["_LARGO_HOJA: int = 31"],
    "operaciones": ["_personal(db, empresa_id): tuple[list[str], list[list]]", "_hojas(db, empresa_id)",
      "a_excel(db, empresa_id): bytes", "_texto(valor): str", "a_zip_csv(db, empresa_id): bytes"]},
  "tablas": {"tipo": "control", "origen": B+"datos/tablas.py",
    "nota": "Acceso generico a las tablas de empresa (Base.metadata.sorted_tables, en orden de dependencias). FUERA_DE_LA_EXPORTACION = respaldo, suscripcion_push, modelo_analitica.",
    "atributos": ["FUERA_DE_LA_COPIA: frozenset[str]", "FUERA_DE_LA_EXPORTACION: frozenset[str]"],
    "operaciones": ["tablas_de_empresa(excluir: frozenset[str]): list[Table]", "filas_de(db, tabla: Table): list[dict]",
      "sin_formula(valor)", "a_json(valor)", "de_json(columna, valor)", "a_celda(valor)"]},
  "respaldos": {"tipo": "control", "origen": B+"datos/respaldos.py",
    "nota": "Rutas en datos/router.py (ADMINISTRADOR): GET /respaldos, POST /respaldos/manual, GET /respaldos/{id}/descarga, POST /respaldos/restaurar (archivo, tope 50 MB), POST /respaldos/{id}/restaurar y POST /mantenimiento/respaldos. Firma HMAC-SHA256; automatica cifrada con Fernet.",
    "atributos": ["FORMATO: str = 'violet-boutique/respaldo'", "VERSION: int = 1", "INTERVALO_AUTOMATICO_POR_OMISION: int = 24",
      "RETENCION_POR_OMISION: int = 7"],
    "operaciones": ["historial(db): dict", "proxima_manual(db): datetime | None", "_ajustes(db): tuple[int | None, int, str]",
      "manual(db, empresa_id, usuario_id): tuple[bytes, str]", "armar(db, empresa_id): tuple[bytes, dict[str, int], datetime]",
      "_instantanea(db): None", "_firmar(cuerpo: dict): str", "automatica(db, empresa_id): dict",
      "contenido_de(db, respaldo_id): tuple[bytes, Respaldo]", "_leer(archivo: bytes, empresa_id): dict",
      "restaurar(db, archivo, *, nombre, empresa_id, usuario_id, origen, respaldo_id): Restauracion",
      "restaurar_copia_guardada(db, respaldo_id, *, empresa_id, usuario_id): Restauracion",
      "_preferencias(db, empresa_id): list[dict]", "_reponer_preferencias(db, preferencias, empresa_id): None"]},
  "tareas": {"tipo": "control", "origen": "backend/app/core/tareas.py",
    "nota": "Las tareas automaticas del Sistema: una tarea asyncio dentro del backend que despierta cada TAREAS_INTERVALO_MINUTOS y, por cada empresa activa, corre _copia -> respaldos.automatica.",
    "atributos": [], "operaciones": ["correr_vuelta(fabrica_de_sesiones, minimo_entre_vueltas): Vuelta",
      "_copia(db, empresa_id): None", "_empresas_activas(db): list[int]"]},
  "roles_service": {"tipo": "control", "origen": B+"roles/service.py",
    "nota": "Modulo de funciones. Rutas en roles/router.py (ADMINISTRADOR sin rol propio): GET /roles/permisos, GET /roles/personal, PUT /roles/asignacion, GET y POST /roles, PATCH /roles/{id}, PATCH /roles/{id}/estado.",
    "atributos": [],
    "operaciones": ["catalogo_de_permisos(db): list[PermisoOut]", "_validar_permisos(db, rol_base, codigos): list[str]",
      "listar(db): list[RolOut]", "crear(db, datos: RolIn): RolOut", "editar(db, rol_id, datos: RolEditarIn): RolOut",
      "cambiar_estado(db, rol_id, activo): RolOut", "personal(db, empresa_id): list[PersonaOut]",
      "asignar(db, empresa_id, quien_id, datos: AsignacionIn): PersonaOut", "_personas_por_rol(db): dict[int, int]",
      "_nombre_libre(db, nombre, excepto): None", "_poner_permisos(rol, codigos): None"]},
  "permisos": {"tipo": "control", "origen": "backend/app/core/permisos.py",
    "nota": "El catalogo de permisos es del sistema (dataclass Permiso: codigo, nombre, area, roles_base, rutas, funcion, asignable). get_usuario_actual (core/dependencies.py) corta con 403 la ruta que el rol propio no cubre.",
    "atributos": ["ROLES_BASE: tuple[str, ...]", "CATALOGO: tuple[Permiso, ...]", "POR_CODIGO: dict[str, Permiso]", "RUTAS_LIBRES: tuple[str, ...]"],
    "operaciones": ["permiso_de_ruta(ruta): str | None", "es_libre(ruta): bool", "asignables_para(rol_base): list[Permiso]",
      "es_consulta_de_apoyo(metodo, ruta): bool"]},
  "BitacoraMiddleware": {"tipo": "control", "origen": B+"bitacora/middleware.py",
    "nota": "Anota toda peticion POST/PUT/PATCH/DELETE (y las exportaciones GET). _anotar llama a bitacora/service.py registrar(db, accion, metodo, ruta, estado_http, exito, usuario_id, actor, rol, entidad, entidad_id, ip, agente, detalle), que inserta con bitacora/repository.py agregar(db, **campos). Los GET no se anotan.",
    "atributos": [], "operaciones": ["dispatch(peticion: Request, siguiente): Response", "_anotar(peticion: Request, respuesta): None"]},

  # ---------------- ENTIDADES ----------------
  "Producto": {"tipo": "entidad", "origen": B+"catalogo/models.py", "tabla": "producto", "nota": OMIT_AUD,
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "codigo: VARCHAR(30)", "nombre: VARCHAR(120)",
      "descripcion: VARCHAR(500)", "categoria_id: INTEGER (FK categoria)", "proveedor_id: BIGINT (FK proveedor)",
      "temporada_id: INTEGER (FK temporada)", "coleccion_id: INTEGER (FK coleccion)", "precio_base: NUMERIC(10,2)", "activo: BOOLEAN"],
    "operaciones": ["producto(db, producto_id): Producto | None  [vestidor_virtual/probador_repository.py]",
      "productos_con_vestidor(db): list[Row]  [vestidor_virtual/probador_repository.py]"]},
  "ImagenProducto": {"tipo": "entidad", "origen": B+"catalogo/models.py", "tabla": "imagen_producto", "nota": OMIT_AUD,
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "producto_id: BIGINT (FK producto, ON DELETE CASCADE)",
      "variante_id: BIGINT (FK variante_producto, ON DELETE CASCADE)", "ruta: VARCHAR(255)", "es_principal: BOOLEAN",
      "es_transparente: BOOLEAN", "es_silueta_generada: BOOLEAN", "orden: SMALLINT"],
    "operaciones": ["imagen(db, imagen_id): ImagenProducto | None  [vestidor_virtual/probador_repository.py]",
      "imagenes_de_vestidor(db, producto_id, solo_activas): list[Row]  [vestidor_virtual/probador_repository.py]",
      "prenda_de_variante(db, variante_id): Row | None  [vestidor_virtual/repository.py]"]},
  "VarianteProducto": {"tipo": "entidad", "origen": B+"catalogo/models.py", "tabla": "variante_producto", "nota": OMIT_AUD,
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "producto_id: BIGINT (FK producto)", "talla_id: INTEGER (FK talla)",
      "color_id: INTEGER (FK color)", "sku: VARCHAR(40)", "precio: NUMERIC(10,2)", "activa: BOOLEAN"],
    "operaciones": ["variante_preparada(db, variante_id): Row | None  [vestidor_virtual/probador_repository.py]"]},
  "Talla": {"tipo": "entidad", "origen": B+"catalogo/models.py", "tabla": "talla", "nota": OMIT_AUD,
    "atributos": ["id: INTEGER (PK)", "empresa_id: BIGINT (FK empresa)", "tipo_prenda: VARCHAR(30)", "codigo: VARCHAR(10)",
      "orden: SMALLINT", "activa: BOOLEAN"],
    "operaciones": ["tallas_del_producto(db, producto_id): list[Row]  [vestidor_virtual/probador_repository.py, JOIN medida_talla]"]},
  "PuntoPrenda": {"tipo": "entidad", "origen": B+"vestidor_virtual/models.py", "tabla": "punto_prenda",
    "nota": OMIT_AUD + " CHECK: coordenadas entre 0 y 1, hombro_izq_x < hombro_der_x, ruedo debajo de los hombros. Migracion 0041_cu36_probador.",
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "imagen_id: BIGINT (FK imagen_producto, UNIQUE, ON DELETE CASCADE)",
      "hombro_izq_x: NUMERIC(5,4)", "hombro_izq_y: NUMERIC(5,4)", "hombro_der_x: NUMERIC(5,4)", "hombro_der_y: NUMERIC(5,4)",
      "ruedo_x: NUMERIC(5,4)", "ruedo_y: NUMERIC(5,4)"],
    "operaciones": ["puntos_de(db, imagen_id): PuntoPrenda | None  [vestidor_virtual/probador_repository.py]",
      "imagenes_de_vestidor(db, producto_id, solo_activas): list[Row]  [vestidor_virtual/probador_repository.py, OUTER JOIN punto_prenda]"]},
  "MedidaTalla": {"tipo": "entidad", "origen": B+"medidas/models.py", "tabla": "medida_talla",
    "nota": OMIT_AUD + " UNIQUE (producto_id, talla_id); busto, cintura y cadera entre 30 y 250, largo entre 20 y 200.",
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "producto_id: BIGINT (FK producto, ON DELETE CASCADE)",
      "talla_id: INTEGER (FK talla)", "busto_cm: NUMERIC(5,1)", "cintura_cm: NUMERIC(5,1)", "cadera_cm: NUMERIC(5,1)", "largo_cm: NUMERIC(5,1)"],
    "operaciones": ["medida_talla(db, producto_id, talla_id): MedidaTalla | None  [vestidor_virtual/probador_repository.py]",
      "tallas_del_producto(db, producto_id): list[Row]  [vestidor_virtual/probador_repository.py]",
      "tabla_de_producto(db, producto_id): list[tuple]  [medidas/repository.py]"]},
  "MedidaCliente": {"tipo": "entidad", "origen": B+"medidas/models.py", "tabla": "medida_cliente",
    "nota": OMIT_AUD + " No es tabla de empresa (sin empresa_id): el cliente es de la plataforma (RN-13).",
    "atributos": ["id: BIGINT (PK)", "cliente_id: BIGINT (FK cliente, UNIQUE, ON DELETE CASCADE)", "busto_cm: NUMERIC(5,1)",
      "cintura_cm: NUMERIC(5,1)", "cadera_cm: NUMERIC(5,1)", "altura_cm: NUMERIC(5,1)"],
    "operaciones": ["medidas_de(db, cliente_id): MedidaCliente | None  [medidas/repository.py]",
      "guardar_medidas(db, cliente_id, busto_cm, cintura_cm, cadera_cm, altura_cm): MedidaCliente  [medidas/repository.py]",
      "cliente_de_usuario(db, usuario_id): Cliente | None  [medidas/repository.py]"]},
  "SesionVestidorVirtual": {"tipo": "entidad", "origen": B+"vestidor_virtual/models.py", "tabla": "sesion_probador",
    "nota": "CHECK metodo IN ('POSE', 'MANUAL') y (foto_ruta IS NULL) = (foto_generada_por IS NULL).",
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "cliente_id: BIGINT (FK cliente, ON DELETE CASCADE)",
      "variante_id: BIGINT (FK variante_producto, ON DELETE CASCADE)", "metodo: VARCHAR(10)", "ajuste: VARCHAR(15)",
      "talla_recomendada: VARCHAR(10)", "foto_ruta: VARCHAR(255)", "foto_generada_por: VARCHAR(60)", "creado_en: TIMESTAMPTZ"],
    "operaciones": ["sesion(db, sesion_id): SesionVestidorVirtual | None  [vestidor_virtual/probador_repository.py]",
      "sesiones_de(db, cliente_id, limite): list[Row]  [vestidor_virtual/probador_repository.py]",
      "una_sesion_con_detalle(db, sesion_id): Row | None  [vestidor_virtual/probador_repository.py]"]},
  "ConsumoCupo": {"tipo": "entidad", "origen": B+"plataforma/models.py", "tabla": "consumo_cupo",
    "nota": "PK compuesta (empresa_id, recurso, periodo); periodo = primer dia del mes. CHECK usados >= 0.",
    "atributos": ["empresa_id: BIGINT (PK, FK empresa)", "recurso: VARCHAR(20) (PK)", "periodo: DATE (PK)", "usados: INTEGER"],
    "operaciones": ["uso_del_mes(db, cupo): int  [plataforma/verificador.py]",
      "consumir_cupo(db, cupo): int  [plataforma/verificador.py, INSERT ... ON CONFLICT DO UPDATE]"]},
  "Plan": {"tipo": "entidad", "origen": B+"plataforma/models.py", "tabla": "plan",
    "nota": "Funciones usadas aca (en funciones JSONB): foto_ia, exportar_datos, respaldo_intervalo_horas, respaldo_retencion y las de los permisos con funcion (RN-22).",
    "atributos": ["id: SMALLINT (PK)", "codigo: VARCHAR(20) (UNIQUE)", "nombre: VARCHAR(40) (UNIQUE)", "precio_mensual: NUMERIC(10,2)",
      "duracion_dias: SMALLINT", "max_sucursales: INTEGER", "max_empleados: INTEGER", "cupo_reportes_ia: INTEGER",
      "cupo_fotos_ia: INTEGER", "funciones: JSONB", "activo: BOOLEAN"],
    "operaciones": ["plan_vigente(db): Plan  [plataforma/verificador.py, por la suscripcion vigente]"]},
  "Respaldo": {"tipo": "entidad", "origen": B+"datos/models.py", "tabla": "respaldo",
    "nota": "Sin repository: las consultas estan en datos/respaldos.py. CHECK tipo IN ('MANUAL', 'AUTOMATICA') y (tipo = 'AUTOMATICA') = (contenido IS NOT NULL): la manual no se guarda (RNF17).",
    "atributos": ["id: INTEGER (PK)", "empresa_id: BIGINT (FK empresa)", "tipo: VARCHAR(10)", "archivo: VARCHAR(120)", "tamano_bytes: INTEGER",
      "sha256: VARCHAR(64)", "filas: JSONB", "contenido: BYTEA", "creado_por: BIGINT (FK usuario, ON DELETE SET NULL)", "creado_en: TIMESTAMPTZ"],
    "operaciones": ["_ultima(db, tipo): datetime | None  [datos/respaldos.py]",
      "manual(db, empresa_id, usuario_id): INSERT respaldo  [datos/respaldos.py]",
      "automatica(db, empresa_id): INSERT respaldo y DELETE de las sobrantes  [datos/respaldos.py]",
      "contenido_de(db, respaldo_id): tuple[bytes, Respaldo]  [datos/respaldos.py]",
      "historial(db): SELECT respaldo ORDER BY creado_en DESC  [datos/respaldos.py]"]},
  "Restauracion": {"tipo": "entidad", "origen": B+"datos/models.py", "tabla": "restauracion",
    "nota": "Sin repository: las consultas estan en datos/respaldos.py. CHECK origen IN ('ARCHIVO', 'COPIA').",
    "atributos": ["id: INTEGER (PK)", "empresa_id: BIGINT (FK empresa)", "origen: VARCHAR(10)", "archivo: VARCHAR(120)", "sha256: VARCHAR(64)",
      "datos_del: TIMESTAMPTZ", "filas: JSONB", "respaldo_id: INTEGER (FK respaldo, ON DELETE SET NULL)",
      "restaurado_por: BIGINT (FK usuario, ON DELETE SET NULL)", "creado_en: TIMESTAMPTZ"],
    "operaciones": ["restaurar(db, archivo, *, nombre, empresa_id, usuario_id, origen, respaldo_id): INSERT restauracion  [datos/respaldos.py]",
      "historial(db): SELECT restauracion ORDER BY creado_en DESC  [datos/respaldos.py]"]},
  "RolEmpresa": {"tipo": "entidad", "origen": B+"roles/models.py", "tabla": "rol_empresa",
    "nota": OMIT_AUD + " Sin repository: las consultas estan en roles/service.py. UNIQUE (empresa_id, nombre); CHECK rol_base IN ('ADMINISTRADOR', 'ENCARGADO', 'CAJERO').",
    "atributos": ["id: INTEGER (PK)", "empresa_id: BIGINT (FK empresa)", "nombre: VARCHAR(40)", "descripcion: VARCHAR(150)",
      "rol_base: VARCHAR(15)", "activo: BOOLEAN"],
    "operaciones": ["listar(db): SELECT rol_empresa ORDER BY rol_base, nombre  [roles/service.py]",
      "_rol(db, rol_id): RolEmpresa  [roles/service.py]", "_nombre_libre(db, nombre, excepto): None  [roles/service.py]"]},
  "RolEmpresaPermiso": {"tipo": "entidad", "origen": B+"roles/models.py", "tabla": "rol_empresa_permiso",
    "nota": "UNIQUE (rol_empresa_id, permiso). permiso guarda el codigo del catalogo de app/core/permisos.py (no hay tabla de permisos).",
    "atributos": ["id: INTEGER (PK)", "empresa_id: BIGINT (FK empresa)", "rol_empresa_id: INTEGER (FK rol_empresa, ON DELETE CASCADE)",
      "permiso: VARCHAR(60)"],
    "operaciones": ["_poner_permisos(rol, codigos): None  [roles/service.py, cascade all, delete-orphan]"]},
  "Usuario": {"tipo": "entidad", "origen": B+"seguridad/models.py", "tabla": "usuario", "nota": OMIT_AUD + " usuario no esta bajo RLS: la empresa se filtra a mano.",
    "atributos": ["id: BIGINT (PK)", "correo: VARCHAR(120)", "hash_contrasena: VARCHAR(255)", "nombres: VARCHAR(80)", "apellidos: VARCHAR(80)",
      "rol_id: SMALLINT (FK rol)", "activo: BOOLEAN", "empresa_id: BIGINT (FK empresa)", "rol_empresa_id: INTEGER (FK rol_empresa, ON DELETE SET NULL)"],
    "operaciones": ["_consulta_personal(empresa_id): Select  [roles/service.py, JOIN rol, empleado, sucursal, rol_empresa]",
      "_personas_por_rol(db): dict[int, int]  [roles/service.py]",
      "asignar(db, empresa_id, quien_id, datos): UPDATE usuario.rol_empresa_id  [roles/service.py]",
      "_personal(db, empresa_id): tuple[list[str], list[list]]  [datos/exportacion.py]",
      "armar(db, empresa_id): SELECT id, rol_empresa_id  [datos/respaldos.py]",
      "historial(db): SELECT id, nombres, apellidos  [datos/respaldos.py]"]},
  "Rol": {"tipo": "entidad", "origen": B+"seguridad/models.py", "tabla": "rol",
    "atributos": ["id: SMALLINT (PK)", "nombre: VARCHAR(30) (UNIQUE)", "descripcion: VARCHAR(150)"],
    "operaciones": ["_consulta_personal(empresa_id): Select  [roles/service.py, JOIN rol]",
      "_personal(db, empresa_id)  [datos/exportacion.py, JOIN rol]"]},
  "AsientoBitacora": {"tipo": "entidad", "origen": B+"bitacora/models.py", "tabla": "bitacora",
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "ocurrido_en: TIMESTAMPTZ", "usuario_id: BIGINT (FK usuario, ON DELETE SET NULL)",
      "actor: VARCHAR(160)", "rol: VARCHAR(40)", "accion: VARCHAR(40)", "entidad: VARCHAR(60)", "entidad_id: VARCHAR(60)", "metodo: VARCHAR(10)",
      "ruta: VARCHAR(300)", "estado_http: INTEGER", "exito: BOOLEAN", "ip: VARCHAR(60)", "agente: VARCHAR(200)", "detalle: JSONB"],
    "operaciones": ["agregar(db, **campos): AsientoBitacora", "contar(db, **filtros): int", "listar(db, limite, desplazamiento, **filtros): list[tuple]",
      "acciones(db): list[str]", "roles(db): list[str]", "entidades(db): list[str]", "ultimo(db): AsientoBitacora | None"]},
}

# FK reales (multiplicidad: primero en el extremo ClaseA, despues en ClaseB)
FK = [
  ["Producto", "ImagenProducto", "TIENE", "1", "0..*"],
  ["VarianteProducto", "ImagenProducto", "SE_MUESTRA_EN", "0..1", "0..*"],
  ["ImagenProducto", "PuntoPrenda", "SE_CALIBRA_CON", "1", "0..1"],
  ["Producto", "VarianteProducto", "TIENE", "1", "0..*"],
  ["Talla", "VarianteProducto", "CLASIFICA", "1", "0..*"],
  ["Producto", "MedidaTalla", "SE_MIDE_EN", "1", "0..*"],
  ["Talla", "MedidaTalla", "SE_MIDE_EN", "1", "0..*"],
  ["VarianteProducto", "SesionVestidorVirtual", "SE_PRUEBA_EN", "1", "0..*"],
  ["Usuario", "Respaldo", "GENERA", "0..1", "0..*"],
  ["Usuario", "Restauracion", "RESTAURA", "0..1", "0..*"],
  ["Respaldo", "Restauracion", "SE_RESTAURA_EN", "0..1", "0..*"],
  ["RolEmpresa", "RolEmpresaPermiso", "TIENE", "1", "0..*"],
  ["RolEmpresa", "Usuario", "SE_ASIGNA_A", "0..1", "0..*"],
  ["Rol", "Usuario", "CLASIFICA", "1", "0..*"],
  ["Usuario", "AsientoBitacora", "DEJA_RASTRO_EN", "0..1", "0..*"],
]


def fks(cls):
    s = set(cls)
    return [list(v) for v in FK if v[0] in s and v[1] in s]


def bit(controles):
    return [[c, "BitacoraMiddleware", "ES_ANOTADO_POR", "1", "1"] for c in controles] + \
           [["BitacoraMiddleware", "AsientoBitacora", "REGISTRA", "1", "0..*"]]


CUS = {}

c36 = ["ProbadorAdmin", "ProbadorService", "probador_service", "BitacoraMiddleware", "AsientoBitacora", "Producto",
       "ImagenProducto", "PuntoPrenda", "VarianteProducto", "Talla", "MedidaTalla"]
CUS["CU-36"] = {"actores": ["Administrador"], "clases": c36,
  "operaciones_en_cu": {
     "ProbadorService": ["productos()", "preparacion(productoId)", "guardarPuntos(imagenId, puntos)", "guardarMedidas(productoId, tallas)"],
     "probador_service": ["productos(db)", "preparacion(db, producto_id)", "validar_puntos(puntos)", "guardar_puntos(db, imagen_id, puntos)",
       "guardar_medidas(db, producto_id, tallas)", "_producto_o_404(db, producto_id)"],
     "ImagenProducto": ["imagen(db, imagen_id)", "imagenes_de_vestidor(db, producto_id, solo_activas)"]},
  "nota": "Solo se calibran las imagenes de vestidor (es_transparente y con variante_id); las sube el CU-11 del primer parcial (galeria del producto). Las rutas van bajo /catalogo para que el permiso catalogo.gestionar de un rol propio (CU-41) las cubra. VarianteProducto entra por imagenes_de_vestidor (JOIN variante -> talla y color).",
  "relaciones": [["Administrador", "ProbadorAdmin", "USA", "1", "1"], ["ProbadorAdmin", "ProbadorService", "SOLICITA", "1", "1"],
    ["ProbadorService", "probador_service", "LLAMA_A", "1", "1"],
    ["probador_service", "Producto", "CONSULTA", "1", "0..*"], ["probador_service", "ImagenProducto", "CONSULTA", "1", "0..*"],
    ["probador_service", "VarianteProducto", "CONSULTA", "1", "0..*"], ["probador_service", "Talla", "CONSULTA", "1", "0..*"],
    ["probador_service", "PuntoPrenda", "REGISTRA", "1", "0..*"], ["probador_service", "MedidaTalla", "REGISTRA", "1", "0..*"]]
    + bit(["probador_service"]) + fks(c36)}

c37 = ["Probador", "ProbadorService", "probador_service", "medidas_service", "BitacoraMiddleware", "AsientoBitacora",
       "SesionVestidorVirtual", "PuntoPrenda", "ImagenProducto", "VarianteProducto", "MedidaTalla", "MedidaCliente"]
CUS["CU-37"] = {"actores": ["Cliente"], "clases": c37,
  "operaciones_en_cu": {
     "Probador": ["ngOnInit()", "guardarMedidas()", "elegirTalla(tallaId)", "cambiarPrenda(prenda)", "elegirFoto(evento)",
       "detectarPose()", "marcarHombro(evento)", "dibujar()", "guardarPrueba()", "borrar(s)"],
     "ProbadorService": ["prueba(productoId)", "guardarMisMedidas(medidas)", "registrar(varianteId, metodo)", "misPruebas()", "borrar(sesionId)"],
     "probador_service": ["prueba(db, producto_id, usuario_id)", "registrar_sesion(db, usuario_id, variante_id, metodo)",
       "mis_sesiones(db, usuario_id)", "borrar_sesion(db, usuario_id, sesion_id)", "_sesion_propia(db, usuario_id, sesion_id)",
       "_cliente_o_404(db, usuario_id)"],
     "ImagenProducto": ["imagenes_de_vestidor(db, producto_id, solo_activas)"]},
  "nota": "WEB, no movil (el 2.5 dice Movil). La pose (MediaPipe Pose) y el dibujo a escala corren en el navegador: px_por_cm = hombros_px / (busto_cliente_cm x 0.42), ancho = busto_talla_cm x 0.42 x px_por_cm, largo = largo_talla_cm x px_por_cm. El ajuste y la talla recomendada los recalcula el servidor (medidas_service). Omitidos por el tope: Producto, Cliente (medidas/repository.py cliente_de_usuario) y medidas/router.py guardar_mis_medidas (PUT /clientes/me/medidas).",
  "relaciones": [["Cliente", "Probador", "USA", "1", "1"], ["Probador", "ProbadorService", "SOLICITA", "1", "1"],
    ["ProbadorService", "probador_service", "LLAMA_A", "1", "1"], ["probador_service", "medidas_service", "LLAMA_A", "1", "1"],
    ["probador_service", "ImagenProducto", "CONSULTA", "1", "0..*"], ["probador_service", "PuntoPrenda", "CONSULTA", "1", "0..*"],
    ["probador_service", "VarianteProducto", "CONSULTA", "1", "0..1"], ["probador_service", "MedidaCliente", "CONSULTA", "1", "0..1"],
    ["medidas_service", "MedidaTalla", "CONSULTA", "1", "0..*"], ["medidas_service", "MedidaCliente", "CONSULTA", "1", "0..1"],
    ["probador_service", "SesionVestidorVirtual", "REGISTRA", "1", "0..*"]]
    + bit(["probador_service"]) + fks(c37)}

c38 = ["Probador", "ProbadorService", "probador_service", "verificador", "probador_ia", "BitacoraMiddleware", "AsientoBitacora",
       "SesionVestidorVirtual", "ImagenProducto", "ConsumoCupo", "Plan"]
CUS["CU-38"] = {"actores": ["Cliente"], "clases": c38,
  "operaciones_en_cu": {
     "Probador": ["generarFoto()", "generadaPor(s)"],
     "ProbadorService": ["registrar(varianteId, metodo)", "generarFoto(sesionId, composicion)"],
     "probador_service": ["generar_foto(db, usuario_id, sesion_id, composicion, tipo_mime)", "_sesion_propia(db, usuario_id, sesion_id)",
       "_guardar_foto(contenido)", "registrar_sesion(db, usuario_id, variante_id, metodo)"],
     "verificador": ["plan_vigente(db)", "incluye(db, funcion)", "verificar_funcion(db, funcion)", "verificar_cupo(db, cupo)",
       "uso_del_mes(db, cupo)", "consumir_cupo(db, cupo)"],
     "ImagenProducto": ["prenda_de_variante(db, variante_id)"]},
  "nota": "Incluye CU-05: requiere_funcion('foto_ia') y requiere_cupo('fotos_ia') en la ruta; el cupo es de la tienda, no del cliente, y se descuenta con consumir_cupo solo despues de que la foto salio (si falla el descuento, borra el archivo). Una foto por prueba (409). Composicion de hasta 4 MB (TAMANO_MAXIMO_CAPTURA de vestidor_virtual/service.py). La foto se guarda en MEDIA_ROOT/probador con un nombre aleatorio de 128 bits.",
  "relaciones": [["Cliente", "Probador", "USA", "1", "1"], ["Probador", "ProbadorService", "SOLICITA", "1", "1"],
    ["ProbadorService", "probador_service", "LLAMA_A", "1", "1"], ["probador_service", "verificador", "VERIFICA_CON", "1", "1"],
    ["probador_service", "probador_ia", "LLAMA_A", "1", "1"],
    ["probador_service", "SesionVestidorVirtual", "ACTUALIZA", "1", "0..1"], ["probador_service", "ImagenProducto", "CONSULTA", "1", "0..1"],
    ["verificador", "Plan", "CONSULTA", "1", "1"], ["verificador", "ConsumoCupo", "ACTUALIZA", "1", "0..1"]]
    + bit(["probador_service"]) + fks(c38)}

c39 = ["Datos", "DatosService", "exportacion", "tablas", "verificador", "Usuario", "Rol", "Plan"]
CUS["CU-39"] = {"actores": ["Administrador"], "clases": c39,
  "operaciones_en_cu": {
     "Datos": ["ngOnInit()", "exportar(formato)"], "DatosService": ["exportar(formato)"],
     "verificador": ["plan_vigente(db)", "incluye(db, funcion)", "verificar_funcion(db, funcion)"],
     "Usuario": ["_personal(db, empresa_id)"], "Rol": ["_personal(db, empresa_id)"]},
  "nota": "Incluye CU-05 (requiere_funcion('exportar_datos')). Solo lectura: GET /exportacion/datos.xlsx y GET /exportacion/datos.zip. Ojo: el middleware de bitacora solo anota las exportaciones de /reportes/*.pdf|xlsx y /comprobante, asi que esta descarga NO deja asiento; por eso no hay BitacoraMiddleware. Las demas tablas de empresa se leen de forma generica con tablas.filas_de (RLS); al abrir, la pantalla pregunta el plan por MiPlanService.incluye('exportar_datos') (omitido).",
  "relaciones": [["Administrador", "Datos", "USA", "1", "1"], ["Datos", "DatosService", "SOLICITA", "1", "1"],
    ["DatosService", "exportacion", "DESCARGA_DE", "1", "1"], ["exportacion", "verificador", "VERIFICA_CON", "1", "1"],
    ["exportacion", "tablas", "LLAMA_A", "1", "1"], ["exportacion", "Usuario", "CONSULTA", "1", "0..*"],
    ["exportacion", "Rol", "CONSULTA", "1", "0..*"], ["verificador", "Plan", "CONSULTA", "1", "1"]] + fks(c39)}

c40 = ["Datos", "DatosService", "respaldos", "tablas", "verificador", "tareas", "BitacoraMiddleware", "AsientoBitacora",
       "Respaldo", "Restauracion", "Usuario", "Plan"]
CUS["CU-40"] = {"actores": ["Administrador", "Sistema"], "clases": c40,
  "operaciones_en_cu": {
     "Datos": ["ngOnInit()", "cargar()", "textoIntervalo(horas)", "totalFilas(filas)", "copiaManual()", "copiaAutomatica()",
       "descargar(copia)", "elegirArchivo(evento)", "prepararRestauracion(copia)", "cancelarRestauracion()", "restaurar()"],
     "DatosService": ["historial()", "copiaManual()", "descargarCopia(id)", "copiaAutomatica()", "restaurarArchivo(archivo)", "restaurarCopia(id)"],
     "verificador": ["plan_vigente(db)"],
     "Usuario": ["armar(db, empresa_id)", "historial(db)"]},
  "nota": "Incluye CU-05: el plan limita cada cuanto sale una copia manual (funciones.respaldo_intervalo_horas) y cuantas automaticas se conservan (respaldo_retencion); la restauracion nunca (RN-18). La manual se descarga y solo queda su registro; la automatica se guarda cifrada (Fernet). Restaurar exige escribir RESTAURAR en la pantalla, verifica formato, version, firma HMAC y empresa, y borra/inserta en una transaccion. Todas las tablas de empresa se leen y reponen de forma generica (tablas); omitidas Empresa (slug para el nombre del archivo) y cliente_categoria (preferencias de los clientes).",
  "relaciones": [["Administrador", "Datos", "USA", "1", "1"], ["Sistema", "tareas", "DISPARA", "1", "1"],
    ["Datos", "DatosService", "SOLICITA", "1", "1"], ["DatosService", "respaldos", "LLAMA_A", "1", "1"],
    ["tareas", "respaldos", "LLAMA_A", "1", "1"], ["respaldos", "verificador", "VERIFICA_CON", "1", "1"],
    ["respaldos", "tablas", "LLAMA_A", "1", "1"], ["respaldos", "Respaldo", "REGISTRA", "1", "0..*"],
    ["respaldos", "Restauracion", "REGISTRA", "1", "0..*"], ["respaldos", "Usuario", "ACTUALIZA", "1", "0..*"],
    ["verificador", "Plan", "CONSULTA", "1", "1"]] + bit(["respaldos"]) + fks(c40)}

c41 = ["Roles", "RolesService", "roles_service", "permisos", "verificador", "BitacoraMiddleware", "AsientoBitacora",
       "RolEmpresa", "RolEmpresaPermiso", "Usuario", "Rol", "Plan"]
CUS["CU-41"] = {"actores": ["Administrador"], "clases": c41,
  "operaciones_en_cu": {
     "verificador": ["plan_vigente(db)", "incluye(db, funcion)", "verificar_funcion(db, funcion)"],
     "Usuario": ["_consulta_personal(empresa_id)", "_personas_por_rol(db)", "asignar(db, empresa_id, quien_id, datos)"],
     "Rol": ["_consulta_personal(empresa_id)"]},
  "nota": "Incluye CU-05: un permiso con funcion del plan se rechaza con verificar_funcion (403 plan_limit, RN-22). usuarios.gestionar, roles.gestionar y respaldos.gestionar no son asignables. El rol propio se lee en cada peticion (core/dependencies.py get_usuario_actual): vale desde la siguiente. Omitidos por el tope: Empleado y Sucursal (OUTER JOIN de _consulta_personal para mostrar la sucursal).",
  "relaciones": [["Administrador", "Roles", "USA", "1", "1"], ["Roles", "RolesService", "SOLICITA", "1", "1"],
    ["RolesService", "roles_service", "LLAMA_A", "1", "1"], ["roles_service", "permisos", "CONSULTA", "1", "1"],
    ["roles_service", "verificador", "VERIFICA_CON", "1", "1"], ["roles_service", "RolEmpresa", "REGISTRA", "1", "0..*"],
    ["roles_service", "RolEmpresaPermiso", "REGISTRA", "1", "0..*"], ["roles_service", "Usuario", "ACTUALIZA", "1", "0..*"],
    ["roles_service", "Rol", "CONSULTA", "1", "0..*"], ["verificador", "Plan", "CONSULTA", "1", "1"]]
    + bit(["roles_service"]) + fks(c41)}

# ------------------------------------------------------------------ 2.6 ---
ESPEC = {
    'CU-36': dict(
        descripcion='Permite al administrador dejar una prenda lista para el probador: marca dónde están los hombros y '
                    'el ruedo en su imagen sin fondo y carga cuánto mide la prenda en cada talla.',
        actores='Administrador de la empresa',
        iniciador='Administrador de la empresa',
        precondiciones='El administrador inició sesión. El producto tiene al menos una imagen PNG sin fondo asociada a '
                       'una variante, subida en la galería del producto.',
        flujo=['El administrador abre «Probador» en el menú de administración.',
               'El sistema lista los productos con imagen de vestidor y su avance: imágenes calibradas y tallas con medidas.',
               'El administrador elige un producto; el sistema muestra sus imágenes, sus tallas y lo que falta para dejarlo listo.',
               'El administrador marca con un clic el hombro izquierdo, el hombro derecho y el ruedo sobre la imagen, y pulsa «Guardar puntos».',
               'El sistema verifica que la imagen sea de vestidor y que los puntos sean coherentes, y los guarda en coordenadas relativas.',
               'El administrador carga busto, cintura, cadera y largo en cm de cada talla y pulsa «Guardar medidas».',
               'El sistema verifica que cada talla se venda en el producto, que no se repita y que el busto no baje al subir de talla, y guarda las medidas.',
               'El sistema actualiza el avance: con una imagen calibrada y todas las tallas medidas, el producto queda «Lista» para el probador.'],
        alternativos=['5a. Imagen que no es de vestidor: si la imagen no es un PNG sin fondo asociado a una variante, el '
                      'sistema la rechaza y no guarda los puntos.',
                      '5b. Puntos incoherentes: hombros invertidos, separados menos del 10 % del ancho, con un desnivel '
                      'de más del 15 % del alto o con el ruedo a menos del 10 % debajo de los hombros; el sistema explica '
                      'el motivo y no guarda.',
                      '6a. Talla incompleta: si a una talla le falta alguna de las cuatro medidas, la pantalla avisa '
                      'cuál es antes de enviar.',
                      '7a. Medidas inválidas: una talla que no se vende en el producto, una talla repetida o un busto '
                      'menor que el de la talla anterior; el sistema rechaza todo el lote con el motivo.'],
        postcondiciones='La imagen queda calibrada y las medidas por talla quedan guardadas. El probador de la tienda ya '
                        'puede dibujar esa prenda a su tamaño real. La bitácora registra cada cambio.',
        rastreo='RF-43'),
    'CU-37': dict(
        descripcion='Permite al cliente probarse una prenda sobre su propia foto, dibujada con los centímetros reales de la '
                    'talla elegida, para ver si le queda grande o chica antes de comprar.',
        actores='Cliente',
        iniciador='Cliente',
        precondiciones='El cliente inició sesión en la tienda en línea de la empresa (web). La prenda fue preparada '
                       'para el probador (CU-36).',
        flujo=['En la ficha de una prenda de la tienda en línea, el cliente pulsa «Probármela».',
               'El sistema devuelve las variantes preparadas con su imagen y sus puntos, las medidas del cliente, el ajuste de cada talla con la talla recomendada y si la foto realista está disponible.',
               'El cliente sube o toma una foto de cuerpo entero.',
               'El navegador detecta los hombros con MediaPipe Pose; la foto no sale del dispositivo.',
               'El cliente elige la talla y el color; por omisión se muestra la talla recomendada.',
               'El navegador dibuja la prenda con los cm de esa talla, a la escala que dan el busto del cliente y sus hombros en la foto, y muestra cómo le queda.',
               'El cliente pulsa «Guardar esta prueba».',
               'El sistema recalcula en el servidor el ajuste y la talla recomendada, registra la prueba y la muestra en «Mis pruebas».'],
        alternativos=['2a. Faltan las medidas: la pantalla pide busto, cintura, cadera y, si quiere, la estatura; las '
                      'guarda y vuelve a cargar la prueba. Sin medidas la prenda se dibuja en tamaño aproximado y se avisa.',
                      '2b. Prenda no preparada: si ninguna variante tiene puntos, el sistema muestra «Esta prenda todavía '
                      'no está preparada para el probador».',
                      '4a. No se detecta la pose: el sistema pide marcar los dos hombros con un clic sobre la foto; la '
                      'prueba queda con el método MANUAL.',
                      '7a. Foto realista: el cliente pulsa «Generar foto realista» (extiende con CU-38).',
                      '8a. Borrar una prueba: el cliente borra una prueba de «Mis pruebas»; el sistema la elimina con su '
                      'foto, si la tenía.'],
        postcondiciones='La prueba queda registrada con la variante, el método, el ajuste y la talla recomendada. La foto '
                        'del cliente no se guardó en el servidor. La bitácora registra la prueba.',
        rastreo='RF-44'),
    'CU-38': dict(
        descripcion='Permite al cliente obtener una foto realista de su prueba, generada con IA a partir de la composición '
                    'a escala, sin que la prenda cambie de tamaño.',
        actores='Cliente',
        iniciador='Cliente',
        precondiciones='El cliente está en el probador con la prenda dibujada a escala (CU-37). El plan de la tienda '
                       'incluye la foto con IA y le queda cupo en el mes.',
        flujo=['El cliente pulsa «Generar foto realista».',
               'Si la prueba no estaba guardada, el sistema la registra primero.',
               'El navegador exporta la composición del lienzo como PNG y la envía; es la única imagen del cliente que sale de su dispositivo.',
               'El sistema verifica que el plan de la tienda incluya la foto con IA y que le quede cupo en el mes (incluye CU-05).',
               'El sistema verifica que la prueba sea del cliente, que no tenga foto y que la composición sea una imagen de hasta 4 MB.',
               'El sistema envía la composición y la imagen de la prenda al proveedor de IA, con el pedido de no cambiar su tamaño.',
               'Con la foto hecha, el sistema la guarda con un nombre aleatorio y recién entonces descuenta una del cupo mensual de la tienda.',
               'El sistema muestra la foto en la prueba y en «Mis pruebas», y dice si la generó la IA o es una vista simulada.'],
        alternativos=['4a. Sin la función o sin cupo: el plan no incluye la foto con IA o la tienda ya usó las del mes; '
                      'el sistema rechaza con el motivo y la pantalla muestra «Foto realista no disponible».',
                      '5a. La prueba ya tiene foto: el sistema pide hacer otra prueba para generar una nueva.',
                      '6a. Falla el proveedor: si Gemini no responde, la foto sale igual con la vista simulada, marcada '
                      'como tal; si la foto con IA está apagada en el entorno, el sistema rechaza sin descontar el cupo.',
                      '7a. Se agotó el cupo mientras tanto: si otro pedido se llevó el último lugar, el sistema borra la '
                      'foto recién guardada y rechaza sin descontar.'],
        postcondiciones='La prueba tiene su foto realista y quién la generó. El cupo de fotos con IA de la tienda bajó en '
                        'una. La bitácora registra el pedido.',
        rastreo='RF-45, RF-09 · RN-11'),
    'CU-39': dict(
        descripcion='Permite al administrador descargar todos los datos de su empresa para leerlos, en un Excel con una '
                    'hoja por tabla o en un ZIP con un CSV por tabla.',
        actores='Administrador de la empresa',
        iniciador='Administrador de la empresa',
        precondiciones='El administrador inició sesión. El plan de la empresa incluye la exportación de datos.',
        flujo=['El administrador abre «Datos y copias» en el menú de administración.',
               'El sistema consulta si el plan incluye la exportación y, si no, deja los botones bloqueados antes del clic.',
               'El administrador pulsa «Excel».',
               'El sistema verifica que sea administrador y que el plan incluya la función de exportar los datos (incluye CU-05).',
               'El sistema lee todas las tablas de la empresa en orden de dependencias; del personal saca solo lo que muestra la pantalla de usuarios, nunca la contraseña.',
               'El sistema deja fuera las copias de seguridad, los dispositivos push y los modelos de analítica, y escapa los textos que una planilla tomaría por fórmula.',
               'El sistema arma un Excel con una hoja por tabla y una hoja «resumen» con las filas de cada una.',
               'El navegador descarga el archivo con la empresa y la fecha en el nombre.'],
        alternativos=['3a. En CSV: el administrador pulsa «CSV (ZIP)»; el sistema arma un ZIP con un CSV por tabla, con '
                      'BOM para que Excel en español lea bien las tildes.',
                      '4a. El plan no incluye la exportación: el sistema rechaza con el motivo y la pantalla deja los '
                      'botones bloqueados.',
                      '4b. Rol propio sin el permiso: si el administrador tiene un rol propio sin «Exportar todos los '
                      'datos», el sistema rechaza el pedido (CU-41).'],
        postcondiciones='El administrador tiene una copia legible de los datos de su empresa. No se modificó ningún dato.',
        rastreo='RF-48, RF-09'),
    'CU-40': dict(
        descripcion='Permite al administrador generar copias de seguridad de su empresa, descargarlas, restaurar los datos '
                    'desde una copia y ver el historial; el sistema genera además copias automáticas.',
        actores='Administrador de la empresa, Sistema',
        iniciador='Administrador de la empresa (la copia automática la inicia el Sistema)',
        precondiciones='El administrador inició sesión y no tiene un rol propio. La empresa tiene una suscripción vigente '
                       'para generar copias; para restaurar no hace falta.',
        flujo=['El administrador abre «Datos y copias» en el menú de administración.',
               'El sistema muestra el historial de copias y restauraciones (cuándo, quién, tamaño y filas por tabla), lo que permite el plan y desde cuándo se puede pedir la próxima copia manual.',
               'El administrador pulsa «Generar y descargar copia».',
               'El sistema verifica que el plan permita otra copia manual según su intervalo (incluye CU-05).',
               'El sistema lee todas las tablas de la empresa en una sola foto, con el rol propio de cada persona del personal y las preferencias de los clientes.',
               'El sistema firma la copia, registra su SHA-256, su tamaño y sus filas por tabla, y no guarda el contenido.',
               'El navegador descarga el archivo JSON y avisa que no queda en el servidor.'],
        alternativos=['1a. Copia automática: en cada vuelta de las tareas automáticas, si ya pasó el intervalo del plan '
                      '(diaria por omisión), el sistema genera la copia cifrada y conserva solo las últimas que indica el '
                      'plan (7 por omisión).',
                      '3a. Restaurar: el administrador elige un archivo o una copia automática del historial y escribe '
                      'RESTAURAR; el sistema reemplaza todos los datos de la empresa por los de la copia en una sola '
                      'transacción y registra la restauración.',
                      '3b. Descargar una automática: el sistema descifra la copia guardada y la entrega; una manual no se '
                      'puede volver a bajar porque no quedó en el servidor.',
                      '3c. Copia inválida: si el archivo no es una copia, es de otra versión, su firma no coincide o es de '
                      'otra empresa, el sistema la rechaza; si una fila no entra, deshace todo y los datos no cambian.',
                      '4a. Todavía no toca: el sistema rechaza con la fecha desde la que se puede pedir la próxima copia '
                      'manual; las automáticas siguen saliendo.'],
        postcondiciones='Queda registrada la copia o la restauración, con quién, cuándo, tamaño y filas por tabla. Tras '
                        'una restauración, los datos de la empresa son los de la copia. La bitácora registra cada operación.',
        rastreo='RF-60, RF-61, RF-62, RF-63 · RN-18, RN-19'),
    'CU-41': dict(
        descripcion='Permite al administrador crear roles propios de su empresa a partir de un rol base, elegir sus '
                    'permisos y asignarlos a su personal.',
        actores='Administrador de la empresa',
        iniciador='Administrador de la empresa',
        precondiciones='El administrador inició sesión y no tiene un rol propio.',
        flujo=['El administrador abre «Roles y permisos» en el menú de administración.',
               'El sistema muestra el catálogo de permisos por área, marcando los que el plan no incluye, los roles de la empresa con cuántas personas tienen cada uno, y el personal con su rol.',
               'El administrador pulsa «Nuevo rol», escribe el nombre y la descripción, elige el rol base (administrador, encargado o cajero) y marca los permisos.',
               'El sistema verifica que el nombre no esté usado y que cada permiso exista, se pueda delegar, sea del rol base y esté incluido en el plan (incluye CU-05).',
               'El sistema guarda el rol con sus permisos, solo para la empresa.',
               'En la pestaña «Personal», el administrador elige el rol para una persona.',
               'El sistema verifica que la persona sea del personal, que no sea él mismo, y que el rol esté activo y sea de su mismo rol base, y se lo asigna.',
               'Desde su siguiente pedido, esa persona solo entra a las pantallas que cubren los permisos de su rol.'],
        alternativos=['3a. Editar: el administrador cambia el nombre, la descripción o los permisos; el rol base no se '
                      'cambia.',
                      '3b. Desactivar: el sistema no apaga un rol con personas asignadas y pide reasignarlas antes.',
                      '4a. Permiso no permitido: si un permiso no está en el plan, el sistema rechaza por el plan; si no es '
                      'del rol base o no se delega (usuarios, roles y copias de seguridad), lo rechaza con el motivo.',
                      '4b. Nombre repetido: ya hay un rol con ese nombre en la empresa.',
                      '6a. Quitar el rol propio: con «Todo lo de su rol», la persona vuelve a tener todos los permisos de '
                      'su rol base.'],
        postcondiciones='El rol queda guardado solo para la empresa y la persona queda con sus permisos, que nunca superan '
                        'los de su rol base ni los del plan. La bitácora registra cada cambio.',
        rastreo='RF-64, RF-09 · RN-22'),
}


# ------------------------------------------------------------- validación ---
def validar():
    ids = {c[0] for c in CASOS}
    for r in ROBUSTEZ:
        assert r['cu'] in ids, r['cu']
        tipos = {**{f'A:{x}': 'A' for x in r['a']}, **{x: 'F' for x in r['f']},
                 **{x: 'C' for x in r['c']}, **{x: 'E' for x in r['e']}}
        grupos = sorted({g for g, *_ in r['m']})
        assert grupos == list(range(1, len(r['grupos']) + 1)), (r['cu'], grupos)
        for g, de, a, op in r['m']:
            assert de in tipos and a in tipos, (r['cu'], de, a)
            par = {tipos[de], tipos[a]}
            # la regla de la ing: nunca entidad con entidad; tampoco frontera con frontera
            assert par in ({'A', 'F'}, {'F', 'C'}, {'C', 'E'}, {'C'}), (r['cu'], de, a, op)
        usados = {p for _, de, a, _ in r['m'] for p in (de, a)}
        assert usados == set(tipos), (r['cu'], set(tipos) - usados)
        # F3: si aparece la bitácora, aparecen los dos y el agregar(...)
        if BM in r['c'] or AB in r['e']:
            assert BM in r['c'] and AB in r['e'], r['cu']
            assert any(de == BM and a == AB and op.startswith('agregar(') for _, de, a, op in r['m']), r['cu']
            assert any(a == BM and op == 'registrar(peticion)' for _, de, a, op in r['m']), r['cu']
    # DESCRIPCION solo trae nombres que aparecen en alguna robustez (los reusados de p2 no van).
    nombres_nuevos = set(DESCRIPCION)
    assert nombres_nuevos <= {x for r in ROBUSTEZ for x in r['f'] + r['c'] + r['e']}, \
        nombres_nuevos - {x for r in ROBUSTEZ for x in r['f'] + r['c'] + r['e']}
    actores_validos = {'Administrador de la plataforma', 'Administrador de la empresa', 'Encargado de sucursal', 'Cajero',
                       'Cliente', 'Proveedor', 'Sistema', 'Usuario', 'Empresa interesada'}
    for c in CASOS:
        assert set(c[2]) <= actores_validos, c[0]
        for x in c[3] + (c[5] if len(c) > 5 else []):
            assert x in ids or (x.startswith('CU-') and 1 <= int(x[3:]) <= 20), (c[0], x)


def validar_cus():
    for cu, d in CUS.items():
        assert 6 <= len(d["clases"]) <= 12, (cu, len(d["clases"]))
        for c in d["clases"]:
            assert c in CLASES, (cu, c)
        for r in d["relaciones"]:
            for x in r[:2]:
                assert x in d["clases"] or x in d["actores"], (cu, r)
        for c in d.get("operaciones_en_cu", {}):
            assert c in d["clases"], (cu, c)
        if "BitacoraMiddleware" in d["clases"]:
            assert "AsientoBitacora" in d["clases"], cu
            assert any(r[1] == "BitacoraMiddleware" and r[2] == "ES_ANOTADO_POR" for r in d["relaciones"]), cu
    assert set(CUS) == {c[0] for c in CASOS}, set(CUS) ^ {c[0] for c in CASOS}


CLAVES_ESPEC = ('descripcion', 'actores', 'iniciador', 'precondiciones', 'flujo', 'alternativos', 'postcondiciones',
                'rastreo')


def validar_espec():
    import re
    assert set(ESPEC) == {c[0] for c in CASOS}, set(ESPEC) ^ {c[0] for c in CASOS}
    for cu, e in ESPEC.items():
        for k in CLAVES_ESPEC:
            assert k in e and e[k], (cu, k)
        assert 5 <= len(e['flujo']) <= 10, (cu, len(e['flujo']))
        assert 2 <= len(e['alternativos']) <= 5, (cu, len(e['alternativos']))
        for alt in e['alternativos']:
            assert re.match(r'^\d+[a-z]\. [^:]+: ', alt), (cu, alt)
            paso = int(re.match(r'^(\d+)', alt).group(1))
            assert 1 <= paso <= len(e['flujo']), (cu, alt)


if __name__ == '__main__':
    validar()
    validar_cus()
    validar_espec()
    print('ok:', len(CASOS), 'casos de uso,', len(ROBUSTEZ), 'robusteces,', len(CLASES), 'clases,',
          len(ESPEC), 'fichas')
    for cu, d in CUS.items():
        print(' ', cu, len(d['clases']), 'clases,', len(d['relaciones']), 'relaciones')
