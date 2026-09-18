/// CU-21 · Dibuja la prenda DEFORMADA sobre el cuerpo, no pegada encima.
///
/// EL PROBLEMA QUE ESTO RESUELVE
/// -----------------------------
/// Hasta el 18/09 la prenda era un `Image.network` dentro de un rectangulo
/// rotado: una calcomania. Seguía al cuerpo en posicion, tamano e inclinacion,
/// y nada mas. Si la persona se giraba, la prenda quedaba igual de ancha; si
/// se inclinaba hacia adelante, la prenda no se acortaba. Se veía pegada
/// porque **estaba** pegada.
///
/// Ahora la prenda se dibuja como una MALLA de triangulos texturados cuyos
/// puntos salen de la pose. La malla se estrecha donde el cuerpo se estrecha y
/// se inclina con el torso, asi que la prenda se deforma con la persona.
///
/// POR QUE `drawVertices` Y NO UN `Transform`
/// -------------------------------------------
/// Una matriz de transformacion solo puede hacer transformaciones afines:
/// mover, rotar, escalar, sesgar. Un torso visto en perspectiva **no es una
/// transformacion afin** --- los hombros y la cadera se ven de anchos
/// distintos segun como este parada la persona ---, asi que con una matriz no
/// hay forma de conseguirlo.
///
/// `Canvas.drawVertices` dibuja triangulos con coordenadas de textura, que es
/// exactamente lo que hace falta: cada punto de la malla dice de que parte del
/// PNG se pinta. Es lo mismo que hace un motor 3D con una tela, con una malla
/// mucho mas chica.
///
/// TODO ESTO CORRE EN EL TELEFONO Y NO CUESTA NADA
/// ------------------------------------------------
/// Es la respuesta a «se ve muy simple» sin depender de ningun servicio: la
/// deteccion de pose ya daba los puntos, solo que no se estaban aprovechando.
/// El probado por IA sigue siendo otra cosa --- y sigue apagado, porque la
/// generacion de imagenes de Gemini no esta en el plan gratuito.
library;

import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

/// Los cuatro puntos del torso que manejan la malla, ya en coordenadas de
/// pantalla y ORDENADOS por su x en pantalla --- no por su nombre anatomico.
///
/// El orden importa por el espejo de la camara frontal: el «hombro izquierdo»
/// del cuerpo aparece a la derecha de la pantalla. Tomarlos por su nombre daba
/// una malla dada vuelta, que es el mismo defecto que ya se habia corregido en
/// el angulo el 13/09.
class TorsoEnPantalla {
  const TorsoEnPantalla({
    required this.hombroA,
    required this.hombroB,
    this.caderaA,
    this.caderaB,
  });

  final Offset hombroA;
  final Offset hombroB;

  /// Pueden faltar: la deteccion pierde la cadera cuando la persona esta muy
  /// cerca de la camara. La malla sigue funcionando, con menos informacion.
  final Offset? caderaA;
  final Offset? caderaB;

  Offset get centroHombros => (hombroA + hombroB) / 2;
  double get anchoHombros => (hombroA - hombroB).distance;

  Offset? get centroCadera =>
      (caderaA != null && caderaB != null) ? (caderaA! + caderaB!) / 2 : null;

  double? get anchoCadera =>
      (caderaA != null && caderaB != null) ? (caderaA! - caderaB!).distance : null;
}

/// Cuanto mas ancha es la prenda que la distancia entre los hombros.
///
/// 2.1 venia del prototipo I3 y estaba calibrado contra las siluetas que
/// dibuja el `seed`: rectangulos angostos, sin mangas, que necesitaban
/// ensancharse bastante para cubrir el torso.
///
/// **Una foto real de una prenda ya trae las mangas adentro**, asi que con 2.1
/// sale enorme --- se probo el 18/09 con una blusa de verdad y tapaba media
/// pantalla. Lo que hay que cubrir es el ancho de hombros mas lo que sobresale
/// la manga, que en una prenda de frente es alrededor de 1.5 veces.
///
/// SE AJUSTA MIRANDO EL TELEFONO, NO RAZONANDO
/// --------------------------------------------
/// Este numero y `subida` son los dos que hay que calibrar con una persona
/// delante de la camara. No hay forma de deducirlos: dependen de como se
/// fotografio la prenda.
///
/// Lo que lo resolveria de verdad es una convencion mas: fijar tambien cuanto
/// ocupan los HOMBROS dentro del PNG ---por ejemplo, el 60 % de su ancho--- y
/// derivar la escala de ahi. Cada prenda se corregiria sola. Queda anotado.
const double anchoRespectoAHombros = 1.78;

/// Cuanto sube la prenda por encima de la linea de hombros, en proporcion a su
/// propio ancho. **Es el mismo 0.18 que la guia de carga le pide al PNG.**
const double subida = 0.18;

/// Cuantas divisiones tiene la malla.
///
/// 6 x 10 es el equilibrio que se midio en el telefono: con menos, el
/// estrechamiento de la cintura se ve como un quiebre; con muchas mas, no se
/// nota la diferencia y cada fotograma cuesta mas. Son 120 triangulos, que es
/// nada para la GPU.
const int _columnas = 6;
const int _filas = 10;

class PintorPrenda extends CustomPainter {
  const PintorPrenda({required this.prenda, required this.torso});

  final ui.Image prenda;
  final TorsoEnPantalla torso;

  @override
  void paint(Canvas canvas, Size size) {
    final anchoHombros = torso.anchoHombros;
    if (anchoHombros < 8) return;

    // --- El sistema de referencia del torso ------------------------------
    //
    // `eje` apunta de los hombros a la cadera --- el «hacia abajo» del cuerpo,
    // que no es el hacia abajo de la pantalla cuando la persona se inclina ---
    // y `perp` es su perpendicular, el «hacia la derecha» del cuerpo.
    final centroHombros = torso.centroHombros;
    final centroCadera = torso.centroCadera;

    Offset eje;
    if (centroCadera != null && (centroCadera - centroHombros).distance > 20) {
      eje = (centroCadera - centroHombros);
      eje = eje / eje.distance;
    } else {
      // Sin cadera visible se usa la perpendicular a los hombros, que es la
      // mejor aproximacion disponible.
      final h = (torso.hombroB - torso.hombroA);
      eje = Offset(-h.dy, h.dx);
      eje = eje / eje.distance;
      // Que apunte hacia abajo en pantalla, no hacia arriba.
      if (eje.dy < 0) eje = -eje;
    }
    final perp = Offset(-eje.dy, eje.dx);

    // --- Las dos anchuras que gobiernan la deformacion --------------------
    // EL ANCHO NO PUEDE COLAPSAR AL GIRARSE.
    //
    // Al ponerse de perfil, los dos hombros se proyectan casi en el mismo
    // punto y `anchoHombros` cae a una fraccion. El ancho de la prenda caia
    // con el mientras el largo ---que sale del torso--- se mantenia, y la
    // blusa quedaba como una tira larga y angosta pegada de costado. Se vio en
    // el telefono el 18/09.
    //
    // El cuerpo SI se ve mas angosto al girar, asi que la prenda tiene que
    // angostarse; lo que no puede es desaparecer. En una persona de frente el
    // ancho de hombros y el largo del torso son parecidos ---hombros algo mas
    // angostos---, asi que el largo del torso sirve de referencia para poner
    // un piso.
    final largoTorsoRef = centroCadera == null
        ? null
        : (centroCadera - centroHombros).distance;
    final hombrosEfectivos = largoTorsoRef == null
        ? anchoHombros
        : math.max(anchoHombros, largoTorsoRef * 0.62);

    final anchoArriba = hombrosEfectivos * anchoRespectoAHombros;

    // La cadera manda el ancho de abajo, pero ACOTADA contra los hombros.
    //
    // La idea de que la cadera gobierne el ruedo es la que hace que un cuerpo
    // girado ---hombros anchos y cadera angosta, o al reves--- lleve una
    // prenda que se estrecha donde el cuerpo se estrecha, en vez de una tabla.
    //
    // Sin acotar se rompe, y se vio en el telefono el 18/09: parada de costado
    // y con las manos en la cintura, la deteccion pone los puntos de cadera
    // mas separados que los hombros y la prenda **se abria abajo hasta salirse
    // del cuerpo**, flotando sobre el fondo.
    //
    // Dos razones para acotar y no confiar:
    //   - una blusa REAL no se ensancha en la cadera: cae recta o afina;
    //   - los puntos de cadera son los menos fiables de la pose --- quedan
    //     tapados por los brazos, por la ropa suelta y por el encuadre.
    //
    // Asi que se usa la PROPORCION cadera/hombros, no el ancho crudo, y se
    // acota: puede angostar hasta un 22 % y ensanchar apenas un 2 %.
    final proporcion = torso.anchoCadera == null
        ? 0.92
        : (torso.anchoCadera! / hombrosEfectivos).clamp(0.78, 1.02);
    final anchoAbajo = anchoArriba * proporcion;

    // --- De la imagen a la pantalla ---------------------------------------
    //
    // DOS ESCALAS, NO UNA. El ancho sale de los hombros y el LARGO del torso.
    //
    // Con una sola escala pasaba esto, visto en el telefono el 18/09: al
    // girarse, la distancia entre hombros se achica en pantalla ---es cierto,
    // el cuerpo se ve mas angosto--- y el largo, que salia del ancho, se
    // achicaba con el. La blusa quedaba como un top a media panza. Pero el
    // torso de la persona NO se acorto al girarse.
    //
    // El largo del torso ---de hombros a cadera--- casi no cambia al girar,
    // asi que es la medida correcta para el largo. Que las dos escalas sean
    // distintas no es un defecto: es lo que hace que la prenda se estire para
    // cubrir el cuerpo en vez de encogerse entera.
    final escalaX = anchoArriba / prenda.width;

    // Lo que hay del hombro al ruedo DENTRO del PNG, en pixeles de la imagen.
    final altoDePrenda = prenda.height - subida * prenda.width;

    double escalaY = escalaX;
    if (centroCadera != null) {
      final largoTorso = (centroCadera - centroHombros).distance;
      if (largoTorso > 20 && altoDePrenda > 1) {
        // El ruedo de una blusa cae un poco por debajo de la cadera. 1.25 sale
        // de mirarlo en el telefono, como las otras dos constantes.
        escalaY = (largoTorso * 1.25) / altoDePrenda;
      }
    }
    // Donde cae la linea de hombros DENTRO del PNG, en coordenadas 0..1 de su
    // alto. Sale de la convencion de carga: `subida x ancho del PNG`.
    final vHombros = (subida * prenda.width) / prenda.height;

    final posiciones = Float32List(((_columnas + 1) * (_filas + 1)) * 2);
    final textura = Float32List(((_columnas + 1) * (_filas + 1)) * 2);

    var i = 0;
    for (var fila = 0; fila <= _filas; fila++) {
      final v = fila / _filas;

      // Cuanto se avanzo por el eje del cuerpo desde la linea de hombros.
      final avance = (v - vHombros) * prenda.height * escalaY;

      // El ancho en esta altura. Se interpola de la linea de hombros hacia
      // abajo; por encima de los hombros --- el cuello --- se mantiene.
      final t = vHombros >= 1
          ? 0.0
          : ((v - vHombros) / (1 - vHombros)).clamp(0.0, 1.0);
      var ancho = anchoArriba + (anchoAbajo - anchoArriba) * t;

      // Un ensanchamiento suave a la altura del pecho. Sin esto la prenda se
      // lee como un cono: la tela sobre un cuerpo no va estrechandose parejo
      // desde el hombro.
      ancho *= 1 + 0.05 * math.sin(math.pi * t);

      final centro = centroHombros + eje * avance;

      for (var col = 0; col <= _columnas; col++) {
        final u = col / _columnas;
        final desplazamiento = (u - 0.5) * ancho;
        final punto = centro + perp * desplazamiento;

        posiciones[i] = punto.dx;
        posiciones[i + 1] = punto.dy;
        // La textura se lee en pixeles del PNG, asi que el `ImageShader` va
        // con la matriz identidad.
        textura[i] = u * prenda.width;
        textura[i + 1] = v * prenda.height;
        i += 2;
      }
    }

    // --- Los triangulos ----------------------------------------------------
    final indices = Uint16List(_columnas * _filas * 6);
    var k = 0;
    for (var fila = 0; fila < _filas; fila++) {
      for (var col = 0; col < _columnas; col++) {
        final a = fila * (_columnas + 1) + col;
        final b = a + 1;
        final c = a + (_columnas + 1);
        final d = c + 1;
        indices[k++] = a;
        indices[k++] = b;
        indices[k++] = c;
        indices[k++] = b;
        indices[k++] = d;
        indices[k++] = c;
      }
    }

    final vertices = ui.Vertices.raw(
      ui.VertexMode.triangles,
      posiciones,
      textureCoordinates: textura,
      indices: indices,
    );

    final pintura = Paint()
      ..shader = ui.ImageShader(
        prenda,
        TileMode.clamp,
        TileMode.clamp,
        Matrix4.identity().storage,
        // Sin filtro la malla muestra el escalonado del PNG en los bordes de
        // cada triangulo.
        filterQuality: FilterQuality.high,
      )
      ..isAntiAlias = true;

    canvas.drawVertices(vertices, BlendMode.srcOver, pintura);
    vertices.dispose();
  }

  @override
  bool shouldRepaint(PintorPrenda anterior) =>
      anterior.prenda != prenda ||
      anterior.torso.hombroA != torso.hombroA ||
      anterior.torso.hombroB != torso.hombroB ||
      anterior.torso.caderaA != torso.caderaA ||
      anterior.torso.caderaB != torso.caderaB;
}
