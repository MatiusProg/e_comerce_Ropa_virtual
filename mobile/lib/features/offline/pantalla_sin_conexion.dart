/// CU-13 Preparar el dispositivo · CU-18 Consultar operaciones pendientes.
///
/// La cola que se muestra es la del TELEFONO: lo que el cliente reservo sin
/// red y todavia no llego, y lo que el servidor ya decidio, con su motivo,
/// hasta que el cliente lo limpia.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/enrutado/router.dart';
import '../../core/red/excepciones.dart';
import '../../core/tema.dart';
import '../../data/modelos/offline.dart';
import '../../data/repositorios/repositorio_offline.dart';
import 'estado_offline.dart';

final _fecha = DateFormat('dd/MM HH:mm');

class PantallaSinConexion extends ConsumerStatefulWidget {
  const PantallaSinConexion({super.key});

  @override
  ConsumerState<PantallaSinConexion> createState() =>
      _PantallaSinConexionState();
}

class _PantallaSinConexionState extends ConsumerState<PantallaSinConexion> {
  bool _preparando = false;

  @override
  Widget build(BuildContext context) {
    final estado = ref.watch(offlineProvider);
    final paquete = estado.paquete;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Reservar sin conexión'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Chip(
              avatar: Icon(
                estado.enLinea ? Icons.cloud_done_outlined : Icons.cloud_off,
                size: 18,
              ),
              label: Text(estado.enLinea ? 'En línea' : 'Sin conexión'),
            ),
          ),
        ],
      ),
      floatingActionButton: paquete == null
          ? null
          : FloatingActionButton.extended(
              onPressed: () => context.push(Rutas.reservaSinRedNueva),
              backgroundColor: ColoresVB.malva,
              foregroundColor: Colors.white,
              icon: const Icon(Icons.add),
              label: const Text('Nueva reserva'),
            ),
      body: !estado.cargado
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 96),
              children: [
                _tarjetaPaquete(context, paquete, estado.enLinea),
                const SizedBox(height: 16),
                _tarjetaCola(context, estado),
              ],
            ),
    );
  }

  // --- CU-13 ---------------------------------------------------------------

  Widget _tarjetaPaquete(
    BuildContext context,
    PaqueteCliente? paquete,
    bool enLinea,
  ) {
    final texto = Theme.of(context).textTheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Preparar el teléfono', style: texto.titleMedium),
            const SizedBox(height: 8),
            if (paquete == null)
              const Text(
                'Hágalo con internet, antes de quedarse sin señal: guardamos en '
                'el teléfono las sucursales y las prendas con lo que hay de '
                'cada una, para que pueda reservar sin conexión.',
              )
            else ...[
              Text(
                'Datos del ${_fecha.format(paquete.generadoEn)}: '
                '${paquete.sucursales.length} sucursales y '
                '${paquete.prendas.length} prendas.',
              ),
              if (paquete.vencido) ...[
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(Icons.schedule, color: Colors.orange.shade800),
                    const SizedBox(width: 8),
                    const Expanded(
                      child: Text(
                        'Pueden estar desactualizados. Vuelva a prepararlo '
                        'cuando tenga internet.',
                      ),
                    ),
                  ],
                ),
              ],
            ],
            if (_preparando) ...[
              const SizedBox(height: 12),
              const LinearProgressIndicator(),
            ],
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: _preparando ? null : _preparar,
              icon: const Icon(Icons.download_for_offline_outlined),
              label: Text(paquete == null ? 'Preparar' : 'Actualizar datos'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _preparar() async {
    setState(() => _preparando = true);
    final aviso = ScaffoldMessenger.of(context);
    try {
      final p = await ref.read(offlineProvider.notifier).preparar();
      aviso.showSnackBar(
        SnackBar(
          content: Text(
            'Listo: ${p.prendas.length} prendas guardadas en el teléfono.',
          ),
        ),
      );
    } on SinRespuesta {
      ref.read(offlineProvider.notifier).marcarSinRed();
      aviso.showSnackBar(
        const SnackBar(
          content: Text('Sin conexión: el teléfono se prepara con internet.'),
        ),
      );
    } on ErrorApi catch (e) {
      aviso.showSnackBar(SnackBar(content: Text(e.mensaje)));
    } finally {
      if (mounted) setState(() => _preparando = false);
    }
  }

  // --- CU-18 + CU-17 -------------------------------------------------------

  Widget _tarjetaCola(BuildContext context, EstadoOffline estado) {
    final texto = Theme.of(context).textTheme;
    final hayDecididas = estado.operaciones.any((o) => !o.estado.pendiente);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Reservas sin conexión (${estado.pendientes.length} pendientes)',
              style: texto.titleMedium,
            ),
            if (estado.sincronizando) ...[
              const SizedBox(height: 12),
              const LinearProgressIndicator(),
            ],
            const SizedBox(height: 8),
            if (estado.operaciones.isEmpty)
              const Text('No hay reservas guardadas en este teléfono.')
            else
              for (final op in estado.operaciones) _fila(context, op),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilledButton.icon(
                  onPressed: estado.sincronizando || estado.pendientes.isEmpty
                      ? null
                      : _sincronizar,
                  icon: const Icon(Icons.sync),
                  label: const Text('Sincronizar ahora'),
                ),
                if (hayDecididas)
                  OutlinedButton.icon(
                    onPressed: () =>
                        ref.read(offlineProvider.notifier).limpiarDecididas(),
                    icon: const Icon(Icons.cleaning_services_outlined),
                    label: const Text('Limpiar historial'),
                  ),
              ],
            ),
            if (hayDecididas) ...[
              const SizedBox(height: 8),
              const Text(
                'Limpiar historial solo quita de esta lista las que el servidor '
                'ya confirmó o rechazó. Sus reservas siguen en «Mis reservas». '
                'Las pendientes no se quitan nunca.',
                style: TextStyle(fontSize: 12),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _fila(BuildContext context, OperacionGuardada op) {
    final (icono, color) = switch (op.estado) {
      EstadoOperacion.confirmada => (Icons.check_circle, Colors.green.shade700),
      EstadoOperacion.rechazada => (Icons.block, Colors.red.shade700),
      EstadoOperacion.enConflicto => (Icons.warning_amber, Colors.red.shade700),
      _ => (Icons.save_outlined, Colors.orange.shade800),
    };
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Icon(icono, color: color),
      title: Text(op.resumen),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${op.estado.etiqueta} · ${_fecha.format(op.creadaEn)}'
            '${op.intentos > 1 ? ' · ${op.intentos} intentos' : ''}',
          ),
          if (op.motivo != null)
            Text(op.motivo!, style: TextStyle(color: Colors.red.shade700)),
        ],
      ),
      onTap: op.reservaId == null
          ? null
          : () => context.push('${Rutas.reservas}/${op.reservaId}'),
    );
  }

  Future<void> _sincronizar() async {
    final aviso = ScaffoldMessenger.of(context);
    final r = await ref.read(offlineProvider.notifier).sincronizar();
    if (r == null) return;
    aviso.showSnackBar(
      SnackBar(
        content: Text(
          ref.read(offlineProvider).enLinea
              ? '${r.confirmadas} confirmada(s) y ${r.rechazadas} rechazada(s).'
              : 'Sigue sin conexión. Las reservas quedan guardadas.',
        ),
      ),
    );
  }
}
