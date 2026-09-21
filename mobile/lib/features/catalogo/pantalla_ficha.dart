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
import 'package:go_router/go_router.dart';

import '../../core/enrutado/router.dart';
import '../../core/red/excepciones.dart';
import '../../core/tema.dart';
import '../../data/modelos/catalogo.dart';
import '../../data/repositorios/repositorio_catalogo.dart';
import '../compra/estado_compra.dart';
import '../reservas/estado_reservas.dart';
import 'boton_favorito.dart';
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
      appBar: AppBar(
        title: const Text('Prenda'),
        actions: [
          // CU-20. En la barra y no junto al precio: es la posicion en la que
          // ya esta en el catalogo ---arriba a la derecha--- y el cliente que
          // entro tocandolo ahi lo vuelve a buscar en el mismo lado.
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: BotonFavorito(productoId: widget.productoId),
          ),
        ],
      ),
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
              // El descuento SIGUE A LA VARIANTE ELEGIDA, no al producto.
              //
              // El del producto está calculado sobre el precio «desde»: si se
              // usara con una variante elegida, la talla más cara anunciaría
              // una rebaja que no le corresponde y el carrito cobraría otra
              // cosa. Es la misma regla que aplica la ficha de la web.
              if ((variante?.descuento ?? prenda.descuento) case final d?) ...[
                Row(
                  crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic,
                  children: [
                    Text(
                      'Bs ${d.precioFinal}',
                      style: const TextStyle(
                        fontSize: 21,
                        fontWeight: FontWeight.w700,
                        color: ColoresVB.malvaOscuro,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      variante != null
                          ? 'Bs ${variante.precio}'
                          : prenda.precioRotulado,
                      style: const TextStyle(
                        fontSize: 15,
                        decoration: TextDecoration.lineThrough,
                        color: Color(0xFF9A8A92),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                // El NOMBRE de la promoción y no solo el porcentaje: quien ve
                // «−16 %» sin saber de qué se pregunta si es un error.
                Row(
                  children: [
                    const Icon(Icons.sell_outlined,
                        size: 15, color: ColoresVB.malva),
                    const SizedBox(width: 5),
                    Flexible(
                      child: Text(
                        '${d.nombre} · -${d.porcentajeRotulado}%',
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: ColoresVB.malva,
                        ),
                      ),
                    ),
                  ],
                ),
              ] else
                Text(
                  // Con variante elegida se muestra su precio propio; sin
                  // ella, el rango del producto. La variante tiene precio.
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
              // CU-26. El boton de agregar esta en la FICHA y no en la tarjeta
              // del catalogo: el carrito guarda variantes, y desde el listado
              // no hay talla ni color elegidos. Es la misma decision que tomo
              // la web.
              _BotonAgregar(variante: variante),
              const SizedBox(height: 10),
              // CU-22. Va JUNTO a «Agregar al carrito» y no en otra pantalla.
              //
              // Hasta el 19/09 la unica forma de reservar en el movil era
              // entrar a «Mis reservas» y buscar la prenda por su nombre en un
              // selector de texto: para reservar habia que saber como se
              // llama. Comprar, en cambio, ya se hacia desde aca. Eran dos
              // flujos para la misma decision, y uno estaba mucho peor. La web
              // tenia el mismo hueco y se arreglo igual.
              _BotonReservar(prenda: prenda, variante: variante),
              const SizedBox(height: 10),
              _BotonVestidor(prenda: prenda, variante: variante),

              const SizedBox(height: 8),
              const _Rotulo('Dónde encontrarla'),
              // CU-19. Se consulta al completar la seleccion, porque la
              // existencia es por variante.
              _Disponibilidad(variante: variante),
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

/// CU-22 · Reservar la variante elegida para probarsela en la sucursal.
///
/// Agrega la prenda al BORRADOR de la reserva y navega al formulario, que ya
/// la encuentra puesta. No se duplica nada del formulario: se reutiliza
/// entero, igual que en la web.
///
/// Deshabilitado hasta que haya talla y color, por lo mismo que el carrito: la
/// reserva aparta UNIDADES de una variante concreta (decision D1).
class _BotonReservar extends ConsumerWidget {
  const _BotonReservar({required this.prenda, required this.variante});

  final FichaPrenda prenda;
  final VariantePrenda? variante;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final elegida = variante;

    return SizedBox(
      width: double.infinity,
      child: OutlinedButton.icon(
        icon: const Icon(Icons.event_available),
        label: const Text('Reservar para probarme'),
        onPressed: elegida == null ? null : () => _reservar(context, ref, elegida),
      ),
    );
  }

  void _reservar(BuildContext context, WidgetRef ref, VariantePrenda elegida) {
    final fallo = ref.read(borradorProvider.notifier).agregar(
      prenda: prenda,
      variante: elegida,
      cantidad: 1,
    );
    // `agregar` devuelve el motivo si no se pudo ---ya estaba, o el borrador
    // esta lleno---. Se avisa y NO se navega: llevarlo a un formulario que no
    // cambio seria hacerle creer que algo paso.
    if (fallo != null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(fallo)));
      return;
    }
    context.push(Rutas.reservaNueva);
  }
}


/// CU-26 · Agregar la variante elegida al carrito.
///
/// Deshabilitado hasta que haya talla y color: el carrito apunta a la VARIANTE
/// y no al producto (decision D1), asi que «una blusa» sin talla ni color no se
/// puede convertir en pedido.
///
/// AGREGAR NO NAVEGA AL CARRITO
/// -----------------------------
/// Quien esta mirando una ficha suele querer seguir mirando; llevarlo de golpe
/// le corta el recorrido. El aviso le OFRECE ir, y ahi decide el. Es la misma
/// decision que tomo la web.
class _BotonAgregar extends ConsumerStatefulWidget {
  const _BotonAgregar({required this.variante});

  final VariantePrenda? variante;

  @override
  ConsumerState<_BotonAgregar> createState() => _BotonAgregarState();
}

class _BotonAgregarState extends ConsumerState<_BotonAgregar> {
  bool _agregando = false;

  @override
  Widget build(BuildContext context) {
    final variante = widget.variante;
    // Se puede agregar algo agotado a proposito: el carrito es una intencion y
    // no inmoviliza inventario. Quien se planta es CU-27, al confirmar.
    final sePuede = variante != null && !_agregando;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            icon: _agregando
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.add_shopping_cart),
            label: Text(_agregando ? 'Agregando…' : 'Agregar al carrito'),
            onPressed: sePuede ? () => _agregar(variante) : null,
          ),
        ),
        if (variante == null)
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Text(
              'Elija talla y color para agregarla al carrito.',
              style: TextStyle(fontSize: 13, color: Color(0xFF7A6A72)),
            ),
          ),
      ],
    );
  }

  Future<void> _agregar(VariantePrenda variante) async {
    setState(() => _agregando = true);
    final fallo = await ref
        .read(carritoProvider.notifier)
        .agregar(varianteId: variante.id);
    if (!mounted) return;
    setState(() => _agregando = false);

    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(fallo ?? 'Agregada al carrito.'),
          action: fallo == null
              ? SnackBarAction(
                  label: 'Ver carrito',
                  onPressed: () => context.push(Rutas.carrito),
                )
              : null,
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
            // Conectado al prototipo I3 el 13/09. Le pasa el PNG de ESTA
            // variante --- la costura C5 --- para que la pantalla de realidad
            // aumentada no tenga que volver a consultar la API ni conocer la
            // tabla de imagenes.
            onPressed: sePuede
                ? () => context.push(
                    Rutas.vestidor,
                    extra: <String, String?>{
                      'url': RepositorioCatalogo.urlDeImagen(
                        variante!.imagenVestidorUrl,
                      ),
                      'nombre': prenda.nombre,
                    },
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

/// CU-19 · en que sucursales hay stock de la variante elegida.
///
/// Se apoya en `disponibilidadProvider`, que es `family` por variante: pedir la
/// de todas las variantes al abrir la ficha serian tantas consultas como
/// combinaciones tenga la prenda, de las que el cliente mira una.
///
/// Un fallo deja el bloque con un aviso y no rompe la ficha: la disponibilidad
/// es un dato de apoyo, y quedarse sin ella no impide ver la prenda ni su
/// precio.
class _Disponibilidad extends ConsumerWidget {
  const _Disponibilidad({required this.variante});

  final VariantePrenda? variante;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final elegida = variante;
    if (elegida == null) {
      return const _Nota('Elija talla y color para ver en qué sucursales hay.');
    }

    return ref
        .watch(disponibilidadProvider(elegida.id))
        .when(
          loading: () => const _Nota('Consultando disponibilidad…'),
          error: (fallo, rastro) =>
              const _Nota('No se pudo consultar la disponibilidad.'),
          data: (stock) {
            if (!stock.hayStock) {
              // No es un error: la prenda existe y se ofrece, lo que no hay es
              // stock. Decirlo asi evita que parezca que desaparecio.
              return const _Nota(
                'Sin unidades disponibles por ahora en ninguna sucursal.',
                icono: Icons.info_outline,
              );
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final sucursal in stock.sucursales)
                  Container(
                    margin: const EdgeInsets.only(bottom: 6),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 10,
                    ),
                    decoration: BoxDecoration(
                      color: ColoresVB.marfil,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0x1A2E1F28)),
                    ),
                    child: Row(
                      children: [
                        const Icon(
                          Icons.store,
                          size: 18,
                          color: ColoresVB.malva,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                sucursal.sucursalNombre,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              Text(
                                sucursal.ciudadNombre,
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: Color(0xFF9A8A92),
                                ),
                              ),
                            ],
                          ),
                        ),
                        Text(
                          sucursal.unidades,
                          style: const TextStyle(
                            fontWeight: FontWeight.w600,
                            color: ColoresVB.malvaOscuro,
                          ),
                        ),
                      ],
                    ),
                  ),
                Text(
                  '${stock.totalDisponible} en total en la red',
                  style: const TextStyle(
                    fontSize: 12,
                    color: Color(0xFF9A8A92),
                  ),
                ),
              ],
            );
          },
        );
  }
}

class _Nota extends StatelessWidget {
  const _Nota(this.texto, {this.icono});

  final String texto;
  final IconData? icono;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icono ?? Icons.store_outlined, size: 18, color: const Color(0xFF9A8A92)),
        const SizedBox(width: 6),
        Expanded(
          child: Text(
            texto,
            style: const TextStyle(fontSize: 12, color: Color(0xFF9A8A92)),
          ),
        ),
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
