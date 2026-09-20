/// Pantalla posterior al inicio de sesion.
///
/// Provisional: hoy solo confirma que la autenticacion funciona de punta a
/// punta contra la API desplegada. En el Ciclo 2 se convierte en el armazon con
/// la barra de navegacion (Catalogo · Reservas · Mi cuenta) y cada quien cuelga
/// ahi sus pantallas.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/constantes.dart';
import '../../core/enrutado/router.dart';
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
            tooltip: 'Cerrar sesión',
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
          const _MiCuenta(),
          const SizedBox(height: 20),
          const _PendientesDelCiclo(),
          const _Gestion(),
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

/// Lo que ya se puede usar. Hoy es solo el perfil (CU-04); el catalogo y las
/// reservas se suman aqui cuando cada uno cierre su caso de uso.
class _MiCuenta extends StatelessWidget {
  const _MiCuenta();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          children: [
            const ListTile(
              dense: true,
              title: Text(
                'Mi cuenta',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
            ListTile(
              leading: const Icon(
                Icons.person_outline,
                color: ColoresVB.malva,
              ),
              title: const Text('Mi perfil'),
              subtitle: const Text('Datos, tallas, direcciones y contraseña'),
              trailing: const Icon(Icons.chevron_right, size: 20),
              onTap: () => context.push(Rutas.perfil),
            ),
          ],
        ),
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
    // El cuarto elemento es la ruta, o `null` si todavia no existe: lo que
    // esta hecho se abre desde aca y lo que no, se lista igual para que se vea
    // que falta sin ir a buscarlo al cronograma.
    // El tipo va escrito y no inferido: cuando las tres rutas existen, Dart
    // infiere String en vez de String? y las comprobaciones de abajo quedan
    // marcadas como siempre falsas. Declararlo nullable mantiene la lista
    // preparada para el Ciclo 3, donde vuelve a haber modulos sin ruta.
    const List<(String, String, IconData, String?)> modulos = [
      (
        'Catálogo',
        'CU-17 · CU-18',
        Icons.storefront_outlined,
        Rutas.catalogo,
      ),
      (
        'Reservas',
        'CU-22 · CU-23',
        Icons.event_available_outlined,
        Rutas.reservas,
      ),
      (
        'Vestidor virtual',
        'Prototipo · CU-21',
        Icons.camera_alt_outlined,
        Rutas.vestidor,
      ),
      (
        'Para vos',
        'CU-33 · IA',
        Icons.auto_awesome,
        Rutas.paraVos,
      ),
      (
        'Mis favoritos',
        'CU-20',
        Icons.favorite_border,
        Rutas.favoritos,
      ),
      (
        'Mi carrito',
        'CU-26 · CU-27',
        Icons.shopping_bag_outlined,
        Rutas.carrito,
      ),
      // CU-29. Va JUSTO despues del carrito: comprar y despues buscar lo
      // comprado es la secuencia natural, y hasta el 20/09 la segunda mitad
      // no existia en el telefono.
      (
        'Mis compras',
        'CU-29',
        Icons.receipt_long_outlined,
        Rutas.misCompras,
      ),
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          children: [
            const ListTile(
              dense: true,
              title: Text(
                'Ciclo 2',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
            for (final (titulo, casos, icono, ruta) in modulos)
              ListTile(
                leading: Icon(
                  icono,
                  color: ruta == null ? ColoresVB.malvaClaro : ColoresVB.malva,
                ),
                title: Text(titulo),
                subtitle: Text(casos),
                enabled: ruta != null,
                onTap: ruta == null ? null : () => context.push(ruta),
                trailing: Icon(
                  ruta == null ? Icons.circle_outlined : Icons.chevron_right,
                  size: 18,
                  color: const Color(0xFFD6C4CC),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// Las pantallas de gestión: tablero, reportes y bitácora.
///
/// SE MUESTRAN SEGÚN EL ROL, Y ESO CAMBIÓ EL 20/09/2026
/// ------------------------------------------------------
/// Antes «Pedir un reporte» aparecía para todo el mundo, con este argumento:
/// *el servidor rechaza a quien no corresponda, y esconderlo obligaría a la
/// pantalla de inicio a conocer los roles*.
///
/// **El argumento estaba mal.** Ofrecerle a un cliente una puerta que se le
/// cierra en la cara no es neutral: le dice que hay algo que podría hacer y
/// no puede, y lo manda a averiguar por qué. Un control que no hace nada es
/// peor que un control ausente.
///
/// Y la premisa tampoco era cierta: la sesión **sí** conoce el rol, viene en
/// `UsuarioAutenticado.rol` desde el primer ciclo.
///
/// El PROVEEDOR tampoco los ve: sus pantallas son otras y están en la web.
class _Gestion extends ConsumerWidget {
  const _Gestion();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sesion = ref.watch(sesionProvider);
    if (sesion is! SesionAbierta) return const SizedBox.shrink();

    final rol = sesion.usuario.rol;
    final esAdmin = rol == 'ADMINISTRADOR';
    final esEncargado = rol == 'ENCARGADO';
    if (!esAdmin && !esEncargado) return const SizedBox.shrink();

    // La bitácora es SOLO del administrador: dice a qué hora entra cada
    // empleado y qué toca. En manos de un encargado eso es vigilancia de sus
    // compañeros, no auditoría. Es la misma regla que aplica el servidor,
    // repetida acá para no ofrecer lo que después se rechaza.
    final entradas = <(String, String, IconData, String)>[
      ('Tablero', 'CU-36 · indicadores', Icons.dashboard_outlined, Rutas.tablero),
      ('Reportes', 'CU-37 · PDF y Excel', Icons.download_outlined, Rutas.reportes),
      ('Pedir un reporte', 'CU-35 · voz', Icons.mic_none, Rutas.reportePorVoz),
      if (esAdmin)
        ('Bitácora', 'CU-42 · quién hizo qué', Icons.history, Rutas.bitacora),
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          children: [
            const ListTile(
              dense: true,
              title: Text(
                'Gestión',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
            for (final (titulo, casos, icono, ruta) in entradas)
              ListTile(
                leading: Icon(icono, color: ColoresVB.malva),
                title: Text(titulo),
                subtitle: Text(casos),
                onTap: () => context.push(ruta),
                trailing: const Icon(
                  Icons.chevron_right,
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
