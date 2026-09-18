/// CU-21 · Utilizar vestidor virtual (RA).  RF13.
///
/// Nacio como el prototipo de riesgo I3, que existia para contestar UNA
/// pregunta antes del Ciclo 3: ¿se puede detectar la pose en este telefono, a
/// una velocidad usable, y poner la prenda encima siguiendo al que se mueve?
/// La respuesta fue que si, y el 18/09 se completo hasta ser el caso de uso.
///
/// Lo que hace:
///   - abre la camara frontal y corre la deteccion de pose sobre sus fotogramas
///   - superpone el PNG transparente de una variante real, tomado del catalogo
///   - lo escala, lo ubica y lo rota siguiendo los hombros y la cadera
///   - **cambia talla y color en vivo**, sin volver a pedir nada al servidor
///   - **captura** lo que se ve y lo guarda en el telefono
///   - **deriva al carrito o a la reserva** desde la propia captura
///   - informa cuantos fotogramas por segundo esta procesando
///
/// LOS FOTOGRAMAS POR SEGUNDO NO SON UN ADORNO DE DESARROLLO
/// ----------------------------------------------------------
/// Son el dato que el prototipo existia para medir, y se dejan a la vista: si
/// la deteccion no llega a un ritmo usable en el telefono de la defensa, eso
/// se tiene que ver mientras se demuestra y no descubrirse despues.
///
/// LO QUE SIGUE SIN HACER, Y ES DELIBERADO
/// ----------------------------------------
/// No ajusta la prenda a la profundidad ni a la rotacion del torso: es un
/// recorte plano que sigue hombros y cadera. Para eso esta la opcion de
/// «amoldar» por IA, que es otro camino y no parte del flujo obligatorio.
///
/// POR QUE NO SE PUEDE PROBAR EN EMULADOR
/// -------------------------------------
/// `google_mlkit_pose_detection` corre sobre los fotogramas de la camara y un
/// emulador entrega una camara sintetica --- una imagen de prueba que no tiene
/// cuerpo que detectar. Esta pantalla solo dice algo en un telefono de verdad.
library;

import 'dart:async';
import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../core/enrutado/router.dart';
import '../../core/tema.dart';
import '../../data/modelos/catalogo.dart';
import '../../data/repositorios/repositorio_catalogo.dart';
import '../../data/repositorios/repositorio_medidas.dart';
import '../../data/repositorios/repositorio_vestidor.dart';
import '../auth/estado_sesion.dart';
import '../catalogo/estado_catalogo.dart';
import '../compra/estado_compra.dart';
import 'pantalla_medidas.dart';
import 'pintor_prenda.dart';

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

  /// Las camaras del telefono y cual se esta usando.
  ///
  /// La FRONTAL es la que sirve para probarse solo: se ve la pantalla mientras
  /// se mueve. La TRASERA es mejor sensor en casi todos los telefonos y es la
  /// que corresponde cuando alguien mas sostiene el aparato --- que es como se
  /// va a demostrar ---, asi que se ofrecen las dos.
  List<CameraDescription> _camaras = const [];
  bool _usandoFrontal = true;

  bool _iniciando = true;
  String? _error;

  /// El detector procesa un fotograma por vez. Sin esta bandera, la camara
  /// encola fotogramas mas rapido de lo que ML Kit los resuelve y la memoria
  /// crece hasta que el sistema mata la aplicacion.
  bool _ocupado = false;

  Pose? _pose;
  Size? _tamanoImagen;

  /// Los puntos del torso SUAVIZADOS, en coordenadas de la imagen.
  ///
  /// POR QUE HACE FALTA
  /// ------------------
  /// La deteccion devuelve puntos con ruido: de un fotograma al siguiente un
  /// hombro se mueve varios pixeles aunque la persona este quieta. A 10 fps
  /// eso se ve como si la prenda temblara y «descuadrara», y es lo que mas
  /// delata que esta pegada encima en vez de puesta.
  ///
  /// Se aplica un promedio exponencial: cada punto nuevo pesa [_suavizado] y
  /// el anterior el resto. No hay forma de tener las dos cosas --- responder
  /// rapido y no temblar --- asi que el valor es un equilibrio, medido en el
  /// telefono.
  final Map<PoseLandmarkType, Offset> _suave = {};

  /// Cuanto pesa el punto nuevo. Mas bajo = mas estable y mas lento.
  static const double _suavizado = 0.35;

  /// Cuantos fotogramas se sigue mostrando la prenda despues de perder el
  /// cuerpo. Sin esto, un parpadeo de la deteccion ---que pasa seguido cuando
  /// la persona mueve los brazos--- hace desaparecer la prenda y volver, que
  /// se ve peor que dejarla un instante donde estaba.
  static const int _fotogramasDeGracia = 6;
  int _sinCuerpo = 0;

  int _fotogramas = 0;
  double _fps = 0;
  DateTime _ultimoCorte = DateTime.now();

  // --- la prenda -----------------------------------------------------------
  List<ProductoVitrina> _prendas = const [];
  ProductoVitrina? _prendaElegida;
  String? _urlPrenda;

  /// La ficha completa de la prenda puesta. Se guarda ENTERA y no solo la URL
  /// porque CU-21 pide cambiar talla y color EN VIVO: para ofrecer las
  /// opciones hay que tener todas las variantes a mano, y volver a pedir la
  /// ficha en cada cambio dejaria la camara esperando a la red.
  FichaPrenda? _ficha;
  VariantePrenda? _variante;

  /// Como le queda cada talla de la prenda puesta a ESTE cliente (CU-21).
  ///
  /// Se pide una sola vez por prenda, junto con la ficha, y trae TODAS las
  /// tallas: cambiar de M a L no vuelve a hablar con el servidor, igual que el
  /// cambio de color.
  ///
  /// Cuando no sirve ---el cliente no cargo sus medidas, el producto no tiene
  /// tabla, o la consulta fallo--- vale `ninguno` y la prenda se dibuja como
  /// se dibujaba antes de que existieran las medidas.
  AjusteDeProducto _ajuste = AjusteDeProducto.ninguno;

  /// El ajuste de la talla puesta, o `null` si no hay.
  AjusteDeTalla? get _ajusteDeLaPuesta {
    final variante = _variante;
    if (variante == null || !_ajuste.sirve) return null;
    return _ajuste.de(variante.tallaId);
  }

  /// El PNG de la prenda YA DECODIFICADO.
  ///
  /// Hace falta como `ui.Image` y no como widget porque la malla lo usa de
  /// TEXTURA: `drawVertices` pinta triangulos leyendo pixeles de una imagen,
  /// y un `Image.network` no expone esos pixeles. Se decodifica una vez por
  /// prenda y se reusa en cada fotograma.
  ui.Image? _imagenPrenda;

  /// Para capturar lo que se ve. `RepaintBoundary` solo sabe pintarse a si
  /// mismo si tiene una llave con la que encontrarlo en el arbol.
  final GlobalKey _lienzo = GlobalKey();
  bool _capturando = false;

  /// Si el probado por IA esta habilitado en este entorno. Se pregunta UNA vez
  /// al abrir, y si es `false` el boton no se dibuja --- en vez de dibujarlo y
  /// fallar al tocarlo.
  bool _hayProbador = false;

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
      _decodificar(widget.urlInicial);
    }
    _cargarPrendas();
    _mirarSiHayProbador();
  }

  /// Pregunta si se puede ofrecer el «amoldar por IA».
  ///
  /// No bloquea nada ni corta el arranque: si la consulta falla, el vestidor
  /// abre igual y sin el boton. Es una comodidad opcional.
  Future<void> _mirarSiHayProbador() async {
    final hay = await RepositorioVestidor(
      ref.read(clienteApiProvider),
    ).hayProbador();
    if (mounted) setState(() => _hayProbador = hay);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _camara?.dispose();
    _detector?.close();
    _imagenPrenda?.dispose();
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
      _camaras = await availableCameras();
      final buscada = _usandoFrontal
          ? CameraLensDirection.front
          : CameraLensDirection.back;
      final elegida = _camaras.firstWhere(
        (c) => c.lensDirection == buscada,
        orElse: () => _camaras.first,
      );
      // Si el telefono no tiene la que se pidio, se deja constancia de cual
      // quedo: el espejo depende de esto, y suponerlo daria la prenda al reves.
      _usandoFrontal = elegida.lensDirection == CameraLensDirection.front;

      final control = CameraController(
        elegida,
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
      // El SERVIDOR filtra, no esta pantalla.
      //
      // Hasta el 17/09 se pedia la primera pagina de 48 y se filtraba aca por
      // `tieneVestidor`. Parecia razonable y tenia un defecto que no se veia:
      // con mas de 48 productos, las prendas probables que quedaran fuera de
      // esa pagina NO APARECIAN NUNCA --- medido sobre el conjunto de
      // demostracion, 10 de 32 ---. Y cuales quedaban fuera cambiaba al
      // agregar productos, asi que el defecto aparecia y desaparecia solo.
      //
      // `solo_vestidor` existe para esto. Ver
      // docs/entregas/ciclo-3/cu-21-cargar-prendas-del-vestidor.md.
      final pagina = await ref
          .read(repositorioCatalogoProvider)
          .listar(const ConsultaVitrina(tamano: 48, soloVestidor: true));
      final con = pagina.items;
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
      _ficha = null;
      _variante = null;
      // Se limpia YA y no al llegar la respuesta: si quedara el de la prenda
      // anterior, durante el viaje de red la prenda nueva se dibujaria con los
      // factores de otra --- una XS con el largo de un abrigo ---.
      _ajuste = AjusteDeProducto.ninguno;
    });
    try {
      // Las dos consultas van juntas: son independientes y encadenarlas
      // duplicaria la espera con la camara ya andando.
      final (ficha, ajuste) = await (
        ref.read(repositorioCatalogoProvider).obtenerFicha(prenda.id),
        RepositorioMedidas(ref.read(clienteApiProvider)).deProducto(prenda.id),
      ).wait;
      final probables = ficha.variantes.where((v) => v.sePuedeProbar).toList();
      if (!mounted) return;
      setState(() {
        _ficha = ficha;
        _ajuste = ajuste;
      });
      // Si hay una talla recomendada, se pone ESA. Hasta hoy se ponia siempre
      // la primera de la lista, que es la mas chica: al cliente le caia una XS
      // sin ningun motivo, y con la foto de una variante que ademas podia ser
      // una silueta dibujada en vez de la prenda real.
      final recomendada = _ajuste.tallaRecomendadaId;
      final elegida = recomendada == null
          ? null
          : probables.where((v) => v.tallaId == recomendada).firstOrNull;
      if (elegida != null) {
        _ponerse(elegida);
      } else if (probables.isNotEmpty) {
        _ponerse(probables.first);
      }
    } catch (_) {
      /* se queda sin prenda; el aviso lo da la pantalla */
    }
  }

  /// Cambia la variante puesta SIN volver a pedir nada al servidor.
  ///
  /// Es el «cambiar talla y color» que pide CU-21. La ficha ya trae el PNG de
  /// cada variante, asi que el cambio es instantaneo: lo unico que pasa es que
  /// el `Image.network` de la superposicion apunta a otra URL, y `Flutter` ya
  /// la tiene en cache si el cliente la probo antes.
  void _ponerse(VariantePrenda variante) {
    final url = RepositorioCatalogo.urlDeImagen(variante.imagenVestidorUrl);
    setState(() {
      _variante = variante;
      _urlPrenda = url;
    });
    _decodificar(url);
  }

  /// Baja el PNG y lo decodifica para poder usarlo de textura.
  ///
  /// La imagen anterior se libera: cada `ui.Image` retiene su mapa de bits en
  /// memoria de GPU, y cambiando de talla y de color varias veces se acumulan
  /// hasta que el sistema mata la aplicacion. Es el mismo cuidado que ya
  /// obligaba a soltar la camara al pasar a segundo plano.
  Future<void> _decodificar(String? url) async {
    if (url == null) {
      setState(() {
        _imagenPrenda?.dispose();
        _imagenPrenda = null;
      });
      return;
    }
    try {
      final flujo = NetworkImage(url).resolve(const ImageConfiguration());
      final completado = Completer<ui.Image>();
      late ImageStreamListener oyente;
      oyente = ImageStreamListener(
        (info, _) {
          if (!completado.isCompleted) completado.complete(info.image);
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
        _imagenPrenda?.dispose();
        _imagenPrenda = imagen;
      });
    } catch (_) {
      // Sin prenda decodificada la camara sigue andando y no se dibuja nada.
      // El aviso lo da la pantalla, que ya contempla no tener prenda.
    }
  }

  /// Las variantes que se pueden probar, sin repetir talla ni color vacios.
  List<VariantePrenda> get _probables =>
      _ficha?.variantes.where((v) => v.sePuedeProbar).toList() ?? const [];

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
      final nueva = poses.isEmpty ? null : poses.first;
      setState(() {
        _tamanoImagen = tamano;
        if (nueva != null) {
          _sinCuerpo = 0;
          _pose = nueva;
          _suavizar(nueva);
        } else if (_sinCuerpo < _fotogramasDeGracia) {
          // Parpadeo de la deteccion: se deja la prenda donde estaba.
          _sinCuerpo++;
        } else {
          _pose = null;
          _suave.clear();
        }
      });
    } catch (_) {
      /* un fotograma perdido no es un error: llega otro en 33 ms */
    } finally {
      _ocupado = false;
    }
  }

  /// Mezcla los puntos nuevos con los anteriores. Ver `_suave`.
  void _suavizar(Pose pose) {
    const interesan = [
      PoseLandmarkType.leftShoulder,
      PoseLandmarkType.rightShoulder,
      PoseLandmarkType.leftHip,
      PoseLandmarkType.rightHip,
    ];
    for (final tipo in interesan) {
      final punto = pose.landmarks[tipo];
      if (punto == null) continue;
      final crudo = Offset(punto.x, punto.y);
      final anterior = _suave[tipo];
      if (anterior == null) {
        _suave[tipo] = crudo;
        continue;
      }
      // Un salto grande NO se suaviza: es la persona moviendose de verdad, y
      // arrastrarlo haria que la prenda la siguiera con retraso visible. Solo
      // se suaviza el temblor chico, que es el ruido del detector.
      final salto = (crudo - anterior).distance;
      final peso = salto > 60 ? 1.0 : _suavizado;
      _suave[tipo] = anterior + (crudo - anterior) * peso;
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
          if (_hayDosCamaras)
            IconButton(
              tooltip: _usandoFrontal
                  ? 'Usar la cámara trasera'
                  : 'Usar la cámara frontal',
              icon: Icon(
                _usandoFrontal
                    ? Icons.camera_rear_outlined
                    : Icons.camera_front_outlined,
              ),
              onPressed: _iniciando ? null : _cambiarCamara,
            ),
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

  bool get _hayDosCamaras =>
      _camaras.map((c) => c.lensDirection).toSet().length > 1;

  /// Cambia entre la frontal y la trasera.
  ///
  /// Se suelta la camara anterior ANTES de abrir la otra: son un recurso
  /// exclusivo del sistema y abrir la segunda sin cerrar la primera falla en
  /// algunos telefonos. Y se limpia el suavizado, porque los puntos de la
  /// camara vieja ya no valen --- sin eso, la prenda viaja desde donde estaba
  /// hasta la posicion nueva, que se ve como un salto raro.
  Future<void> _cambiarCamara() async {
    final anterior = _camara;
    setState(() {
      _camara = null;
      _iniciando = true;
      _usandoFrontal = !_usandoFrontal;
      _pose = null;
      _suave.clear();
    });
    await anterior?.dispose();
    await _arrancar();
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
            // Lo que entra en la captura: la camara y la prenda, NO el panel.
            // El `RepaintBoundary` marca exactamente ese recorte; si envolviera
            // el Stack entero, la foto saldria con los botones encima.
            RepaintBoundary(
              key: _lienzo,
              child: Stack(
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
                ],
              ),
            ),

            _panel(),
          ],
        );
      },
    );
  }

  /// Dibuja la prenda DEFORMADA sobre el cuerpo.
  ///
  /// Lo unico que hace esta funcion es traducir la pose a coordenadas de
  /// pantalla; la deformacion la hace `PintorPrenda`, y el por que esta
  /// explicado alli.
  List<Widget> _prendaSobreElCuerpo(Size caja) {
    final img = _tamanoImagen!;
    final imagen = _imagenPrenda;
    // Mientras el PNG se decodifica no hay nada que dibujar. Dura un
    // fotograma o dos y solo pasa al cambiar de prenda.
    if (imagen == null) return const [];

    // Los SUAVIZADOS, no los crudos: ver `_suave`.
    final hi = _suave[PoseLandmarkType.leftShoulder];
    final hd = _suave[PoseLandmarkType.rightShoulder];
    if (hi == null || hd == null) return const [];

    final ci = _suave[PoseLandmarkType.leftHip];
    final cd = _suave[PoseLandmarkType.rightHip];

    // La misma geometria que usa el BoxFit.cover de la vista, para que la
    // prenda y el cuerpo queden en el mismo sistema de coordenadas.
    final escala = math.max(caja.width / img.width, caja.height / img.height);
    final dx = (caja.width - img.width * escala) / 2;
    final dy = (caja.height - img.height * escala) / 2;

    // EL ESPEJO ES SOLO DE LA FRONTAL.
    //
    // La camara frontal muestra la imagen reflejada --- es lo que espera quien
    // se mira ---, asi que hay que invertir la X o la prenda se mueve al reves
    // que la persona. La TRASERA no refleja: invertir ahi seria introducir el
    // defecto en vez de corregirlo.
    Offset aPantalla(double x, double y) => Offset(
      dx + (_usandoFrontal ? (img.width - x) : x) * escala,
      dy + y * escala,
    );

    final pHi = aPantalla(hi.dx, hi.dy);
    final pHd = aPantalla(hd.dx, hd.dy);

    // ORDENADOS POR SU X EN PANTALLA, no por su nombre anatomico.
    //
    // Es la misma correccion del 13/09 que ya se habia hecho para el angulo:
    // el espejo de la camara frontal invierte cual hombro cae a la izquierda,
    // y tomarlos por su nombre daba la prenda dada vuelta. Con la malla el
    // sintoma seria peor --- la textura sale reflejada ---, asi que el orden
    // se resuelve aca, una sola vez, y el pintor no tiene que saber nada del
    // espejo.
    final hombroA = pHi.dx <= pHd.dx ? pHi : pHd;
    final hombroB = pHi.dx <= pHd.dx ? pHd : pHi;

    Offset? caderaA;
    Offset? caderaB;
    if (ci != null && cd != null) {
      final pCi = aPantalla(ci.dx, ci.dy);
      final pCd = aPantalla(cd.dx, cd.dy);
      caderaA = pCi.dx <= pCd.dx ? pCi : pCd;
      caderaB = pCi.dx <= pCd.dx ? pCd : pCi;
    }

    return [
      Positioned.fill(
        child: IgnorePointer(
          child: CustomPaint(
            painter: PintorPrenda(
              prenda: imagen,
              // 1.0 cuando no hay medidas: se dibuja como siempre.
              factorAncho: _ajusteDeLaPuesta?.factorAncho ?? 1.0,
              factorLargo: _ajusteDeLaPuesta?.factorLargo ?? 1.0,
              torso: TorsoEnPantalla(
                hombroA: hombroA,
                hombroB: hombroB,
                caderaA: caderaA,
                caderaB: caderaB,
              ),
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
            else ...[
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
                    child: const Text('Otra prenda'),
                  ),
                ],
              ),
              _comoTeQueda(),
              // CU-21: cambiar talla y color EN VIVO, sin salir de la cámara.
              // Es medio caso de uso: probarse una prenda sin poder cambiar la
              // talla es mirar una foto.
              _selectorDeVariante(),
              const SizedBox(height: 10),
              _acciones(hayCuerpo),
            ],
          ],
        ),
      ),
    );
  }

  /// Abre el formulario de medidas y, si se guardaron, vuelve a pedir el
  /// ajuste de la prenda puesta.
  ///
  /// Se vuelve a pedir y no se supone nada: los factores y la talla
  /// recomendada los calcula el servidor, y dejarlos sin refrescar mostraria
  /// «cargá tus medidas» a alguien que las acaba de cargar.
  Future<void> _abrirMedidas() async {
    final guardadas = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => const PantallaMedidas()),
    );
    if (guardadas != true || !mounted) return;
    final prenda = _prendaElegida;
    if (prenda == null) return;
    final ajuste = await RepositorioMedidas(
      ref.read(clienteApiProvider),
    ).deProducto(prenda.id);
    if (!mounted) return;
    setState(() => _ajuste = ajuste);
  }

  /// Cómo le queda al cliente la talla que tiene puesta (CU-21).
  ///
  /// Es la mitad visible de las medidas: la otra mitad es que la prenda se
  /// DIBUJA distinta según la talla. Sin este cartel el cliente ve que la XS
  /// es más chica pero no sabe si eso significa que no le entra.
  ///
  /// Cuando no hay medidas cargadas no se calla: ofrece cargarlas. Un probador
  /// que puede decirte tu talla y no lo menciona es una función que nadie
  /// encuentra.
  Widget _comoTeQueda() {
    if (!_ajuste.hayTabla) return const SizedBox.shrink();

    if (!_ajuste.hayMedidas) {
      return Padding(
        padding: const EdgeInsets.only(top: 6),
        child: Row(
          children: [
            const Icon(Icons.straighten, size: 15, color: Colors.white54),
            const SizedBox(width: 8),
            const Expanded(
              child: Text(
                'Cargá tus medidas y te digo qué talla te va.',
                style: TextStyle(color: Colors.white70, fontSize: 12),
              ),
            ),
            TextButton(
              onPressed: _abrirMedidas,
              child: const Text('Cargar'),
            ),
          ],
        ),
      );
    }

    final ajuste = _ajusteDeLaPuesta;
    if (ajuste == null) return const SizedBox.shrink();

    // El color dice lo mismo que el texto, para que se lea de un vistazo sobre
    // el video: rojo no entra, ámbar apretada o suelta, verde te queda bien.
    final color = switch (ajuste.ajuste) {
      Ajuste.noEntra => const Color(0xFFFF6B6B),
      Ajuste.aTuMedida => const Color(0xFF7BD88F),
      _ => const Color(0xFFFFC46B),
    };
    final recomendada = _ajuste.tallaRecomendada;
    final esLaRecomendada = ajuste.codigo == recomendada;

    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Row(
        children: [
          Icon(
            ajuste.ajuste == Ajuste.aTuMedida
                ? Icons.check_circle
                : Icons.info_outline,
            size: 15,
            color: color,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              esLaRecomendada || recomendada == null
                  ? ajuste.ajuste.texto
                  : '${ajuste.ajuste.texto} · te va la $recomendada',
              overflow: TextOverflow.ellipsis,
              style: TextStyle(color: color, fontSize: 12.5),
            ),
          ),
        ],
      ),
    );
  }

  /// Las tallas y los colores que se pueden probar, en fila y sobre la cámara.
  ///
  /// Solo se ofrecen las variantes que TIENEN PNG de vestidor: una talla sin
  /// activo no se puede probar, y ofrecerla sería prometer algo que al tocarlo
  /// no pasa nada. Las que faltan se ven en la ficha, no acá.
  Widget _selectorDeVariante() {
    final probables = _probables;
    if (probables.isEmpty) return const SizedBox.shrink();

    // Una fila por talla, y dentro los colores de esa talla. Agrupar así —y no
    // una lista plana de variantes— es como la persona piensa: primero «cuál
    // es mi talla» y después «de qué color».
    final tallas = <String, List<VariantePrenda>>{};
    for (final v in probables) {
      tallas.putIfAbsent(v.tallaCodigo ?? '—', () => []).add(v);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 10),
        SizedBox(
          height: 34,
          child: ListView(
            scrollDirection: Axis.horizontal,
            children: [
              for (final entrada in tallas.entries)
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: _Ficha(
                    texto: entrada.key,
                    activa: _variante?.tallaCodigo == entrada.key,
                    alTocar: () => _ponerse(entrada.value.first),
                  ),
                ),
            ],
          ),
        ),
        if (_variante != null)
          Builder(
            builder: (_) {
              final delMismoTalle = tallas[_variante!.tallaCodigo ?? '—'] ?? [];
              if (delMismoTalle.length < 2) return const SizedBox.shrink();
              return Padding(
                padding: const EdgeInsets.only(top: 8),
                child: SizedBox(
                  height: 30,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    children: [
                      for (final v in delMismoTalle)
                        Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: _Punto(
                            hex: v.colorHexadecimal,
                            nombre: v.colorNombre ?? '',
                            activo: v.id == _variante!.id,
                            alTocar: () => _ponerse(v),
                          ),
                        ),
                    ],
                  ),
                ),
              );
            },
          ),
      ],
    );
  }

  /// Capturar y llevarse la prenda. Los dos pasos que le faltaban a CU-21.
  Widget _acciones(bool hayCuerpo) {
    return Row(
      children: [
        Expanded(
          child: FilledButton.icon(
            icon: _capturando
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.camera_alt),
            label: Text(_capturando ? 'Capturando…' : 'Capturar'),
            // Sin cuerpo detectado la prenda no está puesta: la captura sería
            // una foto de la persona y nada más.
            onPressed: (hayCuerpo && _urlPrenda != null && !_capturando)
                ? _capturar
                : null,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: OutlinedButton.icon(
            style: OutlinedButton.styleFrom(foregroundColor: Colors.white),
            icon: const Icon(Icons.add_shopping_cart),
            label: const Text('Al carrito'),
            onPressed: _variante == null ? null : _agregarAlCarrito,
          ),
        ),
      ],
    );
  }

  // --- Capturar y llevarse la prenda (CU-21, pasos 5 y 6) ------------------

  /// Guarda lo que se ve —cámara y prenda— en un PNG y lo muestra.
  ///
  /// Se pinta el `RepaintBoundary`, que contiene la vista de la cámara y la
  /// superposición y **no** el panel de botones. Tomar la foto con la cámara
  /// (`takePicture`) no serviría: devolvería el fotograma limpio, sin la
  /// prenda encima, que es justo lo que el cliente quiere llevarse.
  ///
  /// `pixelRatio` sale del dispositivo para que la captura tenga la resolución
  /// real de la pantalla y no la lógica: con 1.0 sale borrosa en un teléfono
  /// moderno.
  Future<void> _capturar() async {
    setState(() => _capturando = true);
    try {
      final limite =
          _lienzo.currentContext?.findRenderObject() as RenderRepaintBoundary?;
      if (limite == null) throw StateError('la vista todavía no está pintada');

      final imagen = await limite.toImage(
        pixelRatio: MediaQuery.of(context).devicePixelRatio,
      );
      final datos = await imagen.toByteData(format: ui.ImageByteFormat.png);
      imagen.dispose();
      if (datos == null) throw StateError('no se pudo codificar la captura');

      final bytes = datos.buffer.asUint8List();

      // Se guarda en el directorio de la aplicación y no en la galería: llevar
      // la foto a la galería exige otro permiso y otro paquete, y para el flujo
      // de CU-21 —mirarla y decidir— no hace falta salir de la app.
      final carpeta = await getApplicationDocumentsDirectory();
      final archivo = File(
        '${carpeta.path}/vestidor-${DateTime.now().millisecondsSinceEpoch}.png',
      );
      await archivo.writeAsBytes(bytes);

      if (!mounted) return;
      await _mostrarCaptura(bytes, archivo);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No se pudo capturar: $e')),
      );
    } finally {
      if (mounted) setState(() => _capturando = false);
    }
  }

  /// La hoja con la captura y qué hacer con ella.
  ///
  /// Las dos salidas son las que nombra la ficha de CU-21: **al carrito** o
  /// **a la reserva**. Probarse una prenda y no poder hacer nada con ella
  /// dejaría el caso de uso a medias.
  Future<void> _mostrarCaptura(Uint8List bytes, File archivo) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: ColoresVB.marfil,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(radioVB)),
      ),
      builder: (hoja) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.black26,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'Así te queda',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: ColoresVB.malvaOscuro,
                  fontWeight: FontWeight.w600,
                ),
              ),
              if (_variante != null)
                Text(
                  '${_prendaElegida?.nombre ?? _nombreSuelto ?? ""} · '
                  '${_variante!.tallaCodigo ?? ""} ${_variante!.colorNombre ?? ""}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              const SizedBox(height: 12),
              ConstrainedBox(
                constraints: BoxConstraints(
                  maxHeight: MediaQuery.of(context).size.height * 0.42,
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.memory(bytes, fit: BoxFit.contain),
                ),
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: FilledButton.icon(
                      icon: const Icon(Icons.add_shopping_cart),
                      label: const Text('Al carrito'),
                      onPressed: _variante == null
                          ? null
                          : () {
                              Navigator.pop(hoja);
                              _agregarAlCarrito();
                            },
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: OutlinedButton.icon(
                      icon: const Icon(Icons.event_available_outlined),
                      label: const Text('Reservar'),
                      // Lleva al formulario de CU-22 para ir a probársela de
                      // verdad en la sucursal. Es la otra salida que nombra la
                      // ficha, y la que cierra el recorrido de la defensa:
                      // vestidor → reserva → atención en sucursal.
                      onPressed: () {
                        Navigator.pop(hoja);
                        context.push(Rutas.reservaNueva);
                      },
                    ),
                  ),
                ],
              ),
              if (_hayProbador && _variante != null) ...[
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: TextButton.icon(
                    icon: const Icon(Icons.auto_fix_high),
                    label: const Text('Ver cómo me queda de verdad'),
                    onPressed: () {
                      Navigator.pop(hoja);
                      _amoldar(bytes);
                    },
                  ),
                ),
                Text(
                  'Ajusta la prenda al cuerpo con inteligencia artificial. '
                  'Tarda unos segundos y es opcional.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
              const SizedBox(height: 8),
              Text(
                'La captura quedó guardada en el teléfono como '
                '${archivo.path.split("/").last}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Manda la captura al servidor para que la prenda se vea PUESTA.
  ///
  /// Es lo OPCIONAL de CU-21. El recorrido obligatorio ya termino: el cliente
  /// tiene su captura guardada pase lo que pase acá.
  ///
  /// Se muestra un diálogo bloqueante mientras tanto, y no un indicador
  /// discreto: tarda segundos, y sin algo que diga que está trabajando el
  /// cliente vuelve a tocar el botón o cierra la pantalla.
  Future<void> _amoldar(Uint8List captura) async {
    final variante = _variante;
    if (variante == null) return;

    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => const AlertDialog(
        content: Row(
          children: [
            SizedBox(
              width: 22,
              height: 22,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            SizedBox(width: 16),
            Expanded(child: Text('Ajustando la prenda a tu cuerpo…')),
          ],
        ),
      ),
    );

    try {
      final resultado = await RepositorioVestidor(
        ref.read(clienteApiProvider),
      ).amoldar(varianteId: variante.id, captura: captura);
      if (!mounted) return;
      Navigator.of(context).pop();          // cierra el diálogo de espera
      await _mostrarAmoldada(resultado);
    } on ErrorProbador catch (fallo) {
      if (!mounted) return;
      Navigator.of(context).pop();
      // Si resultó estar apagado, se esconde el botón: no tiene sentido
      // ofrecerlo otra vez en esta sesión.
      if (fallo.tipo == TipoErrorProbador.apagado) {
        setState(() => _hayProbador = false);
      }
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(content: Text(fallo.mensaje)));
    }
  }

  /// La imagen amoldada, con su aviso de que fue generada.
  Future<void> _mostrarAmoldada(PrendaAmoldada resultado) {
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
                'Así te quedaría',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: ColoresVB.malvaOscuro,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 10),
              ConstrainedBox(
                constraints: BoxConstraints(
                  maxHeight: MediaQuery.of(context).size.height * 0.5,
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.memory(resultado.imagen, fit: BoxFit.contain),
                ),
              ),
              const SizedBox(height: 10),
              // Que la imagen fue generada NO puede quedar implícito. Mostrarla
              // sin decirlo sería hacer pasar por foto algo que no lo es, y en
              // una tienda de ropa eso es una promesa sobre cómo le va a
              // quedar la prenda a esa persona.
              Row(
                children: [
                  const Icon(Icons.auto_fix_high, size: 16),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Imagen generada por ${resultado.generadaPor}. Es una '
                      'aproximación: la prenda real puede caer distinto.',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  icon: const Icon(Icons.add_shopping_cart),
                  label: const Text('Al carrito'),
                  onPressed: () {
                    Navigator.pop(hoja);
                    _agregarAlCarrito();
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _agregarAlCarrito() async {
    final variante = _variante;
    if (variante == null) return;
    final fallo = await ref
        .read(carritoProvider.notifier)
        .agregar(varianteId: variante.id);
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(fallo ?? 'Agregada al carrito.'),
          action: fallo == null
              ? SnackBarAction(
                  label: 'Ver carrito',
                  onPressed: () => context.push(Rutas.carrito),
                )
              : null,
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

/// Una talla, sobre la cámara.
///
/// Fondo semiopaco y no un `Chip` de Material: encima del vídeo, un control con
/// fondo claro se pierde cuando la persona lleva ropa clara. El contraste lo
/// tiene que poner el control, no la escena.
class _Ficha extends StatelessWidget {
  const _Ficha({
    required this.texto,
    required this.activa,
    required this.alTocar,
  });

  final String texto;
  final bool activa;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: activa ? ColoresVB.malva : Colors.black.withValues(alpha: 0.45),
      borderRadius: BorderRadius.circular(17),
      child: InkWell(
        borderRadius: BorderRadius.circular(17),
        onTap: alTocar,
        child: Container(
          alignment: Alignment.center,
          constraints: const BoxConstraints(minWidth: 44),
          padding: const EdgeInsets.symmetric(horizontal: 14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(17),
            border: Border.all(
              color: activa ? Colors.white : Colors.white24,
              width: activa ? 2 : 1,
            ),
          ),
          child: Text(
            texto,
            style: TextStyle(
              color: Colors.white,
              fontWeight: activa ? FontWeight.bold : FontWeight.normal,
            ),
          ),
        ),
      ),
    );
  }
}

/// Un color, sobre la cámara.
///
/// El color se muestra como una moneda y no como texto: es más rápido de leer
/// y no depende de que el nombre del color sea claro —«Oro rosa» no le dice
/// nada a nadie hasta verlo—. El nombre queda en el tooltip, para lectores de
/// pantalla y para quien dude.
class _Punto extends StatelessWidget {
  const _Punto({
    required this.hex,
    required this.nombre,
    required this.activo,
    required this.alTocar,
  });

  final String? hex;
  final String nombre;
  final bool activo;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) {
    Color color = ColoresVB.malvaClaro;
    final crudo = hex?.replaceAll('#', '');
    if (crudo != null && crudo.length == 6) {
      final valor = int.tryParse(crudo, radix: 16);
      if (valor != null) color = Color(0xFF000000 | valor);
    }

    return Tooltip(
      message: nombre,
      child: GestureDetector(
        onTap: alTocar,
        child: Container(
          width: 30,
          height: 30,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
            border: Border.all(
              color: activo ? Colors.white : Colors.white30,
              width: activo ? 3 : 1,
            ),
          ),
        ),
      ),
    );
  }
}
