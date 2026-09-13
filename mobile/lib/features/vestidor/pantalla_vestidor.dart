/// I3 · Prototipo del vestidor virtual.
///
/// **Es un prototipo de riesgo, no el CU-21.** Existe para contestar UNA
/// pregunta antes del Ciclo 3: ¿se puede detectar la pose del cuerpo en este
/// telefono, a una velocidad usable, y colocar la prenda encima siguiendo al
/// que se mueve? Si la respuesta hubiera sido que no, CU-21 habria que
/// replantearlo entero, y es mejor saberlo ahora que en el ultimo ciclo.
///
/// Lo que el prototipo SI hace:
///   - abre la camara frontal y corre la deteccion de pose sobre sus fotogramas
///   - superpone el PNG transparente de una variante real, tomado del catalogo
///   - lo escala, lo ubica y lo rota siguiendo los hombros y la cadera
///   - informa cuantos fotogramas por segundo esta procesando
///
/// Lo que NO hace, y es del Ciclo 3:
///   - no guarda la captura ni la comparte (eso es el flujo de CU-21)
///   - no ajusta la prenda a la profundidad ni a la rotacion del torso
///   - no distingue talla: pega el PNG de la variante que se elija
///
/// POR QUE NO SE PUEDE PROBAR EN EMULADOR
/// -------------------------------------
/// `google_mlkit_pose_detection` corre sobre los fotogramas de la camara y un
/// emulador entrega una camara sintetica --- una imagen de prueba que no tiene
/// cuerpo que detectar. Este prototipo solo dice algo cuando corre en un
/// telefono de verdad.
library;

import 'dart:math' as math;

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../core/tema.dart';
import '../../data/modelos/catalogo.dart';
import '../../data/repositorios/repositorio_catalogo.dart';
import '../catalogo/estado_catalogo.dart';

/// Cuanto mas ancha es la prenda que la distancia entre los hombros.
///
/// Los hombros que devuelve la deteccion son las articulaciones, no el borde
/// del cuerpo: una remera cubre bastante mas. El valor sale de probar sobre el
/// telefono, que es la unica forma de calibrarlo.
const double _anchoRespectoAHombros = 2.1;

/// Cuanto sube la prenda por encima de la linea de los hombros, en proporcion
/// a su propio ancho. Sin esto el cuello queda cortado.
const double _subida = 0.18;

class PantallaVestidor extends ConsumerStatefulWidget {
  /// [urlInicial] y [nombreInicial] llegan cuando se entra desde la ficha de
  /// una prenda (CU-18): la variante ya esta elegida y su PNG es el que hay que
  /// probarse. Es la costura C5.
  ///
  /// Sin ellos --- al entrar desde el menu --- la pantalla busca por su cuenta
  /// las prendas del catalogo que tengan PNG y ofrece elegir.
  const PantallaVestidor({super.key, this.urlInicial, this.nombreInicial});

  final String? urlInicial;
  final String? nombreInicial;

  @override
  ConsumerState<PantallaVestidor> createState() => _EstadoPantallaVestidor();
}

class _EstadoPantallaVestidor extends ConsumerState<PantallaVestidor>
    with WidgetsBindingObserver {
  CameraController? _camara;
  PoseDetector? _detector;

  bool _iniciando = true;
  String? _error;

  /// El detector procesa un fotograma por vez. Sin esta bandera, la camara
  /// encola fotogramas mas rapido de lo que ML Kit los resuelve y la memoria
  /// crece hasta que el sistema mata la aplicacion.
  bool _ocupado = false;

  Pose? _pose;
  Size? _tamanoImagen;

  int _fotogramas = 0;
  double _fps = 0;
  DateTime _ultimoCorte = DateTime.now();

  // --- la prenda -----------------------------------------------------------
  List<ProductoVitrina> _prendas = const [];
  ProductoVitrina? _prendaElegida;
  String? _urlPrenda;

  /// El nombre de la prenda cuando llego desde la ficha y todavia no esta en
  /// la lista del selector.
  String? _nombreSuelto;
  bool _cargandoPrendas = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _arrancar();
    if (widget.urlInicial != null) {
      // Viene de la ficha: la prenda ya esta resuelta y no hace falta ir al
      // catalogo. Igual se cargan las demas, para poder cambiar sin salir.
      _urlPrenda = widget.urlInicial;
      _nombreSuelto = widget.nombreInicial;
    }
    _cargarPrendas();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _camara?.dispose();
    _detector?.close();
    super.dispose();
  }

  /// La camara es un recurso del sistema: si la aplicacion pasa a segundo plano
  /// hay que soltarla, o al volver queda tomada y no se puede reabrir.
  @override
  void didChangeAppLifecycleState(AppLifecycleState estado) {
    final camara = _camara;
    if (camara == null || !camara.value.isInitialized) return;
    if (estado == AppLifecycleState.inactive) {
      camara.dispose();
    } else if (estado == AppLifecycleState.resumed) {
      _arrancar();
    }
  }

  Future<void> _arrancar() async {
    setState(() {
      _iniciando = true;
      _error = null;
    });

    final permiso = await Permission.camera.request();
    if (!permiso.isGranted) {
      if (!mounted) return;
      setState(() {
        _iniciando = false;
        _error = permiso.isPermanentlyDenied
            ? 'El permiso de cámara está denegado para siempre. Hay que '
                  'habilitarlo desde los ajustes del teléfono.'
            : 'Sin permiso de cámara no se puede usar el vestidor.';
      });
      return;
    }

    try {
      final camaras = await availableCameras();
      final frontal = camaras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.front,
        orElse: () => camaras.first,
      );

      final control = CameraController(
        frontal,
        ResolutionPreset.medium,
        enableAudio: false,
        // NV21 y no YUV420: es el formato que ML Kit consume de una sola
        // pasada en Android. Con YUV420 hay que recomponer los tres planos a
        // mano en Dart, y eso cuesta mas que la deteccion misma.
        imageFormatGroup: ImageFormatGroup.nv21,
      );
      await control.initialize();

      _detector = PoseDetector(
        options: PoseDetectorOptions(mode: PoseDetectionMode.stream),
      );

      await control.startImageStream(_alLlegarFotograma);

      if (!mounted) {
        await control.dispose();
        return;
      }
      setState(() {
        _camara = control;
        _iniciando = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _iniciando = false;
        _error = 'No se pudo abrir la cámara: $e';
      });
    }
  }

  Future<void> _cargarPrendas() async {
    try {
      // Se piden las ofrecibles y se filtran las que tienen PNG de vestidor.
      // `tiene_vestidor` viaja en el listado justamente para no abrir la ficha
      // de cada una solo para saberlo.
      final pagina = await ref
          .read(repositorioCatalogoProvider)
          .listar(const ConsultaVitrina(tamano: 48));
      final con = pagina.items.where((p) => p.tieneVestidor).toList();
      if (!mounted) return;
      setState(() {
        _prendas = con;
        _cargandoPrendas = false;
      });
      if (con.isNotEmpty && widget.urlInicial == null) {
        await _elegirPrenda(con.first);
      }
    } catch (_) {
      if (!mounted) return;
      setState(() => _cargandoPrendas = false);
    }
  }

  /// Abre la ficha y se queda con el PNG de la primera variante que lo tenga.
  Future<void> _elegirPrenda(ProductoVitrina prenda) async {
    setState(() {
      _prendaElegida = prenda;
      _urlPrenda = null;
    });
    try {
      final ficha = await ref
          .read(repositorioCatalogoProvider)
          .obtenerFicha(prenda.id);
      final variante = ficha.variantes.firstWhere(
        (v) => v.sePuedeProbar,
        orElse: () => ficha.variantes.first,
      );
      if (!mounted) return;
      setState(() {
        _urlPrenda = RepositorioCatalogo.urlDeImagen(variante.imagenVestidorUrl);
      });
    } catch (_) {
      /* se queda sin prenda; el aviso lo da la pantalla */
    }
  }

  // --- deteccion -----------------------------------------------------------

  Future<void> _alLlegarFotograma(CameraImage imagen) async {
    if (_ocupado || _detector == null || _camara == null) return;
    _ocupado = true;

    try {
      final camara = _camara!.description;
      final rotacion = InputImageRotationValue.fromRawValue(
        camara.sensorOrientation,
      );
      if (rotacion == null) return;

      final entrada = InputImage.fromBytes(
        bytes: imagen.planes.first.bytes,
        metadata: InputImageMetadata(
          size: Size(imagen.width.toDouble(), imagen.height.toDouble()),
          rotation: rotacion,
          format: InputImageFormat.nv21,
          bytesPerRow: imagen.planes.first.bytesPerRow,
        ),
      );

      final poses = await _detector!.processImage(entrada);

      // Con la imagen rotada 90 o 270 grados, ML Kit devuelve las coordenadas
      // en el espacio YA ROTADO: el ancho y el alto vienen cambiados respecto
      // del fotograma crudo. Sin esto, la prenda aparece tumbada.
      final vertical =
          rotacion == InputImageRotation.rotation90deg ||
          rotacion == InputImageRotation.rotation270deg;
      final tamano = vertical
          ? Size(imagen.height.toDouble(), imagen.width.toDouble())
          : Size(imagen.width.toDouble(), imagen.height.toDouble());

      _fotogramas++;
      final ahora = DateTime.now();
      final transcurrido = ahora.difference(_ultimoCorte).inMilliseconds;
      if (transcurrido >= 1000) {
        _fps = _fotogramas * 1000 / transcurrido;
        _fotogramas = 0;
        _ultimoCorte = ahora;
      }

      if (!mounted) return;
      setState(() {
        _pose = poses.isEmpty ? null : poses.first;
        _tamanoImagen = tamano;
      });
    } catch (_) {
      /* un fotograma perdido no es un error: llega otro en 33 ms */
    } finally {
      _ocupado = false;
    }
  }

  // --- pantalla ------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text('Vestidor virtual'),
        actions: [
          if (_prendas.isNotEmpty)
            IconButton(
              tooltip: 'Elegir prenda',
              icon: const Icon(Icons.checkroom),
              onPressed: _abrirSelector,
            ),
        ],
      ),
      body: _cuerpo(),
    );
  }

  Widget _cuerpo() {
    if (_iniciando) {
      return const Center(child: CircularProgressIndicator(color: Colors.white));
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.videocam_off, size: 48, color: Colors.white54),
              const SizedBox(height: 16),
              Text(
                _error!,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white, height: 1.5),
              ),
              const SizedBox(height: 20),
              FilledButton(onPressed: _arrancar, child: const Text('Reintentar')),
            ],
          ),
        ),
      );
    }

    final camara = _camara;
    if (camara == null || !camara.value.isInitialized) {
      return const Center(child: Text('Cámara no disponible',
          style: TextStyle(color: Colors.white)));
    }

    return LayoutBuilder(
      builder: (context, limites) {
        final caja = Size(limites.maxWidth, limites.maxHeight);
        return Stack(
          fit: StackFit.expand,
          children: [
            // La vista de la camara, recortada para llenar la pantalla.
            FittedBox(
              fit: BoxFit.cover,
              child: SizedBox(
                width: camara.value.previewSize?.height ?? caja.width,
                height: camara.value.previewSize?.width ?? caja.height,
                child: CameraPreview(camara),
              ),
            ),

            // La prenda, ubicada sobre el cuerpo detectado.
            if (_pose != null && _tamanoImagen != null && _urlPrenda != null)
              ..._prendaSobreElCuerpo(caja),

            _panel(),
          ],
        );
      },
    );
  }

  /// Coloca el PNG usando los hombros y la cadera.
  ///
  /// Los hombros dan el ancho y la inclinacion; la cadera, el alto. Es la
  /// aproximacion mas simple que sigue al cuerpo cuando se mueve, y alcanza
  /// para saber si el camino es viable.
  List<Widget> _prendaSobreElCuerpo(Size caja) {
    final pose = _pose!;
    final img = _tamanoImagen!;

    final hi = pose.landmarks[PoseLandmarkType.leftShoulder];
    final hd = pose.landmarks[PoseLandmarkType.rightShoulder];
    if (hi == null || hd == null) return const [];

    final ci = pose.landmarks[PoseLandmarkType.leftHip];
    final cd = pose.landmarks[PoseLandmarkType.rightHip];

    // La misma geometria que usa el BoxFit.cover de la vista, para que la
    // prenda y el cuerpo queden en el mismo sistema de coordenadas.
    final escala = math.max(caja.width / img.width, caja.height / img.height);
    final dx = (caja.width - img.width * escala) / 2;
    final dy = (caja.height - img.height * escala) / 2;

    // La camara frontal muestra el espejo: hay que invertir la X o la prenda
    // se mueve al reves que la persona.
    Offset aPantalla(double x, double y) =>
        Offset(dx + (img.width - x) * escala, dy + y * escala);

    final pHi = aPantalla(hi.x, hi.y);
    final pHd = aPantalla(hd.x, hd.y);

    final centroHombros = Offset(
      (pHi.dx + pHd.dx) / 2,
      (pHi.dy + pHd.dy) / 2,
    );
    final anchoHombros = (pHi - pHd).distance;
    if (anchoHombros < 8) return const [];

    final ancho = anchoHombros * _anchoRespectoAHombros;

    double alto = ancho * 1.35;
    if (ci != null && cd != null) {
      final pCentroCadera = Offset(
        (aPantalla(ci.x, ci.y).dx + aPantalla(cd.x, cd.y).dx) / 2,
        (aPantalla(ci.x, ci.y).dy + aPantalla(cd.x, cd.y).dy) / 2,
      );
      final torso = (pCentroCadera - centroHombros).distance;
      if (torso > 20) alto = torso * 1.45;
    }

    // El angulo se mide SIEMPRE del hombro que quedo mas a la izquierda EN
    // PANTALLA hacia el otro, no de «izquierdo» a «derecho» del cuerpo.
    //
    // Es la correccion del 13/09: el espejo de la camara frontal invierte cual
    // de los dos hombros cae a la izquierda, asi que tomarlos por su nombre
    // anatomico daba un vector apuntando al reves y `atan2` devolvia un angulo
    // cercano a 180 grados. La prenda salia dada vuelta, apuntando hacia
    // arriba. Ordenandolos por su x en pantalla, dx es siempre positivo y el
    // angulo queda cerca de cero, que es lo que corresponde a hombros
    // nivelados.
    final izq = pHi.dx <= pHd.dx ? pHi : pHd;
    final der = pHi.dx <= pHd.dx ? pHd : pHi;
    final angulo = math.atan2(der.dy - izq.dy, der.dx - izq.dx);

    return [
      Positioned(
        left: centroHombros.dx - ancho / 2,
        top: centroHombros.dy - ancho * _subida,
        width: ancho,
        height: alto,
        child: IgnorePointer(
          child: Transform.rotate(
            angle: angulo,
            alignment: Alignment.topCenter,
            child: Image.network(
              _urlPrenda!,
              fit: BoxFit.contain,
              gaplessPlayback: true,
              errorBuilder: (_, __, ___) => const SizedBox.shrink(),
            ),
          ),
        ),
      ),
    ];
  }

  /// El panel de abajo: qué prenda está puesta y a qué velocidad va.
  ///
  /// Los fotogramas por segundo no son un adorno de desarrollo: son **el dato
  /// que este prototipo existe para medir**. Si la detección no llega a un
  /// ritmo usable en este teléfono, CU-21 hay que replantearlo.
  Widget _panel() {
    final hayCuerpo = _pose != null;
    return Positioned(
      left: 0,
      right: 0,
      bottom: 0,
      child: Container(
        padding: const EdgeInsets.fromLTRB(18, 14, 18, 26),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Colors.transparent, Colors.black.withValues(alpha: 0.78)],
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  hayCuerpo ? Icons.accessibility_new : Icons.search,
                  size: 18,
                  color: hayCuerpo ? ColoresVB.oroRosa : Colors.white54,
                ),
                const SizedBox(width: 8),
                Text(
                  hayCuerpo ? 'Cuerpo detectado' : 'Buscando el cuerpo…',
                  style: TextStyle(
                    color: hayCuerpo ? Colors.white : Colors.white70,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const Spacer(),
                Text(
                  '${_fps.toStringAsFixed(1)} fps',
                  style: const TextStyle(
                    color: Colors.white70,
                    fontFamily: 'monospace',
                    fontSize: 12,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            if (_cargandoPrendas)
              const Text('Cargando prendas…',
                  style: TextStyle(color: Colors.white70, fontSize: 13))
            else if (_prendas.isEmpty)
              const Text(
                'Ninguna prenda del catálogo tiene su PNG para el vestidor.',
                style: TextStyle(color: Colors.white70, fontSize: 13),
              )
            else
              Row(
                children: [
                  const Icon(Icons.checkroom, size: 16, color: Colors.white54),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _prendaElegida?.nombre ?? _nombreSuelto ?? '—',
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                    ),
                  ),
                  TextButton(
                    onPressed: _abrirSelector,
                    child: const Text('Cambiar'),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }

  void _abrirSelector() {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: ColoresVB.marfil,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(radioVB)),
      ),
      builder: (_) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 18, 20, 8),
              child: Text(
                'Prendas que se pueden probar',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: ColoresVB.malvaOscuro,
                ),
              ),
            ),
            for (final p in _prendas)
              ListTile(
                title: Text(p.nombre),
                subtitle: Text(p.codigo,
                    style: const TextStyle(fontSize: 12, fontFamily: 'monospace')),
                trailing: p.id == _prendaElegida?.id
                    ? const Icon(Icons.check, color: ColoresVB.malva)
                    : null,
                onTap: () {
                  Navigator.of(context).pop();
                  _elegirPrenda(p);
                },
              ),
          ],
        ),
      ),
    );
  }
}
