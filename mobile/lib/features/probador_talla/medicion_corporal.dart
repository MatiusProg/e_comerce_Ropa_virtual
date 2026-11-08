/// Medir a la persona que está frente a la cámara (CU-37 en el móvil).
///
/// EL PROBLEMA
/// -----------
/// La escala del probador salía de las medidas guardadas en la cuenta. Si con
/// la misma cuenta se paraba otra persona frente a la cámara, la prenda se
/// dibujaba en la MISMA proporción respecto de sus hombros: a todos «les
/// quedaba igual». El teléfono no puede saber cuánto mide algo en centímetros
/// con una sola cámara si no tiene una referencia.
///
/// LA REFERENCIA ES LA ESTATURA
/// ----------------------------
/// La persona dice solo su estatura y se para de cuerpo entero. ML Kit da la
/// nariz, los tobillos y los hombros. De la nariz a los tobillos hay, en un
/// adulto, cerca del 89 % de la estatura; con eso se sabe cuántos píxeles es un
/// centímetro de ESA persona, y el ancho entre sus hombros pasa a centímetros.
///
/// Los puntos de hombro de ML Kit están en la articulación, un poco adentro
/// del borde del hombro: el ancho de hombros real (biacromial) es cerca de un
/// 15 % mayor. Y el ancho de hombros es cerca del 42 % del contorno de busto
/// (la misma relación que usa el dibujo, `hombrosSobreBusto`). Son
/// aproximaciones antropométricas: el resultado es una ESTIMACIÓN y la pantalla
/// lo dice así. Sirve para que dos personas distintas vean tallas distintas.
library;

import 'dart:math' as math;
import 'dart:ui';

import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart';

import '../../data/repositorios/repositorio_medidas.dart';
import 'pintor_talla_real.dart';

/// Nariz a tobillos, como fracción de la estatura de un adulto.
const double narizATobillosSobreEstatura = 0.89;

/// Ancho biacromial real sobre la distancia entre los puntos de hombro de ML Kit.
const double biacromialSobreLandmarks = 1.15;

class MedicionCorporal {
  const MedicionCorporal({required this.bustoCm, required this.hombrosCm});

  final double bustoCm;
  final double hombrosCm;

  /// Mide con UNA pose (coordenadas de la imagen). Devuelve `null` si no se ven
  /// la nariz, los dos hombros y los dos tobillos con suficiente confianza.
  static MedicionCorporal? desde(Pose pose, double estaturaCm) {
    PoseLandmark? p(PoseLandmarkType t) {
      final l = pose.landmarks[t];
      return (l == null || l.likelihood < 0.6) ? null : l;
    }

    final nariz = p(PoseLandmarkType.nose);
    final hi = p(PoseLandmarkType.leftShoulder);
    final hd = p(PoseLandmarkType.rightShoulder);
    final ti = p(PoseLandmarkType.leftAnkle);
    final td = p(PoseLandmarkType.rightAnkle);
    if (nariz == null || hi == null || hd == null || ti == null || td == null) return null;

    final tobillosY = (ti.y + td.y) / 2;
    final narizATobillosPx = tobillosY - nariz.y;
    if (narizATobillosPx < 100) return null;
    final pxPorCm = narizATobillosPx / (estaturaCm * narizATobillosSobreEstatura);

    final hombrosPx = (Offset(hd.x, hd.y) - Offset(hi.x, hi.y)).distance;
    final hombrosCm = hombrosPx / pxPorCm * biacromialSobreLandmarks;
    final busto = hombrosCm / hombrosSobreBusto;
    // Fuera de un rango humano razonable la medición salió mal (pose rara).
    if (busto < 65 || busto > 160) return null;
    return MedicionCorporal(bustoCm: busto, hombrosCm: hombrosCm);
  }

  /// La mediana de varias mediciones: una sola pose puede salir torcida.
  static MedicionCorporal? mediana(List<MedicionCorporal> lista) {
    if (lista.isEmpty) return null;
    final ordenada = [...lista]..sort((a, b) => a.bustoCm.compareTo(b.bustoCm));
    return ordenada[ordenada.length ~/ 2];
  }
}

/// La regla de `backend/app/modules/medidas/tallaje.py`, en el teléfono, para
/// clasificar con el busto MEDIDO de quien está frente a la cámara.
class TallajeLocal {
  static const Map<String, double> bustoCuerpoPorTalla = {
    'XS': 82, 'S': 87, 'M': 92, 'L': 97, 'XL': 102, 'XXL': 107, 'XXXL': 112,
  };

  static const List<(double, Ajuste)> tramos = [
    (-8, Ajuste.noEntra),
    (-3, Ajuste.ajustada),
    (3, Ajuste.aTuMedida),
    (8, Ajuste.holgada),
  ];

  static double? _desvio(double bustoPrenda, double bustoCuerpo, String codigo) {
    final cuerpo = bustoCuerpoPorTalla[codigo];
    if (cuerpo == null) return null;
    final diseno = bustoPrenda - cuerpo; // la holgura que le dio el fabricante
    return (bustoPrenda - bustoCuerpo) - diseno;
  }

  static Ajuste? clasificar(double bustoPrenda, double bustoCuerpo, String codigo) {
    final d = _desvio(bustoPrenda, bustoCuerpo, codigo);
    if (d == null) return null;
    for (final (limite, ajuste) in tramos) {
      if (d < limite) return ajuste;
    }
    return Ajuste.muyHolgada;
  }

  /// La talla cuyo desvío queda más cerca de cero.
  static String? recomendada(List<AjusteDeTalla> tallas, double bustoCuerpo) {
    String? mejor;
    var menor = double.infinity;
    for (final t in tallas) {
      final d = _desvio(t.bustoCm, bustoCuerpo, t.codigo);
      if (d == null) continue;
      if (d.abs() < menor) {
        menor = d.abs();
        mejor = t.codigo;
      }
    }
    return mejor;
  }

  /// Útil para mostrar: la talla de cuerpo más cercana al busto medido.
  static String tallaDeCuerpo(double busto) {
    var mejor = 'M';
    var menor = double.infinity;
    bustoCuerpoPorTalla.forEach((codigo, b) {
      final d = (b - busto).abs();
      if (d < menor) {
        menor = d;
        mejor = codigo;
      }
    });
    return mejor;
  }

  static double redondear(double v) => (v * 2).roundToDouble() / 2;

  static double max(double a, double b) => math.max(a, b);
}
