/// Modelos del inventario de la sucursal (2do parcial, CU-21).
///
/// Espejo de `PaqueteDeInventarioOut` y `KardexOut` del backend. Lo usa el
/// ENCARGADO: consulta el saldo y el kardex, y registra ingresos y conteos
/// también sin conexión, por la misma cola de CU-17.
library;

/// Una prenda con su saldo en la sucursal del encargado, al descargar (menos
/// o más lo que se registró en el teléfono y todavía no se confirmó).
class PrendaInventario {
  const PrendaInventario({
    required this.varianteId,
    required this.sku,
    required this.producto,
    required this.talla,
    required this.color,
    required this.disponible,
    required this.reservada,
    required this.stockMinimo,
  });

  final int varianteId;
  final String sku;
  final String producto;
  final String talla;
  final String color;
  final int disponible;
  final int reservada;
  final int stockMinimo;

  /// Lo que hay en la percha: un conteo se compara contra esto.
  int get fisica => disponible + reservada;

  bool get bajoMinimo => stockMinimo > 0 && disponible <= stockMinimo;

  String get nombre => '$producto · $talla · $color';

  factory PrendaInventario.desdeJson(Map<String, dynamic> json) =>
      PrendaInventario(
        varianteId: json['variante_id'] as int,
        sku: json['sku'] as String,
        producto: json['producto'] as String,
        talla: json['talla'] as String,
        color: json['color'] as String,
        disponible: json['disponible'] as int,
        reservada: json['reservada'] as int,
        stockMinimo: json['stock_minimo'] as int,
      );
}

class ProveedorLocal {
  const ProveedorLocal({required this.id, required this.razonSocial});

  final int id;
  final String razonSocial;
}

/// CU-21: lo que el encargado se lleva al teléfono.
class PaqueteInventario {
  const PaqueteInventario({
    required this.generadoEn,
    required this.vigenteHasta,
    required this.sucursalId,
    required this.sucursal,
    required this.prendas,
    required this.proveedores,
  });

  final DateTime generadoEn;
  final DateTime vigenteHasta;
  final int sucursalId;
  final String sucursal;
  final List<PrendaInventario> prendas;
  final List<ProveedorLocal> proveedores;

  bool get vencido => DateTime.now().isAfter(vigenteHasta);

  factory PaqueteInventario.desdeJson(Map<String, dynamic> json) {
    final sucursal = json['sucursal'] as Map<String, dynamic>;
    return PaqueteInventario(
      generadoEn: DateTime.parse(json['generado_en'] as String).toLocal(),
      vigenteHasta: DateTime.parse(json['vigente_hasta'] as String).toLocal(),
      sucursalId: sucursal['id'] as int,
      sucursal: sucursal['nombre'] as String,
      prendas: (json['prendas'] as List)
          .cast<Map<String, dynamic>>()
          .map(PrendaInventario.desdeJson)
          .toList(),
      proveedores: [
        for (final p in (json['proveedores'] as List).cast<Map<String, dynamic>>())
          ProveedorLocal(id: p['id'] as int, razonSocial: p['razon_social'] as String),
      ],
    );
  }
}

/// RF-53: una fila del kardex, con el saldo que dejó.
class MovimientoKardex {
  const MovimientoKardex({
    required this.creadoEn,
    required this.tipo,
    required this.cantidad,
    required this.saldo,
    required this.motivo,
    required this.referencia,
    required this.usuario,
    required this.sinConexion,
  });

  final DateTime creadoEn;
  final String tipo;
  final int cantidad;
  final int saldo;
  final String? motivo;
  final String? referencia;
  final String? usuario;
  final bool sinConexion;

  factory MovimientoKardex.desdeJson(Map<String, dynamic> json) => MovimientoKardex(
        creadoEn: DateTime.parse(json['creado_en'] as String).toLocal(),
        tipo: json['tipo'] as String,
        cantidad: json['cantidad'] as int,
        saldo: json['saldo'] as int,
        motivo: json['motivo'] as String?,
        referencia: json['referencia'] as String?,
        usuario: json['usuario'] as String?,
        sinConexion: json['sin_conexion'] as bool,
      );
}

class Kardex {
  const Kardex({
    required this.nombre,
    required this.sku,
    required this.disponible,
    required this.reservada,
    required this.total,
    required this.movimientos,
  });

  final String nombre;
  final String sku;
  final int disponible;
  final int reservada;
  final int total;
  final List<MovimientoKardex> movimientos;

  factory Kardex.desdeJson(Map<String, dynamic> json) => Kardex(
        nombre: '${json['producto']} · ${json['talla']} · ${json['color']}',
        sku: json['sku'] as String,
        disponible: json['disponible'] as int,
        reservada: json['reservada'] as int,
        total: json['total'] as int,
        movimientos: (json['items'] as List)
            .cast<Map<String, dynamic>>()
            .map(MovimientoKardex.desdeJson)
            .toList(),
      );
}
