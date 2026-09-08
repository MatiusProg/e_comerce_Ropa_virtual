/// Tema visual de Violet Boutique.
///
/// Los colores son los mismos que los de la web (`frontend-web/src/styles.scss`,
/// variables `--vb-*`). Se repiten aqui en vez de derivarlos porque Flutter y
/// SCSS no comparten hoja de estilos: si cambia la marca hay que tocar los dos.
library;

import 'package:flutter/material.dart';

/// Paleta de la marca — malva y oro rosa.
class ColoresVB {
  const ColoresVB._();

  static const Color malva = Color(0xFF8E4A67);
  static const Color malvaOscuro = Color(0xFF6D3550);
  static const Color malvaClaro = Color(0xFFB57F9A);
  static const Color oro = Color(0xFFC9A227);
  static const Color oroRosa = Color(0xFFE7BFA8);
  static const Color rosaPalido = Color(0xFFF6E6EC);
  static const Color marfil = Color(0xFFFBF6F4);
  static const Color tinta = Color(0xFF2E1F28);
}

/// Degradado principal, el mismo `--vb-degradado` de la web.
const LinearGradient degradadoVB = LinearGradient(
  begin: Alignment.topLeft,
  end: Alignment.bottomRight,
  colors: [Color(0xFF8E4A67), Color(0xFFA85B7D), Color(0xFFC98DA5)],
  stops: [0.0, 0.45, 1.0],
);

/// Radio de esquina de tarjetas y campos (`--vb-radio`).
const double radioVB = 16;
const double radioChicoVB = 10;

ThemeData construirTema() {
  final esquema = ColorScheme.fromSeed(
    seedColor: ColoresVB.malva,
    brightness: Brightness.light,
  ).copyWith(
    primary: ColoresVB.malva,
    onPrimary: Colors.white,
    primaryContainer: ColoresVB.rosaPalido,
    onPrimaryContainer: const Color(0xFF3F1D2D),
    tertiary: const Color(0xFFA8801F),
    surface: Colors.white,
    onSurface: ColoresVB.tinta,
  );

  return ThemeData(
    useMaterial3: true,
    colorScheme: esquema,
    scaffoldBackgroundColor: ColoresVB.marfil,
    appBarTheme: const AppBarTheme(
      backgroundColor: ColoresVB.malva,
      foregroundColor: Colors.white,
      elevation: 0,
      centerTitle: true,
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(radioChicoVB),
        borderSide: const BorderSide(color: Color(0xFFE3D3DA)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(radioChicoVB),
        borderSide: const BorderSide(color: Color(0xFFE3D3DA)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(radioChicoVB),
        borderSide: const BorderSide(color: ColoresVB.malva, width: 2),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: ColoresVB.malva,
        foregroundColor: Colors.white,
        minimumSize: const Size.fromHeight(52),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radioChicoVB),
        ),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(foregroundColor: ColoresVB.malvaOscuro),
    ),
    cardTheme: CardThemeData(
      color: Colors.white,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(radioVB),
        side: const BorderSide(color: Color(0xFFEFE0E6)),
      ),
    ),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(radioChicoVB),
      ),
    ),
  );
}
