/// CU-37 y CU-38 · El probador con la talla real, en el móvil.
///
/// Habla con los mismos endpoints que la web (`/vestidor/productos/{id}/prueba`
/// y `/vestidor/sesiones`): la diferencia está en la pantalla, que en el
/// teléfono sigue el cuerpo en vivo con la cámara en vez de trabajar sobre una
/// foto fija.
///
/// Lo que llega del servidor es lo que preparó el administrador en el CU-36:
/// por cada variante, su imagen sin fondo y los tres puntos que la calibran
/// (los dos hombros y el ruedo, relativos al ancho y al alto de la imagen). Con
/// eso y los centímetros de la talla, la prenda se dibuja a su tamaño real.
library;

import 'dart:typed_data';

import 'package:dio/dio.dart';

import '../../core/red/excepciones.dart';
import 'repositorio_medidas.dart';

/// Un punto de la imagen de la prenda, relativo (0 a 1) a su ancho y su alto.
class PuntoRelativo {
  const PuntoRelativo(this.x, this.y);

  final double x;
  final double y;

  factory PuntoRelativo.desdeJson(Map<String, dynamic> json) =>
      PuntoRelativo((json['x'] as num).toDouble(), (json['y'] as num).toDouble());
}

/// Los tres puntos del CU-36. «Izquierdo» y «derecho» son como se VEN en la
/// imagen, que es como los marcó el administrador.
class PuntosDePrenda {
  const PuntosDePrenda({
    required this.hombroIzq,
    required this.hombroDer,
    required this.ruedo,
  });

  final PuntoRelativo hombroIzq;
  final PuntoRelativo hombroDer;
  final PuntoRelativo ruedo;

  factory PuntosDePrenda.desdeJson(Map<String, dynamic> json) => PuntosDePrenda(
    hombroIzq: PuntoRelativo.desdeJson(json['hombro_izq'] as Map<String, dynamic>),
    hombroDer: PuntoRelativo.desdeJson(json['hombro_der'] as Map<String, dynamic>),
    ruedo: PuntoRelativo.desdeJson(json['ruedo'] as Map<String, dynamic>),
  );
}

/// Una variante que se puede probar: su imagen calibrada.
class PrendaCalibrada {
  const PrendaCalibrada({
    required this.varianteId,
    required this.tallaId,
    required this.talla,
    required this.colorId,
    required this.color,
    required this.imagenUrl,
    required this.puntos,
  });

  final int varianteId;
  final int tallaId;
  final String talla;
  final int colorId;
  final String color;

  /// Ruta del servidor (`/media/...`) o URL completa.
  final String imagenUrl;
  final PuntosDePrenda puntos;

  factory PrendaCalibrada.desdeJson(Map<String, dynamic> json) => PrendaCalibrada(
    varianteId: json['variante_id'] as int,
    tallaId: json['talla_id'] as int,
    talla: json['talla'] as String,
    colorId: json['color_id'] as int,
    color: json['color'] as String,
    imagenUrl: json['imagen_url'] as String,
    puntos: PuntosDePrenda.desdeJson(json['puntos'] as Map<String, dynamic>),
  );
}

/// Si se puede pedir la foto realista (CU-38) y, si no, por qué.
class EstadoFotoIa {
  const EstadoFotoIa({required this.disponible, this.motivo, this.demora = 15});

  final bool disponible;
  final String? motivo;
  final int demora;

  factory EstadoFotoIa.desdeJson(Map<String, dynamic>? json) => EstadoFotoIa(
    disponible: json?['disponible'] as bool? ?? false,
    motivo: json?['motivo'] as String?,
    demora: json?['demora_estimada_segundos'] as int? ?? 15,
  );
}

/// Un producto listo para el probador (la lista de entrada).
class ProductoParaProbar {
  const ProductoParaProbar({required this.productoId, required this.nombre, required this.imagenUrl});

  final int productoId;
  final String nombre;
  final String imagenUrl;

  factory ProductoParaProbar.desdeJson(Map<String, dynamic> json) => ProductoParaProbar(
    productoId: json['producto_id'] as int,
    nombre: json['nombre'] as String,
    imagenUrl: json['imagen_url'] as String,
  );
}

/// Todo lo que hace falta para probarse un producto.
class PruebaDeProducto {
  const PruebaDeProducto({
    required this.productoId,
    required this.nombre,
    required this.prendas,
    required this.ajuste,
    required this.fotoIa,
    this.bustoCm,
  });

  final int productoId;
  final String nombre;
  final List<PrendaCalibrada> prendas;
  final AjusteDeProducto ajuste;
  final EstadoFotoIa fotoIa;

  /// El busto del cliente. `null` si todavía no cargó sus medidas: entonces
  /// no hay escala real y la prenda se dibuja a un tamaño aproximado.
  final double? bustoCm;

  factory PruebaDeProducto.desdeJson(Map<String, dynamic> json) {
    final medidas = json['medidas'] as Map<String, dynamic>?;
    return PruebaDeProducto(
      productoId: json['producto_id'] as int,
      nombre: json['nombre'] as String,
      prendas: ((json['prendas'] as List?) ?? const [])
          .map((e) => PrendaCalibrada.desdeJson(e as Map<String, dynamic>))
          .toList(),
      ajuste: AjusteDeProducto.desdeJson(json['ajuste'] as Map<String, dynamic>),
      fotoIa: EstadoFotoIa.desdeJson(json['foto_ia'] as Map<String, dynamic>?),
      bustoCm: medidas == null ? null : double.tryParse('${medidas['busto_cm']}'),
    );
  }
}

/// Una prueba guardada («Mis pruebas»), con su foto realista si la tiene.
class SesionProbador {
  const SesionProbador({
    required this.id,
    required this.varianteId,
    required this.productoId,
    required this.producto,
    required this.talla,
    required this.color,
    required this.creadoEn,
    this.ajuste,
    this.tallaRecomendada,
    this.fotoUrl,
    this.fotoGeneradaPor,
  });

  final int id;
  final int varianteId;
  final int productoId;
  final String producto;
  final String talla;
  final String color;
  final DateTime creadoEn;
  final String? ajuste;
  final String? tallaRecomendada;
  final String? fotoUrl;
  final String? fotoGeneradaPor;

  /// Una imagen generada tiene que poder decir que lo es.
  String get origenDeLaFoto {
    final por = fotoGeneradaPor ?? '';
    return por.startsWith('simulado')
        ? 'Vista simulada (sin IA generativa)'
        : 'Generada con IA ($por)';
  }

  factory SesionProbador.desdeJson(Map<String, dynamic> json) => SesionProbador(
    id: json['id'] as int,
    varianteId: json['variante_id'] as int,
    productoId: json['producto_id'] as int,
    producto: json['producto'] as String,
    talla: json['talla'] as String,
    color: json['color'] as String,
    creadoEn: DateTime.parse(json['creado_en'] as String).toLocal(),
    ajuste: json['ajuste'] as String?,
    tallaRecomendada: json['talla_recomendada'] as String?,
    fotoUrl: json['foto_url'] as String?,
    fotoGeneradaPor: json['foto_generada_por'] as String?,
  );
}

class RepositorioProbador {
  const RepositorioProbador(this._dio);

  final Dio _dio;

  /// CU-37 · las prendas listas para probar, la última calibrada primero.
  Future<List<ProductoParaProbar>> listos() async {
    try {
      final r = await _dio.get<List<dynamic>>('/vestidor/productos-listos');
      return (r.data ?? const [])
          .map((e) => ProductoParaProbar.desdeJson(e as Map<String, dynamic>))
          .toList();
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// CU-37 · las prendas calibradas, el ajuste por talla y si hay foto con IA.
  Future<PruebaDeProducto> prueba(int productoId) async {
    try {
      final r = await _dio.get<Map<String, dynamic>>(
        '/vestidor/productos/$productoId/prueba',
      );
      return PruebaDeProducto.desdeJson(r.data!);
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// CU-37 · registra la prueba. El método es POSE: en el móvil los hombros
  /// los da siempre la detección en vivo.
  Future<SesionProbador> registrar(int varianteId) async {
    try {
      final r = await _dio.post<Map<String, dynamic>>(
        '/vestidor/sesiones',
        data: {'variante_id': varianteId, 'metodo': 'POSE'},
      );
      return SesionProbador.desdeJson(r.data!);
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// CU-37 · mis últimas pruebas.
  Future<List<SesionProbador>> misPruebas() async {
    try {
      final r = await _dio.get<List<dynamic>>('/vestidor/sesiones');
      return (r.data ?? const [])
          .map((e) => SesionProbador.desdeJson(e as Map<String, dynamic>))
          .toList();
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  Future<void> borrar(int sesionId) async {
    try {
      await _dio.delete<void>('/vestidor/sesiones/$sesionId');
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// CU-38 · manda la composición (cámara + prenda a escala) y devuelve la
  /// prueba con su foto realista. Descuenta el cupo de la tienda (incluye CU-05).
  Future<SesionProbador> generarFoto(int sesionId, Uint8List composicion) async {
    try {
      final formulario = FormData.fromMap({
        'composicion': MultipartFile.fromBytes(
          composicion,
          filename: 'composicion.png',
          contentType: DioMediaType('image', 'png'),
        ),
      });
      final r = await _dio.post<Map<String, dynamic>>(
        '/vestidor/sesiones/$sesionId/foto',
        data: formulario,
        options: Options(
          // Generar una imagen tarda mucho más que cualquier otra petición.
          receiveTimeout: const Duration(seconds: 120),
          sendTimeout: const Duration(seconds: 60),
        ),
      );
      return SesionProbador.desdeJson(r.data!);
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }
}
