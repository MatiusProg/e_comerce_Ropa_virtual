/// CU-21 · Gestionar el inventario de la sucursal (2do parcial), en el movil.
///
/// Para el ENCARGADO. Todo sale del paquete guardado en SQLite, asi que la
/// consulta funciona igual sin red. Sin red tambien se registran ingresos y
/// conteos: van a la misma cola de CU-17 y los confirma el servidor.
///
/// El kardex es lo unico que pide red: es la historia completa de la prenda
/// y vive en el servidor.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/enrutado/router.dart';
import '../../core/red/excepciones.dart';
import '../../core/tema.dart';
import '../../data/modelos/inventario_offline.dart';
import '../../data/modelos/offline.dart';
import '../../data/repositorios/repositorio_offline.dart';
import '../offline/estado_offline.dart';

final _fecha = DateFormat('dd/MM HH:mm');

/// Lo mismo que `MOTIVO_LONGITUD_MINIMA` del backend.
const _motivoMinimo = 5;

String _mensaje(Object e) => switch (e) {
      SinRespuesta() => 'No hay conexión con el servidor.',
      ErrorApi(:final mensaje) => mensaje,
      _ => 'No se pudo completar la operación.',
    };

class PantallaInventario extends ConsumerStatefulWidget {
  const PantallaInventario({super.key});

  @override
  ConsumerState<PantallaInventario> createState() => _PantallaInventarioState();
}

class _PantallaInventarioState extends ConsumerState<PantallaInventario> {
  bool _preparando = false;
  String _busqueda = '';

  @override
  void initState() {
    super.initState();
    // Con red, se refresca solo al entrar: la consulta sale del teléfono y
    // así no muestra el saldo de ayer si hay internet.
    Future.microtask(() async {
      final estado = ref.read(offlineProvider);
      if (estado.enLinea) await _preparar(silencioso: true);
    });
  }

  Future<void> _preparar({bool silencioso = false}) async {
    setState(() => _preparando = true);
    try {
      final p = await ref.read(offlineProvider.notifier).prepararInventario();
      if (!silencioso && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Listo: ${p.prendas.length} prendas guardadas en el teléfono.')),
        );
      }
    } catch (e) {
      if (e is SinRespuesta) ref.read(offlineProvider.notifier).marcarSinRed();
      if (!silencioso && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_mensaje(e))));
      }
    } finally {
      if (mounted) setState(() => _preparando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final estado = ref.watch(offlineProvider);
    final paquete = estado.inventario;
    final texto = _busqueda.trim().toLowerCase();
    final prendas = (paquete?.prendas ?? const <PrendaInventario>[])
        .where((p) =>
            texto.isEmpty ||
            p.sku.toLowerCase().contains(texto) ||
            p.producto.toLowerCase().contains(texto))
        .toList();
    final pendientes = estado.pendientes.where((o) => esDeInventario(o.cuerpo)).length;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Inventario'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Chip(
              avatar: Icon(estado.enLinea ? Icons.cloud_done_outlined : Icons.cloud_off, size: 18),
              label: Text(estado.enLinea ? 'En línea' : 'Sin conexión'),
            ),
          ),
        ],
      ),
      floatingActionButton: paquete == null
          ? null
          : FloatingActionButton.extended(
              onPressed: () => context.push(Rutas.inventarioIngreso),
              backgroundColor: ColoresVB.malva,
              foregroundColor: Colors.white,
              icon: const Icon(Icons.local_shipping_outlined),
              label: const Text('Ingreso'),
            ),
      body: !estado.cargado
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: () async {
                await ref.read(offlineProvider.notifier).sincronizar();
                await _preparar(silencioso: true);
              },
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
                children: [
                  _tarjetaEstado(context, paquete, pendientes, estado),
                  if (paquete != null) ...[
                    const SizedBox(height: 12),
                    TextField(
                      decoration: const InputDecoration(
                        prefixIcon: Icon(Icons.search),
                        labelText: 'Buscar por SKU o nombre',
                      ),
                      onChanged: (v) => setState(() => _busqueda = v),
                    ),
                    const SizedBox(height: 8),
                    for (final p in prendas.take(200))
                      Card(
                        child: ListTile(
                          title: Text(p.nombre),
                          subtitle: Text('${p.sku} · ${p.disponible} disponibles · ${p.reservada} reservadas'),
                          trailing: p.bajoMinimo
                              ? Icon(Icons.warning_amber, color: Colors.orange.shade800)
                              : const Icon(Icons.chevron_right),
                          onTap: () => _abrirPrenda(context, p, estado.enLinea),
                        ),
                      ),
                    if (prendas.isEmpty)
                      const Padding(
                        padding: EdgeInsets.all(24),
                        child: Text('No hay prendas que coincidan.', textAlign: TextAlign.center),
                      ),
                  ],
                  if (estado.deInventario.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    _tarjetaCola(context, estado),
                  ],
                ],
              ),
            ),
    );
  }

  Widget _tarjetaEstado(
    BuildContext context,
    PaqueteInventario? paquete,
    int pendientes,
    EstadoOffline estado,
  ) {
    final texto = Theme.of(context).textTheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(paquete?.sucursal ?? 'Preparar el teléfono', style: texto.titleMedium),
            const SizedBox(height: 6),
            Text(
              paquete == null
                  ? 'Con internet, descargue las prendas de su sucursal y los '
                      'proveedores. Después puede consultar y registrar ingresos '
                      'y conteos aunque no haya señal.'
                  : 'Datos del ${_fecha.format(paquete.generadoEn)}'
                      '${paquete.vencido ? ' · pueden estar desactualizados' : ''}.',
            ),
            if (_preparando) ...[
              const SizedBox(height: 12),
              const LinearProgressIndicator(),
            ],
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilledButton.icon(
                  onPressed: _preparando || !estado.enLinea ? null : _preparar,
                  icon: const Icon(Icons.download_for_offline_outlined),
                  label: Text(paquete == null ? 'Preparar' : 'Actualizar'),
                ),
                if (pendientes > 0)
                  OutlinedButton.icon(
                    onPressed: estado.sincronizando
                        ? null
                        : () => ref.read(offlineProvider.notifier).sincronizar(),
                    icon: const Icon(Icons.sync),
                    label: Text('Sincronizar ($pendientes)'),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _tarjetaCola(BuildContext context, EstadoOffline estado) {
    final ops = estado.deInventario;
    final hayDecididas = ops.any((o) => !o.estado.pendiente);
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const ListTile(
              dense: true,
              title: Text('Registrado sin conexión', style: TextStyle(fontWeight: FontWeight.w600)),
            ),
            for (final o in ops)
              ListTile(
                leading: Icon(
                  o.cuerpo['tipo'] == 'INGRESO' ? Icons.local_shipping_outlined : Icons.fact_check_outlined,
                  color: switch (o.estado) {
                    EstadoOperacion.confirmada => ColoresVB.malva,
                    EstadoOperacion.rechazada || EstadoOperacion.enConflicto => Colors.red.shade700,
                    _ => Colors.grey,
                  },
                ),
                title: Text(o.resumen),
                subtitle: Text(
                  '${o.estado.etiqueta} · ${_fecha.format(o.creadaEn)}'
                  '${o.motivo != null ? '\n${o.motivo}' : ''}',
                ),
                isThreeLine: o.motivo != null,
              ),
            if (hayDecididas)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                child: TextButton(
                  onPressed: () => ref.read(offlineProvider.notifier).limpiarDecididas(),
                  child: const Text('Quitar las ya decididas'),
                ),
              ),
          ],
        ),
      ),
    );
  }

  void _abrirPrenda(BuildContext context, PrendaInventario p, bool enLinea) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (hoja) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(p.nombre, style: Theme.of(hoja).textTheme.titleMedium),
              Text(p.sku),
              const SizedBox(height: 12),
              Text('${p.disponible} disponibles · ${p.reservada} reservadas · ${p.fisica} en el local'),
              if (p.stockMinimo > 0) Text('Avisa con ${p.stockMinimo} o menos.'),
              const SizedBox(height: 16),
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.fact_check_outlined),
                title: const Text('Contar'),
                subtitle: const Text('Ajuste por conteo físico, también sin conexión'),
                onTap: () {
                  Navigator.of(hoja).pop();
                  _contar(context, p);
                },
              ),
              ListTile(
                contentPadding: EdgeInsets.zero,
                enabled: enLinea,
                leading: const Icon(Icons.receipt_long_outlined),
                title: const Text('Ver el kardex'),
                subtitle: Text(enLinea ? 'Todos sus movimientos con el saldo' : 'Necesita conexión'),
                onTap: () {
                  Navigator.of(hoja).pop();
                  Navigator.of(context).push(
                    MaterialPageRoute<void>(builder: (_) => PantallaKardex(prenda: p)),
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _contar(BuildContext context, PrendaInventario p) async {
    final contado = TextEditingController();
    final motivo = TextEditingController();
    final guardar = await showDialog<bool>(
      context: context,
      builder: (dialogo) => StatefulBuilder(
        builder: (dialogo, actualizar) {
          final valor = int.tryParse(contado.text);
          final valido = valor != null && valor >= 0 && motivo.text.trim().length >= _motivoMinimo;
          return AlertDialog(
            title: const Text('Conteo físico'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${p.nombre}\nEl teléfono ve ${p.fisica} en el local.'),
                const SizedBox(height: 12),
                TextField(
                  controller: contado,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'Unidades contadas',
                    helperText: 'Reservadas incluidas',
                  ),
                  onChanged: (_) => actualizar(() {}),
                ),
                TextField(
                  controller: motivo,
                  maxLength: 200,
                  decoration: const InputDecoration(labelText: 'Motivo'),
                  onChanged: (_) => actualizar(() {}),
                ),
                if (valor != null)
                  Text(
                    'Diferencia: ${valor - p.fisica > 0 ? '+' : ''}${valor - p.fisica}. '
                    'Se aplica la diferencia, no lo contado: las ventas del medio no se pisan.',
                  ),
              ],
            ),
            actions: [
              TextButton(onPressed: () => Navigator.of(dialogo).pop(false), child: const Text('Cancelar')),
              FilledButton(
                onPressed: valido ? () => Navigator.of(dialogo).pop(true) : null,
                child: const Text('Guardar'),
              ),
            ],
          );
        },
      ),
    );
    if (guardar != true) return;
    await ref.read(offlineProvider.notifier).registrarConteo(
          prenda: p,
          contado: int.parse(contado.text),
          motivo: motivo.text,
        );
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Conteo guardado. Se confirma al sincronizar.')),
      );
    }
  }
}

// =====================================================================
// Kardex (RF-53)
// =====================================================================

class PantallaKardex extends ConsumerStatefulWidget {
  const PantallaKardex({super.key, required this.prenda});

  final PrendaInventario prenda;

  @override
  ConsumerState<PantallaKardex> createState() => _PantallaKardexState();
}

class _PantallaKardexState extends ConsumerState<PantallaKardex> {
  late Future<Kardex> _kardex;

  @override
  void initState() {
    super.initState();
    _kardex = ref.read(repositorioOfflineProvider).kardex(widget.prenda.varianteId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Kardex')),
      body: FutureBuilder<Kardex>(
        future: _kardex,
        builder: (context, s) {
          if (s.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (s.hasError) {
            return Center(child: Padding(padding: const EdgeInsets.all(24), child: Text(_mensaje(s.error!))));
          }
          final k = s.data!;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(k.nombre, style: Theme.of(context).textTheme.titleMedium),
              Text('${k.sku} · ${k.disponible} disponibles · ${k.reservada} reservadas'),
              const SizedBox(height: 12),
              if (k.movimientos.isEmpty) const Text('Todavía no tiene movimientos en la sucursal.'),
              for (final m in k.movimientos)
                Card(
                  child: ListTile(
                    leading: Text(
                      m.cantidad > 0 ? '+${m.cantidad}' : '${m.cantidad}',
                      style: TextStyle(
                        fontWeight: FontWeight.w700,
                        color: m.cantidad > 0 ? ColoresVB.malva : Colors.red.shade700,
                      ),
                    ),
                    title: Row(
                      children: [
                        Text(m.tipo),
                        if (m.sinConexion) ...[
                          const SizedBox(width: 6),
                          const Icon(Icons.cloud_off, size: 16),
                        ],
                      ],
                    ),
                    subtitle: Text(
                      '${_fecha.format(m.creadoEn)} · ${m.usuario ?? 'Sistema'}'
                      '${m.motivo != null ? '\n${m.motivo}' : ''}',
                    ),
                    isThreeLine: m.motivo != null,
                    trailing: Text('Saldo ${m.saldo}'),
                  ),
                ),
              if (k.total > k.movimientos.length)
                Padding(
                  padding: const EdgeInsets.all(8),
                  child: Text('Se muestran los ${k.movimientos.length} más recientes de ${k.total}.'),
                ),
            ],
          );
        },
      ),
    );
  }
}

// =====================================================================
// Ingreso sin conexión
// =====================================================================

class PantallaIngresoSinRed extends ConsumerStatefulWidget {
  const PantallaIngresoSinRed({super.key});

  @override
  ConsumerState<PantallaIngresoSinRed> createState() => _PantallaIngresoSinRedState();
}

class _PantallaIngresoSinRedState extends ConsumerState<PantallaIngresoSinRed> {
  ProveedorLocal? _proveedor;
  final _remito = TextEditingController();
  final Map<int, int> _cantidades = {};
  String _busqueda = '';
  bool _guardando = false;

  @override
  Widget build(BuildContext context) {
    final paquete = ref.watch(offlineProvider).inventario;
    if (paquete == null) {
      return const Scaffold(body: Center(child: Text('Prepare el inventario primero.')));
    }
    final texto = _busqueda.trim().toLowerCase();
    final prendas = paquete.prendas
        .where((p) => texto.isEmpty || p.sku.toLowerCase().contains(texto) || p.producto.toLowerCase().contains(texto))
        .take(200)
        .toList();
    final unidades = _cantidades.values.fold<int>(0, (t, c) => t + c);

    return Scaffold(
      appBar: AppBar(title: const Text('Ingreso de mercadería')),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: FilledButton.icon(
            onPressed: _proveedor == null || unidades == 0 || _guardando ? null : () => _guardar(paquete),
            icon: const Icon(Icons.save_outlined),
            label: Text('Guardar ingreso ($unidades unidades)'),
          ),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          DropdownButtonFormField<ProveedorLocal>(
            initialValue: _proveedor,
            decoration: const InputDecoration(labelText: 'Proveedor'),
            items: [
              for (final p in paquete.proveedores) DropdownMenuItem(value: p, child: Text(p.razonSocial)),
            ],
            onChanged: (p) => setState(() => _proveedor = p),
          ),
          TextField(
            controller: _remito,
            maxLength: 40,
            decoration: const InputDecoration(labelText: 'Remito (opcional)'),
          ),
          TextField(
            decoration: const InputDecoration(prefixIcon: Icon(Icons.search), labelText: 'Buscar prenda'),
            onChanged: (v) => setState(() => _busqueda = v),
          ),
          const SizedBox(height: 8),
          for (final p in prendas)
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(p.nombre),
              subtitle: Text('${p.sku} · hay ${p.disponible}'),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  IconButton(
                    icon: const Icon(Icons.remove_circle_outline),
                    onPressed: (_cantidades[p.varianteId] ?? 0) == 0
                        ? null
                        : () => setState(() {
                              final n = _cantidades[p.varianteId]! - 1;
                              n == 0 ? _cantidades.remove(p.varianteId) : _cantidades[p.varianteId] = n;
                            }),
                  ),
                  Text('${_cantidades[p.varianteId] ?? 0}'),
                  IconButton(
                    icon: const Icon(Icons.add_circle_outline),
                    onPressed: () => setState(() => _cantidades[p.varianteId] = (_cantidades[p.varianteId] ?? 0) + 1),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Future<void> _guardar(PaqueteInventario paquete) async {
    setState(() => _guardando = true);
    final porId = {for (final p in paquete.prendas) p.varianteId: p};
    await ref.read(offlineProvider.notifier).registrarIngreso(
          proveedor: _proveedor!,
          remito: _remito.text,
          prendas: {for (final e in _cantidades.entries) porId[e.key]!: e.value},
        );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Ingreso guardado. Se confirma al sincronizar.')),
    );
    context.pop();
  }
}
