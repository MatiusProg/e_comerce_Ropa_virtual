/// CU-17 · Consultar catalogo --- «boundary» PantallaCatalogo (movil).
///
/// La vitrina del cliente: busqueda, filtros, orden y paginacion (RF07), y la
/// navegacion a la ficha (CU-18).
///
/// Es la pantalla equivalente a `features/tienda/catalogo` de la web y consume
/// exactamente los mismos endpoints publicos. Lo que cambia es la forma: dos
/// columnas de tarjetas en vez de una cuadricula ancha, y los filtros en una
/// hoja inferior en vez de una fila de selectores --- en 400 px de ancho, cinco
/// selectores en fila no entran.
library;

import 'dart:async';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/enrutado/router.dart';
import '../../core/red/excepciones.dart';
import '../../core/tema.dart';
import '../../data/modelos/catalogo.dart';
import '../../data/repositorios/repositorio_catalogo.dart';
import 'estado_catalogo.dart';

class PantallaCatalogo extends ConsumerStatefulWidget {
  const PantallaCatalogo({super.key});

  @override
  ConsumerState<PantallaCatalogo> createState() => _EstadoPantallaCatalogo();
}

class _EstadoPantallaCatalogo extends ConsumerState<PantallaCatalogo> {
  final _controlBusqueda = TextEditingController();
  Timer? _retardo;

  @override
  void dispose() {
    _retardo?.cancel();
    _controlBusqueda.dispose();
    super.dispose();
  }

  /// La busqueda no consulta en cada tecla.
  ///
  /// Sin el retardo, escribir «blusa» dispara cinco consultas sobre datos
  /// moviles, y la ultima en llegar puede no ser la ultima escrita.
  void _buscarConRetardo(String texto) {
    _retardo?.cancel();
    _retardo = Timer(const Duration(milliseconds: 400), () {
      ref.read(consultaProvider.notifier).buscar(texto);
    });
  }

  @override
  Widget build(BuildContext context) {
    final vitrina = ref.watch(vitrinaProvider);
    final consulta = ref.watch(consultaProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Catálogo'),
        actions: [
          IconButton(
            tooltip: 'Filtros',
            icon: Badge(
              // El punto sobre el icono es lo unico que le dice al cliente que
              // hay filtros puestos: en el movil el panel esta escondido en una
              // hoja, y sin la marca una vitrina filtrada parece un catalogo
              // vacio.
              isLabelVisible: consulta.hayFiltros,
              child: const Icon(Icons.tune),
            ),
            onPressed: _abrirFiltros,
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: TextField(
              controller: _controlBusqueda,
              textInputAction: TextInputAction.search,
              decoration: InputDecoration(
                hintText: 'Buscar prendas',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _controlBusqueda.text.isEmpty
                    ? null
                    : IconButton(
                        icon: const Icon(Icons.close),
                        onPressed: () {
                          _controlBusqueda.clear();
                          ref.read(consultaProvider.notifier).buscar('');
                          setState(() {});
                        },
                      ),
              ),
              onChanged: (texto) {
                _buscarConRetardo(texto);
                // Redibuja solo para mostrar u ocultar la «x»; la consulta la
                // dispara el temporizador.
                setState(() {});
              },
            ),
          ),
          Expanded(
            child: vitrina.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (fallo, _) => _Aviso(
                icono: Icons.error_outline,
                mensaje: fallo is ErrorApi
                    ? fallo.mensaje
                    : 'No se pudo consultar el catálogo.',
                accion: TextButton.icon(
                  onPressed: () => ref.invalidate(vitrinaProvider),
                  icon: const Icon(Icons.refresh),
                  label: const Text('Reintentar'),
                ),
              ),
              data: (pagina) => _Resultados(pagina: pagina, consulta: consulta),
            ),
          ),
        ],
      ),
    );
  }

  void _abrirFiltros() {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => const _HojaDeFiltros(),
    );
  }
}

/// La cuadricula, el vacio y el paginador.
class _Resultados extends ConsumerWidget {
  const _Resultados({required this.pagina, required this.consulta});

  final PaginaVitrina pagina;
  final ConsultaVitrina consulta;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (pagina.items.isEmpty) {
      // El cartel distingue los dos vacios: no es lo mismo un catalogo sin
      // prendas que una combinacion de filtros sin resultados.
      return _Aviso(
        icono: Icons.search_off,
        mensaje: consulta.hayFiltros
            ? 'No encontramos prendas con esos filtros.\nPruebe quitando alguno.'
            : 'Todavía no hay prendas publicadas en el catálogo.',
        accion: consulta.hayFiltros
            ? TextButton.icon(
                onPressed: () => ref.read(consultaProvider.notifier).limpiar(),
                icon: const Icon(Icons.filter_alt_off),
                label: const Text('Limpiar filtros'),
              )
            : null,
      );
    }

    return Column(
      children: [
        Expanded(
          child: RefreshIndicator(
            onRefresh: () async => ref.invalidate(vitrinaProvider),
            child: GridView.builder(
              padding: const EdgeInsets.all(12),
              gridDelegate:
                  const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    mainAxisSpacing: 12,
                    crossAxisSpacing: 12,
                    // La foto es 3:4 y debajo van categoria, nombre y precio.
                    // Con la proporcion por omision la tarjeta se desborda.
                    childAspectRatio: 0.56,
                  ),
              itemCount: pagina.items.length,
              itemBuilder: (context, i) =>
                  _TarjetaPrenda(producto: pagina.items[i]),
            ),
          ),
        ),
        _Paginador(pagina: pagina),
      ],
    );
  }
}

class _TarjetaPrenda extends StatelessWidget {
  const _TarjetaPrenda({required this.producto});

  final ProductoVitrina producto;

  @override
  Widget build(BuildContext context) {
    final url = RepositorioCatalogo.urlDeImagen(producto.imagenUrl);

    return Card(
      clipBehavior: Clip.antiAlias,
      margin: EdgeInsets.zero,
      child: InkWell(
        onTap: () => context.push('${Rutas.catalogo}/${producto.id}'),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            AspectRatio(
              aspectRatio: 3 / 4,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  if (url == null)
                    Container(
                      color: ColoresVB.marfil,
                      child: const Icon(
                        Icons.checkroom,
                        size: 44,
                        color: ColoresVB.malvaClaro,
                      ),
                    )
                  else
                    CachedNetworkImage(
                      imageUrl: url,
                      fit: BoxFit.cover,
                      placeholder: (contexto, ruta) =>
                          Container(color: ColoresVB.marfil),
                      errorWidget: (contexto, ruta, fallo) => Container(
                        color: ColoresVB.marfil,
                        child: const Icon(
                          Icons.image_not_supported_outlined,
                          color: ColoresVB.malvaClaro,
                        ),
                      ),
                    ),
                  if (producto.tieneVestidor)
                    // La insignia del vestidor virtual: es el diferenciador del
                    // proyecto y se ve desde la vitrina, sin abrir la ficha.
                    const Positioned(
                      left: 6,
                      bottom: 6,
                      child: _InsigniaVestidor(),
                    ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (producto.categoriaNombre != null)
                    Text(
                      producto.categoriaNombre!.toUpperCase(),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 10,
                        letterSpacing: 0.6,
                        color: Color(0xFF9A8A92),
                      ),
                    ),
                  const SizedBox(height: 2),
                  Text(
                    producto.nombre,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      height: 1.2,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    producto.precioRotulado,
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      color: ColoresVB.malvaOscuro,
                    ),
                  ),
                  if (producto.colores.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        // Cuatro muestras y el resto como «+N»: con seis
                        // colores, la fila se sale de una tarjeta de media
                        // pantalla.
                        for (final color in producto.colores.take(4))
                          Padding(
                            padding: const EdgeInsets.only(right: 4),
                            child: _MuestraDeColor(color: color, tamano: 12),
                          ),
                        if (producto.colores.length > 4)
                          Text(
                            '+${producto.colores.length - 4}',
                            style: const TextStyle(
                              fontSize: 10,
                              color: Color(0xFF9A8A92),
                            ),
                          ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _InsigniaVestidor extends StatelessWidget {
  const _InsigniaVestidor();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: ColoresVB.malva,
        borderRadius: BorderRadius.circular(999),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.view_in_ar, size: 12, color: Colors.white),
          SizedBox(width: 3),
          Text(
            'Vestidor',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w600,
              color: Colors.white,
            ),
          ),
        ],
      ),
    );
  }
}

class _MuestraDeColor extends StatelessWidget {
  const _MuestraDeColor({required this.color, this.tamano = 16});

  final ColorPrenda color;
  final double tamano;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: tamano,
      height: tamano,
      decoration: BoxDecoration(
        color: Color(color.valorArgb),
        shape: BoxShape.circle,
        border: Border.all(color: const Color(0x2E2E1F28)),
      ),
    );
  }
}

/// Paginacion por botones y no por desplazamiento infinito.
///
/// El infinito oculta cuantas prendas hay y, sobre datos moviles, sigue
/// pidiendo paginas mientras el dedo se mueve. Con botones el cliente ve el
/// total y decide.
class _Paginador extends ConsumerWidget {
  const _Paginador({required this.pagina});

  final PaginaVitrina pagina;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final control = ref.read(consultaProvider.notifier);
    final ultima = (pagina.total / pagina.tamano).ceil();

    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            IconButton.filledTonal(
              onPressed: pagina.pagina > 1
                  ? () => control.irAPagina(pagina.pagina - 1)
                  : null,
              icon: const Icon(Icons.chevron_left),
            ),
            Text(
              '${pagina.total} prendas · página ${pagina.pagina} de $ultima',
              style: const TextStyle(fontSize: 12, color: Color(0xFF9A8A92)),
            ),
            IconButton.filledTonal(
              onPressed: pagina.hayMas
                  ? () => control.irAPagina(pagina.pagina + 1)
                  : null,
              icon: const Icon(Icons.chevron_right),
            ),
          ],
        ),
      ),
    );
  }
}

/// El panel de filtros, en una hoja inferior.
///
/// Las opciones son las que el catalogo realmente ofrece, no los maestros
/// completos: una talla que ningun producto usa es una opcion que al elegirla
/// vacia la vitrina, y el cliente no tiene forma de saber por que.
class _HojaDeFiltros extends ConsumerWidget {
  const _HojaDeFiltros();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filtros = ref.watch(filtrosProvider);
    final consulta = ref.watch(consultaProvider);
    final control = ref.read(consultaProvider.notifier);

    return DraggableScrollableSheet(
      initialChildSize: 0.75,
      minChildSize: 0.4,
      maxChildSize: 0.95,
      expand: false,
      builder: (context, desplazamiento) => filtros.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (fallo, rastro) => const _Aviso(
          icono: Icons.filter_alt_off,
          mensaje: 'No se pudieron cargar los filtros.',
        ),
        data: (opciones) => ListView(
          controller: desplazamiento,
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Filtrar',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                ),
                if (consulta.hayFiltros)
                  TextButton(
                    onPressed: () {
                      control.limpiar();
                      Navigator.of(context).pop();
                    },
                    child: const Text('Limpiar'),
                  ),
              ],
            ),
            const SizedBox(height: 8),

            const _Rotulo('Ordenar por'),
            Wrap(
              spacing: 8,
              children: [
                for (final (clave, texto) in const [
                  ('novedades', 'Novedades'),
                  ('precio_asc', 'Menor precio'),
                  ('precio_desc', 'Mayor precio'),
                  ('nombre', 'Nombre'),
                ])
                  ChoiceChip(
                    label: Text(texto),
                    selected: consulta.orden == clave,
                    onSelected: (_) => control.ordenarPor(clave),
                  ),
              ],
            ),

            if (opciones.categorias.isNotEmpty) ...[
              const _Rotulo('Categoría'),
              Wrap(
                spacing: 8,
                children: [
                  for (final categoria in opciones.categorias)
                    ChoiceChip(
                      label: Text(categoria.nombre),
                      selected: consulta.categoriaId == categoria.id,
                      // Volver a tocar el elegido lo suelta: sin eso, no hay
                      // forma de quitar un filtro sin usar «Limpiar».
                      onSelected: (elegido) => control.filtrarPorCategoria(
                        elegido ? categoria.id : null,
                      ),
                    ),
                ],
              ),
            ],

            if (opciones.tallas.isNotEmpty) ...[
              const _Rotulo('Talla'),
              Wrap(
                spacing: 8,
                children: [
                  for (final talla in opciones.tallas)
                    ChoiceChip(
                      label: Text(talla.codigo),
                      selected: consulta.tallaId == talla.id,
                      onSelected: (elegido) =>
                          control.filtrarPorTalla(elegido ? talla.id : null),
                    ),
                ],
              ),
            ],

            if (opciones.colores.isNotEmpty) ...[
              const _Rotulo('Color'),
              Wrap(
                spacing: 8,
                children: [
                  for (final color in opciones.colores)
                    ChoiceChip(
                      avatar: _MuestraDeColor(color: color),
                      label: Text(color.nombre),
                      selected: consulta.colorId == color.id,
                      onSelected: (elegido) =>
                          control.filtrarPorColor(elegido ? color.id : null),
                    ),
                ],
              ),
            ],

            if (opciones.temporadas.isNotEmpty) ...[
              const _Rotulo('Temporada'),
              Wrap(
                spacing: 8,
                children: [
                  for (final temporada in opciones.temporadas)
                    ChoiceChip(
                      label: Text(temporada.nombre),
                      selected: consulta.temporadaId == temporada.id,
                      onSelected: (elegido) => control.filtrarPorTemporada(
                        elegido ? temporada.id : null,
                      ),
                    ),
                ],
              ),
            ],

            const SizedBox(height: 20),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Ver resultados'),
            ),
          ],
        ),
      ),
    );
  }
}

class _Rotulo extends StatelessWidget {
  const _Rotulo(this.texto);

  final String texto;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 18, bottom: 8),
      child: Text(
        texto.toUpperCase(),
        style: const TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.6,
          color: Color(0xFF9A8A92),
        ),
      ),
    );
  }
}

class _Aviso extends StatelessWidget {
  const _Aviso({required this.icono, required this.mensaje, this.accion});

  final IconData icono;
  final String mensaje;
  final Widget? accion;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icono, size: 44, color: ColoresVB.malvaClaro),
            const SizedBox(height: 12),
            Text(
              mensaje,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Color(0xFF7A6A72)),
            ),
            if (accion != null) ...[const SizedBox(height: 12), accion!],
          ],
        ),
      ),
    );
  }
}
