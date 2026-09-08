/// Raiz de la aplicacion.
library;

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/enrutado/router.dart';
import 'core/tema.dart';

class AplicacionVioletBoutique extends ConsumerWidget {
  const AplicacionVioletBoutique({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      title: 'Violet Boutique',
      debugShowCheckedModeBanner: false,
      theme: construirTema(),
      routerConfig: ref.watch(routerProvider),
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
