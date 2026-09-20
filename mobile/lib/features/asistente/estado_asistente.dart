/// CU-34 · La conversación, viva mientras la aplicación esté abierta.
///
/// POR QUÉ NO VIVE EN LA PANTALLA
/// --------------------------------
/// Estaba en el estado del widget, y eso la borraba al salir: entrar al
/// catálogo a mirar una prenda que el asistente acababa de nombrar y volver
/// dejaba la conversación en blanco. Justo el recorrido más natural —
/// preguntar, mirar, repreguntar— era el que la perdía.
///
/// Subida a un `Notifier` sobrevive a la navegación, que es lo único que
/// hacía falta.
///
/// **Y SIGUE SIN TOCAR LA BASE.** Vive en memoria y nada más: al cerrar la
/// aplicación se pierde, a propósito. Una tabla de conversaciones crecería
/// sin límite con texto libre de un modelo, y abriría la pregunta de cuánto
/// se guarda y quién lo puede leer — en el caso de uso que más cerca está de
/// los datos personales. Ver `asistente_service.py`.
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/repositorios/repositorio_asistente.dart';
import '../auth/estado_sesion.dart';

final repositorioAsistenteProvider = Provider<RepositorioAsistente>((ref) {
  return RepositorioAsistente(ref.watch(clienteApiProvider));
});

final asistenteDisponibleProvider =
    FutureProvider<({bool disponible, List<String> ejemplos})>((ref) async {
      return ref.watch(repositorioAsistenteProvider).disponible();
    });

/// Los turnos de la conversación en curso.
class ControlConversacion extends Notifier<List<Turno>> {
  @override
  List<Turno> build() {
    // Al cerrar sesión la conversación se va con ella: habla de «tus
    // pedidos», y dejarla visible para quien entre después sería mostrarle
    // datos de otra persona.
    ref.listen(sesionProvider, (_, nuevo) {
      if (nuevo is! SesionAbierta) state = const [];
    });
    return const [];
  }

  void agregar(Turno turno) => state = [...state, turno];

  void limpiar() => state = const [];
}

final conversacionProvider =
    NotifierProvider<ControlConversacion, List<Turno>>(
      ControlConversacion.new,
    );
