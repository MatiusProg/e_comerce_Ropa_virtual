/// Cliente HTTP unico de la aplicacion.
///
/// Equivale al `authInterceptor` de la web
/// (`frontend-web/src/app/core/interceptors/auth.interceptor.ts`): adjunta el
/// token a cada peticion y reacciona al 401 cerrando la sesion. Ninguna
/// pantalla ni repositorio construye su propio `Dio`.
library;

import 'package:dio/dio.dart';

import '../almacenamiento/almacen_seguro.dart';
import '../constantes.dart';

/// Rutas que no llevan token porque el actor todavia no tiene sesion
/// (CU-01 registrar cliente y CU-02 iniciar sesion).
const Set<String> _rutasPublicas = {'/auth/login', '/auth/registro'};

Dio construirDio({
  required AlmacenSeguro almacen,
  required Future<void> Function() alPerderLaSesion,
}) {
  final dio = Dio(
    BaseOptions(
      baseUrl: apiUrlBase,
      connectTimeout: tiempoDeConexion,
      receiveTimeout: tiempoDeRespuesta,
      sendTimeout: tiempoDeConexion,
      headers: {'Accept': 'application/json'},
      contentType: Headers.jsonContentType,
      // El 4xx no se trata como fallo de transporte: se deja llegar al
      // manejador de errores, que sabe leer el `detail` del backend.
      validateStatus: (codigo) => codigo != null && codigo < 400,
    ),
  );

  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (opciones, seguir) async {
        if (!_rutasPublicas.contains(opciones.path)) {
          final token = await almacen.leerToken();
          if (token != null && token.isNotEmpty) {
            opciones.headers['Authorization'] = 'Bearer $token';
          }
        }
        seguir.next(opciones);
      },
      onError: (fallo, seguir) async {
        // 401 sobre una ruta privada = el token fue revocado o expiro. Se cierra
        // la sesion una sola vez, aqui, en lugar de que cada pantalla lo maneje.
        final esPublica = _rutasPublicas.contains(fallo.requestOptions.path);
        if (fallo.response?.statusCode == 401 && !esPublica) {
          await alPerderLaSesion();
        }
        seguir.next(fallo);
      },
    ),
  );

  return dio;
}
