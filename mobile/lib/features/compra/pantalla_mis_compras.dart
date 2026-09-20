/// CU-29 · Consultar historial de compras, en el teléfono.
///
/// POR QUÉ ESTA PANTALLA EXISTE
/// -----------------------------
/// El caso de uso estaba construido en el servidor y en la web, y **desde el
/// teléfono no había forma de llegar**: se veía el pedido recién pagado —la
/// pantalla de CU-27 vuelve a él— y nada más. Comprar y después no poder
/// volver a ver la compra es lo primero que alguien intenta.
///
/// Es la cuarta vez en el Ciclo 3 que aparece el mismo agujero: CU-33, CU-37,
/// los datos de CU-39 y ahora este. Un caso de uso sin forma de llegar no
/// está hecho.
///
/// SE MUESTRAN TODAS, TAMBIÉN LAS QUE NO SE PAGARON
/// --------------------------------------------------
/// Es la regla del servidor y la pantalla la respeta. Un historial que solo
/// mostrara lo cobrado dejaría al cliente sin encontrar el pedido que acaba
/// de hacer —que es justo el que va a buscar— ni entender por qué un cobro
/// que recuerda no aparece. **El estado se muestra; la fila no se esconde.**
///
/// LA FILA LLEVA EL TOTAL Y EL ESTADO, NO LAS PRENDAS
/// ----------------------------------------------------
/// El pedido ya viene con sus líneas, así que dibujarlas sería gratis, pero
/// una lista donde cada fila mide media pantalla deja de ser una lista. Lo
/// que se busca acá es *cuál* compra; el detalle está a un toque.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/enrutado/router.dart';
import '../../core/hora_boliviana.dart';
import '../../core/red/excepciones.dart';
import '../../core/tema.dart';
import '../../data/modelos/compra.dart';
import 'estado_compra.dart';

class PantallaMisCompras extends ConsumerWidget {
  const PantallaMisCompras({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final compras = ref.watch(misComprasProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Mis compras')),
      body: RefreshIndicator(
        color: ColoresVB.malva,
        // Tirar para refrescar es lo que el cliente va a hacer al volver de
        // la pasarela: el webhook de CU-28 puede llegar unos segundos después
        // y el estado cambia de «Esperando el pago» a «Pagado» sin que nada
        // lo empuje desde el servidor.
        onRefresh: () async => ref.invalidate(misComprasProvider),
        child: compras.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (fallo, _) => _Aviso(
            icono: Icons.cloud_off,
            titulo: 'No se pudo cargar tu historial',
            detalle: fallo is ErrorApi
                ? fallo.mensaje
                : 'Revisá tu conexión y volvé a intentar.',
            alReintentar: () => ref.invalidate(misComprasProvider),
          ),
          data: (pagina) => pagina.items.isEmpty
              ? _Aviso(
                  icono: Icons.shopping_bag_outlined,
                  titulo: 'Todavía no compraste nada',
                  detalle:
                      'Cuando hagas tu primer pedido lo vas a encontrar acá, '
                      'con su comprobante.',
                  textoAccion: 'Ver el catálogo',
                  alReintentar: () => context.go(Rutas.catalogo),
                )
              : ListView.separated(
                  // `always` aunque la lista sea corta: sin esto, el gesto de
                  // tirar para refrescar no funciona cuando entran tres
                  // compras en la pantalla, que es el caso común.
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(12),
                  itemCount: pagina.items.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, i) => _FilaDeCompra(pedido: pagina.items[i]),
                ),
        ),
      ),
    );
  }
}

class _FilaDeCompra extends StatelessWidget {
  const _FilaDeCompra({required this.pedido});

  final Pedido pedido;

  @override
  Widget build(BuildContext context) {
    final cuantas = pedido.lineas.fold<int>(0, (s, l) => s + l.cantidad);

    return Card(
      clipBehavior: Clip.antiAlias,
      child: ListTile(
        onTap: () => context.push('/carrito/${pedido.codigo}'),
        leading: CircleAvatar(
          backgroundColor: _fondoDelEstado(pedido.estado),
          foregroundColor: _tintaDelEstado(pedido.estado),
          child: Icon(_iconoDelEstado(pedido.estado), size: 20),
        ),
        title: Text(
          pedido.codigo,
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 2),
            Text(
              '${DateFormat('dd/MM/yyyy HH:mm').format(enHoraBoliviana(pedido.creadoEn))}'
              ' · $cuantas prenda${cuantas == 1 ? '' : 's'}',
              style: const TextStyle(fontSize: 12),
            ),
            const SizedBox(height: 4),
            _Pastilla(
              texto: pedido.estado.rotulo,
              fondo: _fondoDelEstado(pedido.estado),
              tinta: _tintaDelEstado(pedido.estado),
            ),
          ],
        ),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              'Bs ${pedido.total}',
              style: const TextStyle(
                fontWeight: FontWeight.bold,
                color: ColoresVB.malvaOscuro,
              ),
            ),
            const Icon(Icons.chevron_right, color: Colors.black38),
          ],
        ),
        isThreeLine: true,
      ),
    );
  }
}

/// El estado se distingue por **color e icono**, no solo por color: quien no
/// distingue rojo y verde tiene que poder ver igual si su pedido se pagó.
IconData _iconoDelEstado(EstadoPedido estado) => switch (estado) {
  EstadoPedido.pagada => Icons.check_circle_outline,
  EstadoPedido.entregada => Icons.local_shipping_outlined,
  EstadoPedido.cancelada => Icons.cancel_outlined,
  EstadoPedido.pendientePago => Icons.schedule,
};

Color _fondoDelEstado(EstadoPedido estado) => switch (estado) {
  EstadoPedido.pagada || EstadoPedido.entregada => const Color(0xFFE3F2E5),
  EstadoPedido.cancelada => const Color(0xFFFBE3E3),
  EstadoPedido.pendientePago => const Color(0xFFFFF2DC),
};

Color _tintaDelEstado(EstadoPedido estado) => switch (estado) {
  EstadoPedido.pagada || EstadoPedido.entregada => const Color(0xFF1B5E20),
  EstadoPedido.cancelada => const Color(0xFFB3261E),
  EstadoPedido.pendientePago => const Color(0xFF8A5300),
};

class _Pastilla extends StatelessWidget {
  const _Pastilla({
    required this.texto,
    required this.fondo,
    required this.tinta,
  });

  final String texto;
  final Color fondo;
  final Color tinta;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: fondo,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        texto,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: tinta,
        ),
      ),
    );
  }
}

/// Un cartel que ocupa la pantalla, para el error y para la lista vacía.
///
/// Va dentro de un `ListView` y no de un `Center` a propósito: si no, no hay
/// nada que arrastrar y el gesto de tirar para refrescar no existe justo
/// cuando más se lo necesita —cuando no cargó—.
class _Aviso extends StatelessWidget {
  const _Aviso({
    required this.icono,
    required this.titulo,
    required this.detalle,
    this.textoAccion = 'Reintentar',
    this.alReintentar,
  });

  final IconData icono;
  final String titulo;
  final String detalle;
  final String textoAccion;
  final VoidCallback? alReintentar;

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(24, 80, 24, 24),
      children: [
        Icon(icono, size: 56, color: ColoresVB.malvaClaro),
        const SizedBox(height: 16),
        Text(
          titulo,
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        Text(
          detalle,
          textAlign: TextAlign.center,
          style: const TextStyle(color: Colors.black54),
        ),
        const SizedBox(height: 20),
        if (alReintentar != null)
          Center(
            child: FilledButton(
              onPressed: alReintentar,
              style: FilledButton.styleFrom(backgroundColor: ColoresVB.malva),
              child: Text(textoAccion),
            ),
          ),
      ],
    );
  }
}
