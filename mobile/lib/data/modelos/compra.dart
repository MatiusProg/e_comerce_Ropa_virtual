/// Modelos del contrato de compra (P7 y P8) --- CU-26 y CU-27.
///
/// Espejo de `backend/app/modules/ventas/carrito_schemas.py` y
/// `backend/app/modules/ventas/schemas.py`. Los nombres JSON se leen tal como
/// los emite la API --- en castellano y en `snake_case` --- y esta es la unica
/// capa que hay que tocar si cambian.
///
/// Archivo propio y no agregado a `catalogo.dart`, por el mismo motivo que
/// `reservas.dart`: asi ninguna rama comparte lineas con otra durante el ciclo.
///
/// EL DINERO VIAJA COMO TEXTO, Y SE GUARDA COMO TEXTO
/// ---------------------------------------------------
/// La API emite `"250.00"`, no `250.0`. Se conserva la cadena y NO se convierte
/// a `double`: los binarios de punto flotante no representan exactamente los
/// decimales, y `0.1 + 0.2` da `0.30000000000000004` en Dart igual que en
/// cualquier otro lenguaje. Un total de carrito que se muestre con ese error, o
/// peor, que se reenvie al servidor en `total_esperado`, haria fallar la
/// comparacion de CU-27 por una diferencia invisible.
///
/// Para comparar o sumar hay `Decimal`... que no esta en el proyecto. No hace
/// falta: **la app no calcula totales**, los recibe ya calculados del servidor,
/// que es donde viven las reglas. Lo unico que hace con ellos es mostrarlos y
/// devolverlos intactos.
library;

// --- CU-26 · El carrito -----------------------------------------------------

/// Una prenda del carrito, con lo que hace falta para pintarla y decidir.
class LineaCarrito {
  const LineaCarrito({
    required this.varianteId,
    required this.productoId,
    required this.sku,
    required this.productoNombre,
    required this.tallaCodigo,
    required this.colorNombre,
    required this.imagenUrl,
    required this.cantidad,
    required this.precioUnitario,
    required this.subtotal,
    required this.disponible,
    required this.stockTotal,
  });

  factory LineaCarrito.desdeJson(Map<String, dynamic> json) {
    return LineaCarrito(
      varianteId: json['variante_id'] as int,
      productoId: json['producto_id'] as int,
      sku: json['sku'] as String,
      productoNombre: json['producto_nombre'] as String,
      tallaCodigo: json['talla_codigo'] as String?,
      colorNombre: json['color_nombre'] as String?,
      imagenUrl: json['imagen_url'] as String?,
      cantidad: json['cantidad'] as int,
      precioUnitario: json['precio_unitario'].toString(),
      subtotal: json['subtotal'].toString(),
      disponible: json['disponible'] as bool,
      stockTotal: json['stock_total'] as int,
    );
  }

  final int varianteId;
  final int productoId;
  final String sku;
  final String productoNombre;
  final String? tallaCodigo;
  final String? colorNombre;
  final String? imagenUrl;
  final int cantidad;

  /// Precio VIGENTE de la variante, no el que tenia al agregarla. El carrito no
  /// guarda precios: es una intencion, no un contrato. Se congela recien al
  /// confirmar el pedido (CU-27).
  final String precioUnitario;
  final String subtotal;

  /// `false` si la prenda dejo de ofrecerse despues de agregarla. La linea NO
  /// se borra sola: el cliente tiene que ver que estaba ahi. No suma al total.
  final bool disponible;

  /// Unidades en toda la red. Es un aviso, no una reserva.
  final int stockTotal;

  /// «M · Negro», o lo que haya. Para el subtitulo de la linea.
  String get descripcionVariante {
    final partes = [tallaCodigo, colorNombre].whereType<String>();
    return partes.isEmpty ? sku : partes.join(' · ');
  }
}

/// El carrito completo. Un carrito vacio NO es un error: es cero lineas.
class Carrito {
  const Carrito({
    required this.lineas,
    required this.items,
    required this.unidades,
    required this.total,
    required this.noDisponibles,
  });

  factory Carrito.desdeJson(Map<String, dynamic> json) {
    return Carrito(
      lineas: (json['lineas'] as List<dynamic>)
          .map((e) => LineaCarrito.desdeJson(e as Map<String, dynamic>))
          .toList(growable: false),
      items: json['items'] as int,
      unidades: json['unidades'] as int,
      total: json['total'].toString(),
      noDisponibles: json['no_disponibles'] as int,
    );
  }

  /// El carrito de quien todavia no agrego nada. Lo usa la burbuja del icono
  /// antes de la primera consulta, para no tener que pintar un `null`.
  static const Carrito vacio = Carrito(
    lineas: [],
    items: 0,
    unidades: 0,
    total: '0.00',
    noDisponibles: 0,
  );

  final List<LineaCarrito> lineas;

  /// Cuantas prendas distintas.
  final int items;

  /// Cuantas unidades en total. Es lo que va en la burbuja del icono.
  final int unidades;

  /// Suma de los subtotales de las lineas DISPONIBLES.
  final String total;

  /// Cuantas lineas dejaron de ofrecerse. Si es mayor que cero la pantalla lo
  /// dice arriba: el cliente tiene que enterarse de por que bajo su total.
  final int noDisponibles;

  bool get estaVacio => lineas.isEmpty;
}

// --- CU-27 · Las opciones del pedido ---------------------------------------

/// Las dos formas de recibir la compra.
enum ModalidadEntrega {
  retiro('RETIRO', 'Retiro en sucursal'),
  envio('ENVIO', 'Envío a domicilio');

  const ModalidadEntrega(this.codigo, this.rotulo);

  final String codigo;
  final String rotulo;

  static ModalidadEntrega? desdeCodigo(String? codigo) {
    for (final valor in values) {
      if (valor.codigo == codigo) return valor;
    }
    return null;
  }
}

/// Una sucursal donde se puede retirar ESTE pedido.
class SucursalParaRetiro {
  const SucursalParaRetiro({
    required this.id,
    required this.nombre,
    required this.direccion,
    required this.ciudad,
    required this.abasteceTodo,
    required this.faltantes,
  });

  factory SucursalParaRetiro.desdeJson(Map<String, dynamic> json) {
    return SucursalParaRetiro(
      id: json['id'] as int,
      nombre: json['nombre'] as String,
      direccion: json['direccion'] as String,
      ciudad: json['ciudad'] as String,
      abasteceTodo: json['abastece_todo'] as bool,
      faltantes: (json['faltantes'] as List<dynamic>? ?? const [])
          .map((e) => e.toString())
          .toList(growable: false),
    );
  }

  final int id;
  final String nombre;
  final String direccion;
  final String ciudad;

  /// Si tiene stock de TODAS las lineas del carrito. Un pedido se despacha
  /// desde una sola sucursal: `detalle_venta` no lleva sucursal por linea.
  final bool abasteceTodo;

  /// Cuando no abastece todo, que prendas le faltan. Se nombran en vez de
  /// decir «no disponible», que obliga al cliente a adivinar cual.
  final List<String> faltantes;
}

/// Una direccion registrada del cliente (CU-04).
class DireccionParaEnvio {
  const DireccionParaEnvio({
    required this.id,
    required this.alias,
    required this.direccion,
    required this.ciudad,
    required this.referencia,
    required this.predeterminada,
  });

  factory DireccionParaEnvio.desdeJson(Map<String, dynamic> json) {
    return DireccionParaEnvio(
      id: json['id'] as int,
      alias: json['alias'] as String,
      direccion: json['direccion'] as String,
      ciudad: json['ciudad'] as String,
      referencia: json['referencia'] as String?,
      predeterminada: json['predeterminada'] as bool,
    );
  }

  final int id;
  final String alias;
  final String direccion;
  final String ciudad;
  final String? referencia;
  final bool predeterminada;
}

/// Todo lo que la pantalla de confirmacion necesita, en UNA peticion.
class OpcionesDePedido {
  const OpcionesDePedido({
    required this.lineas,
    required this.total,
    required this.unidades,
    required this.sePuedePedir,
    required this.motivo,
    required this.sucursales,
    required this.direcciones,
    required this.pagoReal,
    required this.minutosParaPagar,
  });

  factory OpcionesDePedido.desdeJson(Map<String, dynamic> json) {
    return OpcionesDePedido(
      lineas: (json['lineas'] as List<dynamic>)
          .map((e) => LineaCarrito.desdeJson(e as Map<String, dynamic>))
          .toList(growable: false),
      total: json['total'].toString(),
      unidades: json['unidades'] as int,
      sePuedePedir: json['se_puede_pedir'] as bool,
      motivo: json['motivo'] as String?,
      sucursales: (json['sucursales'] as List<dynamic>)
          .map((e) => SucursalParaRetiro.desdeJson(e as Map<String, dynamic>))
          .toList(growable: false),
      direcciones: (json['direcciones'] as List<dynamic>)
          .map((e) => DireccionParaEnvio.desdeJson(e as Map<String, dynamic>))
          .toList(growable: false),
      pagoReal: json['pago_real'] as bool,
      minutosParaPagar: json['minutos_para_pagar'] as int,
    );
  }

  final List<LineaCarrito> lineas;
  final String total;
  final int unidades;

  /// Si es `false`, el boton de confirmar va deshabilitado y la pantalla dice
  /// [motivo]. Es `false` con el carrito vacio, con lineas caidas, o cuando
  /// ninguna sucursal abastece el pedido entero.
  final bool sePuedePedir;
  final String? motivo;

  final List<SucursalParaRetiro> sucursales;
  final List<DireccionParaEnvio> direcciones;

  /// Si el proveedor de pago configurado mueve dinero de verdad. La pantalla lo
  /// dice con todas las letras cuando es `false`: en la demostracion el pago es
  /// de mentira, y hacerlo pasar por real seria enganar a quien mira.
  final bool pagoReal;

  /// Cuantos minutos aguanta el pedido sin pagar antes de cancelarse solo.
  final int minutosParaPagar;

  /// Las que pueden con el pedido entero. Es lo unico que se ofrece para
  /// retirar; las demas se listan deshabilitadas con su motivo.
  List<SucursalParaRetiro> get sucursalesQuePueden =>
      sucursales.where((s) => s.abasteceTodo).toList(growable: false);
}

// --- CU-27 · El pedido ------------------------------------------------------

/// Los cuatro estados de una venta. Ver `ventas/models.py`.
enum EstadoPedido {
  pendientePago('PENDIENTE_PAGO', 'Esperando el pago'),
  pagada('PAGADA', 'Pagado'),
  entregada('ENTREGADA', 'Entregado'),
  cancelada('CANCELADA', 'Cancelado');

  const EstadoPedido(this.codigo, this.rotulo);

  final String codigo;
  final String rotulo;

  static EstadoPedido desdeCodigo(String codigo) {
    for (final valor in values) {
      if (valor.codigo == codigo) return valor;
    }
    // Un estado que la app no conoce no deberia tumbarla: se muestra como
    // pendiente, que es el mas conservador --- no afirma que se cobro.
    return EstadoPedido.pendientePago;
  }

  /// Si todavia espera el pago. Es el unico estado en el que el cliente puede
  /// pagar o cancelar.
  bool get esperaPago => this == pendientePago;
}

/// Una linea ya vendida, con su precio CONGELADO.
///
/// Distinta de [LineaCarrito] justamente en eso: aquella lleva el precio
/// vigente y esta lleva el que se cobro. Si fueran la misma clase, el historial
/// de compras mostraria precios que cambian solos.
class LineaPedido {
  const LineaPedido({
    required this.varianteId,
    required this.sku,
    required this.productoNombre,
    required this.tallaCodigo,
    required this.colorNombre,
    required this.imagenUrl,
    required this.cantidad,
    required this.precioUnitario,
    required this.descuentoUnitario,
    required this.subtotal,
  });

  factory LineaPedido.desdeJson(Map<String, dynamic> json) {
    return LineaPedido(
      varianteId: json['variante_id'] as int,
      sku: json['sku'] as String,
      productoNombre: json['producto_nombre'] as String,
      tallaCodigo: json['talla_codigo'] as String?,
      colorNombre: json['color_nombre'] as String?,
      imagenUrl: json['imagen_url'] as String?,
      cantidad: json['cantidad'] as int,
      precioUnitario: json['precio_unitario'].toString(),
      descuentoUnitario: json['descuento_unitario'].toString(),
      subtotal: json['subtotal'].toString(),
    );
  }

  final int varianteId;
  final String sku;
  final String productoNombre;
  final String? tallaCodigo;
  final String? colorNombre;
  final String? imagenUrl;
  final int cantidad;
  final String precioUnitario;
  final String descuentoUnitario;
  final String subtotal;

  String get descripcionVariante {
    final partes = [tallaCodigo, colorNombre].whereType<String>();
    return partes.isEmpty ? sku : partes.join(' · ');
  }
}

/// Un pedido. Es una `venta`: no hay tabla `pedido` (decision D2).
class Pedido {
  const Pedido({
    required this.codigo,
    required this.estado,
    required this.canal,
    required this.modalidadEntrega,
    required this.sucursalId,
    required this.sucursalNombre,
    required this.direccionEnvio,
    required this.lineas,
    required this.subtotal,
    required this.descuento,
    required this.total,
    required this.creadoEn,
    required this.pagarAntesDe,
    required this.estadoPago,
  });

  factory Pedido.desdeJson(Map<String, dynamic> json) {
    return Pedido(
      codigo: json['codigo'] as String,
      estado: EstadoPedido.desdeCodigo(json['estado'] as String),
      canal: json['canal'] as String,
      modalidadEntrega: ModalidadEntrega.desdeCodigo(
        json['modalidad_entrega'] as String?,
      ),
      sucursalId: json['sucursal_id'] as int,
      sucursalNombre: json['sucursal_nombre'] as String,
      direccionEnvio: json['direccion_envio'] as String?,
      lineas: (json['lineas'] as List<dynamic>)
          .map((e) => LineaPedido.desdeJson(e as Map<String, dynamic>))
          .toList(growable: false),
      subtotal: json['subtotal'].toString(),
      descuento: json['descuento'].toString(),
      total: json['total'].toString(),
      creadoEn: DateTime.parse(json['creado_en'] as String),
      pagarAntesDe: json['pagar_antes_de'] == null
          ? null
          : DateTime.parse(json['pagar_antes_de'] as String),
      estadoPago: json['estado_pago'] as String?,
    );
  }

  final String codigo;
  final EstadoPedido estado;
  final String canal;
  final ModalidadEntrega? modalidadEntrega;
  final int sucursalId;
  final String sucursalNombre;

  /// Nula en un retiro.
  final String? direccionEnvio;

  final List<LineaPedido> lineas;
  final String subtotal;
  final String descuento;
  final String total;
  final DateTime creadoEn;

  /// Hasta cuando se puede pagar. Nula si el pedido ya no espera pago.
  final DateTime? pagarAntesDe;

  /// Estado de la fila `pago`. Nulo si todavia no se creo.
  final String? estadoPago;

  /// Cuanto falta para que el pedido se cancele solo. Negativo si ya venció:
  /// la barrida todavia no paso, pero el cliente no deberia intentar pagarlo.
  Duration? get tiempoRestante =>
      pagarAntesDe?.difference(DateTime.now());
}

/// La respuesta de confirmar: el pedido y adonde ir a pagar.
class PedidoCreado {
  const PedidoCreado({
    required this.pedido,
    required this.urlPago,
    required this.pagoReal,
  });

  factory PedidoCreado.desdeJson(Map<String, dynamic> json) {
    return PedidoCreado(
      pedido: Pedido.desdeJson(json['pedido'] as Map<String, dynamic>),
      urlPago: json['url_pago'] as String,
      pagoReal: json['pago_real'] as bool,
    );
  }

  final Pedido pedido;

  /// Adonde mandar el navegador del telefono.
  final String urlPago;

  /// `false` con el proveedor `simulada`.
  final bool pagoReal;
}

/// Lo que el cliente confirma.
class CrearPedido {
  const CrearPedido({
    required this.modalidadEntrega,
    required this.totalEsperado,
    this.sucursalId,
    this.direccionId,
  });

  final ModalidadEntrega modalidadEntrega;

  /// El total que el cliente VIO en la pantalla cuando pulso confirmar.
  ///
  /// El carrito no congela precios, asi que entre mirar y confirmar la tienda
  /// pudo cambiar uno. Sin este campo el sistema cobraria el precio nuevo
  /// callado. Con el, el servidor se planta y devuelve 409 con el total nuevo.
  ///
  /// Viaja como la MISMA cadena que mando el servidor, sin reconstruirla: ver
  /// la nota de la cabecera sobre por que el dinero no pasa por `double`.
  final String totalEsperado;

  final int? sucursalId;
  final int? direccionId;

  Map<String, dynamic> aJson() => <String, dynamic>{
    'modalidad_entrega': modalidadEntrega.codigo,
    'total_esperado': totalEsperado,
    if (sucursalId != null) 'sucursal_id': sucursalId,
    if (direccionId != null) 'direccion_id': direccionId,
  };
}

/// CU-29 · una pagina del historial de compras.
///
/// Los items son `Pedido` ENTEROS, con sus lineas: es lo que devuelve
/// `/tienda/compras` y es el mismo objeto que ya usa la pantalla del pedido.
/// Un resumen aparte obligaria a mantener dos formas del mismo dato y a pedir
/// la ficha de nuevo al tocar una fila.
class PaginaDeCompras {
  const PaginaDeCompras({
    required this.total,
    required this.pagina,
    required this.tamano,
    required this.items,
  });

  final int total;
  final int pagina;
  final int tamano;
  final List<Pedido> items;

  bool get hayMas => pagina * tamano < total;

  factory PaginaDeCompras.desdeJson(Map<String, dynamic> json) {
    return PaginaDeCompras(
      total: json['total'] as int,
      pagina: json['pagina'] as int,
      tamano: json['tamano'] as int,
      items: (json['items'] as List<dynamic>? ?? const [])
          .map((p) => Pedido.desdeJson(p as Map<String, dynamic>))
          .toList(growable: false),
    );
  }
}
