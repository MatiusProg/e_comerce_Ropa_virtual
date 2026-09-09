/// CU-04 · Gestionar perfil del cliente.
///
/// Cierra la tercera y última deuda móvil del Ciclo 1. El alcance es el mismo
/// que el de la web: datos personales, tallas habituales, direcciones de
/// entrega y cambio de contraseña. Las **categorías preferidas** no están: su
/// tabla se estrena en el Ciclo 2 y es de Karen (§3 de la contrapropuesta).
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/red/excepciones.dart';
import '../../core/tema.dart';
import '../../data/modelos/perfil.dart';
import 'estado_perfil.dart';
import 'formularios_perfil.dart';

class PantallaPerfil extends ConsumerWidget {
  const PantallaPerfil({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final perfil = ref.watch(perfilProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Mi perfil')),
      body: perfil.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (fallo, _) => _Fallo(
          mensaje: fallo is ErrorApi
              ? fallo.mensaje
              : 'No se pudo cargar su perfil.',
          alReintentar: () => ref.invalidate(perfilProvider),
        ),
        data: (datos) => RefreshIndicator(
          onRefresh: () async => ref.invalidate(perfilProvider),
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              _DatosPersonales(perfil: datos),
              const SizedBox(height: 16),
              _Tallas(perfil: datos),
              const SizedBox(height: 16),
              _Direcciones(perfil: datos),
              const SizedBox(height: 16),
              OutlinedButton.icon(
                icon: const Icon(Icons.lock_outline),
                label: const Text('Cambiar contraseña'),
                onPressed: () => abrirCambioDeContrasena(context),
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}

class _Fallo extends StatelessWidget {
  const _Fallo({required this.mensaje, required this.alReintentar});

  final String mensaje;
  final VoidCallback alReintentar;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.cloud_off_outlined,
              size: 44,
              color: ColoresVB.malvaClaro,
            ),
            const SizedBox(height: 16),
            Text(mensaje, textAlign: TextAlign.center),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: alReintentar,
              child: const Text('Reintentar'),
            ),
          ],
        ),
      ),
    );
  }
}

/// Tarjeta con encabezado y botón de acción, repetida por las tres secciones.
class _Seccion extends StatelessWidget {
  const _Seccion({
    required this.titulo,
    required this.hijos,
    this.accion,
    this.iconoAccion = Icons.edit_outlined,
    this.tooltipAccion,
  });

  final String titulo;
  final List<Widget> hijos;
  final VoidCallback? accion;
  final IconData iconoAccion;
  final String? tooltipAccion;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 14, 12, 18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    titulo,
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 15,
                    ),
                  ),
                ),
                if (accion != null)
                  IconButton(
                    tooltip: tooltipAccion,
                    icon: Icon(iconoAccion, color: ColoresVB.malva),
                    onPressed: accion,
                  ),
              ],
            ),
            const SizedBox(height: 4),
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: hijos,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Una línea «rótulo: valor». El guion largo marca lo que no está cargado, que
/// se lee mejor que un hueco en blanco.
class _Dato extends StatelessWidget {
  const _Dato({required this.rotulo, required this.valor});

  final String rotulo;
  final String? valor;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 110,
            child: Text(
              rotulo,
              style: const TextStyle(fontSize: 13, color: Color(0xFF6B5A62)),
            ),
          ),
          Expanded(
            child: Text(
              valor?.isNotEmpty == true ? valor! : '—',
              style: const TextStyle(fontSize: 14),
            ),
          ),
        ],
      ),
    );
  }
}

class _DatosPersonales extends StatelessWidget {
  const _DatosPersonales({required this.perfil});

  final Perfil perfil;

  @override
  Widget build(BuildContext context) {
    return _Seccion(
      titulo: 'Datos personales',
      tooltipAccion: 'Editar mis datos',
      accion: () => abrirEdicionDeDatos(context, perfil),
      hijos: [
        _Dato(rotulo: 'Nombre', valor: perfil.nombreCompleto),
        _Dato(rotulo: 'Correo', valor: perfil.correo),
        _Dato(rotulo: 'Documento', valor: perfil.documento),
        _Dato(rotulo: 'Teléfono', valor: perfil.telefono),
      ],
    );
  }
}

class _Tallas extends StatelessWidget {
  const _Tallas({required this.perfil});

  final Perfil perfil;

  @override
  Widget build(BuildContext context) {
    return _Seccion(
      titulo: 'Tallas habituales',
      tooltipAccion: 'Editar mis tallas',
      accion: () => abrirEdicionDeDatos(context, perfil),
      hijos: [
        if (!perfil.tieneTallas)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 6),
            child: Text(
              'Cargue sus tallas y le recomendaremos prendas que le queden.',
              style: TextStyle(fontSize: 13, color: Color(0xFF6B5A62)),
            ),
          )
        else ...[
          _Dato(rotulo: 'Superior', valor: perfil.tallaSuperior),
          _Dato(rotulo: 'Inferior', valor: perfil.tallaInferior),
          _Dato(rotulo: 'Calzado', valor: perfil.tallaCalzado),
        ],
      ],
    );
  }
}

class _Direcciones extends ConsumerWidget {
  const _Direcciones({required this.perfil});

  final Perfil perfil;

  Future<void> _ejecutar(
    BuildContext context,
    WidgetRef ref,
    Future<void> Function() accion,
  ) async {
    try {
      await accion();
    } on ErrorApi catch (fallo) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(fallo.mensaje)));
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final control = ref.read(perfilProvider.notifier);

    return _Seccion(
      titulo: 'Direcciones de entrega',
      tooltipAccion: 'Agregar dirección',
      iconoAccion: Icons.add_location_alt_outlined,
      accion: () => abrirNuevaDireccion(context),
      hijos: [
        if (perfil.direcciones.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 6),
            child: Text(
              'Todavía no cargó ninguna dirección.',
              style: TextStyle(fontSize: 13, color: Color(0xFF6B5A62)),
            ),
          )
        else
          for (final direccion in perfil.direcciones)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Icon(
                direccion.predeterminada
                    ? Icons.location_on
                    : Icons.location_on_outlined,
                color: direccion.predeterminada
                    ? ColoresVB.malva
                    : ColoresVB.malvaClaro,
              ),
              title: Row(
                children: [
                  Flexible(child: Text(direccion.alias)),
                  if (direccion.predeterminada) ...[
                    const SizedBox(width: 8),
                    const _EtiquetaPredeterminada(),
                  ],
                ],
              ),
              subtitle: Text(
                [
                  direccion.direccion,
                  direccion.ciudad,
                  if (direccion.referencia != null) direccion.referencia!,
                ].join(' · '),
                style: const TextStyle(fontSize: 12),
              ),
              trailing: PopupMenuButton<String>(
                itemBuilder: (_) => [
                  if (!direccion.predeterminada)
                    const PopupMenuItem(
                      value: 'predeterminada',
                      child: Text('Usar como predeterminada'),
                    ),
                  const PopupMenuItem(
                    value: 'eliminar',
                    child: Text('Eliminar'),
                  ),
                ],
                onSelected: (opcion) => _ejecutar(context, ref, () {
                  return opcion == 'predeterminada'
                      ? control.marcarPredeterminada(direccion.id)
                      : control.eliminarDireccion(direccion.id);
                }),
              ),
            ),
      ],
    );
  }
}

class _EtiquetaPredeterminada extends StatelessWidget {
  const _EtiquetaPredeterminada();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: ColoresVB.rosaPalido,
        borderRadius: BorderRadius.circular(radioChicoVB),
      ),
      child: const Text(
        'Predeterminada',
        style: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w600,
          color: ColoresVB.malvaOscuro,
        ),
      ),
    );
  }
}
