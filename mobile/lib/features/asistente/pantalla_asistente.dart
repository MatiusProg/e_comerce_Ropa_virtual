/// CU-34 · Conversar con el asistente virtual, en el teléfono.
///
/// Realiza el **RF25** junto con CU-33 y CU-35.
///
/// LA CONVERSACIÓN VIVE EN MEMORIA, NO EN LA PANTALLA
/// ----------------------------------------------------
/// No hay tabla de conversaciones en el servidor —ver `asistente_service.py`—
/// así que los turnos se guardan del lado del cliente y se reenvían con cada
/// pregunta.
///
/// Estaban en el estado de este widget, y eso los borraba al navegar: ir al
/// catálogo a mirar una prenda que el asistente acababa de nombrar y volver
/// dejaba la conversación en blanco. Ahora viven en `conversacionProvider`
/// —memoria, nunca base— y sobreviven a la navegación. Ver
/// `estado_asistente.dart`.
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
import 'estado_asistente.dart';

class PantallaAsistente extends ConsumerStatefulWidget {
  const PantallaAsistente({super.key});

  @override
  ConsumerState<PantallaAsistente> createState() => _EstadoAsistente();
}

class _EstadoAsistente extends ConsumerState<PantallaAsistente> {
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
          .read(repositorioAsistenteProvider)
          .preguntar(texto, ref.read(conversacionProvider));
      if (!mounted) return;
      ref.read(conversacionProvider.notifier).agregar(turno);
      setState(() => _pensando = false);
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
    final estado = ref.watch(asistenteDisponibleProvider);
    final turnos = ref.watch(conversacionProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Asistente'),
        actions: [
          // Empezar de nuevo. Sin esto, la conversación que ahora sobrevive
          // a la navegación no se puede soltar nunca.
          if (turnos.isNotEmpty)
            IconButton(
              tooltip: 'Empezar de nuevo',
              icon: const Icon(Icons.refresh),
              onPressed: () =>
                  ref.read(conversacionProvider.notifier).limpiar(),
            ),
        ],
      ),
      body: estado.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, traza) => const _NoDisponible(),
        data: (info) => !info.disponible
            ? const _NoDisponible()
            : Column(
                children: [
                  Expanded(
                    child: turnos.isEmpty && !_pensando
                        ? _Bienvenida(
                            ejemplos: info.ejemplos,
                            alElegir: _enviar,
                          )
                        : ListView.builder(
                            controller: _scroll,
                            padding: const EdgeInsets.all(12),
                            itemCount: turnos.length + (_pensando ? 1 : 0),
                            itemBuilder: (_, i) {
                              if (i == turnos.length) return const _Pensando();
                              return _Intercambio(turno: turnos[i]);
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
                ],
              ),
      ),
      // LA CAJA DE ESCRIBIR VA EN `bottomNavigationBar`, NO EN EL `Column`.
      //
      // Estaba como ultimo hijo del `Column` y **no se veia**: en la captura
      // del telefono aparecia solo una linea vertical a 12 px del borde
      // ---el `padding` izquierdo--- con el campo extendiendose fuera de la
      // pantalla y el boton de enviar ya afuera. En depuracion eso se marca
      // con las franjas amarillas; **en release Flutter lo recorta en
      // silencio**, asi que no habia ningun aviso.
      //
      // Esta ranura esta hecha justo para esto: tiene ancho acotado, queda
      // siempre pegada abajo y sube sola con el teclado.
      bottomNavigationBar: estado.maybeWhen(
        data: (info) => info.disponible
            ? _Redaccion(
                campo: _campo,
                pensando: _pensando,
                alEnviar: _enviar,
              )
            : const SizedBox.shrink(),
        orElse: () => const SizedBox.shrink(),
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
                    onPressed: () => context.push('${Rutas.catalogo}/$id'),
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
    return Material(
      // Fondo y linea arriba: sin esto se confunde con el ultimo mensaje,
      // que en esta pantalla es del mismo color crema.
      color: Colors.white,
      elevation: 8,
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
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
                  minimumSize: const Size(52, 52),
                ),
                child: const Icon(Icons.send, size: 20),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
