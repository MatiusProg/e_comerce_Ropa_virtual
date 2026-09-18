/// CU-20 · Mis prendas favoritas.
///
/// Muestra las mismas tarjetas que la vitrina, porque el servidor devuelve
/// exactamente eso: `GET /tienda/favoritos` responde `ProductoVitrinaOut`, la
/// misma forma que el catálogo. Un modelo propio obligaría a agregar dos veces
/// cada campo nuevo.
///
/// POR QUÉ LA LISTA SE RECARGA SOLA AL QUITAR UNA PRENDA
/// ------------------------------------------------------
/// `listaFavoritosProvider` observa el conjunto de identificadores, así que
/// tocar el corazón de una tarjeta la saca de la lista sin que esta pantalla
/// tenga que enterarse. Es lo que evita el defecto clásico: quitar un favorito
/// y que la prenda siga ahí hasta que uno vuelve a entrar.
library;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/enrutado/router.dart';
import '../../core/tema.dart';
import '../../data/modelos/catalogo.dart';
import '../../data/repositorios/repositorio_catalogo.dart';
import '../auth/estado_sesion.dart';
import 'boton_favorito.dart';
import 'estado_favoritos.dart';

class PantallaFavoritos extends ConsumerWidget {
  const PantallaFavoritos({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hayaSesion = ref.watch(sesionProvider) is SesionAbierta;

    return Scaffold(
      appBar: AppBar(title: const Text('Mis favoritos')),
      body: !hayaSesion
          ? _Vacio(
              icono: Icons.lock_outline,
              titulo: 'Iniciá sesión',
              detalle:
                  'Tus favoritos se guardan en tu cuenta, así los tenés '
                  'también desde la web.',
              accion: 'Iniciar sesión',
              alTocar: () => context.push(Rutas.login),
            )
          : ref
                .watch(listaFavoritosProvider)
                .when(
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (fallo, _) => _Vacio(
                    icono: Icons.cloud_off,
                    titulo: 'No se pudieron cargar',
                    detalle: '$fallo',
                    accion: 'Reintentar',
                    alTocar: () => ref.invalidate(listaFavoritosProvider),
                  ),
                  data: (pagina) => pagina.items.isEmpty
                      ? _Vacio(
                          icono: Icons.favorite_border,
                          titulo: 'Todavía no guardaste nada',
                          detalle:
                              'Tocá el corazón de una prenda en el catálogo '
                              'para tenerla acá.',
                          accion: 'Ver el catálogo',
                          alTocar: () => context.push(Rutas.catalogo),
                        )
                      : _Cuadricula(items: pagina.items),
                ),
    );
  }
}

class _Cuadricula extends StatelessWidget {
  const _Cuadricula({required this.items});

  final List<ProductoVitrina> items;

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      padding: const EdgeInsets.all(12),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        childAspectRatio: 0.62,
      ),
      itemCount: items.length,
      itemBuilder: (contexto, i) => _TarjetaFavorita(producto: items[i]),
    );
  }
}

class _TarjetaFavorita extends StatelessWidget {
  const _TarjetaFavorita({required this.producto});

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
            // Igual que en el catálogo: `Expanded` y no `AspectRatio`, para
            // que la foto ceda y la tarjeta nunca desborde por un nombre de
            // dos líneas.
            Expanded(
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
                  Positioned(
                    top: 4,
                    right: 4,
                    child: BotonFavorito(
                      productoId: producto.id,
                      sobreFoto: true,
                    ),
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
                  Text(
                    producto.nombre,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 13.5,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    producto.precioDesde == null
                        ? '—'
                        : 'Bs ${producto.precioDesde}',
                    style: const TextStyle(
                      color: ColoresVB.malva,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Vacio extends StatelessWidget {
  const _Vacio({
    required this.icono,
    required this.titulo,
    required this.detalle,
    required this.accion,
    required this.alTocar,
  });

  final IconData icono;
  final String titulo;
  final String detalle;
  final String accion;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icono, size: 56, color: ColoresVB.malvaClaro),
            const SizedBox(height: 16),
            Text(
              titulo,
              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Text(
              detalle,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.black54),
            ),
            const SizedBox(height: 20),
            FilledButton(onPressed: alTocar, child: Text(accion)),
          ],
        ),
      ),
    );
  }
}
