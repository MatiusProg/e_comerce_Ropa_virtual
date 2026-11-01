# Datos del 3.4 Diseño de clases de la 1ra presentación (CU-01 a CU-12), sacados del código.
# Mismo formato que p2_clases_datos.py. Lo dibuja scripts/ea-p2-clases.ps1.
# Uso: python -X utf8 scripts/p2_clases_datos_p1.py  -> scripts/ea-p2-clases-p1.datos.json
# Datos del 3.4 Diseño de clases de la 1ra presentación del 2do parcial (CU-01 a CU-12), sacados del código.
# Mismo formato que scripts/p2_clases_datos.py (CU-13..20): interfaz (acciones de la pantalla), control
# (métodos reales) y entidad (columnas con su tipo y las funciones que consultan la tabla).
# Uso: python -X utf8 gen_clases_p1.py  -> ea-p2-clases-p1.datos.json (al lado de este script)
import json, os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ea-p2-clases-p1.datos.json")
B = "backend/app/modules/"
C = "backend/app/core/"
W = "frontend-web/src/app/"
M = "mobile/lib/"
OMIT_AUD = "Omitidas las heredadas de Auditoria: creado_en TIMESTAMPTZ, actualizado_en TIMESTAMPTZ."
SIN_REPO = ("plataforma/ no tiene repository.py para esta tabla: las consultas viven como funciones de los "
            "servicios (planes.py, suscripciones.py, verificador.py, mi_tienda/service.py, contratacion/service.py); "
            "se listan esas funciones con su archivo.")

clases = {
  # ======================= INTERFACES (web Angular) =======================
  "Empresas": {"tipo": "interfaz", "origen": W+"features/plataforma/empresas/empresas.ts",
    "nota": "La busqueda es un FormControl que dispara cargar(). Abrir la ficha de una empresa (CU-03) es un routerLink, sin metodo.",
    "atributos": [], "operaciones": ["cargar(): void", "nueva(): void", "editar(empresa: Empresa): void",
      "cambiarEstado(empresa: Empresa): void", "marcarVencidas(): void"]},
  "EmpresaFormulario": {"tipo": "interfaz", "origen": W+"features/plataforma/empresas/empresa-formulario.ts",
    "nota": "Dialogo de alta/edicion que abre Empresas.nueva()/editar(). Cancelar es ref.close(null) inline.",
    "atributos": [], "operaciones": ["tocarSlug(): void", "guardar(): void"]},
  "Planes": {"tipo": "interfaz", "origen": W+"features/plataforma/planes/planes.ts",
    "atributos": [], "operaciones": ["cargar(): void", "nuevo(): void", "editar(plan: Plan): void", "cambiarEstado(plan: Plan): void"]},
  "PlanFormulario": {"tipo": "interfaz", "origen": W+"features/plataforma/planes/plan-formulario.ts",
    "atributos": [], "operaciones": ["alternar(clave: string, marcada: boolean): void", "guardar(): void"]},
  "FichaEmpresa": {"tipo": "interfaz", "origen": W+"features/plataforma/empresas/ficha-empresa.ts",
    "nota": "renovar() y suspenderOReactivar() piden confirmacion y llaman al privado ejecutar(accion, exito) -> PlataformaService.accionSuscripcion().",
    "atributos": [], "operaciones": ["cargar(): void", "cambiarPlan(): void", "renovar(): void", "suspenderOReactivar(): void"]},
  "CambiarPlan": {"tipo": "interfaz", "origen": W+"features/plataforma/empresas/cambiar-plan.ts",
    "nota": "Dialogo que abre FichaEmpresa.cambiarPlan(): plan y fecha de inicio.",
    "atributos": [], "operaciones": ["guardar(): void"]},
  "MiPlan": {"tipo": "interfaz", "origen": W+"features/admin/mi-plan/mi-plan.ts",
    "nota": "'Comparar con otros planes' es comparando.set(!comparando()) inline, sin metodo propio; los otros planes ya vienen en la respuesta (otros_planes).",
    "atributos": [], "operaciones": ["consultar(): void"]},
  "LimiteDelPlan": {"tipo": "interfaz", "origen": W+"shared/limite-del-plan/limite-del-plan.ts",
    "nota": "Componente <app-limite-del-plan recurso='sucursales'|'empleados'> que muestran Sucursales y Empleados: avisa el uso del limite antes de abrir el formulario. El rechazo real (403 plan_limit) lo traducen los servicios con rechazoDelPlan() de core/models/plan.models.ts.",
    "atributos": ["recurso: InputSignal<'sucursales' | 'empleados'>", "alcanzado: Signal<boolean>"],
    "operaciones": ["recargar(): void", "mensajeAlcanzado(): string"]},
  "Login": {"tipo": "interfaz", "origen": W+"features/auth/login/login.ts",
    "nota": "Mostrar la contrasena es verContrasena.set() inline. El menu del rol y la marca (paso 6) los arma el layout del rol y App (app.ts) con MarcaService.cargar() al cambiar la empresa de la sesion.",
    "atributos": [], "operaciones": ["enviar(): void"]},
  "Registro": {"tipo": "interfaz", "origen": W+"features/auth/registro/registro.ts",
    "atributos": [], "operaciones": ["enviar(): void", "usarCuentaExistente(): void", "volverAlFormulario(): void", "irALogin(): void"]},
  "Usuarios": {"tipo": "interfaz", "origen": W+"features/admin/usuarios/usuarios.ts",
    "nota": "Si eliminar() falla por operaciones asociadas, el privado ofrecerDesactivar() llama a UsuariosService.cambiarEstado(id, false).",
    "atributos": [], "operaciones": ["cargar(): void", "paginar(evento: PageEvent): void", "limpiarFiltros(): void", "nuevo(): void",
      "editar(usuario: UsuarioResumen): void", "cambiarEstado(usuario: UsuarioResumen): void", "eliminar(usuario: UsuarioResumen): void"]},
  "UsuarioFormulario": {"tipo": "interfaz", "origen": W+"features/admin/usuarios/usuario-formulario.ts",
    "nota": "En el constructor carga el selector de sucursales con OrganizacionService.sucursales() (del CU-09, omitido).",
    "atributos": [], "operaciones": ["guardar(): void"]},
  "Sucursales": {"tipo": "interfaz", "origen": W+"features/admin/sucursales/sucursales.ts",
    "nota": "Incluye <app-limite-del-plan recurso='sucursales'> (ver LimiteDelPlan, CU-05). El rechazo del plan lo muestra el privado mostrarRechazoDelPlan(mensaje), que ofrece 'Ver mi plan'.",
    "atributos": [], "operaciones": ["cargar(): void", "limpiarFiltros(): void", "nueva(): void", "editar(sucursal: Sucursal): void",
      "cambiarEstado(sucursal: Sucursal): void"]},
  "SucursalFormulario": {"tipo": "interfaz", "origen": W+"features/admin/sucursales/sucursal-formulario.ts",
    "atributos": [], "operaciones": ["guardar(): void"]},
  "Empleados": {"tipo": "interfaz", "origen": W+"features/admin/empleados/empleados.ts",
    "nota": "Incluye <app-limite-del-plan recurso='empleados'>. El filtro de sucursal se llena con OrganizacionService.sucursales() (omitido).",
    "atributos": [], "operaciones": ["cargar(): void", "limpiarFiltros(): void", "nuevo(): void", "editar(empleado: Empleado): void",
      "darDeBaja(empleado: Empleado): void"]},
  "EmpleadoFormulario": {"tipo": "interfaz", "origen": W+"features/admin/empleados/empleado-formulario.ts",
    "nota": "elegirCamino('nueva' | 'existente'): cuenta nueva o vincular una existente (usuariosVinculables()).",
    "atributos": [], "operaciones": ["elegirCamino(camino: CaminoDeAlta): void", "guardar(): void"]},
  "PlanesPublicos": {"tipo": "interfaz", "origen": W+"features/contratar/planes-publicos.ts",
    "nota": "Elegir un plan es un routerLink a /contratar/:codigo, sin metodo propio.",
    "atributos": [], "operaciones": ["cargar(): void"]},
  "Contratar": {"tipo": "interfaz", "origen": W+"features/contratar/contratar.ts",
    "nota": "El slug se verifica mientras se escribe: un valueChanges con switchMap a ContratacionService.verificarSlug(). El pago simulado es metodo 'QR' con codigo_operacion.",
    "atributos": [], "operaciones": ["tocarSlug(): void", "usarSlug(sugerido: string): void", "contratar(): void", "irALogin(): void"]},
  "MiTienda": {"tipo": "interfaz", "origen": W+"features/admin/mi-tienda/mi-tienda.ts",
    "nota": "Las cuatro acciones que guardan pasan por el privado guardar(peticion, mensaje), que al terminar llama a MarcaService.cargar() (1.11).",
    "atributos": [], "operaciones": ["elegirPrincipal(evento: Event): void", "elegirSecundario(evento: Event): void", "guardarColores(): void",
      "restablecerColores(): void", "elegirLogo(evento: Event): void", "quitarLogo(): void"]},

  # ======================= INTERFACES (movil Flutter) =======================
  "PantallaLogin": {"tipo": "interfaz", "origen": M+"features/auth/pantalla_login.dart",
    "nota": "El metodo vive en _PantallaLoginState. Recuerda el slug en SharedPreferences.",
    "atributos": [], "operaciones": ["_entrar(): Future<void>"]},
  "PantallaRegistro": {"tipo": "interfaz", "origen": M+"features/auth/pantalla_registro.dart",
    "nota": "El metodo vive en _PantallaRegistroState. Llama directo a RepositorioAuth.registrar() (no hay Notifier) y al terminar lleva al login. El movil NO tiene el 4b (usar la cuenta existente).",
    "atributos": [], "operaciones": ["_registrar(): Future<void>"]},

  # ======================= CONTROLES (web Angular) =======================
  "PlataformaService": {"tipo": "control", "origen": W+"core/services/plataforma.service.ts",
    "atributos": [],
    "operaciones": ["listarEmpresas(busqueda?: string): Observable<Empresa[]>", "planes(): Observable<PlanOferta[]>",
      "listarPlanes(): Observable<Plan[]>", "funcionesDePlan(): Observable<FuncionDePlan[]>",
      "crearPlan(datos: PlanGuardar): Observable<PlanGuardado>", "editarPlan(id: number, datos: PlanGuardar): Observable<PlanGuardado>",
      "cambiarEstadoPlan(id: number, activo: boolean): Observable<Plan>", "ciudades(): Observable<Ciudad[]>",
      "obtenerEmpresa(id: number): Observable<Empresa>", "crearEmpresa(datos: EmpresaCrear): Observable<EmpresaCreada>",
      "editarEmpresa(id: number, datos: EmpresaEditar): Observable<Empresa>", "cambiarEstado(id: number, activa: boolean): Observable<Empresa>",
      "suscripciones(empresaId: number): Observable<SuscripcionesEmpresa>",
      "asignarPlan(empresaId: number, datos: AsignarPlan): Observable<SuscripcionGuardada>",
      "accionSuscripcion(empresaId: number, accion: 'renovar' | 'suspender' | 'reactivar'): Observable<SuscripcionGuardada>",
      "marcarVencidas(): Observable<Vencimiento>", "traducir(e: HttpErrorResponse): Observable<never>"]},
  "MiPlanService": {"tipo": "control", "origen": W+"core/services/mi-plan.service.ts",
    "atributos": [], "operaciones": ["consultar(): Observable<MiPlan>", "traducir(error: HttpErrorResponse): ErrorMiPlan"]},
  "AuthService": {"tipo": "control", "origen": W+"core/services/auth.service.ts",
    "nota": "Solo lo del CU-06 y el CU-07; la recuperacion de contrasena (solicitarRecuperacion, confirmarRecuperacion) es de otro CU.",
    "atributos": ["usuario: Signal<UsuarioAutenticado | null>", "autenticado: Signal<boolean>", "rol: Signal<string | null>"],
    "operaciones": ["registrar(datos: ClienteRegistroIn): Observable<ClienteRegistradoOut>",
      "asociarCuentaExistente(datos: LoginIn): Observable<UsuarioAutenticado>", "iniciarSesion(datos: LoginIn): Observable<UsuarioAutenticado>",
      "cerrarSesion(): void", "restaurarSesion(): Observable<UsuarioAutenticado | null>", "inicioDelRol(): string",
      "guardarToken(token: string): void", "borrarToken(): void", "recordarSinRed(usuario: UsuarioAutenticado): void",
      "traducirRegistro(error: HttpErrorResponse): ErrorRegistro", "traducirLogin(error: HttpErrorResponse): ErrorLogin"]},
  "UsuariosService": {"tipo": "control", "origen": W+"core/services/usuarios.service.ts",
    "atributos": [], "operaciones": ["roles(): Observable<RolAsignable[]>", "listar(filtros: FiltrosUsuarios): Observable<PaginaUsuarios>",
      "crear(datos: UsuarioCrear): Observable<UsuarioResumen>", "editar(id: number, datos: UsuarioEditar): Observable<UsuarioResumen>",
      "cambiarEstado(id: number, activo: boolean): Observable<UsuarioResumen>", "eliminar(id: number): Observable<void>",
      "traducir(error: HttpErrorResponse): ErrorUsuarios"]},
  "OrganizacionService": {"tipo": "control", "origen": W+"core/services/organizacion.service.ts",
    "nota": "Solo lo de sucursales; las ciudades (crearCiudad, editarCiudad, eliminarCiudad) son de la plataforma. traducir() reconoce primero el rechazo del plan (CU-05).",
    "atributos": [], "operaciones": ["sucursales(): Observable<SucursalBreve[]>", "listarCiudades(busqueda?: string): Observable<Ciudad[]>",
      "listarSucursales(filtros: FiltrosSucursales): Observable<Sucursal[]>", "crearSucursal(datos: SucursalCrear): Observable<Sucursal>",
      "editarSucursal(id: number, datos: SucursalEditar): Observable<Sucursal>",
      "cambiarEstadoSucursal(id: number, activa: boolean): Observable<Sucursal>", "traducir(error: HttpErrorResponse): ErrorOrganizacion"]},
  "EmpleadosService": {"tipo": "control", "origen": W+"core/services/empleados.service.ts",
    "atributos": [], "operaciones": ["listar(filtros: FiltrosEmpleados): Observable<Empleado[]>",
      "usuariosVinculables(): Observable<UsuarioVinculable[]>", "crear(datos: EmpleadoCrear): Observable<Empleado>",
      "editar(id: number, datos: EmpleadoEditar): Observable<Empleado>", "darDeBaja(id: number, fecha_baja?: string): Observable<Empleado>",
      "traducir(error: HttpErrorResponse): ErrorEmpleados"]},
  "ContratacionService": {"tipo": "control", "origen": W+"core/services/contratacion.service.ts",
    "atributos": [], "operaciones": ["planes(): Observable<PlanPublico[]>", "ciudades(): Observable<CiudadPublica[]>",
      "verificarSlug(valor: string): Observable<SlugVerificado>", "contratar(datos: Contratar): Observable<Contratacion>",
      "traducir(e: HttpErrorResponse): Observable<never>"]},
  "MiTiendaService": {"tipo": "control", "origen": W+"core/services/mi-tienda.service.ts",
    "atributos": [], "operaciones": ["obtener(): Observable<MarcaEmpresa>", "guardarColores(colores: ColoresMarca): Observable<MarcaEmpresa>",
      "subirLogo(archivo: File): Observable<MarcaEmpresa>", "quitarLogo(): Observable<MarcaEmpresa>",
      "fallar(error: HttpErrorResponse): Observable<never>", "traducir(error: HttpErrorResponse): ErrorMiTienda"]},
  "MarcaService": {"tipo": "control", "origen": W+"core/services/marca.service.ts",
    "nota": "Es la 'TiendaEnLinea' de la robustez: pide GET /tienda/marca y pone los colores en las variables CSS de :root.",
    "atributos": ["logo: Signal<string | null>", "empresa: Signal<string | null>"],
    "operaciones": ["cargar(): void", "aplicar(principal: string | null, secundario: string | null): void"]},

  # ======================= CONTROLES (movil Flutter) =======================
  "ControlSesion": {"tipo": "control", "origen": M+"features/auth/estado_sesion.dart",
    "nota": "Notifier<EstadoSesion> (sesionProvider). Habla con el backend por RepositorioAuth (data/repositorios/repositorio_auth.dart) y guarda el token con AlmacenSeguro.",
    "atributos": ["state: EstadoSesion", "_almacen: AlmacenSeguro", "_repositorio: RepositorioAuth"],
    "operaciones": ["build(): EstadoSesion", "restaurar(): Future<void>", "iniciarSesion({empresa, correo, contrasena}): Future<void>",
      "cerrarSesion(): Future<void>", "cerrarPorCambioDeContrasena(): Future<void>", "cerrarPorTokenInvalido(): Future<void>"]},
  "RepositorioAuth": {"tipo": "control", "origen": M+"data/repositorios/repositorio_auth.dart",
    "nota": "Cliente HTTP (Dio) de /auth. En el CU-07 es el unico control del movil: la pantalla lo llama directo.",
    "atributos": ["_dio: Dio"],
    "operaciones": ["registrar(datos: DatosRegistro): Future<void>", "iniciarSesion({empresa, correo, contrasena}): Future<Token>",
      "cerrarSesion(): Future<void>", "usuarioActual(): Future<UsuarioAutenticado>"]},

  # ======================= CONTROLES (backend) =======================
  "plataforma_service": {"tipo": "control", "origen": B+"plataforma/service.py",
    "nota": "GestorEmpresas de la robustez. Modulo de funciones. Rutas en plataforma/router.py (todas exigen ADMIN_PLATAFORMA): GET /plataforma/empresas, POST /plataforma/empresas, GET/PATCH /plataforma/empresas/{id}, POST /plataforma/empresas/{id}/baja y /reactivar. crear_empresa usa suscripciones.registrar_pago, core/tenencia.py fijar_empresa/modo_plataforma, core/security.py hash_password e integrations/correo.py enviar (el correo va despues del commit).",
    "atributos": [],
    "operaciones": ["listar_empresas(db, busqueda): list[EmpresaOut]", "obtener_empresa(db, empresa_id): EmpresaOut",
      "_resumenes(db, empresas): list[EmpresaOut]", "_contrasena_temporal(): str",
      "_correo_de_bienvenida(empresa, correo): Mensaje", "_correo_de_acceso(empresa, correo, clave): Mensaje",
      "crear_empresa(db, datos: EmpresaCrearIn, contrasena, comprobante): EmpresaCreadaOut",
      "editar_empresa(db, empresa_id, datos: EmpresaEditarIn): EmpresaOut", "cambiar_estado(db, empresa_id, activa): EmpresaOut"]},
  "plataforma_planes": {"tipo": "control", "origen": B+"plataforma/planes.py",
    "nota": "GestorPlanes de la robustez. Rutas: GET /plataforma/planes, GET /plataforma/planes/funciones, POST /plataforma/planes, GET/PUT /plataforma/planes/{id}, POST /plataforma/planes/{id}/desactivar y /activar.",
    "atributos": [],
    "operaciones": ["listar_planes(db, incluir_inactivos): list[PlanOut]", "listar_funciones(): list[FuncionOut]", "obtener_plan(db, plan_id): PlanOut",
      "crear_plan(db, datos: PlanIn): PlanGuardadoOut", "editar_plan(db, plan_id, datos: PlanIn): PlanGuardadoOut",
      "cambiar_estado(db, plan_id, activo): PlanOut", "_empresas_por_plan(db): dict[int, int]", "_salida(plan, empresas): PlanOut",
      "_obtener(db, plan_id): Plan", "_codigo_desde(nombre): str", "_codigo_libre(db, base): str", "_validar_nombre(db, nombre, salvo): None",
      "_aplicar(plan, datos): None", "_excedidas(db, plan): list[EmpresaExcedidaOut]",
      "excedidas_en(db, plan, empresas): list[EmpresaExcedidaOut]", "_guardado(db, plan): PlanGuardadoOut"]},
  "plataforma_suscripciones": {"tipo": "control", "origen": B+"plataforma/suscripciones.py",
    "nota": "GestorSuscripciones de la robustez (lo dice su docstring). Rutas: GET/POST /plataforma/empresas/{id}/suscripciones, POST .../suscripciones/renovar, /suspender, /reactivar y POST /plataforma/suscripciones/vencimiento (E1).",
    "atributos": [],
    "operaciones": ["obtener(db, empresa_id): SuscripcionesOut", "asignar_plan(db, empresa_id, datos: AsignarPlanIn): SuscripcionGuardadaOut",
      "renovar(db, empresa_id): SuscripcionGuardadaOut", "cambiar_estado(db, empresa_id, suspender): SuscripcionGuardadaOut",
      "marcar_vencidas(db): VencimientoOut", "registrar_pago(db, suscripcion, plan, concepto, comprobante): PagoSimulado",
      "monto_de(plan): Decimal", "nuevo_comprobante(): str", "estado_efectivo(suscripcion, hoy): str", "_empresa(db, empresa_id): Empresa",
      "_actual(db, empresa_id): Suscripcion | None", "_suscripcion_out(s, hoy): SuscripcionOut", "_pago_out(p): PagoSimuladoOut",
      "_guardado(db, empresa, pago, excedidas): SuscripcionGuardadaOut", "_confirmar(db): None"]},
  "mi_plan_service": {"tipo": "control", "origen": B+"plataforma/mi_plan/service.py",
    "nota": "GestorConsumoPlan de la robustez. Ruta: GET /plataforma/mi-plan (mi_plan/router.py, rol ADMINISTRADOR). Consulta por mi_plan/repository.py.",
    "atributos": [],
    "operaciones": ["consultar_mi_plan(db, empresa_id): MiPlanOut", "_detalle(codigo, valor): tuple[bool, str | None]",
      "_funciones(plan): list[FuncionOut]", "_plan(plan): PlanOut", "_limite(codigo, etiqueta, usado, limite): LimiteOut",
      "_suscripcion(suscripcion): SuscripcionOut"]},
  "plataforma_verificador": {"tipo": "control", "origen": B+"plataforma/verificador.py",
    "nota": "VerificadorPlan de la robustez (lo dice su docstring). El rechazo es la excepcion RechazoDelPlan (SinSuscripcionVigente para el 2a) y lo responde como 403 el manejador _rechazo_del_plan de app/main.py con cuerpo() = {detail, codigo: plan_limit | sin_suscripcion, limite, uso}.",
    "atributos": ["FUNCIONES: dict[str, str]", "LIMITES: dict[str, Limite]", "CUPOS: dict[str, tuple[str, str]]"],
    "operaciones": ["suscripcion_vigente(db): Suscripcion | None", "plan_vigente(db): Plan", "incluye(db, funcion): bool",
      "dias_de_bitacora(db): int | None", "verificar_funcion(db, funcion): None", "verificar_limite(db, recurso): None",
      "uso_del_mes(db, cupo): int", "verificar_cupo(db, cupo): None", "consumir_cupo(db, cupo): int",
      "_contar_sucursales(db): int", "_contar_empleados(db): int", "_periodo(): date"]},
  "core_dependencies": {"tipo": "control", "origen": C+"dependencies.py",
    "nota": "Dependencias de FastAPI. requiere_funcion/limite/cupo devuelven un _verificar(usuario, db) que llama al verificador (la plataforma queda exenta). get_usuario_actual valida el token contra sesion_token y usuario, fija el RLS (core/tenencia.py fijar_contexto_de_usuario) y llama a _exigir_suscripcion_para_escribir (CU-05 2a para toda escritura).",
    "atributos": [],
    "operaciones": ["get_usuario_actual(peticion: Request, token: str, db: Session): UsuarioActual",
      "_exigir_suscripcion_para_escribir(peticion: Request, db: Session, usuario: UsuarioActual): None",
      "requiere_funcion(funcion: str)", "requiere_limite(recurso: str)", "requiere_cupo(cupo: str)", "requiere_roles(*roles: str)"]},
  "contratacion_service": {"tipo": "control", "origen": B+"plataforma/contratacion/service.py",
    "nota": "GestorContratacion de la robustez. Rutas PUBLICAS en contratacion/router.py: GET /contratar/planes, GET /contratar/ciudades, GET /contratar/slug, POST /contratar. El alta la delega en plataforma/service.py crear_empresa (importado como gestor_empresas).",
    "atributos": [],
    "operaciones": ["listar_planes(db): list[PlanPublicoOut]", "listar_ciudades(db): list[CiudadPublicaOut]",
      "verificar_slug(db, slug): SlugOut", "contratar(db, datos: ContratarIn): ContratacionOut", "_ocupados(db, candidatos): set[str]",
      "_sugerir(db, slug): list[str]", "_cobrar(datos: ContratarIn): str"]},
  "mi_tienda_service": {"tipo": "control", "origen": B+"plataforma/mi_tienda/service.py",
    "nota": "GestorMarca de la robustez. Rutas en mi_tienda/router.py (rol ADMINISTRADOR): GET /plataforma/mi-tienda, PUT /plataforma/mi-tienda/colores, POST y DELETE /plataforma/mi-tienda/logo (las tres con requiere_funcion('marca_propia')); y la publica GET /tienda/marca.",
    "atributos": ["FUNCION: str = 'marca_propia'"],
    "operaciones": ["obtener_marca(db, empresa_id): MarcaOut", "guardar_colores(db, empresa_id, datos: ColoresIn): MarcaOut",
      "guardar_logo(db, empresa_id, contenido: bytes): MarcaOut", "quitar_logo(db, empresa_id): MarcaOut",
      "marca_de_la_tienda(db): MarcaTiendaOut", "_empresa(db, empresa_id): Empresa", "_incluida(db): bool", "_url(ruta): str | None",
      "_marca(db, empresa): MarcaOut", "_guardar_archivo(contenido, empresa_id, formato): str"]},
  "catalogo_imagenes_almacen": {"tipo": "control", "origen": B+"catalogo/imagenes_almacen.py",
    "nota": "Del catalogo; el CU-12 lo reusa para validar (4a) y borrar el logo. inspeccionar() lanza ErrorDeArchivo (ArchivoVacio, ArchivoDemasiadoGrande, FormatoNoAdmitido, ImagenDemasiadoGrande).",
    "atributos": [], "operaciones": ["inspeccionar(contenido: bytes): DatosDeImagen", "borrar(ruta: str): None", "url_de(ruta: str): str"]},
  "seguridad_service": {"tipo": "control", "origen": B+"seguridad/service.py",
    "nota": "GestorAutenticacion, GestorRegistro y GestorUsuarios de la robustez. Solo las funciones de los CU-06, 07 y 08 (no el perfil ni la recuperacion). Rutas en seguridad/router.py: POST /auth/registro, POST /auth/registro/asociar, POST /auth/login, POST /auth/logout, GET /auth/roles, y admin_router /usuarios (GET, POST, GET/PATCH/DELETE /{id}, PATCH /{id}/estado). Usa core/security.py hash_password, verify_password y crear_access_token.",
    "atributos": [],
    "operaciones": ["registrar_cliente(db, datos: ClienteRegistroIn): ClienteRegistradoOut", "asociar_cuenta_existente(db, datos: LoginIn): TokenOut",
      "autenticar(db, datos: LoginIn): TokenOut", "_autenticar_en_la_plataforma(db, datos: LoginIn): TokenOut",
      "_emitir(db, usuario, empresa): TokenOut", "_autenticado(db, usuario, empresa, sucursal_id): UsuarioAutenticadoOut",
      "cerrar_sesion(db, jti: UUID): None", "_viola(exc, tabla, columna): bool",
      "listar_roles(db): list[RolOut]", "listar_usuarios(db, empresa_id, busqueda, rol, activo, pagina, tamano): PaginaUsuarios",
      "obtener_usuario(db, usuario_id, empresa_id): UsuarioResumenOut", "_personal_de_la_empresa(db, usuario_id, empresa_id): Usuario",
      "_validar_ambito(db, rol_nombre, sucursal_id): None", "crear_usuario(db, datos: UsuarioCrearIn, empresa_id): UsuarioResumenOut",
      "editar_usuario(db, usuario_id, datos: UsuarioEditarIn, empresa_id): UsuarioResumenOut",
      "cambiar_estado(db, usuario_id, activo, solicitante_id, empresa_id): UsuarioResumenOut",
      "eliminar_usuario(db, usuario_id, solicitante_id, empresa_id): None", "_fila_a_resumen(fila): UsuarioResumenOut"]},
  "organizacion_service": {"tipo": "control", "origen": B+"organizacion/service.py",
    "nota": "GestorOrganizacion de la robustez. Rutas en organizacion/router.py (rol ADMINISTRADOR): GET/POST /organizacion/sucursales, GET/PATCH /organizacion/sucursales/{id}, PATCH /organizacion/sucursales/{id}/estado; GET /organizacion/ciudades. El limite NO va por dependencia: crear_sucursal y cambiar_estado_sucursal llaman a verificador.verificar_limite(db, 'sucursales').",
    "atributos": [],
    "operaciones": ["listar_sucursales(db, busqueda, ciudad_id, activa): list[SucursalOut]", "obtener_sucursal(db, sucursal_id): SucursalOut",
      "crear_sucursal(db, datos: SucursalCrearIn): SucursalOut", "editar_sucursal(db, sucursal_id, datos: SucursalEditarIn): SucursalOut",
      "cambiar_estado_sucursal(db, sucursal_id, activa): SucursalOut", "listar_ciudades(db, busqueda): list[CiudadOut]",
      "_fila_a_sucursal(fila): SucursalOut", "_viola(exc, restriccion): bool"]},
  "empleados_service": {"tipo": "control", "origen": B+"organizacion/empleados/service.py",
    "nota": "GestorEmpleados de la robustez. Rutas en organizacion/empleados/router.py (rol ADMINISTRADOR): GET /organizacion/empleados, GET /cargos, GET /usuarios-vinculables, POST (con Depends(requiere_limite('empleados'))), GET/PATCH /{id}, PATCH /{id}/baja. Revoca sesiones con seguridad/repository.py revocar_sesiones_de_usuario.",
    "atributos": [],
    "operaciones": ["listar_empleados(db, busqueda, sucursal_id, cargo, activo): list[EmpleadoOut]", "obtener_empleado(db, empleado_id): EmpleadoOut",
      "listar_usuarios_vinculables(db, empresa_id): list[UsuarioVinculableOut]", "_validar_sucursal(db, sucursal_id): None",
      "crear_empleado(db, datos: EmpleadoCrearIn, empresa_id): EmpleadoOut", "editar_empleado(db, empleado_id, datos: EmpleadoEditarIn): EmpleadoOut",
      "dar_de_baja(db, empleado_id, datos: BajaEmpleadoIn): EmpleadoOut", "_fila_a_empleado(fila): EmpleadoOut", "_viola(exc, restriccion): bool"]},
  "BitacoraMiddleware": {"tipo": "control", "origen": B+"bitacora/middleware.py",
    "nota": "Anota toda peticion POST/PUT/PATCH/DELETE (y las exportaciones GET), tambien las rechazadas (accion *_RECHAZADO, p. ej. un 403 plan_limit). /auth/login queda como INICIAR_SESION o INTENTO_FALLIDO y /auth/logout como CERRAR_SESION. _anotar llama a bitacora/service.py registrar(db, accion, metodo, ruta, estado_http, exito, usuario_id, actor, rol, entidad, entidad_id, ip, agente, detalle), que inserta con bitacora/repository.py agregar(db, **campos). Los GET no se anotan.",
    "atributos": [], "operaciones": ["dispatch(peticion: Request, siguiente): Response", "_anotar(peticion: Request, respuesta): None"]},

  # ======================= ENTIDADES (PostgreSQL) =======================
  "Empresa": {"tipo": "entidad", "origen": B+"plataforma/models.py", "tabla": "empresa",
    "nota": OMIT_AUD + " Sin RLS (es de la plataforma). " + SIN_REPO,
    "atributos": ["id: BIGINT (PK)", "nombre: VARCHAR(120)", "razon_social: VARCHAR(160)", "nit: VARCHAR(30)", "slug: VARCHAR(40) (UNIQUE)",
      "correo_contacto: VARCHAR(120)", "estado: VARCHAR(10)", "logo: VARCHAR(255)", "color_principal: VARCHAR(7)", "color_secundario: VARCHAR(7)"],
    "operaciones": ["obtener_empresa(db, empresa_id): Empresa | None  [plataforma/mi_plan/repository.py]",
      "obtener_empresa(db, empresa_id): Empresa | None  [seguridad/repository.py]",
      "obtener_empresa_por_slug(db, slug): Empresa | None  [seguridad/repository.py]",
      "estado_de_empresa(db, empresa_id): str | None  [seguridad/repository.py]",
      "_empresa(db, empresa_id): Empresa  [plataforma/suscripciones.py]",
      "_empresa(db, empresa_id): Empresa  [plataforma/mi_tienda/service.py]",
      "_ocupados(db, candidatos): set[str]  [plataforma/contratacion/service.py]"]},
  "Plan": {"tipo": "entidad", "origen": B+"plataforma/models.py", "tabla": "plan",
    "nota": OMIT_AUD + " Sin RLS. max_* y cupo_* en NULL = ilimitado; funciones guarda las funciones (true/false) y bitacora_dias. " + SIN_REPO,
    "atributos": ["id: SMALLINT (PK)", "codigo: VARCHAR(20) (UNIQUE)", "nombre: VARCHAR(40) (UNIQUE)", "precio_mensual: NUMERIC(10,2)",
      "duracion_dias: SMALLINT", "max_sucursales: INTEGER", "max_empleados: INTEGER", "cupo_reportes_ia: INTEGER", "cupo_fotos_ia: INTEGER",
      "funciones: JSONB", "activo: BOOLEAN"],
    "operaciones": ["listar_planes_activos(db): list[Plan]  [plataforma/mi_plan/repository.py]",
      "_obtener(db, plan_id): Plan  [plataforma/planes.py]", "_codigo_libre(db, base): str  [plataforma/planes.py]",
      "_validar_nombre(db, nombre, salvo): None  [plataforma/planes.py]", "plan_vigente(db): Plan  [plataforma/verificador.py]"]},
  "Suscripcion": {"tipo": "entidad", "origen": B+"plataforma/models.py", "tabla": "suscripcion",
    "nota": OMIT_AUD + " Con RLS. Indice unico parcial uq_suscripcion_vigente_por_empresa: una sola VIGENTE o SUSPENDIDA por empresa (RN-02). " + SIN_REPO,
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "plan_id: SMALLINT (FK plan)", "inicio: DATE", "vencimiento: DATE",
      "estado: VARCHAR(12)"],
    "operaciones": ["obtener_suscripcion_actual(db): Suscripcion | None  [plataforma/mi_plan/repository.py]",
      "suscripcion_vigente(db): Suscripcion | None  [plataforma/verificador.py]",
      "_actual(db, empresa_id): Suscripcion | None  [plataforma/suscripciones.py]",
      "_empresas_por_plan(db): dict[int, int]  [plataforma/planes.py]"]},
  "PagoSimulado": {"tipo": "entidad", "origen": B+"plataforma/models.py", "tabla": "pago_simulado",
    "nota": "Sin Auditoria. concepto: ALTA | CAMBIO | RENOVACION. " + SIN_REPO,
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "suscripcion_id: BIGINT (FK suscripcion)", "plan_id: SMALLINT (FK plan)",
      "concepto: VARCHAR(12)", "monto: NUMERIC(10,2)", "comprobante: VARCHAR(24) (UNIQUE)", "pagado_en: TIMESTAMPTZ"],
    "operaciones": ["registrar_pago(db, suscripcion, plan, concepto, comprobante): PagoSimulado  [plataforma/suscripciones.py]"]},
  "ConsumoCupo": {"tipo": "entidad", "origen": B+"plataforma/models.py", "tabla": "consumo_cupo",
    "nota": "Sin Auditoria. PK compuesta (empresa_id, recurso, periodo); periodo = primer dia del mes en hora de Bolivia. " + SIN_REPO,
    "atributos": ["empresa_id: BIGINT (PK, FK empresa)", "recurso: VARCHAR(20) (PK)", "periodo: DATE (PK)", "usados: INTEGER"],
    "operaciones": ["uso_del_mes(db, cupo): int  [plataforma/verificador.py]", "consumir_cupo(db, cupo): int  [plataforma/verificador.py]"]},
  "ClienteEmpresa": {"tipo": "entidad", "origen": B+"plataforma/models.py", "tabla": "cliente_empresa",
    "nota": "Sin Auditoria. PK compuesta (cliente_id, empresa_id); empresa_id toma DEFAULT app_empresa_actual() (la empresa del contexto). Con RLS.",
    "atributos": ["cliente_id: BIGINT (PK, FK cliente, ON DELETE CASCADE)", "empresa_id: BIGINT (PK, FK empresa)", "creado_en: TIMESTAMPTZ"],
    "operaciones": ["agregar_cliente(db, usuario_id, documento, telefono): Cliente  [seguridad/repository.py, inserta ClienteEmpresa]",
      "asociar_cliente_a_la_empresa(db, usuario_id): None  [seguridad/repository.py]"]},
  "Usuario": {"tipo": "entidad", "origen": B+"seguridad/models.py", "tabla": "usuario",
    "nota": OMIT_AUD + " Sin RLS (tabla de identidad). empresa_id es NULL para el cliente (RN-13) y el administrador de la plataforma. Correo unico por empresa (uq_usuario_empresa_correo) y unico entre los sin empresa (uq_usuario_correo_sin_empresa).",
    "atributos": ["id: BIGINT (PK)", "correo: VARCHAR(120)", "hash_contrasena: VARCHAR(255)", "nombres: VARCHAR(80)", "apellidos: VARCHAR(80)",
      "rol_id: SMALLINT (FK rol)", "activo: BOOLEAN", "empresa_id: BIGINT (FK empresa)"],
    "operaciones": ["obtener_usuario_por_correo(db, correo, empresa_id): Usuario | None  [seguridad/repository.py]",
      "agregar_usuario(db, correo, hash_contrasena, nombres, apellidos, rol_id, empresa_id): Usuario  [seguridad/repository.py]",
      "obtener_usuario_con_rol(db, correo, empresa_id): Usuario | None  [seguridad/repository.py]",
      "obtener_usuario_con_id(db, usuario_id): Usuario | None  [seguridad/repository.py]",
      "contar_y_listar_usuarios(db, empresa_id, busqueda, rol, activo, pagina, tamano): tuple[int, list[Row]]  [seguridad/repository.py]",
      "obtener_detalle_usuario(db, usuario_id, empresa_id): Row | None  [seguridad/repository.py]",
      "tiene_operaciones_asociadas(db, usuario_id): bool  [seguridad/repository.py]",
      "eliminar_usuario(db, usuario): None  [seguridad/repository.py]",
      "listar_usuarios_vinculables(db, empresa_id): list[Row]  [organizacion/empleados/repository.py]",
      "obtener_usuario_vinculable(db, usuario_id, empresa_id): Usuario | None  [organizacion/empleados/repository.py]",
      "obtener_usuario_por_correo(db, correo, empresa_id): Usuario | None  [organizacion/empleados/repository.py]",
      "agregar_usuario(db, correo, hash_contrasena, nombres, apellidos, rol_id, empresa_id): Usuario  [organizacion/empleados/repository.py]",
      "obtener_usuario(db, usuario_id): Usuario | None  [organizacion/empleados/repository.py]"]},
  "Cliente_BD": {"tipo": "entidad", "origen": B+"seguridad/models.py", "tabla": "cliente",
    "nota": "En el codigo la clase se llama `Cliente` (tabla cliente); se renombra aca para no chocar con el actor Cliente en el mismo diagrama. " + OMIT_AUD,
    "atributos": ["id: BIGINT (PK)", "usuario_id: BIGINT (FK usuario, UNIQUE, ON DELETE CASCADE)", "documento: VARCHAR(20) (UNIQUE)",
      "telefono: VARCHAR(20)", "talla_superior: VARCHAR(10)", "talla_inferior: VARCHAR(10)"],
    "operaciones": ["agregar_cliente(db, usuario_id, documento, telefono): Cliente  [seguridad/repository.py]",
      "obtener_cliente_de_usuario(db, usuario_id): Cliente | None  [seguridad/repository.py]",
      "existe_cliente_con_documento(db, documento): bool  [seguridad/repository.py]"]},
  "Rol": {"tipo": "entidad", "origen": B+"seguridad/models.py", "tabla": "rol",
    "nota": "Sin Auditoria y sin RLS (los roles son de la plataforma).",
    "atributos": ["id: SMALLINT (PK)", "nombre: VARCHAR(30) (UNIQUE)", "descripcion: VARCHAR(150)"],
    "operaciones": ["obtener_rol_por_nombre(db, nombre): Rol | None  [seguridad/repository.py]", "listar_roles(db): list[Rol]  [seguridad/repository.py]",
      "obtener_rol_por_nombre(db, nombre): Rol | None  [organizacion/empleados/repository.py]"]},
  "SesionToken": {"tipo": "entidad", "origen": B+"seguridad/models.py", "tabla": "sesion_token",
    "nota": "Sin Auditoria: sus fechas son las de su ciclo de vida. get_usuario_actual (core/dependencies.py) la consulta por jti en cada peticion.",
    "atributos": ["id: BIGINT (PK)", "usuario_id: BIGINT (FK usuario, ON DELETE CASCADE)", "jti: UUID (UNIQUE)", "emitido_en: TIMESTAMPTZ",
      "expira_en: TIMESTAMPTZ", "revocado_en: TIMESTAMPTZ"],
    "operaciones": ["agregar_sesion(db, usuario_id, jti, expira_en): SesionToken  [seguridad/repository.py]",
      "obtener_sesion_por_jti(db, jti): SesionToken | None  [seguridad/repository.py]",
      "revocar_sesion(db, jti): int  [seguridad/repository.py]", "revocar_sesiones_de_usuario(db, usuario_id): int  [seguridad/repository.py]"]},
  "Sucursal": {"tipo": "entidad", "origen": B+"organizacion/models.py", "tabla": "sucursal",
    "nota": OMIT_AUD + " UNIQUE (empresa_id, ciudad_id, nombre) = uq_sucursal_ciudad_nombre; CHECK horario_cierre > horario_apertura.",
    "atributos": ["id: INTEGER (PK)", "empresa_id: BIGINT (FK empresa)", "ciudad_id: INTEGER (FK ciudad)", "nombre: VARCHAR(80)", "direccion: VARCHAR(200)",
      "telefono: VARCHAR(20)", "horario_apertura: TIME", "horario_cierre: TIME", "capacidad_vestidores: SMALLINT", "activa: BOOLEAN"],
    "operaciones": ["listar_sucursales(db, busqueda, ciudad_id, activa): list[Row]  [organizacion/repository.py]",
      "obtener_sucursal_con_ciudad(db, sucursal_id): Row | None  [organizacion/repository.py]",
      "obtener_sucursal(db, sucursal_id): Sucursal | None  [organizacion/repository.py]",
      "existe_sucursal_con_nombre(db, ciudad_id, nombre, excepto_id): bool  [organizacion/repository.py]",
      "agregar_sucursal(db, ciudad_id, nombre, direccion, telefono, horario_apertura, horario_cierre, capacidad_vestidores, activa): Sucursal  [organizacion/repository.py]",
      "existe_sucursal_activa(db, sucursal_id): bool  [seguridad/repository.py]",
      "nombre_de_sucursal(db, sucursal_id): str | None  [seguridad/repository.py]",
      "obtener_sucursal_activa(db, sucursal_id): Sucursal | None  [organizacion/empleados/repository.py]",
      "existe_sucursal(db, sucursal_id): bool  [organizacion/empleados/repository.py]",
      "contar_sucursales_activas(db): int  [plataforma/mi_plan/repository.py]",
      "_contar_sucursales(db): int  [plataforma/verificador.py]"]},
  "Ciudad": {"tipo": "entidad", "origen": B+"organizacion/models.py", "tabla": "ciudad",
    "nota": OMIT_AUD + " Compartida por todas las empresas (sin empresa_id ni RLS).",
    "atributos": ["id: INTEGER (PK)", "nombre: VARCHAR(60) (UNIQUE)", "departamento: VARCHAR(60)"],
    "operaciones": ["listar_ciudades(db, busqueda): list[Row]  [organizacion/repository.py]",
      "obtener_ciudad(db, ciudad_id): Ciudad | None  [organizacion/repository.py]"]},
  "Empleado": {"tipo": "entidad", "origen": B+"organizacion/models.py", "tabla": "empleado",
    "nota": OMIT_AUD + " cargo: ENCARGADO | CAJERO (CHECK). UNIQUE (empresa_id, documento) = uq_empleado_documento. Activo = fecha_baja IS NULL (lo que cuenta el limite).",
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "usuario_id: BIGINT (FK usuario, UNIQUE)", "sucursal_id: INTEGER (FK sucursal)",
      "documento: VARCHAR(20)", "telefono: VARCHAR(20)", "cargo: VARCHAR(30)", "fecha_ingreso: DATE", "fecha_baja: DATE"],
    "operaciones": ["listar_empleados(db, busqueda, sucursal_id, cargo, activo): list[Row]  [organizacion/empleados/repository.py]",
      "obtener_empleado_con_detalle(db, empleado_id): Row | None  [organizacion/empleados/repository.py]",
      "obtener_empleado(db, empleado_id): Empleado | None  [organizacion/empleados/repository.py]",
      "existe_documento(db, documento, excepto_empleado_id): bool  [organizacion/empleados/repository.py]",
      "agregar_empleado(db, usuario_id, sucursal_id, documento, telefono, cargo, fecha_ingreso): Empleado  [organizacion/empleados/repository.py]",
      "obtener_sucursal_de_usuario(db, usuario_id): int | None  [seguridad/repository.py]",
      "obtener_empleado_de_usuario(db, usuario_id): Empleado | None  [seguridad/repository.py]",
      "agregar_empleado(db, usuario_id, sucursal_id, documento, cargo, fecha_ingreso): Empleado  [seguridad/repository.py]",
      "contar_empleados_activos(db): int  [plataforma/mi_plan/repository.py]",
      "_contar_empleados(db): int  [plataforma/verificador.py]"]},
  "AsientoBitacora": {"tipo": "entidad", "origen": B+"bitacora/models.py", "tabla": "bitacora",
    "nota": "empresa_id es NULL en lo que hace la plataforma (ninguna empresa lo ve).",
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "ocurrido_en: TIMESTAMPTZ", "usuario_id: BIGINT (FK usuario, ON DELETE SET NULL)",
      "actor: VARCHAR(160)", "rol: VARCHAR(40)", "accion: VARCHAR(40)", "entidad: VARCHAR(60)", "entidad_id: VARCHAR(60)", "metodo: VARCHAR(10)",
      "ruta: VARCHAR(300)", "estado_http: INTEGER", "exito: BOOLEAN", "ip: VARCHAR(60)", "agente: VARCHAR(200)", "detalle: JSONB"],
    "operaciones": ["agregar(db, **campos): AsientoBitacora", "contar(db, **filtros): int", "listar(db, limite, desplazamiento, **filtros): list[tuple]",
      "acciones(db): list[str]", "roles(db): list[str]", "entidades(db): list[str]", "ultimo(db): AsientoBitacora | None"]},
}
# CU-06: el actor 'Usuario' chocaria con la entidad Usuario en el mismo diagrama -> se usa el alias real del codigo.
clases["UsuarioDB"] = dict(clases["Usuario"], nota="Es la entidad Usuario (tabla usuario); se nombra con el alias de core/dependencies.py "
    "(`from app.modules.seguridad.models import Usuario as UsuarioDB`) para no chocar con el actor Usuario. " + clases["Usuario"]["nota"])

# FK reales (multiplicidad: primero en el extremo ClaseA, despues en ClaseB)
FK = [
  ["Empresa","Suscripcion","TIENE","1","0..*"],
  ["Plan","Suscripcion","SE_CONTRATA_EN","1","0..*"],
  ["Suscripcion","PagoSimulado","SE_PAGA_CON","1","0..*"],
  ["Plan","PagoSimulado","SE_COBRA_EN","1","0..*"],
  ["Empresa","PagoSimulado","PAGA","1","0..*"],
  ["Empresa","ConsumoCupo","CONSUME","1","0..*"],
  ["Empresa","Sucursal","TIENE","1","0..*"],
  ["Empresa","Empleado","EMPLEA","1","0..*"],
  ["Empresa","Usuario","AGRUPA","0..1","0..*"],
  ["Empresa","UsuarioDB","AGRUPA","0..1","0..*"],
  ["Empresa","ClienteEmpresa","VENDE_A","1","0..*"],
  ["Empresa","AsientoBitacora","REGISTRA","0..1","0..*"],
  ["Cliente_BD","ClienteEmpresa","COMPRA_EN","1","0..*"],
  ["Usuario","Cliente_BD","ES","1","0..1"],
  ["Rol","Usuario","SE_ASIGNA_A","1","0..*"],
  ["Rol","UsuarioDB","SE_ASIGNA_A","1","0..*"],
  ["Usuario","SesionToken","ABRE","1","0..*"],
  ["UsuarioDB","SesionToken","ABRE","1","0..*"],
  ["Usuario","Empleado","ES","1","0..1"],
  ["Sucursal","Empleado","EMPLEA","1","0..*"],
  ["Ciudad","Sucursal","UBICA","1","0..*"],
  ["Usuario","AsientoBitacora","DEJA_RASTRO_EN","0..1","0..*"],
  ["UsuarioDB","AsientoBitacora","DEJA_RASTRO_EN","0..1","0..*"],
]

def fks(cls):
    s = set(cls)
    return [list(v) for v in FK if v[0] in s and v[1] in s]

def bit(controles):
    return [[c, "BitacoraMiddleware", "ES_ANOTADO_POR", "1", "1"] for c in controles] + [["BitacoraMiddleware","AsientoBitacora","REGISTRA","1","0..*"]]

def sel(clase, *nombres):
    """Las operaciones de la clase con esos nombres, copiadas tal cual. 'nombre@archivo' filtra por el [archivo]."""
    salida = []
    for n in nombres:
        nom, _, arch = n.partition("@")
        hallo = [o for o in clases[clase]["operaciones"] if o.startswith(nom + "(") and (not arch or "[" + arch in o)]
        assert hallo, (clase, n)
        salida += hallo
    return salida

cus = {}

# ---------------- CU-01 Gestionar empresas ----------------
c01 = ["Empresas","EmpresaFormulario","PlataformaService","plataforma_service","BitacoraMiddleware","AsientoBitacora",
       "Empresa","Plan","Suscripcion","PagoSimulado","Sucursal","Usuario"]
cus["CU-01"] = {"actores": ["Administrador de la plataforma"], "clases": c01,
  "operaciones_en_cu": {
    "PlataformaService": sel("PlataformaService","listarEmpresas","planes","ciudades","obtenerEmpresa","crearEmpresa","editarEmpresa","cambiarEstado","traducir"),
    "Empresa": sel("Empresa","_empresa@plataforma/suscripciones.py"),
    "Plan": [], "Suscripcion": [], "Sucursal": [], "Usuario": [],
    "PagoSimulado": sel("PagoSimulado","registrar_pago")},
  "nota": "crear_empresa hace todo en UNA transaccion: Empresa, Suscripcion (inicio hoy, vencimiento + duracion_dias), PagoSimulado ALTA (plataforma/suscripciones.py registrar_pago), la sucursal principal, su Caja 'Caja 1' (ventas/models.py, omitida) y el Usuario ADMINISTRADOR con contrasena temporal; si falla, rollback (5a). Las consultas de esta alta estan en linea en plataforma/service.py (select/db.get), por eso Plan, Suscripcion, Sucursal y Usuario no muestran operaciones aca. El correo de acceso (integrations/correo.py enviar, el 'CanalDeCorreo' de la robustez) va despues del commit. 3b dar de baja revoca las sesiones (update en linea sobre SesionToken, omitida por el tope). Omitidas tambien Rol, Ciudad y Caja.",
  "relaciones": [["Administrador de la plataforma","Empresas","USA","1","1"],["Empresas","EmpresaFormulario","ABRE","1","0..1"],
    ["Empresas","PlataformaService","SOLICITA","1","1"],["EmpresaFormulario","PlataformaService","SOLICITA","1","1"],
    ["PlataformaService","plataforma_service","LLAMA_A","1","1"],
    ["plataforma_service","Empresa","REGISTRA","1","0..*"],["plataforma_service","Plan","CONSULTA","1","0..*"],
    ["plataforma_service","Suscripcion","REGISTRA","1","0..*"],["plataforma_service","PagoSimulado","REGISTRA","1","0..*"],
    ["plataforma_service","Sucursal","REGISTRA","1","0..*"],["plataforma_service","Usuario","REGISTRA","1","0..*"]]
    + bit(["plataforma_service"]) + fks(c01)}

# ---------------- CU-02 Gestionar planes ----------------
c02 = ["Planes","PlanFormulario","PlataformaService","plataforma_planes","BitacoraMiddleware","AsientoBitacora",
       "Plan","Suscripcion","Empresa","Sucursal","Empleado"]
cus["CU-02"] = {"actores": ["Administrador de la plataforma"], "clases": c02,
  "operaciones_en_cu": {
    "PlataformaService": sel("PlataformaService","listarPlanes","funcionesDePlan","crearPlan","editarPlan","cambiarEstadoPlan","traducir"),
    "Plan": sel("Plan","_obtener","_codigo_libre","_validar_nombre"),
    "Suscripcion": sel("Suscripcion","_empresas_por_plan"),
    "Empresa": [], "Sucursal": [], "Empleado": []},
  "nota": "5a: al guardar, _excedidas/excedidas_en cuentan en linea (select ... group_by ... having) las sucursales activas y los empleados sin fecha_baja de las empresas del plan y devuelven las que pasan el limite; no se borra nada (RN-04). 3a desactivar solo pone plan.activo = false. Los cambios valen en la siguiente verificacion del CU-05, que lee el plan de la base.",
  "relaciones": [["Administrador de la plataforma","Planes","USA","1","1"],["Planes","PlanFormulario","ABRE","1","0..1"],
    ["Planes","PlataformaService","SOLICITA","1","1"],["PlanFormulario","PlataformaService","SOLICITA","1","1"],
    ["PlataformaService","plataforma_planes","LLAMA_A","1","1"],
    ["plataforma_planes","Plan","REGISTRA","1","0..*"],["plataforma_planes","Suscripcion","CONSULTA","1","0..*"],
    ["plataforma_planes","Empresa","CONSULTA","1","0..*"],["plataforma_planes","Sucursal","CONSULTA","1","0..*"],
    ["plataforma_planes","Empleado","CONSULTA","1","0..*"]] + bit(["plataforma_planes"]) + fks(c02)}

# ---------------- CU-03 Gestionar suscripciones ----------------
c03 = ["FichaEmpresa","CambiarPlan","Empresas","PlataformaService","plataforma_suscripciones","plataforma_planes",
       "BitacoraMiddleware","AsientoBitacora","Empresa","Suscripcion","Plan","PagoSimulado"]
cus["CU-03"] = {"actores": ["Administrador de la plataforma"], "clases": c03,
  "operaciones_en_cu": {
    "Empresas": sel("Empresas","marcarVencidas"),
    "PlataformaService": sel("PlataformaService","obtenerEmpresa","listarPlanes","suscripciones","asignarPlan","accionSuscripcion","marcarVencidas","traducir"),
    "plataforma_planes": sel("plataforma_planes","excedidas_en"),
    "Empresa": sel("Empresa","_empresa@plataforma/suscripciones.py"),
    "Suscripcion": sel("Suscripcion","_actual"),
    "Plan": []},
  "nota": "No hay tarea programada: el E1 (marcar_vencidas) es POST /plataforma/suscripciones/vencimiento, 'pensado para un planificador', y hoy lo dispara a mano el boton Empresas.marcarVencidas(). Asignar: cierra la actual como REEMPLAZADA y abre la VIGENTE en la misma transaccion, con PagoSimulado ALTA o CAMBIO. Renovar: vencimiento = max(vencimiento, hoy) + duracion_dias y PagoSimulado RENOVACION. 5a: plataforma/planes.py excedidas_en cuenta en linea Sucursal y Empleado (omitidas por el tope). Plan se lee con db.get en linea.",
  "relaciones": [["Administrador de la plataforma","FichaEmpresa","USA","1","1"],["Administrador de la plataforma","Empresas","USA","1","1"],
    ["FichaEmpresa","CambiarPlan","ABRE","1","0..1"],
    ["FichaEmpresa","PlataformaService","SOLICITA","1","1"],["CambiarPlan","PlataformaService","SOLICITA","1","1"],
    ["Empresas","PlataformaService","SOLICITA","1","1"],["PlataformaService","plataforma_suscripciones","LLAMA_A","1","1"],
    ["plataforma_suscripciones","plataforma_planes","CALCULA_EXCEDIDAS_CON","1","1"],
    ["plataforma_suscripciones","Empresa","CONSULTA","1","1"],["plataforma_suscripciones","Suscripcion","REGISTRA","1","0..*"],
    ["plataforma_suscripciones","Plan","CONSULTA","1","1"],["plataforma_suscripciones","PagoSimulado","REGISTRA","1","0..*"]]
    + bit(["plataforma_suscripciones"]) + fks(c03)}

# ---------------- CU-04 Consultar plan y consumo ----------------
c04 = ["MiPlan","MiPlanService","mi_plan_service","Empresa","Suscripcion","Plan","Sucursal","Empleado"]
cus["CU-04"] = {"actores": ["Administrador de la empresa"], "clases": c04,
  "operaciones_en_cu": {
    "Empresa": sel("Empresa","obtener_empresa@plataforma/mi_plan/repository.py"),
    "Suscripcion": sel("Suscripcion","obtener_suscripcion_actual"),
    "Plan": sel("Plan","listar_planes_activos"),
    "Sucursal": sel("Sucursal","contar_sucursales_activas"),
    "Empleado": sel("Empleado","contar_empleados_activos")},
  "nota": "Solo lectura (GET /plataforma/mi-plan): sin bitacora. Las tablas del tenant ya vienen filtradas por RLS. Los cupos del mes se devuelven con usado = None ('mientras no existan'): mi_plan/service.py NO lee consumo_cupo aunque la tabla y verificador.uso_del_mes ya existen. El 2a lo resuelve _suscripcion() con solo_consulta.",
  "relaciones": [["Administrador de la empresa","MiPlan","USA","1","1"],["MiPlan","MiPlanService","SOLICITA","1","1"],
    ["MiPlanService","mi_plan_service","LLAMA_A","1","1"],
    ["mi_plan_service","Empresa","CONSULTA","1","1"],["mi_plan_service","Suscripcion","CONSULTA","1","0..1"],
    ["mi_plan_service","Plan","CONSULTA","1","0..*"],["mi_plan_service","Sucursal","CONSULTA","1","0..*"],
    ["mi_plan_service","Empleado","CONSULTA","1","0..*"]] + fks(c04)}

# ---------------- CU-05 Verificar limites y funciones del plan ----------------
c05 = ["LimiteDelPlan","MiPlanService","core_dependencies","plataforma_verificador","BitacoraMiddleware","AsientoBitacora",
       "Suscripcion","Plan","ConsumoCupo","Sucursal","Empleado"]
cus["CU-05"] = {"actores": ["Usuario"], "clases": c05,
  "operaciones_en_cu": {
    "core_dependencies": sel("core_dependencies","get_usuario_actual","_exigir_suscripcion_para_escribir","requiere_funcion","requiere_limite","requiere_cupo"),
    "Suscripcion": sel("Suscripcion","suscripcion_vigente"),
    "Plan": sel("Plan","plan_vigente"),
    "ConsumoCupo": sel("ConsumoCupo","uso_del_mes","consumir_cupo"),
    "Sucursal": sel("Sucursal","_contar_sucursales"),
    "Empleado": sel("Empleado","_contar_empleados"),
    "MiPlanService": sel("MiPlanService","consultar")},
  "nota": "Lo incluyen las operaciones controladas: requiere_limite('empleados') en POST /organizacion/empleados, requiere_funcion('marca_propia') en /plataforma/mi-tienda, requiere_funcion + requiere_cupo en reportes por voz y foto con IA; las sucursales llaman a verificar_limite desde organizacion/service.py. El 2a vale para TODA escritura del personal: get_usuario_actual -> _exigir_suscripcion_para_escribir. RechazoDelPlan -> 403 {detail, codigo, limite, uso} en app/main.py _rechazo_del_plan; el BitacoraMiddleware anota esa peticion como *_RECHAZADO. consumir_cupo lo llama el servicio que gasta el cupo DESPUES de que la operacion salio bien. LimiteDelPlan avisa el uso antes de abrir el formulario leyendo GET /plataforma/mi-plan (CU-04).",
  "relaciones": [["Usuario","LimiteDelPlan","USA","1","1"],["LimiteDelPlan","MiPlanService","SOLICITA","1","1"],
    ["MiPlanService","core_dependencies","PASA_POR","1","1"],
    ["core_dependencies","plataforma_verificador","DELEGA_EN","1","1"],
    ["plataforma_verificador","Suscripcion","CONSULTA","1","0..1"],["plataforma_verificador","Plan","CONSULTA","1","1"],
    ["plataforma_verificador","ConsumoCupo","REGISTRA","1","0..*"],["plataforma_verificador","Sucursal","CUENTA","1","0..*"],
    ["plataforma_verificador","Empleado","CUENTA","1","0..*"]] + bit(["core_dependencies"]) + fks(c05)}

# ---------------- CU-06 Iniciar sesion en una empresa ----------------
c06 = ["Login","PantallaLogin","AuthService","ControlSesion","seguridad_service","BitacoraMiddleware","AsientoBitacora",
       "Empresa","UsuarioDB","Rol","SesionToken","Suscripcion"]
cus["CU-06"] = {"actores": ["Usuario"], "clases": c06,
  "operaciones_en_cu": {
    "AuthService": sel("AuthService","iniciarSesion","cerrarSesion","restaurarSesion","inicioDelRol","guardarToken","borrarToken","recordarSinRed","traducirLogin"),
    "ControlSesion": sel("ControlSesion","restaurar","iniciarSesion","cerrarSesion"),
    "seguridad_service": sel("seguridad_service","autenticar","_autenticar_en_la_plataforma","_emitir","_autenticado","cerrar_sesion"),
    "Empresa": sel("Empresa","obtener_empresa_por_slug"),
    "UsuarioDB": sel("UsuarioDB","obtener_usuario_con_rol@seguridad"),
    "Rol": [],
    "SesionToken": sel("SesionToken","agregar_sesion","revocar_sesion"),
    "Suscripcion": sel("Suscripcion","suscripcion_vigente")},
  "nota": "Sin slug solo entra ADMIN_PLATAFORMA (1a, modo_plataforma); slug inexistente o empresa BAJA = 404 'Empresa no encontrada' (2a); con la suscripcion vencida entra igual y _autenticado marca solo_consulta con verificador.suscripcion_vigente (3a): el CU-05 impide escribir. El rol llega por joinedload en obtener_usuario_con_rol. Token con empresa_id como claim (core/security.py crear_access_token). Un cliente que entra queda asociado a la empresa del slug (seguridad/repository.py asociar_cliente_a_la_empresa -> ClienteEmpresa, omitida) y la sucursal del token sale de obtener_sucursal_de_usuario (Empleado, omitida). Movil: ControlSesion llama a RepositorioAuth.iniciarSesion (omitido). 6a cerrar sesion = POST /auth/logout -> revocar_sesion. La bitacora anota INICIAR_SESION / INTENTO_FALLIDO / CERRAR_SESION.",
  "relaciones": [["Usuario","Login","USA","1","1"],["Usuario","PantallaLogin","USA","1","1"],
    ["Login","AuthService","SOLICITA","1","1"],["PantallaLogin","ControlSesion","SOLICITA","1","1"],
    ["AuthService","seguridad_service","LLAMA_A","1","1"],["ControlSesion","seguridad_service","LLAMA_A","1","1"],
    ["seguridad_service","Empresa","CONSULTA","1","0..1"],["seguridad_service","UsuarioDB","CONSULTA","1","0..1"],
    ["seguridad_service","Rol","CONSULTA","1","1"],["seguridad_service","SesionToken","REGISTRA","1","0..*"],
    ["seguridad_service","Suscripcion","CONSULTA","1","0..1"]] + bit(["seguridad_service"]) + fks(c06)}

# ---------------- CU-07 Registrar cliente con cuenta unica ----------------
c07 = ["Registro","PantallaRegistro","AuthService","RepositorioAuth","seguridad_service","BitacoraMiddleware","AsientoBitacora",
       "Usuario","Cliente_BD","ClienteEmpresa","Empresa","SesionToken"]
cus["CU-07"] = {"actores": ["Cliente"], "clases": c07,
  "operaciones_en_cu": {
    "AuthService": sel("AuthService","registrar","asociarCuentaExistente","guardarToken","recordarSinRed","traducirRegistro","traducirLogin"),
    "RepositorioAuth": sel("RepositorioAuth","registrar"),
    "seguridad_service": sel("seguridad_service","registrar_cliente","asociar_cuenta_existente","autenticar","_emitir","_viola"),
    "Usuario": sel("Usuario","obtener_usuario_por_correo@seguridad","agregar_usuario@seguridad","obtener_usuario_con_rol"),
    "Empresa": sel("Empresa","obtener_empresa_por_slug"),
    "SesionToken": sel("SesionToken","agregar_sesion")},
  "nota": "registrar_cliente: el correo se busca entre las cuentas SIN empresa (RN-13); si ya es de un cliente responde 409 'cuenta de cliente' y la web ofrece el 4b (POST /auth/registro/asociar: con la contrasena, autenticar() con el slug recordado lo asocia a la tienda y abre la sesion). Usuario y Cliente se crean en una transaccion; agregar_cliente deja usuario.empresa_id = NULL e inserta cliente_empresa con la empresa del CONTEXTO. El rol CLIENTE se lee con obtener_rol_por_nombre (Rol, omitida por el tope). La contrasena se guarda con core/security.py hash_password.",
  "relaciones": [["Cliente","Registro","USA","1","1"],["Cliente","PantallaRegistro","USA","1","1"],
    ["Registro","AuthService","SOLICITA","1","1"],["PantallaRegistro","RepositorioAuth","SOLICITA","1","1"],
    ["AuthService","seguridad_service","LLAMA_A","1","1"],["RepositorioAuth","seguridad_service","LLAMA_A","1","1"],
    ["seguridad_service","Usuario","REGISTRA","1","0..1"],["seguridad_service","Cliente_BD","REGISTRA","1","0..1"],
    ["seguridad_service","ClienteEmpresa","REGISTRA","1","0..*"],["seguridad_service","Empresa","CONSULTA","1","0..1"],
    ["seguridad_service","SesionToken","REGISTRA","1","0..1"]] + bit(["seguridad_service"]) + fks(c07)}

# ---------------- CU-08 Gestionar usuarios de la empresa ----------------
c08 = ["Usuarios","UsuarioFormulario","UsuariosService","seguridad_service","BitacoraMiddleware","AsientoBitacora",
       "Usuario","Rol","Sucursal","Empleado","SesionToken"]
cus["CU-08"] = {"actores": ["Administrador de la empresa"], "clases": c08,
  "operaciones_en_cu": {
    "seguridad_service": sel("seguridad_service","listar_roles","listar_usuarios","obtener_usuario","_personal_de_la_empresa","_validar_ambito",
                             "crear_usuario","editar_usuario","cambiar_estado","eliminar_usuario","_fila_a_resumen","_viola"),
    "Usuario": sel("Usuario","obtener_usuario_por_correo@seguridad","agregar_usuario@seguridad","obtener_usuario_con_id","contar_y_listar_usuarios",
                   "obtener_detalle_usuario","tiene_operaciones_asociadas","eliminar_usuario"),
    "Rol": sel("Rol","obtener_rol_por_nombre@seguridad","listar_roles"),
    "Sucursal": sel("Sucursal","existe_sucursal_activa"),
    "Empleado": sel("Empleado","obtener_empleado_de_usuario","agregar_empleado@seguridad"),
    "SesionToken": sel("SesionToken","revocar_sesiones_de_usuario")},
  "nota": "NO incluye el CU-05: no hay limite de usuarios en el plan (verificador.LIMITES solo tiene 'sucursales' y 'empleados') y ninguna ruta de /usuarios declara requiere_limite; ni siquiera el alta de ENCARGADO/CAJERO, que crea tambien la ficha de Empleado, verifica el limite de empleados. usuario no tiene RLS: el filtro lo pone el codigo con la empresa del token (_empresa(usuario) del router); la sucursal se valida con RLS. 5a: ADMIN_PLATAFORMA y los ROLES_NO_ASIGNABLES (CLIENTE) se rechazan. La lista incluye a los clientes de la empresa (via cliente_empresa, omitida) pero su cuenta no se toca (CuentaDePlataforma). El selector de sucursales del formulario usa OrganizacionService.sucursales() (omitido).",
  "relaciones": [["Administrador de la empresa","Usuarios","USA","1","1"],["Usuarios","UsuarioFormulario","ABRE","1","0..1"],
    ["Usuarios","UsuariosService","SOLICITA","1","1"],["UsuarioFormulario","UsuariosService","SOLICITA","1","1"],
    ["UsuariosService","seguridad_service","LLAMA_A","1","1"],
    ["seguridad_service","Usuario","REGISTRA","1","0..*"],["seguridad_service","Rol","CONSULTA","1","0..*"],
    ["seguridad_service","Sucursal","CONSULTA","1","0..1"],["seguridad_service","Empleado","REGISTRA","1","0..1"],
    ["seguridad_service","SesionToken","REVOCA","1","0..*"]] + bit(["seguridad_service"]) + fks(c08)}

# ---------------- CU-09 Gestionar sucursales de la empresa ----------------
c09 = ["Sucursales","SucursalFormulario","OrganizacionService","organizacion_service","plataforma_verificador",
       "BitacoraMiddleware","AsientoBitacora","Sucursal","Ciudad","Suscripcion","Plan"]
cus["CU-09"] = {"actores": ["Administrador de la empresa"], "clases": c09,
  "operaciones_en_cu": {
    "OrganizacionService": sel("OrganizacionService","listarCiudades","listarSucursales","crearSucursal","editarSucursal","cambiarEstadoSucursal","traducir"),
    "plataforma_verificador": sel("plataforma_verificador","verificar_limite","plan_vigente","suscripcion_vigente","_contar_sucursales"),
    "Sucursal": sel("Sucursal","listar_sucursales","obtener_sucursal_con_ciudad","obtener_sucursal","existe_sucursal_con_nombre","agregar_sucursal","_contar_sucursales"),
    "Ciudad": sel("Ciudad","listar_ciudades","obtener_ciudad"),
    "Suscripcion": sel("Suscripcion","suscripcion_vigente"),
    "Plan": sel("Plan","plan_vigente")},
  "nota": "El limite es de sucursales ACTIVAS: crear_sucursal verifica solo si nace activa, y cambiar_estado_sucursal solo al reactivar; dar de baja nunca se impide (RN-04). El uso del limite (paso 2) lo muestra <app-limite-del-plan> (ver CU-05). La sucursal queda en la empresa del token por el DEFAULT app_empresa_actual() + RLS. 4a: el 403 plan_limit lo traduce OrganizacionService.traducir() y Sucursales ofrece 'Ver mi plan'.",
  "relaciones": [["Administrador de la empresa","Sucursales","USA","1","1"],["Sucursales","SucursalFormulario","ABRE","1","0..1"],
    ["Sucursales","OrganizacionService","SOLICITA","1","1"],["SucursalFormulario","OrganizacionService","SOLICITA","1","1"],
    ["OrganizacionService","organizacion_service","LLAMA_A","1","1"],
    ["organizacion_service","plataforma_verificador","VERIFICA_LIMITE_CON","1","1"],
    ["organizacion_service","Sucursal","REGISTRA","1","0..*"],["organizacion_service","Ciudad","CONSULTA","1","0..*"],
    ["plataforma_verificador","Suscripcion","CONSULTA","1","0..1"],["plataforma_verificador","Plan","CONSULTA","1","1"],
    ["plataforma_verificador","Sucursal","CUENTA","1","0..*"]] + bit(["organizacion_service"]) + fks(c09)}

# ---------------- CU-10 Gestionar empleados de la empresa ----------------
c10 = ["Empleados","EmpleadoFormulario","EmpleadosService","empleados_service","core_dependencies","plataforma_verificador",
       "BitacoraMiddleware","AsientoBitacora","Empleado","Usuario","Sucursal","Rol"]
cus["CU-10"] = {"actores": ["Administrador de la empresa"], "clases": c10,
  "operaciones_en_cu": {
    "core_dependencies": sel("core_dependencies","requiere_limite"),
    "plataforma_verificador": sel("plataforma_verificador","verificar_limite","plan_vigente","_contar_empleados"),
    "Usuario": sel("Usuario","listar_usuarios_vinculables","obtener_usuario_vinculable","obtener_usuario_por_correo@organizacion",
                   "agregar_usuario@organizacion","obtener_usuario"),
    "Sucursal": sel("Sucursal","obtener_sucursal_activa","existe_sucursal"),
    "Rol": sel("Rol","obtener_rol_por_nombre@organizacion"),
    "Empleado": sel("Empleado","listar_empleados","obtener_empleado_con_detalle","obtener_empleado","existe_documento",
                    "agregar_empleado@organizacion","_contar_empleados")},
  "nota": "El limite va por la dependencia Depends(requiere_limite('empleados')) del POST /organizacion/empleados; cuenta empleados con fecha_baja IS NULL. El alta crea el Usuario con el rol del cargo (ENCARGADO o CAJERO) y la ficha en una transaccion, o vincula una cuenta existente (3c, usuariosVinculables). 'Desactivar' es dar_de_baja: fecha_baja, usuario.activo = false y revoca sus sesiones (seguridad/repository.py revocar_sesiones_de_usuario -> SesionToken, omitida); no hay reactivacion. Suscripcion y Plan (via plan_vigente) omitidas por el tope.",
  "relaciones": [["Administrador de la empresa","Empleados","USA","1","1"],["Empleados","EmpleadoFormulario","ABRE","1","0..1"],
    ["Empleados","EmpleadosService","SOLICITA","1","1"],["EmpleadoFormulario","EmpleadosService","SOLICITA","1","1"],
    ["EmpleadosService","core_dependencies","PASA_POR","1","1"],["EmpleadosService","empleados_service","LLAMA_A","1","1"],
    ["core_dependencies","plataforma_verificador","DELEGA_EN","1","1"],
    ["plataforma_verificador","Empleado","CUENTA","1","0..*"],
    ["empleados_service","Empleado","REGISTRA","1","0..*"],["empleados_service","Usuario","REGISTRA","1","0..1"],
    ["empleados_service","Sucursal","CONSULTA","1","0..1"],["empleados_service","Rol","CONSULTA","1","1"]]
    + bit(["empleados_service"]) + fks(c10)}

# ---------------- CU-11 Contratar un plan desde la web ----------------
c11 = ["PlanesPublicos","Contratar","ContratacionService","contratacion_service","plataforma_service","BitacoraMiddleware","AsientoBitacora",
       "Plan","Empresa","PagoSimulado","Suscripcion","Usuario"]
cus["CU-11"] = {"actores": ["Empresa interesada"], "clases": c11,
  "operaciones_en_cu": {
    "plataforma_service": sel("plataforma_service","crear_empresa","_correo_de_bienvenida","obtener_empresa","_resumenes"),
    "Empresa": sel("Empresa","_ocupados"),
    "PagoSimulado": sel("PagoSimulado","registrar_pago"),
    "Plan": [], "Suscripcion": [], "Usuario": []},
  "nota": "Rutas publicas, sin token. Orden: valida plan activo, slug libre (5a: _sugerir arma variantes libres) y ciudad; _cobrar() simula el pago (6a: el codigo_operacion CODIGO_RECHAZADO rechaza sin escribir nada) y recien entonces crear_empresa (la misma alta del CU-01, con la contrasena elegida y el comprobante), que crea tambien la sucursal principal y su Caja (Sucursal omitida por el tope; ver CU-01). Plan, Suscripcion y Usuario se leen/escriben en linea en los servicios. Correo de bienvenida despues del commit. La web recuerda el slug (recordarEmpresa) e irALogin() lleva al login. El POST /contratar se anota sin usuario.",
  "relaciones": [["Empresa interesada","PlanesPublicos","USA","1","1"],["Empresa interesada","Contratar","USA","1","1"],
    ["PlanesPublicos","ContratacionService","SOLICITA","1","1"],["Contratar","ContratacionService","SOLICITA","1","1"],
    ["ContratacionService","contratacion_service","LLAMA_A","1","1"],["contratacion_service","plataforma_service","DELEGA_ALTA_EN","1","1"],
    ["contratacion_service","Plan","CONSULTA","1","0..*"],["contratacion_service","Empresa","CONSULTA","1","0..*"],
    ["contratacion_service","PagoSimulado","CONSULTA","1","0..1"],
    ["plataforma_service","Empresa","REGISTRA","1","1"],["plataforma_service","Suscripcion","REGISTRA","1","1"],
    ["plataforma_service","PagoSimulado","REGISTRA","1","1"],["plataforma_service","Usuario","REGISTRA","1","1"]]
    + bit(["contratacion_service"]) + fks(c11)}

# ---------------- CU-12 Personalizar la tienda de la empresa ----------------
c12 = ["MiTienda","MiTiendaService","MarcaService","mi_tienda_service","core_dependencies","plataforma_verificador","catalogo_imagenes_almacen",
       "BitacoraMiddleware","AsientoBitacora","Empresa","Suscripcion","Plan"]
cus["CU-12"] = {"actores": ["Administrador de la empresa"], "clases": c12,
  "operaciones_en_cu": {
    "core_dependencies": sel("core_dependencies","requiere_funcion"),
    "plataforma_verificador": sel("plataforma_verificador","verificar_funcion","plan_vigente","suscripcion_vigente"),
    "Empresa": sel("Empresa","_empresa@plataforma/mi_tienda/service.py"),
    "Suscripcion": sel("Suscripcion","suscripcion_vigente"),
    "Plan": sel("Plan","plan_vigente")},
  "nota": "Ver la pantalla no exige la funcion: obtener_marca devuelve incluida = _incluida(db) y la interfaz la muestra como no incluida (1a). Guardar colores y subir/quitar el logo exigen requiere_funcion('marca_propia'). El logo se guarda en MEDIA_ROOT/empresas/<id>/ y en empresa.logo va la ruta; el anterior se borra recien despues del commit. La tienda (GET /tienda/marca, marca_de_la_tienda) solo muestra la marca si el plan vigente la incluye (RN-04). La marca vive en columnas de empresa: no hay tabla propia.",
  "relaciones": [["Administrador de la empresa","MiTienda","USA","1","1"],["MiTienda","MiTiendaService","SOLICITA","1","1"],
    ["MiTienda","MarcaService","APLICA_MARCA_CON","1","1"],
    ["MiTiendaService","core_dependencies","PASA_POR","1","1"],["MiTiendaService","mi_tienda_service","LLAMA_A","1","1"],
    ["MarcaService","mi_tienda_service","LLAMA_A","1","1"],
    ["core_dependencies","plataforma_verificador","DELEGA_EN","1","1"],["mi_tienda_service","plataforma_verificador","CONSULTA_FUNCION_EN","1","1"],
    ["mi_tienda_service","catalogo_imagenes_almacen","VALIDA_LOGO_CON","1","1"],
    ["mi_tienda_service","Empresa","ACTUALIZA","1","1"],
    ["plataforma_verificador","Suscripcion","CONSULTA","1","0..1"],["plataforma_verificador","Plan","CONSULTA","1","1"]]
    + bit(["mi_tienda_service"]) + fks(c12)}

# ---------------- validacion ----------------
nombres_ci = {}
for k in clases:
    assert k.lower() not in nombres_ci, ("clave repetida sin mayusculas (PowerShell no distingue)", k, nombres_ci[k.lower()])
    nombres_ci[k.lower()] = k
for cu, d in cus.items():
    assert 6 <= len(d["clases"]) <= 12, (cu, len(d["clases"]))
    assert len(set(d["clases"])) == len(d["clases"]), cu
    for c in d["clases"]:
        assert c in clases, (cu, c)
    nombres = [x.lower() for x in d["clases"] + d["actores"]]
    assert len(set(nombres)) == len(nombres), ("actor y clase con el mismo nombre", cu)
    tipos = {clases[c]["tipo"] for c in d["clases"]}
    assert "control" in tipos and "interfaz" in tipos and "entidad" in tipos, (cu, tipos)
    for r in d["relaciones"]:
        assert len(r) == 5, (cu, r)
        for x in r[:2]:
            assert x in d["clases"] or x in d["actores"], (cu, r)
    vistos = set()
    for r in d["relaciones"]:
        clave = (r[0], r[1], r[2])
        assert clave not in vistos, ("relacion repetida", cu, r)
        vistos.add(clave)
    for c, ops in d.get("operaciones_en_cu", {}).items():
        assert c in d["clases"], (cu, c)
        for o in ops:
            assert o in clases[c]["operaciones"], (cu, c, o)
    conectadas = {x for r in d["relaciones"] for x in r[:2]}
    for c in d["clases"] + d["actores"]:
        assert c in conectadas, ("clase suelta", cu, c)

data = {"_convencion": "relaciones: [ClaseA, ClaseB, ROL, multiplicidad en el extremo de ClaseA, multiplicidad en el extremo de ClaseB]. "
        "'operaciones_en_cu' (opcional) dice que operaciones de una clase compartida se usan en ese CU (una lista vacia: ninguna, porque el CU "
        "consulta esa tabla en linea desde el servicio); si una clase no figura ahi, se usan todas. En las entidades, '[archivo]' al final de una "
        "operacion dice en que archivo esta: el repository.py o, en plataforma/ (que no tiene repository.py para empresa, plan, suscripcion, "
        "pago_simulado ni consumo_cupo), la funcion del servicio que consulta la tabla. Los controles del backend se nombran <paquete>_<modulo> "
        "(plataforma_service = plataforma/service.py, plataforma_planes = plataforma/planes.py, core_dependencies = core/dependencies.py). "
        "Cliente_BD y UsuarioDB son las entidades Cliente y Usuario renombradas para no chocar con el actor del mismo nombre.",
        "clases": clases, "cus": cus}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
for cu, d in cus.items():
    print(cu, len(d["clases"]), "clases", len(d["relaciones"]), "relaciones")
print("clases definidas", len(clases), "->", OUT)
