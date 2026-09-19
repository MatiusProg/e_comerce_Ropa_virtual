/// CU-20 · Gestionar favoritos. Acceso a los cuatro endpoints de `/tienda/favoritos`.
///
/// POR QUE HAY UN ENDPOINT SOLO DE IDENTIFICADORES
/// -----------------------------------------------
/// `GET /favoritos` trae las tarjetas completas ---foto, precios, colores---
/// y sirve para la pantalla de favoritos. Pero el catalogo necesita otra cosa:
/// saber cuales de las prendas que esta mostrando son favoritas, para pintar
/// el corazon. Pedir las tarjetas completas para eso seria traer medio
/// catalogo otra vez; `GET /favoritos/ids` devuelve una lista de enteros.
library;

import 'package:dio/dio.dart';

import '../../core/red/excepciones.dart';
import '../modelos/catalogo.dart';

class RepositorioFavoritos {
  const RepositorioFavoritos(this._dio);

  final Dio _dio;

  /// Las prendas favoritas, como tarjetas de vitrina.
  ///
  /// Son `ProductoVitrina` y no un modelo propio porque el servidor devuelve
  /// exactamente la misma tarjeta que el catalogo: la pantalla de favoritos
  /// muestra lo mismo que la vitrina.
  Future<PaginaVitrina> listar({int pagina = 1, int tamano = 24}) async {
    try {
      final r = await _dio.get<Map<String, dynamic>>(
        '/tienda/favoritos',
        queryParameters: {'pagina': pagina, 'tamano': tamano},
      );
      return PaginaVitrina.desdeJson(r.data!);
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// Solo los identificadores, para pintar el corazon en el catalogo.
  Future<Set<int>> ids() async {
    try {
      final r = await _dio.get<List<dynamic>>('/tienda/favoritos/ids');
      return (r.data ?? const []).map((e) => e as int).toSet();
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  Future<void> marcar(int productoId) async {
    try {
      await _dio.put<void>('/tienda/favoritos/$productoId');
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  Future<void> desmarcar(int productoId) async {
    try {
      await _dio.delete<void>('/tienda/favoritos/$productoId');
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }
}
