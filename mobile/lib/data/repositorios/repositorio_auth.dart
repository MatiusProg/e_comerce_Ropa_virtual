/// Acceso a los endpoints de seguridad (P1).
///
/// Un repositorio por paquete de analisis. Es el unico lugar de la app que
/// conoce las rutas de `/auth`; las pantallas hablan con el, nunca con Dio.
library;

import 'package:dio/dio.dart';

import '../../core/red/excepciones.dart';
import '../modelos/auth.dart';

/// Longitud minima de contrasena que exige el backend
/// (`CONTRASENA_LONGITUD_MINIMA` en `seguridad/schemas.py`). Se repite aqui
/// para poder validar en el formulario antes de gastar una llamada de red.
const int contrasenaLongitudMinima = 8;

class RepositorioAuth {
  const RepositorioAuth(this._dio);

  final Dio _dio;

  /// CU-01 · Registrar cliente.
  ///
  /// El caso de uso termina invitando a iniciar sesion: el backend responde
  /// 201 con los datos del cliente y **sin token**, asi que aqui tampoco se
  /// devuelve uno. Iniciar sesion es CU-02.
  Future<void> registrar(DatosRegistro datos) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        '/auth/registro',
        data: datos.aJson(),
      );
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// CU-02 · Iniciar sesion.
  Future<Token> iniciarSesion({
    required String correo,
    required String contrasena,
  }) async {
    try {
      final respuesta = await _dio.post<Map<String, dynamic>>(
        '/auth/login',
        data: {'correo': correo.trim().toLowerCase(), 'contrasena': contrasena},
      );
      return Token.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// CU-02 · Cerrar sesion. Revoca el token en el servidor.
  Future<void> cerrarSesion() async {
    try {
      await _dio.post<void>('/auth/logout');
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// Quien es el portador del token guardado.
  ///
  /// Se llama al arrancar la app: en vez de confiar en lo que haya en el
  /// telefono, se le pregunta al servidor. Si el token fue revocado, esto
  /// falla con 401 y la sesion se cierra sola.
  Future<UsuarioAutenticado> usuarioActual() async {
    try {
      final respuesta = await _dio.get<Map<String, dynamic>>('/auth/yo');
      return UsuarioAutenticado.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }
}
