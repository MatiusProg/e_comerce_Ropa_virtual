/// Acceso a los endpoints de reservas (P6) --- CU-22 y CU-23.
///
/// Un repositorio por paquete de analisis, igual que `RepositorioCatalogo`: es
/// el unico lugar de la app que conoce las rutas de `/reservas`; las pantallas
/// hablan con el, nunca con Dio.
///
/// Solo el ambito del **Cliente**. `/sucursal/reservas` (CU-24) es del Encargado
/// y vive en la web: son dos colecciones distintas --- «las mias» y «las de mi
/// sucursal» ---, y la app movil es la del cliente.
library;

import 'package:dio/dio.dart';

import '../../core/red/excepciones.dart';
import '../modelos/reservas.dart';

/// Por que fallo una operacion de reservas.
///
/// El repositorio no se conforma con el mensaje: clasifica el error, porque
/// cada clase lleva a una accion distinta en la pantalla y el texto suelto no
/// permite decidirla. Es el mismo reparto que hace `ErrorReservas` en
/// `reservas.service.ts` de la web.
enum TipoErrorReserva {
  /// E1 --- alguna prenda ya no esta en el catalogo. Trae **cuales**, para
  /// señalarlas en vez de invalidar la reserva entera.
  lineasInvalidas,

  /// E9 y el desenlace de una carrera perdida contra otro cliente (riesgo R5).
  /// La disponibilidad que la pantalla muestra ya no vale: hay que volver a
  /// pedirla, no reintentar contra un numero viejo.
  sinStock,

  /// E6 --- manda a elegir otra franja, no otra prenda.
  sinProbadores,

  /// E3, E4, E5 y E8 --- devuelve el control al selector de hora.
  franjaInvalida,

  /// E10 --- casi siempre significa que la pantalla esta vieja (la atendieron o
  /// expiro mientras el cliente miraba). Lo que corresponde es **refrescar**,
  /// no reintentar.
  estadoFinal,

  /// No existe, o es de otro cliente. El servidor responde el mismo 404 a las
  /// dos cosas a proposito: un 403 confirmaria que esa reserva existe.
  noEncontrada,

  /// La cuenta no tiene ficha de cliente. Se arregla completando el perfil.
  sinFicha,

  /// El resto de los 422.
  validacion,

  /// Conexion, 5xx y lo que no encaje en lo anterior.
  sistema,
}

/// Un [ErrorApi] clasificado.
///
/// Extiende y no reemplaza a [ErrorApi] para que cualquier manejador generico
/// que ya exista --- el que mira `esNoAutorizado`, por ejemplo --- lo siga
/// entendiendo sin cambios.
class ErrorReservas extends ErrorApi {
  const ErrorReservas(
    super.mensaje, {
    required this.tipo,
    super.codigo,
    this.variantes = const [],
  });

  final TipoErrorReserva tipo;

  /// Solo en [TipoErrorReserva.lineasInvalidas]: que variantes rechazo el
  /// servidor.
  final List<int> variantes;
}

class RepositorioReservas {
  const RepositorioReservas(this._dio);

  final Dio _dio;

  /// CU-22 · Crear reserva de prendas.
  ///
  /// El cliente no viaja en el cuerpo: sale del token. Si viniera en el JSON,
  /// cualquiera podria reservar a nombre de otro.
  Future<Reserva> crear(ReservaCrear datos) async {
    try {
      final respuesta = await _dio.post<Map<String, dynamic>>(
        '/reservas',
        data: datos.aJson(),
      );
      return Reserva.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw _traducir(fallo);
    }
  }

  /// CU-22/CU-23 · Mis reservas.
  ///
  /// `vivas` existe ademas del filtro por estado porque la pregunta que hace la
  /// pantalla casi siempre es «¿qué tengo pendiente?», y eso son dos estados,
  /// no uno.
  Future<PaginaReservas> listar({
    bool? vivas,
    EstadoReserva? estado,
    int pagina = 1,
    int tamano = 20,
  }) async {
    try {
      final respuesta = await _dio.get<Map<String, dynamic>>(
        '/reservas',
        queryParameters: {
          if (vivas != null) 'vivas': vivas,
          if (estado != null) 'estado': estado.codigo,
          'pagina': pagina,
          'tamano': tamano,
        },
      );
      return PaginaReservas.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw _traducir(fallo);
    }
  }

  /// CU-22/CU-23 · El detalle de una reserva propia, con sus prendas.
  Future<Reserva> obtener(int reservaId) async {
    try {
      final respuesta = await _dio.get<Map<String, dynamic>>(
        '/reservas/$reservaId',
      );
      return Reserva.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw _traducir(fallo);
    }
  }

  /// CU-23 · Cancelar una reserva propia y devolver el stock apartado.
  ///
  /// Es `PATCH` sobre un sub-recurso y no `DELETE` sobre la reserva: cancelar
  /// **no** la borra. La reserva cancelada se conserva --- con su motivo, su
  /// fecha y sus prendas --- porque es historia del cliente y de la sucursal, y
  /// porque los movimientos de `LIBERACION` que deja apuntan a ella.
  Future<Reserva> cancelar(int reservaId, {String? motivo}) async {
    try {
      final respuesta = await _dio.patch<Map<String, dynamic>>(
        '/reservas/$reservaId/cancelacion',
        data: CancelarReserva(motivo: motivo).aJson(),
      );
      return Reserva.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw _traducir(fallo);
    }
  }

  // --- Internos ------------------------------------------------------------

  /// Clasifica el fallo sin perder el mensaje del backend.
  ///
  /// El texto sale de `router.py`, que ya lo escribio para el usuario --- con
  /// los numeros del caso concreto: cuantas unidades quedan, cuantos probadores
  /// tiene la sucursal, entre que horas atiende ---. Reescribirlo aca seria
  /// perder ese detalle y arriesgarse a que la app y la API digan cosas
  /// distintas del mismo error.
  ///
  /// Lo que se agrega es el [TipoErrorReserva], que el texto no lleva.
  ErrorReservas _traducir(DioException fallo) {
    // Timeouts, falta de conexion y certificados no llegan con cuerpo: el
    // traductor general ya sabe redactarlos y no hay nada que clasificar.
    if (fallo.type != DioExceptionType.badResponse) {
      final generico = traducirError(fallo);
      return ErrorReservas(
        generico.mensaje,
        tipo: TipoErrorReserva.sistema,
        codigo: generico.codigo,
      );
    }

    final codigo = fallo.response?.statusCode;
    final cuerpo = fallo.response?.data;
    final bruto = cuerpo is Map<String, dynamic> ? cuerpo['detail'] : null;
    final detalle = bruto is String ? bruto : '';

    if (codigo == 404) {
      return ErrorReservas(
        detalle.isNotEmpty ? detalle : 'No encontramos esa reserva.',
        tipo: TipoErrorReserva.noEncontrada,
        codigo: codigo,
      );
    }

    if (codigo == 409) {
      // Los tres 409 se distinguen por el texto porque el backend no manda un
      // codigo propio. Frágil pero acotado: son las mismas tres cadenas que
      // mira la web, y cada una lleva a una accion distinta en la pantalla.
      final tipo = detalle.contains('probadores')
          ? TipoErrorReserva.sinProbadores
          : detalle.contains('ficha de cliente')
          ? TipoErrorReserva.sinFicha
          : detalle.contains('unidades') || detalle.contains('disponible')
          ? TipoErrorReserva.sinStock
          // Ya fue atendida, ya estaba cancelada, ya vencio.
          : TipoErrorReserva.estadoFinal;
      return ErrorReservas(
        detalle.isNotEmpty
            ? detalle
            : 'Esa reserva ya no admite esta operación.',
        tipo: tipo,
        codigo: codigo,
      );
    }

    if (codigo == 422) {
      // E1 viaja como objeto y no como texto: trae QUE prendas fallaron.
      if (bruto is Map<String, dynamic>) {
        final variantes = bruto['variantes'];
        if (variantes is List) {
          return ErrorReservas(
            bruto['mensaje'] as String? ??
                'Hay prendas que no se pueden reservar.',
            tipo: TipoErrorReserva.lineasInvalidas,
            codigo: codigo,
            variantes: variantes.whereType<int>().toList(),
          );
        }
      }
      if (detalle.contains('franja') ||
          detalle.contains('anticipación') ||
          detalle.contains('atiende') ||
          detalle.contains('pasó')) {
        return ErrorReservas(
          detalle,
          tipo: TipoErrorReserva.franjaInvalida,
          codigo: codigo,
        );
      }
      // FastAPI manda `detail` como lista en los errores de esquema; el
      // traductor general ya sabe resumirla.
      return ErrorReservas(
        detalle.isNotEmpty ? detalle : traducirError(fallo).mensaje,
        tipo: TipoErrorReserva.validacion,
        codigo: codigo,
      );
    }

    final generico = traducirError(fallo);
    return ErrorReservas(
      generico.mensaje,
      tipo: TipoErrorReserva.sistema,
      codigo: codigo,
    );
  }
}
