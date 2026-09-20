/// CU-37 · Generar reportes de gestión, en el teléfono.
///
/// POR QUÉ HACÍA FALTA ADEMÁS DE LA VOZ
/// --------------------------------------
/// CU-35 deja pedir un reporte hablando, y está bien para el caso frecuente.
/// Pero **la voz es un atajo, no el único camino**: si el intérprete no está
/// disponible, si el sitio es ruidoso, o si simplemente se quiere elegir el
/// reporte de una lista, no había forma de bajar nada desde el teléfono.
///
/// LA LISTA NO ESTÁ ESCRITA ACÁ
/// -----------------------------
/// Sale de `/reportes/catalogo`, con sus filtros y sus opciones ya resueltas
/// contra la base. Si el servidor agrega el séptimo reporte, aparece solo. Y
/// `usa_periodo` es lo que esconde el selector de fechas en el inventario:
/// es una foto de ahora, y ofrecer un rango que después se ignora es
/// mentirle a quien lo elige.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/red/excepciones.dart';
import '../../core/tema.dart';
import '../../data/repositorios/repositorio_reportes.dart';
import '../reportes/guardar_reporte.dart';
import 'estado_gestion.dart';

class PantallaReportes extends ConsumerWidget {
  const PantallaReportes({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final catalogo = ref.watch(catalogoDeReportesProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Reportes')),
      body: RefreshIndicator(
        color: ColoresVB.malva,
        onRefresh: () async => ref.invalidate(catalogoDeReportesProvider),
        child: catalogo.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (fallo, _) => ListView(
            padding: const EdgeInsets.fromLTRB(24, 80, 24, 24),
            children: [
              const Icon(Icons.cloud_off, size: 56, color: ColoresVB.malvaClaro),
              const SizedBox(height: 16),
              Text(
                fallo is ErrorApi
                    ? fallo.mensaje
                    : 'No se pudo cargar la lista de reportes.',
                textAlign: TextAlign.center,
              ),
            ],
          ),
          data: (reportes) => ListView.separated(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(12),
            itemCount: reportes.length,
            separatorBuilder: (_, indice) => const SizedBox(height: 8),
            itemBuilder: (_, i) => _TarjetaDeReporte(reporte: reportes[i]),
          ),
        ),
      ),
    );
  }
}

class _TarjetaDeReporte extends ConsumerStatefulWidget {
  const _TarjetaDeReporte({required this.reporte});

  final ReporteDisponible reporte;

  @override
  ConsumerState<_TarjetaDeReporte> createState() => _EstadoTarjeta();
}

class _EstadoTarjeta extends ConsumerState<_TarjetaDeReporte> {
  DateTimeRange? _periodo;
  final Map<String, String?> _filtros = {};
  bool _bajando = false;

  @override
  Widget build(BuildContext context) {
    final r = widget.reporte;

    return Card(
      child: ExpansionTile(
        leading: CircleAvatar(
          backgroundColor: ColoresVB.rosaPalido,
          foregroundColor: ColoresVB.malvaOscuro,
          child: Icon(_iconoDe(r.tipo), size: 20),
        ),
        title: Text(
          r.titulo,
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        subtitle: Text(
          '${r.columnas.length} columnas'
          '${r.usaPeriodo ? '' : ' · situación actual'}',
          style: const TextStyle(fontSize: 12),
        ),
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
        children: [
          // El período solo cuando el reporte lo usa. Ver la nota de arriba.
          if (r.usaPeriodo)
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.date_range, size: 20),
              title: Text(
                _periodo == null
                    ? 'Período: los últimos 30 días'
                    : '${_f(_periodo!.start)} — ${_f(_periodo!.end)}',
                style: const TextStyle(fontSize: 13),
              ),
              trailing: _periodo == null
                  ? null
                  : IconButton(
                      icon: const Icon(Icons.close, size: 18),
                      onPressed: () => setState(() => _periodo = null),
                    ),
              onTap: _elegirPeriodo,
            ),

          for (final filtro in r.filtros)
            if (filtro.opciones.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: DropdownButtonFormField<String?>(
                  initialValue: _filtros[filtro.campo],
                  isExpanded: true,
                  decoration: InputDecoration(
                    labelText: filtro.etiqueta,
                    isDense: true,
                    border: const OutlineInputBorder(),
                  ),
                  items: [
                    const DropdownMenuItem<String?>(
                      value: null,
                      child: Text('Todos'),
                    ),
                    for (final o in filtro.opciones)
                      DropdownMenuItem<String?>(
                        value: o.valor,
                        child: Text(o.etiqueta, overflow: TextOverflow.ellipsis),
                      ),
                  ],
                  onChanged: (v) => setState(() => _filtros[filtro.campo] = v),
                ),
              ),

          const SizedBox(height: 4),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _bajando ? null : () => _bajar('pdf'),
                  icon: const Icon(Icons.picture_as_pdf_outlined, size: 18),
                  label: const Text('PDF'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: FilledButton.icon(
                  onPressed: _bajando ? null : () => _bajar('xlsx'),
                  style: FilledButton.styleFrom(
                    backgroundColor: ColoresVB.malva,
                  ),
                  icon: _bajando
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.table_chart_outlined, size: 18),
                  label: const Text('Excel'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Future<void> _elegirPeriodo() async {
    final hoy = DateTime.now();
    final elegido = await showDateRangePicker(
      context: context,
      firstDate: DateTime(hoy.year - 3),
      lastDate: hoy,
      initialDateRange: _periodo,
    );
    if (elegido != null) setState(() => _periodo = elegido);
  }

  Future<void> _bajar(String formato) async {
    setState(() => _bajando = true);
    try {
      final partes = <String>[
        if (_periodo != null) 'desde=${_iso(_periodo!.start)}',
        if (_periodo != null) 'hasta=${_iso(_periodo!.end)}',
        for (final e in _filtros.entries)
          if (e.value != null && e.value!.isNotEmpty) '${e.key}=${e.value}',
      ];
      final consulta = partes.isEmpty ? '' : '?${partes.join('&')}';
      final ruta = '/reportes/${widget.reporte.tipo}.$formato$consulta';

      final archivo = await ref
          .read(repositorioReportesProvider)
          .descargar(ruta);

      if (!mounted) return;
      await guardarYCompartir(archivo, origen: rectanguloDe(context));
      if (!mounted) return;
      setState(() => _bajando = false);
    } catch (fallo) {
      if (!mounted) return;
      setState(() => _bajando = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            fallo is ErrorApi ? fallo.mensaje : 'No se pudo bajar el reporte.',
          ),
        ),
      );
    }
  }

  /// `YYYY-MM-DD` a mano: `toIso8601String()` convierte a UTC y, con Bolivia
  /// en -4, manda el día anterior.
  String _iso(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-'
      '${d.month.toString().padLeft(2, '0')}-'
      '${d.day.toString().padLeft(2, '0')}';

  String _f(DateTime d) => DateFormat('dd/MM/yy').format(d);
}

IconData _iconoDe(String tipo) => switch (tipo) {
  'ventas' => Icons.point_of_sale_outlined,
  'inventario' => Icons.inventory_2_outlined,
  'movimientos' => Icons.swap_vert,
  'reservas' => Icons.event_available_outlined,
  'rendimiento' => Icons.trending_up,
  'compras' => Icons.local_shipping_outlined,
  _ => Icons.description_outlined,
};
