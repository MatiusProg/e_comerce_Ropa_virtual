/// Aporte propio · «Avísame cuando llegue mi talla» --- estado.
///
/// Mismo patrón que los favoritos: el conjunto de variantes esperadas se pide
/// una vez y la ficha lo consulta para saber qué botón mostrar.
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/repositorios/repositorio_avisos_talla.dart';
import '../auth/estado_sesion.dart';

final repositorioAvisosTallaProvider = Provider<RepositorioAvisosTalla>((ref) {
  return RepositorioAvisosTalla(ref.watch(clienteApiProvider));
});

final avisosTallaProvider =
    AsyncNotifierProvider<ControlAvisosTalla, Set<int>>(ControlAvisosTalla.new);

class ControlAvisosTalla extends AsyncNotifier<Set<int>> {
  @override
  Future<Set<int>> build() async {
    final sesion = ref.watch(sesionProvider);
    if (sesion is! SesionAbierta || !sesion.usuario.esCliente) return <int>{};
    return ref.read(repositorioAvisosTallaProvider).esperadas();
  }

  /// Pide el aviso y, si sale bien, suma la variante al conjunto.
  Future<void> pedir(int varianteId) async {
    await ref.read(repositorioAvisosTallaProvider).pedir(varianteId);
    state = AsyncData({...?state.value, varianteId});
  }
}
