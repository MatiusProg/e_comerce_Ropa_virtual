/// Acceso a los endpoints del perfil del cliente (CU-04) y al listado de
/// ciudades que necesita su formulario de direcciones.
///
/// Mismo criterio que `RepositorioAuth`: es el único lugar de la app que
/// conoce estas rutas, y ninguna excepción de Dio sale de aquí sin traducir.
library;

import 'package:dio/dio.dart';

import '../../core/red/excepciones.dart';
import '../modelos/perfil.dart';

class RepositorioPerfil {
  const RepositorioPerfil(this._dio);

  final Dio _dio;

  /// CU-04 paso 2 · `GET /perfil`.
  Future<Perfil> obtener() async {
    try {
      final respuesta = await _dio.get<Map<String, dynamic>>('/perfil');
      return Perfil.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// CU-04 paso 3 · `PATCH /perfil`. Datos personales y tallas habituales.
  ///
  /// Devuelve el perfil ya actualizado, así que no hace falta volver a pedirlo.
  Future<Perfil> editar(EdicionPerfil datos) async {
    try {
      final respuesta = await _dio.patch<Map<String, dynamic>>(
        '/perfil',
        data: datos.aJson(),
      );
      return Perfil.desdeJson(respuesta.data!);
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// CU-04 flujo alternativo 3a · `POST /perfil/direcciones`.
  Future<void> agregarDireccion(NuevaDireccion datos) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        '/perfil/direcciones',
        data: datos.aJson(),
      );
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// CU-04 · `PATCH /perfil/direcciones/{id}/predeterminada`.
  ///
  /// Marcar una quita la marca de la anterior; eso lo resuelve el servicio, no
  /// esta app.
  Future<void> marcarPredeterminada(int direccionId) async {
    try {
      await _dio.patch<void>('/perfil/direcciones/$direccionId/predeterminada');
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// CU-04 · `DELETE /perfil/direcciones/{id}`.
  Future<void> eliminarDireccion(int direccionId) async {
    try {
      await _dio.delete<void>('/perfil/direcciones/$direccionId');
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// CU-04 flujo alternativo 3c · `PUT /perfil/contrasena`.
  Future<void> cambiarContrasena(CambioContrasena datos) async {
    try {
      await _dio.put<void>('/perfil/contrasena', data: datos.aJson());
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }

  /// `GET /organizacion/ciudades`, para poblar el selector del formulario de
  /// direcciones.
  ///
  /// Vive en el `consulta_router` del backend, que admite Cliente además de
  /// Administrador; el resto de `/organizacion` exige Administrador. Ver
  /// §6.11.4 de las decisiones técnicas.
  Future<List<Ciudad>> ciudades() async {
    try {
      final respuesta = await _dio.get<List<dynamic>>(
        '/organizacion/ciudades',
      );
      return respuesta.data!
          .map((e) => Ciudad.desdeJson(e as Map<String, dynamic>))
          .toList();
    } on DioException catch (fallo) {
      throw traducirError(fallo);
    }
  }
}
