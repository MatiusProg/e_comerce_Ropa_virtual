import 'package:dio/dio.dart';

/// Traduce cualquier fallo de red o de la API a un mensaje que se le puede
/// mostrar a una persona.
///
/// Existe para que ninguna pantalla tenga que conocer los codigos de estado ni
/// la forma en que FastAPI arma sus errores. La regla del proyecto es que la
/// interfaz muestre el `detail` del backend cuando lo hay: los mensajes de los
/// flujos alternativos de los casos de uso ya estan redactados alli, en
/// castellano, y duplicarlos aca los dejaria desincronizados.
class ErrorApi implements Exception {
  const ErrorApi(this.mensaje, {this.codigo});

  final String mensaje;
  final int? codigo;

  bool get esNoAutorizado => codigo == 401;

  @override
  String toString() => mensaje;

  factory ErrorApi.desdeDio(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.transformTimeout:
        return const ErrorApi(
          'El servidor tardó demasiado en responder. Volvé a intentar.',
        );
      case DioExceptionType.connectionError:
      case DioExceptionType.unknown:
        return const ErrorApi(
          'No se pudo conectar con el servidor. Revisá tu conexión a internet.',
        );
      case DioExceptionType.cancel:
        return const ErrorApi('La operación se canceló.');
      case DioExceptionType.badCertificate:
        return const ErrorApi('El certificado del servidor no es válido.');
      case DioExceptionType.badResponse:
        break;
    }

    final respuesta = error.response;
    final codigo = respuesta?.statusCode;
    return ErrorApi(_mensajeDe(respuesta?.data, codigo), codigo: codigo);
  }

  /// FastAPI devuelve dos formas distintas bajo la misma clave `detail`:
  /// un texto cuando es una `HTTPException` levantada por el router, y una
  /// lista de errores por campo cuando es una validacion de Pydantic (422).
  static String _mensajeDe(Object? cuerpo, int? codigo) {
    if (cuerpo is Map && cuerpo['detail'] != null) {
      final detalle = cuerpo['detail'];

      if (detalle is String) return detalle;

      if (detalle is List && detalle.isNotEmpty) {
        final mensajes = detalle
            .whereType<Map>()
            .map((e) => e['msg']?.toString())
            .whereType<String>()
            .map((m) => m.replaceFirst('Value error, ', ''))
            .toList();
        if (mensajes.isNotEmpty) return mensajes.join('\n');
      }
    }

    return switch (codigo) {
      401 => 'Tu sesión venció. Iniciá sesión de nuevo.',
      403 => 'No tenés permiso para hacer esto.',
      404 => 'No se encontró lo que buscabas.',
      final int c when c >= 500 =>
        'El servidor tuvo un problema. Intentá más tarde.',
      _ => 'Ocurrió un error inesperado.',
    };
  }
}
