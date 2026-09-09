/// Estado del perfil del cliente (CU-04).
///
/// El perfil se pide al servidor cada vez que se abre la pantalla y no se
/// guarda en el dispositivo: es un dato que el propio usuario puede haber
/// cambiado desde la web, y mostrarlo desactualizado sería peor que esperar.
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/modelos/perfil.dart';
import '../../data/repositorios/repositorio_perfil.dart';
import '../auth/estado_sesion.dart';

final repositorioPerfilProvider = Provider<RepositorioPerfil>((ref) {
  return RepositorioPerfil(ref.watch(clienteApiProvider));
});

final perfilProvider = AsyncNotifierProvider<ControlPerfil, Perfil>(
  ControlPerfil.new,
);

/// Ciudades para el selector del formulario de direcciones.
///
/// Van aparte del perfil porque cambian mucho menos: se piden una sola vez
/// mientras la pantalla esté viva, en vez de en cada recarga del perfil.
final ciudadesProvider = FutureProvider<List<Ciudad>>((ref) {
  return ref.watch(repositorioPerfilProvider).ciudades();
});

class ControlPerfil extends AsyncNotifier<Perfil> {
  @override
  Future<Perfil> build() => ref.read(repositorioPerfilProvider).obtener();

  RepositorioPerfil get _repositorio => ref.read(repositorioPerfilProvider);

  /// Paso 3 · guarda datos personales y tallas habituales.
  ///
  /// Propaga [ErrorApi] para que el formulario muestre el mensaje junto al
  /// botón, igual que hace el login. El estado solo se toca si salió bien.
  Future<void> editar(EdicionPerfil datos) async {
    final actualizado = await _repositorio.editar(datos);
    state = AsyncData(actualizado);

    // El nombre y el correo también viven en la sesión, que es lo que muestra
    // la pantalla de inicio. Sin esto, cambiar el nombre en el perfil deja el
    // saludo viejo hasta la próxima vez que se abra la app.
    await ref.read(sesionProvider.notifier).restaurar();
  }

  /// Flujo alternativo 3a · agrega una dirección de entrega.
  ///
  /// El endpoint responde 201 sin cuerpo, así que hay que volver a pedir el
  /// perfil para ver la lista con la dirección nueva y su identificador.
  Future<void> agregarDireccion(NuevaDireccion datos) async {
    await _repositorio.agregarDireccion(datos);
    await _recargar();
  }

  Future<void> marcarPredeterminada(int direccionId) async {
    await _repositorio.marcarPredeterminada(direccionId);
    await _recargar();
  }

  Future<void> eliminarDireccion(int direccionId) async {
    await _repositorio.eliminarDireccion(direccionId);
    await _recargar();
  }

  /// Flujo alternativo 3c · cambio de contraseña.
  ///
  /// No toca el estado: la contraseña no forma parte del perfil que se muestra.
  /// Y no cierra la sesión, porque el backend no revoca el token al cambiarla.
  Future<void> cambiarContrasena(CambioContrasena datos) {
    return _repositorio.cambiarContrasena(datos);
  }

  /// Vuelve a pedir el perfil dejando a la vista los datos viejos mientras
  /// llega el nuevo, en vez de vaciar la pantalla y hacerla saltar.
  Future<void> _recargar() async {
    state = await AsyncValue.guard(_repositorio.obtener);
  }
}
