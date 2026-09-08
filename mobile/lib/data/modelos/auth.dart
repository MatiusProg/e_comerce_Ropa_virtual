/// Modelos del contrato de autenticacion.
///
/// Cada clase refleja un esquema de `backend/app/modules/seguridad/schemas.py`.
/// Los nombres de los campos JSON se escriben tal como los emite la API —en
/// castellano y en `snake_case`— y no se traducen: si el backend cambia un
/// nombre, esta es la unica capa que hay que tocar.
library;

/// Espejo de `UsuarioAutenticadoOut`.
class UsuarioAutenticado {
  const UsuarioAutenticado({
    required this.id,
    required this.correo,
    required this.nombres,
    required this.apellidos,
    required this.rol,
    this.sucursalId,
  });

  final int id;
  final String correo;
  final String nombres;
  final String apellidos;

  /// `CLIENTE`, `ADMINISTRADOR`, `ENCARGADO`, `CAJERO` o `PROVEEDOR`.
  final String rol;

  /// Solo viene para los roles cuyo ambito es una sucursal (`ENCARGADO`,
  /// `CAJERO`); ver `ROLES_CON_SUCURSAL` en el backend.
  final int? sucursalId;

  String get nombreCompleto => '$nombres $apellidos';

  /// Iniciales para el avatar. Vacio no puede ser: el backend exige
  /// `min_length=1` en nombres y apellidos.
  String get iniciales {
    final n = nombres.trim();
    final a = apellidos.trim();
    final primera = n.isNotEmpty ? n[0] : '';
    final segunda = a.isNotEmpty ? a[0] : '';
    return '$primera$segunda'.toUpperCase();
  }

  bool get esCliente => rol == 'CLIENTE';

  factory UsuarioAutenticado.desdeJson(Map<String, dynamic> json) {
    return UsuarioAutenticado(
      id: json['id'] as int,
      correo: json['correo'] as String,
      nombres: json['nombres'] as String,
      apellidos: json['apellidos'] as String,
      rol: json['rol'] as String,
      sucursalId: json['sucursal_id'] as int?,
    );
  }
}

/// Espejo de `TokenOut`, la respuesta de `POST /auth/login`.
class Token {
  const Token({
    required this.accessToken,
    required this.expiraEn,
    required this.usuario,
  });

  final String accessToken;
  final DateTime expiraEn;
  final UsuarioAutenticado usuario;

  factory Token.desdeJson(Map<String, dynamic> json) {
    return Token(
      accessToken: json['access_token'] as String,
      expiraEn: DateTime.parse(json['expira_en'] as String),
      usuario: UsuarioAutenticado.desdeJson(
        json['usuario'] as Map<String, dynamic>,
      ),
    );
  }
}

/// Espejo de `ClienteRegistroIn`, el cuerpo de `POST /auth/registro` (CU-01).
class DatosRegistro {
  const DatosRegistro({
    required this.nombres,
    required this.apellidos,
    required this.correo,
    required this.contrasena,
    this.documento,
    this.telefono,
  });

  final String nombres;
  final String apellidos;
  final String correo;
  final String contrasena;
  final String? documento;
  final String? telefono;

  /// El backend acepta `null` en documento y telefono, pero **no** cadena
  /// vacia con `max_length`; su validador convierte el vacio en ausencia. Se
  /// hace lo mismo aqui para no depender de ese detalle del otro lado.
  Map<String, dynamic> aJson() {
    String? limpio(String? valor) {
      final v = valor?.trim();
      return (v == null || v.isEmpty) ? null : v;
    }

    return {
      'nombres': nombres.trim(),
      'apellidos': apellidos.trim(),
      'correo': correo.trim().toLowerCase(),
      'contrasena': contrasena,
      'documento': limpio(documento),
      'telefono': limpio(telefono),
    };
  }
}
