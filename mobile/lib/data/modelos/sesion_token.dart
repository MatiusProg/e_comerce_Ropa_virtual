import 'usuario_autenticado.dart';

/// Respuesta del login. Replica `TokenOut` del backend.
class SesionToken {
  const SesionToken({
    required this.accessToken,
    required this.expiraEn,
    required this.usuario,
  });

  final String accessToken;
  final DateTime expiraEn;
  final UsuarioAutenticado usuario;

  factory SesionToken.desdeJson(Map<String, dynamic> json) => SesionToken(
        accessToken: json['access_token'] as String,
        expiraEn: DateTime.parse(json['expira_en'] as String),
        usuario: UsuarioAutenticado.desdeJson(
          json['usuario'] as Map<String, dynamic>,
        ),
      );
}
