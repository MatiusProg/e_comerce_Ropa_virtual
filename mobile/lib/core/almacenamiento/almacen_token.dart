import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Guarda el token de sesion en el almacenamiento cifrado del dispositivo.
///
/// No se usa `shared_preferences`: ahi el token queda en texto plano y
/// cualquier copia de seguridad del telefono se lo lleva. `flutter_secure_storage`
/// lo deja en el Keystore de Android.
class AlmacenToken {
  AlmacenToken([FlutterSecureStorage? almacen])
      : _almacen = almacen ?? const FlutterSecureStorage();

  static const String _claveToken = 'violetboutique.token';

  final FlutterSecureStorage _almacen;

  /// Copia en memoria, para no ir al Keystore en cada peticion HTTP.
  /// `null` significa "todavia no se leyo", distinto de "no hay token".
  String? _enMemoria;
  bool _leido = false;

  Future<String?> leer() async {
    if (_leido) return _enMemoria;
    _enMemoria = await _almacen.read(key: _claveToken);
    _leido = true;
    return _enMemoria;
  }

  Future<void> guardar(String token) async {
    _enMemoria = token;
    _leido = true;
    await _almacen.write(key: _claveToken, value: token);
  }

  Future<void> borrar() async {
    _enMemoria = null;
    _leido = true;
    await _almacen.delete(key: _claveToken);
  }
}
