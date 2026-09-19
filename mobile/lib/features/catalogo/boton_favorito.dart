/// CU-20 · El corazón. Se usa en la tarjeta del catálogo y en la ficha.
///
/// Está aparte porque son dos pantallas y el comportamiento tiene que ser el
/// mismo en las dos: el mismo aviso al fallar, la misma regla para el invitado
/// y el mismo dibujo. Duplicarlo es cómo terminan discrepando.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/enrutado/router.dart';
import '../auth/estado_sesion.dart';
import 'estado_favoritos.dart';

class BotonFavorito extends ConsumerWidget {
  const BotonFavorito({
    super.key,
    required this.productoId,
    this.sobreFoto = false,
  });

  final int productoId;

  /// Si va encima de la imagen del producto. Cambia el fondo, porque un
  /// corazón blanco sobre una prenda clara no se ve.
  final bool sobreFoto;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hayaSesion = ref.watch(sesionProvider) is SesionAbierta;
    final favoritos = ref.watch(favoritosProvider);
    final esFavorito = favoritos.value?.contains(productoId) ?? false;

    final icono = Icon(
      esFavorito ? Icons.favorite : Icons.favorite_border,
      size: 20,
      color: esFavorito
          ? const Color(0xFFD64562)
          : (sobreFoto ? Colors.white : Colors.black54),
    );

    final boton = IconButton(
      onPressed: () => _alternar(context, ref, hayaSesion),
      icon: icono,
      // El área táctil por omisión es de 48 px y en la tarjeta se come la
      // esquina de la foto. Se achica la caja, NO el área: 36 px sigue por
      // encima del mínimo con el que se puede acertar sin mirar.
      constraints: const BoxConstraints.tightFor(width: 36, height: 36),
      padding: EdgeInsets.zero,
      splashRadius: 20,
      tooltip: esFavorito ? 'Quitar de favoritos' : 'Guardar en favoritos',
    );

    if (!sobreFoto) return boton;

    // Sobre la foto va un círculo oscuro translúcido: sin él, el contorno del
    // corazón desaparece sobre una prenda blanca, que son la mitad.
    return DecoratedBox(
      decoration: const BoxDecoration(
        color: Color(0x66000000),
        shape: BoxShape.circle,
      ),
      child: boton,
    );
  }

  Future<void> _alternar(
    BuildContext context,
    WidgetRef ref,
    bool hayaSesion,
  ) async {
    // El invitado puede recorrer la vitrina entera sin cuenta (CU-17), así que
    // el corazón se le muestra igual. Lo que no puede es guardar: en vez de un
    // error, se le ofrece entrar, que es lo que necesita hacer.
    if (!hayaSesion) {
      final ir = await showDialog<bool>(
        context: context,
        builder: (contexto) => AlertDialog(
          title: const Text('Iniciá sesión'),
          content: const Text(
            'Tus prendas favoritas se guardan en tu cuenta, así las tenés '
            'también desde la web.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(contexto).pop(false),
              child: const Text('Ahora no'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(contexto).pop(true),
              child: const Text('Iniciar sesión'),
            ),
          ],
        ),
      );
      if (ir == true && context.mounted) context.push(Rutas.login);
      return;
    }

    try {
      await ref.read(favoritosProvider.notifier).alternar(productoId);
    } catch (fallo) {
      if (!context.mounted) return;
      // El corazón ya volvió a su estado anterior solo; esto solo explica por
      // qué. Sin el aviso, el corazón «rebota» y parece un defecto de la app.
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No se pudo guardar: $fallo')),
      );
    }
  }
}
