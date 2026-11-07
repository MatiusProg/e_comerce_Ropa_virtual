/// Aporte propio · «Avísame cuando llegue mi talla».
///
/// El cliente pide, desde la ficha, que le avisen cuando una talla y color sin
/// unidades vuelvan a tener. El aviso le llega por push, correo y la campanita.
library;

import 'package:dio/dio.dart';

import '../../core/red/excepciones.dart';

class RepositorioAvisosTalla {
  const RepositorioAvisosTalla(this._dio);

  final Dio _dio;

  /// Las variantes que el cliente ya está esperando.
  Future<Set<int>> esperadas() async {
    try {
      final r = await _dio.get<List<dynamic>>('/tienda/avisos-talla/variantes');
      return (r.data ?? const []).map((e) => e as int).toSet();
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// Pide el aviso. Es idempotente: pedirlo dos veces deja uno solo.
  Future<void> pedir(int varianteId) async {
    try {
      await _dio.post<void>(
        '/tienda/avisos-talla',
        data: {'variante_id': varianteId},
      );
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }
}
