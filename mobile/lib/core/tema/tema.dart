import 'package:flutter/material.dart';

/// Tema de Violet Boutique. El violeta es el mismo de la web
/// (`frontend-web/src/styles.scss`), para que las dos plataformas se vean
/// como el mismo producto.
class TemaVioletBoutique {
  const TemaVioletBoutique._();

  static const Color violeta = Color(0xFF6D28D9);

  static ThemeData claro() {
    final esquema = ColorScheme.fromSeed(
      seedColor: violeta,
      brightness: Brightness.light,
    );
    return _armar(esquema);
  }

  static ThemeData oscuro() {
    final esquema = ColorScheme.fromSeed(
      seedColor: violeta,
      brightness: Brightness.dark,
    );
    return _armar(esquema);
  }

  static ThemeData _armar(ColorScheme esquema) => ThemeData(
        colorScheme: esquema,
        useMaterial3: true,
        inputDecorationTheme: const InputDecorationTheme(
          border: OutlineInputBorder(),
          filled: true,
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            minimumSize: const Size.fromHeight(48),
            textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
          ),
        ),
        snackBarTheme: const SnackBarThemeData(
          behavior: SnackBarBehavior.floating,
        ),
      );
}
