/// CU-34 · Conversar con el asistente virtual.
///
/// EL HISTORIAL LO MANDA LA PANTALLA
/// ----------------------------------
/// No hay tabla de conversaciones en el servidor, y es una decisión: ver
/// `asistente_service.py`. La pantalla guarda los turnos mientras está
/// abierta y los reenvía, que es lo que permite entender «¿y en talla M?».
library;

import 'package:dio/dio.dart';

import '../../core/red/excepciones.dart';

/// Un turno de la conversación.
class Turno {
  const Turno({required this.pregunta, required this.respuesta, this.productos = const []});

  final String pregunta;
  final String respuesta;

  /// Los productos que la respuesta menciona, **ya validados** contra el
  /// catálogo por el servidor: un código inventado no llega hasta acá.
  final List<int> productos;
}

class RepositorioAsistente {
  const RepositorioAsistente(this._dio);

  final Dio _dio;

  /// Si se puede conversar, y con qué empezar.
  ///
  /// Ante cualquier fallo devuelve no disponible en vez de lanzar: lo peor
  /// que pasa es que no se ofrezca el asistente, y eso no puede impedir
  /// usar la aplicación.
  Future<({bool disponible, List<String> ejemplos})> disponible() async {
    try {
      final r = await _dio.get<Map<String, dynamic>>('/asistente/disponible');
      return (
        disponible: r.data?['disponible'] as bool? ?? false,
        ejemplos: ((r.data?['ejemplos'] as List?) ?? const [])
            .map((e) => '$e')
            .toList(growable: false),
      );
    } catch (_) {
      return (disponible: false, ejemplos: const <String>[]);
    }
  }

  Future<Turno> preguntar(String pregunta, List<Turno> historial) async {
    try {
      final r = await _dio.post<Map<String, dynamic>>(
        '/asistente',
        data: {
          'pregunta': pregunta,
          // Solo los últimos diez: es el tope que acepta el servidor y
          // evita que el cuerpo crezca sin límite con la conversación.
          'historial': historial
              .skip(historial.length > 10 ? historial.length - 10 : 0)
              .map((t) => {'pregunta': t.pregunta, 'respuesta': t.respuesta})
              .toList(),
        },
        // Del otro lado hay un modelo pensando y puede probar dos: el
        // tiempo por omisión de la app se queda corto. Mismo caso que la
        // voz de CU-35.
        options: Options(receiveTimeout: const Duration(seconds: 90)),
      );
      return Turno(
        pregunta: pregunta,
        respuesta: '${r.data?['texto'] ?? ''}',
        productos: ((r.data?['productos'] as List?) ?? const [])
            .map((p) => p as int)
            .toList(growable: false),
      );
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }
}
