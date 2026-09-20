/// Estado de las pantallas de gestión: tablero (CU-36) y bitácora (CU-42),
/// más el catálogo de reportes (CU-37).
///
/// Los tres son **lecturas**: nadie las muta desde la pantalla, así que van
/// como `FutureProvider` y no como `Notifier`. Refrescar es invalidar.
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/modelos/gestion.dart';
import '../../data/repositorios/repositorio_gestion.dart';
import '../../data/repositorios/repositorio_reportes.dart';
import '../auth/estado_sesion.dart';

final repositorioGestionProvider = Provider<RepositorioGestion>((ref) {
  return RepositorioGestion(ref.watch(clienteApiProvider));
});

final repositorioReportesProvider = Provider<RepositorioReportes>((ref) {
  return RepositorioReportes(ref.watch(clienteApiProvider));
});

/// CU-36 · el tablero, con el período por omisión del servidor.
final tableroProvider = FutureProvider<Tablero>((ref) async {
  return ref.watch(repositorioGestionProvider).tablero();
});

/// CU-37 · qué reportes hay. La pantalla no los conoce por nombre.
final catalogoDeReportesProvider = FutureProvider<List<ReporteDisponible>>((
  ref,
) async {
  return ref.watch(repositorioReportesProvider).catalogo();
});

/// CU-42 · el filtro puesto en la pantalla de bitácora.
///
/// Un registro simple en vez de tres providers sueltos: los tres cambian
/// juntos al tocar «Aplicar» y separarlos dispararía tres consultas donde
/// hace falta una.
typedef FiltroBitacora = ({
  String? rol,
  String? accion,
  bool? exito,
  String? busqueda,
});

const FiltroBitacora sinFiltro = (
  rol: null,
  accion: null,
  exito: null,
  busqueda: null,
);

/// `Notifier` y no `StateProvider`: Riverpod 3 retiro el segundo.
class ControlFiltroBitacora extends Notifier<FiltroBitacora> {
  @override
  FiltroBitacora build() => sinFiltro;

  void poner(FiltroBitacora filtro) => state = filtro;

  void limpiar() => state = sinFiltro;
}

final filtroBitacoraProvider =
    NotifierProvider<ControlFiltroBitacora, FiltroBitacora>(
      ControlFiltroBitacora.new,
    );

final bitacoraProvider = FutureProvider<PaginaBitacora>((ref) async {
  final f = ref.watch(filtroBitacoraProvider);
  return ref
      .watch(repositorioGestionProvider)
      .bitacora(
        rol: f.rol,
        accion: f.accion,
        exito: f.exito,
        busqueda: f.busqueda,
      );
});

/// Las acciones y los roles registrados, para armar los desplegables con lo
/// que hay de verdad y no con una lista escrita acá que se desactualiza en
/// silencio.
final opcionesDeBitacoraProvider =
    FutureProvider<({List<String> acciones, List<String> roles})>((ref) async {
      return ref.watch(repositorioGestionProvider).opcionesDeBitacora();
    });
