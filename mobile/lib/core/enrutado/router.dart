import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../data/modelos/usuario_autenticado.dart';
import '../../features/auth/estado/sesion.dart';
import '../../features/auth/pantallas/login_pantalla.dart';
import '../../features/auth/pantallas/registro_pantalla.dart';
import '../../features/inicio/arranque_pantalla.dart';
import '../../features/inicio/inicio_pantalla.dart';

/// Rutas de la app.
///
/// **Protocolo de trabajo del Ciclo 2** (§5 y §6 de la organizacion del ciclo):
/// cada uno agrega su bloque de rutas *al final de su propia seccion* y nunca
/// reordena las ajenas. Asi las dos personas tocan este archivo sin que git
/// tenga que decidir nada.
class Rutas {
  const Rutas._();

  static const String arranque = '/';
  static const String login = '/login';
  static const String registro = '/registro';
  static const String inicio = '/inicio';

  /// Rutas a las que se puede entrar sin sesion.
  static const Set<String> publicas = {arranque, login, registro};
}

final routerProvider = Provider<GoRouter>((ref) {
  final refresco = _RefrescoDeRuta();
  ref.listen<AsyncValue<UsuarioAutenticado?>>(
    sesionProvider,
    (_, __) => refresco.refrescar(),
  );
  ref.onDispose(refresco.dispose);

  return GoRouter(
    initialLocation: Rutas.arranque,
    refreshListenable: refresco,
    redirect: (context, state) {
      final sesion = ref.read(sesionProvider);
      final destino = state.matchedLocation;

      // Todavia no se sabe si hay sesion: se espera en la pantalla de arranque
      // en lugar de adivinar y hacer parpadear el login.
      if (sesion.isLoading) {
        return destino == Rutas.arranque ? null : Rutas.arranque;
      }

      final autenticado = sesion.value != null;

      if (!autenticado) {
        return Rutas.publicas.contains(destino) && destino != Rutas.arranque
            ? null
            : Rutas.login;
      }

      // Con sesion abierta, las pantallas de entrada no tienen sentido.
      return Rutas.publicas.contains(destino) ? Rutas.inicio : null;
    },
    routes: [
      GoRoute(
        path: Rutas.arranque,
        builder: (context, state) => const ArranquePantalla(),
      ),

      // --- Seguridad y perfil · CU-01, CU-02, CU-04 -----------------------
      GoRoute(
        path: Rutas.login,
        builder: (context, state) => LoginPantalla(
          correoSugerido: state.uri.queryParameters['correo'],
        ),
      ),
      GoRoute(
        path: Rutas.registro,
        builder: (context, state) => const RegistroPantalla(),
      ),
      GoRoute(
        path: Rutas.inicio,
        builder: (context, state) => const InicioPantalla(),
      ),
      // CU-04 perfil del cliente: se agrega aca.

      // --- Catalogo y vitrina · Karen · CU-17, CU-18, CU-19 ---------------
      // Agregar debajo de esta linea, sin tocar lo de arriba.

      // --- Reservas · Mateo · CU-22, CU-23 --------------------------------
      // Agregar debajo de esta linea, sin tocar lo de arriba.
    ],
    errorBuilder: (context, state) => Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            'No existe la pantalla ${state.uri}',
            textAlign: TextAlign.center,
          ),
        ),
      ),
    ),
  );
});

/// Le avisa a `go_router` que vuelva a evaluar el `redirect` cuando la sesion
/// cambia. Sin esto, cerrar sesion dejaria al usuario mirando una pantalla
/// privada hasta que navegara a mano.
class _RefrescoDeRuta extends ChangeNotifier {
  void refrescar() => notifyListeners();
}
