/// Guarda del token JWT en el almacenamiento cifrado del dispositivo.
///
/// El token no va a `shared_preferences`: en Android eso es un XML en claro
/// dentro del sandbox de la app, legible en un dispositivo con root. La
/// contraparte de la web guarda el token en `localStorage` porque el navegador
/// no ofrece nada mejor; en el telefono si lo hay, y se usa.
library;

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../constantes.dart';

class AlmacenSeguro {
  // En `flutter_secure_storage` 11 el cifrado dejo de ser opcional: la opcion
  // `encryptedSharedPreferences` de las versiones 9 y 10 ya no existe porque
  // ahora es el unico comportamiento. Por eso no se pasan `AndroidOptions`.
  AlmacenSeguro([FlutterSecureStorage? almacen])
    : _almacen = almacen ?? const FlutterSecureStorage();

  final FlutterSecureStorage _almacen;

  Future<String?> leerToken() => _almacen.read(key: ClavesAlmacen.token);

  /// Guarda el token y su fecha de expiracion.
  ///
  /// La fecha se guarda aparte para poder descartar un token vencido sin
  /// abrirlo ni gastar una llamada a la API: es el mismo `expira_en` que
  /// devuelve `TokenOut` en el login.
  Future<void> guardarToken(String token, DateTime expiraEn) async {
    await _almacen.write(key: ClavesAlmacen.token, value: token);
    await _almacen.write(
      key: ClavesAlmacen.expiraEn,
      value: expiraEn.toIso8601String(),
    );
  }

  Future<DateTime?> leerExpiracion() async {
    final texto = await _almacen.read(key: ClavesAlmacen.expiraEn);
    if (texto == null) return null;
    return DateTime.tryParse(texto);
  }

  /// `true` si hay un token guardado y su fecha de expiracion ya paso.
  ///
  /// Se compara en UTC porque el backend emite la fecha en UTC y el telefono
  /// puede estar en cualquier huso.
  Future<bool> tokenVencido() async {
    final expira = await leerExpiracion();
    if (expira == null) return false;
    return expira.toUtc().isBefore(DateTime.now().toUtc());
  }

  Future<void> borrar() async {
    await _almacen.delete(key: ClavesAlmacen.token);
    await _almacen.delete(key: ClavesAlmacen.expiraEn);
  }
}
