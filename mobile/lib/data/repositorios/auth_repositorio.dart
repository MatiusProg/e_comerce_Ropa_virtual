import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/red/cliente_api.dart';
import '../../core/red/error_api.dart';
import '../modelos/registro_cliente.dart';
import '../modelos/sesion_token.dart';
import '../modelos/usuario_autenticado.dart';

final authRepositorioProvider = Provider<AuthRepositorio>(
  (ref) => AuthRepositorio(ref.watch(clienteApiProvider)),
);

/// Unico punto de la app que conoce las rutas de `/auth`.
///
/// Toda excepcion de Dio sale de aca convertida en [ErrorApi]: las pantallas
/// no importan `dio` ni saben que existe.
class AuthRepositorio {
  const AuthRepositorio(this._dio);

  final Dio _dio;

  /// CU-01 · `POST /auth/registro`. Devuelve los datos del cliente creado.
  /// No devuelve token a proposito: el caso de uso termina invitando a iniciar
  /// sesion, y emitir el token es CU-02.
  Future<UsuarioAutenticado> registrar(RegistroCliente datos) async {
    return _llamar(() async {
      final respuesta = await _dio.post<Map<String, dynamic>>(
        '/auth/registro',
        data: datos.aJson(),
      );
      return UsuarioAutenticado.desdeJson(respuesta.data!);
    });
  }

  /// CU-02 · `POST /auth/login`.
  Future<SesionToken> iniciarSesion(String correo, String contrasena) async {
    return _llamar(() async {
      final respuesta = await _dio.post<Map<String, dynamic>>(
        '/auth/login',
        data: {
          'correo': correo.trim().toLowerCase(),
          'contrasena': contrasena,
        },
      );
      return SesionToken.desdeJson(respuesta.data!);
    });
  }

  /// CU-02 · `POST /auth/logout`. Revoca el token en el servidor.
  Future<void> cerrarSesion() async {
    return _llamar(() async {
      await _dio.post<void>('/auth/logout');
    });
  }

  /// `GET /auth/yo`. Se usa al abrir la app: en vez de confiar en el token
  /// guardado, se le pregunta al servidor si sigue valiendo.
  Future<UsuarioAutenticado> yo() async {
    return _llamar(() async {
      final respuesta = await _dio.get<Map<String, dynamic>>('/auth/yo');
      return UsuarioAutenticado.desdeJson(respuesta.data!);
    });
  }

  Future<T> _llamar<T>(Future<T> Function() peticion) async {
    try {
      return await peticion();
    } on DioException catch (error) {
      throw ErrorApi.desdeDio(error);
    }
  }
}
