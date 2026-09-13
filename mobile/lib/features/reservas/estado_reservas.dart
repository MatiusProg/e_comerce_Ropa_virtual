/// Estado de las reservas del cliente (CU-22 y CU-23).
///
/// Sigue el patron de `estado_catalogo.dart`: los proveedores arriba, el
/// control abajo. Ninguna pantalla construye un repositorio ni guarda
/// resultados en un `State`; el estado vive aca y las pantallas lo observan.
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/modelos/catalogo.dart';
import '../../data/modelos/reservas.dart';
import '../../data/repositorios/repositorio_reservas.dart';
import '../auth/estado_sesion.dart';
import '../catalogo/estado_catalogo.dart';

// --- Proveedores ----------------------------------------------------------

final repositorioReservasProvider = Provider<RepositorioReservas>((ref) {
  return RepositorioReservas(ref.watch(clienteApiProvider));
});

/// Mis reservas, separadas en vivas y cerradas.
///
/// `family` sobre `vivas` y no una sola consulta partida en la pantalla: son
/// dos preguntas distintas --- «¿cuándo tengo que ir?» y «¿qué reservé el mes
/// pasado?» --- y el servidor ya sabe contestarlas por separado. Partirlas aca
/// obligaria a traerse el historial entero para mostrar las dos vivas de
/// arriba.
final misReservasProvider = FutureProvider.family<PaginaReservas, bool>((
  ref,
  vivas,
) async {
  return ref.watch(repositorioReservasProvider).listar(vivas: vivas);
});

/// El detalle de una reserva propia, por identificador.
final reservaProvider = FutureProvider.family<Reserva, int>((
  ref,
  reservaId,
) async {
  return ref.watch(repositorioReservasProvider).obtener(reservaId);
});

/// La reserva que el cliente esta armando, antes de confirmarla.
final borradorProvider = NotifierProvider<ControlBorrador, BorradorReserva>(
  ControlBorrador.new,
);

// --- El borrador ----------------------------------------------------------

/// Una linea ya armada, con la prenda resuelta para poder mostrarla.
///
/// Guarda el nombre, la talla y el color ademas del identificador: la pantalla
/// tiene que poder listar «Blusa Aurora · M · Malva» sin volver a pedir la
/// ficha cada vez que se redibuja.
class LineaBorrador {
  const LineaBorrador({
    required this.varianteId,
    required this.cantidad,
    required this.sku,
    required this.producto,
    required this.talla,
    required this.color,
    this.rechazada = false,
  });

  final int varianteId;
  final int cantidad;
  final String sku;
  final String producto;
  final String talla;
  final String color;

  /// E1: el servidor rechazo esta prenda. Se marca en vez de invalidar la
  /// reserva entera, que es lo que pide la excepcion.
  final bool rechazada;

  LineaBorrador copiarCon({int? cantidad, bool? rechazada}) {
    return LineaBorrador(
      varianteId: varianteId,
      cantidad: cantidad ?? this.cantidad,
      sku: sku,
      producto: producto,
      talla: talla,
      color: color,
      rechazada: rechazada ?? this.rechazada,
    );
  }

  LineaReserva aLinea() =>
      LineaReserva(varianteId: varianteId, cantidad: cantidad);
}

/// Lo que el cliente lleva armado: las prendas, las sucursales que pueden
/// cumplir con todas, y cual eligio.
class BorradorReserva {
  const BorradorReserva({
    this.lineas = const [],
    this.sucursalesPosibles = const [],
    this.buscandoSucursales = false,
    this.sucursalId,
  });

  final List<LineaBorrador> lineas;

  /// Solo las sucursales que tienen **todas** las prendas en la cantidad
  /// pedida. Ver [ControlBorrador._recalcularSucursales].
  final List<DisponibilidadSucursal> sucursalesPosibles;

  final bool buscandoSucursales;
  final int? sucursalId;

  bool get vacio => lineas.isEmpty;

  int get unidades => lineas.fold(0, (suma, l) => suma + l.cantidad);

  /// El backend admite hasta diez lineas (`MAXIMO_LINEAS`). El tope existe
  /// porque cada linea aparta stock real.
  bool get lleno => lineas.length >= 10;

  /// Cuando ya se puede confirmar. La franja la valida la pantalla, que es
  /// quien la tiene.
  bool get hayPrendasYSucursal => lineas.isNotEmpty && sucursalId != null;

  BorradorReserva copiarCon({
    List<LineaBorrador>? lineas,
    List<DisponibilidadSucursal>? sucursalesPosibles,
    bool? buscandoSucursales,
    int? sucursalId,
    bool borrarSucursal = false,
  }) {
    return BorradorReserva(
      lineas: lineas ?? this.lineas,
      sucursalesPosibles: sucursalesPosibles ?? this.sucursalesPosibles,
      buscandoSucursales: buscandoSucursales ?? this.buscandoSucursales,
      sucursalId: borrarSucursal ? null : (sucursalId ?? this.sucursalId),
    );
  }
}

/// El armado de la reserva (CU-22, pasos 2 y 3).
///
/// **La sucursal se elige DESPUES de las prendas, y no antes.** Es el orden
/// contrario al que pide el cuerpo del `POST`, y es deliberado: la pregunta del
/// cliente es «¿dónde puedo probarme esto?», no «¿qué hay en la sucursal
/// Centro?». Eligiendo primero las prendas, el selector de sucursal puede
/// ofrecer solo las que tienen stock de todas ellas --- cruzando CU-19, que se
/// apoya en la costura C1 --- en vez de dejar armar una combinacion que el
/// servidor va a rechazar con un 409 despues de que el cliente ya eligio dia y
/// hora.
class ControlBorrador extends Notifier<BorradorReserva> {
  /// Cuantas veces se pidio recalcular. Sirve para descartar la respuesta de un
  /// recalculo viejo: agregar dos prendas seguidas lanza dos rondas de
  /// consultas, y la primera puede contestar despues de la segunda --- dejando
  /// en pantalla sucursales que no tienen la ultima prenda.
  int _generacion = 0;

  @override
  BorradorReserva build() => const BorradorReserva();

  /// Agrega una prenda ya elegida (talla y color) al borrador.
  ///
  /// Devuelve `null` si se agrego, o el motivo por el que no. No lanza: no es
  /// un fallo del sistema, es algo que el cliente tiene que leer y corregir.
  String? agregar({
    required FichaPrenda prenda,
    required VariantePrenda variante,
    required int cantidad,
  }) {
    if (cantidad < 1 || cantidad > 10) {
      return 'La cantidad tiene que estar entre 1 y 10 unidades.';
    }
    if (state.lleno) {
      return 'Una reserva admite hasta 10 prendas distintas.';
    }
    // Excepcion E7. Lo impide ademas el UNIQUE de la base y un validador de
    // Pydantic, pero avisarlo aca evita el viaje y explica que hacer.
    if (state.lineas.any((l) => l.varianteId == variante.id)) {
      return 'Esa prenda ya está en la reserva. Si quiere más de una unidad, '
          'suba la cantidad.';
    }

    state = state.copiarCon(
      lineas: [
        ...state.lineas,
        LineaBorrador(
          varianteId: variante.id,
          cantidad: cantidad,
          sku: variante.sku,
          producto: prenda.nombre,
          talla: variante.tallaCodigo ?? '',
          color: variante.colorNombre ?? '',
        ),
      ],
    );
    _recalcularSucursales();
    return null;
  }

  void quitar(int varianteId) {
    state = state.copiarCon(
      lineas: state.lineas.where((l) => l.varianteId != varianteId).toList(),
    );
    _recalcularSucursales();
  }

  /// Cambiar la cantidad tambien recalcula: una sucursal que tenia una unidad
  /// deja de servir cuando se piden dos.
  void cambiarCantidad(int varianteId, int cantidad) {
    if (cantidad < 1 || cantidad > 10) return;
    state = state.copiarCon(
      lineas: [
        for (final linea in state.lineas)
          linea.varianteId == varianteId
              ? linea.copiarCon(cantidad: cantidad, rechazada: false)
              : linea,
      ],
    );
    _recalcularSucursales();
  }

  void elegirSucursal(int? sucursalId) {
    state = sucursalId == null
        ? state.copiarCon(borrarSucursal: true)
        : state.copiarCon(sucursalId: sucursalId);
  }

  /// E1: marca las prendas que el servidor rechazo, para señalarlas.
  void marcarRechazadas(List<int> variantes) {
    state = state.copiarCon(
      lineas: [
        for (final linea in state.lineas)
          linea.copiarCon(rechazada: variantes.contains(linea.varianteId)),
      ],
    );
  }

  /// Se llama al confirmar con exito, y al abandonar la pantalla.
  void limpiar() {
    _generacion++; // que no vuelva un recalculo en vuelo y lo repueble
    state = const BorradorReserva();
  }

  /// Vuelve a preguntar la disponibilidad. Lo usa la pantalla cuando pierde la
  /// carrera por el stock (E9 / riesgo R5): el numero que mostraba ya no vale.
  void refrescarSucursales() => _recalcularSucursales();

  /// Deja en el selector solo las sucursales que tienen **todas** las prendas.
  ///
  /// Se cruza la disponibilidad de cada variante (CU-19) y se queda con la
  /// interseccion. Ofrecer una sucursal que tiene dos de las tres prendas seria
  /// dejar armar una reserva que el servidor rechaza con un 409, despues de que
  /// el cliente ya eligio dia y hora.
  Future<void> _recalcularSucursales() async {
    final generacion = ++_generacion;
    final lineas = state.lineas;

    if (lineas.isEmpty) {
      state = state.copiarCon(
        sucursalesPosibles: const [],
        buscandoSucursales: false,
        borrarSucursal: true,
      );
      return;
    }

    state = state.copiarCon(buscandoSucursales: true);

    final catalogo = ref.read(repositorioCatalogoProvider);
    final List<Disponibilidad> disponibilidades;
    try {
      disponibilidades = await Future.wait(
        lineas.map((l) => catalogo.obtenerDisponibilidad(l.varianteId)),
      );
    } catch (_) {
      // Sin disponibilidad no se puede afirmar que alguna sucursal sirva. Se
      // deja el selector vacio en vez de ofrecer una lista que quizas mienta;
      // la pantalla explica que no se pudo consultar.
      if (generacion == _generacion) {
        state = state.copiarCon(
          sucursalesPosibles: const [],
          buscandoSucursales: false,
          borrarSucursal: true,
        );
      }
      return;
    }

    // Llego tarde: ya hay otro recalculo mas nuevo en curso o terminado.
    if (generacion != _generacion) return;

    final porVariante = {for (final d in disponibilidades) d.varianteId: d};
    List<DisponibilidadSucursal>? candidatas;

    for (final linea in lineas) {
      final sucursales =
          (porVariante[linea.varianteId]?.sucursales ?? const [])
              .where((s) => s.cantidadDisponible >= linea.cantidad)
              .toList();
      candidatas = candidatas == null
          ? sucursales
          : candidatas
                .where(
                  (c) => sucursales.any((s) => s.sucursalId == c.sucursalId),
                )
                .toList();
    }

    final posibles = candidatas ?? const <DisponibilidadSucursal>[];

    // Si la sucursal elegida dejo de servir --- porque se agrego otra prenda
    // que ahi no hay ---, se deselecciona en vez de quedar mostrando algo
    // invalido que el servidor va a rechazar.
    final elegida = state.sucursalId;
    final sigueSirviendo =
        elegida != null && posibles.any((s) => s.sucursalId == elegida);

    state = state.copiarCon(
      sucursalesPosibles: posibles,
      buscandoSucursales: false,
      borrarSucursal: !sigueSirviendo,
    );
  }
}
