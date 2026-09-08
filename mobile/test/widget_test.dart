import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:violetboutique/data/modelos/usuario_autenticado.dart';
import 'package:violetboutique/features/auth/estado/sesion.dart';
import 'package:violetboutique/main.dart';

/// Sesion falsa: evita que el arranque llame a la API real.
class _SesionSinCuenta extends Sesion {
  @override
  Future<UsuarioAutenticado?> build() async => null;
}

void main() {
  testWidgets(
    'sin sesion guardada, la app arranca en el login (CU-02)',
    (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sesionProvider.overrideWith(_SesionSinCuenta.new),
          ],
          child: const VioletBoutiqueApp(),
        ),
      );

      // Un pump por la pantalla de arranque y otro por el redirect.
      await tester.pumpAndSettle();

      expect(find.text('Iniciar sesión'), findsOneWidget);
      expect(find.text('¿No tenés cuenta? Registrate'), findsOneWidget);
    },
  );
}
