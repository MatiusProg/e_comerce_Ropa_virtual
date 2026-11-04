/// CU-42 · Avisos push en el telefono (Firebase Cloud Messaging).
///
/// QUE HACE CADA PIEZA
/// -------------------
/// - **FCM** entrega el aviso. Con la app cerrada o en segundo plano, Android
///   lo muestra solo en la bandeja, en el canal `avisos`.
/// - **flutter_local_notifications** lo muestra cuando la app esta ABIERTA:
///   ahi Android no pinta nada y el aviso llega solo a `onMessage`.
/// - **El backend** guarda el token en `/notificaciones/push/dispositivos` al
///   abrir sesion, y lo da de baja al cerrarla: el telefono no puede seguir
///   recibiendo los avisos de una cuenta que ya no esta adentro.
///
/// SIN `google-services.json` NO HAY PUSH, Y NO PASA NADA
/// ------------------------------------------------------
/// El archivo no se versiona. Sin el, `Firebase.initializeApp()` falla, se
/// atrapa y `disponible` queda en falso: la app funciona igual y los avisos
/// siguen en la campanita.
///
/// EL TOKEN «VIEJO» A PROPOSITO
/// ----------------------------
/// firebase_messaging 17 marca `getToken`/`onTokenRefresh` como obsoletos en
/// favor de `register()`/`onRegistered`, que entregan el Firebase Installation
/// ID para un envio «directo». El backend manda por la API HTTP v1 con
/// `message.token`, que es el token de registro de siempre; mientras no se
/// verifique que la v1 acepta el FID, se usa el token clasico.
// ignore_for_file: deprecated_member_use
library;

import 'dart:async';

import 'package:dio/dio.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

const _canal = AndroidNotificationChannel(
  'avisos',
  'Avisos de Violet Boutique',
  description: 'Reservas, compras y operaciones sin conexión.',
  importance: Importance.high,
);

class ServicioPush {
  ServicioPush._();

  static final ServicioPush instancia = ServicioPush._();

  bool _disponible = false;
  bool get disponible => _disponible;

  String? _tokenRegistrado;
  StreamSubscription<String>? _renovacion;
  final _locales = FlutterLocalNotificationsPlugin();

  /// A donde llevar al tocar un aviso. Lo conecta `app.dart` con el router.
  void Function(String enlace)? alTocar;

  /// Se llama una vez en `main`, antes de `runApp`. Nunca falla.
  Future<void> inicializar() async {
    try {
      await Firebase.initializeApp();
    } catch (e) {
      debugPrint('CU-42: push apagado (sin google-services.json?): $e');
      return;
    }
    _disponible = true;

    await _locales.initialize(
      settings: const InitializationSettings(
        android: AndroidInitializationSettings('@mipmap/ic_launcher'),
      ),
      onDidReceiveNotificationResponse: (r) {
        final enlace = r.payload;
        if (enlace != null && enlace.isNotEmpty) alTocar?.call(enlace);
      },
    );
    await _locales
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(_canal);

    // App abierta: Android no lo muestra, se pinta a mano.
    FirebaseMessaging.onMessage.listen((mensaje) {
      final n = mensaje.notification;
      if (n == null) return;
      _locales.show(
        id: mensaje.hashCode & 0x7fffffff,
        title: n.title,
        body: n.body,
        notificationDetails: NotificationDetails(
          android: AndroidNotificationDetails(
            _canal.id,
            _canal.name,
            channelDescription: _canal.description,
            importance: Importance.high,
            priority: Priority.high,
            styleInformation: BigTextStyleInformation(n.body ?? ''),
          ),
        ),
        payload: mensaje.data['enlace'] as String?,
      );
    });

    // Tocado con la app en segundo plano, o con la app cerrada.
    FirebaseMessaging.onMessageOpenedApp.listen(_abrir);
    final inicial = await FirebaseMessaging.instance.getInitialMessage();
    if (inicial != null) {
      // Despues del primer cuadro: el router todavia no existe.
      Future.delayed(const Duration(milliseconds: 600), () => _abrir(inicial));
    }
  }

  void _abrir(RemoteMessage mensaje) {
    final enlace = mensaje.data['enlace'] as String?;
    if (enlace != null && enlace.isNotEmpty) alTocar?.call(enlace);
  }

  /// Registra ESTE telefono para la cuenta que acaba de abrir sesion.
  /// Idempotente en el servidor. Nunca falla: el push es un extra.
  Future<void> registrar(Dio dio) async {
    if (!_disponible) return;
    try {
      final permiso = await FirebaseMessaging.instance.requestPermission();
      if (permiso.authorizationStatus == AuthorizationStatus.denied) return;
      final token = await FirebaseMessaging.instance.getToken();
      if (token == null) return;
      await _enviar(dio, token);
      await _renovacion?.cancel();
      _renovacion = FirebaseMessaging.instance.onTokenRefresh.listen(
        (nuevo) => _enviar(dio, nuevo).catchError((_) {}),
      );
    } catch (e) {
      debugPrint('CU-42: no se pudo registrar el dispositivo: $e');
    }
  }

  Future<void> _enviar(Dio dio, String token) async {
    await dio.post<void>(
      '/notificaciones/push/dispositivos',
      data: {
        'canal': 'FCM',
        'direccion': token,
        'dispositivo': 'App Android',
      },
    );
    _tokenRegistrado = token;
  }

  /// Al cerrar sesion, ANTES del logout (necesita el token de la sesion).
  Future<void> darDeBaja(Dio dio) async {
    await _renovacion?.cancel();
    _renovacion = null;
    final token = _tokenRegistrado ??
        (_disponible ? await FirebaseMessaging.instance.getToken() : null);
    _tokenRegistrado = null;
    if (token == null) return;
    try {
      await dio
          .post<void>(
            '/notificaciones/push/dispositivos/baja',
            data: {'direccion': token},
          )
          .timeout(const Duration(seconds: 5));
    } catch (_) {
      // Sin red: el proximo que inicie sesion en este telefono se lo queda.
    }
  }
}

final servicioPushProvider = Provider<ServicioPush>((ref) => ServicioPush.instancia);
