/// CU-42 · Consultar la bitácora del sistema, en el teléfono.
///
/// SOLO SE LEE
/// ------------
/// No hay botón de crear, de editar ni de borrar, porque el servidor tampoco
/// los expone: los asientos los escribe un middleware y **una bitácora que se
/// puede corregir no prueba nada**. Se dice en la pantalla, no solo en la
/// documentación: que no se pueda alterar es una propiedad del registro, y
/// quien lo lee tiene que saberlo para poder confiar en él.
///
/// LA HORA NO SE CONVIERTE ACÁ
/// ----------------------------
/// Viene ya en hora boliviana desde el servidor. Reconvertirla la pasaría a
/// la zona del teléfono, y un aparato con la hora mal puesta mostraría una
/// bitácora distinta a la de la computadora de al lado.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/red/excepciones.dart';
import '../../core/tema.dart';
import '../../data/modelos/gestion.dart';
import 'estado_gestion.dart';

class PantallaBitacora extends ConsumerWidget {
  const PantallaBitacora({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asientos = ref.watch(bitacoraProvider);
    final filtro = ref.watch(filtroBitacoraProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Bitácora'),
        actions: [
          IconButton(
            tooltip: 'Filtrar',
            icon: Badge(
              isLabelVisible: filtro != sinFiltro,
              child: const Icon(Icons.filter_list),
            ),
            onPressed: () => _abrirFiltros(context, ref),
          ),
        ],
      ),
      body: Column(
        children: [
          const _AvisoDeSoloLectura(),
          Expanded(
            child: RefreshIndicator(
              color: ColoresVB.malva,
              onRefresh: () async => ref.invalidate(bitacoraProvider),
              child: asientos.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (fallo, _) => ListView(
                  padding: const EdgeInsets.fromLTRB(24, 60, 24, 24),
                  children: [
                    const Icon(
                      Icons.cloud_off,
                      size: 56,
                      color: ColoresVB.malvaClaro,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      fallo is ErrorApi
                          ? fallo.mensaje
                          : 'No se pudo leer la bitácora.',
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
                data: (pagina) => pagina.items.isEmpty
                    ? ListView(
                        padding: const EdgeInsets.fromLTRB(24, 60, 24, 24),
                        children: const [
                          Icon(
                            Icons.history,
                            size: 56,
                            color: ColoresVB.malvaClaro,
                          ),
                          SizedBox(height: 16),
                          Text(
                            'No hay nada registrado con esos filtros.',
                            textAlign: TextAlign.center,
                          ),
                        ],
                      )
                    : ListView.separated(
                        physics: const AlwaysScrollableScrollPhysics(),
                        padding: const EdgeInsets.all(8),
                        itemCount: pagina.items.length + 1,
                        separatorBuilder: (_, indice) =>
                            const SizedBox(height: 6),
                        itemBuilder: (_, i) => i == pagina.items.length
                            ? _PieDeLista(pagina: pagina)
                            : _Asiento(asiento: pagina.items[i]),
                      ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _abrirFiltros(BuildContext context, WidgetRef ref) async {
    final opciones = await ref.read(opcionesDeBitacoraProvider.future);
    if (!context.mounted) return;

    var actual = ref.read(filtroBitacoraProvider);

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (hoja) => StatefulBuilder(
        builder: (_, redibujar) => Padding(
          padding: EdgeInsets.fromLTRB(
            16,
            16,
            16,
            16 + MediaQuery.of(hoja).viewInsets.bottom,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Filtrar la bitácora',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 12),
              // «Solo empleados» primero: es la pregunta que se hace de
              // verdad al abrir la bitácora.
              DropdownButtonFormField<String?>(
                initialValue: actual.rol,
                isExpanded: true,
                decoration: const InputDecoration(
                  labelText: 'Quién',
                  isDense: true,
                  border: OutlineInputBorder(),
                ),
                items: [
                  const DropdownMenuItem<String?>(
                    value: null,
                    child: Text('Todos'),
                  ),
                  const DropdownMenuItem<String?>(
                    value: 'EMPLEADOS',
                    child: Text('Solo empleados'),
                  ),
                  for (final r in opciones.roles)
                    DropdownMenuItem<String?>(value: r, child: Text(r)),
                ],
                onChanged: (v) => redibujar(
                  () => actual = (
                    rol: v,
                    accion: actual.accion,
                    exito: actual.exito,
                    busqueda: actual.busqueda,
                  ),
                ),
              ),
              const SizedBox(height: 10),
              DropdownButtonFormField<String?>(
                initialValue: actual.accion,
                isExpanded: true,
                decoration: const InputDecoration(
                  labelText: 'Acción',
                  isDense: true,
                  border: OutlineInputBorder(),
                ),
                items: [
                  const DropdownMenuItem<String?>(
                    value: null,
                    child: Text('Todas'),
                  ),
                  for (final a in opciones.acciones)
                    DropdownMenuItem<String?>(
                      value: a,
                      child: Text(_legible(a)),
                    ),
                ],
                onChanged: (v) => redibujar(
                  () => actual = (
                    rol: actual.rol,
                    accion: v,
                    exito: actual.exito,
                    busqueda: actual.busqueda,
                  ),
                ),
              ),
              const SizedBox(height: 10),
              DropdownButtonFormField<bool?>(
                initialValue: actual.exito,
                isExpanded: true,
                decoration: const InputDecoration(
                  labelText: 'Resultado',
                  isDense: true,
                  border: OutlineInputBorder(),
                ),
                items: const [
                  DropdownMenuItem<bool?>(value: null, child: Text('Todos')),
                  DropdownMenuItem<bool?>(
                      value: true, child: Text('Salió bien')),
                  DropdownMenuItem<bool?>(
                    value: false,
                    child: Text('Falló o fue rechazado'),
                  ),
                ],
                onChanged: (v) => redibujar(
                  () => actual = (
                    rol: actual.rol,
                    accion: actual.accion,
                    exito: v,
                    busqueda: actual.busqueda,
                  ),
                ),
              ),
              const SizedBox(height: 10),
              TextFormField(
                initialValue: actual.busqueda,
                decoration: const InputDecoration(
                  labelText: 'Buscar',
                  hintText: 'Correo o ruta',
                  isDense: true,
                  border: OutlineInputBorder(),
                ),
                onChanged: (v) => actual = (
                  rol: actual.rol,
                  accion: actual.accion,
                  exito: actual.exito,
                  busqueda: v,
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () {
                        ref.read(filtroBitacoraProvider.notifier).limpiar();
                        Navigator.pop(hoja);
                      },
                      child: const Text('Limpiar'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: FilledButton(
                      style: FilledButton.styleFrom(
                        backgroundColor: ColoresVB.malva,
                      ),
                      onPressed: () {
                        ref.read(filtroBitacoraProvider.notifier).poner(actual);
                        Navigator.pop(hoja);
                      },
                      child: const Text('Aplicar'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _AvisoDeSoloLectura extends StatelessWidget {
  const _AvisoDeSoloLectura();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      color: ColoresVB.rosaPalido,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: const Row(
        children: [
          Icon(Icons.lock_outline, size: 16, color: ColoresVB.malvaOscuro),
          SizedBox(width: 6),
          Expanded(
            child: Text(
              'Solo lectura. Los asientos los escribe el sistema y no se '
              'pueden editar ni borrar.',
              style: TextStyle(fontSize: 11, color: ColoresVB.malvaOscuro),
            ),
          ),
        ],
      ),
    );
  }
}

class _Asiento extends StatelessWidget {
  const _Asiento({required this.asiento});

  final AsientoBitacora asiento;

  @override
  Widget build(BuildContext context) {
    final verde = asiento.exito;
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                // Color Y icono: quien no distingue rojo y verde tiene que
                // poder ver igual si la operación se rechazó.
                Icon(
                  verde ? Icons.check_circle : Icons.error,
                  size: 16,
                  color:
                      verde ? const Color(0xFF2E7D32) : const Color(0xFFC62828),
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    asiento.titulo,
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                      color: verde
                          ? const Color(0xFF2E7D32)
                          : const Color(0xFFC62828),
                    ),
                  ),
                ),
                Text(
                  DateFormat('dd/MM HH:mm').format(asiento.ocurridoEnBolivia),
                  style: const TextStyle(fontSize: 11, color: Colors.black54),
                ),
              ],
            ),
            const SizedBox(height: 3),
            Row(
              children: [
                const Icon(Icons.person, size: 13, color: Colors.black45),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    asiento.quien,
                    style: const TextStyle(fontSize: 12),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (asiento.rol != null)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 1,
                    ),
                    decoration: BoxDecoration(
                      color: ColoresVB.rosaPalido,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      asiento.rol!,
                      style: const TextStyle(
                        fontSize: 9,
                        color: ColoresVB.malvaOscuro,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 2),
            Text(
              '${asiento.metodo} ${asiento.ruta} · ${asiento.estadoHttp}'
              '${asiento.ip != null ? ' · ${asiento.ip}' : ''}',
              style: const TextStyle(
                fontSize: 10,
                color: Colors.black38,
                fontFamily: 'monospace',
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Dice cuántos hay en total y cuántos se están viendo.
///
/// El móvil **no pagina**: trae los treinta más recientes, que es lo que se
/// mira en un teléfono. Decirlo es mejor que dejar creer que eso es todo.
class _PieDeLista extends StatelessWidget {
  const _PieDeLista({required this.pagina});

  final PaginaBitacora pagina;

  @override
  Widget build(BuildContext context) {
    if (!pagina.hayMas) return const SizedBox(height: 16);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Text(
        'Mostrando los ${pagina.items.length} más recientes de ${pagina.total}. '
        'Para revisar el resto, usá la web.',
        textAlign: TextAlign.center,
        style: const TextStyle(fontSize: 11, color: Colors.black45),
      ),
    );
  }
}

String _legible(String accion) {
  final p = accion.toLowerCase().replaceAll('_', ' ');
  return p.isEmpty ? p : '${p[0].toUpperCase()}${p.substring(1)}';
}
