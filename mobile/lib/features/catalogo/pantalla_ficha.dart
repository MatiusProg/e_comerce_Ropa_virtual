/// CU-18 · Consultar ficha de producto --- «boundary» PantallaFicha (movil).
///
/// El paso 3: la galeria, la descripcion y la seleccion de talla y color, que
/// es lo que fija la **variante** --- la unidad de negocio (D1) --- y con ella el
/// precio y el SKU.
///
/// **La seleccion se resuelve en dos pasos que se restringen entre si.** No
/// toda combinacion talla x color existe: puede haber una blusa en S negra y en
/// M roja, y ninguna en S roja. Elegir la talla acota los colores ofrecidos, y
/// al reves. Sin eso, la pantalla deja armar una combinacion que no se puede
/// reservar y el error aparece recien al confirmar.
///
/// **Es la pantalla desde la que se entra al vestidor virtual.** Es la costura
/// **C5**: la ficha ya recibe, por variante, la URL del PNG con fondo
/// transparente, asi que la pantalla de realidad aumentada --- que es de Mateo y
/// vive en `features/vestidor_virtual/` --- no tiene que volver a consultar la
/// API ni conocer la tabla de imagenes. Mientras esa pantalla no exista, el
/// boton avisa que llega en el Ciclo 3 en vez de navegar a una ruta rota.
library;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/red/excepciones.dart';
import '../../core/tema.dart';
import '../../data/modelos/catalogo.dart';
import '../../data/repositorios/repositorio_catalogo.dart';
import 'estado_catalogo.dart';

class PantallaFicha extends ConsumerStatefulWidget {
  const PantallaFicha({required this.productoId, super.key});

  final int productoId;

  @override
  ConsumerState<PantallaFicha> createState() => _EstadoPantallaFicha();
}

class _EstadoPantallaFicha extends ConsumerState<PantallaFicha> {
  int? _tallaElegida;
  int? _colorElegido;
  int _fotoActiva = 0;

  @override
  Widget build(BuildContext context) {
    final ficha = ref.watch(fichaProvider(widget.productoId));

    return Scaffold(
      appBar: AppBar(title: const Text('Prenda')),
      body: ficha.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (fallo, _) => _Aviso(
          mensaje: fallo is ErrorApi
              ? fallo.mensaje
              : 'La prenda que busca ya no está disponible.',
        ),
        data: _construirFicha,
      ),
    );
  }

  Widget _construirFicha(FichaPrenda prenda) {
    final variante = prenda.varianteDe(_tallaElegida, _colorElegido);
    final tallasOfrecidas = prenda.tallasDeColor(_colorElegido);
    final coloresOfrecidos = prenda.coloresDeTalla(_tallaElegida);

    return ListView(
      padding: const EdgeInsets.only(bottom: 28),
      children: [
        _Galeria(
          prenda: prenda,
          activa: _fotoActiva,
          alElegir: (i) => setState(() => _fotoActiva = i),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (prenda.categoriaNombre != null)
                Text(
                  prenda.categoriaNombre!.toUpperCase(),
                  style: const TextStyle(
                    fontSize: 11,
                    letterSpacing: 0.6,
                    color: Color(0xFF9A8A92),
                  ),
                ),
              const SizedBox(height: 4),
              Text(
                prenda.nombre,
                style: const TextStyle(
                  fontSize: 21,
                  fontWeight: FontWeight.w600,
                  color: ColoresVB.malvaOscuro,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                // Con variante elegida se muestra su precio propio; sin ella,
                // el rango del producto. La variante es la que tiene precio.
                variante != null
                    ? 'Bs ${variante.precio}'
                    : prenda.precioRotulado,
                style: const TextStyle(
                  fontSize: 19,
                  fontWeight: FontWeight.w600,
                ),
              ),
              if (prenda.descripcion != null) ...[
                const SizedBox(height: 12),
                Text(
                  prenda.descripcion!,
                  style: const TextStyle(height: 1.5, color: Color(0xFF5C4C55)),
                ),
              ],

              const SizedBox(height: 20),
              const _Rotulo('Talla'),
              Wrap(
                spacing: 8,
                children: [
                  for (final talla in prenda.tallas)
                    _ChipTalla(
                      talla: talla,
                      elegida: _tallaElegida == talla.id,
                      disponible: tallasOfrecidas.contains(talla),
                      alTocar: () => _elegirTalla(prenda, talla.id),
                    ),
                ],
              ),

              const _Rotulo('Color'),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  for (final color in prenda.colores)
                    _BotonColor(
                      color: color,
                      elegido: _colorElegido == color.id,
                      disponible: coloresOfrecidos.contains(color),
                      alTocar: () => _elegirColor(prenda, color.id),
                    ),
                ],
              ),

              const SizedBox(height: 18),
              if (variante != null)
                Row(
                  children: [
                    const Icon(
                      Icons.qr_code_2,
                      size: 18,
                      color: Color(0xFF9A8A92),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      variante.sku,
                      style: const TextStyle(
                        fontFamily: 'monospace',
                        fontSize: 13,
                        color: Color(0xFF7A6A72),
                      ),
                    ),
                  ],
                )
              else
                const Text(
                  'Elija talla y color para ver el precio y la disponibilidad.',
                  style: TextStyle(fontSize: 13, color: Color(0xFF7A6A72)),
                ),

              const SizedBox(height: 20),
              _BotonVestidor(prenda: prenda, variante: variante),

              const SizedBox(height: 12),
              // CU-19 llega con la costura C1: hasta que el servicio de
              // inventario exponga `disponibilidad_por_sucursal`, la ficha no
              // puede decir en que tienda hay stock. Se anuncia en vez de
              // dibujar un bloque vacio.
              const Row(
                children: [
                  Icon(
                    Icons.store_outlined,
                    size: 18,
                    color: Color(0xFF9A8A92),
                  ),
                  SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'La disponibilidad por sucursal se muestra acá en cuanto '
                      'esté el inventario (CU-19).',
                      style: TextStyle(fontSize: 12, color: Color(0xFF9A8A92)),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  void _elegirTalla(FichaPrenda prenda, int tallaId) {
    setState(() {
      _tallaElegida = _tallaElegida == tallaId ? null : tallaId;
      // Si el color elegido no existe en la talla nueva, se suelta: dejarlo
      // mostraria una combinacion inexistente como si fuera valida.
      final ofrecidos = prenda.coloresDeTalla(_tallaElegida);
      if (_colorElegido != null &&
          !ofrecidos.any((c) => c.id == _colorElegido)) {
        _colorElegido = null;
      }
      _saltarAFotoDeLaVariante(prenda);
    });
  }

  void _elegirColor(FichaPrenda prenda, int colorId) {
    setState(() {
      _colorElegido = _colorElegido == colorId ? null : colorId;
      final ofrecidas = prenda.tallasDeColor(_colorElegido);
      if (_tallaElegida != null &&
          !ofrecidas.any((t) => t.id == _tallaElegida)) {
        _tallaElegida = null;
      }
      _saltarAFotoDeLaVariante(prenda);
    });
  }

  /// Si la variante elegida tiene foto propia, la galeria salta a ella.
  void _saltarAFotoDeLaVariante(FichaPrenda prenda) {
    final variante = prenda.varianteDe(_tallaElegida, _colorElegido);
    if (variante == null) return;
    final indice = prenda.imagenes.indexWhere(
      (i) => i.varianteId == variante.id,
    );
    if (indice >= 0) _fotoActiva = indice;
  }
}

class _Galeria extends StatelessWidget {
  const _Galeria({
    required this.prenda,
    required this.activa,
    required this.alElegir,
  });

  final FichaPrenda prenda;
  final int activa;
  final void Function(int) alElegir;

  @override
  Widget build(BuildContext context) {
    if (prenda.imagenes.isEmpty) {
      return AspectRatio(
        aspectRatio: 3 / 4,
        child: Container(
          color: ColoresVB.marfil,
          child: const Icon(
            Icons.checkroom,
            size: 64,
            color: ColoresVB.malvaClaro,
          ),
        ),
      );
    }

    final principal = RepositorioCatalogo.urlDeImagen(
      prenda.imagenes[activa].url,
    );

    return Column(
      children: [
        AspectRatio(
          aspectRatio: 3 / 4,
          child: CachedNetworkImage(
            imageUrl: principal!,
            fit: BoxFit.cover,
            placeholder: (contexto, ruta) => Container(color: ColoresVB.marfil),
            errorWidget: (contexto, ruta, fallo) => Container(
              color: ColoresVB.marfil,
              child: const Icon(
                Icons.image_not_supported_outlined,
                color: ColoresVB.malvaClaro,
              ),
            ),
          ),
        ),
        if (prenda.imagenes.length > 1)
          SizedBox(
            height: 76,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              itemCount: prenda.imagenes.length,
              separatorBuilder: (contexto, indice) => const SizedBox(width: 8),
              itemBuilder: (context, i) {
                final url = RepositorioCatalogo.urlDeImagen(
                  prenda.imagenes[i].url,
                );
                return GestureDetector(
                  onTap: () => alElegir(i),
                  child: Container(
                    width: 44,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: i == activa
                            ? ColoresVB.malva
                            : Colors.transparent,
                        width: 2,
                      ),
                    ),
                    clipBehavior: Clip.antiAlias,
                    child: CachedNetworkImage(imageUrl: url!, fit: BoxFit.cover),
                  ),
                );
              },
            ),
          ),
      ],
    );
  }
}

class _ChipTalla extends StatelessWidget {
  const _ChipTalla({
    required this.talla,
    required this.elegida,
    required this.disponible,
    required this.alTocar,
  });

  final TallaPrenda talla;
  final bool elegida;
  final bool disponible;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) {
    return ChoiceChip(
      label: Text(talla.codigo),
      selected: elegida,
      // La talla que no existe en el color elegido se deshabilita en vez de
      // desaparecer: si se fuera de la fila, las que quedan saltarian de lugar.
      onSelected: disponible ? (_) => alTocar() : null,
    );
  }
}

class _BotonColor extends StatelessWidget {
  const _BotonColor({
    required this.color,
    required this.elegido,
    required this.disponible,
    required this.alTocar,
  });

  final ColorPrenda color;
  final bool elegido;
  final bool disponible;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: disponible
          ? color.nombre
          : '${color.nombre} — no disponible en esa talla',
      child: Opacity(
        opacity: disponible ? 1 : 0.3,
        child: GestureDetector(
          onTap: disponible ? alTocar : null,
          child: Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              color: Color(color.valorArgb),
              shape: BoxShape.circle,
              border: Border.all(
                color: elegido ? ColoresVB.malva : const Color(0x2E2E1F28),
                width: elegido ? 3 : 1,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// El acceso al vestidor virtual (CU-21, Ciclo 3).
///
/// Tres estados, y los tres dicen algo distinto:
///
/// - La prenda no tiene ningun PNG transparente: no se puede probar, y el
///   motivo es un dato que falta, no un error (supuesto S5).
/// - La tiene, pero todavia no se eligio talla y color: el vestidor necesita
///   una variante concreta, porque el PNG es por variante.
/// - Hay variante con PNG: el boton se habilita. Hoy avisa que la pantalla de
///   realidad aumentada llega en el Ciclo 3; cuando exista, navega a ella
///   pasandole `variante.imagenVestidorUrl`, que es la costura C5.
class _BotonVestidor extends StatelessWidget {
  const _BotonVestidor({required this.prenda, required this.variante});

  final FichaPrenda prenda;
  final VariantePrenda? variante;

  @override
  Widget build(BuildContext context) {
    final sePuede = variante?.sePuedeProbar ?? false;

    final String motivo;
    if (!prenda.tieneVestidor) {
      motivo = 'Esta prenda todavía no tiene su imagen para el vestidor virtual.';
    } else if (variante == null) {
      motivo = 'Elija talla y color para probarla en el vestidor virtual.';
    } else if (!sePuede) {
      motivo = 'Esa combinación todavía no tiene imagen para el vestidor.';
    } else {
      motivo = '';
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            icon: const Icon(Icons.view_in_ar),
            label: const Text('Probar en el vestidor virtual'),
            onPressed: sePuede
                ? () => ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text(
                        'El vestidor virtual llega en el Ciclo 3 (CU-21). '
                        'La prenda ya tiene su imagen lista.',
                      ),
                    ),
                  )
                : null,
          ),
        ),
        if (motivo.isNotEmpty) ...[
          const SizedBox(height: 6),
          Text(
            motivo,
            style: const TextStyle(fontSize: 12, color: Color(0xFF9A8A92)),
          ),
        ],
      ],
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
  const _Aviso({required this.mensaje});

  final String mensaje;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.error_outline,
              size: 44,
              color: ColoresVB.malvaClaro,
            ),
            const SizedBox(height: 12),
            Text(
              mensaje,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Color(0xFF7A6A72)),
            ),
          ],
        ),
      ),
    );
  }
}
