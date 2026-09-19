/// CU-33 · Para vos — las prendas que el recomendador sugiere. Realiza el RF25.
///
/// Es la misma pantalla que `/tienda/para-vos` de la web, con las mismas dos
/// reglas de dibujo, porque salen de cómo responde el servidor y no del
/// aparato:
///
/// 1. **Sin motivo no se dibuja la etiqueta.** Viene vacío cuando ordenó la
///    popularidad en vez del modelo. Un texto fijo repetido seis veces se lee
///    como un error, y le atribuye a la tienda una razón que nadie eligió.
/// 2. **Se dice con qué se generó.** Una sugerencia hecha por un modelo tiene
///    que poder decir que lo es.
///
/// POR QUÉ HAY UN BOTÓN DE ACTUALIZAR A LA VISTA
/// ----------------------------------------------
/// La recomendación se guarda doce horas. Sin forzar, mostrar que cambia al
/// cargar las medidas o marcar favoritos obligaría a esperar medio día — en
/// una defensa, eso es no poder mostrarlo. Pasó de verdad el 19/09: la web
/// quedó con una recomendación degradada guardada y hubo que forzar para ver
/// la buena.
library;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/enrutado/router.dart';
import '../../core/tema.dart';
import '../../data/repositorios/repositorio_catalogo.dart';
import '../../data/repositorios/repositorio_recomendaciones.dart';
import '../auth/estado_sesion.dart';

class PantallaParaVos extends ConsumerStatefulWidget {
  const PantallaParaVos({super.key});

  @override
  ConsumerState<PantallaParaVos> createState() => _EstadoParaVos();
}

class _EstadoParaVos extends ConsumerState<PantallaParaVos> {
  Recomendaciones? _datos;
  String? _error;
  bool _cargando = true;

  @override
  void initState() {
    super.initState();
    _traer();
  }

  Future<void> _traer({bool forzar = false}) async {
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      final datos = await RepositorioRecomendaciones(
        ref.read(clienteApiProvider),
      ).mias(forzar: forzar);
      if (!mounted) return;
      setState(() {
        _datos = datos;
        _cargando = false;
      });
    } catch (fallo) {
      if (!mounted) return;
      setState(() {
        _error = '$fallo';
        _cargando = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Para vos'),
        actions: [
          IconButton(
            onPressed: _cargando ? null : () => _traer(forzar: true),
            icon: const Icon(Icons.refresh),
            tooltip: 'Volver a calcularlas ahora',
          ),
        ],
      ),
      body: _cuerpo(),
    );
  }

  Widget _cuerpo() {
    if (_cargando) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            // Se dice que puede tardar: del otro lado hay un modelo pensando,
            // y una espera sin explicación se lee como que se colgó.
            Text(
              'Eligiendo prendas para vos…',
              style: TextStyle(color: Colors.black54),
            ),
          ],
        ),
      );
    }

    if (_error != null) {
      return _Vacio(
        icono: Icons.cloud_off,
        titulo: 'No se pudieron cargar',
        detalle: _error!,
        accion: 'Reintentar',
        alTocar: () => _traer(),
      );
    }

    final datos = _datos;
    if (datos == null || datos.prendas.isEmpty) {
      return _Vacio(
        icono: Icons.checkroom,
        titulo: 'Todavía no hay nada que sugerirte',
        detalle: 'Cuando la tienda tenga prendas disponibles, van a aparecer acá.',
        accion: 'Ver el catálogo',
        alTocar: () => context.push(Rutas.catalogo),
      );
    }

    return RefreshIndicator(
      onRefresh: () => _traer(forzar: true),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(12, 12, 12, 24),
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(4, 0, 4, 12),
            child: Text(
              'Prendas elegidas según tu talla, lo que te gusta y la temporada.',
              style: TextStyle(color: Colors.black54, fontSize: 13),
            ),
          ),
          ...datos.prendas.map(_tarjeta),
          const SizedBox(height: 8),
          _origen(datos),
        ],
      ),
    );
  }

  /// Una fila por prenda, y no una cuadrícula como el catálogo.
  ///
  /// El motivo es texto y es lo que distingue esta pantalla: en una celda de
  /// cuadrícula entra recortado a dos palabras, y entonces no dice nada.
  Widget _tarjeta(PrendaSugerida prenda) {
    final url = RepositorioCatalogo.urlDeImagen(prenda.imagenUrl);

    return Card(
      clipBehavior: Clip.antiAlias,
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: () => context.push('${Rutas.catalogo}/${prenda.productoId}'),
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: SizedBox(
                  width: 84,
                  height: 112,
                  child: url == null
                      ? Container(
                          color: ColoresVB.marfil,
                          child: const Icon(
                            Icons.checkroom,
                            color: ColoresVB.malvaClaro,
                          ),
                        )
                      : CachedNetworkImage(
                          imageUrl: url,
                          fit: BoxFit.cover,
                          placeholder: (c, u) =>
                              Container(color: ColoresVB.marfil),
                          errorWidget: (c, u, e) => Container(
                            color: ColoresVB.marfil,
                            child: const Icon(
                              Icons.image_not_supported_outlined,
                              color: ColoresVB.malvaClaro,
                            ),
                          ),
                        ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      prenda.categoria.toUpperCase(),
                      style: const TextStyle(
                        fontSize: 10.5,
                        letterSpacing: 0.5,
                        color: Colors.black45,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      prenda.nombre,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 15,
                      ),
                    ),
                    if (prenda.precioDesde != null) ...[
                      const SizedBox(height: 2),
                      Text(
                        'Bs ${prenda.precioDesde}',
                        style: const TextStyle(
                          color: ColoresVB.malva,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                    // Vacío cuando ordenó la popularidad: no se dibuja nada.
                    if (prenda.motivo.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 9,
                          vertical: 7,
                        ),
                        decoration: BoxDecoration(
                          color: ColoresVB.rosaPalido,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(
                              Icons.auto_awesome,
                              size: 14,
                              color: ColoresVB.malvaOscuro,
                            ),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                prenda.motivo,
                                style: const TextStyle(
                                  fontSize: 12.5,
                                  height: 1.3,
                                  color: ColoresVB.malvaOscuro,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Con qué se generó. Se dice siempre.
  Widget _origen(Recomendaciones datos) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            datos.porIa ? Icons.auto_awesome : Icons.trending_up,
            size: 15,
            color: Colors.black45,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              datos.porIa
                  ? 'Sugeridas por inteligencia artificial a partir de tu perfil.'
                  : 'Lo más elegido de la temporada. Cargá tus medidas y marcá '
                        'favoritos para que sean tuyas de verdad.',
              style: const TextStyle(fontSize: 12, color: Colors.black45),
            ),
          ),
        ],
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
              textAlign: TextAlign.center,
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
