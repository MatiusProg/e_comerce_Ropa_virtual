/// CU-27 · El pedido y su pago --- pasos 3 a 5, en el teléfono.
///
/// AQUÍ VIVE D5, Y ES LO QUE PROTEGE LA PLATA
/// -------------------------------------------
/// El estado que muestra esta pantalla es **el que dice la base**, no el que
/// diga la pasarela ni el que suponga la app. Cuando el cliente vuelve del
/// navegador, la app no da el pago por bueno: vuelve a preguntar.
///
/// Mientras el webhook de CU-28 no llegue, el pedido sigue en `PENDIENTE_PAGO`
/// y la pantalla dice «estamos confirmando su pago». Es la verdad, y decir
/// «pagado» porque el navegador volvió sería regalar mercadería a quien escriba
/// esa dirección a mano.
///
/// LA PASARELA SE ABRE EN EL NAVEGADOR, NO EN UN WebView
/// ------------------------------------------------------
/// Meter la página de pago de un tercero en un WebView propio es exactamente lo
/// que los navegadores enseñan a desconfiar: el cliente no puede ver la barra
/// de direcciones ni el candado, que es como comprueba a quién le está dando la
/// tarjeta. Se abre fuera, con `LaunchMode.externalApplication`.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/tema.dart';
import '../../data/modelos/compra.dart';
import '../../data/repositorios/repositorio_compra.dart';
import 'estado_compra.dart';

class PantallaPedido extends ConsumerStatefulWidget {
  const PantallaPedido({super.key, required this.codigo, this.recienCreado});

  final String codigo;

  /// Lo que devolvió confirmar, cuando se llega desde el checkout. Trae la URL
  /// de pago, que la ficha del pedido **no** incluye: esa URL es de una sesión
  /// concreta de la pasarela y no se guarda para volver a entregarla.
  final PedidoCreado? recienCreado;

  @override
  ConsumerState<PantallaPedido> createState() => _PantallaPedidoState();
}

class _PantallaPedidoState extends ConsumerState<PantallaPedido>
    with WidgetsBindingObserver {
  bool _cancelando = false;

  @override
  void initState() {
    super.initState();
    // Escuchar el ciclo de vida es lo que cierra el flujo sin pedirle nada al
    // cliente: cuando vuelve del navegador, la app se reanuda y ahí se vuelve a
    // preguntar. Sin esto habría que confiar en que pulse «Actualizar».
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState estado) {
    if (estado == AppLifecycleState.resumed) _refrescar();
  }

  void _refrescar() => ref.invalidate(pedidoProvider(widget.codigo));

  @override
  Widget build(BuildContext context) {
    final pedido = ref.watch(pedidoProvider(widget.codigo));

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.codigo),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Actualizar el estado',
            onPressed: _refrescar,
          ),
        ],
      ),
      body: RefreshIndicator(
        color: ColoresVB.malva,
        onRefresh: () async => _refrescar(),
        child: switch (pedido) {
          AsyncData(:final value) => _contenido(value),
          AsyncError(:final error) => _fallo('$error'),
          _ => const Center(child: CircularProgressIndicator()),
        },
      ),
      bottomNavigationBar: pedido.hasValue && pedido.requireValue.estado.esperaPago
          ? _acciones(pedido.requireValue)
          : null,
    );
  }

  // --- Contenido ------------------------------------------------------------

  Widget _contenido(Pedido pedido) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
      children: [
        _Estado(pedido: pedido),
        const SizedBox(height: 16),

        if (pedido.estado.esperaPago && widget.recienCreado?.pagoReal == false)
          const _AvisoSimulado(),

        _Titulo('Entrega'),
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: Icon(
            pedido.modalidadEntrega == ModalidadEntrega.envio
                ? Icons.local_shipping_outlined
                : Icons.storefront_outlined,
          ),
          title: Text(
            pedido.modalidadEntrega?.rotulo ?? 'Entrega',
          ),
          subtitle: Text(
            pedido.modalidadEntrega == ModalidadEntrega.envio
                ? (pedido.direccionEnvio ?? 'Sin dirección')
                : pedido.sucursalNombre,
          ),
        ),

        const SizedBox(height: 8),
        _Titulo('Prendas'),
        for (final linea in pedido.lineas)
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            title: Text(linea.productoNombre),
            subtitle: Text(
              '${linea.descripcionVariante}  ·  ${linea.cantidad} x Bs ${linea.precioUnitario}',
            ),
            trailing: Text('Bs ${linea.subtotal}'),
          ),

        const Divider(height: 24),
        _Fila('Subtotal', 'Bs ${pedido.subtotal}'),
        if (pedido.descuento != '0.00' && pedido.descuento != '0')
          _Fila('Descuento', '− Bs ${pedido.descuento}'),
        const SizedBox(height: 4),
        _Fila('Total', 'Bs ${pedido.total}', fuerte: true),

        const SizedBox(height: 20),
        // El precio de estas líneas está CONGELADO: es el que se cobró, no el
        // que la prenda valga hoy. Decirlo evita la consulta de «¿por qué el
        // catálogo dice otro precio?».
        Text(
          'Los precios de este pedido quedaron fijos al confirmarlo.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }

  Widget _fallo(String mensaje) {
    return ListView(
      padding: const EdgeInsets.all(32),
      children: [
        const SizedBox(height: 48),
        const Icon(Icons.receipt_long_outlined, size: 56),
        const SizedBox(height: 16),
        Text(mensaje, textAlign: TextAlign.center),
        const SizedBox(height: 20),
        OutlinedButton.icon(
          onPressed: _refrescar,
          icon: const Icon(Icons.refresh),
          label: const Text('Reintentar'),
        ),
      ],
    );
  }

  // --- Acciones -------------------------------------------------------------

  Widget _acciones(Pedido pedido) {
    final url = widget.recienCreado?.urlPago;

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (url != null)
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  icon: const Icon(Icons.open_in_new),
                  label: const Text('Ir a pagar'),
                  onPressed: () => _abrirPasarela(url),
                ),
              )
            else
              // Se llegó acá sin la URL ---desde «tiene un pedido pendiente», o
              // reabriendo la app---. No se inventa una: la sesión de pago es
              // de un intento concreto. Lo honesto es decirlo y ofrecer lo que
              // sí se puede hacer.
              const Padding(
                padding: EdgeInsets.only(bottom: 8),
                child: Text(
                  'Para pagar este pedido, cancélelo y vuelva a confirmarlo '
                  'desde el carrito.',
                  textAlign: TextAlign.center,
                ),
              ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                icon: _cancelando
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.close),
                label: Text(_cancelando ? 'Cancelando…' : 'Cancelar el pedido'),
                onPressed: _cancelando ? null : () => _cancelar(pedido),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _abrirPasarela(String url) async {
    final abierto = await launchUrl(
      Uri.parse(url),
      // Fuera de la app, no en un WebView. Ver la nota de la cabecera.
      mode: LaunchMode.externalApplication,
    );
    if (!abierto && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No pudimos abrir el navegador para pagar.'),
        ),
      );
    }
    // Al volver, `didChangeAppLifecycleState` refresca. No se marca nada acá:
    // la app no sabe si el cliente pagó, y suponerlo sería D5 al revés.
  }

  Future<void> _cancelar(Pedido pedido) async {
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (contexto) => AlertDialog(
        title: const Text('¿Cancelar el pedido?'),
        content: const Text(
          'Las prendas que apartamos vuelven al catálogo y quedan disponibles '
          'para otros clientes.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(contexto, false),
            child: const Text('No'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(contexto, true),
            child: const Text('Cancelar el pedido'),
          ),
        ],
      ),
    );
    if (confirmado != true || !mounted) return;

    setState(() => _cancelando = true);
    try {
      await ref.read(repositorioCompraProvider).cancelar(pedido.codigo);
      if (!mounted) return;
      _refrescar();
      // El carrito sigue armado: cancelar el pedido no lo toca, así que el
      // cliente puede volver a confirmarlo sin rearmarlo.
      await ref.read(carritoProvider.notifier).refrescar();
    } on ErrorCompra catch (fallo) {
      if (!mounted) return;
      // El caso típico: el webhook llegó mientras el cliente miraba, o la
      // barrida ya lo venció. Refrescar es lo que corresponde, no reintentar.
      _refrescar();
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(fallo.mensaje)));
    } finally {
      if (mounted) setState(() => _cancelando = false);
    }
  }
}

// --- Piezas -----------------------------------------------------------------

/// La tarjeta de estado. Es lo primero que el cliente mira al volver del pago.
class _Estado extends StatelessWidget {
  const _Estado({required this.pedido});

  final Pedido pedido;

  @override
  Widget build(BuildContext context) {
    final (IconData icono, Color color, String titulo, String detalle) =
        switch (pedido.estado) {
      EstadoPedido.pendientePago => (
        Icons.hourglass_top,
        ColoresVB.oro,
        'Estamos confirmando su pago',
        // Se dice así y no «pendiente de pago» a secas porque el cliente que
        // acaba de pagar en la pasarela no entendería por qué sigue pendiente.
        // El webhook puede tardar unos segundos en llegar.
        _textoPendiente(pedido),
      ),
      EstadoPedido.pagada => (
        Icons.check_circle,
        Colors.green,
        'Pago confirmado',
        pedido.modalidadEntrega == ModalidadEntrega.envio
            ? 'Preparamos su pedido para enviarlo.'
            : 'Puede pasar a retirarlo por ${pedido.sucursalNombre}.',
      ),
      EstadoPedido.entregada => (
        Icons.inventory_2,
        Colors.green,
        'Entregado',
        'Gracias por su compra.',
      ),
      EstadoPedido.cancelada => (
        Icons.cancel,
        Theme.of(context).colorScheme.error,
        'Pedido cancelado',
        'Las prendas volvieron al catálogo.',
      ),
    };

    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icono, color: color, size: 32),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    titulo,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(detalle),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  static String _textoPendiente(Pedido pedido) {
    final falta = pedido.tiempoRestante;
    if (falta == null || falta.isNegative) {
      return 'Si ya pagó, tire hacia abajo para actualizar. Si no, el pedido '
          'se cancelará y sus prendas volverán al catálogo.';
    }
    final minutos = falta.inMinutes;
    return 'Apartamos sus prendas. Tiene '
        '${minutos < 1 ? "menos de un minuto" : "$minutos minutos"} para pagar. '
        'Si ya pagó, tire hacia abajo para actualizar.';
  }
}

class _AvisoSimulado extends StatelessWidget {
  const _AvisoSimulado();

  @override
  Widget build(BuildContext context) {
    return Card(
      color: ColoresVB.rosaPalido,
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            const Icon(Icons.science_outlined, color: ColoresVB.malvaOscuro),
            const SizedBox(width: 12),
            const Expanded(
              child: Text(
                'Modo de prueba: el pago no mueve dinero real, y el pedido '
                'queda pendiente hasta que se confirme desde el sistema.',
                style: TextStyle(color: ColoresVB.malvaOscuro, fontSize: 13),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Titulo extends StatelessWidget {
  const _Titulo(this.texto);

  final String texto;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Text(
        texto,
        style: Theme.of(context).textTheme.titleMedium?.copyWith(
          color: ColoresVB.malvaOscuro,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class _Fila extends StatelessWidget {
  const _Fila(this.rotulo, this.valor, {this.fuerte = false});

  final String rotulo;
  final String valor;
  final bool fuerte;

  @override
  Widget build(BuildContext context) {
    final estilo = fuerte
        ? Theme.of(context).textTheme.titleLarge?.copyWith(
            color: ColoresVB.malvaOscuro,
            fontWeight: FontWeight.bold,
          )
        : Theme.of(context).textTheme.bodyMedium;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [Text(rotulo, style: estilo), Text(valor, style: estilo)],
      ),
    );
  }
}
