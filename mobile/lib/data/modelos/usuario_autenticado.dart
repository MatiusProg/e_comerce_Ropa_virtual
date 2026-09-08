/// Quien es el portador del token. Es la respuesta de `GET /auth/yo` y viaja
/// tambien dentro de la del login.
///
/// Replica `UsuarioAutenticadoOut` de
/// `backend/app/modules/seguridad/schemas.py`. Si ese esquema cambia, este
/// modelo cambia con el.
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
  final String rol;
  final int? sucursalId;

  String get nombreCompleto => '$nombres $apellidos';

  /// Iniciales para el avatar del menu.
  String get iniciales {
    final n = nombres.trim();
    final a = apellidos.trim();
    final primera = n.isEmpty ? '' : n[0];
    final segunda = a.isEmpty ? '' : a[0];
    final iniciales = '$primera$segunda'.toUpperCase();
    return iniciales.isEmpty ? '?' : iniciales;
  }

  bool get esCliente => rol.toUpperCase() == 'CLIENTE';

  factory UsuarioAutenticado.desdeJson(Map<String, dynamic> json) =>
      UsuarioAutenticado(
        id: json['id'] as int,
        correo: json['correo'] as String,
        nombres: json['nombres'] as String,
        apellidos: json['apellidos'] as String,
        rol: json['rol'] as String,
        sucursalId: json['sucursal_id'] as int?,
      );
}
