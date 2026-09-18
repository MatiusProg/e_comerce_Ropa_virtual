/// Acceso a los endpoints del vestidor virtual (P9) --- CU-21.
///
/// Solo lo OPCIONAL. El resto de CU-21 --- camara, deteccion de pose,
/// superposicion, captura --- corre entero en el telefono y no habla con el
/// servidor: la seccion 4.2 dice que P9 «reside principalmente en la
/// aplicacion movil».
///
/// Lo unico que no puede correr aca es amoldar la prenda al cuerpo con un
/// modelo de imagen, porque necesita un modelo grande y una clave. Eso es lo
/// que pide este repositorio.
library;

import 'dart:typed_data';

import 'package:dio/dio.dart';

import '../../core/red/excepciones.dart';

/// Por que no se pudo amoldar la prenda.
///
/// Se clasifica porque cada caso lleva a algo distinto en la pantalla, y el
/// mas importante es el primero.
enum TipoErrorProbador {
  /// 503 --- no esta habilitado en este entorno. **No es un fallo**: es que
  /// nadie lo encendio. La pantalla esconde el boton y NO reintenta.
  apagado,

  /// 404 --- esa variante no tiene PNG de vestidor, o dejo de ofrecerse.
  sinPrenda,

  /// 502 --- el servicio de imagenes fallo, o se acabo la cuota. El cliente se
  /// queda con su captura, que es lo que el caso de uso le prometio.
  servicioCaido,

  /// Conexion, 5xx y lo que no encaje.
  sistema,
}

class ErrorProbador extends ErrorApi {
  const ErrorProbador(super.mensaje, {required this.tipo, super.codigo});

  final TipoErrorProbador tipo;
}

/// Lo que devuelve amoldar: la imagen y con que se hizo.
class PrendaAmoldada {
  const PrendaAmoldada({required this.imagen, required this.generadaPor});

  final Uint8List imagen;

  /// `proveedor:modelo`. Viaja hasta la pantalla porque **una imagen generada
  /// tiene que poder decir que lo es**: mostrarla sin aclararlo seria hacer
  /// pasar por foto algo que no lo es.
  final String generadaPor;
}

class RepositorioVestidor {
  const RepositorioVestidor(this._dio);

  final Dio _dio;

  /// Si el probado por IA se puede ofrecer.
  ///
  /// Se consulta UNA vez, al abrir el vestidor, y la pantalla esconde el boton
  /// si la respuesta es que no. Un boton que siempre da error es peor que no
  /// tenerlo: el cliente lo prueba tres veces antes de creer que no funciona.
  ///
  /// Ante cualquier fallo devuelve `false` en vez de lanzar: esto es una
  /// comodidad opcional, y que la consulta falle no puede impedir abrir la
  /// camara.
  Future<bool> hayProbador() async {
    try {
      final respuesta = await _dio.get<Map<String, dynamic>>(
        '/vestidor/probador',
      );
      return respuesta.data?['disponible'] as bool? ?? false;
    } catch (_) {
      return false;
    }
  }

  /// Manda la captura y devuelve la imagen con la prenda amoldada.
  ///
  /// Tarda segundos: quien llama tiene que mostrar que esta trabajando.
  Future<PrendaAmoldada> amoldar({
    required int varianteId,
    required Uint8List captura,
  }) async {
    try {
      final formulario = FormData.fromMap({
        'variante_id': varianteId,
        'captura': MultipartFile.fromBytes(captura, filename: 'captura.png'),
      });
      final respuesta = await _dio.post<List<int>>(
        '/vestidor/probar',
        data: formulario,
        // La respuesta es el PNG crudo y no un JSON: base64 dentro de un JSON
        // infla un tercio el tamano y obliga a decodificar en el hilo de
        // interfaz.
        options: Options(
          responseType: ResponseType.bytes,
          // Holgado a proposito: componer una imagen tarda mucho mas que
          // cualquier otra peticion de esta app, y el tiempo de respuesta
          // general la cortaria a la mitad.
          receiveTimeout: const Duration(seconds: 120),
          sendTimeout: const Duration(seconds: 60),
        ),
      );
      return PrendaAmoldada(
        imagen: Uint8List.fromList(respuesta.data ?? const []),
        generadaPor:
            respuesta.headers.value('x-generada-por') ?? 'inteligencia artificial',
      );
    } on DioException catch (fallo) {
      throw _traducir(fallo);
    }
  }

  ErrorProbador _traducir(DioException fallo) {
    final codigo = fallo.response?.statusCode;

    // El cuerpo llega como bytes porque se pidio `ResponseType.bytes`, asi que
    // el mensaje del backend no se puede leer como JSON sin decodificarlo. No
    // vale la pena: lo que la pantalla necesita es el TIPO, y el texto propio
    // es mas claro que el generico del servidor para estos tres casos.
    return switch (codigo) {
      503 => const ErrorProbador(
        'El probado con inteligencia artificial no está habilitado.',
        tipo: TipoErrorProbador.apagado,
        codigo: 503,
      ),
      404 => const ErrorProbador(
        'Esta prenda no tiene imagen para amoldar.',
        tipo: TipoErrorProbador.sinPrenda,
        codigo: 404,
      ),
      502 => const ErrorProbador(
        'El servicio de imágenes no respondió. Su captura sigue guardada.',
        tipo: TipoErrorProbador.servicioCaido,
        codigo: 502,
      ),
      _ => ErrorProbador(
        traducirError(fallo).mensaje,
        tipo: TipoErrorProbador.sistema,
        codigo: codigo,
      ),
    };
  }
}
