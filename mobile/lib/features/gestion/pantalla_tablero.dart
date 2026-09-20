/// CU-36 · Consultar el tablero de indicadores, en el teléfono.
///
/// SIN GRÁFICOS, Y ES A PROPÓSITO
/// -------------------------------
/// La versión web dibuja barras con Chart.js. Acá van números grandes y
/// listas cortas: en una pantalla de teléfono un gráfico de cinco barras
/// ocupa lo mismo que los cinco números y se lee peor. Además, meter una
/// biblioteca de gráficos por esto sumaría peso a un APK que ya pasa los
/// 100 MB.
///
/// LO QUE NO SE SABE NO SE MUESTRA COMO CERO
/// -------------------------------------------
/// El bloque de ventas puede venir con `disponible: false` y un motivo. En
/// ese caso se muestra el motivo: **un cero afirma que no se vendió nada, y
/// eso es distinto de no saber**. Lo mismo con las tasas de conversión, que
/// llegan nulas cuando no hay denominador.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/hora_boliviana.dart';
import '../../core/red/excepciones.dart';
import '../../core/tema.dart';
import '../../data/modelos/gestion.dart';
import 'estado_gestion.dart';

class PantallaTablero extends ConsumerWidget {
  const PantallaTablero({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tablero = ref.watch(tableroProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Tablero')),
      body: RefreshIndicator(
        color: ColoresVB.malva,
        onRefresh: () async => ref.invalidate(tableroProvider),
        child: tablero.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (fallo, _) => ListView(
            padding: const EdgeInsets.fromLTRB(24, 80, 24, 24),
            children: [
              const Icon(Icons.cloud_off, size: 56, color: ColoresVB.malvaClaro),
              const SizedBox(height: 16),
              Text(
                fallo is ErrorApi
                    ? fallo.mensaje
                    : 'No se pudo cargar el tablero.',
                textAlign: TextAlign.center,
              ),
            ],
          ),
          data: (t) => ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(12),
            children: [
              _Encabezado(tablero: t),
              const SizedBox(height: 12),
              _Ventas(ventas: t.ventas),
              const SizedBox(height: 12),
              _Reservas(reservas: t.reservas, conversion: t.conversion),
              const SizedBox(height: 12),
              _Inventario(salud: t.inventario, alertas: t.alertas),
              if (t.masReservadas.isNotEmpty) ...[
                const SizedBox(height: 12),
                _Ranking(
                  titulo: 'Más reservadas',
                  icono: Icons.event_available_outlined,
                  prendas: t.masReservadas,
                ),
              ],
              if (t.ventas.masVendidas.isNotEmpty) ...[
                const SizedBox(height: 12),
                _Ranking(
                  titulo: 'Más vendidas',
                  icono: Icons.local_fire_department_outlined,
                  prendas: t.ventas.masVendidas,
                ),
              ],
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}

class _Encabezado extends StatelessWidget {
  const _Encabezado({required this.tablero});

  final Tablero tablero;

  @override
  Widget build(BuildContext context) {
    final f = DateFormat('dd/MM/yyyy');
    return Card(
      color: ColoresVB.rosaPalido,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${f.format(tablero.periodo.desde)} — '
              '${f.format(tablero.periodo.hasta)}',
              style: const TextStyle(
                fontWeight: FontWeight.w600,
                color: ColoresVB.malvaOscuro,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              '${tablero.periodo.sucursal ?? 'Toda la red'} · '
              'calculado ${DateFormat('HH:mm').format(enHoraBoliviana(tablero.calculadoEn))}',
              style: const TextStyle(fontSize: 12, color: Colors.black54),
            ),
          ],
        ),
      ),
    );
  }
}

class _Ventas extends StatelessWidget {
  const _Ventas({required this.ventas});

  final Ventas ventas;

  @override
  Widget build(BuildContext context) {
    if (!ventas.disponible) {
      return _Bloque(
        titulo: 'Ventas',
        icono: Icons.point_of_sale_outlined,
        // El motivo y no un cero: no saber no es lo mismo que cero.
        hijo: Text(
          ventas.motivo ?? 'Todavía no hay datos de ventas.',
          style: const TextStyle(color: Colors.black54),
        ),
      );
    }

    return _Bloque(
      titulo: 'Ventas',
      icono: Icons.point_of_sale_outlined,
      hijo: Column(
        children: [
          Row(
            children: [
              _Numero(rotulo: 'Hoy', valor: 'Bs ${ventas.montoHoy ?? '0'}'),
              _Numero(
                rotulo: 'En el período',
                valor: 'Bs ${ventas.montoPeriodo ?? '0'}',
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              _Numero(
                rotulo: 'Ventas',
                valor: '${ventas.cantidadPeriodo ?? 0}',
              ),
              _Numero(
                rotulo: 'Ticket promedio',
                valor: 'Bs ${ventas.ticketPromedio ?? '0'}',
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _Reservas extends StatelessWidget {
  const _Reservas({required this.reservas, required this.conversion});

  final ReservasPorEstado reservas;
  final Conversion conversion;

  @override
  Widget build(BuildContext context) {
    return _Bloque(
      titulo: 'Reservas · ${reservas.total}',
      icono: Icons.event_note_outlined,
      hijo: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              _Pastilla('Pendientes', reservas.pendientes, const Color(0xFFFFF2DC)),
              _Pastilla('Preparadas', reservas.preparadas, const Color(0xFFE3EEFB)),
              _Pastilla('Atendidas', reservas.atendidas, const Color(0xFFE3F2E5)),
              _Pastilla('Canceladas', reservas.canceladas, const Color(0xFFFBE3E3)),
              _Pastilla('Expiradas', reservas.expiradas, const Color(0xFFEDEDED)),
            ],
          ),
          const Divider(height: 20),
          Row(
            children: [
              _Numero(
                rotulo: 'Asistencia',
                valor: _porcentaje(conversion.tasaAtencion),
                ayuda: '${conversion.atendidas} de ${conversion.cerradas} cerradas',
              ),
              _Numero(
                rotulo: 'Se la llevan',
                valor: _porcentaje(conversion.tasaPrueba),
                ayuda:
                    '${conversion.lineasLlevadas} de ${conversion.lineasProbadas} probadas',
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _Inventario extends StatelessWidget {
  const _Inventario({required this.salud, required this.alertas});

  final SaludInventario salud;
  final List<AlertaStock> alertas;

  @override
  Widget build(BuildContext context) {
    return _Bloque(
      titulo: 'Inventario',
      icono: Icons.inventory_2_outlined,
      hijo: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _Numero(rotulo: 'Disponible', valor: '${salud.totalDisponible}'),
              _Numero(rotulo: 'Reservado', valor: '${salud.totalReservado}'),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              _Numero(rotulo: 'En alerta', valor: '${salud.enAlerta}'),
              _Numero(rotulo: 'Sin stock', valor: '${salud.variantesSinStock}'),
            ],
          ),
          if (alertas.isNotEmpty) ...[
            const Divider(height: 20),
            const Text(
              'Hay que reponer',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
            ),
            const SizedBox(height: 6),
            for (final a in alertas.take(5))
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Row(
                  children: [
                    const Icon(
                      Icons.warning_amber_rounded,
                      size: 16,
                      color: Color(0xFFE65100),
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        '${a.producto} · ${a.talla} · ${a.color}',
                        style: const TextStyle(fontSize: 12),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    Text(
                      '${a.disponible}/${a.minimo}',
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFFE65100),
                      ),
                    ),
                  ],
                ),
              ),
            if (alertas.length > 5)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  'y ${alertas.length - 5} más',
                  style: const TextStyle(fontSize: 12, color: Colors.black54),
                ),
              ),
          ],
        ],
      ),
    );
  }
}

class _Ranking extends StatelessWidget {
  const _Ranking({
    required this.titulo,
    required this.icono,
    required this.prendas,
  });

  final String titulo;
  final IconData icono;
  final List<PrendaDestacada> prendas;

  @override
  Widget build(BuildContext context) {
    return _Bloque(
      titulo: titulo,
      icono: icono,
      hijo: Column(
        children: [
          for (final (i, p) in prendas.take(5).indexed)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Row(
                children: [
                  SizedBox(
                    width: 20,
                    child: Text(
                      '${i + 1}.',
                      style: const TextStyle(
                        fontSize: 12,
                        color: Colors.black45,
                      ),
                    ),
                  ),
                  Expanded(
                    child: Text(
                      '${p.producto} · ${p.talla} · ${p.color}',
                      style: const TextStyle(fontSize: 12),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Text(
                    '${p.unidades}',
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: ColoresVB.malvaOscuro,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

// --- Piezas compartidas ---------------------------------------------------

class _Bloque extends StatelessWidget {
  const _Bloque({
    required this.titulo,
    required this.icono,
    required this.hijo,
  });

  final String titulo;
  final IconData icono;
  final Widget hijo;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icono, size: 18, color: ColoresVB.malva),
                const SizedBox(width: 6),
                Text(
                  titulo,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    color: ColoresVB.malvaOscuro,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            hijo,
          ],
        ),
      ),
    );
  }
}

class _Numero extends StatelessWidget {
  const _Numero({required this.rotulo, required this.valor, this.ayuda});

  final String rotulo;
  final String valor;
  final String? ayuda;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            rotulo,
            style: const TextStyle(fontSize: 11, color: Colors.black54),
          ),
          Text(
            valor,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: ColoresVB.tinta,
            ),
          ),
          if (ayuda != null)
            Text(
              ayuda!,
              style: const TextStyle(fontSize: 10, color: Colors.black38),
            ),
        ],
      ),
    );
  }
}

class _Pastilla extends StatelessWidget {
  const _Pastilla(this.rotulo, this.cuantas, this.fondo);

  final String rotulo;
  final int cuantas;
  final Color fondo;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: fondo,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        '$rotulo: $cuantas',
        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
      ),
    );
  }
}

/// Una tasa nula se escribe «—», no «0 %».
///
/// Nula significa que no hay denominador: no hubo reservas cerradas, o nadie
/// se probó nada. Un 0 % ahí se leería como un fracaso que no ocurrió.
String _porcentaje(double? tasa) =>
    tasa == null ? '—' : '${(tasa * 100).toStringAsFixed(0)} %';
