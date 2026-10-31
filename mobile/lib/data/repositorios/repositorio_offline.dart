/// Acceso a `/offline` (2do parcial, CU-13 y CU-17), lado del cliente.
library;

import 'package:dio/dio.dart';

import '../../core/red/excepciones.dart';
import '../modelos/offline.dart';

/// El servidor no contesto: sin red, o un intermediario respondio 504. No es
/// un rechazo de la operacion y no tiene que sacarla de la cola.
class SinRespuesta implements Exception {
  const SinRespuesta();
}

class RepositorioOffline {
  const RepositorioOffline(this._dio);

  final Dio _dio;

  /// CU-13 · Sucursales y prendas con su saldo por sucursal.
  Future<PaqueteCliente> descargarPaquete() async {
    try {
      final r = await _dio.get<Map<String, dynamic>>('/offline/paquete-cliente');
      return PaqueteCliente.desdeJson(r.data!);
    } on DioException catch (fallo) {
      throw _traducir(fallo);
    }
  }

  /// CU-17 · Manda un lote; devuelve lo que decidio el servidor por cada una.
  ///
  /// Lanza [SinRespuesta] si no hubo respuesta, y [ErrorApi] si el servidor
  /// no acepto el lote entero (ninguna se decidio).
  Future<List<ResultadoSincronizacion>> sincronizar(
    List<Map<String, dynamic>> operaciones,
  ) async {
    try {
      final r = await _dio.post<Map<String, dynamic>>(
        '/offline/sincronizar',
        data: {'dispositivo': 'movil', 'operaciones': operaciones},
      );
      return (r.data!['resultados'] as List)
          .cast<Map<String, dynamic>>()
          .map(ResultadoSincronizacion.desdeJson)
          .toList();
    } on DioException catch (fallo) {
      throw _traducir(fallo);
    }
  }

  /// ¿Volvio el servidor? `/health` vive fuera de `/api/v1`.
  Future<bool> hayConexion() async {
    try {
      final base = _dio.options.baseUrl.replaceFirst(RegExp(r'/api/v1/?$'), '');
      await _dio.get<dynamic>('$base/health');
      return true;
    } on DioException {
      return false;
    }
  }

  Exception _traducir(DioException fallo) {
    final codigo = fallo.response?.statusCode;
    if (fallo.type != DioExceptionType.badResponse || codigo == 504) {
      return const SinRespuesta();
    }
    return traducirError(fallo);
  }
}
