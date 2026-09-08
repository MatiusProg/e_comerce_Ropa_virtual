import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/enrutado/router.dart';
import 'core/tema/tema.dart';

void main() {
  runApp(const ProviderScope(child: VioletBoutiqueApp()));
}

class VioletBoutiqueApp extends ConsumerWidget {
  const VioletBoutiqueApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      title: 'Violet Boutique',
      debugShowCheckedModeBanner: false,
      theme: TemaVioletBoutique.claro(),
      darkTheme: TemaVioletBoutique.oscuro(),
      routerConfig: ref.watch(routerProvider),
    );
  }
}
