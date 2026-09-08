/// Pruebas del arranque de la aplicacion.
///
/// No tocan la red: el almacen seguro se sustituye por uno falso, de modo que
/// la app arranca sin token y la redireccion tiene que dejarla en el login.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:violetboutique/app.dart';
import 'package:violetboutique/core/almacenamiento/almacen_seguro.dart';
import 'package:violetboutique/features/auth/estado_sesion.dart';

/// Almacen en memoria. `flutter_secure_storage` necesita el canal nativo, que
/// en las pruebas de widget no existe.
class AlmacenFalso implements AlmacenSeguro {
  String? _token;
  DateTime? _expira;

  @override
  Future<String?> leerToken() async => _token;

  @override
  Future<void> guardarToken(String token, DateTime expiraEn) async {
    _token = token;
    _expira = expiraEn;
  }

  @override
  Future<DateTime?> leerExpiracion() async => _expira;

  @override
  Future<bool> tokenVencido() async =>
      _expira != null && _expira!.toUtc().isBefore(DateTime.now().toUtc());

  @override
  Future<void> borrar() async {
    _token = null;
    _expira = null;
  }
}

void main() {
  testWidgets('sin token guardado, la app arranca en el login', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          almacenSeguroProvider.overrideWithValue(AlmacenFalso()),
        ],
        child: const AplicacionVioletBoutique(),
      ),
    );

    // Primer cuadro: todavia se esta comprobando el token.
    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    // Resuelta la comprobacion, la redireccion lleva al login.
    await tester.pumpAndSettle();
    expect(find.text('Iniciar sesion'), findsOneWidget);
    expect(find.text('Correo electronico'), findsOneWidget);
  });
}
