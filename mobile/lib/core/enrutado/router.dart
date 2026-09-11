/// Enrutado y guarda de sesion.
///
/// Es el equivalente movil de `app.routes.ts` y de `auth.guard.ts` de la web:
/// las rutas y la proteccion viven juntas, porque en `go_router` la guarda es
/// una redireccion declarada sobre el propio enrutador.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/estado_sesion.dart';
import '../../features/auth/pantalla_login.dart';
import '../../features/auth/pantalla_registro.dart';
import '../../features/catalogo/pantalla_catalogo.dart';
import '../../features/catalogo/pantalla_ficha.dart';
import '../../features/inicio/pantalla_carga.dart';
import '../../features/inicio/pantalla_inicio.dart';
import '../../features/perfil/pantalla_perfil.dart';

/// Rutas de la aplicacion. Constantes y no cadenas sueltas: un error de tipeo
/// en un `context.go('/lgin')` no lo detecta nadie hasta que se ejecuta.
class Rutas {
  const Rutas._();

  static const String cargando = '/cargando';
  static const String login = '/login';
  static const String registro = '/registro';
  static const String inicio = '/inicio';
  static const String perfil = '/perfil';

  // --- CICLO 2 ------------------------------------------------------------
  // Karen agrega aqui las rutas de catalogo (CU-17, CU-18, CU-19).
  // Mateo agrega aqui las rutas de reservas (CU-22, CU-23).
  // Cada uno agrega al final de su bloque y no reordena las ajenas; ver
  // docs/entregas/ciclo-2/00-organizacion-por-caso-de-uso.md, seccion 5.

  // Karen:
  /// CU-17 · la vitrina.
  static const String catalogo = '/catalogo';

  /// CU-18 · la ficha. Se navega como `/catalogo/5`; el identificador va en
  /// la ruta y no como parametro de consulta para que la pantalla sea
  /// enlazable y el boton de volver del telefono la deje bien apilada.
  static const String fichaProducto = '/catalogo/:id';
}

/// Rutas accesibles sin sesion: el registro (CU-01) y el login (CU-02).
const Set<String> _rutasPublicas = {Rutas.login, Rutas.registro};

final routerProvider = Provider<GoRouter>((ref) {
  // `go_router` no conoce Riverpod: se le pasa un `Listenable` que se dispara
  // cuando cambia la sesion, y el vuelve a evaluar la redireccion.
  final cambioDeSesion = ValueNotifier<EstadoSesion>(ref.read(sesionProvider));
  ref.listen<EstadoSesion>(
    sesionProvider,
    (_, nuevo) => cambioDeSesion.value = nuevo,
  );
  ref.onDispose(cambioDeSesion.dispose);

  return GoRouter(
    initialLocation: Rutas.cargando,
    refreshListenable: cambioDeSesion,
    redirect: (context, estadoRuta) {
      final sesion = ref.read(sesionProvider);
      final destino = estadoRuta.matchedLocation;

      return switch (sesion) {
        // Todavia se esta comprobando el token guardado: nadie pasa, se
        // muestra la pantalla de carga. Sin esto, la app parpadearia en el
        // login durante el arranque aunque la sesion fuera valida.
        SesionComprobando() =>
          destino == Rutas.cargando ? null : Rutas.cargando,

        // Sin sesion: solo login y registro.
        SesionCerrada() => _rutasPublicas.contains(destino) ? null : Rutas.login,

        // Con sesion: no tiene sentido volver al login ni a la carga.
        SesionAbierta() =>
          _rutasPublicas.contains(destino) || destino == Rutas.cargando
              ? Rutas.inicio
              : null,
      };
    },
    routes: [
      GoRoute(
        path: Rutas.cargando,
        builder: (context, estado) => const PantallaCarga(),
      ),
      GoRoute(
        path: Rutas.login,
        builder: (context, estado) => const PantallaLogin(),
      ),
      GoRoute(
        path: Rutas.registro,
        builder: (context, estado) => const PantallaRegistro(),
      ),
      GoRoute(
        path: Rutas.inicio,
        builder: (context, estado) => const PantallaInicio(),
      ),
      GoRoute(
        path: Rutas.perfil,
        builder: (context, estado) => const PantallaPerfil(),
      ),

      // --- CICLO 2 --------------------------------------------------------
      // Karen: catalogo (CU-17, CU-18, CU-19).
      // Mateo: reservas (CU-22, CU-23).
      GoRoute(
        path: Rutas.catalogo,
        builder: (context, estado) => const PantallaCatalogo(),
        routes: [
          GoRoute(
            // Anidada y no suelta: asi el boton de volver del telefono lleva de
            // la ficha a la vitrina y no a la pantalla de inicio.
            path: ':id',
            builder: (context, estado) {
              // El identificador llega como texto desde la URL. Si no es un
              // entero se manda a la vitrina en vez de reventar al construir:
              // la ruta la puede escribir cualquiera.
              final id = int.tryParse(estado.pathParameters['id'] ?? '');
              if (id == null) return const PantallaCatalogo();
              return PantallaFicha(productoId: id);
            },
          ),
        ],
      ),
    ],
    errorBuilder: (context, estado) => Scaffold(
      appBar: AppBar(title: const Text('Página no encontrada')),
      body: Center(child: Text('No existe la ruta ${estado.uri}')),
    ),
  );
});
