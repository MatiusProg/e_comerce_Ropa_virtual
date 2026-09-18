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
import '../../data/modelos/compra.dart';
import '../../features/compra/pantalla_carrito.dart';
import '../../features/compra/pantalla_checkout.dart';
import '../../features/compra/pantalla_pedido.dart';
import '../../features/inicio/pantalla_carga.dart';
import '../../features/reservas/pantalla_detalle_reserva.dart';
import '../../features/reservas/pantalla_mis_reservas.dart';
import '../../features/reservas/pantalla_nueva_reserva.dart';
import '../../features/catalogo/pantalla_favoritos.dart';
import '../../features/vestidor/pantalla_vestidor.dart';
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

  /// CU-20 · mis prendas favoritas.
  ///
  /// Cuelga del catalogo y no de la raiz porque es una VISTA del catalogo
  /// ---las mismas tarjetas, filtradas por lo que el cliente guardo--- y asi
  /// el boton de volver la deja apilada donde corresponde.
  static const String favoritos = '/catalogo/favoritos';

  // Mateo:
  /// CU-23 · mis reservas, que es la puerta de entrada del paquete: el cliente
  /// llega a reservar desde aca, no al reves.
  static const String reservas = '/reservas';

  /// CU-22 · el formulario. Anidada bajo `/reservas` y declarada ANTES que
  /// `:id`, porque `go_router` prueba las rutas en orden y `nueva` encajaria
  /// en el patron del identificador.
  static const String reservaNueva = '/reservas/nueva';

  /// CU-23 · el detalle. Patron para el enrutador; para navegar se usa
  /// [reservaDetalle].
  static const String reservaDetallePatron = '/reservas/:id';

  /// La ruta concreta de una reserva. Es una funcion y no una interpolacion
  /// suelta en cada pantalla por el mismo motivo que las demas son constantes:
  /// un `/reserva/7` mal escrito no lo detecta nadie hasta que se ejecuta.
  static String reservaDetalle(int id) => '/reservas/$id';

  /// I3 · el prototipo del vestidor virtual. No es CU-21: es la prueba de
  /// riesgo que se construye en el Ciclo 2 para saber, antes del Ciclo 3, si
  /// la deteccion de pose sobre este telefono da un ritmo usable.
  static const String vestidor = '/vestidor';

  /// CU-26 · el carrito. Es la puerta del paquete de compra, igual que
  /// `/reservas` lo es del de reservas: se llega a pagar desde aca.
  static const String carrito = '/carrito';

  /// CU-27 · confirmar el pedido. Anidada bajo el carrito y declarada ANTES
  /// que `:codigo`, por lo mismo que `nueva` en reservas: `go_router` prueba
  /// en orden y 'checkout' encajaria en el patron del codigo.
  static const String checkout = '/carrito/checkout';

  /// CU-27 · la ficha del pedido. Patron para el enrutador; para navegar se
  /// usa [pedidoDe].
  static const String pedidoPatron = '/carrito/:codigo';

  /// La ruta concreta de un pedido. **Por codigo y no por identificador**: es
  /// `VB-20260917-A3F2`, lo que el cliente ve y puede leer por telefono. El
  /// backend tampoco expone el `id` de la venta.
  static String pedidoDe(String codigo) => '/carrito/$codigo';
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
          // CU-20. VA ANTES que ':id' a proposito: la ficha es una ruta
          // ANIDADA con parametro, asi que '/catalogo/favoritos' tambien
          // encaja en ella. go_router se queda con la primera que coincide;
          // al reves, tocar Favoritos abriria la vitrina --- la ficha no
          // revienta porque ya descarta un identificador no numerico, pero
          // la pantalla de favoritos no se veria NUNCA.
          GoRoute(
            path: 'favoritos',
            builder: (context, estado) => const PantallaFavoritos(),
          ),
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

      // Mateo: el prototipo del vestidor (I3).
      GoRoute(
        path: Rutas.vestidor,
        builder: (context, estado) {
          // `extra` lleva la prenda cuando se entra desde la ficha. Va por ahi
          // y no por la ruta porque es una URL completa: meterla en el camino
          // obligaria a escaparla y la pantalla dejaria de ser legible.
          final datos = estado.extra as Map<String, String?>?;
          return PantallaVestidor(
            urlInicial: datos?['url'],
            nombreInicial: datos?['nombre'],
          );
        },
      ),

      // Mateo: reservas (CU-22, CU-23).
      GoRoute(
        path: Rutas.carrito,
        builder: (context, estado) => const PantallaCarrito(),
        routes: [
          GoRoute(
            // ANTES que ':codigo': 'checkout' encajaria en el patron.
            path: 'checkout',
            builder: (context, estado) => const PantallaCheckout(),
          ),
          GoRoute(
            // Anidada y no suelta, igual que el detalle de una reserva: asi el
            // boton de volver del telefono lleva del pedido al carrito.
            path: ':codigo',
            builder: (context, estado) {
              final codigo = estado.pathParameters['codigo'];
              if (codigo == null || codigo.isEmpty) {
                return const PantallaCarrito();
              }
              // `extra` trae el PedidoCreado cuando se llega desde el
              // checkout, porque la URL de pago NO esta en la ficha del
              // pedido: es de una sesion concreta de la pasarela. Llegando de
              // cualquier otro lado viene nulo, y la pantalla lo contempla.
              return PantallaPedido(
                codigo: codigo,
                recienCreado: estado.extra is PedidoCreado
                    ? estado.extra! as PedidoCreado
                    : null,
              );
            },
          ),
        ],
      ),
      GoRoute(
        path: Rutas.reservas,
        builder: (context, estado) => const PantallaMisReservas(),
        routes: [
          GoRoute(
            // ANTES que ':id', porque `go_router` prueba en orden y 'nueva'
            // encajaria en el patron del identificador: sin esto, tocar
            // «Reservar» abriria el detalle de una reserva inexistente.
            path: 'nueva',
            builder: (context, estado) => const PantallaNuevaReserva(),
          ),
          GoRoute(
            // Anidada y no suelta, igual que la ficha: asi el boton de volver
            // del telefono lleva del detalle a la lista y no a la pantalla de
            // inicio.
            path: ':id',
            builder: (context, estado) {
              final id = int.tryParse(estado.pathParameters['id'] ?? '');
              if (id == null) return const PantallaMisReservas();
              return PantallaDetalleReserva(reservaId: id);
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
