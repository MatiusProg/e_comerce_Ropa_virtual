/// Pantalla posterior al inicio de sesion.
///
/// Provisional: hoy solo confirma que la autenticacion funciona de punta a
/// punta contra la API desplegada. En el Ciclo 2 se convierte en el armazon con
/// la barra de navegacion (Catalogo · Reservas · Mi cuenta) y cada quien cuelga
/// ahi sus pantallas.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constantes.dart';
import '../../core/tema.dart';
import '../auth/estado_sesion.dart';

class PantallaInicio extends ConsumerWidget {
  const PantallaInicio({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final usuario = ref.watch(usuarioActualProvider);

    // La redireccion del enrutador garantiza que aqui hay sesion; el `null` solo
    // puede darse en el instante entre cerrar sesion y salir de la pantalla.
    if (usuario == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Violet Boutique'),
        actions: [
          IconButton(
            tooltip: 'Cerrar sesion',
            icon: const Icon(Icons.logout),
            onPressed: () => ref.read(sesionProvider.notifier).cerrarSesion(),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 28,
                    backgroundColor: ColoresVB.rosaPalido,
                    child: Text(
                      usuario.iniciales,
                      style: const TextStyle(
                        color: ColoresVB.malvaOscuro,
                        fontWeight: FontWeight.w700,
                        fontSize: 18,
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
                          style: const TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          usuario.correo,
                          style: const TextStyle(
                            fontSize: 13,
                            color: Color(0xFF6B5A62),
                          ),
                        ),
                        const SizedBox(height: 8),
                        Chip(
                          label: Text(usuario.rol),
                          visualDensity: VisualDensity.compact,
                          backgroundColor: ColoresVB.rosaPalido,
                          side: BorderSide.none,
                          labelStyle: const TextStyle(
                            fontSize: 11,
                            color: ColoresVB.malvaOscuro,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),
          const _PendientesDelCiclo(),
          const SizedBox(height: 20),
          Center(
            child: Text(
              'API: $apiUrlBase',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 11, color: Color(0xFF9A8A92)),
            ),
          ),
        ],
      ),
    );
  }
}

/// Lista lo que va en esta pantalla durante el Ciclo 2, para que quede a la
/// vista de quien abra la app y no haya que ir a buscarlo al cronograma.
class _PendientesDelCiclo extends StatelessWidget {
  const _PendientesDelCiclo();

  @override
  Widget build(BuildContext context) {
    const pendientes = [
      ('Catalogo', 'CU-17 · CU-18 · CU-19', Icons.storefront_outlined),
      ('Reservas', 'CU-22 · CU-23', Icons.event_available_outlined),
      ('Vestidor virtual', 'Prototipo · CU-21', Icons.camera_alt_outlined),
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          children: [
            const ListTile(
              dense: true,
              title: Text(
                'Pendiente del Ciclo 2',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
            for (final (titulo, casos, icono) in pendientes)
              ListTile(
                leading: Icon(icono, color: ColoresVB.malvaClaro),
                title: Text(titulo),
                subtitle: Text(casos),
                trailing: const Icon(
                  Icons.circle_outlined,
                  size: 18,
                  color: Color(0xFFD6C4CC),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
