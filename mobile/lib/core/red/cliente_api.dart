import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../almacenamiento/almacen_token.dart';
import '../config/entorno.dart';

final almacenTokenProvider = Provider<AlmacenToken>((ref) => AlmacenToken());

final interceptorTokenProvider = Provider<InterceptorDeToken>(
  (ref) => InterceptorDeToken(ref.watch(almacenTokenProvider)),
);

/// Cliente HTTP unico de la app. Toda peticion a la API pasa por aca, y por lo
/// tanto lleva el token sin que ninguna pantalla tenga que acordarse.
final clienteApiProvider = Provider<Dio>((ref) {
  final dio = Dio(
    BaseOptions(
      baseUrl: Entorno.urlApi,
      connectTimeout: Entorno.esperaConexion,
      receiveTimeout: Entorno.esperaRespuesta,
      headers: {'Content-Type': 'application/json'},
      // Los codigos de error se manejan como excepcion, no como respuesta:
      // asi ningun repositorio puede olvidarse de mirar el status.
      validateStatus: (codigo) => codigo != null && codigo < 400,
    ),
  );
  dio.interceptors.add(ref.watch(interceptorTokenProvider));
  return dio;
});

/// Agrega el token a cada peticion y avisa cuando el servidor lo rechaza.
class InterceptorDeToken extends Interceptor {
  InterceptorDeToken(this._almacen);

  final AlmacenToken _almacen;

  /// Lo completa el estado de sesion al arrancar. Se dispara con cualquier 401
  /// que no sea del propio login: el token fue revocado (CU-02 cierre de
  /// sesion desde otro dispositivo) o vencio, y la sesion local ya no sirve.
  void Function()? alCaducarSesion;

  /// Rutas publicas: pedirles token no tiene sentido y un 401 en ellas no
  /// significa que la sesion caduco, sino que las credenciales estan mal.
  static const _rutasPublicas = {'/auth/login', '/auth/registro'};

  bool _esPublica(String ruta) =>
      _rutasPublicas.any((publica) => ruta.endsWith(publica));

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    if (!_esPublica(options.path)) {
      final token = await _almacen.leer();
      if (token != null) {
        options.headers['Authorization'] = 'Bearer $token';
      }
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    final esCaducidad = err.response?.statusCode == 401 &&
        !_esPublica(err.requestOptions.path);
    if (esCaducidad) alCaducarSesion?.call();
    handler.next(err);
  }
}
