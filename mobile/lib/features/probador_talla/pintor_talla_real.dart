/// Dibuja la prenda calibrada (CU-36) sobre el cuerpo, a su tamaño REAL.
///
/// Es la misma cuenta que la web (`probador.ts`, `superponer`), pero en vivo:
///
/// ```
/// px_por_cm    = hombros_en_pantalla_px / (busto_cliente_cm × 0,42)
/// ancho_prenda = busto_talla_cm × 0,42 × px_por_cm   (entre los puntos de hombro)
/// largo_prenda = largo_talla_cm × px_por_cm          (de la línea de hombros al ruedo)
/// ```
///
/// El 0,42 (hombros sobre busto) se cancela en la razón ancho de prenda /
/// ancho de cuerpo, que es la misma que usa `medidas.tallaje.factor_de_ancho`.
/// Lo que importa: **la prenda no se acomoda al cuerpo**. Si la talla le queda
/// grande, se ve grande; si le queda chica, se ve chica.
library;

import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

import '../../data/repositorios/repositorio_probador.dart';

/// Hombros sobre busto: ver la explicación en `probador.ts` de la web.
const double hombrosSobreBusto = 0.42;

/// Cuánto subir la línea de hombros sobre los puntos de ML Kit, como fracción
/// del ancho entre ellos. Medido en el teléfono el 08/11 (la prenda quedaba baja).
const double subidaDeHombros = 0.16;

class PintorTallaReal extends CustomPainter {
  PintorTallaReal({
    required this.prenda,
    required this.puntos,
    required this.hombroA,
    required this.hombroB,
    this.bustoClienteCm,
    this.bustoTallaCm,
    this.largoTallaCm,
  });

  final ui.Image prenda;
  final PuntosDePrenda puntos;

  /// Los hombros en pantalla, ORDENADOS por su x: A a la izquierda.
  final Offset hombroA;
  final Offset hombroB;

  /// Si falta cualquiera de los tres, no hay escala real y se dibuja aproximado.
  final double? bustoClienteCm;
  final double? bustoTallaCm;
  final double? largoTallaCm;

  bool get aEscala =>
      bustoClienteCm != null && bustoTallaCm != null && largoTallaCm != null;

  @override
  void paint(Canvas canvas, Size size) {
    final w = prenda.width.toDouble();
    final h = prenda.height.toDouble();

    // La prenda, en píxeles de SU imagen.
    final gIzq = Offset(puntos.hombroIzq.x * w, puntos.hombroIzq.y * h);
    final gDer = Offset(puntos.hombroDer.x * w, puntos.hombroDer.y * h);
    final gMedio = (gIzq + gDer) / 2;
    final gHombros = (gDer - gIzq).distance;
    final gLargo = puntos.ruedo.y * h - gMedio.dy;
    if (gHombros < 1 || gLargo < 1) return;

    // El cuerpo, en píxeles de la pantalla.
    final bHombros = (hombroB - hombroA).distance;
    if (bHombros < 10) return;
    final angulo = math.atan2(hombroB.dy - hombroA.dy, hombroB.dx - hombroA.dx);
    // Los puntos de hombro de ML Kit están en la ARTICULACIÓN, más abajo que la
    // costura del hombro de la prenda: sin corregirlo, la prenda queda caída.
    // Se sube la línea de hombros, perpendicular a ella, una fracción de su ancho.
    final arriba = Offset(math.sin(angulo), -math.cos(angulo));
    final bMedio = (hombroA + hombroB) / 2 + arriba * (bHombros * subidaDeHombros);

    double anchoObjetivo;
    double largoObjetivo;
    if (aEscala) {
      final pxPorCm = bHombros / (bustoClienteCm! * hombrosSobreBusto);
      anchoObjetivo = bustoTallaCm! * hombrosSobreBusto * pxPorCm;
      largoObjetivo = largoTallaCm! * pxPorCm;
    } else {
      // Sin medidas no hay escala real: tamaño aproximado (la pantalla lo avisa).
      anchoObjetivo = bHombros * 1.1;
      largoObjetivo = gLargo * (anchoObjetivo / gHombros);
    }
    final sx = anchoObjetivo / gHombros;
    final sy = largoObjetivo / gLargo;

    canvas.save();
    canvas.translate(bMedio.dx, bMedio.dy);
    canvas.rotate(angulo);
    canvas.scale(sx, sy);
    canvas.drawImage(
      prenda,
      Offset(-gMedio.dx, -gMedio.dy),
      Paint()..filterQuality = FilterQuality.medium,
    );
    canvas.restore();
  }

  @override
  bool shouldRepaint(PintorTallaReal anterior) =>
      anterior.prenda != prenda ||
      anterior.hombroA != hombroA ||
      anterior.hombroB != hombroB ||
      anterior.bustoTallaCm != bustoTallaCm ||
      anterior.largoTallaCm != largoTallaCm ||
      anterior.bustoClienteCm != bustoClienteCm;
}

/// Los hombros detectados, como dos puntos sobre la pantalla (solo cuando
/// todavía no hay prenda puesta, para que se vea que el cuerpo está detectado).
class PintorHombros extends CustomPainter {
  PintorHombros(this.a, this.b);

  final Offset a;
  final Offset b;

  @override
  void paint(Canvas canvas, Size size) {
    final relleno = Paint()..color = const Color(0xFFD81B60);
    final borde = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;
    for (final p in [a, b]) {
      canvas.drawCircle(p, 7, relleno);
      canvas.drawCircle(p, 7, borde);
    }
  }

  @override
  bool shouldRepaint(PintorHombros anterior) => anterior.a != a || anterior.b != b;
}
