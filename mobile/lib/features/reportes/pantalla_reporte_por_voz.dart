/// CU-35 · Pedir un reporte hablando, desde el teléfono.
///
/// El reconocimiento corre **en el aparato**, con el motor del sistema: es
/// gratis, no consume cuota del modelo y no sube audio a ningún lado. Al
/// servidor le llega el texto ya transcrito.
///
/// POR QUÉ SE MUESTRA LO ENTENDIDO ANTES DE DESCARGAR
/// ----------------------------------------------------
/// Porque es la única oportunidad de notar que el modelo interpretó otra
/// cosa. Un reporte equivocado no se nota hasta abrirlo — y para entonces ya
/// se mandó por correo. Descargar es un toque aparte, a propósito.
///
/// CUANDO NO SE ENTIENDE, SE PIDE QUE LO REPITA
/// ----------------------------------------------
/// Con ejemplos de frases que sí funcionan. Nunca se descarga «lo más
/// parecido»: entregar el reporte de reservas a quien pidió ventas es peor
/// que no entregar nada.
library;


import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:speech_to_text/speech_to_text.dart';

import 'guardar_reporte.dart';

import '../../core/tema.dart';
import '../../data/repositorios/repositorio_reportes.dart';
import '../auth/estado_sesion.dart';

class PantallaReportePorVoz extends ConsumerStatefulWidget {
  const PantallaReportePorVoz({super.key});

  @override
  ConsumerState<PantallaReportePorVoz> createState() => _EstadoReportePorVoz();
}

class _EstadoReportePorVoz extends ConsumerState<PantallaReportePorVoz> {
  final SpeechToText _voz = SpeechToText();

  bool _iniciando = true;
  bool _hayMotorEnElTelefono = false;
  bool _hayInterpreteEnElServidor = false;

  bool _escuchando = false;
  bool _interpretando = false;
  bool _bajando = false;

  String _dicho = '';
  String? _error;
  PedidoEntendido? _entendido;

  bool get _sePuedeHablar =>
      _hayMotorEnElTelefono && _hayInterpreteEnElServidor;

  @override
  void initState() {
    super.initState();
    _preparar();
  }

  Future<void> _preparar() async {
    // Las dos mitades tienen que estar: el motor del teléfono y el modelo del
    // servidor. Si falta cualquiera no se ofrece el micrófono, en vez de
    // ofrecerlo y fallar al tocarlo.
    final motor = await _voz.initialize(
      onError: (e) => _enPantalla(() {
        _escuchando = false;
        _error = _explicar(e.errorMsg);
      }),
      onStatus: (estado) {
        if (estado == 'done' || estado == 'notListening') {
          _enPantalla(() => _escuchando = false);
        }
      },
    );
    final servidor = await RepositorioReportes(
      ref.read(clienteApiProvider),
    ).hayVoz();

    if (!mounted) return;
    setState(() {
      _hayMotorEnElTelefono = motor;
      _hayInterpreteEnElServidor = servidor;
      _iniciando = false;
    });
  }

  void _enPantalla(VoidCallback cambio) {
    if (mounted) setState(cambio);
  }

  Future<void> _hablar() async {
    if (_escuchando) {
      await _voz.stop();
      _enPantalla(() => _escuchando = false);
      return;
    }

    setState(() {
      _dicho = '';
      _error = null;
      _entendido = null;
      _escuchando = true;
    });

    await _voz.listen(
      // Los resultados parciales se muestran mientras habla: sin eso, hablar
      // contra una pantalla quieta se siente roto y la gente toca otra vez,
      // cortando su propio dictado.
      onResult: (r) {
        _enPantalla(() => _dicho = r.recognizedWords);
        if (r.finalResult && r.recognizedWords.trim().length >= 2) {
          _interpretar(r.recognizedWords.trim());
        }
      },
      // Todo va en `SpeechListenOptions`: los parametros sueltos de `listen`
      // ---localeId, pauseFor, listenFor--- estan obsoletos en la version 7.
      listenOptions: SpeechListenOptions(
        localeId: 'es_BO',
        partialResults: true,
        cancelOnError: true,
        // Corta sola a los cuatro segundos de silencio: un pedido de reporte
        // es una frase, no un dictado.
        autoPunctuation: false,
        pauseFor: const Duration(seconds: 4),
        listenFor: const Duration(seconds: 20),
      ),
    );
  }

  Future<void> _interpretar(String frase) async {
    setState(() {
      _escuchando = false;
      _interpretando = true;
    });
    try {
      final pedido = await RepositorioReportes(
        ref.read(clienteApiProvider),
      ).interpretar(frase);
      _enPantalla(() {
        _entendido = pedido;
        _interpretando = false;
      });
    } catch (fallo) {
      _enPantalla(() {
        _error = '$fallo';
        _interpretando = false;
      });
    }
  }

  Future<void> _descargar() async {
    final pedido = _entendido;
    if (pedido?.url == null || _bajando) return;

    setState(() => _bajando = true);
    try {
      final archivo = await RepositorioReportes(
        ref.read(clienteApiProvider),
      ).descargar(pedido!.url!);

      // Se guarda y se abre la hoja de compartir del sistema.
      //
      // Antes se guardaba en el directorio de documentos de la app y se
      // avisaba con el nombre. Ese directorio es PRIVADO: no aparece en el
      // explorador de archivos ni se puede adjuntar a nada, asi que el
      // reporte quedaba bajado y la persona no lo encontraba. Ver
      // `guardar_reporte.dart`.
      if (!mounted) return;
      await guardarYCompartir(archivo, origen: rectanguloDe(context));

      if (!mounted) return;
      setState(() => _bajando = false);
    } catch (fallo) {
      _enPantalla(() => _bajando = false);
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('No se pudo bajar: $fallo')));
    }
  }

  String _explicar(String codigo) {
    if (codigo.contains('permission') || codigo.contains('denied')) {
      return 'Falta el permiso del micrófono. Habilitalo y probá de nuevo.';
    }
    if (codigo.contains('no_match') || codigo.contains('speech_timeout')) {
      return 'No se escuchó nada. Probá de nuevo, más cerca del micrófono.';
    }
    if (codigo.contains('network')) {
      return 'El reconocimiento de voz necesita conexión.';
    }
    return 'No se pudo escuchar.';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Pedir un reporte')),
      body: _iniciando
          ? const Center(child: CircularProgressIndicator())
          : !_sePuedeHablar
          ? _noSePuede()
          : _contenido(),
    );
  }

  /// Se dice CUÁL de las dos mitades falta.
  ///
  /// «No disponible» a secas no le sirve a nadie: si es el permiso, se
  /// arregla en el teléfono; si es el servidor, no hay nada que hacer desde
  /// acá y conviene saberlo.
  Widget _noSePuede() {
    final falta = !_hayMotorEnElTelefono
        ? 'Este teléfono no tiene reconocimiento de voz disponible, o falta '
              'el permiso del micrófono.'
        : 'El servidor no tiene habilitada la interpretación de pedidos.';
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.mic_off, size: 56, color: ColoresVB.malvaClaro),
            const SizedBox(height: 16),
            const Text(
              'No se puede pedir por voz',
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Text(
              falta,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.black54),
            ),
          ],
        ),
      ),
    );
  }

  Widget _contenido() {
    final pedido = _entendido;

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        const Text(
          'Tocá el micrófono y decí qué reporte necesitás.',
          style: TextStyle(fontSize: 15),
        ),
        const SizedBox(height: 4),
        const Text(
          'Por ejemplo: «las ventas de este mes en Excel».',
          style: TextStyle(color: Colors.black54, fontSize: 13),
        ),
        const SizedBox(height: 28),

        Center(
          child: GestureDetector(
            onTap: _interpretando ? null : _hablar,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 250),
              width: 104,
              height: 104,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: _escuchando ? ColoresVB.malva : ColoresVB.rosaPalido,
                boxShadow: _escuchando
                    ? [
                        BoxShadow(
                          color: ColoresVB.malva.withValues(alpha: 0.35),
                          blurRadius: 24,
                          spreadRadius: 6,
                        ),
                      ]
                    : null,
              ),
              child: Icon(
                _escuchando ? Icons.stop : Icons.mic,
                size: 44,
                color: _escuchando ? Colors.white : ColoresVB.malvaOscuro,
              ),
            ),
          ),
        ),
        const SizedBox(height: 22),

        if (_escuchando || _dicho.isNotEmpty)
          Center(
            child: Text(
              _dicho.isEmpty ? 'Escuchando…' : '«$_dicho»',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 16),
            ),
          ),

        if (_interpretando) ...[
          const SizedBox(height: 18),
          const Center(child: CircularProgressIndicator()),
          const SizedBox(height: 10),
          const Center(
            child: Text(
              'Interpretando…',
              style: TextStyle(color: Colors.black54),
            ),
          ),
        ],

        if (_error != null) ...[
          const SizedBox(height: 18),
          _Aviso(icono: Icons.mic_off, texto: _error!, esError: true),
        ],

        if (pedido != null && !_interpretando) ...[
          const SizedBox(height: 22),
          if (pedido.entendido)
            Card(
              color: ColoresVB.rosaPalido,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'ENTENDÍ',
                      style: TextStyle(
                        fontSize: 11,
                        letterSpacing: 1,
                        color: ColoresVB.malva,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      pedido.resumen ?? '',
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 14),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        icon: _bajando
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.download),
                        label: Text(_bajando ? 'Bajando…' : 'Descargar'),
                        onPressed: _bajando ? null : _descargar,
                      ),
                    ),
                  ],
                ),
              ),
            )
          else
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _Aviso(
                  icono: Icons.help_outline,
                  texto: pedido.motivo ?? 'No entendí el pedido.',
                  esError: false,
                ),
                if (pedido.ejemplos.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  const Text(
                    'Probá con alguna de estas:',
                    style: TextStyle(color: Colors.black54, fontSize: 13),
                  ),
                  const SizedBox(height: 6),
                  ...pedido.ejemplos.map(
                    (e) => Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: Text(
                        '· «$e»',
                        style: const TextStyle(fontSize: 13.5),
                      ),
                    ),
                  ),
                ],
              ],
            ),
        ],
      ],
    );
  }
}

class _Aviso extends StatelessWidget {
  const _Aviso({
    required this.icono,
    required this.texto,
    required this.esError,
  });

  final IconData icono;
  final String texto;
  final bool esError;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: esError ? const Color(0xFFFDECEA) : ColoresVB.marfil,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            icono,
            size: 20,
            color: esError ? const Color(0xFF8C1D18) : ColoresVB.malvaOscuro,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              texto,
              style: TextStyle(
                color: esError
                    ? const Color(0xFF8C1D18)
                    : ColoresVB.malvaOscuro,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
