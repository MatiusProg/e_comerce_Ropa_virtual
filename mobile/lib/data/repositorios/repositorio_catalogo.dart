/// Acceso a los endpoints del catalogo publico (P5).
///
/// Un repositorio por paquete de analisis, igual que `RepositorioAuth`: es el
/// unico lugar de la app que conoce las rutas de `/tienda`; las pantallas
/// hablan con el, nunca con Dio.
library;

import 'package:dio/dio.dart';

import '../../core/constantes.dart';
import '../../core/red/excepciones.dart';
import '../modelos/catalogo.dart';

class RepositorioCatalogo {
  const RepositorioCatalogo(this._dio);

  final Dio _dio;

  /// La URL absoluta con la que se descarga una imagen.
  ///
  /// El servidor devuelve una ruta que cuelga del **origen** de la API
  /// (`/media/...`), no de `apiUrlBase`, que ademas lleva `/api/v1`. Sin
  /// completarla, `CachedNetworkImage` recibiria una ruta relativa que no sabe
  /// resolver y todas las fotos saldrian rotas.
  ///
  /// Es el equivalente de `urlDeImagen` en `tienda.service.ts` de la web.
  static String? urlDeImagen(String? ruta) {
    if (ruta == null || ruta.isEmpty) return null;
    return '${Uri.parse(apiUrlBase).origin}$ruta';
  }

  /// CU-17 · Consultar catalogo.
  Future<PaginaVitrina> listar(ConsultaVitrina consulta) async {
    try {
      final respuesta = await _dio.get<Map<String, dynamic>>(
        '/tienda/productos',
        queryParameters: consulta.aParametros(),
      );
      return PaginaVitrina.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// CU-18 · Consultar ficha de producto.
  ///
  /// El 404 llega tanto si la prenda no existe como si dejo de ofrecerse: el
  /// backend responde igual a proposito, para que recorrer identificadores no
  /// delate los productos ocultos.
  Future<FichaPrenda> obtenerFicha(int productoId) async {
    try {
      final respuesta = await _dio.get<Map<String, dynamic>>(
        '/tienda/productos/$productoId',
      );
      return FichaPrenda.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// Las opciones del panel de filtros. Se piden una vez al abrir la vitrina.
  Future<FiltrosDisponibles> obtenerFiltros() async {
    try {
      final respuesta = await _dio.get<Map<String, dynamic>>('/tienda/filtros');
      return FiltrosDisponibles.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }
}
