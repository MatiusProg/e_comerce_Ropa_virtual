/// Modelos del contrato del catalogo publico (P5).
///
/// Cada clase refleja un esquema de
/// `backend/app/modules/catalogo_publico/schemas.py`. Igual que en `auth.dart`,
/// los nombres JSON se leen tal como los emite la API --- en castellano y en
/// `snake_case` --- y esta es la unica capa que hay que tocar si cambian.
///
/// Los precios se conservan como **texto**, no como `double`. El backend los
/// declara `NUMERIC(10,2)` y los serializa en decimal; pasarlos por coma
/// flotante mete el redondeo binario justo en el precio de una prenda. La app
/// solo los muestra, no hace cuentas con ellos: el total del carrito y de la
/// reserva los calcula el servidor.
library;

class ColorPrenda {
  const ColorPrenda({
    required this.id,
    required this.nombre,
    required this.hexadecimal,
  });

  final int id;
  final String nombre;

  /// `#RRGGBB`. El backend lo garantiza con una restriccion CHECK.
  final String hexadecimal;

  /// El color listo para pintar. Se convierte aca y no en cada widget.
  int get valorArgb => int.parse('FF${hexadecimal.substring(1)}', radix: 16);

  factory ColorPrenda.desdeJson(Map<String, dynamic> json) {
    return ColorPrenda(
      id: json['id'] as int,
      nombre: json['nombre'] as String,
      hexadecimal: json['hexadecimal'] as String,
    );
  }
}

class TallaPrenda {
  const TallaPrenda({
    required this.id,
    required this.tipoPrenda,
    required this.codigo,
    required this.orden,
  });

  final int id;
  final String tipoPrenda;
  final String codigo;

  /// El orden del maestro, no el alfabetico. Sin el, XL aparece antes que S.
  final int orden;

  factory TallaPrenda.desdeJson(Map<String, dynamic> json) {
    return TallaPrenda(
      id: json['id'] as int,
      tipoPrenda: json['tipo_prenda'] as String,
      codigo: json['codigo'] as String,
      orden: json['orden'] as int,
    );
  }
}

class CategoriaPrenda {
  const CategoriaPrenda({
    required this.id,
    required this.nombre,
    this.categoriaPadreId,
  });

  final int id;
  final String nombre;
  final int? categoriaPadreId;

  factory CategoriaPrenda.desdeJson(Map<String, dynamic> json) {
    return CategoriaPrenda(
      id: json['id'] as int,
      nombre: json['nombre'] as String,
      categoriaPadreId: json['categoria_padre_id'] as int?,
    );
  }
}

class TemporadaPrenda {
  const TemporadaPrenda({required this.id, required this.nombre});

  final int id;
  final String nombre;

  factory TemporadaPrenda.desdeJson(Map<String, dynamic> json) {
    return TemporadaPrenda(
      id: json['id'] as int,
      nombre: json['nombre'] as String,
    );
  }
}

/// Una tarjeta de la vitrina (CU-17). Sin variantes: solo el rango de precios.
class ProductoVitrina {
  const ProductoVitrina({
    required this.id,
    required this.codigo,
    required this.nombre,
    required this.colores,
    required this.tieneVestidor,
    this.categoriaNombre,
    this.precioDesde,
    this.precioHasta,
    this.imagenUrl,
  });

  final int id;
  final String codigo;
  final String nombre;
  final String? categoriaNombre;
  final String? precioDesde;
  final String? precioHasta;

  /// Ruta servida por la API (`/media/...`), **no** URL absoluta. La completa
  /// `RepositorioCatalogo.urlDeImagen`.
  final String? imagenUrl;

  final List<ColorPrenda> colores;

  /// Si alguna variante tiene el PNG del vestidor virtual. Viaja en el listado
  /// para poder rotular la tarjeta sin abrir la ficha.
  final bool tieneVestidor;

  /// Lo que se muestra en la tarjeta. Cuando las variantes valen distinto se
  /// anuncia «desde»: es lo unico que la tarjeta puede prometer sin saber que
  /// talla y color va a elegir el cliente.
  String get precioRotulado {
    if (precioDesde == null) return 'Sin precio';
    if (precioHasta != null && precioHasta != precioDesde) {
      return 'desde Bs $precioDesde';
    }
    return 'Bs $precioDesde';
  }

  factory ProductoVitrina.desdeJson(Map<String, dynamic> json) {
    return ProductoVitrina(
      id: json['id'] as int,
      codigo: json['codigo'] as String,
      nombre: json['nombre'] as String,
      categoriaNombre: json['categoria_nombre'] as String?,
      precioDesde: json['precio_desde'] as String?,
      precioHasta: json['precio_hasta'] as String?,
      imagenUrl: json['imagen_url'] as String?,
      colores: (json['colores'] as List<dynamic>? ?? [])
          .map((c) => ColorPrenda.desdeJson(c as Map<String, dynamic>))
          .toList(),
      tieneVestidor: json['tiene_vestidor'] as bool? ?? false,
    );
  }
}

class PaginaVitrina {
  const PaginaVitrina({
    required this.total,
    required this.pagina,
    required this.tamano,
    required this.items,
  });

  final int total;
  final int pagina;
  final int tamano;
  final List<ProductoVitrina> items;

  /// Si quedan paginas por traer. Lo usa el desplazamiento infinito.
  bool get hayMas => pagina * tamano < total;

  factory PaginaVitrina.desdeJson(Map<String, dynamic> json) {
    return PaginaVitrina(
      total: json['total'] as int,
      pagina: json['pagina'] as int,
      tamano: json['tamano'] as int,
      items: (json['items'] as List<dynamic>)
          .map((p) => ProductoVitrina.desdeJson(p as Map<String, dynamic>))
          .toList(),
    );
  }
}

class ImagenPrenda {
  const ImagenPrenda({
    required this.id,
    required this.url,
    required this.esPrincipal,
    required this.orden,
    this.varianteId,
  });

  final int id;
  final String url;
  final int? varianteId;
  final bool esPrincipal;
  final int orden;

  factory ImagenPrenda.desdeJson(Map<String, dynamic> json) {
    return ImagenPrenda(
      id: json['id'] as int,
      url: json['url'] as String,
      varianteId: json['variante_id'] as int?,
      esPrincipal: json['es_principal'] as bool? ?? false,
      orden: json['orden'] as int? ?? 0,
    );
  }
}

/// Una combinacion talla x color ofrecible. Es el SKU y la unidad de negocio.
///
/// [imagenVestidorUrl] es la mitad de la costura **C5**: el PNG con fondo
/// transparente de ESTA variante, que es el activo del que depende el vestidor
/// virtual (supuesto S5). Viaja en la ficha para que la pantalla de realidad
/// aumentada reciba todo lo que necesita al navegar y no tenga que volver a
/// consultar la API ni conocer la tabla de imagenes.
class VariantePrenda {
  const VariantePrenda({
    required this.id,
    required this.sku,
    required this.precio,
    required this.tallaId,
    required this.colorId,
    this.tallaCodigo,
    this.colorNombre,
    this.colorHexadecimal,
    this.imagenVestidorUrl,
  });

  final int id;
  final String sku;
  final String precio;
  final int tallaId;
  final String? tallaCodigo;
  final int colorId;
  final String? colorNombre;
  final String? colorHexadecimal;
  final String? imagenVestidorUrl;

  bool get sePuedeProbar => imagenVestidorUrl != null;

  factory VariantePrenda.desdeJson(Map<String, dynamic> json) {
    return VariantePrenda(
      id: json['id'] as int,
      sku: json['sku'] as String,
      precio: json['precio'] as String,
      tallaId: json['talla_id'] as int,
      tallaCodigo: json['talla_codigo'] as String?,
      colorId: json['color_id'] as int,
      colorNombre: json['color_nombre'] as String?,
      colorHexadecimal: json['color_hexadecimal'] as String?,
      imagenVestidorUrl: json['imagen_vestidor_url'] as String?,
    );
  }
}

/// El detalle de una prenda (CU-18).
class FichaPrenda {
  const FichaPrenda({
    required this.id,
    required this.codigo,
    required this.nombre,
    required this.imagenes,
    required this.variantes,
    required this.tallas,
    required this.colores,
    required this.tieneVestidor,
    this.descripcion,
    this.categoriaNombre,
    this.precioDesde,
    this.precioHasta,
  });

  final int id;
  final String codigo;
  final String nombre;
  final String? descripcion;
  final String? categoriaNombre;
  final String? precioDesde;
  final String? precioHasta;
  final List<ImagenPrenda> imagenes;

  /// Ya vienen ordenadas por el orden del maestro de tallas.
  final List<VariantePrenda> variantes;

  final List<TallaPrenda> tallas;
  final List<ColorPrenda> colores;
  final bool tieneVestidor;

  /// Los colores en los que existe [tallaId]. No toda combinacion talla x color
  /// existe: puede haber S negra y M roja y ninguna S roja.
  List<ColorPrenda> coloresDeTalla(int? tallaId) {
    if (tallaId == null) return colores;
    final ids = variantes
        .where((v) => v.tallaId == tallaId)
        .map((v) => v.colorId)
        .toSet();
    return colores.where((c) => ids.contains(c.id)).toList();
  }

  /// Las tallas en las que existe [colorId].
  List<TallaPrenda> tallasDeColor(int? colorId) {
    if (colorId == null) return tallas;
    final ids = variantes
        .where((v) => v.colorId == colorId)
        .map((v) => v.tallaId)
        .toSet();
    return tallas.where((t) => ids.contains(t.id)).toList();
  }

  /// La variante que resulta de una talla y un color, si existe.
  VariantePrenda? varianteDe(int? tallaId, int? colorId) {
    if (tallaId == null || colorId == null) return null;
    for (final variante in variantes) {
      if (variante.tallaId == tallaId && variante.colorId == colorId) {
        return variante;
      }
    }
    return null;
  }

  String get precioRotulado {
    if (precioDesde == null) return 'Sin precio';
    if (precioHasta != null && precioHasta != precioDesde) {
      return 'Bs $precioDesde — $precioHasta';
    }
    return 'Bs $precioDesde';
  }

  factory FichaPrenda.desdeJson(Map<String, dynamic> json) {
    return FichaPrenda(
      id: json['id'] as int,
      codigo: json['codigo'] as String,
      nombre: json['nombre'] as String,
      descripcion: json['descripcion'] as String?,
      categoriaNombre: json['categoria_nombre'] as String?,
      precioDesde: json['precio_desde'] as String?,
      precioHasta: json['precio_hasta'] as String?,
      imagenes: (json['imagenes'] as List<dynamic>? ?? [])
          .map((i) => ImagenPrenda.desdeJson(i as Map<String, dynamic>))
          .toList(),
      variantes: (json['variantes'] as List<dynamic>? ?? [])
          .map((v) => VariantePrenda.desdeJson(v as Map<String, dynamic>))
          .toList(),
      tallas: (json['tallas'] as List<dynamic>? ?? [])
          .map((t) => TallaPrenda.desdeJson(t as Map<String, dynamic>))
          .toList(),
      colores: (json['colores'] as List<dynamic>? ?? [])
          .map((c) => ColorPrenda.desdeJson(c as Map<String, dynamic>))
          .toList(),
      tieneVestidor: json['tiene_vestidor'] as bool? ?? false,
    );
  }
}

/// CU-19 · cuanto hay de una variante en una sucursal.
///
/// La forma la fija el contrato de la costura **C1**. `cantidad_reservada` no
/// viaja a proposito: al cliente le sirve saber cuanto puede llevarse, y
/// publicar lo apartado dejaria deducir el movimiento comercial de cada tienda.
class DisponibilidadSucursal {
  const DisponibilidadSucursal({
    required this.sucursalId,
    required this.sucursalNombre,
    required this.ciudadNombre,
    required this.cantidadDisponible,
  });

  final int sucursalId;
  final String sucursalNombre;
  final String ciudadNombre;
  final int cantidadDisponible;

  String get unidades =>
      cantidadDisponible == 1 ? '1 unidad' : '$cantidadDisponible unidades';

  factory DisponibilidadSucursal.desdeJson(Map<String, dynamic> json) {
    return DisponibilidadSucursal(
      sucursalId: json['sucursal_id'] as int,
      sucursalNombre: json['sucursal_nombre'] as String,
      ciudadNombre: json['ciudad_nombre'] as String,
      cantidadDisponible: json['cantidad_disponible'] as int,
    );
  }
}

/// La respuesta de CU-19 para una variante.
class Disponibilidad {
  const Disponibilidad({
    required this.varianteId,
    required this.sku,
    required this.totalDisponible,
    required this.sucursales,
    this.tallaCodigo,
    this.colorNombre,
  });

  final int varianteId;
  final String sku;
  final String? tallaCodigo;
  final String? colorNombre;
  final int totalDisponible;

  /// Solo las sucursales donde hay algo.
  final List<DisponibilidadSucursal> sucursales;

  bool get hayStock => sucursales.isNotEmpty;

  factory Disponibilidad.desdeJson(Map<String, dynamic> json) {
    return Disponibilidad(
      varianteId: json['variante_id'] as int,
      sku: json['sku'] as String,
      tallaCodigo: json['talla_codigo'] as String?,
      colorNombre: json['color_nombre'] as String?,
      totalDisponible: json['total_disponible'] as int? ?? 0,
      sucursales: (json['sucursales'] as List<dynamic>? ?? [])
          .map(
            (s) => DisponibilidadSucursal.desdeJson(s as Map<String, dynamic>),
          )
          .toList(),
    );
  }
}

/// Las opciones del panel de filtros, con lo que el catalogo realmente ofrece.
class FiltrosDisponibles {
  const FiltrosDisponibles({
    required this.categorias,
    required this.tallas,
    required this.colores,
    required this.temporadas,
    this.precioMin,
    this.precioMax,
  });

  final List<CategoriaPrenda> categorias;
  final List<TallaPrenda> tallas;
  final List<ColorPrenda> colores;
  final List<TemporadaPrenda> temporadas;
  final String? precioMin;
  final String? precioMax;

  factory FiltrosDisponibles.desdeJson(Map<String, dynamic> json) {
    return FiltrosDisponibles(
      categorias: (json['categorias'] as List<dynamic>? ?? [])
          .map((c) => CategoriaPrenda.desdeJson(c as Map<String, dynamic>))
          .toList(),
      tallas: (json['tallas'] as List<dynamic>? ?? [])
          .map((t) => TallaPrenda.desdeJson(t as Map<String, dynamic>))
          .toList(),
      colores: (json['colores'] as List<dynamic>? ?? [])
          .map((c) => ColorPrenda.desdeJson(c as Map<String, dynamic>))
          .toList(),
      temporadas: (json['temporadas'] as List<dynamic>? ?? [])
          .map((t) => TemporadaPrenda.desdeJson(t as Map<String, dynamic>))
          .toList(),
      precioMin: json['precio_min'] as String?,
      precioMax: json['precio_max'] as String?,
    );
  }
}

/// Los criterios con los que se consulta la vitrina.
///
/// Inmutable y con [copiarCon]: el estado del filtro es lo que dispara la
/// consulta, y mutarlo en el lugar haria que Riverpod no se entere del cambio.
class ConsultaVitrina {
  const ConsultaVitrina({
    this.busqueda,
    this.categoriaId,
    this.tallaId,
    this.colorId,
    this.temporadaId,
    this.orden = 'novedades',
    this.pagina = 1,
    this.tamano = 12,
  });

  final String? busqueda;
  final int? categoriaId;
  final int? tallaId;
  final int? colorId;
  final int? temporadaId;

  /// `novedades`, `precio_asc`, `precio_desc` o `nombre`.
  final String orden;

  final int pagina;
  final int tamano;

  bool get hayFiltros =>
      (busqueda != null && busqueda!.isNotEmpty) ||
      categoriaId != null ||
      tallaId != null ||
      colorId != null ||
      temporadaId != null;

  /// Los `bool` de borrado existen porque `null` ya significa «no cambia»:
  /// sin ellos no habria forma de pedir «quitar el filtro de talla».
  ConsultaVitrina copiarCon({
    String? busqueda,
    int? categoriaId,
    int? tallaId,
    int? colorId,
    int? temporadaId,
    String? orden,
    int? pagina,
    bool borrarBusqueda = false,
    bool borrarCategoria = false,
    bool borrarTalla = false,
    bool borrarColor = false,
    bool borrarTemporada = false,
  }) {
    return ConsultaVitrina(
      busqueda: borrarBusqueda ? null : (busqueda ?? this.busqueda),
      categoriaId: borrarCategoria ? null : (categoriaId ?? this.categoriaId),
      tallaId: borrarTalla ? null : (tallaId ?? this.tallaId),
      colorId: borrarColor ? null : (colorId ?? this.colorId),
      temporadaId: borrarTemporada ? null : (temporadaId ?? this.temporadaId),
      orden: orden ?? this.orden,
      pagina: pagina ?? this.pagina,
      tamano: tamano,
    );
  }

  Map<String, dynamic> aParametros() {
    return {
      if (busqueda != null && busqueda!.isNotEmpty) 'busqueda': busqueda,
      if (categoriaId != null) 'categoria_id': categoriaId,
      if (tallaId != null) 'talla_id': tallaId,
      if (colorId != null) 'color_id': colorId,
      if (temporadaId != null) 'temporada_id': temporadaId,
      'orden': orden,
      'pagina': pagina,
      'tamano': tamano,
    };
  }

  /// Riverpod compara el estado por igualdad para decidir si vuelve a
  /// consultar. Sin esto, cada `copiarCon` produciria un objeto distinto
  /// aunque los criterios fueran los mismos, y la vitrina consultaria de mas.
  @override
  bool operator ==(Object otro) {
    return otro is ConsultaVitrina &&
        otro.busqueda == busqueda &&
        otro.categoriaId == categoriaId &&
        otro.tallaId == tallaId &&
        otro.colorId == colorId &&
        otro.temporadaId == temporadaId &&
        otro.orden == orden &&
        otro.pagina == pagina &&
        otro.tamano == tamano;
  }

  @override
  int get hashCode => Object.hash(
    busqueda,
    categoriaId,
    tallaId,
    colorId,
    temporadaId,
    orden,
    pagina,
    tamano,
  );
}
