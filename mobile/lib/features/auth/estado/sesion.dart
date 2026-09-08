import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/red/cliente_api.dart';
import '../../../core/red/error_api.dart';
import '../../../data/modelos/usuario_autenticado.dart';
import '../../../data/repositorios/auth_repositorio.dart';

/// Estado de sesion de la app (CU-02).
///
/// `null` = no hay sesion. `AsyncLoading` = todavia no se sabe, porque se esta
/// preguntando al servidor si el token guardado sigue valiendo; el enrutado lo
/// usa para mostrar la pantalla de arranque en vez de mandar al login a alguien
/// que en realidad si tenia sesion.
final sesionProvider =
    AsyncNotifierProvider<Sesion, UsuarioAutenticado?>(Sesion.new);

class Sesion extends AsyncNotifier<UsuarioAutenticado?> {
  @override
  Future<UsuarioAutenticado?> build() async {
    // Cualquier 401 en una ruta privada cierra la sesion local: el token fue
    // revocado o vencio y no tiene sentido seguir mostrando pantallas que van
    // a fallar una por una.
    ref.read(interceptorTokenProvider).alCaducarSesion = _alCaducar;

    final almacen = ref.read(almacenTokenProvider);
    if (await almacen.leer() == null) return null;

    try {
      return await ref.read(authRepositorioProvider).yo();
    } on ErrorApi {
      // Token guardado pero invalido, o sin conexion. En los dos casos se
      // arranca sin sesion; es preferible pedir credenciales de mas que dejar
      // la app en un estado que no se puede usar.
      await almacen.borrar();
      return null;
    }
  }

  /// CU-02 flujo principal. Las excepciones E1 (credenciales invalidas) y E2
  /// (cuenta desactivada) llegan como [ErrorApi] y las muestra la pantalla.
  Future<void> iniciar(String correo, String contrasena) async {
    final sesion =
        await ref.read(authRepositorioProvider).iniciarSesion(correo, contrasena);
    await ref.read(almacenTokenProvider).guardar(sesion.accessToken);
    state = AsyncData(sesion.usuario);
  }

  /// CU-02 flujo de cierre. Se avisa al servidor para que revoque el token,
  /// pero la sesion local se cierra igual aunque esa llamada falle: si no, un
  /// telefono sin senal no podria cerrar sesion nunca.
  Future<void> cerrar() async {
    try {
      await ref.read(authRepositorioProvider).cerrarSesion();
    } on ErrorApi {
      // Sin conexion o token ya revocado. Se sigue.
    }
    await ref.read(almacenTokenProvider).borrar();
    state = const AsyncData(null);
  }

  void _alCaducar() {
    if (state.value == null) return;
    ref.read(almacenTokenProvider).borrar();
    try {
      state = const AsyncData(null);
    } catch (_) {
      // El notificador ya no esta vivo. No hay nada que actualizar.
    }
  }
}
