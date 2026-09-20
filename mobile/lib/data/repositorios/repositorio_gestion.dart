/// CU-36 · Tablero de indicadores y CU-42 · Bitácora, en el teléfono.
///
/// POR QUÉ LOS DOS EN UN MISMO ARCHIVO
/// ------------------------------------
/// Son las dos lecturas de gestión que el móvil ofrece, las dos las consume
/// el mismo rol y las dos son de solo lectura sobre un endpoint único. Dos
/// archivos de treinta líneas cada uno con el mismo `Dio` y el mismo
/// traductor de errores serían dos lugares donde tocar lo mismo.
///
/// LO QUE NO ESTÁ ACÁ
/// -------------------
/// La bitácora **no tiene escritura**, y no es un olvido: los asientos los
/// pone un middleware en el servidor y la API no expone ni un `POST`. Una
/// bitácora que se puede corregir no prueba nada.
library;

import 'package:dio/dio.dart';

import '../../core/red/excepciones.dart';
import '../modelos/gestion.dart';

class RepositorioGestion {
  const RepositorioGestion(this._dio);

  final Dio _dio;

  /// CU-36 · todo el tablero en una sola respuesta.
  ///
  /// Un endpoint y no seis: la pantalla los muestra siempre juntos y salen
  /// del mismo filtrado. Seis viajes abrirían la posibilidad de que dos
  /// tarjetas del mismo tablero muestren períodos distintos si una llega
  /// tarde.
  Future<Tablero> tablero({DateTime? desde, DateTime? hasta}) async {
    try {
      final r = await _dio.get<Map<String, dynamic>>(
        '/reportes/tablero',
        queryParameters: {
          if (desde != null) 'desde': _soloFecha(desde),
          if (hasta != null) 'hasta': _soloFecha(hasta),
        },
      );
      return Tablero.desdeJson(r.data ?? const {});
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// CU-42 · los asientos, del más reciente al más viejo.
  Future<PaginaBitacora> bitacora({
    int pagina = 1,
    int tamano = 30,
    String? rol,
    String? accion,
    bool? exito,
    String? busqueda,
  }) async {
    try {
      final r = await _dio.get<Map<String, dynamic>>(
        '/bitacora',
        queryParameters: {
          'pagina': pagina,
          'tamano': tamano,
          if (rol != null && rol.isNotEmpty) 'rol': rol,
          if (accion != null && accion.isNotEmpty) 'accion': accion,
          if (exito != null) 'exito': exito,
          if (busqueda != null && busqueda.trim().isNotEmpty)
            'busqueda': busqueda.trim(),
        },
      );
      return PaginaBitacora.desdeJson(r.data ?? const {});
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// Las acciones que hay REALMENTE registradas, para armar el filtro.
  ///
  /// Ante cualquier fallo devuelve la lista vacía en vez de lanzar: sin
  /// opciones se pierde un desplegable, no la consulta, y un cartel rojo por
  /// eso sería alarmar por algo que no impide trabajar.
  Future<({List<String> acciones, List<String> roles})>
  opcionesDeBitacora() async {
    try {
      final r = await _dio.get<Map<String, dynamic>>('/bitacora/opciones');
      return (
        acciones: ((r.data?['acciones'] as List?) ?? const [])
            .map((a) => '$a')
            .toList(growable: false),
        roles: ((r.data?['roles'] as List?) ?? const [])
            .map((a) => '$a')
            .toList(growable: false),
      );
    } catch (_) {
      return (acciones: const <String>[], roles: const <String>[]);
    }
  }

  /// `YYYY-MM-DD` armado a mano.
  ///
  /// **No `toIso8601String()`**: ese convierte a UTC y, con Bolivia en -4,
  /// una fecha elegida en el calendario se manda como el día anterior. Es el
  /// mismo defecto que se arregló en el servidor el 20/09.
  String _soloFecha(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-'
      '${d.month.toString().padLeft(2, '0')}-'
      '${d.day.toString().padLeft(2, '0')}';
}
