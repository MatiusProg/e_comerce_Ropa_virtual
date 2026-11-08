/// CU-46 · Consultar mis comprobantes por voz (el «reporte transaccional»).
///
/// Al servidor le llega TEXTO: el dictado corre en el teléfono, igual que en
/// CU-35. El servidor interpreta la frase solo con reglas (no gasta el cupo de
/// IA de la tienda) y devuelve los comprobantes del cliente.
///
/// EL QR LLEGA COMO MATRIZ
/// -----------------------
/// `GET /publico/comprobantes/{token}/qr` devuelve los módulos del QR como
/// filas de «1» y «0», y la pantalla los pinta con un `CustomPainter`. Así no
/// hace falta sumar una librería de QR (ni una de SVG) al proyecto.
library;

import 'package:dio/dio.dart';

import '../../core/red/excepciones.dart';

class ComprobanteCliente {
  const ComprobanteCliente({
    required this.tipo,
    required this.documento,
    required this.codigo,
    required this.referencia,
    required this.fechaTexto,
    required this.total,
    required this.estado,
    required this.detalle,
    required this.token,
    required this.urlVerificacion,
    required this.descargable,
  });

  factory ComprobanteCliente.desdeJson(Map<String, dynamic> j) =>
      ComprobanteCliente(
        tipo: j['tipo'] as String,
        documento: j['documento'] as String?,
        codigo: j['codigo'] as String,
        referencia: j['referencia'] as String,
        fechaTexto: j['fecha_texto'] as String,
        total: '${j['total']}',
        estado: j['estado'] as String,
        detalle: j['detalle'] as String?,
        token: j['token'] as String?,
        urlVerificacion: j['url_verificacion'] as String?,
        descargable: j['descargable'] as bool? ?? false,
      );

  /// COMPRA o DEVOLUCION.
  final String tipo;

  /// RECIBO, NOTA_DEVOLUCION, NOTA_CAMBIO; null si la compra no se pagó.
  final String? documento;
  final String codigo;
  final String referencia;

  /// Ya en hora de Bolivia, armada por el servidor.
  final String fechaTexto;
  final String total;
  final String estado;
  final String? detalle;
  final String? token;
  final String? urlVerificacion;
  final bool descargable;

  String get rotuloDocumento => switch (documento) {
        'RECIBO' => 'Recibo',
        'NOTA_DEVOLUCION' => 'Nota de devolución',
        'NOTA_CAMBIO' => 'Nota de cambio',
        _ => 'Pedido sin pagar',
      };

  String get rotuloEstado => switch (estado) {
        'PAGADA' => 'Pagada',
        'ENTREGADA' => 'Entregada',
        'PENDIENTE_PAGO' => 'Pendiente de pago',
        'CANCELADA' => 'Cancelada',
        'ABIERTA' => 'Abierta',
        'CERRADA' => 'Cerrada',
        _ => estado,
      };
}

class ResultadoComprobantes {
  const ResultadoComprobantes({
    required this.entendido,
    required this.resumen,
    required this.motivo,
    required this.ejemplos,
    required this.avisos,
    required this.items,
  });

  factory ResultadoComprobantes.desdeJson(Map<String, dynamic> j) =>
      ResultadoComprobantes(
        entendido: j['entendido'] as bool? ?? false,
        resumen: j['resumen'] as String?,
        motivo: j['motivo'] as String?,
        ejemplos: [for (final e in (j['ejemplos'] as List? ?? const [])) '$e'],
        avisos: [for (final a in (j['avisos'] as List? ?? const [])) '$a'],
        items: [
          for (final i in (j['items'] as List? ?? const []))
            ComprobanteCliente.desdeJson(i as Map<String, dynamic>),
        ],
      );

  final bool entendido;
  final String? resumen;
  final String? motivo;
  final List<String> ejemplos;
  final List<String> avisos;
  final List<ComprobanteCliente> items;
}

class RepositorioMisComprobantes {
  const RepositorioMisComprobantes(this._dio);

  final Dio _dio;

  Future<ResultadoComprobantes> consultar(String texto) async {
    try {
      final r = await _dio.post<Map<String, dynamic>>(
        '/tienda/mis-comprobantes/consulta',
        data: {'texto': texto},
      );
      return ResultadoComprobantes.desdeJson(r.data ?? const {});
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// Los módulos del QR del comprobante (filas de «1» y «0»).
  Future<List<String>> qr(String token) async {
    try {
      final r = await _dio.get<Map<String, dynamic>>(
        '/publico/comprobantes/${Uri.encodeComponent(token)}/qr',
      );
      return [for (final f in (r.data?['modulos'] as List? ?? const [])) '$f'];
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }
}
