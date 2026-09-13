/// CU-23 · Consultar reserva --- pasos 1 y 2.
///
/// **Las vivas arriba y en tarjetas; las cerradas abajo y en lista.** No es
/// decoracion: son dos preguntas distintas. «¿Cuándo tengo que ir y qué
/// reservé?» necesita ver la franja, la sucursal y las prendas de un vistazo, y
/// es lo unico sobre lo que el cliente puede actuar. «¿Qué reservé el mes
/// pasado?» es historial y se lee en lista. Es el mismo reparto que hace la
/// pantalla web.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/enrutado/router.dart';
import '../../core/red/excepciones.dart';
import '../../core/tema.dart';
import '../../data/modelos/reservas.dart';
import 'estado_reservas.dart';
import 'widgets_reservas.dart';

class PantallaMisReservas extends ConsumerWidget {
  const PantallaMisReservas({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final vivas = ref.watch(misReservasProvider(true));
    final cerradas = ref.watch(misReservasProvider(false));

    return Scaffold(
      appBar: AppBar(title: const Text('Mis reservas')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push(Rutas.reservaNueva),
        backgroundColor: ColoresVB.malva,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add),
        label: const Text('Reservar'),
      ),
      body: RefreshIndicator(
        color: ColoresVB.malva,
        // Tirar para refrescar es el gesto que el cliente va a usar cuando algo
        // no cuadre --- y tambien es lo que corresponde despues de un
        // `estado-final`, cuando la vista quedo vieja.
        onRefresh: () async {
          ref.invalidate(misReservasProvider(true));
          ref.invalidate(misReservasProvider(false));
          await ref.read(misReservasProvider(true).future);
        },
        child: _contenido(context, ref, vivas, cerradas),
      ),
    );
  }

  Widget _contenido(
    BuildContext context,
    WidgetRef ref,
    AsyncValue<PaginaReservas> vivas,
    AsyncValue<PaginaReservas> cerradas,
  ) {
    // Solo las vivas bloquean la pantalla: son la respuesta a la pregunta por
    // la que el cliente entro. El historial puede seguir cargando abajo.
    if (vivas.isLoading && !vivas.hasValue) {
      return const Center(child: CircularProgressIndicator());
    }

    if (vivas.hasError && !vivas.hasValue) {
      final fallo = vivas.error;
      return ListView(
        // `AlwaysScrollable` para que el gesto de refrescar siga funcionando
        // aunque el contenido no llene la pantalla; sin esto no hay nada que
        // arrastrar y el RefreshIndicator no se dispara.
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          SizedBox(
            height: MediaQuery.sizeOf(context).height * 0.7,
            child: AvisoReservas(
              icono: Icons.cloud_off_outlined,
              mensaje: fallo is ErrorApi
                  ? fallo.mensaje
                  : 'No se pudieron cargar sus reservas.',
              accion: FilledButton(
                onPressed: () => ref.invalidate(misReservasProvider(true)),
                child: const Text('Reintentar'),
              ),
            ),
          ),
        ],
      );
    }

    final proximas = vivas.value?.items ?? const <ReservaResumen>[];
    final historial = cerradas.value?.items ?? const <ReservaResumen>[];

    if (proximas.isEmpty && historial.isEmpty) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          SizedBox(
            height: MediaQuery.sizeOf(context).height * 0.7,
            child: AvisoReservas(
              icono: Icons.event_available_outlined,
              mensaje:
                  'Todavía no tiene reservas.\n\nElija sus prendas, la sucursal '
                  'y la hora, y se las apartamos para que se las pruebe.',
              accion: FilledButton.icon(
                onPressed: () => context.push(Rutas.reservaNueva),
                icon: const Icon(Icons.add),
                label: const Text('Reservar prendas'),
              ),
            ),
          ),
        ],
      );
    }

    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      // Espacio abajo para que el boton flotante no tape la ultima fila.
      padding: const EdgeInsets.fromLTRB(20, 4, 20, 96),
      children: [
        if (proximas.isNotEmpty) ...[
          const RotuloSeccion('Próximas'),
          for (final reserva in proximas)
            _TarjetaReserva(
              reserva: reserva,
              alTocar: () => context.push(Rutas.reservaDetalle(reserva.id)),
            ),
        ],
        if (historial.isNotEmpty) ...[
          const RotuloSeccion('Historial'),
          Card(
            child: Column(
              children: [
                for (final reserva in historial)
                  _FilaHistorial(
                    reserva: reserva,
                    alTocar: () =>
                        context.push(Rutas.reservaDetalle(reserva.id)),
                  ),
              ],
            ),
          ),
          if (cerradas.value?.hayMas ?? false)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(
                // No hay paginador: el historial de un cliente se mira de vez
                // en cuando y la pagina completa esta en la web. Decirlo es
                // mejor que cortar la lista sin explicacion.
                'Se muestran las ${historial.length} más recientes '
                'de ${cerradas.value!.total}.',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 12,
                  color: Color(0xFF9A8A92),
                ),
              ),
            ),
        ],
      ],
    );
  }
}

/// Una reserva viva. Muestra lo que hace falta para ir: cuando, donde y que.
class _TarjetaReserva extends StatelessWidget {
  const _TarjetaReserva({required this.reserva, required this.alTocar});

  final ReservaResumen reserva;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        borderRadius: BorderRadius.circular(radioVB),
        onTap: alTocar,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  ChipEstadoReserva(reserva.estado),
                  const Spacer(),
                  Text(
                    'N.º ${reserva.id}',
                    style: const TextStyle(
                      fontSize: 12,
                      color: Color(0xFF9A8A92),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(
                    Icons.schedule,
                    size: 18,
                    color: ColoresVB.malva,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      franjaCompleta(reserva.franjaInicio, reserva.franjaFin),
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        height: 1.35,
                        color: ColoresVB.malvaOscuro,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  const Icon(
                    Icons.storefront_outlined,
                    size: 18,
                    color: Color(0xFF9A8A92),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '${reserva.sucursal} · ${reserva.ciudad}',
                      style: const TextStyle(color: Color(0xFF5C4C55)),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  const Icon(
                    Icons.checkroom_outlined,
                    size: 18,
                    color: Color(0xFF9A8A92),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '${reserva.prendasRotuladas} · '
                    '${reserva.unidades} unidades apartadas',
                    style: const TextStyle(color: Color(0xFF5C4C55)),
                  ),
                  const Spacer(),
                  const Icon(
                    Icons.chevron_right,
                    size: 20,
                    color: Color(0xFFD6C4CC),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Una reserva cerrada. En lista: ya no hay nada que hacer con ella.
class _FilaHistorial extends StatelessWidget {
  const _FilaHistorial({required this.reserva, required this.alTocar});

  final ReservaResumen reserva;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      onTap: alTocar,
      title: Text(
        franjaCompleta(reserva.franjaInicio, reserva.franjaFin),
        style: const TextStyle(fontSize: 14),
      ),
      subtitle: Text(
        '${reserva.sucursal} · ${reserva.prendasRotuladas}',
        style: const TextStyle(fontSize: 12.5),
      ),
      trailing: ChipEstadoReserva(reserva.estado),
    );
  }
}
