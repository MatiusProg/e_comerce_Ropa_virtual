/// CU-27 · Realizar pedido y pagar en línea --- pasos 1 y 2, en el teléfono.
///
/// Una sola pantalla y no un asistente de tres pasos. En el teléfono, un
/// asistente para elegir dos cosas ---cómo recibir y dónde--- son dos toques de
/// más y una pantalla de resumen que repite lo que el cliente acaba de ver.
///
/// LO QUE ESTA PANTALLA DICE ANTES DE QUE EL CLIENTE CHOQUE
/// ---------------------------------------------------------
/// Un pedido se despacha desde UNA sucursal (`detalle_venta` no lleva sucursal
/// por línea), así que no todas pueden. En vez de dejar elegir y fallar al
/// confirmar, las que no pueden salen **deshabilitadas y con la prenda que les
/// falta nombrada**. Decir «no disponible» obligaría al cliente a adivinar cuál.
///
/// EL TOTAL QUE SE MANDA ES EL QUE EL CLIENTE VIO
/// ------------------------------------------------
/// El carrito lee precios en vivo. Entre que esta pantalla se pintó y el
/// cliente pulsó confirmar, la tienda pudo cambiar un precio. Se manda
/// `total_esperado` con la cadena tal cual vino del servidor; si no coincide,
/// el backend responde 409 con el total nuevo y **no cobra nada**, y acá se
/// abre el diálogo que muestra qué cambió.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/enrutado/router.dart';
import '../../core/tema.dart';
import '../../data/modelos/compra.dart';
import '../../data/repositorios/repositorio_compra.dart';
import 'estado_compra.dart';

class PantallaCheckout extends ConsumerStatefulWidget {
  const PantallaCheckout({super.key});

  @override
  ConsumerState<PantallaCheckout> createState() => _PantallaCheckoutState();
}

class _PantallaCheckoutState extends ConsumerState<PantallaCheckout> {
  ModalidadEntrega _modalidad = ModalidadEntrega.retiro;
  int? _sucursalId;
  int? _direccionId;
  bool _confirmando = false;

  @override
  Widget build(BuildContext context) {
    final opciones = ref.watch(opcionesDePedidoProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Confirmar pedido')),
      body: switch (opciones) {
        AsyncData(:final value) => _formulario(value),
        AsyncError(:final error) => _fallo('$error'),
        _ => const Center(child: CircularProgressIndicator()),
      },
      bottomNavigationBar: opciones.hasValue
          ? _barra(opciones.requireValue)
          : null,
    );
  }

  // --- El formulario --------------------------------------------------------

  Widget _formulario(OpcionesDePedido opciones) {
    // La primera vez se preselecciona: la sucursal que puede, y la dirección
    // predeterminada. El caso normal ---comprar como siempre--- no debería
    // exigir ninguna elección.
    _preseleccionar(opciones);

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
      children: [
        if (!opciones.sePuedePedir) ...[
          _Bloqueo(motivo: opciones.motivo ?? 'No se puede pedir ahora.'),
          const SizedBox(height: 16),
        ],

        _Titulo('¿Cómo quiere recibirlo?'),
        SegmentedButton<ModalidadEntrega>(
          segments: const [
            ButtonSegment(
              value: ModalidadEntrega.retiro,
              icon: Icon(Icons.storefront_outlined),
              label: Text('Retiro'),
            ),
            ButtonSegment(
              value: ModalidadEntrega.envio,
              icon: Icon(Icons.local_shipping_outlined),
              label: Text('Envío'),
            ),
          ],
          selected: {_modalidad},
          onSelectionChanged: (elegido) =>
              setState(() => _modalidad = elegido.first),
        ),
        const SizedBox(height: 20),

        if (_modalidad == ModalidadEntrega.retiro)
          ..._sucursales(opciones)
        else
          ..._direcciones(opciones),

        const SizedBox(height: 24),
        _Titulo('Su pedido'),
        for (final linea in opciones.lineas)
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
        if (!opciones.pagoReal) _AvisoPagoSimulado(),
        _AvisoVigencia(minutos: opciones.minutosParaPagar),
      ],
    );
  }

  List<Widget> _sucursales(OpcionesDePedido opciones) {
    return [
      _Titulo('¿En qué sucursal lo retira?'),
      RadioGroup<int>(
        groupValue: _sucursalId,
        onChanged: (valor) => setState(() => _sucursalId = valor),
        child: Column(
          children: [
            for (final sucursal in opciones.sucursales)
              RadioListTile<int>(
                value: sucursal.id,
                // Deshabilitada, no escondida: si la sucursal de siempre no
                // aparece, el cliente cree que cerró. Así ve que existe y por
                // qué no sirve para ESTE pedido.
                enabled: sucursal.abasteceTodo,
                title: Text(sucursal.nombre),
                subtitle: Text(
                  sucursal.abasteceTodo
                      ? '${sucursal.direccion} — ${sucursal.ciudad}'
                      : 'No tiene: ${sucursal.faltantes.join(", ")}',
                  style: sucursal.abasteceTodo
                      ? null
                      : TextStyle(color: Theme.of(context).colorScheme.error),
                ),
                contentPadding: EdgeInsets.zero,
              ),
          ],
        ),
      ),
    ];
  }

  List<Widget> _direcciones(OpcionesDePedido opciones) {
    if (opciones.direcciones.isEmpty) {
      return [
        _Titulo('¿A qué dirección?'),
        Card(
          color: ColoresVB.rosaPalido,
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Todavía no tiene direcciones registradas.'),
                const SizedBox(height: 10),
                OutlinedButton.icon(
                  onPressed: () => context.push(Rutas.perfil),
                  icon: const Icon(Icons.add_location_alt_outlined),
                  label: const Text('Agregar una en mi perfil'),
                ),
              ],
            ),
          ),
        ),
      ];
    }

    return [
      _Titulo('¿A qué dirección?'),
      RadioGroup<int>(
        groupValue: _direccionId,
        onChanged: (valor) => setState(() => _direccionId = valor),
        child: Column(
          children: [
            for (final direccion in opciones.direcciones)
              RadioListTile<int>(
                value: direccion.id,
                title: Row(
                  children: [
                    Text(direccion.alias),
                    if (direccion.predeterminada) ...[
                      const SizedBox(width: 8),
                      const _Etiqueta('Predeterminada'),
                    ],
                  ],
                ),
                subtitle: Text(
                  [
                    '${direccion.direccion} — ${direccion.ciudad}',
                    if (direccion.referencia != null) direccion.referencia!,
                  ].join('\n'),
                ),
                isThreeLine: direccion.referencia != null,
                contentPadding: EdgeInsets.zero,
              ),
          ],
        ),
      ),
      const SizedBox(height: 4),
      // En un envío la sucursal la elige el sistema. Pedirle al cliente que la
      // elija sería pedirle que sepa desde dónde se despacha, que no es asunto
      // suyo.
      Text(
        'Despachamos desde la sucursal que tenga todas sus prendas.',
        style: Theme.of(context).textTheme.bodySmall,
      ),
    ];
  }

  Widget _fallo(String mensaje) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off, size: 56),
            const SizedBox(height: 16),
            Text(mensaje, textAlign: TextAlign.center),
            const SizedBox(height: 20),
            OutlinedButton.icon(
              onPressed: () => ref.invalidate(opcionesDePedidoProvider),
              icon: const Icon(Icons.refresh),
              label: const Text('Reintentar'),
            ),
          ],
        ),
      ),
    );
  }

  // --- La barra de confirmar ------------------------------------------------

  Widget _barra(OpcionesDePedido opciones) {
    final destinoElegido = _modalidad == ModalidadEntrega.retiro
        ? _sucursalId != null
        : _direccionId != null;
    final habilitado =
        opciones.sePuedePedir && destinoElegido && !_confirmando;

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Total a pagar'),
                Text(
                  'Bs ${opciones.total}',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: ColoresVB.malvaOscuro,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                icon: _confirmando
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.lock_outline),
                label: Text(
                  _confirmando ? 'Creando su pedido…' : 'Confirmar y pagar',
                ),
                onPressed: habilitado ? () => _confirmar(opciones) : null,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // --- Confirmar ------------------------------------------------------------

  Future<void> _confirmar(OpcionesDePedido opciones) async {
    setState(() => _confirmando = true);
    try {
      final creado = await ref.read(repositorioCompraProvider).crear(
        CrearPedido(
          modalidadEntrega: _modalidad,
          // La MISMA cadena que mandó el servidor, sin reconstruirla. Ver la
          // nota de `compra.dart` sobre por qué el dinero no pasa por `double`.
          totalEsperado: opciones.total,
          sucursalId:
              _modalidad == ModalidadEntrega.retiro ? _sucursalId : null,
          direccionId: _modalidad == ModalidadEntrega.envio ? _direccionId : null,
        ),
      );
      if (!mounted) return;
      // El carrito NO se vacía acá: lo vacía CU-28 cuando el pago se confirma.
      // Lo que sí hay que hacer es refrescarlo, porque la pantalla del carrito
      // ahora tiene que mostrar que hay un pedido en curso.
      ref.invalidate(opcionesDePedidoProvider);
      context.pushReplacement(
        Rutas.pedidoDe(creado.pedido.codigo),
        extra: creado,
      );
    } on ErrorCompra catch (fallo) {
      if (!mounted) return;
      await _manejar(fallo);
    } finally {
      if (mounted) setState(() => _confirmando = false);
    }
  }

  /// Cada clase de error lleva a una acción distinta, y por eso el repositorio
  /// los clasifica en vez de devolver solo el texto.
  Future<void> _manejar(ErrorCompra fallo) async {
    switch (fallo.tipo) {
      case TipoErrorCompra.precioCambiado:
        await _dialogoPrecioCambiado(fallo);

      case TipoErrorCompra.pedidoPendiente:
        await _dialogoPedidoPendiente(fallo);

      case TipoErrorCompra.sinStock:
        // La pantalla quedó vieja: lo que corresponde es volver a pedir las
        // opciones, no reintentar contra un número que ya no vale.
        ref.invalidate(opcionesDePedidoProvider);
        _avisar(fallo.mensaje);

      case TipoErrorCompra.carritoInvalido:
        _avisar(fallo.mensaje);
        if (mounted) context.pop();

      default:
        _avisar(fallo.mensaje);
    }
  }

  /// El total cambió entre mirar y confirmar. **No se cobró nada.**
  ///
  /// Muestra los dos totales y deja decidir. Reintentar en silencio con el
  /// total nuevo sería cobrarle al cliente un precio que no aceptó, que es
  /// justamente lo que esta comprobación existe para impedir.
  Future<void> _dialogoPrecioCambiado(ErrorCompra fallo) async {
    final seguir = await showDialog<bool>(
      context: context,
      builder: (contexto) => AlertDialog(
        title: const Text('El precio cambió'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Mientras usted decidía, cambió el precio de alguna prenda. '
              'No le cobramos nada.',
            ),
            const SizedBox(height: 14),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Usted vio'),
                Text(
                  'Bs ${fallo.totalEsperado}',
                  style: const TextStyle(
                    decoration: TextDecoration.lineThrough,
                  ),
                ),
              ],
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Ahora es'),
                Text(
                  'Bs ${fallo.totalActual}',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(contexto, false),
            child: const Text('Revisar el carrito'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(contexto, true),
            child: const Text('Aceptar el nuevo total'),
          ),
        ],
      ),
    );
    if (!mounted) return;

    // En los dos caminos hay que recargar: el carrito de la pantalla anterior
    // y estas opciones traen el total viejo.
    await ref.read(carritoProvider.notifier).refrescar();
    ref.invalidate(opcionesDePedidoProvider);
    if (!mounted) return;

    if (seguir != true) context.pop();
  }

  /// Ya hay un pedido esperando pago.
  ///
  /// Ofrece ir a él en vez de dejar al cliente atascado leyendo un error: el
  /// mensaje del backend trae el código justamente para poder hacer esto.
  Future<void> _dialogoPedidoPendiente(ErrorCompra fallo) async {
    final ir = await showDialog<bool>(
      context: context,
      builder: (contexto) => AlertDialog(
        title: const Text('Tiene un pedido sin pagar'),
        content: Text(fallo.mensaje),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(contexto, false),
            child: const Text('Después'),
          ),
          if (fallo.codigoPedido != null)
            FilledButton(
              onPressed: () => Navigator.pop(contexto, true),
              child: const Text('Ver ese pedido'),
            ),
        ],
      ),
    );
    if (ir == true && mounted && fallo.codigoPedido != null) {
      context.pushReplacement(Rutas.pedidoDe(fallo.codigoPedido!));
    }
  }

  void _avisar(String mensaje) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(mensaje)));
  }

  // --- Interno --------------------------------------------------------------

  bool _yaPreseleccionado = false;

  void _preseleccionar(OpcionesDePedido opciones) {
    if (_yaPreseleccionado) return;
    _yaPreseleccionado = true;
    final puede = opciones.sucursalesQuePueden;
    _sucursalId = puede.isEmpty ? null : puede.first.id;
    _direccionId =
        opciones.direcciones.isEmpty ? null : opciones.direcciones.first.id;
  }
}

// --- Piezas -----------------------------------------------------------------

class _Titulo extends StatelessWidget {
  const _Titulo(this.texto);

  final String texto;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
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

class _Etiqueta extends StatelessWidget {
  const _Etiqueta(this.texto);

  final String texto;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: ColoresVB.rosaPalido,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Text(
        texto,
        style: const TextStyle(fontSize: 11, color: ColoresVB.malvaOscuro),
      ),
    );
  }
}

class _Bloqueo extends StatelessWidget {
  const _Bloqueo({required this.motivo});

  final String motivo;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: Theme.of(context).colorScheme.errorContainer,
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            const Icon(Icons.block),
            const SizedBox(width: 12),
            Expanded(child: Text(motivo)),
          ],
        ),
      ),
    );
  }
}

/// El aviso de que el pago es de mentira.
///
/// Sale de `pago_real` que manda el servidor, no de adivinar por el nombre del
/// proveedor: eso obligaría a la app a conocer la lista. Y se muestra a
/// propósito: hacer pasar un pago simulado por real sería engañar a quien mira
/// la demostración.
class _AvisoPagoSimulado extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Card(
      color: ColoresVB.rosaPalido,
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            const Icon(Icons.science_outlined, color: ColoresVB.malvaOscuro),
            const SizedBox(width: 12),
            const Expanded(
              child: Text(
                'Pago en modo de prueba: no se cobra dinero real.',
                style: TextStyle(color: ColoresVB.malvaOscuro),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AvisoVigencia extends StatelessWidget {
  const _AvisoVigencia({required this.minutos});

  final int minutos;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Icon(Icons.timer_outlined, size: 18),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            'Al confirmar apartamos sus prendas durante $minutos minutos. '
            'Si no paga en ese plazo, el pedido se cancela y vuelven al catálogo.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ),
      ],
    );
  }
}
