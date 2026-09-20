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

/// Una opcion de un filtro, ya resuelta por el servidor.
class OpcionDeFiltro {
  const OpcionDeFiltro({required this.valor, required this.etiqueta});

  final String valor;
  final String etiqueta;

  factory OpcionDeFiltro.desdeJson(Map<String, dynamic> j) => OpcionDeFiltro(
    valor: '${j['valor']}',
    etiqueta: '${j['etiqueta']}',
  );
}

/// Un filtro que ESTE reporte admite, con sus opciones.
///
/// Vienen del servidor y no estan escritas aca: las sucursales, los
/// proveedores y las temporadas salen de la base. Si un reporte acepta un
/// filtro mas, aparece en la pantalla sin tocar la app.
class FiltroDeReporte {
  const FiltroDeReporte({
    required this.campo,
    required this.etiqueta,
    required this.opciones,
  });

  final String campo;
  final String etiqueta;
  final List<OpcionDeFiltro> opciones;

  factory FiltroDeReporte.desdeJson(Map<String, dynamic> j) => FiltroDeReporte(
    campo: j['campo'] as String,
    etiqueta: j['etiqueta'] as String,
    opciones: ((j['opciones'] as List?) ?? const [])
        .map((o) => OpcionDeFiltro.desdeJson(o as Map<String, dynamic>))
        .toList(growable: false),
  );
}

/// CU-37 · un reporte que el servidor sabe generar.
class ReporteDisponible {
  const ReporteDisponible({
    required this.tipo,
    required this.titulo,
    required this.columnas,
    required this.usaPeriodo,
    required this.filtros,
  });

  final String tipo;
  final String titulo;
  final List<String> columnas;

  /// `false` para el inventario: es una foto de ahora, no un acumulado. La
  /// pantalla esconde el selector de fechas cuando es falso --- ofrecer un
  /// rango que despues se ignora es mentirle a quien lo elige.
  final bool usaPeriodo;

  final List<FiltroDeReporte> filtros;

  factory ReporteDisponible.desdeJson(Map<String, dynamic> j) =>
      ReporteDisponible(
        tipo: j['tipo'] as String,
        titulo: j['titulo'] as String,
        columnas: ((j['columnas'] as List?) ?? const [])
            .map((c) => '$c')
            .toList(growable: false),
        usaPeriodo: j['usa_periodo'] as bool? ?? true,
        filtros: ((j['filtros'] as List?) ?? const [])
            .map((f) => FiltroDeReporte.desdeJson(f as Map<String, dynamic>))
            .toList(growable: false),
      );
}

class ArchivoDeReporte {
  const ArchivoDeReporte({required this.contenido, required this.nombre});

  final Uint8List contenido;
  final String nombre;

  /// El tipo del archivo, deducido de la extension.
  ///
  /// Hace falta para la hoja de compartir: sin el, Android la abre con la
  /// lista generica y no ofrece las aplicaciones que saben abrir una planilla
  /// o un PDF.
  String get tipoMime => nombre.toLowerCase().endsWith('.pdf')
      ? 'application/pdf'
      : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
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

  /// CU-37 · que reportes hay, con sus filtros ya resueltos.
  ///
  /// La pantalla NO tiene la lista escrita: si se agrega un reporte en el
  /// servidor, aparece solo en el telefono.
  Future<List<ReporteDisponible>> catalogo() async {
    try {
      final r = await _dio.get<List<dynamic>>('/reportes/catalogo');
      return (r.data ?? const [])
          .map((e) => ReporteDisponible.desdeJson(e as Map<String, dynamic>))
          .toList(growable: false);
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
