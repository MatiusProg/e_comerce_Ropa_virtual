/// Estado de la sesion del usuario y los proveedores que dependen de el.
///
/// Es la fuente unica de verdad sobre "hay alguien conectado": el enrutador la
/// consulta para redirigir y las pantallas para saber a quien saludar.
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/almacenamiento/almacen_seguro.dart';
import '../../core/red/cliente_api.dart';
import '../../core/red/excepciones.dart';
import '../../data/modelos/auth.dart';
import '../../data/repositorios/repositorio_auth.dart';

// --- Estado ---------------------------------------------------------------

/// Los tres estados posibles. Son una jerarquia sellada y no un enum con
/// campos opcionales, para que el compilador obligue a contemplar los tres en
/// cada `switch` y no exista un "conectado con usuario nulo".
sealed class EstadoSesion {
  const EstadoSesion();
}

/// Arranque: todavia se esta comprobando si hay un token guardado. Dura lo que
/// tarde la llamada a `/auth/yo`.
class SesionComprobando extends EstadoSesion {
  const SesionComprobando();
}

/// No hay nadie conectado.
class SesionCerrada extends EstadoSesion {
  const SesionCerrada({this.aviso});

  /// Mensaje a mostrar al llegar al login — por ejemplo, cuando la sesion se
  /// cerro sola porque el token expiro.
  final String? aviso;
}

/// Hay un usuario conectado.
class SesionAbierta extends EstadoSesion {
  const SesionAbierta(this.usuario);

  final UsuarioAutenticado usuario;
}

// --- Proveedores ----------------------------------------------------------

final almacenSeguroProvider = Provider<AlmacenSeguro>((ref) => AlmacenSeguro());

final clienteApiProvider = Provider((ref) {
  return construirDio(
    almacen: ref.watch(almacenSeguroProvider),
    // `read` y no `watch`: esto se ejecuta cuando llega un 401, mucho despues
    // de construir el cliente. Con `watch` habria una dependencia circular
    // entre el cliente y la sesion.
    alPerderLaSesion: () async {
      await ref.read(sesionProvider.notifier).cerrarPorTokenInvalido();
    },
  );
});

final repositorioAuthProvider = Provider<RepositorioAuth>((ref) {
  return RepositorioAuth(ref.watch(clienteApiProvider));
});

final sesionProvider = NotifierProvider<ControlSesion, EstadoSesion>(
  ControlSesion.new,
);

/// Atajo para las pantallas que solo necesitan al usuario y no el estado
/// completo. Devuelve `null` si no hay sesion abierta.
final usuarioActualProvider = Provider<UsuarioAutenticado?>((ref) {
  final estado = ref.watch(sesionProvider);
  return estado is SesionAbierta ? estado.usuario : null;
});

// --- Control --------------------------------------------------------------

class ControlSesion extends Notifier<EstadoSesion> {
  @override
  EstadoSesion build() {
    // `build` tiene que ser sincrono, asi que la restauracion se dispara y el
    // estado arranca en "comprobando". El enrutador muestra la pantalla de
    // carga mientras tanto.
    Future.microtask(restaurar);
    return const SesionComprobando();
  }

  AlmacenSeguro get _almacen => ref.read(almacenSeguroProvider);
  RepositorioAuth get _repositorio => ref.read(repositorioAuthProvider);

  /// Reconstruye la sesion a partir del token guardado en el dispositivo.
  Future<void> restaurar() async {
    final token = await _almacen.leerToken();
    if (token == null || token.isEmpty) {
      state = const SesionCerrada();
      return;
    }

    // Descarte barato: si la fecha de expiracion ya paso, no hace falta
    // preguntarle al servidor.
    if (await _almacen.tokenVencido()) {
      await _almacen.borrar();
      state = const SesionCerrada();
      return;
    }

    try {
      state = SesionAbierta(await _repositorio.usuarioActual());
    } on ErrorApi {
      // Token revocado, o el servidor no responde. En ambos casos se entra sin
      // sesion; si fue lo segundo, el login lo dira al intentar conectarse.
      await _almacen.borrar();
      state = const SesionCerrada();
    }
  }

  /// CU-02 · Iniciar sesion. Propaga [ErrorApi] para que el formulario muestre
  /// el mensaje junto al boton, en vez de dejarlo en el estado global.
  Future<void> iniciarSesion({
    required String correo,
    required String contrasena,
  }) async {
    final token = await _repositorio.iniciarSesion(
      correo: correo,
      contrasena: contrasena,
    );
    await _almacen.guardarToken(token.accessToken, token.expiraEn);
    state = SesionAbierta(token.usuario);
  }

  /// CU-02 · Cerrar sesion.
  Future<void> cerrarSesion() async {
    try {
      await _repositorio.cerrarSesion();
    } on ErrorApi {
      // Si la revocacion falla —sin red, o el token ya no valia— la sesion se
      // cierra igual en el dispositivo. Lo contrario dejaria al usuario
      // atrapado dentro de la app.
    } finally {
      await _almacen.borrar();
      state = const SesionCerrada();
    }
  }

  /// La invoca el interceptor cuando el servidor responde 401 a una ruta
  /// privada: el token dejo de valer mientras la app estaba en uso.
  Future<void> cerrarPorTokenInvalido() async {
    if (state is SesionCerrada) return;
    await _almacen.borrar();
    state = const SesionCerrada(
      aviso: 'Su sesion expiro. Vuelva a iniciar sesion.',
    );
  }
}
