/// CU-23 · Consultar y cancelar reserva --- pasos 3 a 5.
///
/// El detalle de una reserva propia y, si sigue viva, el boton de cancelarla.
/// Cancelar **no la borra**: se conserva con su motivo, su fecha y sus prendas,
/// porque es historia del cliente y de la sucursal, y porque los movimientos de
/// `LIBERACION` que deja apuntan a ella. Por eso, despues de cancelar, la
/// pantalla se queda mostrando la reserva --- ahora CANCELADA --- en vez de
/// volver atras.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/red/excepciones.dart';
import '../../core/tema.dart';
import '../../data/modelos/reservas.dart';
import '../../data/repositorios/repositorio_reservas.dart';
import 'estado_reservas.dart';
import 'widgets_reservas.dart';

class PantallaDetalleReserva extends ConsumerStatefulWidget {
  const PantallaDetalleReserva({required this.reservaId, super.key});

  final int reservaId;

  @override
  ConsumerState<PantallaDetalleReserva> createState() =>
      _EstadoPantallaDetalleReserva();
}

class _EstadoPantallaDetalleReserva
    extends ConsumerState<PantallaDetalleReserva> {
  bool _cancelando = false;

  @override
  Widget build(BuildContext context) {
    final reserva = ref.watch(reservaProvider(widget.reservaId));

    return Scaffold(
      appBar: AppBar(title: Text('Reserva N.º ${widget.reservaId}')),
      body: reserva.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (fallo, _) => AvisoReservas(
          icono: Icons.search_off,
          mensaje: fallo is ErrorApi
              ? fallo.mensaje
              : 'No encontramos esa reserva.',
        ),
        data: _construir,
      ),
    );
  }

  Widget _construir(Reserva reserva) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ChipEstadoReserva(reserva.estado),
                const SizedBox(height: 14),
                _Dato(
                  icono: Icons.schedule,
                  texto: franjaCompleta(
                    reserva.franjaInicio,
                    reserva.franjaFin,
                  ),
                  destacado: true,
                ),
                const SizedBox(height: 10),
                _Dato(
                  icono: Icons.storefront_outlined,
                  texto: '${reserva.sucursal} · ${reserva.ciudad}',
                ),
                const SizedBox(height: 10),
                _Dato(
                  icono: Icons.checkroom_outlined,
                  texto: reserva.estado.esViva
                      ? '${reserva.unidades} unidades apartadas para usted'
                      : '${reserva.unidades} unidades',
                ),
                const SizedBox(height: 10),
                _Dato(
                  icono: Icons.event_note_outlined,
                  texto: 'Reservada el ${diaLargo(reserva.creadoEn)} '
                      'a las ${soloHora(reserva.creadoEn)}',
                ),
              ],
            ),
          ),
        ),

        const RotuloSeccion('Prendas'),
        Card(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
            child: Column(
              children: [
                for (final linea in reserva.lineas)
                  FilaPrenda(
                    producto: linea.producto,
                    sku: linea.sku,
                    talla: linea.talla,
                    color: linea.color,
                    cantidad: linea.cantidad,
                    // El resultado solo existe si la reserva fue atendida
                    // (CU-24). Mientras sigue viva no hay nada que mostrar.
                    alFinal: linea.resultadoPrueba == null
                        ? null
                        : _Resultado(seLaLlevo: linea.seLaLlevo),
                  ),
              ],
            ),
          ),
        ),

        // La nota de CIERRE: la escribe CU-23 al cancelar o CU-24 al atender.
        // Nunca es una nota que el cliente haya dejado al reservar --- eso
        // necesitaria columna propia, y por eso CU-22 no la acepta.
        if (reserva.observacion != null) ...[
          const RotuloSeccion('Nota'),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Text(
                reserva.observacion!,
                style: const TextStyle(height: 1.5, color: Color(0xFF5C4C55)),
              ),
            ),
          ),
        ],

        const SizedBox(height: 24),
        if (reserva.estado.seCancela)
          OutlinedButton.icon(
            onPressed: _cancelando ? null : () => _confirmarCancelacion(reserva),
            icon: _cancelando
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.cancel_outlined),
            label: Text(_cancelando ? 'Cancelando…' : 'Cancelar la reserva'),
            style: OutlinedButton.styleFrom(
              foregroundColor: const Color(0xFFA33A3A),
              minimumSize: const Size.fromHeight(50),
              side: const BorderSide(color: Color(0xFFE0BFBF)),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(radioChicoVB),
              ),
            ),
          )
        else
          // Se dice POR QUE no se puede cancelar en vez de esconder el boton
          // sin explicacion: para el cliente que entro justo a cancelar, un
          // boton ausente parece un fallo de la app.
          Text(
            switch (reserva.estado) {
              EstadoReserva.atendida =>
                'Esta reserva ya fue atendida en la sucursal.',
              EstadoReserva.cancelada => 'Esta reserva está cancelada.',
              EstadoReserva.expirada =>
                'Esta reserva venció y las prendas volvieron al catálogo.',
              _ => '',
            },
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 13, color: Color(0xFF9A8A92)),
          ),
      ],
    );
  }

  /// El dialogo dice **que implica** cancelar, no solo pregunta si está seguro.
  ///
  /// Que las prendas vuelven a estar disponibles para otros clientes es
  /// justamente lo que el cliente necesita saber antes de decidir: si duda
  /// entre ir o no, cancelar no es gratis --- puede que a la vuelta ya no
  /// quede.
  Future<void> _confirmarCancelacion(Reserva reserva) async {
    final motivo = TextEditingController();
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (contexto) => AlertDialog(
        title: const Text('¿Cancelar la reserva?'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Las ${reserva.unidades} unidades que tenemos apartadas para '
              'usted vuelven a estar disponibles para otros clientes, y se '
              'libera el probador de esa franja.',
              style: const TextStyle(height: 1.5),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: motivo,
              maxLength: 150,
              decoration: const InputDecoration(
                labelText: 'Motivo (opcional)',
                hintText: 'Por ejemplo: no voy a poder ir',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(contexto).pop(false),
            child: const Text('Volver'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(contexto).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFFA33A3A),
              minimumSize: const Size(0, 44),
            ),
            child: const Text('Sí, cancelar'),
          ),
        ],
      ),
    );

    if (confirmado != true) {
      motivo.dispose();
      return;
    }

    final texto = motivo.text.trim();
    motivo.dispose();
    await _cancelar(texto.isEmpty ? null : texto);
  }

  Future<void> _cancelar(String? motivo) async {
    setState(() => _cancelando = true);

    try {
      await ref
          .read(repositorioReservasProvider)
          .cancelar(widget.reservaId, motivo: motivo);

      // La reserva cambio de estado y salio de las vivas: las dos listas de
      // «Mis reservas» quedaron viejas, no solo esta pantalla.
      _refrescarTodo();

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Reserva cancelada. Las prendas volvieron a estar disponibles.',
          ),
        ),
      );
    } on ErrorReservas catch (fallo) {
      // `estado-final` casi siempre significa que la vista esta vieja: la
      // atendieron o expiro mientras el cliente miraba. Se refresca ADEMAS de
      // avisar, porque reintentar sobre el estado viejo no va a servir.
      if (fallo.tipo == TipoErrorReserva.estadoFinal) {
        _refrescarTodo();
      }
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(fallo.mensaje)));
    } finally {
      if (mounted) setState(() => _cancelando = false);
    }
  }

  void _refrescarTodo() {
    ref.invalidate(reservaProvider(widget.reservaId));
    ref.invalidate(misReservasProvider(true));
    ref.invalidate(misReservasProvider(false));
  }
}

class _Dato extends StatelessWidget {
  const _Dato({
    required this.icono,
    required this.texto,
    this.destacado = false,
  });

  final IconData icono;
  final String texto;
  final bool destacado;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          icono,
          size: 18,
          color: destacado ? ColoresVB.malva : const Color(0xFF9A8A92),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            texto,
            style: TextStyle(
              height: 1.35,
              fontWeight: destacado ? FontWeight.w600 : FontWeight.w400,
              color: destacado
                  ? ColoresVB.malvaOscuro
                  : const Color(0xFF5C4C55),
            ),
          ),
        ),
      ],
    );
  }
}

/// Lo que paso con una prenda cuando el cliente se la probo (lo escribe CU-24).
class _Resultado extends StatelessWidget {
  const _Resultado({required this.seLaLlevo});

  final bool seLaLlevo;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 8, top: 2),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            seLaLlevo ? Icons.check_circle : Icons.remove_circle_outline,
            size: 16,
            color: seLaLlevo
                ? const Color(0xFF2A6B43)
                : const Color(0xFF9A8A92),
          ),
          const SizedBox(width: 4),
          Text(
            seLaLlevo ? 'Se la llevó' : 'No se la llevó',
            style: TextStyle(
              fontSize: 12,
              color: seLaLlevo
                  ? const Color(0xFF2A6B43)
                  : const Color(0xFF9A8A92),
            ),
          ),
        ],
      ),
    );
  }
}
