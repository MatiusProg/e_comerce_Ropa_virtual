/// Modelos del trabajo sin conexion (2do parcial, CU-13 a CU-18).
///
/// Espejo de `backend/app/modules/offline/schemas.py`. En el movil solo el
/// lado del **cliente**: el paquete para reservar y la reserva offline
/// (CU-15). La venta de mostrador sin red vive en la web.
library;

class SucursalOffline {
  const SucursalOffline({
    required this.id,
    required this.nombre,
    required this.apertura,
    required this.cierre,
  });

  final int id;
  final String nombre;

  /// `HH:mm`, la hora de pared de la tienda.
  final String apertura;
  final String cierre;

  factory SucursalOffline.desdeJson(Map<String, dynamic> json) =>
      SucursalOffline(
        id: json['id'] as int,
        nombre: json['nombre'] as String,
        apertura: json['horario_apertura'] as String,
        cierre: json['horario_cierre'] as String,
      );
}

/// Una prenda con lo que hay de ella en cada sucursal, al descargar.
class PrendaOffline {
  const PrendaOffline({
    required this.varianteId,
    required this.sku,
    required this.producto,
    required this.talla,
    required this.color,
    required this.precio,
    required this.disponiblePorSucursal,
  });

  final int varianteId;
  final String sku;
  final String producto;
  final String talla;
  final String color;

  /// Como texto, igual que lo manda la API: el dinero no pasa por `double`.
  final String precio;
  final Map<int, int> disponiblePorSucursal;

  String get nombre => '$producto · $talla · $color';

  factory PrendaOffline.desdeJson(Map<String, dynamic> json) => PrendaOffline(
    varianteId: json['variante_id'] as int,
    sku: json['sku'] as String,
    producto: json['producto'] as String,
    talla: json['talla'] as String,
    color: json['color'] as String,
    precio: json['precio'].toString(),
    disponiblePorSucursal: {
      for (final s in (json['sucursales'] as List).cast<Map<String, dynamic>>())
        s['sucursal_id'] as int: s['disponible'] as int,
    },
  );
}

/// CU-13: lo que el cliente se lleva al telefono.
class PaqueteCliente {
  const PaqueteCliente({
    required this.generadoEn,
    required this.vigenteHasta,
    required this.sucursales,
    required this.prendas,
  });

  final DateTime generadoEn;
  final DateTime vigenteHasta;
  final List<SucursalOffline> sucursales;
  final List<PrendaOffline> prendas;

  /// RF-13: pasada la vigencia se avisa; no se bloquea.
  bool get vencido => DateTime.now().isAfter(vigenteHasta);

  factory PaqueteCliente.desdeJson(Map<String, dynamic> json) => PaqueteCliente(
    generadoEn: DateTime.parse(json['generado_en'] as String).toLocal(),
    vigenteHasta: DateTime.parse(json['vigente_hasta'] as String).toLocal(),
    sucursales: (json['sucursales'] as List)
        .cast<Map<String, dynamic>>()
        .map(SucursalOffline.desdeJson)
        .toList(),
    prendas: (json['prendas'] as List)
        .cast<Map<String, dynamic>>()
        .map(PrendaOffline.desdeJson)
        .toList(),
  );
}

/// Los estados de RF-20 del lado del telefono. `local` y `enviada` solo
/// existen aca; el servidor responde `confirmada` o `rechazada`.
/// `enConflicto` es la que el servidor no pudo ni decidir (el pedido mismo
/// fallo): queda a la vista y no se borra (RNF06).
enum EstadoOperacion {
  local('local', 'Guardada'),
  enviada('enviada', 'Enviada'),
  confirmada('confirmada', 'Confirmada'),
  rechazada('rechazada', 'Rechazada'),
  enConflicto('en_conflicto', 'En conflicto');

  const EstadoOperacion(this.codigo, this.etiqueta);

  final String codigo;
  final String etiqueta;

  bool get pendiente =>
      this == local || this == enviada || this == enConflicto;

  static EstadoOperacion desdeCodigo(String codigo) =>
      values.firstWhere((e) => e.codigo == codigo, orElse: () => local);
}

/// Una operacion guardada en SQLite, con lo que se sabe de ella.
class OperacionGuardada {
  const OperacionGuardada({
    required this.uuid,
    required this.estado,
    required this.cuerpo,
    required this.resumen,
    required this.creadaEn,
    this.intentos = 0,
    this.motivo,
    this.reservaId,
  });

  final String uuid;
  final EstadoOperacion estado;

  /// Lo que viaja tal cual al servidor en CU-17.
  final Map<String, dynamic> cuerpo;
  final String resumen;
  final DateTime creadaEn;
  final int intentos;
  final String? motivo;
  final int? reservaId;

  OperacionGuardada copiarCon({
    EstadoOperacion? estado,
    int? intentos,
    String? motivo,
    int? reservaId,
  }) => OperacionGuardada(
    uuid: uuid,
    estado: estado ?? this.estado,
    cuerpo: cuerpo,
    resumen: resumen,
    creadaEn: creadaEn,
    intentos: intentos ?? this.intentos,
    motivo: motivo ?? this.motivo,
    reservaId: reservaId ?? this.reservaId,
  );
}

/// La respuesta del servidor por cada operacion (CU-17).
class ResultadoSincronizacion {
  const ResultadoSincronizacion({
    required this.uuid,
    required this.confirmada,
    this.motivo,
    this.reservaId,
  });

  final String uuid;
  final bool confirmada;
  final String? motivo;
  final int? reservaId;

  factory ResultadoSincronizacion.desdeJson(Map<String, dynamic> json) =>
      ResultadoSincronizacion(
        uuid: json['uuid'] as String,
        confirmada: json['estado'] == 'CONFIRMADA',
        motivo: json['motivo'] as String?,
        reservaId: json['reserva_id'] as int?,
      );
}
