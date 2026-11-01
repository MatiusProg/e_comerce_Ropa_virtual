/// CU-15 · Registrar reserva offline (cliente).
///
/// La misma reserva que CU-22, pero contra el paquete guardado en el telefono:
/// sucursal, prendas con lo que habia al descargar, y la franja. Se guarda en
/// SQLite y la confirma el servidor al sincronizar (CU-17), con las mismas
/// reglas que la reserva en linea --- horario, probadores, stock ---. Si
/// alguien aparto la ultima unidad antes, se rechaza con el motivo (RN-06).
///
/// Sin pago: la reserva para probarse no se cobra (CU-22), asi que del lado
/// del cliente no hay nada que devolver si se rechaza.
library;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/tema.dart';
import '../../data/modelos/offline.dart';
import '../../data/repositorios/repositorio_catalogo.dart';
import 'estado_offline.dart';

/// Igual que CU-22: hasta tres dias, franjas de 15 a 120 minutos.
const int _diasDeAnticipacion = 3;
const List<int> _duraciones = [15, 30, 45, 60, 90, 120];

class PantallaReservaSinRed extends ConsumerStatefulWidget {
  const PantallaReservaSinRed({super.key});

  @override
  ConsumerState<PantallaReservaSinRed> createState() =>
      _PantallaReservaSinRedState();
}

class _PantallaReservaSinRedState extends ConsumerState<PantallaReservaSinRed> {
  SucursalOffline? _sucursal;
  final Map<PrendaOffline, int> _elegidas = {};
  String _busqueda = '';
  String? _categoria;
  DateTime _dia = DateTime.now().add(const Duration(days: 1));
  TimeOfDay _hora = const TimeOfDay(hour: 15, minute: 0);
  int _duracion = 60;
  bool _guardando = false;

  @override
  Widget build(BuildContext context) {
    final paquete = ref.watch(offlineProvider).paquete;
    if (paquete == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Nueva reserva sin conexión')),
        body: const Center(child: Text('Primero prepare el teléfono.')),
      );
    }
    final texto = Theme.of(context).textTheme;

    return Scaffold(
      appBar: AppBar(title: const Text('Nueva reserva sin conexión')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
        children: [
          if (paquete.vencido)
            Card(
              color: Colors.orange.shade50,
              child: const ListTile(
                leading: Icon(Icons.schedule),
                title: Text(
                  'Los datos guardados pueden estar desactualizados. La '
                  'reserva la confirma el servidor al volver la conexión.',
                ),
              ),
            ),

          // --- 1. La sucursal ------------------------------------------------
          Text('1. ¿Dónde se las prueba?', style: texto.titleMedium),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final s in paquete.sucursales)
                ChoiceChip(
                  label: Text(s.nombre),
                  selected: _sucursal?.id == s.id,
                  onSelected: (_) => setState(() {
                    _sucursal = s;
                    // Lo elegido para otra sucursal puede no estar en esta.
                    _elegidas.clear();
                    _categoria = null;
                  }),
                ),
            ],
          ),

          // --- 2. La franja --------------------------------------------------
          // Antes que las prendas: la lista de prendas puede ser de miles y
          // lo que va despues de ella quedaria al fondo, lejos del pulgar.
          if (_sucursal != null) ...[
            const SizedBox(height: 20),
            Text('2. ¿Cuándo?', style: texto.titleMedium),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.event),
              title: const Text('Día'),
              subtitle: Text('${_dia.day}/${_dia.month}/${_dia.year}'),
              onTap: _elegirDia,
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.schedule),
              title: const Text('Hora de llegada'),
              subtitle: Text(
                '${_hora.format(context)} · atiende de '
                '${_sucursal!.apertura} a ${_sucursal!.cierre}',
              ),
              onTap: _elegirHora,
            ),
            Wrap(
              spacing: 8,
              children: [
                for (final m in _duraciones)
                  ChoiceChip(
                    label: Text('$m min'),
                    selected: _duracion == m,
                    onSelected: (_) => setState(() => _duracion = m),
                  ),
              ],
            ),

            // --- 3. Las prendas ----------------------------------------------
            const SizedBox(height: 20),
            Text('3. Las prendas', style: texto.titleMedium),
            const SizedBox(height: 8),
            // Lo elegido arriba de la busqueda: con miles de prendas, lo que
            // el cliente ya eligio no puede quedar perdido en la lista.
            if (_elegidas.isNotEmpty)
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final e in _elegidas.entries)
                    InputChip(
                      label: Text('${e.value}× ${e.key.nombre}'),
                      onDeleted: () => setState(() => _elegidas.remove(e.key)),
                    ),
                ],
              ),
            const SizedBox(height: 8),
            TextField(
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Buscar por nombre o código',
              ),
              onChanged: (v) =>
                  setState(() => _busqueda = v.trim().toLowerCase()),
            ),
            const SizedBox(height: 8),
            _filtroDeCategorias(paquete),
            const SizedBox(height: 8),
            ..._vitrina(paquete),
          ],
        ],
      ),
      // El boton vive FIJO abajo, siempre a la vista, y no al final de una
      // lista que puede ser de miles de prendas.
      bottomNavigationBar: _sucursal == null
          ? null
          : SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text(
                      'Se guarda en el teléfono y se envía sola al volver la '
                      'conexión. Si alguien apartó la última unidad antes, se '
                      'rechaza y le avisamos.',
                      style: TextStyle(fontSize: 12),
                    ),
                    const SizedBox(height: 8),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        style: FilledButton.styleFrom(
                          backgroundColor: ColoresVB.malva,
                        ),
                        onPressed:
                            _guardando || _elegidas.isEmpty ? null : _guardar,
                        icon: const Icon(Icons.save_outlined),
                        label: Text(
                          _elegidas.isEmpty
                              ? 'Elija al menos una prenda'
                              : 'Guardar reserva · ${_unidades()} '
                                  '${_unidades() == 1 ? 'prenda' : 'prendas'}',
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
    );
  }

  int _unidades() => _elegidas.values.fold(0, (a, b) => a + b);

  /// Las categorias con algo que reservar en la sucursal elegida.
  Widget _filtroDeCategorias(PaqueteCliente paquete) {
    final categorias = {
      for (final p in paquete.prendas)
        if ((p.disponiblePorSucursal[_sucursal!.id] ?? 0) > 0) p.categoria,
    }.toList()
      ..sort();
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          for (final c in [null, ...categorias])
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: ChoiceChip(
                label: Text(c ?? 'Todas'),
                selected: _categoria == c,
                onSelected: (_) => setState(() => _categoria = c),
              ),
            ),
        ],
      ),
    );
  }

  /// Una tarjeta por producto, con su foto. Las tallas y colores se eligen al
  /// tocarla: asi el cliente reconoce la prenda sin saberse el nombre.
  ///
  /// Solo los primeros 20 productos. Dibujar las miles del catalogo no sirve:
  /// el cliente filtra o busca, no las recorre.
  List<Widget> _vitrina(PaqueteCliente paquete) {
    const tope = 20;
    final productos = <int, List<PrendaOffline>>{};
    for (final p in _prendasDe(paquete, _sucursal!)) {
      productos.putIfAbsent(p.productoId, () => []).add(p);
    }
    final grupos = productos.values.toList();
    if (grupos.isEmpty) {
      return const [
        Text('No hay prendas con saldo que coincidan en esta sucursal.'),
      ];
    }
    return [
      GridView.builder(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        itemCount: grupos.length < tope ? grupos.length : tope,
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          childAspectRatio: 0.66,
        ),
        itemBuilder: (_, i) => _tarjetaProducto(grupos[i]),
      ),
      if (grupos.length > tope)
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(
            'Mostrando $tope de ${grupos.length}. Filtre por categoría o '
            'busque por nombre para encontrar la suya.',
            style: const TextStyle(fontSize: 12),
          ),
        ),
    ];
  }

  Iterable<PrendaOffline> _prendasDe(
      PaqueteCliente paquete, SucursalOffline s) {
    return paquete.prendas.where(
      (p) =>
          (p.disponiblePorSucursal[s.id] ?? 0) > 0 &&
          (_categoria == null || p.categoria == _categoria) &&
          (_busqueda.isEmpty ||
              p.producto.toLowerCase().contains(_busqueda) ||
              p.sku.toLowerCase().contains(_busqueda)),
    );
  }

  Widget _tarjetaProducto(List<PrendaOffline> variantes) {
    final primera = variantes.first;
    // El precio mas bajo, comparado como numero pero mostrado tal como llego.
    final masBarata = variantes.reduce(
      (a, b) =>
          (double.tryParse(b.precio) ?? 0) < (double.tryParse(a.precio) ?? 0)
              ? b
              : a,
    );
    final elegidas = variantes.fold<int>(0, (n, v) => n + (_elegidas[v] ?? 0));
    final texto = Theme.of(context).textTheme;

    return Card(
      clipBehavior: Clip.antiAlias,
      margin: EdgeInsets.zero,
      child: InkWell(
        onTap: () => _elegirVariantes(variantes),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // `Expanded`, como en el catalogo: la foto cede y la tarjeta no
            // desborda con un nombre de dos lineas.
            Expanded(
              child: Stack(
                fit: StackFit.expand,
                children: [
                  _foto(primera.imagenUrl),
                  if (elegidas > 0)
                    Positioned(
                      top: 8,
                      right: 8,
                      child: CircleAvatar(
                        radius: 14,
                        backgroundColor: ColoresVB.malva,
                        child: Text(
                          '$elegidas',
                          style: const TextStyle(
                              color: Colors.white, fontSize: 12),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    primera.categoria.toUpperCase(),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: texto.labelSmall?.copyWith(color: ColoresVB.malva),
                  ),
                  Text(
                    primera.producto,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style:
                        texto.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
                  ),
                  Text(
                    variantes.length == 1
                        ? 'Bs ${masBarata.precio}'
                        : 'Desde Bs ${masBarata.precio}',
                    style: texto.bodySmall,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// La foto guardada al preparar. Sin red sale de la cache del telefono.
  Widget _foto(String? ruta) {
    final url = RepositorioCatalogo.urlDeImagen(ruta);
    final vacia = Container(
      color: ColoresVB.marfil,
      child: const Icon(Icons.checkroom, size: 44, color: ColoresVB.malvaClaro),
    );
    if (url == null) return vacia;
    return CachedNetworkImage(
      imageUrl: url,
      fit: BoxFit.cover,
      placeholder: (contexto, ruta) => Container(color: ColoresVB.marfil),
      errorWidget: (contexto, ruta, fallo) => vacia,
    );
  }

  /// La hoja de abajo con las tallas y colores del producto tocado.
  Future<void> _elegirVariantes(List<PrendaOffline> variantes) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (hoja) => StatefulBuilder(
        builder: (hoja, refrescar) {
          // Cambia la hoja y, debajo, la tarjeta y los chips de lo elegido.
          void cambiar(VoidCallback cambio) {
            setState(cambio);
            refrescar(() {});
          }

          return SafeArea(
            child: ConstrainedBox(
              constraints: BoxConstraints(
                maxHeight: MediaQuery.of(hoja).size.height * 0.75,
              ),
              child: ListView(
                shrinkWrap: true,
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
                children: [
                  Row(
                    children: [
                      SizedBox(
                        width: 72,
                        height: 90,
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: _foto(variantes.first.imagenUrl),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          variantes.first.producto,
                          style: Theme.of(hoja).textTheme.titleMedium,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  for (final v in variantes)
                    _filaVariante(
                      v,
                      v.disponiblePorSucursal[_sucursal!.id] ?? 0,
                      cambiar,
                    ),
                  const SizedBox(height: 8),
                  FilledButton(
                    onPressed: () => Navigator.of(hoja).pop(),
                    child: const Text('Listo'),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _filaVariante(
    PrendaOffline prenda,
    int disponible,
    void Function(VoidCallback) cambiar,
  ) {
    final cantidad = _elegidas[prenda] ?? 0;
    return ListTile(
      contentPadding: EdgeInsets.zero,
      title: Text('Talla ${prenda.talla} · ${prenda.color}'),
      subtitle: Text('Bs ${prenda.precio} · quedan $disponible'),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            icon: const Icon(Icons.remove_circle_outline),
            onPressed: cantidad == 0
                ? null
                : () => cambiar(() {
                      cantidad == 1
                          ? _elegidas.remove(prenda)
                          : _elegidas[prenda] = cantidad - 1;
                    }),
          ),
          Text('$cantidad'),
          IconButton(
            icon: const Icon(Icons.add_circle_outline),
            // Hasta 10 prendas distintas y 10 unidades de cada una (CU-22).
            onPressed: cantidad >= disponible ||
                    cantidad >= 10 ||
                    (cantidad == 0 && _elegidas.length >= 10)
                ? null
                : () => cambiar(() => _elegidas[prenda] = cantidad + 1),
          ),
        ],
      ),
    );
  }

  Future<void> _elegirDia() async {
    final hoy = DateTime.now();
    final elegido = await showDatePicker(
      context: context,
      initialDate: _dia,
      firstDate: DateTime(hoy.year, hoy.month, hoy.day),
      lastDate: hoy.add(const Duration(days: _diasDeAnticipacion)),
      helpText: 'Elija el día',
    );
    if (elegido != null) setState(() => _dia = elegido);
  }

  Future<void> _elegirHora() async {
    final elegida = await showTimePicker(
      context: context,
      initialTime: _hora,
      helpText: 'Hora de llegada',
    );
    if (elegida != null) setState(() => _hora = elegida);
  }

  Future<void> _guardar() async {
    final inicio =
        DateTime(_dia.year, _dia.month, _dia.day, _hora.hour, _hora.minute);
    // Lo que se puede saber sin red se avisa antes; el resto lo decide el
    // servidor al sincronizar.
    if (inicio.isBefore(DateTime.now())) {
      _avisar('Esa hora ya pasó. Elija otra.');
      return;
    }
    final fin = inicio.add(Duration(minutes: _duracion));
    String hhmm(DateTime d) =>
        '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';
    if (hhmm(inicio).compareTo(_sucursal!.apertura) < 0 ||
        hhmm(fin).compareTo(_sucursal!.cierre) > 0) {
      _avisar(
        '${_sucursal!.nombre} atiende de ${_sucursal!.apertura} a '
        '${_sucursal!.cierre}.',
      );
      return;
    }

    setState(() => _guardando = true);
    try {
      await ref.read(offlineProvider.notifier).reservar(
            sucursal: _sucursal!,
            prendas: Map.of(_elegidas),
            inicio: inicio,
            fin: fin,
          );
      if (!mounted) return;
      _avisar(
          'Reserva guardada en el teléfono. Se enviará al volver la conexión.');
      context.pop();
    } catch (e) {
      _avisar('No se pudo guardar la reserva: $e');
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  void _avisar(String texto) => ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(texto)));
}
