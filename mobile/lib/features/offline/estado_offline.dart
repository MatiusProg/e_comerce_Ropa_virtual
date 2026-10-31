/// Estado del trabajo sin conexion del cliente (2do parcial).
///
/// CU-13 Preparar el dispositivo · CU-15 Registrar reserva offline ·
/// CU-17 Sincronizar · CU-18 Consultar pendientes.
///
/// LA REGLA QUE SOSTIENE TODO (RNF06)
/// ----------------------------------
/// Una operacion sale de la cola solo cuando el servidor la confirma o la
/// rechaza. Si se manda y la respuesta se pierde, queda `enviada` y se vuelve
/// a mandar: el UUID hace que el servidor no la registre dos veces.
library;

import 'dart:async';
import 'dart:math';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/almacenamiento/base_local.dart';
import '../../core/red/excepciones.dart';
import '../../data/modelos/offline.dart';
import '../../data/modelos/reservas.dart';
import '../../data/repositorios/repositorio_offline.dart';
import '../auth/estado_sesion.dart';
import '../reservas/estado_reservas.dart';

/// Igual que `MAXIMO_POR_LOTE` del backend.
const _porLote = 50;
const _reintento = Duration(minutes: 1);

final repositorioOfflineProvider = Provider<RepositorioOffline>((ref) {
  return RepositorioOffline(ref.watch(clienteApiProvider));
});

final offlineProvider = NotifierProvider<ControlOffline, EstadoOffline>(
  ControlOffline.new,
);

class EstadoOffline {
  const EstadoOffline({
    this.paquete,
    this.operaciones = const [],
    this.sincronizando = false,
    this.enLinea = true,
    this.cargado = false,
  });

  final PaqueteCliente? paquete;
  final List<OperacionGuardada> operaciones;
  final bool sincronizando;
  final bool enLinea;
  final bool cargado;

  List<OperacionGuardada> get pendientes =>
      operaciones.where((o) => o.estado.pendiente).toList();

  EstadoOffline copiarCon({
    PaqueteCliente? paquete,
    List<OperacionGuardada>? operaciones,
    bool? sincronizando,
    bool? enLinea,
    bool? cargado,
  }) =>
      EstadoOffline(
        paquete: paquete ?? this.paquete,
        operaciones: operaciones ?? this.operaciones,
        sincronizando: sincronizando ?? this.sincronizando,
        enLinea: enLinea ?? this.enLinea,
        cargado: cargado ?? this.cargado,
      );
}

class ControlOffline extends Notifier<EstadoOffline> {
  final _base = BaseLocal.instancia;
  Timer? _reloj;

  RepositorioOffline get _repo => ref.read(repositorioOfflineProvider);

  @override
  EstadoOffline build() {
    _reloj = Timer.periodic(_reintento, (_) => _alReloj());
    ref.onDispose(() => _reloj?.cancel());
    Future.microtask(_cargar);
    return const EstadoOffline();
  }

  Future<void> _cargar() async {
    state = state.copiarCon(
      paquete: await _base.leerPaquete(),
      operaciones: await _base.operaciones(),
      cargado: true,
    );
  }

  Future<void> _alReloj() async {
    if (state.pendientes.isNotEmpty) {
      await sincronizar();
    } else if (!state.enLinea) {
      state = state.copiarCon(enLinea: await _repo.hayConexion());
    }
  }

  /// Lo marca una pantalla cuando una peticion se queda sin respuesta.
  void marcarSinRed() => state = state.copiarCon(enLinea: false);

  // --- CU-13 ---------------------------------------------------------------

  /// Descarga y guarda el paquete. Lanza [SinRespuesta] o [ErrorApi].
  Future<PaqueteCliente> preparar() async {
    final paquete = await _repo.descargarPaquete();
    await _base.guardarPaquete(paquete);
    // Lo apartado sin red y todavia no confirmado ya no esta disponible.
    for (final op in state.pendientes) {
      await _base.descontar(
        op.cuerpo['sucursal_id'] as int,
        _cantidades(op.cuerpo),
      );
    }
    final guardado = await _base.leerPaquete();
    state = state.copiarCon(paquete: guardado, enLinea: true);
    return guardado!;
  }

  // --- CU-15 ---------------------------------------------------------------

  /// Guarda la reserva en el telefono. **No la confirma**: la confirma el
  /// servidor al sincronizar, con las mismas reglas que la reserva en linea.
  Future<OperacionGuardada> reservar({
    required SucursalOffline sucursal,
    required Map<PrendaOffline, int> prendas,
    required DateTime inicio,
    required DateTime fin,
  }) async {
    final uuid = _uuidV4();
    final op = OperacionGuardada(
      uuid: uuid,
      estado: EstadoOperacion.local,
      creadaEn: DateTime.now(),
      resumen: '${sucursal.nombre}: '
          '${prendas.entries.map((e) => '${e.value}× ${e.key.nombre}').join(', ')}',
      cuerpo: {
        'uuid': uuid,
        'tipo': 'RESERVA',
        'creada_en': conDesfase(DateTime.now()),
        'sucursal_id': sucursal.id,
        'franja_inicio': conDesfase(inicio),
        'franja_fin': conDesfase(fin),
        'lineas': [
          for (final e in prendas.entries)
            {
              'variante_id': e.key.varianteId,
              'cantidad': e.value,
              'precio_unitario': e.key.precio,
            },
        ],
      },
    );
    // Primero la operacion y despues el saldo: si la app se cierra en el
    // medio, lo peor es un saldo de mas, que el servidor corrige.
    await _base.guardarOperacion(op);
    await _base.descontar(sucursal.id, _cantidades(op.cuerpo));
    state = state.copiarCon(
      operaciones: await _base.operaciones(),
      paquete: await _base.leerPaquete(),
    );
    unawaited(sincronizar());
    return op;
  }

  // --- CU-17 ---------------------------------------------------------------

  /// Manda la cola por lotes. Nunca lanza: lo que no se pudo, queda.
  Future<({int confirmadas, int rechazadas})?> sincronizar() async {
    if (state.sincronizando) return null;
    final cola = state.pendientes;
    if (cola.isEmpty) return (confirmadas: 0, rechazadas: 0);

    state = state.copiarCon(sincronizando: true);
    final cuenta = _Cuenta();
    try {
      for (var i = 0; i < cola.length; i += _porLote) {
        final lote = cola.sublist(i, min(i + _porLote, cola.length));
        if (!await _enviar(lote, cuenta)) break;
      }
    } finally {
      state = state.copiarCon(
        sincronizando: false,
        operaciones: await _base.operaciones(),
      );
    }
    if (cuenta.confirmadas > 0) ref.invalidate(misReservasProvider);
    return (confirmadas: cuenta.confirmadas, rechazadas: cuenta.rechazadas);
  }

  /// `false` = parar (sin red); `true` = seguir con el proximo lote.
  Future<bool> _enviar(List<OperacionGuardada> lote, _Cuenta cuenta) async {
    for (final op in lote) {
      await _base.guardarOperacion(
        op.copiarCon(
            estado: EstadoOperacion.enviada, intentos: op.intentos + 1),
      );
    }
    try {
      final resultados =
          await _repo.sincronizar([for (final o in lote) o.cuerpo]);
      state = state.copiarCon(enLinea: true);
      final porUuid = {for (final o in lote) o.uuid: o};
      for (final r in resultados) {
        final op = porUuid[r.uuid];
        if (op == null) continue;
        await _base.guardarOperacion(
          op.copiarCon(
            estado: r.confirmada
                ? EstadoOperacion.confirmada
                : EstadoOperacion.rechazada,
            intentos: op.intentos + 1,
            motivo: r.motivo,
            reservaId: r.reservaId,
          ),
        );
        r.confirmada ? cuenta.confirmadas++ : cuenta.rechazadas++;
      }
      return true;
    } on SinRespuesta {
      state = state.copiarCon(enLinea: false);
      return false;
    } on ErrorApi catch (error) {
      if (error.esNoAutorizado || (error.codigo ?? 500) >= 500) return false;
      // El servidor no acepto el lote: una sola mal formada lo tumba. Se
      // reintentan de a una y solo la culpable queda en conflicto.
      if (lote.length > 1) {
        for (final op in lote) {
          if (!await _enviar([op], cuenta)) return false;
        }
        return true;
      }
      await _base.guardarOperacion(
        lote.first.copiarCon(
          estado: EstadoOperacion.enConflicto,
          intentos: lote.first.intentos + 1,
          motivo: error.mensaje,
        ),
      );
      return true;
    }
  }

  /// Saca de la vista las ya decididas por el servidor.
  Future<void> limpiarDecididas() async {
    await _base.borrarDecididas();
    state = state.copiarCon(operaciones: await _base.operaciones());
  }

  Map<int, int> _cantidades(Map<String, dynamic> cuerpo) => {
        for (final l in (cuerpo['lineas'] as List).cast<Map<String, dynamic>>())
          l['variante_id'] as int: l['cantidad'] as int,
      };
}

class _Cuenta {
  int confirmadas = 0;
  int rechazadas = 0;
}

/// UUID v4 con el generador criptografico del sistema. Es la llave de la
/// idempotencia (RNF05): lo crea el telefono, no el servidor.
String _uuidV4() {
  final r = Random.secure();
  final b = List<int>.generate(16, (_) => r.nextInt(256));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  final h = b.map((x) => x.toRadixString(16).padLeft(2, '0')).join();
  return '${h.substring(0, 8)}-${h.substring(8, 12)}-${h.substring(12, 16)}-'
      '${h.substring(16, 20)}-${h.substring(20)}';
}
