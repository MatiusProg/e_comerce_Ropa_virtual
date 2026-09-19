/// CU-33 · Recibir recomendaciones de prendas. Realiza el RF25.
///
/// LO QUE HAY QUE ENTENDER ANTES DE TOCAR ESTO
/// --------------------------------------------
/// El servidor **nunca falla por falta de datos ni por el modelo**. Sin talla
/// cargada, sin categorias elegidas, sin historial, sin proveedor de IA o sin
/// cuota, responde igual: las mismas prendas, ordenadas por popularidad y con
/// `motor` en `popularidad`. Por eso aca no hay camino de error para eso ---
/// solo para que la red se caiga.
///
/// De ahi salen las dos reglas de dibujo de la pantalla:
///
/// 1. **Sin motivo no se dibuja la etiqueta.** Viene vacio cuando ordeno la
///    popularidad. Poner un texto fijo repetido seis veces se lee como un
///    error, y le atribuye a la tienda una razon que nadie eligio.
/// 2. **Se dice con que se genero.** Una sugerencia hecha por un modelo tiene
///    que poder decir que lo es.
///
/// Esa distincion no es teorica: el 19/09 la pantalla web mostro la lista sin
/// motivos y Mateo detecto en el acto que no estaba usando la IA --- a
/// produccion le faltaba la clave. Con un texto generico habria creido que
/// funcionaba.
library;

import 'package:dio/dio.dart';

import '../../core/red/excepciones.dart';

class PrendaSugerida {
  const PrendaSugerida({
    required this.productoId,
    required this.nombre,
    required this.categoria,
    this.precioDesde,
    this.imagenUrl,
    this.motivo = '',
  });

  final int productoId;
  final String nombre;
  final String categoria;
  final String? precioDesde;
  final String? imagenUrl;

  /// Por que se sugiere, en una linea. **Vacio cuando ordeno la popularidad.**
  final String motivo;

  factory PrendaSugerida.desdeJson(Map<String, dynamic> json) => PrendaSugerida(
    productoId: json['producto_id'] as int,
    nombre: json['nombre'] as String,
    categoria: json['categoria'] as String? ?? '—',
    precioDesde: json['precio_desde']?.toString(),
    imagenUrl: json['imagen_url'] as String?,
    motivo: json['motivo'] as String? ?? '',
  );
}

class Recomendaciones {
  const Recomendaciones({
    required this.prendas,
    required this.motor,
    required this.generadaEn,
  });

  final List<PrendaSugerida> prendas;

  /// `gemini` cuando las ordeno el modelo, `popularidad` cuando no.
  final String motor;

  final DateTime? generadaEn;

  /// Si las ordeno un modelo. Cambia el pie de la pantalla, no el contenido.
  bool get porIa => motor.isNotEmpty && motor != 'popularidad';

  factory Recomendaciones.desdeJson(Map<String, dynamic> json) =>
      Recomendaciones(
        prendas: ((json['prendas'] as List?) ?? const [])
            .map((e) => PrendaSugerida.desdeJson(e as Map<String, dynamic>))
            .toList(),
        motor: json['motor'] as String? ?? 'popularidad',
        generadaEn: DateTime.tryParse('${json['generada_en']}'),
      );
}

class RepositorioRecomendaciones {
  const RepositorioRecomendaciones(this._dio);

  final Dio _dio;

  /// Las prendas sugeridas para quien pregunta.
  ///
  /// [forzar] vuelve a llamar al modelo aunque lo guardado siga vigente. Es lo
  /// que permite mostrar que la recomendacion cambia al cargar las medidas:
  /// sin eso habria que esperar doce horas.
  ///
  /// **Tarda.** La primera del dia la hace el modelo y son entre diez y
  /// veinte segundos; las siguientes doce horas salen de lo guardado y son
  /// instantaneas. La pantalla tiene que mostrar que esta trabajando.
  Future<Recomendaciones> mias({bool forzar = false}) async {
    try {
      final r = await _dio.get<Map<String, dynamic>>(
        '/tienda/recomendaciones',
        queryParameters: forzar ? {'forzar': true} : null,
        // El tiempo por omision de la app es corto y esto lo pasa: del otro
        // lado hay un modelo pensando, no una consulta a la base.
        options: Options(receiveTimeout: const Duration(seconds: 90)),
      );
      return Recomendaciones.desdeJson(r.data ?? const {});
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }
}
