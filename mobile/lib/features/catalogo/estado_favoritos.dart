/// CU-20 · Estado de los favoritos del cliente.
///
/// Sigue el patron de `estado_catalogo.dart`: los proveedores arriba, el
/// control abajo. Ninguna pantalla construye un repositorio.
///
/// POR QUE EL CONJUNTO DE IDENTIFICADORES VIVE APARTE DE LA LISTA
/// ---------------------------------------------------------------
/// Son dos cosas con vidas distintas. El CONJUNTO lo necesita el catalogo en
/// cada tarjeta, se pide una vez al entrar y cabe en memoria; la LISTA con las
/// fotos solo la necesita la pantalla de favoritos, y pedirla para pintar un
/// corazon seria traer medio catalogo otra vez.
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/modelos/catalogo.dart';
import '../../data/repositorios/repositorio_favoritos.dart';
import '../auth/estado_sesion.dart';

// --- Proveedores ----------------------------------------------------------

final repositorioFavoritosProvider = Provider<RepositorioFavoritos>((ref) {
  return RepositorioFavoritos(ref.watch(clienteApiProvider));
});

/// Los identificadores de las prendas favoritas del cliente.
final favoritosProvider =
    AsyncNotifierProvider<ControlFavoritos, Set<int>>(ControlFavoritos.new);

/// La lista completa, con sus tarjetas. Solo la mira la pantalla de favoritos.
final listaFavoritosProvider = FutureProvider.autoDispose<PaginaVitrina>((
  ref,
) async {
  // Depende del conjunto: al quitar una prenda desde la propia pantalla, el
  // conjunto cambia y esta lista se vuelve a pedir sola. Sin esta linea habria
  // que acordarse de invalidarla a mano en cada sitio que marque o desmarque.
  ref.watch(favoritosProvider);
  return ref.watch(repositorioFavoritosProvider).listar();
});

// --- Control ---------------------------------------------------------------

class ControlFavoritos extends AsyncNotifier<Set<int>> {
  @override
  Future<Set<int>> build() async {
    // Sin sesion no hay favoritos, y pedirlos daria 401. Devolver el conjunto
    // vacio deja que el catalogo se dibuje igual, con todos los corazones
    // apagados, en vez de fallar entero por una comodidad.
    //
    // Se OBSERVA la sesion, no se lee: al iniciar sesion desde el catalogo,
    // esto se reconstruye solo y los corazones aparecen sin recargar nada.
    if (ref.watch(sesionProvider) is! SesionAbierta) return <int>{};
    return ref.read(repositorioFavoritosProvider).ids();
  }

  bool esFavorito(int productoId) => state.value?.contains(productoId) ?? false;

  /// Marca o desmarca, y **se adelanta al servidor**.
  ///
  /// El corazon cambia en el momento y la peticion viaja despues. Si falla, se
  /// vuelve atras y se propaga el error para que la pantalla avise.
  ///
  /// POR QUE ADELANTARSE Y NO ESPERAR
  /// ---------------------------------
  /// Marcar un favorito es un gesto que se hace mientras se recorre el
  /// catalogo, muchas veces seguidas. Con la espera de la red en el medio, el
  /// corazon tarda medio segundo en pintarse y el cliente vuelve a tocarlo
  /// creyendo que no registro --- con lo que lo desmarca ---. Es peor que el
  /// riesgo de mostrar por un instante algo que no se guardo.
  Future<void> alternar(int productoId) async {
    final actuales = state.value ?? <int>{};
    final estaba = actuales.contains(productoId);

    final optimista = Set<int>.from(actuales);
    if (estaba) {
      optimista.remove(productoId);
    } else {
      optimista.add(productoId);
    }
    state = AsyncData(optimista);

    try {
      final repo = ref.read(repositorioFavoritosProvider);
      if (estaba) {
        await repo.desmarcar(productoId);
      } else {
        await repo.marcar(productoId);
      }
    } catch (_) {
      // Se vuelve al conjunto de antes, no se recarga del servidor: recargar
      // pisaria cualquier otro cambio que el cliente haya hecho mientras esta
      // peticion viajaba.
      state = AsyncData(actuales);
      rethrow;
    }
  }
}
