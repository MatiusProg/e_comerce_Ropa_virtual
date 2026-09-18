/// CU-21 · Medidas del cuerpo y ajuste de la prenda por talla.
///
/// EL PROBLEMA QUE ESTO RESUELVE
/// -----------------------------
/// Hasta el 18/09 el vestidor escalaba la prenda para que CALZARA el cuerpo,
/// siempre. La consecuencia es que **la XS y la XXL se veian identicas en
/// pantalla**: el cliente elegia talla a ciegas, que es justo lo que un
/// probador tendria que resolver.
///
/// Con las medidas del cliente y las de la prenda, el servidor devuelve cuanto
/// ensanchar y alargar cada talla al dibujarla, y cual le corresponde.
///
/// TODO DEGRADA A LO DE ANTES
/// ---------------------------
/// Si el cliente no cargo sus medidas, o el producto no tiene tabla de tallas,
/// la respuesta viene con `hayMedidas` o `hayTabla` en falso y sin factores. La
/// pantalla dibuja como dibujaba siempre. Una funcionalidad nueva que rompe el
/// vestidor cuando le falta un dato es peor que no tenerla.
library;

import 'package:dio/dio.dart';

import '../../core/red/excepciones.dart';

/// Como le queda una talla a un cuerpo. Los mismos codigos que manda la API.
enum Ajuste {
  noEntra,
  ajustada,
  aTuMedida,
  holgada,
  muyHolgada;

  static Ajuste desdeCodigo(String? codigo) => switch (codigo) {
    'NO_ENTRA' => Ajuste.noEntra,
    'AJUSTADA' => Ajuste.ajustada,
    'A_TU_MEDIDA' => Ajuste.aTuMedida,
    'HOLGADA' => Ajuste.holgada,
    _ => Ajuste.muyHolgada,
  };

  /// El texto se escribe ACA y no en la API, para poder cambiarlo sin
  /// desplegar el servidor y porque la web lo dice distinto.
  String get texto => switch (this) {
    Ajuste.noEntra => 'No te entra',
    Ajuste.ajustada => 'Te queda ajustada',
    Ajuste.aTuMedida => 'Te queda bien',
    Ajuste.holgada => 'Te queda holgada',
    Ajuste.muyHolgada => 'Te queda muy holgada',
  };
}

class MedidasCuerpo {
  const MedidasCuerpo({
    required this.bustoCm,
    required this.cinturaCm,
    required this.caderaCm,
    this.alturaCm,
  });

  final double bustoCm;
  final double cinturaCm;
  final double caderaCm;
  final double? alturaCm;

  factory MedidasCuerpo.desdeJson(Map<String, dynamic> json) {
    double leer(String clave) => double.parse('${json[clave]}');
    return MedidasCuerpo(
      bustoCm: leer('busto_cm'),
      cinturaCm: leer('cintura_cm'),
      caderaCm: leer('cadera_cm'),
      alturaCm: json['altura_cm'] == null
          ? null
          : double.tryParse('${json['altura_cm']}'),
    );
  }

  Map<String, dynamic> aJson() => {
    'busto_cm': bustoCm,
    'cintura_cm': cinturaCm,
    'cadera_cm': caderaCm,
    if (alturaCm != null) 'altura_cm': alturaCm,
  };
}

class AjusteDeTalla {
  const AjusteDeTalla({
    required this.tallaId,
    required this.codigo,
    required this.bustoCm,
    required this.largoCm,
    required this.ajuste,
    required this.factorAncho,
    required this.factorLargo,
  });

  final int tallaId;
  final String codigo;
  final double bustoCm;
  final double largoCm;
  final Ajuste ajuste;

  /// Cuanto ensanchar la prenda al dibujarla. 1.0 = la talla que corresponde
  /// al cuerpo, que se dibuja como se dibujaba siempre.
  final double factorAncho;

  /// Lo mismo para el largo. Es lo que hace que una XS se vea CORTA.
  final double factorLargo;

  factory AjusteDeTalla.desdeJson(Map<String, dynamic> json) => AjusteDeTalla(
    tallaId: json['talla_id'] as int,
    codigo: json['codigo'] as String,
    bustoCm: double.parse('${json['busto_cm']}'),
    largoCm: double.parse('${json['largo_cm']}'),
    ajuste: Ajuste.desdeCodigo(json['ajuste'] as String?),
    factorAncho: (json['factor_ancho'] as num).toDouble(),
    factorLargo: (json['factor_largo'] as num).toDouble(),
  );
}

class AjusteDeProducto {
  const AjusteDeProducto({
    required this.hayMedidas,
    required this.hayTabla,
    this.tallaRecomendadaId,
    this.tallaRecomendada,
    this.tallas = const [],
  });

  /// Lo que se devuelve cuando la consulta falla. **No es un error visible**:
  /// el vestidor dibuja como siempre.
  static const ninguno = AjusteDeProducto(hayMedidas: false, hayTabla: false);

  final bool hayMedidas;
  final bool hayTabla;
  final int? tallaRecomendadaId;
  final String? tallaRecomendada;
  final List<AjusteDeTalla> tallas;

  bool get sirve => hayMedidas && hayTabla && tallas.isNotEmpty;

  AjusteDeTalla? de(int tallaId) {
    for (final t in tallas) {
      if (t.tallaId == tallaId) return t;
    }
    return null;
  }

  factory AjusteDeProducto.desdeJson(Map<String, dynamic> json) =>
      AjusteDeProducto(
        hayMedidas: json['hay_medidas'] as bool? ?? false,
        hayTabla: json['hay_tabla'] as bool? ?? false,
        tallaRecomendadaId: json['talla_recomendada_id'] as int?,
        tallaRecomendada: json['talla_recomendada'] as String?,
        tallas: ((json['tallas'] as List?) ?? const [])
            .map((e) => AjusteDeTalla.desdeJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class RepositorioMedidas {
  const RepositorioMedidas(this._dio);

  final Dio _dio;

  /// `null` cuando el cliente todavia no las cargo. **No es un error**: es el
  /// estado normal de una cuenta nueva.
  Future<MedidasCuerpo?> mias() async {
    try {
      final r = await _dio.get<Map<String, dynamic>>('/clientes/me/medidas');
      final datos = r.data;
      return datos == null ? null : MedidasCuerpo.desdeJson(datos);
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  Future<MedidasCuerpo> guardar(MedidasCuerpo medidas) async {
    try {
      final r = await _dio.put<Map<String, dynamic>>(
        '/clientes/me/medidas',
        data: medidas.aJson(),
      );
      return MedidasCuerpo.desdeJson(r.data!);
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// Ante cualquier fallo devuelve `ninguno` en vez de lanzar.
  ///
  /// El vestidor tiene que abrir aunque esto no responda: la camara y la
  /// superposicion no dependen del servidor, y hacer que un extra opcional
  /// impida probarse una prenda seria cambiar una mejora por una regresion.
  Future<AjusteDeProducto> deProducto(int productoId) async {
    try {
      final r = await _dio.get<Map<String, dynamic>>(
        '/tienda/productos/$productoId/ajuste',
      );
      return AjusteDeProducto.desdeJson(r.data ?? const {});
    } catch (_) {
      return AjusteDeProducto.ninguno;
    }
  }
}
