/// CU-37 · Probarse una prenda con su talla real — PantallaProbador (móvil).
/// CU-38 · Generar foto realista de la prueba (botón de esta misma pantalla).
///
/// LA DIFERENCIA CON LA WEB
/// ------------------------
/// En la web el cliente sube una foto fija y la prenda se dibuja encima. En el
/// teléfono la cámara está EN VIVO: ML Kit detecta los hombros en cada
/// fotograma y la prenda calibrada por el administrador (CU-36) se dibuja a su
/// tamaño real, siguiendo a la persona mientras se mueve. La cuenta de la
/// escala es la misma de la web (ver `pintor_talla_real.dart`).
///
/// LA DIFERENCIA CON EL VESTIDOR DEL PRIMER PARCIAL
/// ------------------------------------------------
/// El vestidor viejo (`features/vestidor`) estira la prenda hasta que calza el
/// cuerpo y le aplica factores. Acá la prenda NO se acomoda: los centímetros de
/// la talla mandan. Una S en un cuerpo de L se ve chica, que es lo que el
/// cliente necesita ver antes de comprar.
///
/// PRIVACIDAD (RNF14)
/// ------------------
/// La cámara y la detección corren en el teléfono: no se sube nada para
/// probarse. Solo si el cliente pide la foto realista (CU-38) se manda la
/// composición, y se descuenta del cupo mensual de la tienda.
library;

import 'dart:async';
import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../core/red/excepciones.dart';
import '../../core/tema.dart';
import '../../data/repositorios/repositorio_catalogo.dart';
import '../../data/repositorios/repositorio_medidas.dart';
import '../../data/repositorios/repositorio_probador.dart';
import '../auth/estado_sesion.dart';
import '../vestidor/pantalla_medidas.dart';
import 'pintor_talla_real.dart';

class PantallaProbadorTalla extends ConsumerStatefulWidget {
  const PantallaProbadorTalla({super.key, required this.productoId});

  final int productoId;

  @override
  ConsumerState<PantallaProbadorTalla> createState() => _EstadoProbadorTalla();
}

class _EstadoProbadorTalla extends ConsumerState<PantallaProbadorTalla>
    with WidgetsBindingObserver {
  // --- cámara y pose (la misma técnica del vestidor del primer parcial) ------
  CameraController? _camara;
  PoseDetector? _detector;
  List<CameraDescription> _camaras = const [];
  bool _usandoFrontal = true;
  bool _iniciandoCamara = true;
  String? _errorCamara;
  bool _ocupado = false;
  Size? _tamanoImagen;
  bool _hayCuerpo = false;
  int _sinCuerpo = 0;
  static const int _fotogramasDeGracia = 6;
  final Map<PoseLandmarkType, Offset> _suave = {};
  static const double _suavizado = 0.35;
  int _fotogramas = 0;
  double _fps = 0;
  DateTime _ultimoCorte = DateTime.now();

  // --- la prueba ------------------------------------------------------------
  RepositorioProbador get _repo => RepositorioProbador(ref.read(clienteApiProvider));
  PruebaDeProducto? _prueba;
  bool _cargando = true;
  String? _error;
  PrendaCalibrada? _elegida;
  ui.Image? _imagen;
  String? _urlDecodificada;
  final Map<String, ui.Image> _cache = {};

  // --- guardar y foto realista ------------------------------------------------
  final GlobalKey _lienzo = GlobalKey();
  SesionProbador? _sesion;
  bool _guardando = false;
  bool _generando = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _cargar();
    _arrancarCamara();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _camara?.dispose();
    _detector?.close();
    for (final img in _cache.values) {
      img.dispose();
    }
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState estado) {
    final camara = _camara;
    if (camara == null || !camara.value.isInitialized) return;
    if (estado == AppLifecycleState.inactive) {
      camara.dispose();
      _camara = null;
    } else if (estado == AppLifecycleState.resumed) {
      _arrancarCamara();
    }
  }

  // =========================================================================
  // Datos
  // =========================================================================

  Future<void> _cargar() async {
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      final prueba = await _repo.prueba(widget.productoId);
      if (!mounted) return;
      PrendaCalibrada? elegida = _elegida == null
          ? null
          : prueba.prendas.where((p) => p.varianteId == _elegida!.varianteId).firstOrNull;
      // La talla recomendada primero: es la que el cliente quiere ver.
      elegida ??= prueba.prendas
          .where((p) => p.tallaId == prueba.ajuste.tallaRecomendadaId)
          .firstOrNull;
      elegida ??= prueba.prendas.firstOrNull;
      setState(() {
        _prueba = prueba;
        _cargando = false;
        if (prueba.prendas.isEmpty) {
          _error = 'Esta prenda todavía no está preparada para el probador.';
        }
      });
      if (elegida != null) _ponerse(elegida);
    } on ErrorApi catch (e) {
      if (!mounted) return;
      setState(() {
        _cargando = false;
        _error = e.mensaje;
      });
    }
  }

  void _ponerse(PrendaCalibrada prenda) {
    setState(() {
      _elegida = prenda;
      _sesion = null; // otra talla u otro color es otra prueba
    });
    _decodificar(RepositorioCatalogo.urlDeImagen(prenda.imagenUrl) ?? prenda.imagenUrl);
  }

  /// Baja el PNG sin fondo y lo decodifica una vez (se reusa en cada fotograma
  /// y al volver a elegir la misma variante).
  Future<void> _decodificar(String url) async {
    final guardada = _cache[url];
    if (guardada != null) {
      setState(() {
        _imagen = guardada;
        _urlDecodificada = url;
      });
      return;
    }
    try {
      final flujo = NetworkImage(url).resolve(const ImageConfiguration());
      final completado = Completer<ui.Image>();
      late ImageStreamListener oyente;
      oyente = ImageStreamListener(
        (info, _) {
          if (!completado.isCompleted) completado.complete(info.image.clone());
          flujo.removeListener(oyente);
        },
        onError: (e, _) {
          if (!completado.isCompleted) completado.completeError(e);
          flujo.removeListener(oyente);
        },
      );
      flujo.addListener(oyente);
      final imagen = await completado.future;
      if (!mounted) {
        imagen.dispose();
        return;
      }
      setState(() {
        _cache[url] = imagen;
        if (RepositorioCatalogo.urlDeImagen(_elegida?.imagenUrl) == url ||
            _elegida?.imagenUrl == url) {
          _imagen = imagen;
          _urlDecodificada = url;
        }
      });
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No se pudo cargar la imagen de la prenda.')),
      );
    }
  }

  AjusteDeTalla? get _ajusteDeLaElegida {
    final p = _prueba;
    final e = _elegida;
    if (p == null || e == null || !p.ajuste.sirve) return null;
    return p.ajuste.de(e.tallaId);
  }

  // =========================================================================
  // Cámara y detección de pose
  // =========================================================================

  Future<void> _arrancarCamara() async {
    setState(() {
      _iniciandoCamara = true;
      _errorCamara = null;
    });
    final permiso = await Permission.camera.request();
    if (!permiso.isGranted) {
      if (!mounted) return;
      setState(() {
        _iniciandoCamara = false;
        _errorCamara = permiso.isPermanentlyDenied
            ? 'El permiso de cámara está denegado. Habilitalo en los ajustes del teléfono.'
            : 'Sin permiso de cámara no se puede usar el probador.';
      });
      return;
    }
    try {
      _camaras = await availableCameras();
      final buscada = _usandoFrontal ? CameraLensDirection.front : CameraLensDirection.back;
      final elegida = _camaras.firstWhere(
        (c) => c.lensDirection == buscada,
        orElse: () => _camaras.first,
      );
      _usandoFrontal = elegida.lensDirection == CameraLensDirection.front;
      final control = CameraController(
        elegida,
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.nv21,
      );
      await control.initialize();
      _detector ??= PoseDetector(
        options: PoseDetectorOptions(mode: PoseDetectionMode.stream),
      );
      await control.startImageStream(_alLlegarFotograma);
      if (!mounted) {
        await control.dispose();
        return;
      }
      setState(() {
        _camara = control;
        _iniciandoCamara = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _iniciandoCamara = false;
        _errorCamara = 'No se pudo abrir la cámara: $e';
      });
    }
  }

  Future<void> _alLlegarFotograma(CameraImage imagen) async {
    if (_ocupado || _detector == null || _camara == null) return;
    _ocupado = true;
    try {
      final rotacion = InputImageRotationValue.fromRawValue(
        _camara!.description.sensorOrientation,
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
      final vertical = rotacion == InputImageRotation.rotation90deg ||
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
      final pose = poses.isEmpty ? null : poses.first;
      setState(() {
        _tamanoImagen = tamano;
        if (pose != null && _suavizar(pose)) {
          _sinCuerpo = 0;
          _hayCuerpo = true;
        } else if (_sinCuerpo < _fotogramasDeGracia) {
          _sinCuerpo++;
        } else {
          _hayCuerpo = false;
          _suave.clear();
        }
      });
    } catch (_) {
      // Un fotograma perdido no es un error: llega otro enseguida.
    } finally {
      _ocupado = false;
    }
  }

  /// Promedio exponencial de los hombros: sin esto la prenda tiembla.
  /// Devuelve `false` si en este fotograma no se ven los dos hombros.
  bool _suavizar(Pose pose) {
    var vistos = 0;
    for (final tipo in const [PoseLandmarkType.leftShoulder, PoseLandmarkType.rightShoulder]) {
      final punto = pose.landmarks[tipo];
      if (punto == null || punto.likelihood < 0.5) continue;
      vistos++;
      final crudo = Offset(punto.x, punto.y);
      final anterior = _suave[tipo];
      if (anterior == null) {
        _suave[tipo] = crudo;
        continue;
      }
      final salto = (crudo - anterior).distance;
      final peso = salto > 60 ? 1.0 : _suavizado;
      _suave[tipo] = anterior + (crudo - anterior) * peso;
    }
    return vistos == 2;
  }

  Future<void> _cambiarCamara() async {
    final anterior = _camara;
    setState(() {
      _camara = null;
      _iniciandoCamara = true;
      _usandoFrontal = !_usandoFrontal;
      _hayCuerpo = false;
      _suave.clear();
    });
    await anterior?.dispose();
    await _arrancarCamara();
  }

  /// Los hombros en coordenadas de PANTALLA, ordenados por su x.
  (Offset, Offset)? _hombrosEnPantalla(Size caja) {
    final img = _tamanoImagen;
    final hi = _suave[PoseLandmarkType.leftShoulder];
    final hd = _suave[PoseLandmarkType.rightShoulder];
    if (img == null || hi == null || hd == null || !_hayCuerpo) return null;
    // La misma geometría del BoxFit.cover de la vista de la cámara.
    final escala = math.max(caja.width / img.width, caja.height / img.height);
    final dx = (caja.width - img.width * escala) / 2;
    final dy = (caja.height - img.height * escala) / 2;
    // El espejo es solo de la cámara frontal.
    Offset aPantalla(Offset p) => Offset(
      dx + (_usandoFrontal ? (img.width - p.dx) : p.dx) * escala,
      dy + p.dy * escala,
    );
    final a = aPantalla(hi);
    final b = aPantalla(hd);
    return a.dx <= b.dx ? (a, b) : (b, a);
  }

  // =========================================================================
  // Guardar la prueba y la foto realista
  // =========================================================================

  Future<void> _guardarPrueba() async {
    final prenda = _elegida;
    if (prenda == null || _guardando) return;
    setState(() => _guardando = true);
    try {
      final s = await _repo.registrar(prenda.varianteId);
      if (!mounted) return;
      setState(() => _sesion = s);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Prueba guardada en «Mis pruebas».')),
      );
    } on ErrorApi catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.mensaje)));
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  /// Captura la composición (cámara + prenda a escala, sin los botones).
  Future<Uint8List> _composicion() async {
    final limite = _lienzo.currentContext?.findRenderObject() as RenderRepaintBoundary?;
    if (limite == null) throw StateError('la vista todavía no está pintada');
    // 1.5 alcanza para la IA y no infla la subida.
    final imagen = await limite.toImage(pixelRatio: 1.5);
    final datos = await imagen.toByteData(format: ui.ImageByteFormat.png);
    imagen.dispose();
    if (datos == null) throw StateError('no se pudo codificar la composición');
    return datos.buffer.asUint8List();
  }

  Future<void> _generarFoto() async {
    final prenda = _elegida;
    if (prenda == null || _generando) return;
    setState(() => _generando = true);
    try {
      final composicion = await _composicion();
      var sesion = _sesion;
      if (sesion == null || sesion.fotoUrl != null) {
        sesion = await _repo.registrar(prenda.varianteId);
      }
      final conFoto = await _repo.generarFoto(sesion.id, composicion);
      if (!mounted) return;
      setState(() => _sesion = conFoto);
      await _mostrarFoto(conFoto);
      unawaited(_cargar()); // el cupo pudo agotarse
    } on ErrorApi catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.mensaje)));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No se pudo generar la foto: $e')),
      );
    } finally {
      if (mounted) setState(() => _generando = false);
    }
  }

  Future<void> _mostrarFoto(SesionProbador s) {
    final url = RepositorioCatalogo.urlDeImagen(s.fotoUrl) ?? s.fotoUrl;
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: ColoresVB.marfil,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(radioVB)),
      ),
      builder: (hoja) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '${s.producto} · talla ${s.talla} · ${s.color}',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: ColoresVB.malvaOscuro,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 4),
              Text(s.origenDeLaFoto, style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: 12),
              if (url != null)
                ClipRRect(
                  borderRadius: BorderRadius.circular(radioVB),
                  child: ConstrainedBox(
                    constraints: BoxConstraints(
                      maxHeight: MediaQuery.of(context).size.height * 0.6,
                    ),
                    child: Image.network(url, fit: BoxFit.contain),
                  ),
                ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: () => Navigator.of(hoja).pop(),
                  child: const Text('Listo'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _abrirMedidas() async {
    final guardadas = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => const PantallaMedidas()),
    );
    if (guardadas == true && mounted) await _cargar();
  }

  Future<void> _abrirMisPruebas() async {
    List<SesionProbador> lista;
    try {
      lista = (await _repo.misPruebas())
          .where((s) => s.productoId == widget.productoId)
          .toList();
    } on ErrorApi catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.mensaje)));
      return;
    }
    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: ColoresVB.marfil,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(radioVB)),
      ),
      builder: (hoja) => StatefulBuilder(
        builder: (hoja, refrescar) => SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Mis pruebas de esta prenda',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: ColoresVB.malvaOscuro,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 8),
                if (lista.isEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 16),
                    child: Text('Todavía no guardaste ninguna prueba de esta prenda.'),
                  ),
                for (final s in lista)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(
                      s.fotoUrl == null ? Icons.checkroom : Icons.auto_awesome,
                      color: ColoresVB.malvaOscuro,
                    ),
                    title: Text('Talla ${s.talla} · ${s.color}'),
                    subtitle: Text(
                      [
                        _fecha(s.creadoEn),
                        if (s.tallaRecomendada != null) 'te va la ${s.tallaRecomendada}',
                      ].join(' · '),
                    ),
                    onTap: s.fotoUrl == null ? null : () => _mostrarFoto(s),
                    trailing: IconButton(
                      tooltip: 'Borrar',
                      icon: const Icon(Icons.delete_outline),
                      onPressed: () async {
                        try {
                          await _repo.borrar(s.id);
                          refrescar(() => lista.remove(s));
                        } on ErrorApi catch (e) {
                          if (!hoja.mounted) return;
                          ScaffoldMessenger.of(hoja).showSnackBar(
                            SnackBar(content: Text(e.mensaje)),
                          );
                        }
                      },
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  static String _fecha(DateTime f) =>
      '${f.day.toString().padLeft(2, '0')}/${f.month.toString().padLeft(2, '0')} '
      '${f.hour.toString().padLeft(2, '0')}:${f.minute.toString().padLeft(2, '0')}';

  // =========================================================================
  // Pantalla
  // =========================================================================

  @override
  Widget build(BuildContext context) {
    final dosCamaras = _camaras.map((c) => c.lensDirection).toSet().length > 1;
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: Text(_prueba?.nombre ?? 'Probador'),
        actions: [
          if (dosCamaras)
            IconButton(
              tooltip: _usandoFrontal ? 'Usar la cámara trasera' : 'Usar la cámara frontal',
              icon: Icon(_usandoFrontal ? Icons.camera_rear_outlined : Icons.camera_front_outlined),
              onPressed: _iniciandoCamara ? null : _cambiarCamara,
            ),
          IconButton(
            tooltip: 'Mis pruebas',
            icon: const Icon(Icons.photo_library_outlined),
            onPressed: _abrirMisPruebas,
          ),
        ],
      ),
      body: _cuerpo(),
    );
  }

  Widget _cuerpo() {
    if (_cargando && _prueba == null) {
      return const Center(child: CircularProgressIndicator(color: Colors.white));
    }
    if (_error != null) {
      return _mensaje(Icons.checkroom, _error!, accion: ('Reintentar', _cargar));
    }
    if (_iniciandoCamara) {
      return const Center(child: CircularProgressIndicator(color: Colors.white));
    }
    if (_errorCamara != null) {
      return _mensaje(Icons.videocam_off, _errorCamara!, accion: ('Reintentar', _arrancarCamara));
    }
    final camara = _camara;
    if (camara == null || !camara.value.isInitialized) {
      return _mensaje(Icons.videocam_off, 'Cámara no disponible.');
    }

    return LayoutBuilder(
      builder: (context, limites) {
        final caja = Size(limites.maxWidth, limites.maxHeight);
        final hombros = _hombrosEnPantalla(caja);
        final imagen = _imagen;
        final prenda = _elegida;
        final ajuste = _ajusteDeLaElegida;
        return Stack(
          fit: StackFit.expand,
          children: [
            // Lo que va en la composición del CU-38: cámara y prenda, sin botones.
            RepaintBoundary(
              key: _lienzo,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  FittedBox(
                    fit: BoxFit.cover,
                    child: SizedBox(
                      width: camara.value.previewSize?.height ?? caja.width,
                      height: camara.value.previewSize?.width ?? caja.height,
                      child: CameraPreview(camara),
                    ),
                  ),
                  if (hombros != null && imagen != null && prenda != null && _urlDecodificada != null)
                    Positioned.fill(
                      child: IgnorePointer(
                        child: CustomPaint(
                          painter: PintorTallaReal(
                            prenda: imagen,
                            puntos: prenda.puntos,
                            hombroA: hombros.$1,
                            hombroB: hombros.$2,
                            bustoClienteCm: _prueba?.bustoCm,
                            bustoTallaCm: ajuste?.bustoCm,
                            largoTallaCm: ajuste?.largoCm,
                          ),
                        ),
                      ),
                    )
                  else if (hombros != null)
                    Positioned.fill(
                      child: IgnorePointer(
                        child: CustomPaint(painter: PintorHombros(hombros.$1, hombros.$2)),
                      ),
                    ),
                ],
              ),
            ),
            _panel(hombros != null),
          ],
        );
      },
    );
  }

  Widget _mensaje(IconData icono, String texto, {(String, Future<void> Function())? accion}) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icono, size: 48, color: Colors.white54),
            const SizedBox(height: 16),
            Text(
              texto,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white, height: 1.5),
            ),
            if (accion != null) ...[
              const SizedBox(height: 20),
              FilledButton(onPressed: accion.$2, child: Text(accion.$1)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _panel(bool hayCuerpo) {
    final prueba = _prueba;
    return Positioned(
      left: 0,
      right: 0,
      bottom: 0,
      child: Container(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 22),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Colors.transparent, Colors.black.withValues(alpha: 0.82)],
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
                Expanded(
                  child: Text(
                    hayCuerpo
                        ? 'Hombros detectados'
                        : 'Ponete de frente, a un par de metros, que se vean tus hombros',
                    style: TextStyle(
                      color: hayCuerpo ? Colors.white : Colors.white70,
                      fontWeight: FontWeight.w600,
                      fontSize: 12.5,
                    ),
                  ),
                ),
                Text(
                  '${_fps.toStringAsFixed(1)} fps',
                  style: const TextStyle(color: Colors.white54, fontFamily: 'monospace', fontSize: 11),
                ),
              ],
            ),
            const SizedBox(height: 6),
            _escala(),
            if (prueba != null) _selector(prueba),
            const SizedBox(height: 10),
            _acciones(hayCuerpo, prueba),
          ],
        ),
      ),
    );
  }

  /// A escala real, o aproximado con la invitación a cargar las medidas.
  Widget _escala() {
    if (_prueba?.bustoCm == null) {
      return Row(
        children: [
          const Icon(Icons.straighten, size: 15, color: Color(0xFFFFC46B)),
          const SizedBox(width: 8),
          const Expanded(
            child: Text(
              'Tamaño aproximado: cargá tus medidas para verla a escala real.',
              style: TextStyle(color: Color(0xFFFFC46B), fontSize: 12),
            ),
          ),
          TextButton(onPressed: _abrirMedidas, child: const Text('Cargar')),
        ],
      );
    }
    final ajuste = _ajusteDeLaElegida;
    if (ajuste == null) {
      return const Text(
        'Esta talla no tiene medidas cargadas: se ve a tamaño aproximado.',
        style: TextStyle(color: Colors.white70, fontSize: 12),
      );
    }
    final color = switch (ajuste.ajuste) {
      Ajuste.noEntra => const Color(0xFFFF6B6B),
      Ajuste.aTuMedida => const Color(0xFF7BD88F),
      _ => const Color(0xFFFFC46B),
    };
    final recomendada = _prueba?.ajuste.tallaRecomendada;
    final texto = recomendada == null || recomendada == ajuste.codigo
        ? ajuste.ajuste.texto
        : '${ajuste.ajuste.texto} · te va la $recomendada';
    return Row(
      children: [
        Icon(
          ajuste.ajuste == Ajuste.aTuMedida ? Icons.check_circle : Icons.info_outline,
          size: 15,
          color: color,
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            '$texto · a escala real (${ajuste.bustoCm.toStringAsFixed(0)} cm de busto, '
            '${ajuste.largoCm.toStringAsFixed(0)} cm de largo)',
            style: TextStyle(color: color, fontSize: 12),
          ),
        ),
      ],
    );
  }

  /// Talla y color en vivo: primero la talla, después los colores de esa talla.
  Widget _selector(PruebaDeProducto prueba) {
    final tallas = <int, String>{};
    for (final p in prueba.prendas) {
      tallas[p.tallaId] = p.talla;
    }
    final elegida = _elegida;
    final colores = prueba.prendas.where((p) => p.tallaId == elegida?.tallaId).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 8),
        SizedBox(
          height: 34,
          child: ListView(
            scrollDirection: Axis.horizontal,
            children: [
              for (final t in tallas.entries)
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text(
                      t.key == prueba.ajuste.tallaRecomendadaId ? '${t.value} ★' : t.value,
                    ),
                    selected: elegida?.tallaId == t.key,
                    onSelected: (_) {
                      final mismoColor = prueba.prendas
                          .where((p) => p.tallaId == t.key && p.colorId == elegida?.colorId)
                          .firstOrNull;
                      _ponerse(mismoColor ?? prueba.prendas.firstWhere((p) => p.tallaId == t.key));
                    },
                  ),
                ),
            ],
          ),
        ),
        if (colores.length > 1)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: SizedBox(
              height: 32,
              child: ListView(
                scrollDirection: Axis.horizontal,
                children: [
                  for (final c in colores)
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        label: Text(c.color),
                        selected: c.varianteId == elegida?.varianteId,
                        onSelected: (_) => _ponerse(c),
                      ),
                    ),
                ],
              ),
            ),
          ),
      ],
    );
  }

  Widget _acciones(bool hayCuerpo, PruebaDeProducto? prueba) {
    final puesta = hayCuerpo && _elegida != null && _imagen != null;
    final fotoIa = prueba?.fotoIa;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(foregroundColor: Colors.white),
                icon: _guardando
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                    : Icon(_sesion == null ? Icons.bookmark_add_outlined : Icons.bookmark_added),
                label: Text(_sesion == null ? 'Guardar prueba' : 'Guardada'),
                onPressed: (puesta && _sesion == null && !_guardando) ? _guardarPrueba : null,
              ),
            ),
            if (fotoIa?.disponible ?? false) ...[
              const SizedBox(width: 10),
              Expanded(
                child: FilledButton.icon(
                  icon: _generando
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.auto_awesome),
                  label: Text(_generando ? 'Generando…' : 'Foto realista'),
                  onPressed: (puesta && !_generando) ? _generarFoto : null,
                ),
              ),
            ],
          ],
        ),
        if (_generando)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(
              'Puede tardar unos ${fotoIa?.demora ?? 15} segundos…',
              style: const TextStyle(color: Colors.white70, fontSize: 11.5),
            ),
          )
        else if (fotoIa != null && !fotoIa.disponible && fotoIa.motivo != null)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(
              'Foto realista: ${fotoIa.motivo}',
              style: const TextStyle(color: Colors.white54, fontSize: 11.5),
            ),
          ),
      ],
    );
  }
}
