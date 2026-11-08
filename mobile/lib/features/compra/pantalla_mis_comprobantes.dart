/// CU-46 · Consultar mis comprobantes por voz, en el teléfono.
///
/// El cliente dice o escribe «mis últimas 3 compras», «mis recibos de
/// octubre» o «mis devoluciones» y ve sus comprobantes, cada uno con su QR.
///
/// El dictado es el mismo de CU-35 (`speech_to_text`, en el aparato). A
/// diferencia de CU-35, el micrófono es un atajo y no el único camino: si el
/// teléfono no reconoce voz, el campo de texto sigue funcionando.
///
/// Si el pedido no se entiende, se muestran ejemplos y **ningún dato**: el
/// servidor nunca adivina qué quiso decir.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/moneda.dart';
import '../../core/red/excepciones.dart';
import '../../core/tema.dart';
import '../../data/repositorios/repositorio_mis_comprobantes.dart';
import '../auth/estado_sesion.dart';

const _ejemplos = [
  'Mis últimas 3 compras',
  'Mis recibos de octubre',
  'Mis devoluciones',
  'Mis compras del mes pasado',
];

class PantallaMisComprobantes extends ConsumerStatefulWidget {
  const PantallaMisComprobantes({super.key});

  @override
  ConsumerState<PantallaMisComprobantes> createState() =>
      _EstadoMisComprobantes();
}

class _EstadoMisComprobantes extends ConsumerState<PantallaMisComprobantes> {
  final SpeechToText _voz = SpeechToText();
  final TextEditingController _campo = TextEditingController();

  bool _hayVoz = false;
  bool _escuchando = false;
  bool _consultando = false;
  String? _error;
  ResultadoComprobantes? _resultado;

  @override
  void initState() {
    super.initState();
    _prepararVoz();
  }

  @override
  void dispose() {
    _campo.dispose();
    _voz.stop();
    super.dispose();
  }

  Future<void> _prepararVoz() async {
    final ok = await _voz.initialize(
      onError: (_) => _enPantalla(() => _escuchando = false),
      onStatus: (estado) {
        if (estado == 'done' || estado == 'notListening') {
          _enPantalla(() => _escuchando = false);
        }
      },
    );
    _enPantalla(() => _hayVoz = ok);
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
      _escuchando = true;
      _error = null;
    });
    await _voz.listen(
      onResult: (r) {
        _enPantalla(() => _campo.text = r.recognizedWords);
        if (r.finalResult && r.recognizedWords.trim().length >= 2) {
          _consultar(r.recognizedWords.trim());
        }
      },
      listenOptions: SpeechListenOptions(
        localeId: 'es_BO',
        partialResults: true,
        cancelOnError: true,
        pauseFor: const Duration(seconds: 4),
        listenFor: const Duration(seconds: 15),
      ),
    );
  }

  Future<void> _consultar([String? frase]) async {
    final texto = (frase ?? _campo.text).trim();
    if (texto.length < 2 || _consultando) return;
    _campo.text = texto;
    FocusScope.of(context).unfocus();
    setState(() {
      _escuchando = false;
      _consultando = true;
      _error = null;
    });
    try {
      final r = await RepositorioMisComprobantes(
        ref.read(clienteApiProvider),
      ).consultar(texto);
      _enPantalla(() {
        _resultado = r;
        _consultando = false;
      });
    } catch (fallo) {
      _enPantalla(() {
        _error = fallo is ErrorApi ? fallo.mensaje : 'No se pudo consultar.';
        _consultando = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final r = _resultado;
    return Scaffold(
      appBar: AppBar(title: const Text('Mis comprobantes')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          TextField(
            controller: _campo,
            maxLength: 300,
            textInputAction: TextInputAction.search,
            onSubmitted: (_) => _consultar(),
            decoration: InputDecoration(
              labelText: '¿Qué comprobantes querés ver?',
              hintText: 'Ej.: mis últimas 3 compras',
              counterText: '',
              border: const OutlineInputBorder(),
              suffixIcon: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (_hayVoz)
                    IconButton(
                      tooltip: _escuchando ? 'Detener' : 'Dictar',
                      color: _escuchando ? ColoresVB.malva : null,
                      icon: Icon(_escuchando ? Icons.stop_circle : Icons.mic),
                      onPressed: _consultando ? null : _hablar,
                    ),
                  IconButton(
                    tooltip: 'Buscar',
                    icon: const Icon(Icons.search),
                    onPressed: _consultando ? null : _consultar,
                  ),
                ],
              ),
            ),
          ),
          if (_escuchando)
            const Padding(
              padding: EdgeInsets.only(top: 6),
              child: Text('Escuchando… hablá ahora.',
                  style: TextStyle(color: ColoresVB.malva)),
            ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              for (final e in _ejemplos)
                ActionChip(
                  label: Text(e),
                  backgroundColor: ColoresVB.rosaPalido,
                  onPressed: _consultando ? null : () => _consultar(e),
                ),
            ],
          ),
          if (_consultando)
            const Padding(
              padding: EdgeInsets.only(top: 16),
              child: LinearProgressIndicator(color: ColoresVB.malva),
            ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 16),
              child: Text(_error!, style: const TextStyle(color: Colors.red)),
            ),
          if (r != null) ..._resultadoEnPantalla(r),
        ],
      ),
    );
  }

  List<Widget> _resultadoEnPantalla(ResultadoComprobantes r) {
    if (!r.entendido) {
      return [
        const SizedBox(height: 20),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('No entendí tu pedido.',
                    style: TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                Text(r.motivo ?? ''),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: [
                    for (final e in r.ejemplos)
                      ActionChip(label: Text(e), onPressed: () => _consultar(e)),
                  ],
                ),
              ],
            ),
          ),
        ),
      ];
    }
    return [
      const SizedBox(height: 20),
      Text.rich(TextSpan(children: [
        const TextSpan(text: 'Entendí: '),
        TextSpan(
          text: r.resumen ?? '',
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
      ])),
      for (final a in r.avisos)
        Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text(a,
              style: const TextStyle(fontSize: 12, color: Colors.black54)),
        ),
      const SizedBox(height: 12),
      if (r.items.isEmpty)
        const Padding(
          padding: EdgeInsets.all(24),
          child: Center(
            child: Text('No hay comprobantes que coincidan con tu pedido.'),
          ),
        ),
      for (final c in r.items) _TarjetaComprobante(comprobante: c),
    ];
  }
}

class _TarjetaComprobante extends ConsumerWidget {
  const _TarjetaComprobante({required this.comprobante});

  final ComprobanteCliente comprobante;

  Future<void> _abrir(BuildContext context) async {
    final url = comprobante.urlVerificacion;
    if (url == null) return;
    final ok = await launchUrl(Uri.parse(url),
        mode: LaunchMode.externalApplication);
    if (!ok && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No se pudo abrir la verificación.')),
      );
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final c = comprobante;
    final devolucion = c.tipo == 'DEVOLUCION';
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(
          color: devolucion ? ColoresVB.oro : ColoresVB.malva,
          width: 1.2,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 96,
              height: 96,
              child: c.token == null
                  ? Container(
                      color: ColoresVB.marfil,
                      alignment: Alignment.center,
                      child: const Text('Sin\ncomprobante',
                          textAlign: TextAlign.center,
                          style: TextStyle(fontSize: 11)),
                    )
                  : GestureDetector(
                      onTap: () => _abrir(context),
                      child: _Qr(token: c.token!),
                    ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(c.rotuloDocumento.toUpperCase(),
                      style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: ColoresVB.malva)),
                  Text(c.codigo,
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.w600)),
                  Text(c.fechaTexto,
                      style:
                          const TextStyle(fontSize: 12, color: Colors.black54)),
                  if (c.detalle != null)
                    Text(c.detalle!,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            fontSize: 12, color: Colors.black54)),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Text(bs(c.total),
                          style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              color: ColoresVB.malvaOscuro)),
                      const SizedBox(width: 10),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: ColoresVB.rosaPalido,
                          borderRadius: BorderRadius.circular(99),
                        ),
                        child: Text(c.rotuloEstado,
                            style: const TextStyle(fontSize: 11)),
                      ),
                    ],
                  ),
                  if (c.urlVerificacion != null)
                    TextButton.icon(
                      style: TextButton.styleFrom(padding: EdgeInsets.zero),
                      onPressed: () => _abrir(context),
                      icon: const Icon(Icons.open_in_new, size: 16),
                      label: const Text('Ver / imprimir'),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// El QR, pedido como matriz al servidor y pintado acá.
class _Qr extends ConsumerStatefulWidget {
  const _Qr({required this.token});

  final String token;

  @override
  ConsumerState<_Qr> createState() => _EstadoQr();
}

class _EstadoQr extends ConsumerState<_Qr> {
  late final Future<List<String>> _modulos =
      RepositorioMisComprobantes(ref.read(clienteApiProvider)).qr(widget.token);

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<String>>(
      future: _modulos,
      builder: (context, foto) {
        final filas = foto.data;
        if (filas == null || filas.isEmpty) {
          return Container(
            color: ColoresVB.marfil,
            alignment: Alignment.center,
            child: foto.hasError
                ? const Icon(Icons.qr_code_2, color: ColoresVB.malvaClaro)
                : const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
          );
        }
        return CustomPaint(painter: _PintorQr(filas));
      },
    );
  }
}

class _PintorQr extends CustomPainter {
  _PintorQr(this.filas);

  final List<String> filas;

  @override
  void paint(Canvas canvas, Size size) {
    const margen = 2;
    final n = filas.length + 2 * margen;
    final lado = size.shortestSide / n;
    canvas.drawRect(Offset.zero & size, Paint()..color = Colors.white);
    final tinta = Paint()..color = ColoresVB.tinta;
    for (var y = 0; y < filas.length; y++) {
      for (var x = 0; x < filas[y].length; x++) {
        if (filas[y].codeUnitAt(x) == 0x31) {
          canvas.drawRect(
            Rect.fromLTWH((x + margen) * lado, (y + margen) * lado, lado, lado),
            tinta,
          );
        }
      }
    }
  }

  @override
  bool shouldRepaint(_PintorQr viejo) => viejo.filas != filas;
}
