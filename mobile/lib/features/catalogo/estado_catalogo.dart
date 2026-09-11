/// Estado del catalogo publico (CU-17 y CU-18).
///
/// Sigue el patron de `estado_sesion.dart`: los proveedores arriba, el control
/// abajo. Ninguna pantalla construye un repositorio ni guarda resultados en un
/// `State`; el estado vive aca y las pantallas lo observan.
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/modelos/catalogo.dart';
import '../../data/repositorios/repositorio_catalogo.dart';
import '../auth/estado_sesion.dart';

// --- Proveedores ----------------------------------------------------------

final repositorioCatalogoProvider = Provider<RepositorioCatalogo>((ref) {
  return RepositorioCatalogo(ref.watch(clienteApiProvider));
});

/// Los criterios de la vitrina. Cambiarlos es lo que dispara la consulta.
final consultaProvider = NotifierProvider<ControlConsulta, ConsultaVitrina>(
  ControlConsulta.new,
);

/// La pagina de la vitrina que corresponde a los criterios vigentes.
///
/// Depende de `consultaProvider`, asi que cambiar un filtro la recalcula sola:
/// no hay que acordarse de volver a llamar a nada desde la pantalla.
final vitrinaProvider = FutureProvider<PaginaVitrina>((ref) async {
  final consulta = ref.watch(consultaProvider);
  return ref.watch(repositorioCatalogoProvider).listar(consulta);
});

/// Las opciones del panel de filtros.
///
/// `keepAlive`: son cinco listas cortas que cambian cuando el Administrador
/// toca el catalogo, no mientras el cliente navega. Sin esto se volverian a
/// pedir cada vez que se abre el panel.
final filtrosProvider = FutureProvider<FiltrosDisponibles>((ref) async {
  ref.keepAlive();
  return ref.watch(repositorioCatalogoProvider).obtenerFiltros();
});

/// La ficha de una prenda (CU-18), por identificador.
final fichaProvider = FutureProvider.family<FichaPrenda, int>((
  ref,
  productoId,
) async {
  return ref.watch(repositorioCatalogoProvider).obtenerFicha(productoId);
});

/// CU-19 · la disponibilidad de una variante.
///
/// Por variante y no por producto: se pide cuando el cliente termina de elegir
/// talla y color. Pedirla al abrir la ficha serian tantas consultas como
/// variantes tenga la prenda, de las que mira una.
final disponibilidadProvider = FutureProvider.family<Disponibilidad, int>((
  ref,
  varianteId,
) async {
  return ref.watch(repositorioCatalogoProvider).obtenerDisponibilidad(varianteId);
});

// --- Control --------------------------------------------------------------

class ControlConsulta extends Notifier<ConsultaVitrina> {
  @override
  ConsultaVitrina build() => const ConsultaVitrina();

  /// Cualquier cambio de criterio vuelve a la primera pagina.
  ///
  /// Sin esto, filtrar estando en la pagina 4 deja una vitrina vacia que parece
  /// un error, cuando lo que pasa es que el resultado filtrado no llega hasta
  /// esa pagina.
  void buscar(String texto) {
    final limpio = texto.trim();
    state = limpio.isEmpty
        ? state.copiarCon(borrarBusqueda: true, pagina: 1)
        : state.copiarCon(busqueda: limpio, pagina: 1);
  }

  void filtrarPorCategoria(int? categoriaId) {
    state = categoriaId == null
        ? state.copiarCon(borrarCategoria: true, pagina: 1)
        : state.copiarCon(categoriaId: categoriaId, pagina: 1);
  }

  void filtrarPorTalla(int? tallaId) {
    state = tallaId == null
        ? state.copiarCon(borrarTalla: true, pagina: 1)
        : state.copiarCon(tallaId: tallaId, pagina: 1);
  }

  void filtrarPorColor(int? colorId) {
    state = colorId == null
        ? state.copiarCon(borrarColor: true, pagina: 1)
        : state.copiarCon(colorId: colorId, pagina: 1);
  }

  void filtrarPorTemporada(int? temporadaId) {
    state = temporadaId == null
        ? state.copiarCon(borrarTemporada: true, pagina: 1)
        : state.copiarCon(temporadaId: temporadaId, pagina: 1);
  }

  void ordenarPor(String orden) {
    state = state.copiarCon(orden: orden, pagina: 1);
  }

  void irAPagina(int pagina) {
    state = state.copiarCon(pagina: pagina);
  }

  void limpiar() {
    // Se reemplaza el estado entero en vez de borrar campo por campo: es una
    // sola notificacion a Riverpod y por lo tanto una sola consulta.
    state = ConsultaVitrina(orden: state.orden);
  }
}
