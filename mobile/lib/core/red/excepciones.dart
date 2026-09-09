/// Traduccion de los fallos de red a algo que se le pueda mostrar al usuario.
///
/// Regla: ninguna pantalla ve un `DioException`. El repositorio lo convierte en
/// un [ErrorApi] con un mensaje ya redactado en castellano, y la pantalla se
/// limita a mostrarlo. Asi el texto de error se escribe una sola vez.
library;

import 'package:dio/dio.dart';

class ErrorApi implements Exception {
  const ErrorApi(this.mensaje, {this.codigo});

  /// Mensaje listo para mostrar al usuario.
  final String mensaje;

  /// Codigo HTTP, cuando lo hubo. Es `null` si el fallo fue de conexion.
  final int? codigo;

  /// `true` cuando el token dejo de valer y hay que volver a iniciar sesion.
  bool get esNoAutorizado => codigo == 401;

  @override
  String toString() => 'ErrorApi($codigo): $mensaje';
}

/// Convierte un fallo de Dio en un [ErrorApi].
///
/// El backend responde los errores de negocio con `{"detail": "..."}` y un
/// mensaje ya redactado —ver los `HTTPException` de
/// `backend/app/modules/seguridad/router.py`—, asi que cuando ese campo viene
/// como texto se usa tal cual: es la fuente de verdad y evita que la app y la
/// API digan cosas distintas del mismo error.
ErrorApi traducirError(DioException fallo) {
  switch (fallo.type) {
    case DioExceptionType.connectionTimeout:
    case DioExceptionType.sendTimeout:
    case DioExceptionType.receiveTimeout:
    // `transformTimeout` es de dio 5.11: se agota el tiempo transformando la
    // respuesta, no esperandola. Para el usuario es lo mismo que un timeout.
    case DioExceptionType.transformTimeout:
      return const ErrorApi(
        'El servidor está tardando demasiado en responder. '
        'Vuelva a intentarlo en unos segundos.',
      );
    case DioExceptionType.connectionError:
    case DioExceptionType.unknown:
      return const ErrorApi(
        'No se pudo conectar con el servidor. Revise su conexión a internet.',
      );
    case DioExceptionType.cancel:
      return const ErrorApi('La operación fue cancelada.');
    case DioExceptionType.badCertificate:
      return const ErrorApi('El certificado del servidor no es válido.');
    case DioExceptionType.badResponse:
      break;
  }

  final respuesta = fallo.response;
  final codigo = respuesta?.statusCode;
  final cuerpo = respuesta?.data;

  if (cuerpo is Map<String, dynamic>) {
    final detalle = cuerpo['detail'];

    // Caso normal: el backend mando un mensaje escrito para el usuario.
    //
    // Con una excepcion: cuando falta el token, el 401 no lo produce el codigo
    // del proyecto sino el `HTTPBearer` de FastAPI, que responde un
    // "Not authenticated" en ingles y sin traducir. Ese texto no se le muestra
    // a nadie; se reemplaza por el mensaje propio.
    if (detalle is String &&
        detalle.trim().isNotEmpty &&
        !(codigo == 401 && detalle == 'Not authenticated')) {
      return ErrorApi(detalle, codigo: codigo);
    }

    // 422 de Pydantic: `detail` es una lista de errores de validacion campo a
    // campo. Es util para el desarrollador, no para el cliente; se resume.
    if (detalle is List && detalle.isNotEmpty) {
      return ErrorApi(
        'Revise los datos ingresados: hay ${detalle.length} '
        '${detalle.length == 1 ? "campo inválido" : "campos inválidos"}.',
        codigo: codigo,
      );
    }
  }

  return ErrorApi(_mensajePorCodigo(codigo), codigo: codigo);
}

String _mensajePorCodigo(int? codigo) {
  return switch (codigo) {
    400 => 'La solicitud no es válida.',
    401 => 'Su sesión expiró. Vuelva a iniciar sesión.',
    403 => 'No tiene permiso para realizar esta acción.',
    404 => 'No se encontró lo que buscaba.',
    409 => 'El dato ya existe.',
    503 => 'El servicio no está disponible en este momento.',
    _ => 'Ocurrió un error inesperado. Inténtelo de nuevo.',
  };
}
