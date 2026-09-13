/// Modelos del contrato de reservas (P6) --- CU-22 a CU-25.
///
/// Espejo de `backend/app/modules/reservas/schemas.py`, igual que
/// `frontend-web/src/app/core/models/reservas.models.ts` lo es en la web. Los
/// nombres JSON se leen tal como los emite la API --- en castellano y en
/// `snake_case` --- y esta es la unica capa que hay que tocar si cambian.
///
/// Archivo propio y no agregado a `catalogo.dart`, por el mismo motivo que en
/// la web: asi ninguna rama comparte lineas con otra durante el ciclo (seccion
/// 5 del acuerdo de organizacion).
library;

// --- Estados ---------------------------------------------------------------

/// Los cinco estados del ciclo de vida. Ver el diagrama en `models.py`.
///
/// Es un `enum` con el nombre del backend adentro y no una cadena suelta: un
/// `switch` sobre el enum obliga al compilador a contemplar los cinco, y el dia
/// que se agregue uno los `switch` dejan de compilar en vez de caer en un
/// `default` sin que nadie se entere.
enum EstadoReserva {
  pendiente('PENDIENTE', 'Pendiente'),
  preparada('PREPARADA', 'Preparada'),
  atendida('ATENDIDA', 'Atendida'),
  cancelada('CANCELADA', 'Cancelada'),
  expirada('EXPIRADA', 'Expirada');

  const EstadoReserva(this.codigo, this.rotulo);

  /// Como lo escribe el backend.
  final String codigo;

  /// Como se le muestra al cliente.
  final String rotulo;

  /// Los dos estados en los que la reserva sigue reteniendo stock y probador.
  ///
  /// Es la contraparte de `ESTADOS_VIVOS` del repositorio del backend, que se
  /// declara una sola vez alli por el mismo motivo: el control de capacidad de
  /// CU-22, la cancelacion de CU-23 y la expiracion de CU-25 tienen que estar
  /// de acuerdo sobre que es una reserva viva.
  bool get esViva => this == pendiente || this == preparada;

  /// Si el cliente todavia puede cancelarla (RF29).
  ///
  /// `PREPARADA` tambien se cancela: que el Encargado ya haya juntado las
  /// prendas no le quita al cliente el derecho a avisar que no va. Lo que no se
  /// cancela es una reserva ATENDIDA, CANCELADA o EXPIRADA.
  bool get seCancela => esViva;

  static EstadoReserva desdeCodigo(String codigo) {
    return EstadoReserva.values.firstWhere(
      (e) => e.codigo == codigo,
      // Un estado que esta version de la app todavia no conoce no puede tumbar
      // la pantalla. Se cae en `expirada`, que es lo conservador: se muestra
      // como cerrada y por lo tanto NO ofrece cancelar, en vez de ofrecer una
      // accion que el servidor va a rechazar.
      orElse: () => EstadoReserva.expirada,
    );
  }
}

// --- CU-22 - Crear reserva -------------------------------------------------

/// Una prenda y cuantas unidades se apartan de ella.
class LineaReserva {
  const LineaReserva({required this.varianteId, required this.cantidad});

  final int varianteId;
  final int cantidad;

  Map<String, dynamic> aJson() => {
    'variante_id': varianteId,
    'cantidad': cantidad,
  };
}

/// El cuerpo del `POST /reservas`.
class ReservaCrear {
  const ReservaCrear({
    required this.sucursalId,
    required this.franjaInicio,
    required this.franjaFin,
    required this.lineas,
  });

  final int sucursalId;

  /// **Con desfase horario y conservando la hora de pared.** Ver [conDesfase].
  final String franjaInicio;
  final String franjaFin;

  final List<LineaReserva> lineas;

  Map<String, dynamic> aJson() => {
    'sucursal_id': sucursalId,
    'franja_inicio': franjaInicio,
    'franja_fin': franjaFin,
    'lineas': lineas.map((l) => l.aJson()).toList(),
  };
}

/// Convierte una fecha local a ISO **conservando la hora de pared**.
///
/// `toIso8601String()` no sirve aca y el motivo no es evidente: sobre una fecha
/// en UTC devuelve `19:00Z` para las 15:00 de Bolivia, y sobre una local
/// devuelve `15:00` **sin desfase**, que el backend rechaza con un 422 porque
/// `ReservaCrearIn._con_zona_horaria` exige la zona.
///
/// El servidor compara la hora de la franja contra `sucursal.horario_apertura`,
/// que es un `TIME` sin zona y significa «abre a las nueve» en esa tienda; con
/// la hora convertida a UTC, un local que cierra a las 18:00 rechazaria una
/// reserva de las 15:00 por cuatro horas de diferencia horaria.
///
/// Lo que hace falta es mandar la hora tal cual **mas el desfase** ---
/// `2026-09-12T15:00:00-04:00` ---, que es lo que el backend exige y lo que
/// `timestamptz` guarda sin ambiguedad. Es el mismo `conDesfase()` de
/// `reserva-formulario.ts` en la web.
String conDesfase(DateTime fecha) {
  final local = fecha.isUtc ? fecha.toLocal() : fecha;

  // `timeZoneOffset` de Dart ya viene con el signo correcto y resuelto para
  // ESE instante, asi que contempla el horario de verano solo. (En JavaScript
  // hay que invertirle el signo a `getTimezoneOffset()`; aca no.)
  final desfase = local.timeZoneOffset;
  final signo = desfase.isNegative ? '-' : '+';
  final minutos = desfase.inMinutes.abs();

  String p(int n) => n.toString().padLeft(2, '0');

  return '${local.year}-${p(local.month)}-${p(local.day)}'
      'T${p(local.hour)}:${p(local.minute)}:00'
      '$signo${p(minutos ~/ 60)}:${p(minutos % 60)}';
}

// --- CU-23 - Cancelar ------------------------------------------------------

/// El cuerpo del `PATCH /reservas/{id}/cancelacion`.
///
/// El motivo es **opcional**: cancelar no es un tramite y exigir una
/// justificacion para no ir a probarse ropa solo consigue que la gente escriba
/// «asdf». Lo que si se guarda siempre es quien y cuando, en el movimiento de
/// `LIBERACION`.
class CancelarReserva {
  const CancelarReserva({this.motivo});

  final String? motivo;

  Map<String, dynamic> aJson() => {if (motivo != null) 'motivo': motivo};
}

// --- Salida ----------------------------------------------------------------

/// Una linea de la reserva, con la prenda ya nombrada.
///
/// Igual que en P4, la variante se nombra y no se numera: «variante 412» no le
/// dice nada a un cliente mirando su reserva en el telefono.
class LineaReservaDetalle {
  const LineaReservaDetalle({
    required this.id,
    required this.varianteId,
    required this.sku,
    required this.producto,
    required this.talla,
    required this.color,
    required this.cantidad,
    this.resultadoPrueba,
  });

  final int id;
  final int varianteId;
  final String sku;
  final String producto;
  final String talla;
  final String color;
  final int cantidad;

  /// `LLEVA` o `NO_LLEVA`. Lo escribe CU-24 al atender; es nulo mientras la
  /// reserva sigue viva.
  final String? resultadoPrueba;

  bool get seLaLlevo => resultadoPrueba == 'LLEVA';

  factory LineaReservaDetalle.desdeJson(Map<String, dynamic> json) {
    return LineaReservaDetalle(
      id: json['id'] as int,
      varianteId: json['variante_id'] as int,
      sku: json['sku'] as String,
      producto: json['producto'] as String,
      talla: json['talla'] as String,
      color: json['color'] as String,
      cantidad: json['cantidad'] as int,
      resultadoPrueba: json['resultado_prueba'] as String?,
    );
  }
}

/// Una reserva con su detalle.
class Reserva {
  const Reserva({
    required this.id,
    required this.clienteId,
    required this.sucursalId,
    required this.sucursal,
    required this.ciudad,
    required this.franjaInicio,
    required this.franjaFin,
    required this.estado,
    required this.creadoEn,
    required this.unidades,
    required this.lineas,
    this.observacion,
  });

  final int id;
  final int clienteId;
  final int sucursalId;
  final String sucursal;
  final String ciudad;

  /// En hora local del telefono. El backend las emite con zona y
  /// `DateTime.parse` devuelve el instante en UTC; se pasa a local aqui, una
  /// sola vez, para que ninguna pantalla se olvide de hacerlo y muestre una
  /// franja corrida cuatro horas.
  final DateTime franjaInicio;
  final DateTime franjaFin;

  final EstadoReserva estado;

  /// Nota de **cierre**: la escribe CU-23 al cancelar o CU-24 al atender.
  final String? observacion;

  final DateTime creadoEn;

  /// Suma de las cantidades de todas las lineas.
  final int unidades;

  final List<LineaReservaDetalle> lineas;

  factory Reserva.desdeJson(Map<String, dynamic> json) {
    return Reserva(
      id: json['id'] as int,
      clienteId: json['cliente_id'] as int,
      sucursalId: json['sucursal_id'] as int,
      sucursal: json['sucursal'] as String,
      ciudad: json['ciudad'] as String,
      franjaInicio: DateTime.parse(json['franja_inicio'] as String).toLocal(),
      franjaFin: DateTime.parse(json['franja_fin'] as String).toLocal(),
      estado: EstadoReserva.desdeCodigo(json['estado'] as String),
      observacion: json['observacion'] as String?,
      creadoEn: DateTime.parse(json['creado_en'] as String).toLocal(),
      unidades: json['unidades'] as int? ?? 0,
      lineas: (json['lineas'] as List<dynamic>? ?? [])
          .map((l) => LineaReservaDetalle.desdeJson(l as Map<String, dynamic>))
          .toList(),
    );
  }
}

/// Fila del listado.
///
/// `cliente` no se lee a proposito: viaja en el esquema para el panel del
/// Encargado (CU-24), que es web, y el Cliente ya sabe que las reservas son
/// suyas.
class ReservaResumen {
  const ReservaResumen({
    required this.id,
    required this.sucursalId,
    required this.sucursal,
    required this.ciudad,
    required this.franjaInicio,
    required this.franjaFin,
    required this.estado,
    required this.prendas,
    required this.unidades,
  });

  final int id;
  final int sucursalId;
  final String sucursal;
  final String ciudad;
  final DateTime franjaInicio;
  final DateTime franjaFin;
  final EstadoReserva estado;

  /// Cuantas prendas distintas.
  final int prendas;

  /// Cuantas unidades en total. Puede ser mayor que [prendas]: dos unidades de
  /// la misma blusa son una prenda y dos unidades.
  final int unidades;

  String get prendasRotuladas =>
      prendas == 1 ? '1 prenda' : '$prendas prendas';

  factory ReservaResumen.desdeJson(Map<String, dynamic> json) {
    return ReservaResumen(
      id: json['id'] as int,
      sucursalId: json['sucursal_id'] as int,
      sucursal: json['sucursal'] as String,
      ciudad: json['ciudad'] as String,
      franjaInicio: DateTime.parse(json['franja_inicio'] as String).toLocal(),
      franjaFin: DateTime.parse(json['franja_fin'] as String).toLocal(),
      estado: EstadoReserva.desdeCodigo(json['estado'] as String),
      prendas: json['prendas'] as int? ?? 0,
      unidades: json['unidades'] as int? ?? 0,
    );
  }
}

/// Listado paginado, con el total aparte.
class PaginaReservas {
  const PaginaReservas({
    required this.total,
    required this.pagina,
    required this.tamano,
    required this.items,
  });

  final int total;
  final int pagina;
  final int tamano;
  final List<ReservaResumen> items;

  bool get hayMas => pagina * tamano < total;

  factory PaginaReservas.desdeJson(Map<String, dynamic> json) {
    return PaginaReservas(
      total: json['total'] as int,
      pagina: json['pagina'] as int,
      tamano: json['tamano'] as int,
      items: (json['items'] as List<dynamic>? ?? [])
          .map((r) => ReservaResumen.desdeJson(r as Map<String, dynamic>))
          .toList(),
    );
  }
}

// --- Formato de la franja --------------------------------------------------
//
// A mano y no con `intl`: `DateFormat` con una configuracion regional distinta
// de la del sistema exige llamar a `initializeDateFormatting('es')` en el
// arranque, y olvidarse de eso produce una excepcion en tiempo de ejecucion en
// vez de un error de compilacion. Son dos listas y tres funciones.

const List<String> _dias = [
  'lunes',
  'martes',
  'miércoles',
  'jueves',
  'viernes',
  'sábado',
  'domingo',
];

const List<String> _meses = [
  'enero',
  'febrero',
  'marzo',
  'abril',
  'mayo',
  'junio',
  'julio',
  'agosto',
  'septiembre',
  'octubre',
  'noviembre',
  'diciembre',
];

String _dosDigitos(int n) => n.toString().padLeft(2, '0');

/// `15:00`.
String soloHora(DateTime fecha) =>
    '${_dosDigitos(fecha.hour)}:${_dosDigitos(fecha.minute)}';

/// `viernes 12 de septiembre`, con `hoy` y `mañana` por delante cuando toca.
///
/// El dia relativo va primero a proposito: la pregunta del cliente al abrir
/// «Mis reservas» es «¿cuándo tengo que ir?», y «mañana» la contesta de un
/// vistazo mientras que «13 de septiembre» obliga a pensar.
String diaLargo(DateTime fecha) {
  final hoy = DateTime.now();
  // Se comparan los dias pelados y no los instantes: a las 23:00, una franja de
  // las 00:30 esta a hora y media pero es «mañana», no «hoy».
  final diferencia = DateTime(fecha.year, fecha.month, fecha.day)
      .difference(DateTime(hoy.year, hoy.month, hoy.day))
      .inDays;

  final fijo =
      '${_dias[fecha.weekday - 1]} ${fecha.day} de ${_meses[fecha.month - 1]}';

  return switch (diferencia) {
    0 => 'hoy, $fijo',
    1 => 'mañana, $fijo',
    _ => fijo,
  };
}

/// `viernes 12 de septiembre · 15:00 – 16:00`.
///
/// La franja se escribe entera y no solo el inicio porque lo que el cliente
/// reservo es un rango: saber hasta cuando puede llegar es la mitad del dato.
String franjaCompleta(DateTime inicio, DateTime fin) =>
    '${diaLargo(inicio)} · ${soloHora(inicio)} – ${soloHora(fin)}';
