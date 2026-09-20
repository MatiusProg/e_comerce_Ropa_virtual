/// CU-36 · Tablero de indicadores y CU-42 · Bitácora — modelos del contrato.
///
/// Espejo de `backend/app/modules/reportes/tablero_schemas.py` y de
/// `backend/app/modules/bitacora/schemas.py`.
///
/// LOS IMPORTES VIAJAN COMO TEXTO
/// -------------------------------
/// Igual que en el resto de la app: el servidor los declara `NUMERIC(10,2)` y
/// pasarlos por coma flotante mete el redondeo binario justo en el dinero.
/// Acá se guardan como cadena y se muestran tal cual.
library;

import '../../core/hora_boliviana.dart';

// =====================================================================
// CU-36 · Tablero
// =====================================================================

class PeriodoTablero {
  const PeriodoTablero({
    required this.desde,
    required this.hasta,
    this.sucursal,
  });

  final DateTime desde;
  final DateTime hasta;
  final String? sucursal;

  factory PeriodoTablero.desdeJson(Map<String, dynamic> j) => PeriodoTablero(
    desde: DateTime.parse(j['desde'] as String),
    hasta: DateTime.parse(j['hasta'] as String),
    sucursal: j['sucursal'] as String?,
  );
}

class ReservasPorEstado {
  const ReservasPorEstado({
    required this.pendientes,
    required this.preparadas,
    required this.atendidas,
    required this.canceladas,
    required this.expiradas,
    required this.total,
  });

  final int pendientes;
  final int preparadas;
  final int atendidas;
  final int canceladas;
  final int expiradas;
  final int total;

  factory ReservasPorEstado.desdeJson(Map<String, dynamic> j) =>
      ReservasPorEstado(
        pendientes: j['pendientes'] as int? ?? 0,
        preparadas: j['preparadas'] as int? ?? 0,
        atendidas: j['atendidas'] as int? ?? 0,
        canceladas: j['canceladas'] as int? ?? 0,
        expiradas: j['expiradas'] as int? ?? 0,
        total: j['total'] as int? ?? 0,
      );
}

class Conversion {
  const Conversion({
    required this.cerradas,
    required this.atendidas,
    required this.tasaAtencion,
    required this.lineasProbadas,
    required this.lineasLlevadas,
    required this.tasaPrueba,
  });

  final int cerradas;
  final int atendidas;

  /// Nula cuando no hay denominador. **No se reemplaza por cero**: «no hubo
  /// reservas cerradas» y «ninguna se atendió» son cosas distintas, y un 0 %
  /// sobre nada se lee como un fracaso que no ocurrió.
  final double? tasaAtencion;

  final int lineasProbadas;
  final int lineasLlevadas;
  final double? tasaPrueba;

  factory Conversion.desdeJson(Map<String, dynamic> j) => Conversion(
    cerradas: j['cerradas'] as int? ?? 0,
    atendidas: j['atendidas'] as int? ?? 0,
    tasaAtencion: (j['tasa_atencion'] as num?)?.toDouble(),
    lineasProbadas: j['lineas_probadas'] as int? ?? 0,
    lineasLlevadas: j['lineas_llevadas'] as int? ?? 0,
    tasaPrueba: (j['tasa_prueba'] as num?)?.toDouble(),
  );
}

class PrendaDestacada {
  const PrendaDestacada({
    required this.sku,
    required this.producto,
    required this.talla,
    required this.color,
    required this.unidades,
  });

  final String sku;
  final String producto;
  final String talla;
  final String color;
  final int unidades;

  factory PrendaDestacada.desdeJson(Map<String, dynamic> j) => PrendaDestacada(
    sku: '${j['sku']}',
    producto: '${j['producto']}',
    talla: '${j['talla']}',
    color: '${j['color']}',
    unidades: j['unidades'] as int? ?? 0,
  );
}

class SaludInventario {
  const SaludInventario({
    required this.totalDisponible,
    required this.totalReservado,
    required this.enAlerta,
    required this.variantesSinStock,
  });

  final int totalDisponible;
  final int totalReservado;
  final int enAlerta;
  final int variantesSinStock;

  factory SaludInventario.desdeJson(Map<String, dynamic> j) => SaludInventario(
    totalDisponible: j['total_disponible'] as int? ?? 0,
    totalReservado: j['total_reservado'] as int? ?? 0,
    enAlerta: j['en_alerta'] as int? ?? 0,
    variantesSinStock: j['variantes_sin_stock'] as int? ?? 0,
  );
}

class AlertaStock {
  const AlertaStock({
    required this.sku,
    required this.producto,
    required this.talla,
    required this.color,
    required this.sucursal,
    required this.disponible,
    required this.minimo,
  });

  final String sku;
  final String producto;
  final String talla;
  final String color;
  final String sucursal;
  final int disponible;
  final int minimo;

  factory AlertaStock.desdeJson(Map<String, dynamic> j) => AlertaStock(
    sku: '${j['sku']}',
    producto: '${j['producto']}',
    talla: '${j['talla']}',
    color: '${j['color']}',
    sucursal: '${j['sucursal']}',
    disponible: j['cantidad_disponible'] as int? ?? 0,
    minimo: j['stock_minimo'] as int? ?? 0,
  );
}

class Ventas {
  const Ventas({
    required this.disponible,
    this.montoHoy,
    this.montoPeriodo,
    this.cantidadPeriodo,
    this.ticketPromedio,
    this.masVendidas = const [],
    this.motivo,
  });

  /// `false` cuando el paquete de ventas todavía no puede contestar. En ese
  /// caso `motivo` dice por qué, y la tarjeta muestra eso en vez de ceros —
  /// un cero afirma que no se vendió nada, que es distinto de no saber.
  final bool disponible;

  final String? montoHoy;
  final String? montoPeriodo;
  final int? cantidadPeriodo;
  final String? ticketPromedio;
  final List<PrendaDestacada> masVendidas;
  final String? motivo;

  factory Ventas.desdeJson(Map<String, dynamic> j) => Ventas(
    disponible: j['disponible'] as bool? ?? false,
    montoHoy: j['monto_hoy']?.toString(),
    montoPeriodo: j['monto_periodo']?.toString(),
    cantidadPeriodo: j['cantidad_periodo'] as int?,
    ticketPromedio: j['ticket_promedio']?.toString(),
    masVendidas: ((j['mas_vendidas'] as List?) ?? const [])
        .map((p) => PrendaDestacada.desdeJson(p as Map<String, dynamic>))
        .toList(growable: false),
    motivo: j['motivo'] as String?,
  );
}

class Tablero {
  const Tablero({
    required this.periodo,
    required this.calculadoEn,
    required this.reservas,
    required this.conversion,
    required this.masReservadas,
    required this.inventario,
    required this.alertas,
    required this.ventas,
  });

  final PeriodoTablero periodo;

  /// Cuándo se calculó. El tablero es «en tiempo real» (RF24) y la pantalla
  /// tiene que poder decir desde cuándo no se refresca.
  final DateTime calculadoEn;

  final ReservasPorEstado reservas;
  final Conversion conversion;
  final List<PrendaDestacada> masReservadas;
  final SaludInventario inventario;
  final List<AlertaStock> alertas;
  final Ventas ventas;

  factory Tablero.desdeJson(Map<String, dynamic> j) => Tablero(
    periodo: PeriodoTablero.desdeJson(
      (j['periodo'] as Map<String, dynamic>?) ?? const {},
    ),
    calculadoEn: DateTime.parse(j['calculado_en'] as String),
    reservas: ReservasPorEstado.desdeJson(
      (j['reservas'] as Map<String, dynamic>?) ?? const {},
    ),
    conversion: Conversion.desdeJson(
      (j['conversion'] as Map<String, dynamic>?) ?? const {},
    ),
    masReservadas: ((j['mas_reservadas'] as List?) ?? const [])
        .map((p) => PrendaDestacada.desdeJson(p as Map<String, dynamic>))
        .toList(growable: false),
    inventario: SaludInventario.desdeJson(
      (j['inventario'] as Map<String, dynamic>?) ?? const {},
    ),
    alertas: ((j['alertas'] as List?) ?? const [])
        .map((a) => AlertaStock.desdeJson(a as Map<String, dynamic>))
        .toList(growable: false),
    ventas: Ventas.desdeJson((j['ventas'] as Map<String, dynamic>?) ?? const {}),
  );
}

// =====================================================================
// CU-42 · Bitácora
// =====================================================================

class AsientoBitacora {
  const AsientoBitacora({
    required this.id,
    required this.ocurridoEn,
    required this.accion,
    required this.metodo,
    required this.ruta,
    required this.estadoHttp,
    required this.exito,
    this.actor,
    this.nombre,
    this.rol,
    this.entidad,
    this.entidadId,
    this.ip,
  });

  final int id;

  /// El instante en que pasó, **en UTC**.
  ///
  /// El servidor lo manda ya en hora boliviana (`…T13:16:13-04:00`), pero
  /// `DateTime.parse` convierte a UTC al leerlo. Para mostrarlo va
  /// [ocurridoEnBolivia]: formatear este directo imprime cuatro horas de
  /// más, que es el defecto que se corrigió el 20/09.
  final DateTime ocurridoEn;

  /// Lo que se muestra. Ver `core/hora_boliviana.dart`.
  DateTime get ocurridoEnBolivia => enHoraBoliviana(ocurridoEn);

  final String accion;
  final String metodo;
  final String ruta;
  final int estadoHttp;
  final bool exito;

  /// El correo tal como estaba cuando pasó.
  final String? actor;

  /// El nombre completo, si la cuenta todavía existe.
  final String? nombre;

  final String? rol;
  final String? entidad;
  final String? entidadId;
  final String? ip;

  /// Quién lo hizo: el nombre si la cuenta existe, el correo si no.
  String get quien => (nombre?.trim().isNotEmpty ?? false)
      ? nombre!.trim()
      : (actor ?? 'Sin identificar');

  /// `CREAR_RECHAZADO` se lee «Crear rechazado».
  String get accionLegible {
    final p = accion.toLowerCase().replaceAll('_', ' ');
    return p.isEmpty ? p : '${p[0].toUpperCase()}${p.substring(1)}';
  }

  /// Lo que se lee como título: **la acción Y sobre qué**.
  ///
  /// «Crear» a secas no dice nada: hay que abrir la ruta para enterarse de
  /// qué se creó, y la ruta está en letra chica y en inglés de la API.
  /// «Crear categoría #7» se entiende de un vistazo, que es para lo que se
  /// abre una bitácora.
  ///
  /// El identificador solo cuando lo hay: en un alta todavía no existe.
  String get titulo {
    if (entidad == null || entidad!.isEmpty) return accionLegible;
    final cual = entidadId == null ? '' : ' #$entidadId';
    return '$accionLegible $entidad$cual';
  }

  factory AsientoBitacora.desdeJson(Map<String, dynamic> j) => AsientoBitacora(
    id: j['id'] as int,
    ocurridoEn: DateTime.parse(j['ocurrido_en'] as String),
    accion: '${j['accion']}',
    metodo: '${j['metodo']}',
    ruta: '${j['ruta']}',
    estadoHttp: j['estado_http'] as int? ?? 0,
    exito: j['exito'] as bool? ?? false,
    actor: j['actor'] as String?,
    nombre: j['nombre'] as String?,
    rol: j['rol'] as String?,
    entidad: j['entidad'] as String?,
    entidadId: j['entidad_id'] as String?,
    ip: j['ip'] as String?,
  );
}

class PaginaBitacora {
  const PaginaBitacora({
    required this.total,
    required this.pagina,
    required this.tamano,
    required this.items,
  });

  final int total;
  final int pagina;
  final int tamano;
  final List<AsientoBitacora> items;

  bool get hayMas => pagina * tamano < total;

  factory PaginaBitacora.desdeJson(Map<String, dynamic> j) => PaginaBitacora(
    total: j['total'] as int? ?? 0,
    pagina: j['pagina'] as int? ?? 1,
    tamano: j['tamano'] as int? ?? 0,
    items: ((j['items'] as List?) ?? const [])
        .map((a) => AsientoBitacora.desdeJson(a as Map<String, dynamic>))
        .toList(growable: false),
  );
}
