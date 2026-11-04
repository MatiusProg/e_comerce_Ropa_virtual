/// Violet Boutique — aplicacion movil del Cliente.
///
/// Punto de entrada. Todo lo demas cuelga de `app.dart`.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';
import 'core/push/servicio_push.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // CU-42. Nunca falla: sin Firebase configurado, la app sigue sin push.
  await ServicioPush.instancia.inicializar();

  // La app se diseno en vertical; el vestidor virtual del Ciclo 3 tampoco tiene
  // sentido en horizontal.
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  runApp(const ProviderScope(child: AplicacionVioletBoutique()));
}
