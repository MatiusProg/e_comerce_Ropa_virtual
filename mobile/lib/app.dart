/// Raiz de la aplicacion.
library;

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/enrutado/router.dart';
import 'core/push/servicio_push.dart';
import 'core/tema.dart';

/// CU-42: el enlace de un aviso es una ruta de la WEB. Se traduce a la
/// pantalla de la app que muestra lo mismo; lo que la app no tiene (la caja,
/// la sucursal) cae en el inicio.
String rutaDeLaApp(String enlace) {
  if (enlace.startsWith('/mi-cuenta/reservas')) return Rutas.reservas;
  if (enlace.startsWith('/mi-cuenta/compras')) return Rutas.misCompras;
  if (enlace.startsWith('/sucursal/inventario')) return Rutas.inventario;
  return Rutas.inicio;
}

class AplicacionVioletBoutique extends ConsumerWidget {
  const AplicacionVioletBoutique({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    ref.read(servicioPushProvider).alTocar =
        (enlace) => router.go(rutaDeLaApp(enlace));
    return MaterialApp.router(
      title: 'Violet Boutique',
      debugShowCheckedModeBanner: false,
      theme: construirTema(),
      routerConfig: router,
      // La app es para clientes en Bolivia: los textos de los widgets de
      // Material —selector de fecha, menu de un campo de texto— tienen que
      // salir en castellano, no en ingles.
      locale: const Locale('es'),
      supportedLocales: const [Locale('es'), Locale('en')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
    );
  }
}
