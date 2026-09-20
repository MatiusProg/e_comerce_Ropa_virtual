/// CU-34 · Conversar con el asistente virtual, en el teléfono.
///
/// Realiza el **RF25** junto con CU-33 y CU-35.
///
/// LA CONVERSACIÓN VIVE EN LA PANTALLA
/// -------------------------------------
/// No hay tabla de conversaciones en el servidor —ver `asistente_service.py`—
/// así que los turnos se guardan acá y se reenvían con cada pregunta. Al
/// cerrar la pantalla se pierden, que es lo que espera cualquiera de un chat
/// de atención.
///
/// SI NO HAY MODELO, NO SE OFRECE
/// --------------------------------
/// Se pregunta antes de dibujar nada. **Sin modelo no hay degradación
/// posible**: un asistente que contesta con frases armadas daría respuestas
/// que parecen del sistema y no salen de sus datos. Es lo mismo que hace
/// CU-35 con el micrófono.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/enrutado/router.dart';
import '../../core/red/excepciones.dart';
import '../../core/tema.dart';
import '../../data/repositorios/repositorio_asistente.dart';
import '../auth/estado_sesion.dart';

final _repositorioProvider = Provider<RepositorioAsistente>((ref) {
  return RepositorioAsistente(ref.watch(clienteApiProvider));
});

final _disponibleProvider =
    FutureProvider<({bool disponible, List<String> ejemplos})>((ref) async {
      return ref.watch(_repositorioProvider).disponible();
    });

class PantallaAsistente extends ConsumerStatefulWidget {
  const PantallaAsistente({super.key});

  @override
  ConsumerState<PantallaAsistente> createState() => _EstadoAsistente();
}

class _EstadoAsistente extends ConsumerState<PantallaAsistente> {
  final _turnos = <Turno>[];
  final _campo = TextEditingController();
  final _scroll = ScrollController();
  bool _pensando = false;
  String? _error;

  @override
  void dispose() {
    _campo.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _enviar(String texto) async {
    texto = texto.trim();
    if (texto.length < 2 || _pensando) return;

    setState(() {
      _pensando = true;
      _error = null;
      _campo.clear();
    });
    _alFinal();

    try {
      final turno = await ref
          .read(_repositorioProvider)
          .preguntar(texto, _turnos);
      if (!mounted) return;
      setState(() {
        _turnos.add(turno);
        _pensando = false;
      });
      _alFinal();
    } catch (fallo) {
      if (!mounted) return;
      setState(() {
        _pensando = false;
        _error = fallo is ErrorApi
            ? fallo.mensaje
            : 'No pude responder ahora. Probá de nuevo.';
      });
    }
  }

  /// Baja al último mensaje después de que el marco se dibuje.
  void _alFinal() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final estado = ref.watch(_disponibleProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Asistente')),
      body: estado.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, traza) => const _NoDisponible(),
        data: (info) => !info.disponible
            ? const _NoDisponible()
            : Column(
                children: [
                  Expanded(
                    child: _turnos.isEmpty && !_pensando
                        ? _Bienvenida(
                            ejemplos: info.ejemplos,
                            alElegir: _enviar,
                          )
                        : ListView.builder(
                            controller: _scroll,
                            padding: const EdgeInsets.all(12),
                            itemCount: _turnos.length + (_pensando ? 1 : 0),
                            itemBuilder: (_, i) {
                              if (i == _turnos.length) return const _Pensando();
                              return _Intercambio(turno: _turnos[i]);
                            },
                          ),
                  ),
                  if (_error != null)
                    Container(
                      width: double.infinity,
                      color: const Color(0xFFFBE3E3),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 8,
                      ),
                      child: Text(
                        _error!,
                        style: const TextStyle(
                          fontSize: 12,
                          color: Color(0xFFB3261E),
                        ),
                      ),
                    ),
                  _Redaccion(
                    campo: _campo,
                    pensando: _pensando,
                    alEnviar: _enviar,
                  ),
                ],
              ),
      ),
    );
  }
}

/// El asistente no está. **No se dibuja una versión degradada.**
class _NoDisponible extends StatelessWidget {
  const _NoDisponible();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(24, 80, 24, 24),
      children: const [
        Icon(Icons.chat_bubble_outline, size: 56, color: ColoresVB.malvaClaro),
        SizedBox(height: 16),
        Text(
          'El asistente no está disponible',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
        ),
        SizedBox(height: 8),
        Text(
          'Podés seguir usando el catálogo, las reservas y el carrito '
          'normalmente.',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.black54),
        ),
      ],
    );
  }
}

/// Qué preguntar cuando no se sabe qué preguntar.
///
/// Los ejemplos vienen del servidor y no están escritos acá: dependen de lo
/// que el asistente puede contestar, y si mañana ve algo más el ejemplo se
/// actualiza donde está el contexto y no en dos frentes.
class _Bienvenida extends StatelessWidget {
  const _Bienvenida({required this.ejemplos, required this.alElegir});

  final List<String> ejemplos;
  final void Function(String) alElegir;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 40, 20, 20),
      children: [
        const Icon(Icons.auto_awesome, size: 48, color: ColoresVB.malva),
        const SizedBox(height: 12),
        const Text(
          'Preguntame lo que quieras',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 6),
        const Text(
          'Sé lo que hay en el catálogo y puedo ver tus pedidos y tus '
          'reservas.',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.black54, fontSize: 13),
        ),
        const SizedBox(height: 20),
        for (final e in ejemplos)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: OutlinedButton(
              onPressed: () => alElegir(e),
              style: OutlinedButton.styleFrom(
                alignment: Alignment.centerLeft,
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 12,
                ),
              ),
              child: Text(e, style: const TextStyle(fontSize: 13)),
            ),
          ),
      ],
    );
  }
}

class _Intercambio extends StatelessWidget {
  const _Intercambio({required this.turno});

  final Turno turno;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // La pregunta, a la derecha.
        Align(
          alignment: Alignment.centerRight,
          child: Container(
            margin: const EdgeInsets.only(bottom: 8, left: 40),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: ColoresVB.malva,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(16),
                topRight: Radius.circular(16),
                bottomLeft: Radius.circular(16),
              ),
            ),
            child: Text(
              turno.pregunta,
              style: const TextStyle(color: Colors.white),
            ),
          ),
        ),
        // La respuesta, a la izquierda.
        Container(
          margin: const EdgeInsets.only(bottom: 4, right: 40),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: const BoxDecoration(
            color: ColoresVB.rosaPalido,
            borderRadius: BorderRadius.only(
              topLeft: Radius.circular(16),
              topRight: Radius.circular(16),
              bottomRight: Radius.circular(16),
            ),
          ),
          child: Text(_sinCodigos(turno.respuesta)),
        ),
        // Las prendas que mencionó, como atajos.
        //
        // Ya vienen validadas contra el catálogo por el servidor: un código
        // que el modelo invente no llega hasta acá, así que tocar uno nunca
        // lleva a una ficha vacía.
        if (turno.productos.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: 12, right: 40),
            child: Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final id in turno.productos)
                  ActionChip(
                    avatar: const Icon(Icons.checkroom, size: 16),
                    label: Text('Ver #$id'),
                    onPressed: () =>
                        context.push('${Rutas.catalogo}/$id'),
                  ),
              ],
            ),
          ),
      ],
    );
  }

  /// Saca los `[#12]` del texto: en la pantalla se ven como botones.
  ///
  /// Se quitan los corchetes y no el número entero porque el modelo a veces
  /// los usa dentro de la frase —«el [#9] camisero»— y borrarlo del todo
  /// dejaría «el camisero» sin referencia.
  String _sinCodigos(String texto) =>
      texto.replaceAll(RegExp(r'\[[^\]]*?#\d+[^\]]*?\]'), '').replaceAll(
        RegExp(r' {2,}'),
        ' ',
      );
}

class _Pensando extends StatelessWidget {
  const _Pensando();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(vertical: 12),
      child: Row(
        children: [
          SizedBox(
            width: 16,
            height: 16,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              color: ColoresVB.malva,
            ),
          ),
          SizedBox(width: 10),
          // Se dice que puede tardar: el modelo se toma entre 3 y 25
          // segundos, y una espera sin explicación se lee como que se colgó.
          Text(
            'Pensando… puede tardar unos segundos',
            style: TextStyle(fontSize: 12, color: Colors.black54),
          ),
        ],
      ),
    );
  }
}

class _Redaccion extends StatelessWidget {
  const _Redaccion({
    required this.campo,
    required this.pensando,
    required this.alEnviar,
  });

  final TextEditingController campo;
  final bool pensando;
  final void Function(String) alEnviar;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: campo,
                enabled: !pensando,
                maxLength: 500,
                minLines: 1,
                maxLines: 4,
                textInputAction: TextInputAction.send,
                onSubmitted: alEnviar,
                decoration: const InputDecoration(
                  hintText: 'Escribí tu pregunta…',
                  counterText: '',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
              ),
            ),
            const SizedBox(width: 8),
            FilledButton(
              onPressed: pensando ? null : () => alEnviar(campo.text),
              style: FilledButton.styleFrom(
                backgroundColor: ColoresVB.malva,
                padding: const EdgeInsets.all(14),
              ),
              child: const Icon(Icons.send, size: 20),
            ),
          ],
        ),
      ),
    );
  }
}
