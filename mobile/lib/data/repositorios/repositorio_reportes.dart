/// CU-35 · Pedir un reporte hablando, y descargarlo.
///
/// AL SERVIDOR LE LLEGA TEXTO, NO AUDIO
/// -------------------------------------
/// El reconocimiento corre en el telefono con el motor del sistema: es
/// gratis, no consume cuota del modelo y no sube audio a ningun lado.
/// Transcribir en el servidor obligaria a un servicio de pago y a subir
/// megabytes por cada pedido, para obtener exactamente el mismo texto.
///
/// EL SERVIDOR NO DEVUELVE EL ARCHIVO: DEVUELVE QUE ENTENDIO
/// ----------------------------------------------------------
/// Y la URL para bajarlo. Asi la pantalla puede mostrar «entendi: ventas de
/// septiembre, en Excel» y recien entonces descargar. Bajarlo de una quitaria
/// la unica oportunidad de notar que el modelo entendio otra cosa --- y un
/// reporte equivocado no se nota hasta abrirlo.
library;

import 'dart:typed_data';

import 'package:dio/dio.dart';

import '../../core/red/excepciones.dart';

class PedidoEntendido {
  const PedidoEntendido({
    required this.entendido,
    this.resumen,
    this.tipo,
    this.formato,
    this.url,
    this.motivo,
    this.ejemplos = const [],
  });

  final bool entendido;

  /// Que se entendio, en una frase. Se muestra ANTES de descargar.
  final String? resumen;

  final String? tipo;
  final String? formato;

  /// La URL ya armada por el servidor, con periodo y filtros. **No se rearma
  /// aca**: hacerlo seria arriesgarse a perder un filtro por el camino.
  final String? url;

  /// Por que no se entendio, y frases que si funcionan.
  final String? motivo;
  final List<String> ejemplos;

  factory PedidoEntendido.desdeJson(Map<String, dynamic> json) =>
      PedidoEntendido(
        entendido: json['entendido'] as bool? ?? false,
        resumen: json['resumen'] as String?,
        tipo: json['tipo'] as String?,
        formato: json['formato'] as String?,
        url: json['url'] as String?,
        motivo: json['motivo'] as String?,
        ejemplos: ((json['ejemplos'] as List?) ?? const [])
            .map((e) => '$e')
            .toList(),
      );
}

class ArchivoDeReporte {
  const ArchivoDeReporte({required this.contenido, required this.nombre});

  final Uint8List contenido;
  final String nombre;
}

class RepositorioReportes {
  const RepositorioReportes(this._dio);

  final Dio _dio;

  /// Si el servidor puede interpretar pedidos hablados.
  ///
  /// Ante cualquier fallo devuelve `false` en vez de lanzar: lo peor que pasa
  /// es que no se ofrezca el microfono, y eso no puede impedir usar la app.
  Future<bool> hayVoz() async {
    try {
      final r = await _dio.get<Map<String, dynamic>>(
        '/reportes/voz/disponible',
      );
      return r.data?['disponible'] as bool? ?? false;
    } catch (_) {
      return false;
    }
  }

  Future<PedidoEntendido> interpretar(String texto) async {
    try {
      final r = await _dio.post<Map<String, dynamic>>(
        '/reportes/voz',
        data: {'texto': texto},
        // Del otro lado hay un modelo pensando y puede probar dos: el tiempo
        // por omision de la app se queda corto.
        options: Options(receiveTimeout: const Duration(seconds: 90)),
      );
      return PedidoEntendido.desdeJson(r.data ?? const {});
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// Baja el archivo que el servidor indico.
  Future<ArchivoDeReporte> descargar(String ruta) async {
    try {
      final r = await _dio.get<List<int>>(
        ruta,
        options: Options(
          // Binario: con el tipo por omision Dio intenta leerlo como JSON,
          // falla al analizarlo, y el error no dice nada sobre lo que pasa.
          responseType: ResponseType.bytes,
          receiveTimeout: const Duration(seconds: 120),
        ),
      );
      return ArchivoDeReporte(
        contenido: Uint8List.fromList(r.data ?? const []),
        nombre: _nombreDe(r.headers.value('content-disposition'), ruta),
      );
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// El nombre que puso el servidor. Se respeta en vez de rearmarlo, para que
  /// el archivo se llame igual se baje desde donde se baje.
  String _nombreDe(String? disposicion, String ruta) {
    final m = RegExp(r'filename="([^"]+)"').firstMatch(disposicion ?? '');
    if (m != null) return m.group(1)!;
    return ruta.split('/').last.split('?').first;
  }
}
