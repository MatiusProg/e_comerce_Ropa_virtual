/// CU-26 · Gestionar carrito de compras --- pantalla móvil.
///
/// Karen difirió la pantalla móvil del carrito a CU-27 a propósito: hasta que
/// la compra no se pudiera completar, un carrito en el teléfono era un callejón
/// sin salida. Ahora sí se puede, así que llega con su botón de pagar.
///
/// LO QUE ESTA PANTALLA NO HACE, Y ES DELIBERADO
/// ----------------------------------------------
/// **No calcula el total.** Lo recibe del servidor en cada respuesta. Sumar acá
/// los subtotales daría el mismo número casi siempre, y el día que no ---una
/// promoción, un redondeo--- la app diría un precio y la caja otro.
///
/// **No decide qué está disponible.** Una prenda que dejó de ofrecerse llega
/// marcada con `disponible: false` y se muestra tachada, no se esconde: si
/// desapareciera, el cliente vería bajar el total sin entender por qué.
library;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/enrutado/router.dart';
import '../../core/tema.dart';
import '../../data/modelos/compra.dart';
import '../../data/repositorios/repositorio_catalogo.dart';
import 'estado_compra.dart';

class PantallaCarrito extends ConsumerWidget {
  const PantallaCarrito({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final carrito = ref.watch(carritoProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Mi carrito'),
        actions: [
          if (carrito.value?.estaVacio == false)
            IconButton(
              icon: const Icon(Icons.delete_sweep_outlined),
              tooltip: 'Vaciar el carrito',
              onPressed: () => _confirmarVaciar(context, ref),
            ),
        ],
      ),
      body: RefreshIndicator(
        color: ColoresVB.malva,
        // Tirar para refrescar no es adorno acá: los precios se leen en vivo,
        // así que el carrito que quedó abierto anoche puede tener otro total.
        onRefresh: () => ref.read(carritoProvider.notifier).refrescar(),
        child: switch (carrito) {
          AsyncData(:final value) when value.estaVacio => const _Vacio(),
          AsyncData(:final value) => _Contenido(carrito: value),
          AsyncError(:final error) => _Fallo(mensaje: '$error'),
          _ => const Center(child: CircularProgressIndicator()),
        },
      ),
      bottomNavigationBar: carrito.value?.estaVacio == false
          ? _BarraDePago(carrito: carrito.value!)
          : null,
    );
  }

  Future<void> _confirmarVaciar(BuildContext context, WidgetRef ref) async {
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (contexto) => AlertDialog(
        title: const Text('¿Vaciar el carrito?'),
        content: const Text('Se quitarán todas las prendas. No se puede deshacer.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(contexto, false),
            child: const Text('No'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(contexto, true),
            child: const Text('Vaciar'),
          ),
        ],
      ),
    );
    if (confirmado != true || !context.mounted) return;

    final fallo = await ref.read(carritoProvider.notifier).vaciar();
    if (fallo != null && context.mounted) _avisar(context, fallo);
  }
}

void _avisar(BuildContext context, String mensaje) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(mensaje)));
}

// --- Estados de la pantalla -------------------------------------------------

class _Vacio extends StatelessWidget {
  const _Vacio();

  @override
  Widget build(BuildContext context) {
    // En un `ListView` y no en un `Center` a propósito: sin algo desplazable,
    // `RefreshIndicator` no reacciona y el cliente no puede tirar para
    // refrescar justo en la pantalla donde más ganas tiene de hacerlo.
    return ListView(
      padding: const EdgeInsets.all(32),
      children: [
        const SizedBox(height: 64),
        Icon(
          Icons.shopping_bag_outlined,
          size: 72,
          color: ColoresVB.malvaClaro,
        ),
        const SizedBox(height: 16),
        Text(
          'Su carrito está vacío',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        const Text(
          'Las prendas que agregue desde el catálogo aparecen acá.',
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 24),
        FilledButton.icon(
          onPressed: () => context.go(Rutas.catalogo),
          icon: const Icon(Icons.storefront_outlined),
          label: const Text('Ver el catálogo'),
        ),
      ],
    );
  }
}

class _Fallo extends ConsumerWidget {
  const _Fallo({required this.mensaje});

  final String mensaje;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ListView(
      padding: const EdgeInsets.all(32),
      children: [
        const SizedBox(height: 64),
        const Icon(Icons.cloud_off, size: 64),
        const SizedBox(height: 16),
        Text(mensaje, textAlign: TextAlign.center),
        const SizedBox(height: 24),
        OutlinedButton.icon(
          onPressed: () => ref.read(carritoProvider.notifier).refrescar(),
          icon: const Icon(Icons.refresh),
          label: const Text('Reintentar'),
        ),
      ],
    );
  }
}

class _Contenido extends StatelessWidget {
  const _Contenido({required this.carrito});

  final Carrito carrito;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 24),
      children: [
        if (carrito.noDisponibles > 0) ...[
          _AvisoPrendasCaidas(cuantas: carrito.noDisponibles),
          const SizedBox(height: 12),
        ],
        for (final linea in carrito.lineas) ...[
          _Linea(linea: linea),
          const SizedBox(height: 8),
        ],
      ],
    );
  }
}

/// El aviso de que el total bajó, y por qué.
///
/// Va arriba y no junto a la línea: el cliente mira el total primero, y si no
/// encuentra la explicación ahí arriba, cree que el sistema se equivocó.
class _AvisoPrendasCaidas extends StatelessWidget {
  const _AvisoPrendasCaidas({required this.cuantas});

  final int cuantas;

  @override
  Widget build(BuildContext context) {
    final texto = cuantas == 1
        ? 'Una prenda de su carrito ya no se ofrece. No suma al total.'
        : '$cuantas prendas de su carrito ya no se ofrecen. No suman al total.';
    return Card(
      color: Theme.of(context).colorScheme.errorContainer,
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            const Icon(Icons.info_outline),
            const SizedBox(width: 12),
            Expanded(child: Text(texto)),
          ],
        ),
      ),
    );
  }
}

class _Linea extends ConsumerStatefulWidget {
  const _Linea({required this.linea});

  final LineaCarrito linea;

  @override
  ConsumerState<_Linea> createState() => _LineaState();
}

class _LineaState extends ConsumerState<_Linea> {
  /// Mientras una operación de ESTA línea está en vuelo. Es por línea y no
  /// global: bloquear el carrito entero porque el cliente subió una unidad de
  /// una blusa haría que la pantalla se sienta trabada.
  bool _ocupada = false;

  @override
  Widget build(BuildContext context) {
    final linea = widget.linea;
    final caida = !linea.disponible;

    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _Miniatura(url: linea.imagenUrl, apagada: caida),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    linea.productoNombre,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      decoration: caida ? TextDecoration.lineThrough : null,
                    ),
                  ),
                  Text(
                    linea.descripcionVariante,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(height: 6),
                  if (caida)
                    Text(
                      'Ya no se ofrece',
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                        fontWeight: FontWeight.w600,
                      ),
                    )
                  else ...[
                    Text('Bs ${linea.precioUnitario} c/u'),
                    if (linea.stockTotal <= 3)
                      Text(
                        linea.stockTotal == 0
                            ? 'Sin unidades ahora mismo'
                            : 'Quedan ${linea.stockTotal}',
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                          fontSize: 12,
                        ),
                      ),
                  ],
                  const SizedBox(height: 6),
                  _Cantidad(
                    cantidad: linea.cantidad,
                    habilitada: !caida && !_ocupada,
                    alCambiar: _fijar,
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  'Bs ${linea.subtotal}',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                IconButton(
                  icon: const Icon(Icons.close),
                  tooltip: 'Quitar',
                  onPressed: _ocupada ? null : _quitar,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _fijar(int cantidad) async {
    setState(() => _ocupada = true);
    final fallo = await ref
        .read(carritoProvider.notifier)
        .fijarCantidad(varianteId: widget.linea.varianteId, cantidad: cantidad);
    if (mounted) setState(() => _ocupada = false);
    if (fallo != null && mounted) _avisar(context, fallo);
  }

  Future<void> _quitar() async {
    setState(() => _ocupada = true);
    final fallo =
        await ref.read(carritoProvider.notifier).quitar(widget.linea.varianteId);
    if (mounted) setState(() => _ocupada = false);
    if (fallo != null && mounted) _avisar(context, fallo);
  }
}

class _Miniatura extends StatelessWidget {
  const _Miniatura({required this.url, required this.apagada});

  final String? url;
  final bool apagada;

  @override
  Widget build(BuildContext context) {
    final resuelta = url == null ? null : RepositorioCatalogo.urlDeImagen(url);
    final imagen = ClipRRect(
      borderRadius: BorderRadius.circular(8),
      child: SizedBox(
        width: 64,
        height: 80,
        child: resuelta == null
            ? Container(
                color: ColoresVB.rosaPalido,
                child: const Icon(Icons.checkroom, color: ColoresVB.malvaClaro),
              )
            : CachedNetworkImage(
                imageUrl: resuelta,
                fit: BoxFit.cover,
                errorWidget: (contexto, ruta, fallo) => Container(
                  color: ColoresVB.rosaPalido,
                  child: const Icon(Icons.checkroom, color: ColoresVB.malvaClaro),
                ),
              ),
      ),
    );
    // Apagar la miniatura de una prenda caída dice, sin texto, que esa línea ya
    // no cuenta. El texto está igual: esto lo refuerza, no lo reemplaza.
    return apagada ? Opacity(opacity: 0.4, child: imagen) : imagen;
  }
}

/// El selector de cantidad. **FIJA** la cantidad, no la suma.
///
/// Es la operación contraria a «Agregar» de la ficha, y va por otro verbo a
/// propósito: un mismo control que a veces sume y a veces fije sería imposible
/// de usar sin mirar el código.
class _Cantidad extends StatelessWidget {
  const _Cantidad({
    required this.cantidad,
    required this.habilitada,
    required this.alCambiar,
  });

  final int cantidad;
  final bool habilitada;
  final void Function(int) alCambiar;

  /// El mismo tope que declara el backend en `carrito_schemas.py`. Se repite
  /// acá para poder deshabilitar el botón en vez de dejar que el cliente pulse
  /// y reciba un error: el viaje sobra cuando la respuesta ya se sabe.
  static const int maximo = 20;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        _Boton(
          icono: Icons.remove,
          // En 1 se deshabilita en vez de bajar a 0: cero no es una línea, es
          // una línea borrada, y para eso está la X.
          alPulsar: habilitada && cantidad > 1 ? () => alCambiar(cantidad - 1) : null,
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Text('$cantidad', style: const TextStyle(fontSize: 16)),
        ),
        _Boton(
          icono: Icons.add,
          alPulsar:
              habilitada && cantidad < maximo ? () => alCambiar(cantidad + 1) : null,
        ),
      ],
    );
  }
}

class _Boton extends StatelessWidget {
  const _Boton({required this.icono, required this.alPulsar});

  final IconData icono;
  final VoidCallback? alPulsar;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 34,
      height: 34,
      child: IconButton(
        padding: EdgeInsets.zero,
        iconSize: 18,
        style: IconButton.styleFrom(
          backgroundColor: ColoresVB.rosaPalido,
          foregroundColor: ColoresVB.malvaOscuro,
        ),
        icon: Icon(icono),
        onPressed: alPulsar,
      ),
    );
  }
}

/// El total y el botón de pagar, fijos abajo.
///
/// Fijos y no al final de la lista: con seis prendas, un botón que hay que ir a
/// buscar desplazando es un botón que no se pulsa.
class _BarraDePago extends StatelessWidget {
  const _BarraDePago({required this.carrito});

  final Carrito carrito;

  @override
  Widget build(BuildContext context) {
    final hayCaidas = carrito.noDisponibles > 0;

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '${carrito.unidades} ${carrito.unidades == 1 ? "unidad" : "unidades"}',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                Text(
                  'Bs ${carrito.total}',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: ColoresVB.malvaOscuro,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            // El total va SIN descuentos y la pantalla lo dice. Mostrar un
            // «descuentos: 0,00» parecería un total final ya calculado, y las
            // promociones (CU-12) todavía no existen.
            const SizedBox(height: 2),
            Align(
              alignment: Alignment.centerRight,
              child: Text(
                'Sin promociones aplicadas',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                icon: const Icon(Icons.lock_outline),
                label: const Text('Continuar con la compra'),
                // Con prendas caídas el botón se apaga: el pedido no admite un
                // carrito a medias, y es mejor decirlo acá que dejar que el
                // servidor lo rechace después de tres pantallas.
                onPressed:
                    hayCaidas ? null : () => context.push(Rutas.checkout),
              ),
            ),
            if (hayCaidas)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(
                  'Quite las prendas que ya no se ofrecen para continuar.',
                  style: TextStyle(
                    color: Theme.of(context).colorScheme.error,
                    fontSize: 12,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
