/// Acceso a los endpoints de compra (P7 y P8) --- CU-26 y CU-27.
///
/// Un repositorio por paquete de analisis, igual que `RepositorioReservas`: es
/// el unico lugar de la app que conoce las rutas de `/tienda/carrito` y
/// `/tienda/pedidos`; las pantallas hablan con el, nunca con Dio.
///
/// Solo el ambito del **Cliente**. El punto de venta (CU-31), la caja (CU-30) y
/// las devoluciones (CU-32) son del Cajero y viven en la web.
///
/// LOS CINCO ENDPOINTS DEL CARRITO DEVUELVEN EL CARRITO ENTERO
/// ------------------------------------------------------------
/// No solo la linea tocada. Es una decision del backend (CU-26) y la app se
/// apoya en ella: cada operacion deja el estado completo y actualizado, asi que
/// la burbuja del icono y el total se refrescan sin una segunda consulta.
library;

import 'package:dio/dio.dart';

import '../../core/red/excepciones.dart';
import '../modelos/compra.dart';

/// Por que fallo una operacion de compra.
///
/// El repositorio no se conforma con el mensaje: clasifica el error, porque
/// cada clase lleva a una accion distinta en la pantalla y el texto suelto no
/// permite decidirla. Mismo reparto que hace `ErrorReservas`.
enum TipoErrorCompra {
  /// El total cambio entre mirar el carrito y confirmar. **Trae el total nuevo
  /// y el carrito al dia**: la pantalla tiene que mostrar QUE cambio, no solo
  /// que cambio. Es la decision 3 de CU-27.
  precioCambiado,

  /// Ya hay un pedido esperando pago. Trae su [ErrorCompra.codigoPedido] para
  /// poder ofrecer ir a pagarlo o cancelarlo en vez de dejar al cliente
  /// atascado. Es la decision 4 de CU-27.
  pedidoPendiente,

  /// Alguien se llevo la ultima unidad mientras el cliente confirmaba, o la
  /// sucursal elegida no abastece el pedido entero. Lo que corresponde es
  /// **refrescar las opciones**, no reintentar contra un numero viejo.
  sinStock,

  /// El carrito esta vacio o tiene prendas que dejaron de ofrecerse. Manda de
  /// vuelta al carrito, no al selector de sucursal.
  carritoInvalido,

  /// La prenda ya no esta en el catalogo (E1 de CU-26).
  prendaNoOfrecible,

  /// Solo se cancela un pedido que todavia espera pago.
  pedidoNoCancelable,

  /// No existe, o es de otro cliente. El servidor responde el mismo 404 a las
  /// dos cosas a proposito: un 403 confirmaria que ese pedido existe.
  noEncontrado,

  /// La cuenta no tiene ficha de cliente. Se arregla completando el perfil.
  sinFicha,

  /// La pasarela de pago no respondio (502). **No es culpa nuestra y no quedo
  /// nada escrito**: el cliente puede reintentar tal cual.
  pasarelaCaida,

  /// El resto de los 422.
  validacion,

  /// Conexion, 5xx y lo que no encaje en lo anterior.
  sistema,
}

/// Un [ErrorApi] clasificado.
class ErrorCompra extends ErrorApi {
  const ErrorCompra(
    super.mensaje, {
    required this.tipo,
    super.codigo,
    this.totalEsperado,
    this.totalActual,
    this.lineas = const [],
    this.codigoPedido,
  });

  final TipoErrorCompra tipo;

  /// Solo en [TipoErrorCompra.precioCambiado].
  final String? totalEsperado;
  final String? totalActual;

  /// Solo en [TipoErrorCompra.precioCambiado]: el carrito al dia, para que el
  /// cliente vea que linea cambio sin tener que recargar y comparar de memoria.
  final List<LineaCarrito> lineas;

  /// Solo en [TipoErrorCompra.pedidoPendiente]: cual es.
  final String? codigoPedido;
}

class RepositorioCompra {
  const RepositorioCompra(this._dio);

  final Dio _dio;

  // --- CU-26 · El carrito ---------------------------------------------------

  /// El carrito del cliente del token, con precios y disponibilidad al dia.
  ///
  /// Leerlo NO lo crea: quien nunca agrego nada recibe un carrito de cero
  /// lineas y no queda una fila de rastro.
  Future<Carrito> verCarrito() async {
    try {
      final respuesta = await _dio.get<Map<String, dynamic>>('/tienda/carrito');
      return Carrito.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw _traducir(fallo);
    }
  }

  /// Agregar una prenda. **SUMA** a lo que ya hubiera de esa variante.
  ///
  /// Es lo que espera quien pulsa «Agregar» dos veces desde la ficha: la
  /// segunda vez no reemplaza la primera. Para fijar la cantidad esta
  /// [fijarCantidad], que va por otro verbo a proposito.
  Future<Carrito> agregar({required int varianteId, int cantidad = 1}) async {
    try {
      final respuesta = await _dio.post<Map<String, dynamic>>(
        '/tienda/carrito/items',
        data: {'variante_id': varianteId, 'cantidad': cantidad},
      );
      return Carrito.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw _traducir(fallo);
    }
  }

  /// Fijar la cantidad de una linea. **NO suma**: reemplaza.
  Future<Carrito> fijarCantidad({
    required int varianteId,
    required int cantidad,
  }) async {
    try {
      final respuesta = await _dio.patch<Map<String, dynamic>>(
        '/tienda/carrito/items/$varianteId',
        data: {'cantidad': cantidad},
      );
      return Carrito.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw _traducir(fallo);
    }
  }

  /// Quitar una linea. Para dejarla en cero esta esto, no `fijarCantidad(0)`:
  /// el `CHECK` de la base rechaza una linea de cantidad cero.
  Future<Carrito> quitar(int varianteId) async {
    try {
      final respuesta = await _dio.delete<Map<String, dynamic>>(
        '/tienda/carrito/items/$varianteId',
      );
      return Carrito.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw _traducir(fallo);
    }
  }

  /// Vaciar el carrito entero.
  Future<Carrito> vaciar() async {
    try {
      final respuesta = await _dio.delete<Map<String, dynamic>>(
        '/tienda/carrito',
      );
      return Carrito.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw _traducir(fallo);
    }
  }

  // --- CU-27 · El pedido ----------------------------------------------------

  /// Paso 1: el carrito, las sucursales que pueden abastecerlo y mis
  /// direcciones, **en una sola peticion**.
  ///
  /// Junto y no en tres viajes: pedirlo por separado dejaria la pantalla
  /// pintandose por partes y abriria una ventana en la que el total podria
  /// cambiar entre una consulta y la siguiente.
  Future<OpcionesDePedido> opciones() async {
    try {
      final respuesta = await _dio.get<Map<String, dynamic>>(
        '/tienda/pedidos/opciones',
      );
      return OpcionesDePedido.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw _traducir(fallo);
    }
  }

  /// Paso 2: confirmar el pedido e iniciar el pago.
  ///
  /// Devuelve el pedido en `PENDIENTE_PAGO` y la URL de la pasarela. El estado
  /// **no lo mueve esta llamada**: lo mueve el webhook verificado de CU-28. Es
  /// la decision D5.
  Future<PedidoCreado> crear(CrearPedido datos) async {
    try {
      final respuesta = await _dio.post<Map<String, dynamic>>(
        '/tienda/pedidos',
        data: datos.aJson(),
      );
      return PedidoCreado.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw _traducir(fallo);
    }
  }

  /// La ficha de un pedido propio.
  ///
  /// Es lo que se consulta al volver de la pasarela, y devuelve el estado que
  /// dice la BASE, no el que diga la URL por la que el navegador volvio.
  Future<Pedido> obtener(String codigo) async {
    try {
      final respuesta = await _dio.get<Map<String, dynamic>>(
        '/tienda/pedidos/$codigo',
      );
      return Pedido.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw _traducir(fallo);
    }
  }

  /// Cancelar un pedido que todavia espera pago y devolver el stock apartado.
  ///
  /// Una venta ya pagada NO se cancela por aca: eso es una devolucion (CU-32),
  /// que mueve dinero y necesita una caja.
  Future<Pedido> cancelar(String codigo) async {
    try {
      final respuesta = await _dio.post<Map<String, dynamic>>(
        '/tienda/pedidos/$codigo/cancelar',
      );
      return Pedido.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw _traducir(fallo);
    }
  }

  // --- Internos -------------------------------------------------------------

  /// Clasifica el fallo sin perder el mensaje del backend.
  ///
  /// El texto sale de `router.py`, que ya lo escribio para el usuario y con los
  /// datos del caso concreto --- que prendas faltan, cual es el pedido
  /// pendiente ---. Reescribirlo aca seria perder ese detalle y arriesgarse a
  /// que la app y la API digan cosas distintas del mismo error.
  ErrorCompra _traducir(DioException fallo) {
    if (fallo.type != DioExceptionType.badResponse) {
      final generico = traducirError(fallo);
      return ErrorCompra(
        generico.mensaje,
        tipo: TipoErrorCompra.sistema,
        codigo: generico.codigo,
      );
    }

    final codigo = fallo.response?.statusCode;
    final cuerpo = fallo.response?.data;
    final bruto = cuerpo is Map<String, dynamic> ? cuerpo['detail'] : null;
    final detalle = bruto is String ? bruto : '';

    if (codigo == 502) {
      return ErrorCompra(
        detalle.isNotEmpty
            ? detalle
            : 'No pudimos comunicarnos con la pasarela de pago. Intente de nuevo.',
        tipo: TipoErrorCompra.pasarelaCaida,
        codigo: codigo,
      );
    }

    if (codigo == 404) {
      return ErrorCompra(
        detalle.isNotEmpty ? detalle : 'No encontramos ese pedido.',
        tipo: TipoErrorCompra.noEncontrado,
        codigo: codigo,
      );
    }

    if (codigo == 409) {
      // El precio cambiado viaja como OBJETO y no como texto: trae el total
      // nuevo y el carrito entero. Es el unico 409 con cuerpo estructurado, y
      // por eso se mira primero.
      if (bruto is Map<String, dynamic> && bruto['total_actual'] != null) {
        return ErrorCompra(
          bruto['detalle'] as String? ??
              'El precio cambió mientras usted decidía.',
          tipo: TipoErrorCompra.precioCambiado,
          codigo: codigo,
          totalEsperado: bruto['total_esperado']?.toString(),
          totalActual: bruto['total_actual']?.toString(),
          lineas: (bruto['lineas'] as List<dynamic>? ?? const [])
              .map((e) => LineaCarrito.desdeJson(e as Map<String, dynamic>))
              .toList(growable: false),
        );
      }

      // Los demas 409 se distinguen por el texto porque el backend no manda un
      // codigo propio. Frágil pero acotado: son las mismas cadenas que mira la
      // web, y cada una lleva a una accion distinta en la pantalla.
      if (detalle.contains('Ya tiene el pedido')) {
        return ErrorCompra(
          detalle,
          tipo: TipoErrorCompra.pedidoPendiente,
          codigo: codigo,
          codigoPedido: _codigoDeVenta(detalle),
        );
      }
      if (detalle.contains('ya no se puede cancelar')) {
        return ErrorCompra(
          detalle,
          tipo: TipoErrorCompra.pedidoNoCancelable,
          codigo: codigo,
        );
      }
      if (detalle.contains('carrito está vacío') ||
          detalle.contains('ya no se ofrecen')) {
        return ErrorCompra(
          detalle,
          tipo: TipoErrorCompra.carritoInvalido,
          codigo: codigo,
        );
      }
      if (detalle.contains('ficha de cliente')) {
        return ErrorCompra(detalle, tipo: TipoErrorCompra.sinFicha, codigo: codigo);
      }
      // Sucursal que no abastece, ninguna que abastezca, y la ultima unidad
      // que se llevo otro. Las tres se resuelven igual: refrescar opciones.
      return ErrorCompra(
        detalle.isNotEmpty ? detalle : 'Ese pedido ya no se puede hacer así.',
        tipo: TipoErrorCompra.sinStock,
        codigo: codigo,
      );
    }

    if (codigo == 403 && detalle.contains('ficha de cliente')) {
      return ErrorCompra(detalle, tipo: TipoErrorCompra.sinFicha, codigo: codigo);
    }

    if (codigo == 422) {
      return ErrorCompra(
        detalle.isNotEmpty ? detalle : 'Revise los datos del pedido.',
        tipo: TipoErrorCompra.validacion,
        codigo: codigo,
      );
    }

    final generico = traducirError(fallo);
    return ErrorCompra(
      generico.mensaje,
      tipo: TipoErrorCompra.sistema,
      codigo: generico.codigo,
    );
  }

  /// Saca `VB-20260917-A3F2` del mensaje «Ya tiene el pedido X esperando pago».
  ///
  /// Leer el codigo del texto es feo y se hace igual: sin el, la pantalla solo
  /// puede decirle al cliente que tiene un pedido pendiente y dejarlo que lo
  /// busque. Con el, le ofrece ir. Si el mensaje cambiara, se pierde el atajo
  /// pero no el aviso --- por eso devuelve nulo en vez de fallar.
  static String? _codigoDeVenta(String texto) {
    final hallazgo = RegExp(r'VB-\d{8}-[0-9A-F]+').firstMatch(texto);
    return hallazgo?.group(0);
  }
}
