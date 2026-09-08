import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/estado/sesion.dart';

/// Pantalla posterior al inicio de sesion.
///
/// Es el marco de la app, no una funcionalidad: confirma que la sesion esta
/// viva y ofrece cerrarla (CU-02). Las tarjetas de abajo son los accesos a los
/// casos de uso del Ciclo 2, que se van habilitando a medida que se entregan.
class InicioPantalla extends ConsumerWidget {
  const InicioPantalla({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final usuario = ref.watch(sesionProvider).value;
    final tema = Theme.of(context);

    if (usuario == null) {
      // El enrutado ya se esta encargando de sacar de aca; se evita construir
      // media pantalla con datos nulos mientras tanto.
      return const Scaffold(body: SizedBox.shrink());
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Violet Boutique'),
        actions: [
          IconButton(
            tooltip: 'Cerrar sesión',
            icon: const Icon(Icons.logout),
            onPressed: () => ref.read(sesionProvider.notifier).cerrar(),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Row(
            children: [
              CircleAvatar(
                radius: 26,
                backgroundColor: tema.colorScheme.primaryContainer,
                child: Text(
                  usuario.iniciales,
                  style: TextStyle(
                    color: tema.colorScheme.onPrimaryContainer,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      usuario.nombreCompleto,
                      style: tema.textTheme.titleMedium,
                    ),
                    Text(
                      usuario.correo,
                      style: tema.textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 28),
          Text('Tu tienda', style: tema.textTheme.titleSmall),
          const SizedBox(height: 12),
          const _AccesoPendiente(
            icono: Icons.checkroom,
            titulo: 'Catálogo',
            detalle: 'CU-17 · en construcción',
          ),
          const _AccesoPendiente(
            icono: Icons.event_available,
            titulo: 'Mis reservas',
            detalle: 'CU-23 · en construcción',
          ),
          const _AccesoPendiente(
            icono: Icons.person_outline,
            titulo: 'Mi perfil',
            detalle: 'CU-04 · en construcción',
          ),
          const _AccesoPendiente(
            icono: Icons.camera_alt_outlined,
            titulo: 'Vestidor virtual',
            detalle: 'CU-21 · prototipo del Ciclo 2',
          ),
        ],
      ),
    );
  }
}

class _AccesoPendiente extends StatelessWidget {
  const _AccesoPendiente({
    required this.icono,
    required this.titulo,
    required this.detalle,
  });

  final IconData icono;
  final String titulo;
  final String detalle;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        leading: Icon(icono),
        title: Text(titulo),
        subtitle: Text(detalle),
        enabled: false,
      ),
    );
  }
}
