import 'package:flutter/material.dart';

/// Pantalla de arranque. Se muestra mientras se averigua si el token guardado
/// sigue siendo valido (`GET /auth/yo`). Es breve, pero sin ella la app
/// mostraria el login por un instante a quien ya tenia sesion abierta.
class ArranquePantalla extends StatelessWidget {
  const ArranquePantalla({super.key});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Scaffold(
      backgroundColor: tema.colorScheme.surface,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Violet Boutique',
              style: tema.textTheme.headlineSmall?.copyWith(
                color: tema.colorScheme.primary,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 24),
            const SizedBox(
              width: 28,
              height: 28,
              child: CircularProgressIndicator(strokeWidth: 3),
            ),
          ],
        ),
      ),
    );
  }
}
