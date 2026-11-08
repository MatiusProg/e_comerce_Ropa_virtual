/// La entrada del probador con la talla real (CU-37): las prendas que el
/// administrador ya preparó (CU-36), LA ÚLTIMA CALIBRADA PRIMERO, para no
/// tener que buscarlas en el catálogo.
library;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/enrutado/router.dart';
import '../../core/red/excepciones.dart';
import '../../core/tema.dart';
import '../../data/repositorios/repositorio_catalogo.dart';
import '../../data/repositorios/repositorio_probador.dart';
import '../auth/estado_sesion.dart';

final _listosProvider = FutureProvider.autoDispose<List<ProductoParaProbar>>((ref) {
  return RepositorioProbador(ref.watch(clienteApiProvider)).listos();
});

class PantallaListaProbador extends ConsumerWidget {
  const PantallaListaProbador({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final listos = ref.watch(_listosProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Probador con talla real')),
      body: listos.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(e is ErrorApi ? e.mensaje : 'No se pudo cargar la lista.',
                textAlign: TextAlign.center),
          ),
        ),
        data: (lista) => lista.isEmpty
            ? const Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text('Todavía no hay prendas preparadas para el probador.',
                      textAlign: TextAlign.center),
                ),
              )
            : ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  const Text(
                    'Elegí una prenda y probátela con la cámara: se dibuja con los centímetros de '
                    'cada talla, así ves si te queda chica o grande antes de comprar.',
                  ),
                  const SizedBox(height: 12),
                  GridView.count(
                    crossAxisCount: 2,
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    mainAxisSpacing: 12,
                    crossAxisSpacing: 12,
                    childAspectRatio: 0.72,
                    children: [
                      for (final p in lista)
                        Card(
                          clipBehavior: Clip.antiAlias,
                          child: InkWell(
                            onTap: () => context.push(Rutas.probadorTalla(p.productoId)),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                Expanded(
                                  child: Container(
                                    color: ColoresVB.marfil,
                                    padding: const EdgeInsets.all(8),
                                    child: CachedNetworkImage(
                                      imageUrl: RepositorioCatalogo.urlDeImagen(p.imagenUrl) ?? p.imagenUrl,
                                      fit: BoxFit.contain,
                                    ),
                                  ),
                                ),
                                Padding(
                                  padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
                                  child: Text(
                                    p.nombre,
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontWeight: FontWeight.w600),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                    ],
                  ),
                ],
              ),
      ),
    );
  }
}
