# Datos del 3.4 Diseño de clases de la 2da presentación (CU-13 a CU-20), sacados del código.
# Clases interfaz (acciones del componente), control (métodos reales) y entidad (columnas con su tipo
# y las funciones del repository.py). Lo arma la sesión del 01/11; lo dibuja scripts/ea-p2-clases.ps1.
# Uso: python -X utf8 scripts/p2_clases_datos.py  -> scripts/ea-p2-clases.datos.json
import json, os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ea-p2-clases.datos.json")
B = "backend/app/modules/"
W = "frontend-web/src/app/"
M = "mobile/lib/"
OMIT_AUD = "Omitidas las heredadas de Auditoria: creado_en TIMESTAMPTZ, actualizado_en TIMESTAMPTZ."

clases = {
  # ---------------- INTERFACES ----------------
  "Pendientes": {"tipo": "interfaz", "origen": W+"features/caja/pendientes/pendientes.ts",
    "atributos": [], "operaciones": ["preparar(): Promise<void>", "sincronizar(): Promise<void>", "limpiar(): void"]},
  "Venta_PWA": {"tipo": "interfaz", "origen": W+"features/caja/venta/venta.ts",
    "nota": "En el codigo la clase se llama `Venta` (export class Venta); se renombra aca para no chocar con la entidad Venta (tabla venta). registrarSinRed() es privado y lo llama cobrar() cuando sinRed() es verdadero.",
    "atributos": [], "operaciones": ["agregar(prenda: PrendaEnMostrador): void", "cambiarCantidad(linea: LineaEnCurso, cantidad: number): void",
      "quitar(linea: LineaEnCurso): void", "cargarReserva(fila: ReservaPorCobrar): void", "soltarReserva(): void", "vaciar(): void",
      "elegirMetodo(metodo: MetodoDePago): void", "cobrar(): void", "nuevaVenta(): void", "imprimir(): void"]},
  "Turno": {"tipo": "interfaz", "origen": W+"features/caja/turno/turno.ts",
    "atributos": [], "operaciones": ["elegir(caja: Caja): void", "abrir(): void", "cerrar(): Promise<void>", "volverAEmpezar(): void"]},
  "Rechazadas": {"tipo": "interfaz", "origen": W+"features/sucursal/rechazadas/rechazadas.ts",
    "atributos": [], "operaciones": ["cambiarVista(vista: 'por-devolver' | 'todas'): void", "abrir(fila: OperacionDeSucursal): void", "devolver(fila: OperacionDeSucursal): void"]},
  "PantallaSinConexion": {"tipo": "interfaz", "origen": M+"features/offline/pantalla_sin_conexion.dart",
    "nota": "Los metodos viven en _PantallaSinConexionState. 'Limpiar historial' llama inline a ControlOffline.limpiarDecididas() (no hay metodo propio en la pantalla).",
    "atributos": [], "operaciones": ["_preparar(): Future<void>", "_sincronizar(): Future<void>"]},
  "PantallaReservaSinRed": {"tipo": "interfaz", "origen": M+"features/offline/pantalla_reserva_sin_red.dart",
    "nota": "Los metodos viven en _PantallaReservaSinRedState. Elegir sucursal, duracion, categoria, buscar y +/- cantidad son setState inline, sin metodo propio.",
    "atributos": [], "operaciones": ["_elegirDia(): Future<void>", "_elegirHora(): Future<void>", "_elegirVariantes(variantes: List<PrendaOffline>): Future<void>", "_guardar(): Future<void>"]},

  # ---------------- CONTROLES (dispositivo) ----------------
  "OfflineService": {"tipo": "control", "origen": W+"core/services/offline.service.ts",
    "atributos": ["enLinea: Signal<boolean>", "paquete: Signal<PaqueteDeMostrador | null>", "sincronizando: Signal<boolean>",
      "operaciones: Signal<OperacionGuardada[]>", "pendientes: Signal<OperacionGuardada[]>", "vencido: Signal<boolean>", "listo: Promise<void>"],
    "operaciones": ["probarConexion(): Promise<boolean>", "cargar(): Promise<void>", "marcarSinRed(): void", "preparar(): Promise<PaqueteDeMostrador>",
      "registrarVenta(operacion, resumen, total): Promise<OperacionGuardada>", "sincronizar(): Promise<{confirmadas, rechazadas} | null>",
      "enviar(lote, cuenta): Promise<'seguir' | 'parar'>", "limpiarConfirmadas(): Promise<void>", "actualizar(uuid, cambios): Promise<void>",
      "nombreDelDispositivo(): string", "deSucursal(porDevolver): Observable<OperacionDeSucursal[]>",
      "registrarDevolucion(uuid, datos): Observable<OperacionDeSucursal>"]},
  "CajaService": {"tipo": "control", "origen": W+"core/services/caja.service.ts",
    "atributos": ["turno: Signal<Turno | null>"],
    "operaciones": ["cajas(): Observable<Caja[]>", "miTurno(): Observable<Turno | null>", "abrir(datos: AbrirTurno): Observable<Turno>",
      "cerrar(turnoId: number, datos: CerrarTurno): Observable<Turno>", "traducir(error: HttpErrorResponse): ErrorCaja"]},
  "ControlOffline": {"tipo": "control", "origen": M+"features/offline/estado_offline.dart",
    "nota": "Notifier<EstadoOffline> (offlineProvider). Habla con el backend por RepositorioOffline (descargarPaquete, sincronizar, hayConexion) y con SQLite por BaseLocal.",
    "atributos": ["state: EstadoOffline", "_base: BaseLocal", "_reloj: Timer?"],
    "operaciones": ["build(): EstadoOffline", "_cargar(): Future<void>", "_alReloj(): Future<void>", "marcarSinRed(): void",
      "preparar(): Future<PaqueteCliente>", "_guardarFotos(paquete: PaqueteCliente): Future<void>",
      "reservar(sucursal, prendas, inicio, fin): Future<OperacionGuardada>", "sincronizar(): Future<({int confirmadas, int rechazadas})?>",
      "_enviar(lote, cuenta): Future<bool>", "limpiarDecididas(): Future<void>", "_cantidades(cuerpo): Map<int, int>"]},

  # ---------------- CONTROLES (backend) ----------------
  "offline_service": {"tipo": "control", "origen": B+"offline/service.py",
    "nota": "Modulo de funciones, no una clase de Python. Lo exponen las rutas de offline/router.py: GET /offline/paquete, GET /offline/paquete-cliente, POST /offline/sincronizar, GET /offline/operaciones/mias, GET /offline/operaciones, POST /offline/operaciones/{uuid}/devolucion.",
    "atributos": [],
    "operaciones": ["paquete_de_mostrador(db, usuario_id): PaqueteDeMostradorOut", "paquete_de_cliente(db): PaqueteDeClienteOut",
      "sincronizar(db, usuario_id, rol, sucursal_del_usuario, lote): LoteOut",
      "_sincronizar_una(db, op, usuario_id, rol, sucursal_del_usuario, dispositivo): ResultadoOut",
      "_sucursal_declarada(db, op, usuario_id, sucursal_del_usuario): int", "_confirmar_venta(db, op, usuario_id): tuple[int, int]",
      "_confirmar_reserva(db, op, usuario_id, rol, sucursal_del_usuario): tuple[int, int]", "_resultado(db, fila, repetida): ResultadoOut",
      "_por_devolver(fila): bool", "_operacion_out(db, fila, usuario): OperacionOut", "operaciones_mias(db, usuario_id, estado): list[OperacionOut]",
      "operaciones_de_sucursal(db, sucursal_id, estado, por_devolver): list[OperacionOut]",
      "registrar_devolucion(db, uuid, datos, usuario_id, sucursal_id): OperacionOut", "_sucursal_out(sucursal): SucursalOfflineOut",
      "_vigencia(generado): datetime", "_ahora(): datetime"]},
  "reservas_service": {"tipo": "control", "origen": B+"reservas/service.py",
    "nota": "Solo las funciones que usa la reserva offline (_confirmar_reserva llama a registrar_reserva). Por dentro llama a inventario/service.py apartar_para_reserva (Existencia).",
    "atributos": [], "operaciones": ["registrar_reserva(db, datos, cliente_id, usuario_id)", "_validar_franja(datos, sucursal): None"]},
  "caja_service": {"tipo": "control", "origen": B+"caja/service.py",
    "nota": "Modulo de funciones. Rutas en caja/router.py: GET /caja/cajas, GET /caja/turnos/mio, POST /caja/turnos, POST /caja/turnos/{turno_id}/cierre.",
    "atributos": [],
    "operaciones": ["cajas_disponibles(db, sucursal_id): list[tuple]", "mi_turno(db, usuario_id): EstadoDelTurno | None",
      "abrir(db, caja_id, usuario_id, monto_apertura): EstadoDelTurno", "cerrar(db, turno_id, usuario_id, monto_cierre): EstadoDelTurno",
      "_esperado(db, turno): tuple[Decimal, Decimal, Decimal, Decimal, Decimal]", "_armar(db, turno, diferencia): EstadoDelTurno"]},
  "BitacoraMiddleware": {"tipo": "control", "origen": B+"bitacora/middleware.py",
    "nota": "Anota toda peticion POST/PUT/PATCH/DELETE (y las exportaciones GET). _anotar llama a bitacora/service.py registrar(db, accion, metodo, ruta, estado_http, exito, usuario_id, actor, rol, entidad, entidad_id, ip, agente, detalle), que inserta con bitacora/repository.py agregar(db, **campos). Los GET no se anotan.",
    "atributos": [], "operaciones": ["dispatch(peticion: Request, siguiente): Response", "_anotar(peticion: Request, respuesta): None"]},

  # ---------------- ENTIDADES (almacenes locales) ----------------
  "paquetes": {"tipo": "entidad", "origen": W+"core/services/almacen-local.ts",
    "nota": "Object store de IndexedDB (base 'violet-offline', version 1), sin keyPath: una sola fila con clave 'mostrador' cuyo valor es un PaqueteDeMostrador (core/models/offline.models.ts).",
    "atributos": ["generado_en: string", "vigente_hasta: string", "empresa_id: number", "usuario_id: number", "sucursal: SucursalOffline",
      "turno_caja_id: number", "caja_nombre: string", "prendas: PrendaOffline[]", "clientes: ClienteOffline[]"],
    "operaciones": ["leer(almacen, clave): Promise<T | undefined>", "guardar(almacen, valor, clave): Promise<void>"]},
  "operaciones": {"tipo": "entidad", "origen": W+"core/services/almacen-local.ts",
    "nota": "Object store de IndexedDB con keyPath 'uuid'; cada valor es un OperacionGuardada (core/models/offline.models.ts). estado: 'local' | 'enviada' | 'confirmada' | 'rechazada' | 'en_conflicto'. El pago (CU-16) va dentro de operacion.pago {metodo, monto, referencia}.",
    "atributos": ["uuid: string", "estado: EstadoLocal", "operacion: OperacionOfflineIn", "resumen: string", "total: string", "intentos: number",
      "motivo: string | null", "venta_codigo: string | null", "requiere_devolucion: boolean", "actualizada_en: string"],
    "operaciones": ["todos(almacen): Promise<T[]>", "guardar(almacen, valor, clave): Promise<void>", "borrar(almacen, clave): Promise<void>"]},
  "metadato": {"tipo": "entidad", "origen": M+"core/almacenamiento/base_local.dart",
    "nota": "SQLite violet_offline.db. Guarda generado_en y vigente_hasta del paquete. No entra en ningun CU por el tope de 12 (seria del CU-13).",
    "atributos": ["clave: TEXT (PK)", "valor: TEXT"], "operaciones": ["guardarPaquete(paquete: PaqueteCliente): Future<void>", "leerPaquete(): Future<PaqueteCliente?>"]},
  "sucursal_local": {"tipo": "entidad", "origen": M+"core/almacenamiento/base_local.dart",
    "atributos": ["id: INTEGER (PK)", "nombre: TEXT", "apertura: TEXT", "cierre: TEXT"],
    "operaciones": ["guardarPaquete(paquete: PaqueteCliente): Future<void>", "leerPaquete(): Future<PaqueteCliente?>"]},
  "prenda_local": {"tipo": "entidad", "origen": M+"core/almacenamiento/base_local.dart",
    "atributos": ["variante_id: INTEGER (PK)", "sku: TEXT", "producto_id: INTEGER", "producto: TEXT", "categoria: TEXT", "imagen_url: TEXT",
      "talla: TEXT", "color: TEXT", "precio: TEXT"],
    "operaciones": ["guardarPaquete(paquete: PaqueteCliente): Future<void>", "leerPaquete(): Future<PaqueteCliente?>"]},
  "disponible_local": {"tipo": "entidad", "origen": M+"core/almacenamiento/base_local.dart",
    "nota": "PK compuesta (variante_id, sucursal_id). SQLite no declara FOREIGN KEY: las asociaciones con prenda_local y sucursal_local son logicas.",
    "atributos": ["variante_id: INTEGER (PK)", "sucursal_id: INTEGER (PK)", "disponible: INTEGER"],
    "operaciones": ["guardarPaquete(paquete: PaqueteCliente): Future<void>", "leerPaquete(): Future<PaqueteCliente?>", "descontar(sucursalId: int, cantidades: Map<int, int>): Future<void>"]},
  "operacion_pendiente": {"tipo": "entidad", "origen": M+"core/almacenamiento/base_local.dart",
    "nota": "estado: local | enviada | confirmada | rechazada | en_conflicto (EstadoOperacion en data/modelos/offline.dart). cuerpo = JSON de la operacion que se manda a /offline/sincronizar.",
    "atributos": ["uuid: TEXT (PK)", "estado: TEXT", "cuerpo: TEXT", "resumen: TEXT", "creada_en: TEXT", "intentos: INTEGER", "motivo: TEXT", "reserva_id: INTEGER"],
    "operaciones": ["guardarOperacion(op: OperacionGuardada): Future<void>", "operaciones(): Future<List<OperacionGuardada>>", "borrarDecididas(): Future<void>"]},

  # ---------------- ENTIDADES (PostgreSQL) ----------------
  "OperacionOffline": {"tipo": "entidad", "origen": B+"offline/models.py", "tabla": "operacion_offline",
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "uuid: UUID (UNIQUE)", "tipo: VARCHAR(10)", "estado: VARCHAR(12)",
      "sucursal_id: INTEGER (FK sucursal)", "usuario_id: BIGINT (FK usuario)", "dispositivo: VARCHAR(80)", "creada_en_cliente: TIMESTAMPTZ",
      "recibida_en: TIMESTAMPTZ", "intentos: SMALLINT", "metodo_pago: VARCHAR(10)", "monto_cobrado: NUMERIC(12,2)", "referencia_pago: VARCHAR(60)",
      "carga: JSONB", "venta_id: BIGINT (FK venta, UNIQUE)", "reserva_id: BIGINT (FK reserva, UNIQUE)", "motivo_rechazo: VARCHAR(300)",
      "devuelto_en: TIMESTAMPTZ", "devuelto_por: BIGINT (FK usuario)", "metodo_devolucion: VARCHAR(10)", "referencia_devolucion: VARCHAR(60)",
      "observacion_devolucion: VARCHAR(300)"],
    "operaciones": ["operacion_por_uuid(db, uuid, bloquear): OperacionOffline | None  [offline/repository.py]",
      "operaciones(db, sucursal_id, usuario_id, estado, por_devolver, limite): list[tuple[OperacionOffline, Usuario]]  [offline/repository.py]",
      "ventas_offline_del_turno(db, turno_id): tuple[int, Decimal]  [caja/repository.py]",
      "efectivo_por_devolver(db, turno_id): tuple[int, Decimal]  [caja/repository.py]"]},
  "Venta": {"tipo": "entidad", "origen": B+"ventas/models.py", "tabla": "venta",
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "codigo: VARCHAR(20) (UNIQUE)", "canal: VARCHAR(12)", "estado: VARCHAR(20)",
      "cliente_id: BIGINT (FK cliente)", "sucursal_id: INTEGER (FK sucursal)", "turno_caja_id: BIGINT (FK turno_caja)", "reserva_id: BIGINT (FK reserva, UNIQUE)",
      "modalidad_entrega: VARCHAR(10)", "direccion_id: BIGINT (FK direccion_cliente)", "metodo_pago: VARCHAR(20)", "subtotal: NUMERIC(10,2)",
      "descuento: NUMERIC(10,2)", "total: NUMERIC(10,2)", "creado_en: TIMESTAMPTZ", "actualizado_en: TIMESTAMPTZ"],
    "operaciones": ["agregar_venta_presencial(db, codigo, cliente_id, sucursal_id, turno_caja_id, reserva_id, metodo_pago, subtotal, descuento, total): Venta  [pos/repository.py]",
      "existe_codigo(db, codigo): bool  [pos/repository.py]", "efectivo_cobrado(db, turno_id): Decimal  [caja/repository.py]",
      "ventas_del_turno(db, turno_id): list[tuple[str, int, Decimal]]  [caja/repository.py]"]},
  "DetalleVenta": {"tipo": "entidad", "origen": B+"ventas/models.py", "tabla": "detalle_venta",
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "venta_id: BIGINT (FK venta, ON DELETE CASCADE)", "variante_id: BIGINT (FK variante_producto)",
      "cantidad: INTEGER", "precio_unitario: NUMERIC(10,2)", "descuento_unitario: NUMERIC(10,2)", "creado_en: TIMESTAMPTZ"],
    "operaciones": ["agregar_detalle(db, venta_id, variante_id, cantidad, precio_unitario, descuento_unitario): DetalleVenta  [pos/repository.py]"]},
  "TurnoCaja": {"tipo": "entidad", "origen": B+"ventas/models.py", "tabla": "turno_caja",
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "caja_id: INTEGER (FK caja)", "usuario_id: BIGINT (FK usuario)", "abierto_en: TIMESTAMPTZ",
      "cerrado_en: TIMESTAMPTZ", "monto_apertura: NUMERIC(10,2)", "monto_cierre: NUMERIC(10,2)", "monto_esperado: NUMERIC(10,2)"],
    "operaciones": ["turno_abierto_de_caja(db, caja_id): TurnoCaja | None  [caja/repository.py]", "turno_abierto_de_usuario(db, usuario_id): TurnoCaja | None  [caja/repository.py]",
      "turno_por_id(db, turno_id): TurnoCaja | None  [caja/repository.py]", "abrir(db, caja_id, usuario_id, monto_apertura): TurnoCaja  [caja/repository.py]"]},
  "Caja": {"tipo": "entidad", "origen": B+"ventas/models.py", "tabla": "caja",
    "atributos": ["id: INTEGER (PK)", "empresa_id: BIGINT (FK empresa)", "sucursal_id: INTEGER (FK sucursal)", "nombre: VARCHAR(50)", "activa: BOOLEAN"],
    "operaciones": ["caja_por_id(db, caja_id): Caja | None  [caja/repository.py]", "cajas_de_sucursal(db, sucursal_id): list[Caja]  [caja/repository.py]",
      "bloquear_caja(db, caja_id): Caja | None  [caja/repository.py]"]},
  "Devolucion": {"tipo": "entidad", "origen": B+"ventas/models.py", "tabla": "devolucion",
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "venta_id: BIGINT (FK venta)", "turno_caja_id: BIGINT (FK turno_caja)", "tipo: VARCHAR(12)",
      "venta_cambio_id: BIGINT (FK venta, UNIQUE)", "motivo: VARCHAR(200)", "monto: NUMERIC(10,2)", "diferencia: NUMERIC(10,2)", "metodo_diferencia: VARCHAR(20)",
      "creado_en: TIMESTAMPTZ"],
    "operaciones": ["devoluciones_del_turno(db, turno_id): Decimal  [caja/repository.py]", "diferencias_de_cambios(db, turno_id): Decimal  [caja/repository.py]"]},
  "Sucursal": {"tipo": "entidad", "origen": B+"organizacion/models.py", "tabla": "sucursal", "nota": OMIT_AUD,
    "atributos": ["id: INTEGER (PK)", "empresa_id: BIGINT (FK empresa)", "ciudad_id: INTEGER (FK ciudad)", "nombre: VARCHAR(80)", "direccion: VARCHAR(200)",
      "telefono: VARCHAR(20)", "horario_apertura: TIME", "horario_cierre: TIME", "capacidad_vestidores: SMALLINT", "activa: BOOLEAN"],
    "operaciones": ["sucursal(db, sucursal_id): Sucursal | None  [offline/repository.py]", "sucursales_activas(db): list[Sucursal]  [offline/repository.py]",
      "sucursal_activa(db, sucursal_id): Sucursal | None  [caja/repository.py]"]},
  "Usuario": {"tipo": "entidad", "origen": B+"seguridad/models.py", "tabla": "usuario", "nota": OMIT_AUD,
    "atributos": ["id: BIGINT (PK)", "correo: VARCHAR(120)", "hash_contrasena: VARCHAR(255)", "nombres: VARCHAR(80)", "apellidos: VARCHAR(80)",
      "rol_id: SMALLINT (FK rol)", "activo: BOOLEAN", "empresa_id: BIGINT (FK empresa)"],
    "operaciones": ["operaciones(db, sucursal_id, usuario_id, estado, por_devolver, limite): list[tuple[OperacionOffline, Usuario]]  [offline/repository.py, JOIN usuario]"]},
  "Existencia": {"tipo": "entidad", "origen": B+"inventario/models.py", "tabla": "existencia", "nota": OMIT_AUD,
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "variante_id: BIGINT (FK variante_producto)", "sucursal_id: INTEGER (FK sucursal)",
      "cantidad_disponible: INTEGER", "cantidad_reservada: INTEGER", "stock_minimo: INTEGER"],
    "operaciones": ["prendas_de_sucursal(db, sucursal_id): list[Row]  [offline/repository.py]", "prendas_en_sucursales_activas(db): list[Row]  [offline/repository.py]",
      "obtener_existencia(db, variante_id, sucursal_id, bloquear): Existencia | None  [inventario/repository.py]",
      "agregar_existencia(db, variante_id, sucursal_id): Existencia  [inventario/repository.py]"]},
  "VarianteProducto": {"tipo": "entidad", "origen": B+"catalogo/models.py", "tabla": "variante_producto", "nota": OMIT_AUD,
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "producto_id: BIGINT (FK producto)", "talla_id: INTEGER (FK talla)", "color_id: INTEGER (FK color)",
      "sku: VARCHAR(40)", "precio: NUMERIC(10,2)", "activa: BOOLEAN"],
    "operaciones": ["prendas_de_sucursal(db, sucursal_id): list[Row]  [offline/repository.py]", "prendas_en_sucursales_activas(db): list[Row]  [offline/repository.py]",
      "prendas_por_id(db, variante_ids, sucursal_id): dict[int, Row]  [pos/repository.py]"]},
  "Reserva": {"tipo": "entidad", "origen": B+"reservas/models.py", "tabla": "reserva", "nota": OMIT_AUD,
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "cliente_id: BIGINT (FK cliente)", "sucursal_id: INTEGER (FK sucursal)",
      "franja_inicio: TIMESTAMPTZ", "franja_fin: TIMESTAMPTZ", "estado: VARCHAR(10)", "observacion: VARCHAR(200)"],
    "operaciones": ["agregar_reserva(db, cliente_id, sucursal_id, franja_inicio, franja_fin, estado, observacion): Reserva  [reservas/repository.py]",
      "contar_reservas_solapadas(db, sucursal_id, inicio, fin): int  [reservas/repository.py]"]},
  "DetalleReserva": {"tipo": "entidad", "origen": B+"reservas/models.py", "tabla": "reserva_detalle", "nota": OMIT_AUD,
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "reserva_id: BIGINT (FK reserva, ON DELETE CASCADE)", "variante_id: BIGINT (FK variante_producto)",
      "cantidad: INTEGER", "resultado_prueba: VARCHAR(10)"],
    "operaciones": ["agregar_detalle(db, reserva_id, variante_id, cantidad): DetalleReserva  [reservas/repository.py]"]},
  "AsientoBitacora": {"tipo": "entidad", "origen": B+"bitacora/models.py", "tabla": "bitacora",
    "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "ocurrido_en: TIMESTAMPTZ", "usuario_id: BIGINT (FK usuario, ON DELETE SET NULL)",
      "actor: VARCHAR(160)", "rol: VARCHAR(40)", "accion: VARCHAR(40)", "entidad: VARCHAR(60)", "entidad_id: VARCHAR(60)", "metodo: VARCHAR(10)",
      "ruta: VARCHAR(300)", "estado_http: INTEGER", "exito: BOOLEAN", "ip: VARCHAR(60)", "agente: VARCHAR(200)", "detalle: JSONB"],
    "operaciones": ["agregar(db, **campos): AsientoBitacora", "contar(db, **filtros): int", "listar(db, limite, desplazamiento, **filtros): list[tuple]",
      "acciones(db): list[str]", "roles(db): list[str]", "entidades(db): list[str]", "ultimo(db): AsientoBitacora | None"]},
}

# FK reales (multiplicidad: primero en el extremo ClaseA, despues en ClaseB)
FK = [
  ["Sucursal","OperacionOffline","ATIENDE","1","0..*"],
  ["Usuario","OperacionOffline","REGISTRA","1","0..*"],
  ["Usuario","OperacionOffline","DEVUELVE","0..1","0..*"],
  ["OperacionOffline","Venta","CONFIRMA","0..1","0..1"],
  ["OperacionOffline","Reserva","CONFIRMA","0..1","0..1"],
  ["TurnoCaja","Venta","AGRUPA","0..1","0..*"],
  ["Sucursal","Venta","VENDE","1","0..*"],
  ["Reserva","Venta","SE_COBRA_EN","0..1","0..1"],
  ["Venta","DetalleVenta","CONTIENE","1","0..*"],
  ["VarianteProducto","DetalleVenta","SE_VENDE_EN","1","0..*"],
  ["Caja","TurnoCaja","TIENE","1","0..*"],
  ["Usuario","TurnoCaja","ABRE","1","0..*"],
  ["Sucursal","Caja","TIENE","1","0..*"],
  ["TurnoCaja","Devolucion","PROCESA","1","0..*"],
  ["Venta","Devolucion","SE_DEVUELVE_EN","1","0..*"],
  ["Venta","Devolucion","SE_CAMBIA_POR","0..1","0..1"],
  ["VarianteProducto","Existencia","TIENE_SALDO_EN","1","0..*"],
  ["Sucursal","Existencia","GUARDA","1","0..*"],
  ["Sucursal","Reserva","RECIBE","1","0..*"],
  ["Reserva","DetalleReserva","CONTIENE","1","0..*"],
  ["VarianteProducto","DetalleReserva","SE_RESERVA_EN","1","0..*"],
  ["Usuario","AsientoBitacora","DEJA_RASTRO_EN","0..1","0..*"],
  # SQLite: logicas, sin FOREIGN KEY declarada
  ["prenda_local","disponible_local","TIENE_SALDO_EN","1","0..*"],
  ["sucursal_local","disponible_local","GUARDA","1","0..*"],
]

def fks(cls):
    s = set(cls)
    return [list(v) for v in FK if v[0] in s and v[1] in s]

def bit(controles):
    return [[c, "BitacoraMiddleware", "ES_ANOTADO_POR", "1", "1"] for c in controles] + [["BitacoraMiddleware","AsientoBitacora","REGISTRA","1","0..*"]]

cus = {}

c13 = ["Pendientes","PantallaSinConexion","OfflineService","ControlOffline","offline_service","paquetes","sucursal_local","prenda_local","disponible_local","Existencia","VarianteProducto","TurnoCaja"]
cus["CU-13"] = {"actores": ["Cajero","Cliente"], "clases": c13,
  "operaciones_en_cu": {"Pendientes": ["preparar()"], "PantallaSinConexion": ["_preparar()"],
     "OfflineService": ["preparar()","probarConexion()","marcarSinRed()"], "ControlOffline": ["preparar()","_guardarFotos(paquete)","marcarSinRed()"],
     "offline_service": ["paquete_de_mostrador(db, usuario_id)","paquete_de_cliente(db)","_sucursal_out(sucursal)","_vigencia(generado)"]},
  "nota": "Solo lectura en el servidor (GET /offline/paquete y GET /offline/paquete-cliente): el middleware no anota GET, por eso no hay bitacora. paquete_de_mostrador exige turno abierto via pos/service.py mostrador_de -> caja/repository.py turno_abierto_de_usuario (TurnoCaja). Omitida la tabla SQLite 'metadato' (vigencia del paquete) por el tope de 12.",
  "relaciones": [["Cajero","Pendientes","USA","1","1"],["Cliente","PantallaSinConexion","USA","1","1"],
    ["Pendientes","OfflineService","SOLICITA","1","1"],["PantallaSinConexion","ControlOffline","SOLICITA","1","1"],
    ["OfflineService","offline_service","DESCARGA_DE","1","1"],["ControlOffline","offline_service","DESCARGA_DE","1","1"],
    ["OfflineService","paquetes","GUARDA","1","0..1"],["ControlOffline","sucursal_local","GUARDA","1","0..*"],
    ["ControlOffline","prenda_local","GUARDA","1","0..*"],["ControlOffline","disponible_local","GUARDA","1","0..*"],
    ["offline_service","TurnoCaja","CONSULTA","1","0..1"],["offline_service","Existencia","CONSULTA","1","0..*"],
    ["offline_service","VarianteProducto","CONSULTA","1","0..*"]] + fks(c13)}

c14 = ["Venta_PWA","OfflineService","paquetes","operaciones","offline_service","BitacoraMiddleware","AsientoBitacora","OperacionOffline","Venta","DetalleVenta","Existencia","TurnoCaja"]
cus["CU-14"] = {"actores": ["Cajero"], "clases": c14,
  "operaciones_en_cu": {"Venta_PWA": ["agregar(prenda)","cambiarCantidad(linea, cantidad)","quitar(linea)","vaciar()","elegirMetodo(metodo)","cobrar()","nuevaVenta()"],
     "OfflineService": ["registrarVenta(operacion, resumen, total)","marcarSinRed()","sincronizar()"],
     "offline_service": ["sincronizar(db, usuario_id, rol, sucursal_del_usuario, lote)","_sincronizar_una(...)","_confirmar_venta(db, op, usuario_id)","_resultado(db, fila, repetida)"]},
  "nota": "La venta se guarda solo en IndexedDB (no llama al servidor). Se confirma en el servidor al sincronizar (POST /offline/sincronizar, CU-17), que es donde se escribe la bitacora. _confirmar_venta llama ademas a pos/service.py generar_codigo_de_venta, inventario/service.py descontar_por_venta (escribe MovimientoInventario, omitido) y ventas/historial_service.py asegurar_comprobante (Comprobante, omitido).",
  "relaciones": [["Cajero","Venta_PWA","USA","1","1"],["Venta_PWA","OfflineService","REGISTRA_EN","1","1"],
    ["OfflineService","paquetes","DESCUENTA_SALDO_EN","1","0..1"],["OfflineService","operaciones","ENCOLA","1","0..*"],
    ["OfflineService","offline_service","SINCRONIZA_CON","1","1"],
    ["offline_service","OperacionOffline","REGISTRA","1","0..*"],["offline_service","Venta","REGISTRA","1","0..*"],
    ["offline_service","DetalleVenta","REGISTRA","1","0..*"],["offline_service","Existencia","DESCUENTA","1","0..*"],
    ["offline_service","TurnoCaja","CONSULTA","1","0..1"]] + bit(["offline_service"]) + fks(c14)}

c15 = ["PantallaReservaSinRed","ControlOffline","operacion_pendiente","prenda_local","disponible_local","offline_service","reservas_service","BitacoraMiddleware","AsientoBitacora","OperacionOffline","Reserva","DetalleReserva"]
cus["CU-15"] = {"actores": ["Cliente"], "clases": c15,
  "operaciones_en_cu": {"ControlOffline": ["reservar(sucursal, prendas, inicio, fin)","_cantidades(cuerpo)","sincronizar()"],
     "offline_service": ["sincronizar(...)","_sincronizar_una(...)","_confirmar_reserva(db, op, usuario_id, rol, sucursal_del_usuario)","_resultado(db, fila, repetida)"],
     "reservas_service": ["registrar_reserva(db, datos, cliente_id, usuario_id)","_validar_franja(datos, sucursal)"]},
  "nota": "reservar() guarda en operacion_pendiente, descuenta disponible_local y dispara sincronizar() sin esperar. La confirmacion del servidor pasa por CU-17. Omitidas por el tope: sucursal_local (de donde salen las sucursales elegibles), Existencia (inventario.apartar_para_reserva) y Notificacion (notificaciones.avisar_reserva_en_sucursal).",
  "relaciones": [["Cliente","PantallaReservaSinRed","USA","1","1"],["PantallaReservaSinRed","ControlOffline","REGISTRA_EN","1","1"],
    ["ControlOffline","operacion_pendiente","ENCOLA","1","0..*"],["ControlOffline","prenda_local","CONSULTA","1","0..*"],
    ["ControlOffline","disponible_local","DESCUENTA","1","0..*"],["ControlOffline","offline_service","SINCRONIZA_CON","1","1"],
    ["offline_service","reservas_service","DELEGA_EN","1","1"],["offline_service","OperacionOffline","REGISTRA","1","0..*"],
    ["reservas_service","Reserva","REGISTRA","1","0..*"],["reservas_service","DetalleReserva","REGISTRA","1","0..*"]] + bit(["offline_service"]) + fks(c15)}

c16 = ["Venta_PWA","OfflineService","operaciones","offline_service","BitacoraMiddleware","AsientoBitacora","OperacionOffline","Venta","TurnoCaja"]
cus["CU-16"] = {"actores": ["Cajero"], "clases": c16,
  "operaciones_en_cu": {"Venta_PWA": ["elegirMetodo(metodo)","cobrar()"], "OfflineService": ["registrarVenta(operacion, resumen, total)"],
     "offline_service": ["_sincronizar_una(...)","_confirmar_venta(db, op, usuario_id)","_por_devolver(fila)"]},
  "nota": "Sin red solo EFECTIVO o QR con referencia (registrarSinRed() descarta TARJETA; CHECK metodo_pago en operacion_offline). El pago viaja en operaciones.operacion.pago y en el servidor queda en operacion_offline.metodo_pago/monto_cobrado/referencia_pago; si se confirma, tambien en venta.metodo_pago. _confirmar_venta rechaza si el efectivo no alcanza o si el QR no es exacto. operacion_offline NO tiene FK a turno_caja: el turno va en carga->>'turno_caja_id'.",
  "relaciones": [["Cajero","Venta_PWA","USA","1","1"],["Venta_PWA","OfflineService","REGISTRA_PAGO_EN","1","1"],
    ["OfflineService","operaciones","GUARDA","1","0..*"],["OfflineService","offline_service","SINCRONIZA_CON","1","1"],
    ["offline_service","OperacionOffline","REGISTRA","1","0..*"],["offline_service","Venta","REGISTRA","1","0..*"],
    ["offline_service","TurnoCaja","CONSULTA","1","0..1"]] + bit(["offline_service"]) + fks(c16)}

c17 = ["Pendientes","PantallaSinConexion","OfflineService","ControlOffline","operaciones","operacion_pendiente","offline_service","BitacoraMiddleware","AsientoBitacora","OperacionOffline","Venta","Reserva"]
cus["CU-17"] = {"actores": ["Cajero","Cliente"], "clases": c17,
  "operaciones_en_cu": {"Pendientes": ["sincronizar()"], "PantallaSinConexion": ["_sincronizar()"],
     "OfflineService": ["sincronizar()","enviar(lote, cuenta)","actualizar(uuid, cambios)","nombreDelDispositivo()","probarConexion()"],
     "ControlOffline": ["sincronizar()","_enviar(lote, cuenta)","_alReloj()"],
     "offline_service": ["sincronizar(db, usuario_id, rol, sucursal_del_usuario, lote)","_sincronizar_una(db, op, usuario_id, rol, sucursal_del_usuario, dispositivo)",
       "_confirmar_venta(db, op, usuario_id)","_confirmar_reserva(db, op, usuario_id, rol, sucursal_del_usuario)","_sucursal_declarada(db, op, usuario_id, sucursal_del_usuario)","_resultado(db, fila, repetida)"]},
  "nota": "Tambien sincroniza sola: evento 'online' y cada 60 s en la web, Timer de 1 min en el movil (_alReloj). El movil manda por RepositorioOffline.sincronizar(operaciones) (data/repositorios/repositorio_offline.dart), omitido. Idempotente por uuid (operacion_por_uuid con FOR UPDATE).",
  "relaciones": [["Cajero","Pendientes","USA","1","1"],["Cliente","PantallaSinConexion","USA","1","1"],
    ["Pendientes","OfflineService","SOLICITA","1","1"],["PantallaSinConexion","ControlOffline","SOLICITA","1","1"],
    ["OfflineService","operaciones","ACTUALIZA","1","0..*"],["ControlOffline","operacion_pendiente","ACTUALIZA","1","0..*"],
    ["OfflineService","offline_service","ENVIA_LOTE_A","1","1"],["ControlOffline","offline_service","ENVIA_LOTE_A","1","1"],
    ["offline_service","OperacionOffline","REGISTRA","1","0..*"],["offline_service","Venta","REGISTRA","1","0..*"],
    ["offline_service","Reserva","REGISTRA","1","0..*"]] + bit(["offline_service"]) + fks(c17)}

c18 = ["Pendientes","PantallaSinConexion","OfflineService","ControlOffline","operaciones","operacion_pendiente"]
cus["CU-18"] = {"actores": ["Cajero","Cliente"], "clases": c18,
  "operaciones_en_cu": {"Pendientes": ["limpiar()"], "PantallaSinConexion": ["_sincronizar()"],
     "OfflineService": ["cargar()","limpiarConfirmadas()"], "ControlOffline": ["_cargar()","limpiarDecididas()"]},
  "nota": "Todo local: la cola se lee de IndexedDB / SQLite (signals operaciones y pendientes en la web; EstadoOffline.pendientes en el movil). El backend tiene GET /offline/operaciones/mias (offline_service.operaciones_mias) pero NINGUN cliente lo llama, por eso no se incluye. Sin escritura en el servidor = sin bitacora.",
  "relaciones": [["Cajero","Pendientes","USA","1","1"],["Cliente","PantallaSinConexion","USA","1","1"],
    ["Pendientes","OfflineService","CONSULTA","1","1"],["PantallaSinConexion","ControlOffline","CONSULTA","1","1"],
    ["OfflineService","operaciones","CONSULTA","1","0..*"],["ControlOffline","operacion_pendiente","CONSULTA","1","0..*"]] + fks(c18)}

c19 = ["Rechazadas","OfflineService","offline_service","BitacoraMiddleware","AsientoBitacora","OperacionOffline","Usuario","Sucursal"]
cus["CU-19"] = {"actores": ["Encargado"], "clases": c19,
  "operaciones_en_cu": {"OfflineService": ["deSucursal(porDevolver)","registrarDevolucion(uuid, datos)"],
     "offline_service": ["operaciones_de_sucursal(db, sucursal_id, estado, por_devolver)","registrar_devolucion(db, uuid, datos, usuario_id, sucursal_id)","_operacion_out(db, fila, usuario)","_por_devolver(fila)","_ahora()"]},
  "nota": "El router tambien deja entrar al ADMINISTRADOR (ve todas las sucursales). No escribe movimiento de caja: la devolucion solo llena devuelto_en/devuelto_por/metodo_devolucion/referencia_devolucion/observacion_devolucion en operacion_offline.",
  "relaciones": [["Encargado","Rechazadas","USA","1","1"],["Rechazadas","OfflineService","SOLICITA","1","1"],
    ["OfflineService","offline_service","CONSULTA","1","1"],["offline_service","OperacionOffline","ACTUALIZA","1","0..*"],
    ["offline_service","Usuario","CONSULTA","1","0..*"]] + bit(["offline_service"]) + fks(c19)}

c20 = ["Turno","CajaService","OfflineService","caja_service","BitacoraMiddleware","AsientoBitacora","Caja","TurnoCaja","Venta","Devolucion","OperacionOffline","Sucursal"]
cus["CU-20"] = {"actores": ["Cajero"], "clases": c20,
  "operaciones_en_cu": {"OfflineService": ["sincronizar()"]},
  "nota": "Turno.cerrar() primero llama a OfflineService.sincronizar() si hay ventas sin subir de este turno (sinSubir); si quedan, no deja cerrar; si subieron, recarga miTurno() y pide volver a cerrar. esperado = apertura + efectivo_cobrado - devoluciones_del_turno + diferencias_de_cambios + efectivo_por_devolver. Las rutas de /caja admiten CAJERO y ENCARGADO.",
  "relaciones": [["Cajero","Turno","USA","1","1"],["Turno","CajaService","SOLICITA","1","1"],["Turno","OfflineService","SINCRONIZA_ANTES_DE_CERRAR","1","1"],
    ["CajaService","caja_service","LLAMA_A","1","1"],["caja_service","Caja","CONSULTA","1","0..*"],["caja_service","TurnoCaja","REGISTRA","1","0..*"],
    ["caja_service","Venta","CONSULTA","1","0..*"],["caja_service","Devolucion","CONSULTA","1","0..*"],
    ["caja_service","OperacionOffline","CONSULTA","1","0..*"],["caja_service","Sucursal","CONSULTA","1","0..1"]] + bit(["caja_service"]) + fks(c20)}

for cu, d in cus.items():
    assert 6 <= len(d["clases"]) <= 12, (cu, len(d["clases"]))
    for c in d["clases"]:
        assert c in clases, (cu, c)
    for r in d["relaciones"]:
        for x in r[:2]:
            assert x in d["clases"] or x in d["actores"], (cu, r)
    for c in d.get("operaciones_en_cu", {}):
        assert c in d["clases"], (cu, c)

data = {"_convencion": "relaciones: [ClaseA, ClaseB, ROL, multiplicidad en el extremo de ClaseA, multiplicidad en el extremo de ClaseB]. 'operaciones_en_cu' (opcional) dice que operaciones de una clase compartida se usan en ese CU; si una clase no figura ahi, se usan todas. Las asociaciones prenda_local/sucursal_local -> disponible_local son logicas (SQLite sin FOREIGN KEY). En las entidades del backend, '[archivo]' al final de una operacion dice en que repository.py esta.",
        "clases": clases, "cus": cus}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
for cu, d in cus.items():
    print(cu, len(d["clases"]), len(d["relaciones"]))
print("clases", len(clases))
